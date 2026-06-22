# -*- coding: utf-8 -*-
"""用 MoneyDJ HTML 爬蟲自動下載個股研發費用 (RD_fee) 並寫入至 sql/stock/{id}.db，用以計算 PRR。

用法:
    python finmind_backfill_prr.py                   # 全部個股
    python finmind_backfill_prr.py 30                # 只前 30 檔(測試)
    python finmind_backfill_prr.py 0 10              # 全部, gap=10s
    python finmind_backfill_prr.py --dry-run 2330    # 印欄位對應與數據，不寫入
"""
import os
import sys
import time
import glob
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

import truststore
truststore.inject_into_ssl()

import requests
import pandas as pd
from bs4 import BeautifulSoup
import stock_comm as comm
from FinMind.data import DataLoader

os.chdir(os.path.dirname(os.path.abspath(__file__)))

STOCK_SQL_DIR = 'sql/stock'
COLS = ['stock_id', 'date', 'stock_name', '研發費用(百萬)', 'YQ']


def get_stock_ids():
    ids = sorted(
        os.path.basename(f)[:-3]
        for f in glob.glob('%s/*.db' % STOCK_SQL_DIR)
    )
    return [s for s in ids if len(s) == 4 and s.isdigit()]


def fetch_moneydj_rd_fee(stock_id, stock_name, debug=False):
    """
    爬取 MoneyDJ 綜合損益表並解析「研究發展費」。
    """
    url = 'http://5850web.moneydj.com/z/zc/zcq/zcq_%s.djhtm' % stock_id
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            if debug:
                print(f"[prr] {stock_id} HTTP 錯誤: {r.status_code}")
            return pd.DataFrame()
        
        html = r.content.decode('big5hkscs', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尋找含有「期別」的那個巨大 td
        target_td = None
        for td in soup.find_all('td'):
            if '期別' in td.text:
                target_td = td
                break
                
        if not target_td:
            if debug:
                print(f"[prr] {stock_id} 找不到包含「期別」的 td")
            return pd.DataFrame()

        # 以 \n 切分並清洗
        lines = [l.strip() for l in target_td.text.split('\n') if l.strip()]
        
        # 尋找 "期別" 起始位置
        start_idx = -1
        for idx, line in enumerate(lines):
            if '期別' in line:
                start_idx = idx
                break
                
        if start_idx == -1:
            if debug:
                print(f"[prr] {stock_id} 找不到「期別」行")
            return pd.DataFrame()
            
        # 每 9 行切分成一個項目（第一個元素是項目名稱，後面 8 個是數值）
        chunks = []
        for i in range(start_idx, len(lines), 9):
            chunks.append(lines[i:i+9])
            
        if not chunks:
            return pd.DataFrame()
            
        # 季度 chunk 是第一個
        seasons_raw = chunks[0][1:]
        
        # 尋找「研究發展費」或「研究發展費用」chunk
        fee_raw = None
        for c in chunks:
            if len(c) > 0 and ('研究發展' in c[0] or 'RDExp' in c[0]):
                fee_raw = c[1:]
                break
                
        if not fee_raw:
            if debug:
                print(f"[prr] {stock_id} 找不到「研究發展費」相關數據")
            return pd.DataFrame()
            
        rows = []
        for s_str, f_str in zip(seasons_raw, fee_raw):
            # 解析期別格式如: "2025.3Q"
            m = re.match(r'(\d{4})\.(\d)Q', s_str)
            if not m:
                continue
            year, q = m.group(1), m.group(2)
            
            # 對應財報申報月份
            q_map = {
                '1': ('-03-31', '1'),
                '2': ('-06-30', '2'),
                '3': ('-09-30', '3'),
                '4': ('-12-31', '4'),
            }
            
            suffix, q_val = q_map.get(q, ('-03-31', q))
            date_str = f"{year}{suffix}"
            date_val = pd.to_datetime(date_str)
            yq_val = f"{year}.{q_val}"
            
            # 解析費用
            try:
                val = float(f_str.replace(',', '').strip())
            except ValueError:
                val = np.nan
                
            rows.append({
                'stock_id': stock_id,
                'date': date_val,
                'stock_name': stock_name,
                '研發費用(百萬)': val,
                'YQ': yq_val
            })
            
        return pd.DataFrame(rows)
    except Exception as e:
        if debug:
            print(f"[prr] {stock_id} 發生異常: {str(e)}")
        return pd.DataFrame()


def main():
    args = sys.argv[1:]

    # --dry-run 2330
    if args and args[0] == '--dry-run':
        stock_id = args[1] if len(args) > 1 else '2330'
        print('[dry-run] 開始抓取 stock=%s 的研發費用...' % stock_id)
        out = fetch_moneydj_rd_fee(stock_id, stock_id, debug=True)
        if not out.empty:
            print('\n[dry-run] 抓取到的研發費用資料：')
            print(out[COLS].to_string(index=False))
        else:
            print('[dry-run] 撈取失敗或無資料。')
        return

    # 一般回補模式
    limit = int(args[0]) if len(args) > 0 else 0
    gap = float(args[1]) if len(args) > 1 else 6.0

    ids = get_stock_ids()
    if limit > 0:
        ids = ids[:limit]

    # 從全域資料庫取得股票名稱字典
    dl = DataLoader()
    try:
        info = dl.taiwan_stock_info()
        names = dict(zip(info['stock_id'].astype(str), info['stock_name']))
    except Exception:
        names = {}

    print('[prr] 開始回補 %d 檔個股研發費用... (間隔 %.1fs)'
          % (len(ids), gap), flush=True)

    done = fail = written = 0
    t0 = time.time()

    for i, sid in enumerate(ids):
        name = names.get(sid, sid)
        for attempt in range(3):
            try:
                out = fetch_moneydj_rd_fee(sid, name)
                if not out.empty:
                    out = out.sort_values('date').drop_duplicates('date')[COLS]
                    comm.stock_read_sql_add_df(sid, 'RD_fee', out)
                    written += len(out)
                done += 1
                if done % 25 == 0 or done == len(ids):
                    print('[prr] 進度 %d/%d (已處理=%d 失敗=%d 寫入筆數=%d)'
                          % (i + 1, len(ids), done, fail, written), flush=True)
                break
            except Exception as e:
                m = repr(e)
                if attempt < 2:
                    wait = 30
                    print('[prr] %s 錯誤，退避 %ds 後重試: %s' % (sid, wait, m[:70]), flush=True)
                    time.sleep(wait)
                else:
                    print('[prr] 失敗 %s: %s' % (sid, m[:90]), flush=True)
                    fail += 1
        time.sleep(gap)

    elapsed = (time.time() - t0) / 60
    print('[prr] 完成！耗時 %.1f 分鐘。已處理=%d 失敗=%d 寫入總筆數=%d'
          % (elapsed, done, fail, written), flush=True)


if __name__ == '__main__':
    main()
