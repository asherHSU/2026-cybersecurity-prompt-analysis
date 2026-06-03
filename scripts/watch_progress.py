r"""
即時監控 AI 編碼進度（讀 data/coded_remaining_v2.csv）。
用法：python scripts\watch_progress.py
每 10 秒刷新一次儀表板，按 Ctrl+C 結束（不影響編碼）。
"""
import time, csv, sys, os
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT = Path(r"C:\Users\simonnien\Desktop\2026詩雅poster\data\coded_remaining_v2.csv")
TOTAL  = 29047          # 待編碼總數
REFRESH = 10            # 刷新秒數

CFA = "Binary classfication of Contextual Framing Availibility (CFA)"
OA  = "Binary classfication of Operational Actionability (OA)"

def read_rows():
    if not OUTPUT.exists():
        return []
    try:
        with open(OUTPUT, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def bar(pct, width=40):
    filled = int(pct / 100 * width)
    return "█" * filled + "·" * (width - filled)

# 監控起點（用於算即時速度）
start_time = time.time()
start_done = len(read_rows())

try:
    while True:
        rows = read_rows()
        done = len(rows)
        pct = done / TOTAL * 100 if TOTAL else 0

        elapsed = time.time() - start_time
        delta = done - start_done
        rate = delta / elapsed if elapsed > 0 else 0          # 筆/秒（監控期間）
        eta_min = (TOTAL - done) / rate / 60 if rate > 0 else 0

        err = sum(1 for r in rows if r.get(CFA, "").strip() == "ERR")
        src = Counter(r["source"] for r in rows)

        os.system("cls")
        print("=" * 64)
        print("  AI 編碼進度監控　（Ctrl+C 結束，不影響編碼）")
        print("=" * 64)
        print(f"  時間：{time.strftime('%H:%M:%S')}")
        print()
        print(f"  [{bar(pct)}] {pct:5.1f}%")
        print(f"  已完成：{done:,} / {TOTAL:,} 筆")
        if err:
            print(f"  編碼失敗(ERR)：{err:,} 筆（{err/done*100:.1f}%）" if done else "")
        print()
        if rate > 0:
            print(f"  速度：{rate:.1f} 筆/秒　預估剩餘：{eta_min:.0f} 分（約 {eta_min/60:.1f} 小時）")
        else:
            print(f"  速度：計算中…")
        print()
        print("  各來源完成數：")
        for s, n in sorted(src.items(), key=lambda x: -x[1]):
            print(f"    {s:<24} {n:>6,}")

        if done >= TOTAL:
            print("\n  ✅ 編碼完成！")
            break

        time.sleep(REFRESH)
except KeyboardInterrupt:
    print("\n（已停止監控，編碼仍在背景進行）")
