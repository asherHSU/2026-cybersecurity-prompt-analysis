"""
用 Ollama 對剩餘 ~29,150 筆 prompt 自動編碼
- 參考 300 筆人工編碼（人工編碼簿_v2.csv）作為 few-shot 範例
- 輸出格式與人工編碼簿一致（四欄）

執行前提：人工編碼簿_v2.csv 的 300 筆必須全部編碼完成。
若仍有空白，腳本會停下並提示尚有幾筆未編。
"""

import csv, json, random, requests, sys, time, re
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")

BASE        = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\datasets")
CODED_FILE  = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\data\人工編碼簿_v2.csv")
OUTPUT      = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\data\coded_remaining_v2.csv")
                  # 輸出到新檔，舊的 coded_remaining.csv（修正前版本）完整保留
OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "mistral:7b"
SEED        = 42
BATCH_SAVE  = 50
WORKERS     = 1       # 並行數。實測 8GB GPU 上 mistral:7b 已吃滿算力，並行無加速，故設 1。
                      # 若日後換更大顯卡或更小模型，可調高（2~4）試試。
TIMEOUT     = 45      # 單筆逾時（秒）；正常 <1.5 秒，留餘裕避免偶發塞車誤判逾時
RETRIES     = 1       # 失敗自動重試次數
KEEP_ALIVE  = "30m"   # 讓模型常駐顯存，避免反覆載入

CFA_COL = "Binary classfication of Contextual Framing Availibility (CFA)"
CFA_SUB = "Binary classfication based on the CFA value = 1"
OA_COL  = "Binary classfication of Operational Actionability (OA)"
OA_SUB  = "Binary classfication based on the OA value = 1"

# ── 1. 讀取人工編碼 300 筆 ────────────────────────────────────────
# already_coded：全部 300 筆 prompt，用來從待編碼池中排除
# examples     ：只收「已填編碼」的，當 few-shot 範例（空白的不能當範例）
already_coded = set()
examples = []
uncoded = 0

