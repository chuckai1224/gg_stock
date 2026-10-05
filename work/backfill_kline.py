# -*- coding: utf-8 -*-
"""
日K線資料自動補足工具 (支援指定日期區間或單日)
用法範例：
    .\venv\Scripts\python.exe work/backfill_kline.py 2026-09-01 2026-10-02
    .\venv\Scripts\python.exe work/backfill_kline.py 2026-10-02
"""
import os
import sys
import time
from datetime import datetime, timedelta

# 確保在專案目錄下執行
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.abspath('.'))

import stock_comm as comm
from crawl import Crawler

def backfill_date(d: datetime, crawler: Crawler):
    date_str = d.strftime('%Y-%m-%d')
    date_tuple = (d.year, d.month, d.day)
    print(f"[{date_str}] 開始抓取證交所(TSE)與櫃買中心(OTC)行情...")
    
    # 1. 爬取 TSE / OTC
    crawler.get_data(date_tuple)
    
    # 檢查該日是否休市（若 TSE 檔案不存在或為空則跳過後續入庫）
    tse_file = f"data/exchange/tse/{d.strftime('%Y%m%d')}"
    if not os.path.exists(tse_file):
        print(f"[{date_str}] 無交易資料 (休市或假日)，跳過入庫。")
        return
        
    # 2. 轉存至交易所資料庫 (sql/tse_exchange_data.db & sql/otc_exchange_data.db)
    print(f"[{date_str}] 寫入交易所資料庫 (exchange2sql)...")
    comm.exchange2sql(d, d)
    
    # 3. 轉存至個股日K資料庫 (sql/stock_data.db)
    print(f"[{date_str}] 寫入個股日K資料庫 (insert_daily_stock_data)...")
    comm.insert_daily_stock_data(d)
    
    # 4. 抓取類股指數 (選用)
    try:
        crawler.get_stocks_index(date_tuple)
    except Exception:
        pass
    print(f"[{date_str}] 完成！\n")

def main():
    if len(sys.argv) == 1:
        # 預設補最近 5 個工作日
        end_date = datetime.today()
        start_date = end_date - timedelta(days=5)
    elif len(sys.argv) == 2:
        start_date = datetime.strptime(sys.argv[1].replace('/', '-'), '%Y-%m-%d')
        end_date = start_date
    elif len(sys.argv) >= 3:
        start_date = datetime.strptime(sys.argv[1].replace('/', '-'), '%Y-%m-%d')
        end_date = datetime.strptime(sys.argv[2].replace('/', '-'), '%Y-%m-%d')

    print(f"=== 執行日K回補區間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ===")
    crawler = Crawler()
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5:  # 週一至週五
            backfill_date(curr, crawler)
            time.sleep(2)
        else:
            print(f"[{curr.strftime('%Y-%m-%d')}] 週六/週日休市，跳過。")
        curr += timedelta(days=1)

if __name__ == '__main__':
    main()
