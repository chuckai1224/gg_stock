import os
import sys
import subprocess
import threading
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from flask import Flask, render_template, redirect, url_for, jsonify, request, send_from_directory
from werkzeug.utils import safe_join
import sqlite3
import stock_comm as comm
import kline as kline_tool
import stock_big3
import director

app = Flask(__name__)

# Task state
task_process = None
task_log_path = "log/execution.log"
task_status = "idle"  # idle, running, completed, failed
_task_lock = threading.Lock()

def ensure_log_dir():
    if not os.path.exists("log"):
        os.makedirs("log")

def run_subprocess_thread(cmd, log_file):
    global task_process, task_status
    try:
        # 強制子進程使用 UTF-8 編碼輸出
        import os
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        
        task_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            shell=True,
            env=env
        )
        task_process.wait()
        with _task_lock:
            if task_status == "running":
                task_status = "completed" if task_process.returncode == 0 else "failed"
    except Exception as e:
        log_file.write(f"\n[Execution error: {str(e)}]\n")
        log_file.flush()
        with _task_lock:
            if task_status == "running":
                task_status = "failed"
    finally:
        log_file.close()

@app.route('/')
def index():
    return redirect(url_for('online'))

@app.route('/online/')
def online():
    return render_template('online.html')

@app.route('/online/top')
def top():
    return render_template('top.html')

@app.route('/online/kline')
def kline():
    return render_template('kline.html')

