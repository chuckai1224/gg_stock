import sqlite3
import pandas as pd

con = sqlite3.connect('sql/stock_data.db')
df = pd.read_sql("SELECT substr(date, 1, 7) as ym, count(*) as cnt FROM [2330] GROUP BY ym ORDER BY ym", con)
print(df)
