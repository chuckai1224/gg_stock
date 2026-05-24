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
        task_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        task_process.wait()
        with _task_lock:
            if task_status == "running":
                task_status = "completed" if task_process.returncode == 0 else "failed"
    except Exception as e:
        log_file.write(f"\n[Execution error: {str(e)}]\n")
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
        cmd = f".\\venv\\Scripts\\python.exe gg_stock.py {mode_str} {date_str}"
    elif action == "snapshot":
        log_file.write("[System] Starting Database Snapshot Download...\n")
        cmd = ".\\venv\\Scripts\\python.exe download_snapshot.py"
    elif action == "crawl":
        if date_str and len(date_str) == 8 and date_str.isdigit():
            y = date_str[0:4]
            m = str(int(date_str[4:6]))
            d = str(int(date_str[6:8]))
            log_file.write(f"[System] Starting Live Crawler for {y}-{m.zfill(2)}-{d.zfill(2)}...\n")
            cmd = f".\\venv\\Scripts\\python.exe crawl.py {y} {m} {d}"
        else:
            log_file.write("[System] Starting Live Crawler for today...\n")
            cmd = ".\\venv\\Scripts\\python.exe crawl.py"
    elif action == "big3":
        if date_str and len(date_str) == 8 and date_str.isdigit():
            log_file.write(f"[System] Starting Three Institutional Investors Crawler for {date_str}...\n")
            cmd = f".\\venv\\Scripts\\python.exe stock_big3.py -d {date_str} {date_str}"
        else:
            log_file.write("[System] Starting Three Institutional Investors Crawler for today...\n")
            cmd = ".\\venv\\Scripts\\python.exe stock_big3.py"
    elif action == "pe":
        if date_str and len(date_str) == 8 and date_str.isdigit():
            log_file.write(f"[System] Starting PE/NetWorth/Yield Crawler for {date_str}...\n")
            cmd = f".\\venv\\Scripts\\python.exe pe_networth_yeild.py -d {date_str} {date_str}"
        else:
            log_file.write("[System] Starting PE/NetWorth/Yield Crawler for today...\n")
            cmd = ".\\venv\\Scripts\\python.exe pe_networth_yeild.py"
    elif action == "tdcc":
        log_file.write("[System] Starting TDCC (集保股權) Crawler...\n")
        cmd = ".\\venv\\Scripts\\python.exe tdcc_get.py"
    elif action == "revenue":
        log_file.write("[System] Starting Monthly Revenue Crawler...\n")
        cmd = ".\\venv\\Scripts\\python.exe revenue.py"
    elif action == "director":
        log_file.write("[System] Starting Directors Shareholding Crawler...\n")
        cmd = ".\\venv\\Scripts\\python.exe director.py"
    elif action == "eps":
        roc_year = int(date_str[:4]) - 1911 if (date_str and len(date_str) >= 4 and date_str[:4].isdigit()) else 115
        season = (int(date_str[4:6]) - 1) // 3 + 1 if (date_str and len(date_str) == 8 and date_str.isdigit()) else 1
        log_file.write(f"[System] Starting Quarterly EPS Crawler (ROC {roc_year} Q{season})...\n")
        cmd = f".\\venv\\Scripts\\python.exe eps.py {roc_year} {season}"
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
            with open(task_log_path, "r", encoding="utf-8") as f:
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
                table_html = f.read()
            report_type = filename.replace('_good.html', '')
            title_map = {
                'fund': '投信追蹤好股 (Fund)',
                'pointK': '技術分析好股 (PointK)',
                'revenue': '營收強勢好股 (Revenue)',
                'director': '董監持股好股 (Director)'
            }
            title = title_map.get(report_type, report_type.upper() + " 選股報表")
            return render_template('report.html', table_html=table_html, title=title)
        except Exception as e:
            return f"Error reading report: {str(e)}", 500
            
    # For static assets like CSVs, serve them securely
    directory, file = os.path.split(safe_path)
    return send_from_directory(directory, file)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
