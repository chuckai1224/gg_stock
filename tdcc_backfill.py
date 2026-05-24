# -*- coding: utf-8 -*-
"""
tdcc_backfill.py — 補抓歷史集保股權分散表

從 https://www.tdcc.com.tw/portal/zh/smWeb/qryStock 取得歷史資料，
補寫入 sql/tdcc_dist.db（與 tdcc_get.py 同格式）。

使用方式：
    # 補抓最近 2 個月（預設）
    .\venv\Scripts\python.exe tdcc_backfill.py

    # 指定要補的日期
    .\venv\Scripts\python.exe tdcc_backfill.py 20260430 20260424

    # 補抓所有 portal 有的日期（最多 51 週）
    .\venv\Scripts\python.exe tdcc_backfill.py --all

注意：每筆約 0.3s，約 3500 檔 × 1 日期 ≈ 18 分鐘；8 個日期 ≈ 2.4 小時（建議深夜執行）。
"""
import re
import sys
import time
import sqlite3
import warnings
from datetime import datetime, timedelta

import pandas as pd
import requests
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.types import DateTime

warnings.filterwarnings('ignore')

PORTAL_URL = 'https://www.tdcc.com.tw/portal/zh/smWeb/qryStock'
DB_PATH    = 'sql/tdcc_dist.db'
SLEEP_SEC  = 0.3   # 每筆請求間隔（秒）


# ── session helpers ──────────────────────────────────────────────────────────

def new_session():
    """建立帶 JSESSIONID 的 requests.Session，並取得 CSRF token。"""
    sess = requests.Session()
    sess.verify = False
    sess.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    r = sess.get(PORTAL_URL, timeout=15)
    token = re.search(r'name="SYNCHRONIZER_TOKEN" value="([^"]+)"', r.text)
    firDate = re.search(r'name="firDate" value="([^"]+)"', r.text)
    if not token or not firDate:
        raise RuntimeError('無法解析 CSRF token，請確認網路可連到 tdcc.com.tw')
    sess._csrf_token = token.group(1)
    sess._fir_date   = firDate.group(1)
    return sess


def get_available_dates(sess):
    """從 portal 取得下拉清單中的所有可用日期（格式 YYYYMMDD），同時更新 CSRF token。"""
    r = sess.get(PORTAL_URL, timeout=15)
    # refresh token from this response (previous token is now stale)
    token = re.search(r'name="SYNCHRONIZER_TOKEN" value="([^"]+)"', r.text)
    if token:
        sess._csrf_token = token.group(1)
    firDate = re.search(r'name="firDate" value="([^"]+)"', r.text)
    if firDate:
        sess._fir_date = firDate.group(1)
    dates = re.findall(r'<option value="(\d{8})"', r.text)
    return dates   # 最新在前


# ── portal query ─────────────────────────────────────────────────────────────

def query_stock(sess, stock_no, sca_date, retries=2):
    """
    向 portal 查詢單一股票的集保分散資料。
    回傳 list[5] × 15 (level 1-15)：
        [[人數, 股數, 比例], ...]
    失敗回傳 None。
    """
    data = {
        'SYNCHRONIZER_TOKEN': sess._csrf_token,
        'SYNCHRONIZER_URI': '/portal/zh/smWeb/qryStock',
        'method': 'submit',
        'firDate': sess._fir_date,
        'scaDate': sca_date,
        'sqlMethod': 'StockNo',
        'stockNo': stock_no,
        'stockName': '',
    }
    for attempt in range(retries + 1):
        try:
            r = sess.post(PORTAL_URL, data=data, timeout=20)
            if r.status_code != 200:
                return None
            # Response has 2 tables: [0]=search form, [1]=results data
            all_tables = re.findall(r'<table[^>]*>(.*?)</table>', r.text, re.DOTALL)
            # Pick the table with 15+ rows (distribution data)
            table_content = None
            for t in all_tables:
                if t.count('<tr') >= 15:
                    table_content = t
                    break
            if not table_content:
                return None
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.DOTALL)
            result = []
            for row in rows:
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
                vals = [re.sub(r'<[^>]+>', '', c).strip().replace(',', '') for c in cells]
                if len(vals) >= 5 and vals[0].isdigit():
                    level = int(vals[0])
                    if 1 <= level <= 15:
                        try:
                            result.append([float(vals[2]), float(vals[3]), float(vals[4])])
                        except ValueError:
                            result.append([0.0, 0.0, 0.0])
            return result if len(result) == 15 else None
        except Exception:
            if attempt < retries:
                time.sleep(2)
    return None


