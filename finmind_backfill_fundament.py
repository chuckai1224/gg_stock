# -*- coding: utf-8 -*-
"""用 FinMind 回補個股財務基本面到 sql/stock/{id}.db。

回補項目:
  mix_income  — 季損益表(累計營收/毛利/營利/綜合損益/EPS), ys 去重
  revenue     — 月營收(含 MoM/YoY/累計YoY 自動計算), date 去重

用法:
    python finmind_backfill_fundament.py                   # 全部個股
    python finmind_backfill_fundament.py 30                # 只前 30 檔(測試)
    python finmind_backfill_fundament.py 0 12              # 全部, gap=12s
    python finmind_backfill_fundament.py 0 12 6 12         # gap=12s, min_seasons=6, min_months=12
    python finmind_backfill_fundament.py --dry-run 2330    # 印欄位對應, 不寫入
"""
import os
import sys
import time
import glob
from datetime import datetime
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.types import Date
from FinMind.data import DataLoader

os.chdir(os.path.dirname(os.path.abspath(__file__)))

STOCK_SQL_DIR = 'sql/stock'

# FinMind financial statement type → mix_income 欄位
# 同一欄有多個備用 type 時，取優先度最高（數字最小）的那一筆
FS_TYPE_PRIORITY = {
    'Revenue':                              ('營業收入',              1),
    'TotalRevenue':                         ('營業收入',              2),
    'GrossProfit':                          ('營業毛利（毛損）淨額',  1),
    'GrossProfitLoss':                      ('營業毛利（毛損）淨額',  2),
    'OperatingIncome':                      ('營業利益（損失）',      1),
    'TotalConsolidatedProfitForThePeriod':  ('本期綜合損益總額',      1),
    'TotalComprehensiveIncome':             ('本期綜合損益總額',      2),
    'ContinuingOperationsNetIncome':        ('本期綜合損益總額',      3),
    'NetIncome':                            ('本期綜合損益總額',      4),
    'EPS':                                  ('基本每股盈餘（元）',    1),
    'BasicEPS':                             ('基本每股盈餘（元）',    2),
}
EPS_COLS = {'基本每股盈餘（元）'}   # 這幾欄不除 1000

MIX_INCOME_COLS = [
    '公司代號', '公司名稱', '營業收入',
    '營業毛利（毛損）淨額', '營業利益（損失）',
    '本期綜合損益總額', '基本每股盈餘（元）', 'ys',
]

REVENUE_COLS = [
    '公司代號', '公司名稱',
    '當月營收', '上月營收', '去年當月營收',
    '上月比較增減(%)', '去年同月增減(%)',
    '當月累計營收', '去年累計營收', '前期比較增減(%)',
    '備註', 'date',
]


# ── helpers ──────────────────────────────────────────────────────────────────

def get_stock_ids():
    ids = sorted(
        os.path.basename(f)[:-3]
        for f in glob.glob('%s/*.db' % STOCK_SQL_DIR)
    )
    return [s for s in ids if len(s) == 4 and s.isdigit()]


def get_engine(stock_id):
    os.makedirs(STOCK_SQL_DIR, exist_ok=True)
    return create_engine('sqlite:///%s/%s.db' % (STOCK_SQL_DIR, stock_id), echo=False)


def existing_ys(engine, stock_id):
    """已存在的 ys 集合 (mix_income)。"""
    insp = sa_inspect(engine)
    if 'mix_income' not in insp.get_table_names():
        return set()
    with engine.connect() as con:
        df = pd.read_sql('SELECT ys FROM mix_income', con)
    return set(df['ys'].tolist())


def existing_dates(engine, stock_id):
    """已存在的 date 集合 (revenue)。"""
    insp = sa_inspect(engine)
    if 'revenue' not in insp.get_table_names():
        return set()
    with engine.connect() as con:
        df = pd.read_sql('SELECT date FROM revenue', con)
    return set(df['date'].astype(str).str[:10].tolist())


def date_to_ys(dt):
    """datetime → ys (民國年*4 + season-1)。"""
    month = dt.month
    season = (month - 1) // 3 + 1
    roc_year = dt.year - 1911
    return roc_year * 4 + season - 1


