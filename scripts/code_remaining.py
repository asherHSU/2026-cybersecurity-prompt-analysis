"""
用 Ollama 對剩餘 ~29,781 筆 prompt 自動編碼
- 參考 300 筆人工編碼作為 few-shot 範例
- 輸出格式與人工編碼簿一致（四欄）
"""

import csv, json, random, requests
import pandas as pd
from pathlib import Path

BASE        = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\datasets")
CODED_FILE  = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\人工編碼簿.csv")
OUTPUT      = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\coded_remaining.csv")
OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "mistral:7b"
SEED        = 42
BATCH_SAVE  = 50

CFA_COL = "Binary classfication of Contextual Framing Availibility (CFA)"
CFA_SUB = "Binary classfication based on the CFA value = 1"
OA_COL  = "Binary classfication of Operational Actionability (OA)"
OA_SUB  = "Binary classfication based on the OA value = 1"

# ── 1. 讀取人工編碼 300 筆 ────────────────────────────────────────
already_coded = set()
examples = []

with open(CODED_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        prompt = row["prompt"].strip()
        already_coded.add(prompt)
        cfa     = row.get(CFA_COL, "").strip()
        cfa_sub = row.get(CFA_SUB, "").strip()
        oa      = row.get(OA_COL,  "").strip()
        oa_sub  = row.get(OA_SUB,  "").strip()
        examples.append({
            "prompt":   prompt,
            "CFA":      cfa,
            "CFA_sub":  cfa_sub,
            "OA":       oa,
            "OA_sub":   oa_sub,
        })

print(f"人工編碼範例：{len(examples)} 筆")

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

# ── 3. 建立 prompt template ──────────────────────────────────────
def build_prompt(target_prompt):
    few = ""
    for e in fewshot:
        few += f'Prompt: "{e["prompt"][:200]}"\n'
        few += f'CFA: {e["CFA"]} | CFA_sub: {e["CFA_sub"]} | OA: {e["OA"]} | OA_sub: {e["OA_sub"]}\n\n'

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
{few}
### Now code this prompt. Reply ONLY with this exact CSV line (no header, no explanation):
CFA_value,CFA_sub,OA_value,OA_sub

Prompt: "{truncated}"
Answer:"""

# ── 4. 解析回應 ───────────────────────────────────────────────────
def parse_response(text):
    text = text.strip().split("\n")[0].strip()
    parts = [p.strip() for p in text.split(",")]
    # 補齊到 4 個欄位
    while len(parts) < 4:
        parts.append("")
    cfa, cfa_sub, oa, oa_sub = parts[:4]
    cfa     = cfa     if cfa     in ("0","1","999") else "ERR"
    cfa_sub = cfa_sub if cfa_sub in ("A","B","999","")  else ""
    oa      = oa      if oa      in ("0","1","999") else "ERR"
    oa_sub  = oa_sub  if oa_sub  in ("A","B","999","")  else ""
    # 若任一為 999，兩個都設 999，sub 留空
    if cfa == "999" or oa == "999":
        return "999", "", "999", ""
    return cfa, cfa_sub, oa, oa_sub

def code_prompt(target):
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": build_prompt(target),
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 20}
        }, timeout=180)
        return parse_response(resp.json().get("response", ""))
    except:
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
            p = (item.get("base_prompt") or "").strip()
            if p and p not in already_coded: pool.append({"source": "CyberattackAssistance", "prompt": p})

    latest = sorted((BASE / "CyberLLMInstruct/dataset_creation/final_dataset").glob("*.json"))[-1]
    with open(latest, encoding="utf-8-sig") as f:
        for item in json.load(f):
            p = item.get("instruction", "").strip()
            if p and p not in already_coded: pool.append({"source": "CyberLLMInstruct", "prompt": p})

    df = pd.read_excel(BASE / "MalwareBench/dataset/attack_prompts.xlsx")
    for v in df["prompt"].dropna():  # 改用完整的越獄包裝版 prompt
        p = str(v).strip()
        if p and p not in already_coded: pool.append({"source": "MalwareBench", "prompt": p})

    with open(BASE / "RMCBench/data/csv/prompt.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r.get("prompt", "").strip()
            if p and p not in already_coded: pool.append({"source": "RMCBench", "prompt": p})

    with open(BASE / "llm-attacks/data/advbench/harmful_behaviors.csv", encoding="utf-8") as f:
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

# ── 7. 主迴圈 ────────────────────────────────────────────────────
FIELDNAMES = ["id", "source", "prompt", CFA_COL, CFA_SUB, OA_COL, OA_SUB]
write_header = not OUTPUT.exists() or len(done_prompts) == 0

with open(OUTPUT, "a", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    if write_header:
        writer.writeheader()

    buffer = []
    done_count = len(done_prompts)
    total = len(remaining)

    for item in remaining:
        if item["prompt"] in done_prompts:
            continue

        cfa, cfa_sub, oa, oa_sub = code_prompt(item["prompt"])
        done_count += 1

        buffer.append({
            "id":      done_count,
            "source":  item["source"],
            "prompt":  item["prompt"],
            CFA_COL:   cfa,
            CFA_SUB:   cfa_sub,
            OA_COL:    oa,
            OA_SUB:    oa_sub,
        })

        if len(buffer) >= BATCH_SAVE:
            writer.writerows(buffer)
            f.flush()
            buffer = []
            print(f"進度：{done_count}/{total} 筆")

    if buffer:
        writer.writerows(buffer)

print(f"\n完成！{OUTPUT}，共 {done_count} 筆")
