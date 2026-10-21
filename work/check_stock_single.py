# -*- coding: utf-8 -*-
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

con = sqlite3.connect('sql/stock/2330.db')
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('tables in sql/stock/2330.db:', tables)
for t in tables:
    cnt = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
    cols = [d[0] for d in con.execute(f'SELECT * FROM "{t}" LIMIT 1').description]
    date_col = 'date' if 'date' in cols else (cols[0] if '日期' in cols[0] else None)
    if 'date' in cols:
        last = con.execute(f'SELECT date FROM "{t}" ORDER BY date DESC LIMIT 3').fetchall()
    elif '日期' in cols:
        last = con.execute(f'SELECT 日期 FROM "{t}" ORDER BY 日期 DESC LIMIT 3').fetchall()
    else:
        last = con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 1').fetchall()
    print(f'  table {t}: count={cnt}, cols={cols[:4]}..., last_records={last}')
con.close()