@app.route('/online/stock_detail')
def stock_detail():
    stock_id = request.args.get('stock_id', '').strip()
    if not stock_id:
        return "請提供股票代號", 400

    # 1. 檢查是否存在於日K資料庫
    db_path = "sql/stock_data.db"
    if not os.path.exists(db_path):
        return "股價資料庫不存在，請先執行爬蟲或下載快照資料", 400

    # 為了防護，先查詢表格是否存在
    con = sqlite3.connect(db_path)
    try:
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (stock_id,)).fetchall()
        if not tables:
            con.close()
            return f"找不到股票代號 {stock_id}，請確認是否已爬取該股日K線", 400
            
        # 找出最大日期
        row = con.execute(f'SELECT MAX(date) FROM "{stock_id}"').fetchone()
        latest_date_str = row[0] if row else None
        con.close()
    except Exception as e:
        con.close()
        return f"讀取股價資料庫時出錯: {str(e)}", 500

    if not latest_date_str:
        return f"股票代號 {stock_id} 查無資料", 400

    base_date = datetime.strptime(latest_date_str[:10], '%Y-%m-%d')

    # 2. 獲取日K與週K資料
    try:
        df1 = comm.get_stock_df_bydate_nums(stock_id, 300, base_date)
        if df1.empty:
            return f"無法讀取股票 {stock_id} 的K線資料", 400
            
        # 複製並轉換 vol (日K取最近60天)
        day_df = df1.tail(60).reset_index(drop=True).copy()
        day_df['vol'] = day_df['vol'] / 1000  # 轉為張數

        # 週K取最近60週
        df_for_week = df1.copy()
        df_for_week['vol'] = df_for_week['vol'] / 1000
        week_df = kline_tool.resample(df_for_week, 'W-FRI', 60).reset_index(drop=True).copy()
        
        # 轉換日期字串格式
        def format_date_str(x):
            if hasattr(x, 'strftime'):
                return x.strftime('%Y-%m-%d')
            return str(x)[:10]

        day_dates = [format_date_str(d) for d in day_df['date'].values]
        day_open = [float(v) if pd.notna(v) else None for v in day_df['open'].values]
        day_high = [float(v) if pd.notna(v) else None for v in day_df['high'].values]
        day_low = [float(v) if pd.notna(v) else None for v in day_df['low'].values]
        day_close = [float(v) if pd.notna(v) else None for v in day_df['close'].values]
        day_vol = [float(v) if pd.notna(v) else None for v in day_df['vol'].values]

        # 週K
        week_dates = [format_date_str(d) for d in week_df['date'].values]
        week_open = [float(v) if pd.notna(v) else None for v in week_df['open'].values]
        week_high = [float(v) if pd.notna(v) else None for v in week_df['high'].values]
        week_low = [float(v) if pd.notna(v) else None for v in week_df['low'].values]
        week_close = [float(v) if pd.notna(v) else None for v in week_df['close'].values]
        week_vol = [float(v) if pd.notna(v) else None for v in week_df['vol'].values]
        
        try:
            csv_path = f"data/stock_data/{stock_id}.csv"
            if os.path.exists(csv_path):
                temp_df = pd.read_csv(csv_path, nrows=2, header=None)
                if len(temp_df) > 1:
                    stock_name = str(temp_df.iloc[1].values[-1]).strip()
                else:
                    stock_name = str(temp_df.iloc[0].values[-1]).strip()
            else:
                stock_name = stock_id
        except:
            stock_name = stock_id
    except Exception as e:
        return f"處理K線數據時發生錯誤: {str(e)}", 500

    # 3. 獲取集保大戶散戶比 (tdcc)
    class FakeRow:
        def __init__(self, s_id):
            self.stock_id = s_id
    r_obj = FakeRow(stock_id)

    chip_dates = []
    big_holders = []
    small_holders = []
    try:
        tdcc_df = comm.get_stock_tdcc_dist_df(r_obj)
        if not tdcc_df.empty:
            cols = ['15','16','17','18','19','20','21','22','23','24','25','26','27','28','29']
            s_cols = ['15','16','17','18','19','20','21','22','23','24','25']
            tdcc_sub = tdcc_df.tail(24).copy()
            for i in range(len(tdcc_sub)):
                row_data = tdcc_sub.iloc[i]
                total_stock = sum([float(row_data[c]) for c in cols if pd.notna(row_data[c])])
                if total_stock > 0:
                    b_val = float(row_data['29']) / total_stock * 100 if pd.notna(row_data['29']) else 0.0
                    s_val = sum([float(row_data[c]) for c in s_cols if pd.notna(row_data[c])]) / total_stock * 100
                    chip_dates.append(format_date_str(row_data['date']))
                    big_holders.append(round(b_val, 2))
                    small_holders.append(round(s_val, 2))
    except Exception as e:
        print(f"Warn: failed to load TDCC dist for {stock_id}: {str(e)}")

    # 4. 三大法人買賣超 (最近60日)
    inst_dates = []
    inst_foreign = []
    inst_it = []
    inst_prop = []
    try:
        market = 'tse'
        tse_conn = sqlite3.connect("sql/tse_exchange_data.db")
        tse_tables = tse_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tse_list'").fetchall()
        if tse_tables:
            tse_list = tse_conn.execute("SELECT stock_id FROM tse_list WHERE stock_id=?", (stock_id,)).fetchone()
            if not tse_list:
                market = 'otc'
        tse_conn.close()
        
        stock_3big_df = stock_big3.get_stock_3big(stock_id, base_date, 60, market)
        if not stock_3big_df.empty:
            stock_3big_df = stock_3big_df.iloc[::-1]
            for i in range(len(stock_3big_df)):
                row_data = stock_3big_df.iloc[i]
                inst_dates.append(format_date_str(row_data['日期']))
                inst_foreign.append(round(float(row_data['外資']), 1) if pd.notna(row_data['外資']) else 0.0)
                inst_it.append(round(float(row_data['投信']), 1) if pd.notna(row_data['投信']) else 0.0)
                inst_prop.append(round(float(row_data['自營商']), 1) if pd.notna(row_data['自營商']) else 0.0)
    except Exception as e:
        print(f"Warn: failed to load Big 3 for {stock_id}: {str(e)}")

    # 5. 財務季報三率走勢、單季營收、單季 EPS (最近8季)
    finance_quarters = []
    finance_eps = []
    finance_gross = []
    finance_operating = []
    finance_net = []
    finance_revenue = []
    try:
        season_df = comm.get_stock_season_df(r_obj)
        if not season_df.empty:
            season_sub = season_df.head(8).iloc[::-1]
            for i in range(len(season_sub)):
                row_data = season_sub.iloc[i]
                yr = int(row_data['ys'] // 4) + 1911
                sea = int(row_data['ys'] % 4) + 1
                q_str = f"{yr}Q{sea}"
                finance_quarters.append(q_str)
                finance_eps.append(round(float(row_data['單季EPS']), 2) if pd.notna(row_data['單季EPS']) else 0.0)
                
                def py_calc_ratio(num, den):
                    if pd.isna(num) or pd.isna(den) or den == 0:
                        return 0.0
                    return round((float(num) / float(den)) * 100, 2)
                    
                rev = row_data['單季營收']
                finance_gross.append(py_calc_ratio(row_data['單季毛利淨額'], rev))
                finance_operating.append(py_calc_ratio(row_data['單季營業利益淨額'], rev))
                finance_net.append(py_calc_ratio(row_data['單季綜合損益總額'], rev))
                finance_revenue.append(round(float(row_data['單季營收']) / 1000, 1) if pd.notna(row_data['單季營收']) else 0.0)
    except Exception as e:
        print(f"Warn: failed to load fundamental metrics for {stock_id}: {str(e)}")

    # 6. 近一年月營收與年增率 (YoY) (最近12個月)
    monthly_revenue_months = []
    monthly_revenue_values = []
    monthly_revenue_yoy = []
    try:
        rev_df = comm.get_stock_revenue_df(r_obj)
        if not rev_df.empty:
            rev_sub = rev_df.head(12).iloc[::-1]
            for i in range(len(rev_sub)):
                row_data = rev_sub.iloc[i]
                try:
                    dt = pd.to_datetime(row_data['date'])
                    yymm = dt.strftime('%y-%m')
                except:
                    yymm = str(row_data['date'])[:7]
                monthly_revenue_months.append(yymm)
                monthly_revenue_values.append(round(float(row_data['當月營收']) / 1000, 1) if pd.notna(row_data['當月營收']) else 0.0)
                monthly_revenue_yoy.append(round(float(row_data['去年同月增減(%)']), 1) if pd.notna(row_data['去年同月增減(%)']) else 0.0)
    except Exception as e:
        print(f"Warn: failed to load monthly revenue for {stock_id}: {str(e)}")
    # 嘗試從 final/ 下的 CSV 尋找當前 stock_id 的基本面數據 (總分, 本益比 等)
    score_val = None
    pe_val = None
    rev_yoy_val = None
    foreign_val = None
    it_val = None
    large_month_val = None
    large_week_val = None
    retail_month_val = None

    import glob
    csv_files = glob.glob("final/*_good*.csv")
    if csv_files:
        csv_files.sort(key=os.path.getmtime, reverse=True)
        for cf in csv_files:
            try:
                tmp_df = pd.read_csv(cf, dtype={'stock_id': str})
                row_match = tmp_df[tmp_df['stock_id'] == stock_id]
                if not row_match.empty:
                    r_match = row_match.iloc[0]
                    score_val = float(r_match['總分']) if '總分' in r_match and pd.notna(r_match['總分']) else None
                    pe_val = float(r_match['本益比']) if '本益比' in r_match and pd.notna(r_match['本益比']) else None
                    rev_yoy_val = float(r_match['最新單月營收年增率']) if '最新單月營收年增率' in r_match and pd.notna(r_match['最新單月營收年增率']) else None
                    foreign_val = float(r_match['外資增減']) if '外資增減' in r_match and pd.notna(r_match['外資增減']) else None
                    it_val = float(r_match['投信增減']) if '投信增減' in r_match and pd.notna(r_match['投信增減']) else None
                    large_month_val = float(r_match['大戶近一月增加比']) if '大戶近一月增加比' in r_match and pd.notna(r_match['大戶近一月增加比']) else None
                    large_week_val = float(r_match['大戶近一周增加比']) if '大戶近一周增加比' in r_match and pd.notna(r_match['大戶近一周增加比']) else None
                    retail_month_val = float(r_match['散戶近一月增加比']) if '散戶近一月增加比' in r_match and pd.notna(r_match['散戶近一月增加比']) else None
                    break
            except Exception as e:
                print(f"Error reading {cf}: {str(e)}")

    # 彙整為 dictionary
    stock_data = {
        "stock_id": stock_id,
        "stock_name": stock_name,
        "market": market.upper() if 'market' in locals() else 'TSE',
        "dayDates": day_dates,
        "dayOpen": day_open,
        "dayHigh": day_high,
        "dayLow": day_low,
        "dayClose": day_close,
        "dayVol": day_vol,
        "weekDates": week_dates,
        "weekOpen": week_open,
        "weekHigh": week_high,
        "weekLow": week_low,
        "weekClose": week_close,
        "weekVol": week_vol,
        "chipDates": chip_dates,
        "bigHolders": big_holders,
        "smallHolders": small_holders,
        "instDates": inst_dates,
        "foreign": inst_foreign,
        "it": inst_it,
        "prop": inst_prop,
        "financeQuarters": finance_quarters,
        "financeEps": finance_eps,
        "financeGross": finance_gross,
        "financeOperating": finance_operating,
        "financeNet": finance_net,
        "financeRevenue": finance_revenue,
        "monthlyRevenueMonths": monthly_revenue_months,
        "monthlyRevenueValues": monthly_revenue_values,
        "monthlyRevenueYoy": monthly_revenue_yoy,
        
        # 8 Core metrics (scalar value for details bar)
        "score": score_val,
        "pe": pe_val,
        "revYoy": rev_yoy_val if rev_yoy_val is not None else (monthly_revenue_yoy[-1] if monthly_revenue_yoy else None),
        "foreign_val": foreign_val if foreign_val is not None else (inst_foreign[-1] if inst_foreign else None),
        "it_val": it_val if it_val is not None else (inst_it[-1] if inst_it else None),
        "largeMonth": large_month_val,
        "largeWeek": large_week_val,
        "retailMonth": retail_month_val
    }

    return render_template('stock_detail.html', stock_data=stock_data)

@app.route('/online/run', methods=['POST'])
def run_task():
    global task_status
    with _task_lock:
        if task_status == "running":
            return jsonify({"success": False, "message": "A task is already running."})
        task_status = "running"
    
    data = request.get_json() or {}
    action = data.get("action")
    date_str = data.get("date", "20260522")
    mode_str = data.get("mode", "gg")
    
    ensure_log_dir()
    try:
        log_file = open(task_log_path, "w", encoding="utf-8")
    except Exception as e:
        with _task_lock:
            task_status = "idle"
        return jsonify({"success": False, "message": f"Failed to open log file: {str(e)}"})
    
    if action == "picker":
        log_file.write(f"[System] Starting Stock Picker (gg_stock.py {mode_str} {date_str})...\n")
        log_file.flush()
        cmd = f'"{sys.executable}" gg_stock.py {mode_str} {date_str}'
    elif action == "snapshot":
        log_file.write("[System] Starting Database Snapshot Download...\n")
        log_file.flush()
        cmd = f'"{sys.executable}" download_snapshot.py'
    elif action == "crawl":
        if date_str and len(date_str) == 8 and date_str.isdigit():
            y = date_str[0:4]
            m = str(int(date_str[4:6]))
            d = str(int(date_str[6:8]))
            log_file.write(f"[System] Starting Live Crawler for {y}-{m.zfill(2)}-{d.zfill(2)}...\n")
            log_file.flush()
            cmd = f'"{sys.executable}" crawl.py {y} {m} {d}'
        else:
            log_file.write("[System] Starting Live Crawler for today...\n")
            log_file.flush()
            cmd = f'"{sys.executable}" crawl.py'
    elif action == "big3":
        if date_str and len(date_str) == 8 and date_str.isdigit():
            log_file.write(f"[System] Starting Three Institutional Investors Crawler for {date_str}...\n")
            log_file.flush()
            cmd = f'"{sys.executable}" stock_big3.py -d {date_str} {date_str}'
        else:
            log_file.write("[System] Starting Three Institutional Investors Crawler for today...\n")
            log_file.flush()
            cmd = f'"{sys.executable}" stock_big3.py'
    elif action == "pe":
        if date_str and len(date_str) == 8 and date_str.isdigit():
            log_file.write(f"[System] Starting PE/NetWorth/Yield Crawler for {date_str}...\n")
            log_file.flush()
            cmd = f'"{sys.executable}" pe_networth_yeild.py -d {date_str} {date_str}'
        else:
            log_file.write("[System] Starting PE/NetWorth/Yield Crawler for today...\n")
            log_file.flush()
            cmd = f'"{sys.executable}" pe_networth_yeild.py'
    elif action == "tdcc":
        log_file.write("[System] Starting TDCC (集保股權) Crawler...\n")
        log_file.flush()
        cmd = f'"{sys.executable}" tdcc_get.py'
    elif action == "revenue":
        log_file.write("[System] Starting Monthly Revenue Crawler...\n")
        log_file.flush()
        cmd = f'"{sys.executable}" revenue.py'
    elif action == "director":
        log_file.write("[System] Starting Directors Shareholding Crawler...\n")
        log_file.flush()
        cmd = f'"{sys.executable}" director.py'
    elif action == "eps":
        roc_year = int(date_str[:4]) - 1911 if (date_str and len(date_str) >= 4 and date_str[:4].isdigit()) else 115
        season = (int(date_str[4:6]) - 1) // 3 + 1 if (date_str and len(date_str) == 8 and date_str.isdigit()) else 1
        log_file.write(f"[System] Starting Quarterly EPS Crawler (ROC {roc_year} Q{season})...\n")
        log_file.flush()
        cmd = f'"{sys.executable}" eps.py {roc_year} {season}'
    else:
        log_file.close()
        with _task_lock:
            task_status = "idle"
        return jsonify({"success": False, "message": "Unknown action."})
    
    thread = threading.Thread(target=run_subprocess_thread, args=(cmd, log_file))
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True, "message": "Task started."})

