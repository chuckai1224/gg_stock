# -*- coding: utf-8 -*-
"""
天堂 (Lineage) 連線與環境追蹤檢測腳本
功能：持續記錄 12:05 ~ 12:08 (或指定時間區間) 的網路延遲、DNS、TCP 狀態與遊戲程序狀態
"""
import time
import socket
import subprocess
import datetime
import os
import sys

# 確保控制台輸出不亂碼
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

LOG_FILE = os.path.join(os.path.dirname(__file__), "lineage_monitor_log.txt")

DOMAINS = ["tw.beanfun.com", "lineage.beanfun.com", "gamania.com"]
# 常見遊戲啟動/通訊埠 (443, 80, 2000, 7000, 8000, 2001)
TEST_PORTS = [
    ("tw.beanfun.com", 443),
    ("lineage.beanfun.com", 443),
]

def log(msg):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = f"[{now_str}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def test_ping(host):
    try:
        # Windows ping -n 1 -w 1000
        cmd = f"ping -n 1 -w 1000 {host}"
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if res.returncode == 0:
            # 解析時間
            for l in res.stdout.splitlines():
                if "時間=" in l or "time=" in l or "Time=" in l or "ms" in l:
                    return True, l.strip()
            return True, "Ping 成功"
        else:
            return False, "Ping 超時或失敗"
    except Exception as e:
        return False, str(e)

def test_tcp(host, port, timeout=2.0):
    start = time.time()
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        elapsed = (time.time() - start) * 1000
        return True, f"{elapsed:.1f} ms"
    except Exception as e:
        return False, str(e)

def check_game_processes():
    try:
        cmd = 'tasklist /FO CSV /NH'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        lines = res.stdout.splitlines()
        found = []
        target_names = ["lineage", "beanfun", "purple", "game"]
        for line in lines:
            line_lower = line.lower()
            if any(name in line_lower for name in target_names):
                found.append(line.replace('"', ''))
        return found
    except Exception as e:
        return [str(e)]

def run_monitoring(duration_seconds=240, interval=2):
    log("=== 開始執行 天堂 連線與環境追蹤檢測 ===")
    start_time = time.time()
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n--- 開始監控: {datetime.datetime.now()} ---\n")

    count = 0
    while time.time() - start_time < duration_seconds:
        count += 1
        log(f"--- [檢測次數 #{count}] ---")
        
        # 1. 測試 Domain Ping
        for d in DOMAINS:
            ok, info = test_ping(d)
            status_str = "SUCCESS" if ok else "FAIL"
            log(f"Ping {d:20s}: [{status_str}] -> {info}")
            
        # 2. 測試 TCP 埠連線
        for host, port in TEST_PORTS:
            ok, info = test_tcp(host, port)
            status_str = "SUCCESS" if ok else "FAIL"
            log(f"TCP {host}:{port}: [{status_str}] -> {info}")
            
        # 3. 檢查相關程序狀態
        procs = check_game_processes()
        if procs:
            log(f"偵測到相關程序 ({len(procs)} 個):")
            for p in procs:
                log(f"   -> {p}")
        else:
            log("未偵測到 Lineage / beanfun / Purple 相關執行程序")
            
        time.sleep(interval)
        
    log("=== 追蹤結束 ===")

if __name__ == "__main__":
    import sys
    duration = 240 # 預設跑 4 分鐘
    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    run_monitoring(duration_seconds=duration, interval=3)