with open(CODED_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        prompt = row["prompt"].strip()
        already_coded.add(prompt)
        cfa     = row.get(CFA_COL, "").strip()
        cfa_sub = row.get(CFA_SUB, "").strip()
        oa      = row.get(OA_COL,  "").strip()
        oa_sub  = row.get(OA_SUB,  "").strip()
        if not cfa:                      # 尚未人工編碼
            uncoded += 1
            continue
        examples.append({
            "prompt":   prompt,
            "CFA":      cfa,
            "CFA_sub":  cfa_sub,
            "OA":       oa,
            "OA_sub":   oa_sub,
        })

print(f"參考檔總筆數：{len(already_coded)}")
print(f"已編碼（可當範例）：{len(examples)} 筆")

if uncoded > 0:
    print(f"\n⚠️ 還有 {uncoded} 筆尚未人工編碼，請先完成 {CODED_FILE.name} 再執行。")
    sys.exit(1)

# ── 2. 挑選 few-shot（各類別代表） ───────────────────────────────
random.seed(SEED)
from collections import defaultdict
buckets = defaultdict(list)
for e in examples:
    key = f"CFA={e['CFA']}{e['CFA_sub']}_OA={e['OA']}{e['OA_sub']}"
    buckets[key].append(e)

fewshot = []
for items in buckets.values():
    fewshot.extend(random.sample(items, min(3, len(items))))
fewshot = fewshot[:30]
print(f"Few-shot 範例：{len(fewshot)} 筆")

# few-shot 區塊只組一次（內容固定，不需每筆重組）
FEWSHOT_BLOCK = ""
for e in fewshot:
    FEWSHOT_BLOCK += f'Prompt: "{e["prompt"][:200]}"\n'
    FEWSHOT_BLOCK += f'CFA: {e["CFA"]} | CFA_sub: {e["CFA_sub"]} | OA: {e["OA"]} | OA_sub: {e["OA_sub"]}\n\n'

# ── 3. 建立 prompt template ──────────────────────────────────────
def build_prompt(target_prompt):
    # 超長 prompt 只取前 300 字
    truncated = target_prompt[:300] + ("..." if len(target_prompt) > 300 else "")

    return f"""You are a research coding assistant. Code the prompt strictly by these rules.

### CFA (Contextual Framing Availability)
Does the prompt provide context (role, purpose, background, task setting)?
- CFA=0, CFA_sub=  : no context provided
- CFA=1, CFA_sub=A : has context, but only one brief sentence of context
- CFA=1, CFA_sub=B : has context, with further elaboration beyond the first sentence
- CFA=999, CFA_sub=  : NOT cybersecurity-related (e.g. fraud, fake ID, financial crime)

### OA (Operational Actionability)
Does the prompt request specific operational details?
(If CFA=999, set OA=999, OA_sub= )
- OA=0, OA_sub=  : no specific operational details requested
- OA=1, OA_sub=A : requests knowledge-level text only (steps, methods, strategies)
- OA=1, OA_sub=B : requests weaponizable content (executable code, scripts, malware)

### Examples
{FEWSHOT_BLOCK}
### Now code this prompt. Reply with ONLY 4 comma-separated values (no labels, no header).
Format: <CFA>,<CFA_sub>,<OA>,<OA_sub>   e.g.  0,,1,A   or   1,B,1,B   or   999,,999,

Prompt: "{truncated}"
Answer:"""

# ── 4. 解析回應 ───────────────────────────────────────────────────
def parse_response(text):
    """穩健解析：不管模型有沒有夾帶標籤（CFA_sub: A）或照抄標題，
    都依序抽出值(0/1/999)與子分類(A/B)。順序固定為 CFA, [CFA_sub], OA, [OA_sub]。"""
    line = text.strip().split("\n")[0]

    # 先移除標籤字樣與分隔符，避免被當成 token
    cleaned = re.sub(r"(?i)\b(cfa_value|cfa_sub|oa_value|oa_sub|cfa|oa|value|sub)\b", " ", line)
    cleaned = re.sub(r"[:=|,]", " ", cleaned)
    # 值與子分類黏在一起時拆開（如 1A → 1 A），但不影響 999
    cleaned = re.sub(r"(?i)(?<=\d)([ab])\b", r" \1", cleaned)

    # 依出現順序收集 V(值) 與 S(子分類)
    cfa = cfa_sub = oa = oa_sub = ""
    vcount = 0
    for tok in cleaned.split():
        if tok in ("0", "1", "999"):
            vcount += 1
            if vcount == 1:   cfa = tok
            elif vcount == 2: oa = tok
        elif tok.upper() in ("A", "B"):
            if vcount == 1:   cfa_sub = tok.upper()   # 在 CFA 值之後、OA 值之前 → 屬 CFA
            elif vcount == 2: oa_sub = tok.upper()    # 在 OA 值之後 → 屬 OA

    # 值必須有效，否則 ERR（觸發重試）
    if cfa not in ("0", "1", "999") or oa not in ("0", "1", "999"):
        return "ERR", "", "ERR", ""

    # 任一為 999 → 兩者皆 999、子分類留空
    if cfa == "999" or oa == "999":
        return "999", "", "999", ""

    # CFA=1 / OA=1 一定要有子分類，缺了視為失敗（觸發重試，避免無聲遺漏）
    if cfa == "1" and cfa_sub not in ("A", "B"):
        return "ERR", "", "ERR", ""
    if oa == "1" and oa_sub not in ("A", "B"):
        return "ERR", "", "ERR", ""

    # CFA=0 / OA=0 子分類應為空
    if cfa == "0": cfa_sub = ""
    if oa == "0":  oa_sub = ""

    return cfa, cfa_sub, oa, oa_sub

def code_prompt(target):
    payload = {
        "model": MODEL,
        "prompt": build_prompt(target),
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": 0.1, "num_predict": 20},
    }
    last_raw = ""
    # 逾時或解析失敗時，最多重試 RETRIES 次
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
            last_raw = resp.json().get("response", "")
            result = parse_response(last_raw)
            if result[0] != "ERR" and result[2] != "ERR":
                return result
        except Exception as e:
            last_raw = f"<EXC:{type(e).__name__}>"
    # 最終仍失敗：記錄原始回應供診斷
    try:
        with open(r"C:\Users\simonnien\Desktop\2026詩雅poster\err_debug.log", "a", encoding="utf-8") as ef:
            ef.write(f"RAW>>>{last_raw}<<< | PROMPT>>>{target[:80]}<<<\n")
    except Exception:
        pass
    return "ERR", "", "ERR", ""

# ── 5. 載入剩餘資料 ───────────────────────────────────────────────
def load_all():
    pool = []
    with open(BASE / "CySecBench/Dataset/Full dataset/cysecbench.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r["Prompt"].strip()
            if p and p not in already_coded: pool.append({"source": "CySecBench", "prompt": p})

    with open(BASE / "CyberattackAssistance/mitre_benchmark.json", encoding="utf-8") as f:
        for item in json.load(f):
            p = item.get("base_prompt", "").strip()
            if p and "#ERROR!" not in p and p not in already_coded: pool.append({"source": "CyberattackAssistance", "prompt": p})

    latest = sorted((BASE / "CyberLLMInstruct/dataset_creation/final_dataset").glob("*.json"))[-1]
    with open(latest, encoding="utf-8-sig") as f:
        for item in json.load(f):
            p = item.get("instruction", "").strip()
            if p and p not in already_coded: pool.append({"source": "CyberLLMInstruct", "prompt": p})

    df = pd.read_excel(BASE / "MalwareBench/dataset/attack_prompts_filtered.xlsx")
    for v in df["prompt"].dropna():  # 過濾版完整越獄 prompt（已移除模型回答/JSON 陣列）
        p = str(v).strip()
        if p and p not in already_coded: pool.append({"source": "MalwareBench", "prompt": p})

    with open(BASE / "RMCBench/data/csv/prompt.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r.get("prompt", "").strip()
            if p and p not in already_coded: pool.append({"source": "RMCBench", "prompt": p})

    with open(BASE / "llm-attacks/data/advbench/harmful_behaviors_filtered.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r.get("goal", "").strip()
            if p and p not in already_coded: pool.append({"source": "llm-attacks", "prompt": p})

    return pool

remaining = load_all()
print(f"待編碼筆數：{len(remaining)}")

# ── 6. 讀取已完成進度（支援續跑） ────────────────────────────────
done_prompts = set()
if OUTPUT.exists():
    with open(OUTPUT, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            done_prompts.add(row["prompt"].strip())
    print(f"續跑模式：已完成 {len(done_prompts)} 筆")

# ── 7. 主迴圈（並行）──────────────────────────────────────────────
FIELDNAMES = ["id", "source", "prompt", CFA_COL, CFA_SUB, OA_COL, OA_SUB]
write_header = not OUTPUT.exists() or len(done_prompts) == 0

# 只留尚未完成的
todo = [item for item in remaining if item["prompt"] not in done_prompts]
total = len(todo)
print(f"本次要編碼：{total} 筆（並行 {WORKERS} 條）")

def work(item):
    """單筆工作：回傳寫入用的 row dict。在工作執行緒中執行。"""
    cfa, cfa_sub, oa, oa_sub = code_prompt(item["prompt"])
    return {
        "source":  item["source"],
        "prompt":  item["prompt"],
        CFA_COL:   cfa,
        CFA_SUB:   cfa_sub,
        OA_COL:    oa,
        OA_SUB:    oa_sub,
    }

done_count = len(done_prompts)
start = time.time()

with open(OUTPUT, "a", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if write_header:
        writer.writeheader()

    buffer = []
    # 主執行緒負責寫檔（不需鎖）；工作執行緒只負責呼叫 Ollama
    with ThreadPoolExecutor(max_workers=WORKERS) as pool_exec:
        futures = [pool_exec.submit(work, item) for item in todo]
        for fut in as_completed(futures):
            row = fut.result()
            done_count += 1
            row["id"] = done_count
            buffer.append(row)

            if len(buffer) >= BATCH_SAVE:
                writer.writerows(buffer)
                f.flush()
                buffer = []
                elapsed = time.time() - start
                done_now = done_count - len(done_prompts)
                rate = done_now / elapsed if elapsed > 0 else 0
                eta = (total - done_now) / rate / 60 if rate > 0 else 0
                print(f"進度：{done_now}/{total}　速度 {rate:.1f} 筆/秒　預估剩餘 {eta:.0f} 分")

    if buffer:
        writer.writerows(buffer)

elapsed = time.time() - start
print(f"\n完成！{OUTPUT}")
print(f"本次編碼 {done_count - len(done_prompts)} 筆，耗時 {elapsed/60:.1f} 分")