@app.route('/online/status')
def get_task_status():
    global task_status
    return jsonify({"status": task_status})

@app.route('/online/log')
def get_task_log():
    if os.path.exists(task_log_path):
        try:
            # 加上 errors="replace" 防止遇到非 UTF-8 字元時解碼崩潰
            with open(task_log_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return jsonify({"log": content})
        except Exception as e:
            return jsonify({"log": f"Error reading log: {str(e)}"})
    return jsonify({"log": "No logs recorded yet."})

@app.route('/online/stop', methods=['POST'])
def stop_task():
    global task_process, task_status
    with _task_lock:
        if task_status != "running" or not task_process:
            return jsonify({"success": False, "message": "No running task to stop."})
        task_status = "idle"
    try:
        task_process.terminate()
        return jsonify({"success": True, "message": "Task stopped."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to terminate task: {str(e)}"})

@app.route('/online/db_status')
def db_status():
    import sqlite3, os, glob
    result = {}

    # stock_data: get latest date from table "2330" (or fallback to first table)
    path = "sql/stock_data.db"
    if not os.path.exists(path):
        result["stock_data"] = {"error": "檔案不存在"}
    else:
        size_mb = round(os.path.getsize(path) / 1024 / 1024, 1)
        try:
            con = sqlite3.connect(path)
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='2330'").fetchall()
            if tables:
                row = con.execute('SELECT MAX(date) FROM "2330"').fetchone()
                latest = row[0] if row else "no data"
            else:
                first = con.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
                if first:
                    row = con.execute(f'SELECT MAX(date) FROM "{first[0]}"').fetchone()
                    latest = row[0] if row else "no data"
                else:
                    latest = "no tables"
            con.close()
            result["stock_data"] = {"latest": latest, "size_mb": size_mb}
        except Exception as e:
            result["stock_data"] = {"error": str(e)}

    # stock_big3: table names are dates like YYYYMMDD
    path = "sql/stock_big3.db"
    if not os.path.exists(path):
        result["stock_big3"] = {"error": "檔案不存在"}
    else:
        size_mb = round(os.path.getsize(path) / 1024 / 1024, 1)
        try:
            con = sqlite3.connect(path)
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if tables:
                table_dates = [t[0] for t in tables if t[0].isdigit() and len(t[0]) == 8]
                latest = max(table_dates) if table_dates else f"{len(tables)} tables"
            else:
                latest = "no tables"
            con.close()
            result["stock_big3"] = {"latest": latest, "size_mb": size_mb}
        except Exception as e:
            result["stock_big3"] = {"error": str(e)}

    # tdcc_dist: tables are stock IDs
    path = "sql/tdcc_dist.db"
    if not os.path.exists(path):
        result["tdcc_dist"] = {"error": "檔案不存在"}
    else:
        size_mb = round(os.path.getsize(path) / 1024 / 1024, 1)
        try:
            con = sqlite3.connect(path)
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            latest = f"{len(tables)} tables"
            con.close()
            result["tdcc_dist"] = {"latest": latest, "size_mb": size_mb}
        except Exception as e:
            result["tdcc_dist"] = {"error": str(e)}

    # pe_networth_yield: count CSV files
    pe_files = sorted(glob.glob("data/down_pe_networth_yield/tse*.csv"))
    result["pe_networth"] = {
        "latest": os.path.basename(pe_files[-1]) if pe_files else "no data",
        "count": len(pe_files)
    }

    # tdcc latest date from one known stock
    if "tdcc_dist" in result and "tables" in str(result["tdcc_dist"].get("latest", "")):
        try:
            con = sqlite3.connect("sql/tdcc_dist.db")
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if tables:
                t = tables[0][0]
                row = con.execute(f'SELECT MAX(date) FROM "{t}"').fetchone()
                result["tdcc_dist"]["latest_date"] = row[0] if row else "?"
                result["tdcc_dist"]["table_count"] = len(tables)
            con.close()
        except Exception:
            pass

    return jsonify(result)

@app.route('/static/final/<path:filename>')
def serve_final_files(filename):
    # Strict directory traversal check
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        return "Access Denied", 400
        
    safe_path = safe_join('final', filename)
    if not safe_path or not os.path.exists(safe_path):
        return "File not found", 404

    if filename.endswith('.html'):
        try:
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()
            report_type = filename.replace('_good.html', '')
            title_map = {
                'fund': '投信追蹤好股 (Fund)',
                'pointK': '技術分析好股 (PointK)',
                'revenue': '營收強勢好股 (Revenue)',
                'director': '董監持股好股 (Director)',
                'chip_fund': '籌碼+基本面精選好股 (Chip & Fund)'
            }
            title = title_map.get(report_type, report_type.upper() + " 選股報表")
            # extract only the <table> if file is already a full rendered page
            if '<table' in content and '<!DOCTYPE' in content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                tbl = soup.find('table')
                table_html = str(tbl) if tbl else content
            else:
                table_html = content
            return render_template('report.html', table_html=table_html, title=title)
        except Exception as e:
            return f"Error reading report: {str(e)}", 500
            
    # For static assets like CSVs, serve them securely
    directory, file = os.path.split(safe_path)
    return send_from_directory(directory, file)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
