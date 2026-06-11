# -*- coding: utf-8 -*-
"""用 FinMind 補抓上市(TWSE)月營收，寫入 sql/income.db。

免費版須逐檔查詢，~1000 檔約 20~30 分鐘。
已存在的股票自動跳過，中途中斷後重跑可續。

用法:
    python revenue_finmind_twse.py              # 補上個月
    python revenue_finmind_twse.py 20260501     # 指定月份 (取年月)
    python revenue_finmind_twse.py 20260501 2   # gap=2s (預設 1s)
"""
import os, sys, time
import truststore; truststore.inject_into_ssl()
import requests
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── 參數 ──────────────────────────────────────────────────────────────────────

if len(sys.argv) >= 2:
    target = datetime.strptime(sys.argv[1][:6], '%Y%m')
else:
    today = datetime.today()
    target = datetime(today.year, today.month, 1) - relativedelta(months=1)

gap = float(sys.argv[2]) if len(sys.argv) >= 3 else 1.0

year, month = target.year, target.month
table_name = '%d%02d' % (year, month)
print(f'Target: {year}/{month:02d}  table={table_name}  gap={gap}s')

# ── 上市股票清單（從 tse_exchange_data.db 取最新一天）────────────────────────

def get_tse_stocks():
    con = sqlite3.connect('sql/tse_exchange_data.db')
    latest = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC LIMIT 1"
    ).fetchone()[0]
    df = pd.read_sql(f'SELECT stock_id, stock_name FROM "{latest}"', con)
    con.close()
    df['stock_id'] = df['stock_id'].astype(str).str.strip()
    df = df[df['stock_id'].str.match(r'^\d{4}$')].drop_duplicates('stock_id')
    return df

# ── income.db 已存在的股票 ────────────────────────────────────────────────────

def existing_ids(table):
    try:
        con = sqlite3.connect('sql/income.db')
        df = pd.read_sql(f'SELECT "公司代號" FROM "{table}"', con)
        con.close()
        return set(df.iloc[:, 0].astype(str).str.strip().tolist())
    except Exception:
        return set()

# ── FinMind 查詢（帶重試）────────────────────────────────────────────────────

FM_URL = 'https://api.finmindtrade.com/api/v4/data'

def fetch_revenue(stock_id, start_date):
    wait = 60
    attempt = 0
    while True:
        attempt += 1
        try:
            r = requests.get(FM_URL, params={
                'dataset': 'TaiwanStockMonthRevenue',
                'data_id': stock_id,
                'start_date': start_date,
            }, timeout=30)
            d = r.json()
            if d.get('status') == 200:
                return pd.DataFrame(d['data']) if d.get('data') else pd.DataFrame()
            msg = d.get('msg', '')
            if any(k in msg.lower() for k in ('banned', 'upper limit', 'reach')):
                print(f'  rate limit (attempt {attempt}), wait {wait}s ...')
                time.sleep(wait)
                wait = min(wait * 2, 600)  # 指數退避，最長 10 分鐘
            else:
                print(f'  API error {stock_id}: {msg}')
                return pd.DataFrame()
        except Exception as e:
            print(f'  fetch error {stock_id}: {e}')
            time.sleep(5)

# ── 計算欄位 ──────────────────────────────────────────────────────────────────

def pct(a, b):
    try:
        if pd.isna(b) or float(b) == 0:
            return np.nan
        return round((float(a) / float(b) - 1) * 100, 2)
    except Exception:
        return np.nan

def build_row(stock_id, stock_name, hist, yr, mo):
    """從歷史 DataFrame 取出 yr/mo 的月營收並計算比較欄位。"""
    def rev(y, m):
        r = hist[(hist['revenue_year'] == y) & (hist['revenue_month'] == m)]
        return float(r.iloc[0]['revenue']) / 1000 if len(r) else np.nan  # 元→千元

    def cum(y, m):
        r = hist[(hist['revenue_year'] == y) & (hist['revenue_month'] <= m)]
        return float(r['revenue'].sum()) / 1000 if len(r) else np.nan

    cur  = rev(yr, mo)
    if np.isnan(cur):
        return None
    prev = rev(yr, mo - 1) if mo > 1 else rev(yr - 1, 12)
    ly   = rev(yr - 1, mo)
    cum_cur  = cum(yr, mo)
    cum_ly   = cum(yr - 1, mo)

    return {
        '公司代號':        stock_id,
        '公司名稱':        stock_name,
        '當月營收':        cur,
        '上月營收':        prev,
        '去年當月營收':    ly,
        '上月比較增減(%)': pct(cur, prev),
        '去年同月增減(%)': pct(cur, ly),
        '當月累計營收':    cum_cur,
        '去年累計營收':    cum_ly,
        '前期比較增減(%)': pct(cum_cur, cum_ly),
        '備註':            '',
    }

# ── 主流程 ────────────────────────────────────────────────────────────────────

stocks   = get_tse_stocks()
done_ids = existing_ids(table_name)
todo     = stocks[~stocks['stock_id'].isin(done_ids)].reset_index(drop=True)
print(f'TWSE stocks: {len(stocks)}  already in DB: {len(done_ids)}  to fetch: {len(todo)}')

if len(todo) == 0:
    print('Nothing to do.')
    sys.exit(0)

# 從 target 年的前一年 1 月開始，取足夠資料計算累計 YoY
start_date = '%d-01-01' % (year - 1)

engine = create_engine('sqlite:///sql/income.db', echo=False)
out_rows = []
n = len(todo)

for i, row in todo.iterrows():
    sid   = row['stock_id']
    sname = row['stock_name']
    pct_done = (i + 1) / n * 100
    print(f'[{i+1}/{n} {pct_done:.0f}%] {sid} {sname}', end=' ', flush=True)

    hist = fetch_revenue(sid, start_date)
    if len(hist) == 0:
        print('no data')
    else:
        built = build_row(sid, sname, hist, year, month)
        if built:
            out_rows.append(built)
            print(f"YoY={built['去年同月增減(%)']}")
        else:
            print(f'no {year}/{month:02d} data')

    # 每 50 筆批次寫入，避免中途中斷全丟
    if len(out_rows) >= 50:
        df_batch = pd.DataFrame(out_rows)
        with engine.connect() as con:
            df_batch.to_sql(table_name, con, if_exists='append', index=False, chunksize=200)
        print(f'  >> flushed {len(out_rows)} rows to {table_name}')
        out_rows = []

    time.sleep(gap)

# 寫入剩餘
if out_rows:
    df_batch = pd.DataFrame(out_rows)
    with engine.connect() as con:
        df_batch.to_sql(table_name, con, if_exists='append', index=False, chunksize=200)
    print(f'  >> flushed {len(out_rows)} rows to {table_name}')

# 統計
done_after = existing_ids(table_name)
print(f'\nDone. {table_name} now has {len(done_after)} rows.')
