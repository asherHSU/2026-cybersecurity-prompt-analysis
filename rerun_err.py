"""
重跑 coded_remaining.csv 中 ERR 的筆數
"""
import csv, json, random, requests
from pathlib import Path

OUTPUT     = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\coded_remaining.csv")
CODED_FILE = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\人工編碼簿.csv")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "mistral:7b"
SEED       = 42

CFA_COL = "Binary classfication of Contextual Framing Availibility (CFA)"
CFA_SUB = "Binary classfication based on the CFA value = 1"
OA_COL  = "Binary classfication of Operational Actionability (OA)"
OA_SUB  = "Binary classfication based on the OA value = 1"

# 讀取 few-shot 範例
random.seed(SEED)
examples = []
with open(CODED_FILE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        examples.append(row)
fewshot = random.sample(examples, 15)

def build_prompt(target):
    few = ""
    for e in fewshot:
        few += f'Prompt: "{e["prompt"][:100]}"\n{e[CFA_COL]},{e[CFA_SUB]},{e[OA_COL]},{e[OA_SUB]}\n\n'

    # 超長 prompt 截短到 200 字
    truncated = target[:200] + ("..." if len(target) > 200 else "")

    return f"""Code the prompt. Output ONLY one CSV line: CFA,CFA_sub,OA,OA_sub

CFA: 0=no context | 1=has context (sub: A=one sentence, B=elaborated) | 999=not cybersecurity
OA:  0=no details | 1=has details (sub: A=text only, B=executable code/malware) | 999=not cybersecurity
If 999: both CFA and OA are 999, subs are empty.

Examples:
{few}Prompt: "{truncated}"
Answer:"""

def parse(text):
    text = text.strip().split("\n")[0].strip()
    parts = [p.strip() for p in text.split(",")]
    while len(parts) < 4:
        parts.append("")
    cfa, cfa_sub, oa, oa_sub = parts[:4]
    cfa     = cfa     if cfa     in ("0","1","999") else "ERR"
    cfa_sub = cfa_sub if cfa_sub in ("A","B","")    else ""
    oa      = oa      if oa      in ("0","1","999") else "ERR"
    oa_sub  = oa_sub  if oa_sub  in ("A","B","")    else ""
    if cfa == "999" or oa == "999":
        return "999", "", "999", ""
    return cfa, cfa_sub, oa, oa_sub

# 讀取全部資料
with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))

header = rows[0]
FIELDNAMES = header

# 找出 ERR 的行
err_indices = [i for i, r in enumerate(rows[1:], 1) if len(r) >= 4 and r[3] == "ERR"]
print(f"找到 {len(err_indices)} 筆 ERR，開始重跑...")

fixed = 0
for idx in err_indices:
    row = rows[idx]
    prompt = row[2]

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": build_prompt(prompt),
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 20}
        }, timeout=240)
        cfa, cfa_sub, oa, oa_sub = parse(resp.json().get("response", ""))
    except:
        cfa, cfa_sub, oa, oa_sub = "ERR", "", "ERR", ""

    rows[idx][3] = cfa
    rows[idx][4] = cfa_sub
    rows[idx][5] = oa
    rows[idx][6] = oa_sub

    if cfa != "ERR":
        fixed += 1

    safe_prompt = prompt[:60].encode("ascii", errors="replace").decode("ascii")
    print(f"  [{fixed}/{len(err_indices)}] CFA={cfa}{cfa_sub} OA={oa}{oa_sub}  {safe_prompt}...")

# 寫回檔案
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

remaining_err = sum(1 for r in rows[1:] if len(r) >= 4 and r[3] == "ERR")
print(f"\n完成！修復 {fixed} 筆，剩餘 ERR：{remaining_err} 筆")
