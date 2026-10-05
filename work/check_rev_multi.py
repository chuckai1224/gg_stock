import sqlite3
import pandas as pd
import glob

print("Checking revenue dates across multiple stocks:")
for sid in ['2330', '2317', '2454', '3008', '2603']:
    path = f"sql/stock/{sid}.db"
    try:
        con = sqlite3.connect(path)
        df = pd.read_sql("SELECT date, 當月營收, `去年同月增減(%)` FROM revenue ORDER BY date DESC LIMIT 3", con)
        print(f"\nStock {sid}:")
        print(df)
        con.close()
    except Exception as e:
        print(f"Error {sid}: {e}")
