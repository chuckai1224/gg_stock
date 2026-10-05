import sqlite3
import pandas as pd
import glob

con = sqlite3.connect('sql/stock_data.db')
df = pd.read_sql("SELECT DISTINCT date FROM [2330] WHERE date >= '2026-08-01' ORDER BY date", con)
print("Dates in sql/stock_data.db [2330] >= 2026-08-01:")
for d in df['date']:
    print(d)

tse_files = sorted(glob.glob("data/exchange/tse/2026*"))
print("\nTSE files for 2026-09 and 2026-10:")
for f in tse_files:
    if "202609" in f or "202610" in f:
        print(f)
