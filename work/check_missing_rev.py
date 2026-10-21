# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

con = sqlite3.connect('sql/income.db')
cur = con.cursor()

df08 = pd.read_sql('SELECT "公司代號" FROM "202608"', con)
df09 = pd.read_sql('SELECT "公司代號" FROM "202609"', con)
con.close()

s08 = set(df08['公司代號'].astype(str).str.strip())
s09 = set(df09['公司代號'].astype(str).str.strip())

diff = sorted(list(s08 - s09))
print(f"202608 有但 202609 沒有的股票數: {len(diff)}")
print(f"前 20 檔缺少的代號: {diff[:20]}")

# 檢查 tse 和 otc 的情況
con_tse = sqlite3.connect('sql/tse_exchange_data.db')
latest_tse = con_tse.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC LIMIT 1").fetchone()[0]
df_tse = pd.read_sql(f'SELECT stock_id FROM "{latest_tse}"', con_tse)
con_tse.close()

tse_stocks = set(df_tse['stock_id'].astype(str).str.strip())
tse_missing = [s for s in diff if s in tse_stocks]
otc_missing = [s for s in diff if s not in tse_stocks]
print(f"其中屬於上市(TSE)缺少的數量: {len(tse_missing)}")
print(f"其中屬於上櫃(OTC)缺少的數量: {len(otc_missing)}")
print(f"上市缺少範例: {tse_missing[:10]}")
print(f"上櫃缺少範例: {otc_missing[:10]}")
