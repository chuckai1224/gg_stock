import sqlite3

con = sqlite3.connect('sql/income.db')
tables = [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in sql/income.db (latest 10):", sorted(tables)[-10:])
con.close()
