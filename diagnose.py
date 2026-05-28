# -*- coding: utf-8 -*-
import sqlite3, pandas as pd

today = "2026-05-23"  # Friday (last trading day before 5/25 weekend)

# Check stock_data.db
con = sqlite3.connect("sql/stock_data.db")
cnt = con.execute(f'SELECT COUNT(*) FROM "2330" WHERE date >= "{today}"').fetchone()[0]
row = con.execute(f'SELECT MAX(date) FROM "2330"').fetchone()[0]
print(f"stock_data.db  2330 最新日期: {row}, 今日資料筆數: {cnt}")
con.close()

# Check tse_exchange_data.db
con2 = sqlite3.connect("sql/tse_exchange_data.db")
tables = [t[0] for t in con2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"tse_exchange_data.db tables: {tables[-3:]}")
if tables:
    last = tables[-1]
    row2 = con2.execute(f'SELECT COUNT(*) FROM "{last}"').fetchone()[0]
    print(f"  最新日期表: {last}, {row2} 筆")
con2.close()

# Check stock_big3.db
con3 = sqlite3.connect("sql/stock_big3.db")
tables3 = [t[0] for t in con3.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"\nstock_big3.db tables: {tables3}")
if tables3:
    t3 = tables3[-1]
    r3 = con3.execute(f'SELECT MAX(date) FROM "{t3}"').fetchone()[0]
    cnt3 = con3.execute(f'SELECT COUNT(*) FROM "{t3}" WHERE date >= "{today}"').fetchone()[0]
    print(f"  {t3} 最新日期: {r3}, 今日筆數: {cnt3}")
con3.close()

# Check CSV
df = pd.read_csv("data/stock_data/2330.csv")
print(f"\n2330.csv 最新日期: {df.iloc[-1,0]}, 總行數: {len(df)}")
