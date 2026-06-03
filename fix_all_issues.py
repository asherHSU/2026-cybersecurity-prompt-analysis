import csv, sys

sys.stdout.reconfigure(encoding="utf-8")
OUTPUT = r"C:\Users\simonnien\Desktop\2026詩雅poster\coded_remaining.csv"

with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.reader(f))

data = rows[1:]
fixed = 0

# ── 問題 1 & 2：CFA=0/999 有 sub → 清空 ─────────────────────────
for i, r in enumerate(data):
    if len(r) < 7: continue
    if r[3] in ("0", "999") and r[4].strip() != "":
        rows[i+1][4] = ""
        fixed += 1
    if r[5] in ("0", "999") and r[6].strip() != "":
        rows[i+1][6] = ""
        fixed += 1

print(f"問題 1&2（sub 不應有值）清除完成")

# ── 問題 3 & 4：CFA=1 或 OA=1 但 sub 空白 → 看 prompt 補填 ──────
# 先列出這些筆，手動判斷
need_review = []
for i, r in enumerate(data):
    if len(r) < 7: continue
    issues = []
    if r[3] == "1" and r[4].strip() == "":
        issues.append("CFA_sub空白")
    if r[5] == "1" and r[6].strip() == "":
        issues.append("OA_sub空白")
    if issues:
        need_review.append((i+2, r[1], r[3], r[4], r[5], r[6], r[2], issues))

# ── 問題 3 & 4：補填空白 sub ────────────────────────────────────
FILL_SUBS = {
    # row_number: (CFA_sub, OA_sub)  None = 不改
    848:   (None, "A"),
    1471:  ("A",  "A"),
    2403:  (None, "A"),
    2868:  (None, "A"),
    2940:  (None, "A"),
    7814:  (None, "A"),
    10309: (None, "B"),
    10511: (None, "A"),
    10696: (None, "B"),
    11101: (None, "A"),
    11142: (None, "A"),
    11242: (None, "A"),
}

# 建立 row_number → rows index 的對應（row_number 指 CSV 第幾行，1=header）
for i, r in enumerate(rows[1:], 1):
    row_num = i + 1  # 第 1 行是 header，data 從第 2 行起
    if row_num in FILL_SUBS:
        cfa_sub_new, oa_sub_new = FILL_SUBS[row_num]
        if cfa_sub_new is not None:
            rows[i][4] = cfa_sub_new
            fixed += 1
        if oa_sub_new is not None:
            rows[i][6] = oa_sub_new
            fixed += 1

# 寫回檔案
with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"共修復 {fixed} 處問題")

# 驗證
with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
    data2 = list(csv.reader(f))[1:]

err_cfa1 = sum(1 for r in data2 if len(r)>=5 and r[3]=="1" and r[4] not in ("A","B"))
err_oa1  = sum(1 for r in data2 if len(r)>=7 and r[5]=="1" and r[6] not in ("A","B"))
err_cfa0 = sum(1 for r in data2 if len(r)>=5 and r[3] in ("0","999") and r[4].strip()!="")
err_oa0  = sum(1 for r in data2 if len(r)>=7 and r[5] in ("0","999") and r[6].strip()!="")
print(f"\n驗證結果：")
print(f"  CFA=1 sub 異常：{err_cfa1}")
print(f"  OA=1  sub 異常：{err_oa1}")
print(f"  CFA=0/999 有 sub：{err_cfa0}")
print(f"  OA=0/999  有 sub：{err_oa0}")
