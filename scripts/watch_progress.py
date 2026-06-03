import time, csv, io
from pathlib import Path

OUTPUT = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\coded_remaining.csv")
TOTAL  = 29781

# 印一次標頭
print(f"{'時間':<10} {'完成':>7} {'進度':>7}  {'來源':<22} {'CFA':>4} {'sub':>4} {'OA':>4} {'sub':>4}  Prompt")
print("-" * 120)

last_done = 0

while True:
    if OUTPUT.exists():
        with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        done = len(rows) - 1  # 扣掉 header

        if done > last_done:
            pct = done / TOTAL * 100
            now = time.strftime("%H:%M:%S")

            # 印出新增的那幾筆
            for row in rows[last_done + 1:done + 1]:
                if len(row) >= 7 and row[0] != "id":
                    src     = row[1][:20]
                    cfa     = row[3]
                    cfa_sub = row[4]
                    oa      = row[5]
                    oa_sub  = row[6]
                    prompt  = row[2][:50]
                    print(f"{now:<10} {done:>7,} {pct:>6.1f}%  {src:<22} {cfa:>4} {cfa_sub:>4} {oa:>4} {oa_sub:>4}  {prompt}...")

            last_done = done

    time.sleep(10)
