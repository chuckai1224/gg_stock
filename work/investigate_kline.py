import sqlite3
import pandas as pd
import glob
import os
from datetime import datetime, timedelta

con = sqlite3.connect('sql/stock_data.db')
cursor = con.cursor()

# Get max date across multiple stocks
for sid in ['2330', '2317', '2454', '0050']:
    try:
        r = cursor.execute(f'SELECT MIN(date), MAX(date), COUNT(*) FROM "{sid}"').fetchone()
        print(f"Stock {sid}: min={r[0]}, max={r[1]}, count={r[2]}")
    except Exception as e:
        print(f"Stock {sid}: error {e}")

# Check distinct dates in Sept & Oct 2026 in 2330
df_dates = pd.read_sql('SELECT DISTINCT date FROM "2330" WHERE date >= "2026-09-01" ORDER BY date', con)
print("\nDates in 2330 (Sept-Oct 2026):")
dates_in_db = [str(d)[:10] for d in df_dates['date']]
print(dates_in_db)

# Check TSE and OTC files
tse_files = [os.path.basename(f) for f in glob.glob("data/exchange/tse/202609*") + glob.glob("data/exchange/tse/202610*")]
otc_files = [os.path.basename(f) for f in glob.glob("data/exchange/otc/202609*") + glob.glob("data/exchange/otc/202610*")]
print("\nTSE files in data/exchange/tse (Sept/Oct):")
print(sorted(tse_files))
print("\nOTC files in data/exchange/otc (Sept/Oct):")
print(sorted(otc_files))

# Also check 2024 / 2025 just in case!
df_recent_years = pd.read_sql('SELECT DISTINCT strftime("%Y-%m", date) as ym FROM "2330" GROUP BY ym ORDER BY ym DESC LIMIT 12', con)
print("\nLatest year-months in 2330:")
print(df_recent_years['ym'].tolist())
