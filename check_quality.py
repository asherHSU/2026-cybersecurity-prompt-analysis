import csv, sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT = r"C:\Users\simonnien\Desktop\2026詩雅poster\coded_remaining.csv"

with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))

header = rows[0]
data = rows[1:]
print(f"總筆數：{len(data)}\n")

# 1. 欄位數檢查
wrong_cols = [(i+2, r) for i, r in enumerate(data) if len(r) != 7]
print(f"[欄位數異常] {len(wrong_cols)} 筆（應為 7 欄）")
for i, r in wrong_cols[:3]:
    print(f"  row {i}: {len(r)} 欄 → {r[:4]}")

# 2. CFA 值檢查
valid_cfa = {"0", "1", "999"}
invalid_cfa = [(i+2, r[3]) for i, r in enumerate(data) if len(r) >= 4 and r[3] not in valid_cfa]
print(f"\n[CFA 值異常] {len(invalid_cfa)} 筆")
for row, val in invalid_cfa[:5]:
    print(f"  row {row}: CFA='{val}'")

# 3. OA 值檢查
valid_oa = {"0", "1", "999"}
invalid_oa = [(i+2, r[5]) for i, r in enumerate(data) if len(r) >= 6 and r[5] not in valid_oa]
print(f"\n[OA 值異常] {len(invalid_oa)} 筆")
for row, val in invalid_oa[:5]:
    print(f"  row {row}: OA='{val}'")

# 4. Sub 值一致性（CFA=1 但 sub 不是 A/B）
cfa1_bad_sub = [(i+2, r[4]) for i, r in enumerate(data)
                if len(r) >= 5 and r[3] == "1" and r[4] not in ("A", "B")]
print(f"\n[CFA=1 但 sub 異常] {len(cfa1_bad_sub)} 筆")
for row, val in cfa1_bad_sub[:5]:
    print(f"  row {row}: CFA_sub='{val}'")

oa1_bad_sub = [(i+2, r[6]) for i, r in enumerate(data)
               if len(r) >= 7 and r[5] == "1" and r[6] not in ("A", "B")]
print(f"\n[OA=1 但 sub 異常] {len(oa1_bad_sub)} 筆")
for row, val in oa1_bad_sub[:5]:
    print(f"  row {row}: OA_sub='{val}'")

# 5. CFA=0/999 但 sub 有值
cfa0_has_sub = [(i+2, r[4]) for i, r in enumerate(data)
                if len(r) >= 5 and r[3] in ("0", "999") and r[4].strip() != ""]
print(f"\n[CFA=0/999 但 sub 有值] {len(cfa0_has_sub)} 筆")
for row, val in cfa0_has_sub[:5]:
    print(f"  row {row}: CFA_sub='{val}'")

oa0_has_sub = [(i+2, r[6]) for i, r in enumerate(data)
               if len(r) >= 7 and r[5] in ("0", "999") and r[6].strip() != ""]
print(f"\n[OA=0/999 但 sub 有值] {len(oa0_has_sub)} 筆")
for row, val in oa0_has_sub[:5]:
    print(f"  row {row}: OA_sub='{val}'")

# 6. 分布統計
print(f"\n{'='*40}")
print("CFA 分布：")
cfa_counts = Counter(r[3] for r in data if len(r) >= 4)
for val, cnt in sorted(cfa_counts.items()):
    print(f"  {val}: {cnt:,} 筆 ({cnt/len(data)*100:.1f}%)")

print("\nCFA_sub 分布（僅 CFA=1）：")
sub_counts = Counter(r[4] for r in data if len(r) >= 5 and r[3] == "1")
for val, cnt in sorted(sub_counts.items()):
    label = val if val else "(空)"
    print(f"  {label}: {cnt:,} 筆")

print("\nOA 分布：")
oa_counts = Counter(r[5] for r in data if len(r) >= 6)
for val, cnt in sorted(oa_counts.items()):
    print(f"  {val}: {cnt:,} 筆 ({cnt/len(data)*100:.1f}%)")

print("\nOA_sub 分布（僅 OA=1）：")
oa_sub_counts = Counter(r[6] for r in data if len(r) >= 7 and r[5] == "1")
for val, cnt in sorted(oa_sub_counts.items()):
    label = val if val else "(空)"
    print(f"  {label}: {cnt:,} 筆")

print("\n各來源筆數：")
src_counts = Counter(r[1] for r in data if len(r) >= 2)
for src, cnt in sorted(src_counts.items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt:,}")
