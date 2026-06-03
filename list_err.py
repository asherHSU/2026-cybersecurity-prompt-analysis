import csv, sys

OUTPUT = r"C:\Users\simonnien\Desktop\2026詩雅poster\coded_remaining.csv"

sys.stdout.reconfigure(encoding="utf-8")

with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))

err_rows = [(i, r) for i, r in enumerate(rows[1:], 1) if len(r) >= 4 and r[3] == "ERR"]
print(f"ERR 筆數：{len(err_rows)}\n")
for idx, (i, r) in enumerate(err_rows):
    print(f"[{idx+1}] row={i} source={r[1]}")
    print(f"  {r[2][:250]}")
    print()
