import json
import random
import csv
import pandas as pd
import math
from pathlib import Path

BASE = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\datasets")
EXISTING_SAMPLE = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\sample_50_final.csv")
OUTPUT = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\sample_250_final.csv")
SEED = 99       # 不同 seed，確保抽到不同的樣本
N = 300
MIN_PER_SOURCE = 30

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

# 載入已有的 50 筆，排除重複
existing = set()
with open(EXISTING_SAMPLE, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        existing.add(row["prompt"].strip())
print(f"排除已有的 {len(existing)} 筆 prompt\n")

# 載入各資料集，排除已抽過的
pools = {}
for src, loader in loaders.items():
    all_prompts = loader()
    pools[src] = [p for p in all_prompts if p not in existing]

total = sum(len(p) for p in pools.values())
sources = list(pools.keys())

# 保底 30 則，剩餘 120 則按比例分配（最大餘數法）
floor = {src: MIN_PER_SOURCE for src in sources}
remaining = N - MIN_PER_SOURCE * len(sources)  # = 120

exact_extra = {src: len(pools[src]) / total * remaining for src in sources}
floor_extra = {src: math.floor(v) for src, v in exact_extra.items()}
leftover = remaining - sum(floor_extra.values())

by_remainder = sorted(sources, key=lambda s: exact_extra[s] - floor_extra[s], reverse=True)
extra = dict(floor_extra)
for src in by_remainder[:leftover]:
    extra[src] += 1

quotas = {src: floor[src] + extra[src] for src in sources}

# 抽樣
print(f"總資料池（排除已有）：{total:,} 筆（保底 {MIN_PER_SOURCE} 則，剩餘 {remaining} 則按比例）\n")
sample = []
for src in sources:
    q = quotas[src]
    picked = random.sample(pools[src], min(q, len(pools[src])))
    for p in picked:
        sample.append({"source": src, "prompt": p})
    pct = len(pools[src]) / total * 100
    print(f"{src}: {len(picked)} 則（保底 {MIN_PER_SOURCE} + 比例 {extra[src]}｜pool {len(pools[src]):,}，佔 {pct:.1f}%）")

random.shuffle(sample)

# 只取補抽的 250 筆（不含原本 50 筆）
sample_250 = sample[:250]

# 輸出
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "source", "prompt",
                                            "contextual_framing", "operational_actionability"])
    writer.writeheader()
    for i, item in enumerate(sample_250, 1):
        writer.writerow({"id": i, "source": item["source"], "prompt": item["prompt"],
                         "contextual_framing": "", "operational_actionability": ""})

print(f"\n完成！{OUTPUT}  共 {len(sample_250)} 筆（補抽部分，與 sample_50_final.csv 分開放）")
