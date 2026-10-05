import sqlite3

con = sqlite3.connect('sql/stock_big3.db')
tables = [t[0] for t in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() if t[0].isdigit() and len(t[0]) == 8]
print("Latest big3 dates:", sorted(tables)[-10:])
