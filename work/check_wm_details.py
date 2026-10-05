import glob
import os
import sqlite3
import pandas as pd

print("--- Checking TDCC dates in sql/tdcc_dist.db ---")
con = sqlite3.connect("sql/tdcc_dist.db")
df = pd.read_sql('SELECT DISTINCT date FROM "2330" ORDER BY date DESC LIMIT 10', con)
print("Latest TDCC dates for 2330:")
for d in df['date']:
    print(d)
con.close()

print("\n--- Checking TDCC files in csv/ or data/ ---")
print(glob.glob("csv/*tdcc*") + glob.glob("data/*tdcc*") + glob.glob("data/tdcc*/*"))

print("\n--- Checking director files/tables ---")
print("Files in data/director:")
print(glob.glob("data/director/*"))
if os.path.exists("sql/director.db"):
    con = sqlite3.connect("sql/director.db")
    print("Tables in sql/director.db:", [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
    con.close()

print("\n--- Checking revenue files ---")
print("Files in data/revenue:")
print(glob.glob("data/revenue/*"))
if os.path.exists("csv/revenue"):
    print("Files in csv/revenue:", glob.glob("csv/revenue/*")[:5])

print("\n--- Checking kline weekly/monthly ---")
print("Any week/month files:", glob.glob("*week*") + glob.glob("*month*") + glob.glob("data/*week*") + glob.glob("data/*month*"))
