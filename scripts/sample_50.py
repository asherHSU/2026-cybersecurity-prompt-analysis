import json, re
import random
import csv
import pandas as pd
from pathlib import Path


BASE = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\datasets")
OUTPUT = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\sample_50.csv")
SEED = 42
N = 50

random.seed(SEED)

prompts = []  # list of dicts: {prompt, source}

# 1. CySecBench
path = BASE / "CySecBench/Dataset/Full dataset/cysecbench.csv"
with open(path, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        prompts.append({"prompt": row["Prompt"].strip(), "source": "CySecBench"})

# 2. CyberattackAssistance
path = BASE / "CyberattackAssistance/mitre_benchmark.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)
for item in data:
    p = _extract_mutated(item.get("mutated_prompt", "")).strip()
    if p:
        prompts.append({"prompt": p, "source": "CyberattackAssistance"})

# 3. CyberLLMInstruct
path = BASE / "CyberLLMInstruct/dataset_creation/final_dataset"
files = sorted(path.glob("*.json"))
latest = files[-1]
with open(latest, encoding="utf-8-sig") as f:
    data = json.load(f)
for item in data:
    p = item.get("instruction", "").strip()
    if p:
        prompts.append({"prompt": p, "source": "CyberLLMInstruct"})

# 4. MalwareBench (xlsx)
path = BASE / "MalwareBench/dataset/attack_prompts_filtered.xlsx"
df = pd.read_excel(path)
for val in df["Original Question"].dropna():
    prompts.append({"prompt": str(val).strip(), "source": "MalwareBench"})

# 5. RMCBench
path = BASE / "RMCBench/data/csv/prompt.csv"
with open(path, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        p = row.get("prompt", "").strip()
        if p:
            prompts.append({"prompt": p, "source": "RMCBench"})

# 6. llm-attacks
path = BASE / "llm-attacks/data/advbench/harmful_behaviors_filtered.csv"
with open(path, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        p = row.get("goal", "").strip()
        if p:
            prompts.append({"prompt": p, "source": "llm-attacks"})

print(f"總筆數：{len(prompts)}")

# 隨機抽樣 50 筆
sample = random.sample(prompts, N)

# 輸出 CSV
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "source", "prompt"])
    writer.writeheader()
    for i, item in enumerate(sample, 1):
        writer.writerow({"id": i, "source": item["source"], "prompt": item["prompt"]})

print(f"抽樣完成！輸出至：{OUTPUT}")
print("\n來源分布：")
from collections import Counter
c = Counter(item["source"] for item in sample)
for src, cnt in sorted(c.items()):
    print(f"  {src}: {cnt} 筆")
