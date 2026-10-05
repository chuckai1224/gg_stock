import sqlite3
import pandas as pd

con = sqlite3.connect('sql/stock_data.db')
df = pd.read_sql("SELECT * FROM [2330] WHERE date >= '2026-09-10' AND date <= '2026-09-15' ORDER BY date", con)
print(df)
