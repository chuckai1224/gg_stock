import os
import sqlite3
import glob
import pandas as pd
from datetime import datetime

print("="*60)
print(f"檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("上週日期範圍: 2026-10-12 (一) ~ 2026-10-16 (五)")
print("="*60)

# 1. 檢查 日K資料 (crawl.py)
print("\n【1. 日K股價資料 (crawl.py / sql/stock_data.db)】")
try:
    if os.path.exists("sql/stock_data.db"):
        con = sqlite3.connect("sql/stock_data.db")
        cur = con.cursor()
        # 抽查台積電 2330, 鴻海 2317, 聯發科 2454
        for sid in ['2330', '2317', '2454']:
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{sid}'")
            if cur.fetchone():
                cur.execute(f"SELECT date, close, vol FROM '{sid}' ORDER BY date DESC LIMIT 10")
                rows = cur.fetchall()
                print(f"  股票 {sid} 最新5筆日K:")
                for r in rows[:5]:
                    print(f"    日期: {r[0]}, 收盤: {r[1]}, 成交量: {r[2]}")
            else:
                print(f"  股票 {sid} 不在 stock_data.db")
        con.close()
    else:
        print("  sql/stock_data.db 不存在！")
except Exception as e:
    print(f"  檢查 stock_data.db 失敗: {e}")

# 檢查 data/stock_data/
print("\n【1-2. data/stock_data/ CSV 檔案檢查】")
try:
    csv_sample = ["data/stock_data/2330.csv", "data/stock_data/2317.csv"]
    for cp in csv_sample:
        if os.path.exists(cp):
            df = pd.read_csv(cp)
            print(f"  {cp} 最後3筆:")
            print(df.tail(3)[['date', 'close', 'vol'] if 'date' in df.columns else df.columns[:3]])
        else:
            print(f"  {cp} 不存在")
except Exception as e:
    print(f"  檢查 CSV 失敗: {e}")

# 2. 檢查三大法人 (stock_big3.py)
print("\n【2. 三大法人資料 (stock_big3.py / sql/stock_big3.db & exchange)】")
try:
    if os.path.exists("sql/stock_big3.db"):
        con = sqlite3.connect("sql/stock_big3.db")
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"  stock_big3.db 資料表數: {len(tables)}, 範例表: {tables[:5]}")
        # 如果是按個股存
        if '2330' in tables:
            cur.execute("SELECT * FROM '2330' ORDER BY rowid DESC LIMIT 5")
            print("  2330 法人資料最新5筆:", cur.fetchall())
        con.close()
except Exception as e:
    print(f"  檢查 stock_big3.db 失敗: {e}")

try:
    if os.path.exists("sql/tse_exchange_data.db"):
        con = sqlite3.connect("sql/tse_exchange_data.db")
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"  tse_exchange_data.db 資料表數: {len(tables)}, 範例: {tables[:5]}")
        if '2330' in tables:
            cur.execute("SELECT * FROM '2330' ORDER BY date DESC LIMIT 5")
            cols = [d[0] for d in cur.description]
            print(f"  tse 2330 欄位: {cols}")
            for r in cur.fetchall():
                print("   ", r)
        con.close()
except Exception as e:
    print(f"  檢查 tse_exchange_data.db 失敗: {e}")

# 3. 檢查本益比淨值比殖利率 (pe_networth_yeild.py)
print("\n【3. 本益比淨值比殖利率 (pe_networth_yeild.py / data/down_pe_networth_yield/)】")
try:
    pe_files = sorted(glob.glob("data/down_pe_networth_yield/*.csv")) + sorted(glob.glob("data/down_pe_networth_yield/*.html"))
    print(f"  檔案數量: {len(pe_files)}")
    if pe_files:
        print(f"  最新5個檔案: {[os.path.basename(f) for f in pe_files[-5:]]}")
        # 看看有沒有 2026-10-12 ~ 2026-10-16
        for d in ['20261012', '20261013', '20261014', '20261015', '20261016']:
            matched = [f for f in pe_files if d in f]
            print(f"    {d}: {'V 有' if matched else 'X 無'}")
except Exception as e:
    print(f"  檢查 PE 失敗: {e}")

# 4. 檢查周資料：集保股權 (tdcc_get.py / sql/tdcc_dist.db)
print("\n【4. 周資料：集保股權分散表 (tdcc_get.py / sql/tdcc_dist.db)】")
try:
    if os.path.exists("sql/tdcc_dist.db"):
        con = sqlite3.connect("sql/tdcc_dist.db")
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"  tdcc_dist.db 資料表數: {len(tables)}")
        if '2330' in tables:
            cur.execute("SELECT date FROM '2330' ORDER BY date DESC LIMIT 10")
            print("  2330 最新10週集保日期:", [r[0] for r in cur.fetchall()])
        con.close()
except Exception as e:
    print(f"  檢查 tdcc_dist.db 失敗: {e}")

# 5. 檢查月資料：營收 (revenue.py / sql/income.db / data/revenue)
print("\n【5. 月資料：月營收 (revenue.py / sql/income.db & data/revenue)】")
try:
    if os.path.exists("sql/income.db"):
        con = sqlite3.connect("sql/income.db")
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"  income.db 資料表數: {len(tables)}, 範例: {tables[:5]}")
        if '2330' in tables:
            cur.execute("SELECT * FROM '2330' ORDER BY rowid DESC LIMIT 5")
            cols = [d[0] for d in cur.description]
            print(f"  income.db 2330 欄位: {cols}")
            for r in cur.fetchall():
                print("   ", r)
        con.close()
    
    rev_files = sorted(glob.glob("data/revenue/*"))
    print(f"  data/revenue/ 檔案數: {len(rev_files)}")
    if rev_files:
        print(f"  最新5個營收檔案/目錄: {[os.path.basename(f) for f in rev_files[-5:]]}")
except Exception as e:
    print(f"  檢查 revenue 失敗: {e}")

# 6. 檢查月資料：董監持股 (director.py / data/director)
print("\n【6. 月資料：董監持股 (director.py / data/director)】")
try:
    dir_files = sorted(glob.glob("data/director/*"))
    print(f"  data/director/ 檔案數: {len(dir_files)}")
    if dir_files:
        print(f"  最新5個董監檔案/目錄: {[os.path.basename(f) for f in dir_files[-5:]]}")
except Exception as e:
    print(f"  檢查 director 失敗: {e}")
