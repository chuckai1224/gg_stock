import os
import sys
import subprocess
import threading
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from flask import Flask, render_template, redirect, url_for, jsonify, request, send_from_directory

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
        log_file.write("[System] Starting Database Snapshot Download & Extraction...\n")
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

@app.route('/static/final/<path:filename>')
def serve_final_files(filename):
    return send_from_directory('final', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)