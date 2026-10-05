import sqlite3
import pandas as pd
from datetime import datetime

con = sqlite3.connect('sql/stock_data.db')
df = pd.read_sql("SELECT DISTINCT substr(date, 1, 10) as dt FROM [2330] WHERE date >= '2026-09-01' ORDER BY dt", con)
db_dates = set(df['dt'])
print("Dates currently in 2330 in sql/stock_data.db:")
print(sorted(list(db_dates)))

all_dates = [
    '2026-09-01', '2026-09-02', '2026-09-03', '2026-09-04', '2026-09-07',
    '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-14',
    '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-21',
    '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-29', '2026-09-30',
    '2026-10-01', '2026-10-02'
]

missing_in_db = [d for d in all_dates if d not in db_dates]
print("\nMissing in sql/stock_data.db:")
print(missing_in_db)