def calc_start_date(end_dt):
    """
    API start_date = 3年前的1月1日。
    確保首年 YoY 計算有完整的去年同期資料。
    """
    return datetime(end_dt.year - 3, 1, 1)


# ── mix_income ────────────────────────────────────────────────────────────────

def build_mix_income(raw, stock_id, stock_name, dry_run=False):
    """
    raw: FinMind taiwan_stock_financial_statement DataFrame
    Returns list of single-row DataFrames (one per quarter).
    """
    if dry_run:
        print('\n[dry-run] taiwan_stock_financial_statement columns:', raw.columns.tolist())
        print('[dry-run] type 值樣本:')
        print(raw[['date', 'type', 'value']].drop_duplicates('type').to_string(index=False))
        return []

    needed = set(FS_TYPE_PRIORITY.keys())
    df = raw[raw['type'].isin(needed)].copy()
    if len(df) == 0:
        return []

    df['date'] = pd.to_datetime(df['date'])
    df['ys']       = df['date'].apply(date_to_ys)
    df['col']      = df['type'].map(lambda t: FS_TYPE_PRIORITY[t][0])
    df['priority'] = df['type'].map(lambda t: FS_TYPE_PRIORITY[t][1])

    # 同季同欄有多筆時，保留優先度最高（數字最小）的一筆，避免 pivot 出現重複 index
    df = (df.sort_values('priority')
            .drop_duplicates(subset=['ys', 'col'])
            .reset_index(drop=True))

    rows = []
    for ys, grp in df.groupby('ys'):
        pivot = grp.set_index('col')['value']
        row = {'公司代號': stock_id, '公司名稱': stock_name, 'ys': ys}
        for col in MIX_INCOME_COLS[2:-1]:   # 5 財務欄位
            v = pivot.get(col, np.nan)
            if col not in EPS_COLS and pd.notna(v):
                v = float(v) / 1000         # 元 → 千元
            row[col] = v
        rows.append(pd.DataFrame([row])[MIX_INCOME_COLS])

    # FinMind EPS 是單季值，系統需要年內累計值（Q1=Q1, Q2=Q1+Q2, ...）
    # 其他財報欄位 FinMind 已是 YTD 累計，不需調整
    if rows:
        all_df = pd.concat(rows, ignore_index=True).sort_values('ys')
        eps_col = '基本每股盈餘（元）'
        cum = {}   # roc_year → 累計 EPS
        for idx in all_df.index:
            ys_val   = int(all_df.at[idx, 'ys'])
            roc_year = ys_val // 4
            q        = ys_val % 4 + 1
            eps      = all_df.at[idx, eps_col]
            if pd.notna(eps):
                if q == 1:
                    cum[roc_year] = float(eps)
                else:
                    cum[roc_year] = cum.get(roc_year, 0.0) + float(eps)
                all_df.at[idx, eps_col] = cum[roc_year]
        rows = [all_df.iloc[[i]][MIX_INCOME_COLS] for i in range(len(all_df))]

    return rows


def write_mix_income(engine, stock_id, rows, done_ys):
    written = 0
    for row_df in rows:
        ys = int(row_df.iloc[0]['ys'])
        if ys in done_ys:
            continue
        insp = sa_inspect(engine)
        with engine.connect() as con:
            if 'mix_income' in insp.get_table_names():
                row_df.to_sql('mix_income', con, if_exists='append', index=False, chunksize=10)
            else:
                row_df.to_sql('mix_income', con, if_exists='replace', index=False, chunksize=10)
        done_ys.add(ys)
        written += 1
    return written


# ── revenue ──────────────────────────────────────────────────────────────────

