# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

# 1. income.db
con = sqlite3.connect('sql/income.db')
cur = con.cursor()
for m in ['202607', '202608', '202609']:
    try:
        cnt = cur.execute(f'SELECT count(*) FROM "{m}"').fetchone()[0]
        print(f'income.db 表 {m} 筆數: {cnt}')
    except Exception as e:
        print(f'income.db 表 {m} 查詢失敗: {e}')
con.close()

# 2. director
sample_files = ['data/director/final/2330.csv', 'data/director/final/2317.csv']
for f in sample_files:
    if glob.glob(f):
        df = pd.read_csv(f)
        print(f"\n{f} 最後3筆:")
        print(df.tail(3))
    else:
        print(f"\n{f} 不存在")
