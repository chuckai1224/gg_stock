# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import glob

# 強制輸出為 UTF-8
sys.stdout.reconfigure(encoding='utf-8')

print("="*60)
print("GG_STOCK 上週與近期下載狀態深度檢查")
print("="*60)

# 1. 檢查三大法人 (stock_big3.db, tse_exchange_data.db, otc_exchange_data.db)
print("\n【檢查三大法人資料庫 table 日期】")
for db_name in ["sql/stock_big3.db", "sql/tse_exchange_data.db", "sql/otc_exchange_data.db"]:
    if os.path.exists(db_name):
        con = sqlite3.connect(db_name)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        con.close()
        # 篩選出 2026 年 10 月的表
        oct_tables = sorted([t for t in tables if t.startswith('202610') or t.startswith('tse_202610') or t.startswith('otc_202610')])
        all_2026 = sorted([t for t in tables if '2026' in t])
        latest_5 = all_2026[-5:] if all_2026 else tables[-5:]
        print(f"{db_name}:")
        print(f"  總表數: {len(tables)}, 10月份表: {oct_tables}, 最新5表: {latest_5}")

# 2. 檢查 TDCC 集保 (tdcc_dist.db) 所有日期的清單
print("\n【檢查集保股權 (tdcc_dist.db) 基準日】")
if os.path.exists("sql/tdcc_dist.db"):
    con = sqlite3.connect("sql/tdcc_dist.db")
    cur = con.cursor()
    # 查 2330 的所有日期
    cur.execute("SELECT DISTINCT date FROM '2330' ORDER BY date DESC LIMIT 10")
    dates = [str(r[0])[:10] for r in cur.fetchall()]
    print(f"  2330 最近 10 個集保週日期: {dates}")
    con.close()

# 3. 檢查月營收 (sql/income.db)
print("\n【檢查月營收 (income.db)】")
if os.path.exists("sql/income.db"):
    con = sqlite3.connect("sql/income.db")
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"  income.db 包含月份表: {sorted(tables)}")
    con.close()

# 4. 檢查董監持股 (director.py 是怎麼存的？)
print("\n【檢查董監持股】")
# 查看 director.py 邏輯或相關檔案
dir_files = glob.glob("data/director/**", recursive=True)
print(f"  data/director 檔案數量: {len(dir_files)}")
for f in dir_files[:10]:
    if os.path.isfile(f):
        print(f"    檔案: {f}")

# 5. 檢查當前本益比/殖利率 CSV
print("\n【檢查本益比/殖利率 (data/down_pe_networth_yield/)】")
pe_files = sorted(glob.glob("data/down_pe_networth_yield/*"))
oct_pe = [os.path.basename(f) for f in pe_files if "202610" in f]
print(f"  10月份 PE 檔案: {oct_pe}")