def build_revenue(raw, stock_id, stock_name, dry_run=False):
    """
    raw: FinMind taiwan_stock_month_revenue DataFrame
    Returns DataFrame with REVENUE_COLS, sorted oldest→newest.
    """
    if dry_run:
        print('\n[dry-run] taiwan_stock_month_revenue columns:', raw.columns.tolist())
        print('[dry-run] sample:')
        print(raw.tail(3).to_string(index=False))
        return pd.DataFrame()

    df = raw.copy()
    if 'revenue' not in df.columns and 'Revenue' in df.columns:
        df = df.rename(columns={'Revenue': 'revenue'})
    df['revenue'] = df['revenue'].astype(float) / 1000  # 元 → 千元

    # 去重：同年同月保留第一筆（FinMind 偶爾重複回傳）
    df = (df.sort_values(['revenue_year', 'revenue_month'])
            .drop_duplicates(subset=['revenue_year', 'revenue_month'])
            .reset_index(drop=True))

    df['date'] = pd.to_datetime(
        df['revenue_year'].astype(str) + '-' +
        df['revenue_month'].astype(str).str.zfill(2) + '-01'
    )

    def pct(a, b):
        if pd.isna(b) or b == 0:
            return np.nan
        return round((float(a) / float(b) - 1) * 100, 6)

    out_rows = []
    for i in range(len(df)):
        row = df.iloc[i]
        rev = float(row['revenue'])
        yr, mo = int(row['revenue_year']), int(row['revenue_month'])

        prev   = float(df.iloc[i - 1]['revenue']) if i > 0 else np.nan
        ly_m   = df[(df['revenue_year'] == yr - 1) & (df['revenue_month'] == mo)]
        ly_rev = float(ly_m.iloc[0]['revenue']) if len(ly_m) > 0 else np.nan

        cum    = float(df[(df['revenue_year'] == yr) & (df['revenue_month'] <= mo)]['revenue'].sum())
        ly_c   = df[(df['revenue_year'] == yr - 1) & (df['revenue_month'] <= mo)]
        ly_cum = float(ly_c['revenue'].sum()) if len(ly_c) > 0 else np.nan

        out_rows.append({
            '公司代號':        str(stock_id),
            '公司名稱':        stock_name,
            '當月營收':        rev,
            '上月營收':        prev,
            '去年當月營收':    ly_rev,
            '上月比較增減(%)': pct(rev, prev),
            '去年同月增減(%)': pct(rev, ly_rev),
            '當月累計營收':    cum,
            '去年累計營收':    ly_cum,
            '前期比較增減(%)': pct(cum, ly_cum),
            '備註':            '',
            'date':            row['date'],
        })

    return pd.DataFrame(out_rows)[REVENUE_COLS]


def write_revenue(engine, stock_id, df, done_dates):
    if len(df) == 0:
        return 0
    new = df[~df['date'].astype(str).str[:10].isin(done_dates)]
    if len(new) == 0:
        return 0
    insp = sa_inspect(engine)
    with engine.connect() as con:
        if_ex = 'append' if 'revenue' in insp.get_table_names() else 'replace'
        new.to_sql('revenue', con, if_exists=if_ex, index=False,
                   dtype={'date': Date()}, chunksize=50)
    return len(new)


# ── main ─────────────────────────────────────────────────────────────────────

def is_ratelimit(msg):
    m = msg.lower()
    return any(k in m for k in ('banned', 'upper limit', 'reach'))


def process_one(dl, stock_id, stock_name, start_s, end_s,
                min_seasons=8, min_months=24, dry_run=False):
    """
    min_seasons : mix_income 已有幾季以上視為完成，跳過該 API call (dry_run 時忽略)
    min_months  : revenue 已有幾個月以上視為完成，跳過該 API call (dry_run 時忽略)
    回傳 (mi_written, rev_written, mi_skip, rev_skip)
    """
    engine = get_engine(stock_id)

    if dry_run:
        # dry-run 一律呼叫 API，不做 DB 檢查
        done_ys, done_dates = set(), set()
        mi_skip = rev_skip = False
    else:
        done_ys    = existing_ys(engine, stock_id)
        done_dates = existing_dates(engine, stock_id)
        mi_skip    = len(done_ys)    >= min_seasons
        rev_skip   = len(done_dates) >= min_months

    mi_written = rev_written = 0

    # ── mix_income ──
    if not mi_skip:
        fs = dl.taiwan_stock_financial_statement(
            stock_id=stock_id, start_date=start_s, end_date=end_s)
        if fs is not None and len(fs) > 0:
            rows = build_mix_income(fs, stock_id, stock_name, dry_run=dry_run)
            if not dry_run:
                mi_written = write_mix_income(engine, stock_id, rows, done_ys)

    # ── revenue ──
    if not rev_skip:
        rv = dl.taiwan_stock_month_revenue(
            stock_id=stock_id, start_date=start_s, end_date=end_s)
        if rv is not None and len(rv) > 0:
            rev_df = build_revenue(rv, stock_id, stock_name, dry_run=dry_run)
            if not dry_run:
                rev_written = write_revenue(engine, stock_id, rev_df, done_dates)

    return mi_written, rev_written, mi_skip, rev_skip


