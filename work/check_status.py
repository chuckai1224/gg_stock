import sqlite3
import os

for db in ['tse_exchange_data.db', 'otc_exchange_data.db', 'stock_data.db']:
    path = os.path.join('sql', db)
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        print(f"=== {db} (tables: {len(tables)}) ===")
        # check table 2330 or first table
        sample_t = '2330' if '2330' in tables else (tables[0] if tables else None)
        if sample_t:
            cur.execute(f'SELECT * FROM "{sample_t}" ORDER BY ROWID DESC LIMIT 3')
            rows = cur.fetchall()
            print(f"Table {sample_t} latest rows:")
            for r in rows:
                print(" ", r)
