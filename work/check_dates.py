import sqlite3
import pandas as pd
import glob
import os

print("--- Checking sql/stock_data.db ---")
try:
    con = sqlite3.connect('sql/stock_data.db')
    df = pd.read_sql("SELECT * FROM [2330] ORDER BY date DESC LIMIT 5", con)
    print("Latest 2330 in sql/stock_data.db:")
    print(df)
except Exception as e:
    print("Error stock_data.db:", e)

print("\n--- Checking data/stock_data/2330.csv ---")
if os.path.exists("data/stock_data/2330.csv"):
    df_csv = pd.read_csv("data/stock_data/2330.csv")
    print("Tail of data/stock_data/2330.csv:")
    print(df_csv.tail())

print("\n--- Checking kbar_cache/ ---")
if os.path.exists("kbar_cache"):
    files = glob.glob("kbar_cache/*")
    print(f"kbar_cache count: {len(files)}, samples: {files[:5]}")
else:
    print("kbar_cache does not exist")

print("\n--- Checking data/exchange/tse and otc ---")
tse_files = sorted(glob.glob("data/exchange/tse/*"))
print(f"tse count: {len(tse_files)}, latest 3: {tse_files[-3:] if tse_files else 'none'}")
otc_files = sorted(glob.glob("data/exchange/otc/*"))
print(f"otc count: {len(otc_files)}, latest 3: {otc_files[-3:] if otc_files else 'none'}")