# ── database helpers ─────────────────────────────────────────────────────────

def get_db_stocks(engine):
    """回傳 tdcc_dist.db 中已有的所有股票代碼（4碼）。"""
    insp = sa_inspect(engine)
    return [t for t in insp.get_table_names() if len(t) == 4]


def get_db_dates(engine, stock_id):
    """回傳某股票已有的日期集合（datetime 物件）。"""
    try:
        df = pd.read_sql(f'SELECT date FROM "{stock_id}"', engine, parse_dates=['date'])
        return set(df['date'].tolist())
    except Exception:
        return set()


def save_to_db(engine, stock_id, sca_date, rows):
    """將 15 列資料寫入 tdcc_dist.db（columns 0~44）。"""
    人數  = [r[0] for r in rows]
    股數  = [r[1] for r in rows]
    比例  = [r[2] for r in rows]
    data = 人數 + 股數 + 比例   # 45 columns
    date = datetime.strptime(sca_date, '%Y%m%d')
    df = pd.DataFrame([data], columns=list(range(45)), index=[date])
    dtypedict = {'date': DateTime()}
    with engine.connect() as conn:
        df.to_sql(stock_id, conn, if_exists='append', index_label='date',
                  dtype=dtypedict, chunksize=10)
        conn.commit()


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    stocks = get_db_stocks(engine)
    if not stocks:
        print('tdcc_dist.db 中沒有股票資料，請先執行 tdcc_get.py。')
        return

    print(f'DB 中共有 {len(stocks)} 檔股票')

    # 取得 portal 可用日期
    print('連線 TDCC portal，取得可用日期清單…')
    sess = new_session()
    available = get_available_dates(sess)
    print(f'Portal 提供 {len(available)} 個日期（{available[-1]} ~ {available[0]}）')

    # 決定要補哪些日期
    if '--all' in args:
        target_dates = available
    elif args:
        target_dates = [d for d in args if d.isdigit() and len(d) == 8]
        invalid = [d for d in args if d not in target_dates and d != '--all']
        if invalid:
            print(f'忽略無效參數：{invalid}')
    else:
        # 預設：最近 2 個月（約 9 週）
        cutoff = datetime.today() - timedelta(days=60)
        target_dates = [d for d in available if datetime.strptime(d, '%Y%m%d') >= cutoff]

    if not target_dates:
        print('沒有需要補抓的日期。')
        return
    print(f'目標日期：{target_dates}')

    total_saved = 0
    total_skipped = 0
    total_fail = 0
    session_req_count = 0   # 每 500 req 換一次 session

    for date_str in target_dates:
        date_dt = datetime.strptime(date_str, '%Y%m%d')
        # 只補 DB 裡已有的股票（避免查不到的新股）
        todo_stocks = []
        for sid in stocks:
            if date_dt not in get_db_dates(engine, sid):
                todo_stocks.append(sid)

        if not todo_stocks:
            print(f'{date_str}: 全部已有，略過')
            continue

        print(f'{date_str}: 需補 {len(todo_stocks)} 檔…')
        date_saved = 0
        date_fail  = 0

        for i, sid in enumerate(todo_stocks):
            # 定期更新 session（CSRF token 有效期有限）
            if session_req_count > 0 and session_req_count % 500 == 0:
                print('  更新 session…')
                sess = new_session()

            rows = query_stock(sess, sid, date_str)
            session_req_count += 1

            if rows:
                try:
                    save_to_db(engine, sid, date_str, rows)
                    date_saved += 1
                except Exception as e:
                    print(f'  存檔失敗 {sid}: {e}')
                    date_fail += 1
            else:
                date_fail += 1

            if (i + 1) % 100 == 0:
                print(f'  進度: {i+1}/{len(todo_stocks)}, 已存={date_saved}, 失敗={date_fail}')

            time.sleep(SLEEP_SEC)

        print(f'{date_str}: 完成，已存={date_saved}, 失敗={date_fail}')
        total_saved   += date_saved
        total_skipped += (len(stocks) - len(todo_stocks))
        total_fail    += date_fail

    print(f'\n全部完成。總共存入={total_saved}, 略過={total_skipped}, 失敗={total_fail}')


if __name__ == '__main__':
    main()
