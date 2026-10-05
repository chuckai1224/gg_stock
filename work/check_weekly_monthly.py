import sqlite3
import pandas as pd
import glob
import os

print("=== 1. 集保股權分散表 (TDCC - 週資料) ===")
tdcc_db = "sql/tdcc_dist.db"
if os.path.exists(tdcc_db):
    con = sqlite3.connect(tdcc_db)
    # Check 2330 in tdcc_dist
    try:
        df = pd.read_sql('SELECT * FROM "2330" ORDER BY date DESC LIMIT 5', con)
        print("Latest TDCC for 2330 in sql/tdcc_dist.db:")
        print(df[['date', '29', 'stock_id'] if '29' in df.columns else df.columns[:5]])
    except Exception as e:
        print("Error reading 2330 from tdcc_dist.db:", e)
    
    # Check overall max date in tdcc_dist.db
    tables = [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"Total tables in tdcc_dist.db: {len(tables)}")
    if tables:
        sample_t = tables[0]
        r = con.execute(f'SELECT MAX(date) FROM "{sample_t}"').fetchone()
        print(f"Latest date in tdcc table '{sample_t}': {r[0]}")
    con.close()
else:
    print("sql/tdcc_dist.db does not exist")

print("\n=== 2. TDCC 原始檔案 ===")
tdcc_files = sorted(glob.glob("data/tdcc/*")) + sorted(glob.glob("data/*tdcc*"))
print(f"TDCC files count: {len(tdcc_files)}, latest 5:")
for f in tdcc_files[-5:]:
    print(f)

print("\n=== 3. 月營收 (Monthly Revenue - 月資料) ===")
# Check revenue table in sql/stock/2330.db
stock_db_2330 = "sql/stock/2330.db"
if os.path.exists(stock_db_2330):
    con = sqlite3.connect(stock_db_2330)
    tables = [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"Tables in sql/stock/2330.db: {tables}")
    if 'revenue' in tables:
        df_rev = pd.read_sql('SELECT * FROM revenue ORDER BY date DESC LIMIT 5', con)
        print("Latest revenue in sql/stock/2330.db:")
        print(df_rev[['date', '當月營收', '去年同月增減(%)'] if '當月營收' in df_rev.columns else df_rev])
    con.close()
else:
    print("sql/stock/2330.db does not exist")

print("\n=== 4. 月營收原始檔案 ===")
rev_files = sorted(glob.glob("data/revenue/*")) + sorted(glob.glob("data/*rev*"))
print(f"Revenue files: {len(rev_files)}, latest 5:")
for f in rev_files[-5:]:
    print(f)

print("\n=== 5. 董監事持股 (Director - 月資料) ===")
dir_files = sorted(glob.glob("data/director/*")) + sorted(glob.glob("data/*director*"))
print(f"Director files: {len(dir_files)}, latest 5:")
for f in dir_files[-5:]:
    print(f)
if os.path.exists("sql/stock/2330.db"):
    con = sqlite3.connect("sql/stock/2330.db")
    tables = [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'director' in tables:
        df_dir = pd.read_sql('SELECT * FROM director ORDER BY date DESC LIMIT 5', con)
        print("Latest director in 2330.db:")
        print(df_dir)
    con.close()
