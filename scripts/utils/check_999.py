import csv

with open(r'C:\Users\simonnien\Desktop\2026詩雅poster\人工編碼簿.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

cfa_col = 'Binary classfication of Contextual Framing Availibility (CFA)'
nines = [r for r in rows if r.get(cfa_col, '').strip() == '999']
print(f'999 筆數：{len(nines)}（佔 {len(nines)/len(rows)*100:.1f}%）')
print()
print('999 範例（前5筆）：')
for r in nines[:5]:
    print(f'  [{r["source"]}] {r["prompt"][:120]}')
    print()
