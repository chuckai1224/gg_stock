import subprocess
import os
import sys

# Set standard output encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

lines = []
def log(s):
    print(s)
    lines.append(str(s))

log("=== 1. 顯示卡與硬體配備 ===")
gpu_info = run_ps("Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, Status | Format-List | Out-String")
log(gpu_info)

cpu_info = run_ps("Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List | Out-String")
log(cpu_info)

log("=== 2. 近 7 天重大系統錯誤 (Critical & Error in System) ===")
sys_errs = run_ps("""
Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-7)} -ErrorAction SilentlyContinue | 
Select-Object TimeCreated, ProviderName, Id, Message | Format-Table -Wrap | Out-String -Width 200
""")
log(sys_errs if sys_errs else "無近 7 天 System 錯誤")

log("=== 3. 顯示卡 / 驅動重設相關 (Display Driver Crashes / TDR / Event ID 4101) ===")
tdr_errs = run_ps("""
Get-WinEvent -FilterHashtable @{LogName='System'; Id=4101; StartTime=(Get-Date).AddDays(-14)} -ErrorAction SilentlyContinue |
Select-Object TimeCreated, Message | Format-Table -Wrap | Out-String -Width 200
""")
log(tdr_errs if tdr_errs else "無 Display Driver 4101 重設紀錄")

log("=== 4. 近 7 天應用程式當機與凍結 (Application Hang / Error) ===")
app_errs = run_ps("""
Get-WinEvent -FilterHashtable @{LogName='Application'; Level=1,2; StartTime=(Get-Date).AddDays(-7)} -ErrorAction SilentlyContinue |
Where-Object { $_.ProviderName -match 'Application Hang|Application Error|Desktop Window Manager' -or $_.Id -in 1000,1001,1002 } |
Select-Object TimeCreated, ProviderName, Id, Message | Format-Table -Wrap | Out-String -Width 200
""")
log(app_errs if app_errs else "無近 7 天 App Hang/Error 紀錄")

log("=== 5. Windows 穩定度紀錄 (Reliability Records) ===")
rel_errs = run_ps("""
Get-CimInstance Win32_ReliabilityRecords -ErrorAction SilentlyContinue | 
Where-Object { $_.TimeGenerated -gt (Get-Date).AddDays(-7) } |
Select-Object TimeGenerated, SourceName, Message | Format-Table -Wrap | Out-String -Width 200
""")
log(rel_errs if rel_errs else "無近 7 天可靠度異常紀錄")

log("=== 6. 藍底白字 / Minidump ===")
minidump_path = "C:\\Windows\\Minidump"
if os.path.exists(minidump_path):
    try:
        files = os.listdir(minidump_path)
        log(f"Minidump 檔案 ({len(files)} 個): {files[-5:]}")
    except Exception as e:
        log(f"讀取 Minidump 失敗: {e}")
else:
    log("無 Minidump 資料夾")

with open("work/health_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
