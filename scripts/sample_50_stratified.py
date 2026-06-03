import json
import random
import csv
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\datasets")
OUTPUT = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\sample_50_stratified.csv")
SEED = 42
random.seed(SEED)

# ── 各資料集分配比例（總計 50 筆）────────────────────────────
# 可依需要自行調整數字
QUOTA = {
    "CySecBench":            15,  # 最大資料集，代表「未包裝惡意 prompt」
    "CyberLLMInstruct":      10,  # 知識性 instruction-response
    "MalwareBench":           8,  # 惡意軟體導向
    "CyberattackAssistance":  8,  # MITRE ATT&CK 框架
    "llm-attacks":            5,  # 有害行為清單
    "RMCBench":               4,  # 越獄導向
}
assert sum(QUOTA.values()) == 50, "總配額必須等於 50"

# ── 讀取各資料集 ─────────────────────────────────────────────

def load_cysecbench():
    path = BASE / "CySecBench/Dataset/Full dataset/cysecbench.csv"
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = row["Prompt"].strip()
            if p:
                rows.append(p)
    return rows

def load_cyberattack():
    path = BASE / "CyberattackAssistance/mitre_benchmark.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for item in data:
        p = (item.get("base_prompt") or "").strip()
        if p:
            rows.append(p)
    return rows

def load_cyberllm():
    path = BASE / "CyberLLMInstruct/dataset_creation/final_dataset"
    latest = sorted(path.glob("*.json"))[-1]
    with open(latest, encoding="utf-8-sig") as f:
        data = json.load(f)
    return [item["instruction"].strip() for item in data if item.get("instruction", "").strip()]

def load_malwarebench():
    path = BASE / "MalwareBench/dataset/attack_prompts.xlsx"
    df = pd.read_excel(path)
    # 用 Original Question（原始問題）而非越獄包裝後的 prompt
    return [str(v).strip() for v in df["Original Question"].dropna() if str(v).strip()]

def load_rmcbench():
    path = BASE / "RMCBench/data/csv/prompt.csv"
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = row.get("prompt", "").strip()
            if p:
                rows.append(p)
    return rows

def load_llmattacks():
    path = BASE / "llm-attacks/data/advbench/harmful_behaviors.csv"
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p = row.get("goal", "").strip()
            if p:
                rows.append(p)
    return rows

# ── 載入並抽樣 ───────────────────────────────────────────────

loaders = {
    "CySecBench":            load_cysecbench,
    "CyberLLMInstruct":      load_cyberllm,
    "MalwareBench":          load_malwarebench,
    "CyberattackAssistance": load_cyberattack,
    "llm-attacks":           load_llmattacks,
    "RMCBench":              load_rmcbench,
}

sample = []
for source, quota in QUOTA.items():
    pool = loaders[source]()
    picked = random.sample(pool, min(quota, len(pool)))
    for p in picked:
        sample.append({"source": source, "prompt": p})
    print(f"{source}: {len(picked)} / {quota} 筆（pool: {len(pool)}）")

# 打亂順序
random.shuffle(sample)

# ── 輸出 CSV ─────────────────────────────────────────────────
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "source", "prompt",
                                            "contextual_framing", "operational_actionability"])
    writer.writeheader()
    for i, item in enumerate(sample, 1):
        writer.writerow({
            "id": i,
            "source": item["source"],
            "prompt": item["prompt"],
            "contextual_framing": "",
            "operational_actionability": "",
        })

print(f"\n完成！輸出至：{OUTPUT}")
print(f"總計：{len(sample)} 筆")