def main():
    args = sys.argv[1:]

    # --dry-run 2330
    if args and args[0] == '--dry-run':
        stock_id = args[1] if len(args) > 1 else '2330'
        dl = DataLoader()
        end   = datetime.today()
        start = calc_start_date(end)
        start_s, end_s = start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
        try:
            info  = dl.taiwan_stock_info()
            names = dict(zip(info['stock_id'].astype(str), info['stock_name']))
        except Exception:
            names = {}
        name = names.get(stock_id, stock_id)
        print('[dry-run] stock=%s  %s ~ %s' % (stock_id, start_s, end_s))
        process_one(dl, stock_id, name, start_s, end_s, dry_run=True)
        return

    # 用法: limit  gap  min_seasons  min_months
    limit       = int(args[0])   if len(args) > 0 else 0
    gap         = float(args[1]) if len(args) > 1 else 12.0
    min_seasons = int(args[2])   if len(args) > 2 else 8
    min_months  = int(args[3])   if len(args) > 3 else 24

    end   = datetime.today()
    start = calc_start_date(end)
    start_s, end_s = start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')

    dl = DataLoader()
    try:
        info  = dl.taiwan_stock_info()
        names = dict(zip(info['stock_id'].astype(str), info['stock_name']))
    except Exception:
        names = {}

    ids = get_stock_ids()
    if limit > 0:
        ids = ids[:limit]

    print('[fundament] backfill %d stocks  %s ~ %s  gap=%.1fs  '
          'min_seasons=%d min_months=%d'
          % (len(ids), start_s, end_s, gap, min_seasons, min_months), flush=True)

    mi_total = rev_total = both_skip = fail = 0
    t0 = time.time()

    for i, sid in enumerate(ids):
        name = names.get(sid, sid)

        # 整檔預檢：兩項都已足夠 → 完全跳過
        engine       = get_engine(sid)
        done_ys_n    = len(existing_ys(engine, sid))
        done_dates_n = len(existing_dates(engine, sid))
        if done_ys_n >= min_seasons and done_dates_n >= min_months:
            both_skip += 1
            continue

        for attempt in range(4):
            try:
                mi_n, rev_n, _, _ = process_one(
                    dl, sid, name, start_s, end_s,
                    min_seasons=min_seasons, min_months=min_months)
                mi_total  += mi_n
                rev_total += rev_n
                if (i + 1) % 25 == 0:
                    print('[fundament] %d/%d %s  mix_income+=%d revenue+=%d  skip=%d'
                          % (i + 1, len(ids), sid, mi_total, rev_total, both_skip),
                          flush=True)
                break
            except Exception as e:
                m = repr(e)
                if attempt < 3:
                    wait = 3600 if is_ratelimit(m) else 60
                    print('[fundament] %s err, backoff %ds -- %s'
                          % (sid, wait, m[:70]), flush=True)
                    time.sleep(wait)
                else:
                    print('[fundament] FAIL %s %s' % (sid, m[:90]), flush=True)
                    fail += 1
        time.sleep(gap)

    elapsed = (time.time() - t0) / 60
    print('[fundament] done: mix_income=%d revenue=%d both_skip=%d fail=%d  %.0f min'
          % (mi_total, rev_total, both_skip, fail, elapsed), flush=True)


if __name__ == '__main__':
    main()
