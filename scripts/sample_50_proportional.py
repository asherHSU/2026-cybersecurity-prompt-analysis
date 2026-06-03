import json
import random
import csv
import pandas as pd
import math
from pathlib import Path
from collections import Counter

BASE = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\datasets")
OUTPUT = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\sample_50_proportional.csv")
SEED = 42
N = 50

random.seed(SEED)



def load_cysecbench():
    path = BASE / "CySecBench/Dataset/Full dataset/cysecbench.csv"
    with open(path, encoding="utf-8") as f:
        return [r["Prompt"].strip() for r in csv.DictReader(f) if r["Prompt"].strip()]

def load_cyberattack():
    path = BASE / "CyberattackAssistance/mitre_benchmark.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [p for d in data if (p := d.get("base_prompt", "")).strip())]

def load_cyberllm():
    path = BASE / "CyberLLMInstruct/dataset_creation/final_dataset"
    latest = sorted(path.glob("*.json"))[-1]
    with open(latest, encoding="utf-8-sig") as f:
        data = json.load(f)
    return [d["instruction"].strip() for d in data if d.get("instruction", "").strip()]

def load_malwarebench():
    df = pd.read_excel(BASE / "MalwareBench/dataset/attack_prompts_filtered.xlsx")
    return [str(v).strip() for v in df["Original Question"].dropna() if str(v).strip()]

def load_rmcbench():
    path = BASE / "RMCBench/data/csv/prompt.csv"
    with open(path, encoding="utf-8") as f:
        return [r.get("prompt", "").strip() for r in csv.DictReader(f) if r.get("prompt", "").strip()]

def load_llmattacks():
    path = BASE / "llm-attacks/data/advbench/harmful_behaviors_filtered.csv"
    with open(path, encoding="utf-8") as f:
        return [r.get("goal", "").strip() for r in csv.DictReader(f) if r.get("goal", "").strip()]

loaders = {
    "CySecBench":            load_cysecbench,
    "CyberLLMInstruct":      load_cyberllm,
    "MalwareBench":          load_malwarebench,
    "CyberattackAssistance": load_cyberattack,
    "llm-attacks":           load_llmattacks,
    "RMCBench":              load_rmcbench,
}

# 載入各資料集
pools = {src: loader() for src, loader in loaders.items()}
total = sum(len(p) for p in pools.values())

# 最大餘數法（largest remainder method）確保總和精確等於 N
exact = {src: len(p) / total * N for src, p in pools.items()}
floor_quotas = {src: math.floor(v) for src, v in exact.items()}
remainder = N - sum(floor_quotas.values())

# 依餘數大小排序，補足剩餘名額
remainders = sorted(exact.keys(), key=lambda s: exact[s] - floor_quotas[s], reverse=True)
quotas = dict(floor_quotas)
for src in remainders[:remainder]:
    quotas[src] += 1

# 抽樣
sample = []
for src, quota in quotas.items():
    pool = pools[src]
    picked = random.sample(pool, min(quota, len(pool)))
    for p in picked:
        sample.append({"source": src, "prompt": p})
    pct = len(pool) / total * 100
    print(f"{src}: {len(picked)}/{quota} 筆（pool: {len(pool):,}，佔比 {pct:.1f}%）")

random.shuffle(sample)

# 輸出 CSV
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "source", "prompt",
                                            "contextual_framing", "operational_actionability"])
    writer.writeheader()
    for i, item in enumerate(sample, 1):
        writer.writerow({"id": i, "source": item["source"], "prompt": item["prompt"],
                         "contextual_framing": "", "operational_actionability": ""})

print(f"\n完成！輸出至：{OUTPUT}")
print(f"總計：{len(sample)} 筆（總資料池：{total:,}）")
