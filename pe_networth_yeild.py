# -*- coding: utf-8 -*-

import csv
import os
import sys
import time
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
import requests
from io import StringIO
from inspect import currentframe, getframeinfo
from sqlalchemy import create_engine
import inspect
import traceback
import stock_comm as comm
DEBUG=1
LOG=1
def lno():
    cf = currentframe()
    filename = getframeinfo(cf).filename
    return '%s-L(%d)'%(os.path.basename(filename),inspect.currentframe().f_back.f_lineno)
def check_dst_folder(dstpath):
    if not os.path.isdir(dstpath):
        os.makedirs(dstpath)     
  
def down_pe_networth_yield(date, dw=1, debug=1):
    """下載個股 本益比/股價淨值比/殖利率,輸出
    data/down_pe_networth_yield/{tse,otc}YYYYMMDD.csv
    欄位: stock_id, 本益比, 股價淨值比, 殖利率(%), 股利年度
    上市: TWSE BWIBBU_d(可指定日期);上櫃: TPEX 開放資料(僅最新一日)。"""
    dst_folder = 'data/down_pe_networth_yield'
    check_dst_folder(dst_folder)
    headers = {'User-Agent': 'Mozilla/5.0'}
    ymd = date.strftime('%Y%m%d')

    def _save(df, ofile):
        d = df.copy()
        d['stock_id'] = d['stock_id'].astype(str).str.strip()
        for c in ('本益比', '股價淨值比', '殖利率(%)'):
            d[c] = pd.to_numeric(d[c].astype(str).str.replace(',', '', regex=False),
                                 errors='coerce')
        d = d[['stock_id', '本益比', '股價淨值比', '殖利率(%)', '股利年度']]
        d.to_csv(ofile, encoding='utf-8', index=False)
        print(lno(), 'saved', ofile, len(d))

    # 上市 TSE
    tse_file = '%s/tse%s.csv' % (dst_folder, ymd)
    if dw == 1 or not os.path.exists(tse_file):
        url = ('https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d'
               '?date=%s&selectType=ALL&response=json' % ymd)
        try:
            js = requests.get(url, headers=headers, timeout=30).json()
        except Exception as e:
            print(lno(), 'tse pe request fail', e)
            js = {}
        if js.get('stat') == 'OK' and js.get('data'):
            df = pd.DataFrame(js['data'], columns=js['fields'])
            df = df.rename(columns={'證券代號': 'stock_id'})
            _save(df, tse_file)
        else:
            print(lno(), 'no tse pe data', ymd)

    # 上櫃 OTC(TPEX 開放資料,僅最新一日)
    otc_file = '%s/otc%s.csv' % (dst_folder, ymd)
    if dw == 1 or not os.path.exists(otc_file):
        url = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis'
        try:
            arr = requests.get(url, headers=headers, timeout=30).json()
        except Exception as e:
            print(lno(), 'otc pe request fail', e)
            arr = []
        if arr:
            df = pd.DataFrame(arr)
            df = df.rename(columns={'SecuritiesCompanyCode': 'stock_id',
                                    'PriceEarningRatio': '本益比',
                                    'PriceBookRatio': '股價淨值比',
                                    'YieldRatio': '殖利率(%)'})
            df['股利年度'] = np.nan
            _save(df, otc_file)
        else:
            print(lno(), 'no otc pe data')


if __name__ == '__main__':

    if len(sys.argv)==1:
        now_date=datetime.today().date()
        
        down_pe_networth_yield(now_date) #new
        #down_tse_monthly_report(int(startdate.year),int(startdate.month)-1)
        #down_otc_monthly_report(int(startdate.year),int(startdate.month)-1)
        
    elif sys.argv[1]=='-d' :
        #print (lno(),len(sys.argv))
        
        startdate=datetime.strptime(sys.argv[2],'%Y%m%d')
        try:
            enddate=datetime.strptime(sys.argv[3],'%Y%m%d')
        except:
            enddate=startdate    
        now_date = startdate 
        while   now_date<=enddate :
            down_pe_networth_yield(now_date,dw=1) #new
            now_date = now_date + relativedelta(days=1)
   
        
    else:
        print (lno(),"unsport ")
        sys.exit()
    
    