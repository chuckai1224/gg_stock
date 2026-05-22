# -*- coding: utf-8 -*-
"""用 FinMind 免費版回補個股日K(近兩年)到 data/stock_data/{id}.csv。

特性:
  - 可續跑:已回補(CSV 已涵蓋起始日)的個股自動跳過
  - 分批節流:每檔之間 sleep,降低觸發 FinMind 免費版限流的機率
  - 遇錯退避:被限流時 backoff 300 秒後重試,最多 4 次
  - 適合背景執行,中途中斷後重跑會接續

用法:
    python finmind_backfill.py          # 回補 data/stock_data 既有的全部個股
    python finmind_backfill.py 30       # 只回補前 30 檔(測試用)
    python finmind_backfill.py 0 10     # 全部,每檔間隔 10 秒(更保守)
"""
import os
import sys
import time
import glob
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from FinMind.data import DataLoader

os.chdir(os.path.dirname(os.path.abspath(__file__)))
DST = 'data/stock_data'
COLS = ['date', 'vol', 'cash', 'open', 'high', 'low', 'close',
        'diff', 'Tnumber', 'stock_name']


def get_stock_ids():
    """回補對象 = data/stock_data 既有個股(crawl.py 抓過的真實上市櫃股)。"""
    ids = sorted(os.path.basename(f)[:-4] for f in glob.glob('%s/*.csv' % DST))
    return [s for s in ids if len(s) == 4 and s.isdigit()]


def already_done(stock_id, start_date):
    f = '%s/%s.csv' % (DST, stock_id)
    if not os.path.exists(f):
        return False
    try:
        d = pd.read_csv(f, usecols=['date'])
        return len(d) > 0 and str(d['date'].min())[:10] <= start_date
    except Exception:
        return False


def fetch_write(dl, stock_id, start_date, end_date, name):
    df = dl.taiwan_stock_daily(stock_id=stock_id,
                               start_date=start_date, end_date=end_date)
    if df is None or len(df) == 0:
        return 0
    out = pd.DataFrame({
        'date': df['date'],
        'vol': df['Trading_Volume'],
        'cash': df['Trading_money'],
        'open': df['open'],
        'high': df['max'],
        'low': df['min'],
        'close': df['close'],
        'diff': df['spread'],
        'Tnumber': df['Trading_turnover'],
        'stock_name': name,
    })
    out = out.sort_values('date').drop_duplicates('date')[COLS]
    out.to_csv('%s/%s.csv' % (DST, stock_id), index=False, encoding='utf-8')
    return len(out)


def main():
    os.makedirs(DST, exist_ok=True)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    gap = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
    end = datetime.today()
    start = end - relativedelta(years=2)
    start_s, end_s = start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

    dl = DataLoader()
    try:
        info = dl.taiwan_stock_info()
        names = dict(zip(info['stock_id'].astype(str), info['stock_name']))
    except Exception:
        names = {}

    ids = get_stock_ids()
    if limit > 0:
        ids = ids[:limit]
    print('[finmind] backfill %d stocks  %s ~ %s  gap=%.1fs'
          % (len(ids), start_s, end_s, gap), flush=True)

    done = skip = fail = 0
    t0 = time.time()
    for i, sid in enumerate(ids):
        if already_done(sid, start_s):
            skip += 1
            continue
        for attempt in range(4):
            try:
                n = fetch_write(dl, sid, start_s, end_s, names.get(sid, sid))
                done += 1
                if done % 25 == 0:
                    print('[finmind] %d/%d %s rows=%d (done=%d skip=%d fail=%d)'
                          % (i + 1, len(ids), sid, n, done, skip, fail),
                          flush=True)
                break
            except Exception as e:
                m = repr(e)
                is_ratelimit = any(k in m.lower() for k in ('banned', 'upper limit', 'reach'))
                if attempt < 3:
                    wait = 3600 if is_ratelimit else 60
                    print('[finmind] %s err, backoff %ds -- %s'
                          % (sid, wait, m[:70]), flush=True)
                    time.sleep(wait)
                else:
                    print('[finmind] FAIL %s %s' % (sid, m[:90]), flush=True)
                    fail += 1
        time.sleep(gap)
    print('[finmind] finished: done=%d skip=%d fail=%d, %.0f min'
          % (done, skip, fail, (time.time() - t0) / 60), flush=True)


if __name__ == '__main__':
    main()
