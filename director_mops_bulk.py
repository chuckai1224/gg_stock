# -*- coding: utf-8 -*-
"""從 MOPS ajax_stapap1 逐股抓取董監持股，補 data/director/final/ 月檔。

TWSE OpenAPI t187ap11_L 更新慢時用此腳本補抓，格式與 director.down_director() 相同。
已在月檔的股票自動跳過，支援中途中斷續跑。

用法:
    python director_mops_bulk.py              # 補上個月
    python director_mops_bulk.py 20260501     # 指定月份
    python director_mops_bulk.py 20260501 8   # delay_max=8s（預設 6s）
"""
import os, sys, time, random
import truststore; truststore.inject_into_ssl()
import requests
import pandas as pd
import sqlite3
from io import StringIO
from datetime import datetime
from dateutil.relativedelta import relativedelta

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── 參數 ──────────────────────────────────────────────────────────────────────

if len(sys.argv) >= 2:
    target = datetime.strptime(sys.argv[1][:6], '%Y%m')
else:
    today = datetime.today()
    target = datetime(today.year, today.month, 1) - relativedelta(months=1)

delay_max = float(sys.argv[2]) if len(sys.argv) >= 3 else 6.0
DELAY_MIN = 4.0  # 固定下限，隨機上限由 delay_max 控制

year, month = target.year, target.month
roc_year = year - 1911
mfile = 'data/director/final/%d-%d.csv' % (roc_year, month)
print(f'Target: {year}/{month:02d}  roc={roc_year}  mfile={mfile}  '
      f'delay={DELAY_MIN:.1f}~{delay_max:.1f}s')

# ── User-Agent 池（輪替）──────────────────────────────────────────────────────

UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
]

def make_headers():
    return {
        'User-Agent': random.choice(UA_POOL),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://mopsov.twse.com.tw/mops/web/stapap1',
        'Connection': 'keep-alive',
    }

# ── Session（保持 Cookie / 連線狀態）─────────────────────────────────────────

session = requests.Session()
# 先 GET 首頁，取得初始 Cookie
try:
    session.get('https://mopsov.twse.com.tw/mops/web/stapap1',
                headers=make_headers(), timeout=15)
except Exception:
    pass

# ── 股票清單（TSE + OTC）────────────────────────────────────────────────────

def get_stocks():
    rows = []
    for db, market in [('sql/tse_exchange_data.db', 'sii'),
                       ('sql/otc_exchange_data.db', 'otc')]:
        if not os.path.exists(db):
            print(f'skip {db}: not found')
            continue
        con = sqlite3.connect(db)
        latest = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC LIMIT 1"
        ).fetchone()[0]
        df = pd.read_sql(f'SELECT stock_id, stock_name FROM "{latest}"', con)
        con.close()
        df['stock_id'] = df['stock_id'].astype(str).str.strip()
        df = df[df['stock_id'].str.match(r'^\d{4}$')].drop_duplicates('stock_id')
        df['market'] = market
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

# ── 已存在的股票 ──────────────────────────────────────────────────────────────

def existing_ids():
    if os.path.exists(mfile):
        df = pd.read_csv(mfile, dtype={'stock_id': str})
        return set(df['stock_id'].astype(str).str.strip().tolist())
    return set()

# ── 抓單股 MOPS 董監合計 ──────────────────────────────────────────────────────

MOPS_URL = 'https://mopsov.twse.com.tw/mops/web/ajax_stapap1'
MIN_BYTES = 2000

def fetch_director(stock_id, market):
    url = (f'{MOPS_URL}?TYPEK={market}&firstin=true'
           f'&year={roc_year}&month={month:02d}&off=1&co_id={stock_id}&step=0')
    for attempt in range(3):
        try:
            r = session.get(url, headers=make_headers(), timeout=30)
            if len(r.content) < MIN_BYTES:
                wait = random.uniform(5, 10) * (attempt + 1)
                time.sleep(wait)
                continue
            text = r.content.decode('utf-8', errors='replace')
            dfs = pd.read_html(StringIO(text), flavor='lxml')
            break
        except ValueError:
            return None, None
        except Exception as e:
            print(f'  fetch error (attempt {attempt+1}): {e}')
            time.sleep(random.uniform(5, 12))
    else:
        return None, None

    if len(dfs) < 5:
        return None, None

    try:
        ym_cell = str(dfs[2].iloc[0][0])
        if f'{roc_year}{month:02d}' not in ym_cell:
            print(f'  wrong month: {ym_cell}')
            return None, None
    except Exception:
        return None, None

    summary = dfs[4]
    mask = summary[0].astype(str).str.contains('全體董監持股合計', na=False)
    rows = summary[mask]
    if len(rows) == 0:
        return None, None

    try:
        total = int(str(rows.iloc[0][1]).replace(',', ''))
    except Exception:
        return None, None

    try:
        name_raw = str(dfs[0].iloc[0][0])
        sname = name_raw.replace(stock_id, '').strip()
    except Exception:
        sname = ''

    return total, sname

# ── 寫入月檔 ──────────────────────────────────────────────────────────────────

def append_to_mfile(rows):
    df_new = pd.DataFrame(rows, columns=['stock_id', 'stock_name', '全體董監持股合計'])
    os.makedirs('data/director/final', exist_ok=True)
    if os.path.exists(mfile):
        df_old = pd.read_csv(mfile, dtype={'stock_id': str})
        df_out = pd.concat([df_old, df_new], ignore_index=True)
        df_out.drop_duplicates(subset=['stock_id'], keep='last', inplace=True)
    else:
        df_out = df_new
    df_out.to_csv(mfile, encoding='utf-8', index=False)

# ── 主流程 ────────────────────────────────────────────────────────────────────

stocks   = get_stocks()
done_ids = existing_ids()
todo     = stocks[~stocks['stock_id'].isin(done_ids)].reset_index(drop=True)
print(f'Total stocks: {len(stocks)}  already done: {len(done_ids)}  to fetch: {len(todo)}')

if len(todo) == 0:
    print('Nothing to do.')
    sys.exit(0)

pending = []
n = len(todo)
flush_every = 50

for i, row in todo.iterrows():
    sid    = row['stock_id']
    market = row['market']
    pct    = (i + 1) / n * 100
    total, sname = fetch_director(sid, market)
    if total is not None:
        pending.append((sid, sname, total))
        print(f'[{i+1}/{n} {pct:.0f}%] {sid}  {total:,}', flush=True)

    if len(pending) >= flush_every:
        append_to_mfile(pending)
        print(f'  >> flushed {len(pending)} rows -> {mfile}')
        pending = []

    time.sleep(random.uniform(DELAY_MIN, delay_max))

if pending:
    append_to_mfile(pending)
    print(f'  >> flushed {len(pending)} rows -> {mfile}')

total_rows = len(existing_ids())
print(f'\nDone. {mfile} now has {total_rows} stocks.')
