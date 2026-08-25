import subprocess
import os

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

print("=== 1. AIPro / AIPSo 檔案路徑與資訊 ===")
aip_find = run_ps("Get-ChildItem -Path C:\\, D:\\ -Filter 'AIPro2.bin' -Recurse -ErrorAction SilentlyContinue | Select-Object FullName, Length, LastWriteTime | Format-Table -Wrap | Out-String -Width 200")
print(aip_find)

print("=== 2. 瀏覽器 (Chrome / Edge / Brave / Firefox) 錯誤或當機 ===")
browser_errs = run_ps("""
Get-WinEvent -FilterHashtable @{LogName='Application'; Level=1,2; StartTime=(Get-Date).AddDays(-14)} -ErrorAction SilentlyContinue |
Where-Object { $_.Message -match 'chrome|msedge|brave|firefox|opera' } |
Select-Object TimeCreated, ProviderName, Id, Message | Format-Table -Wrap | Out-String -Width 200
""")
print(browser_errs if browser_errs else "無瀏覽器崩潰紀錄")

print("=== 3. 系統核心電力與凍結 (Kernel-Power Event 41 / 睡眠喚醒) ===")
power_errs = run_ps("""
Get-WinEvent -FilterHashtable @{LogName='System'; Id=41; StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue |
Select-Object TimeCreated, Message | Format-Table -Wrap | Out-String -Width 200
""")
print(power_errs if power_errs else "無異常斷電重啟 (Event 41)")

print("=== 4. DWM 桌面視窗管理員錯誤 ===")
dwm_errs = run_ps("""
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Desktop Window Manager'; StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue |
Select-Object TimeCreated, Id, Message | Format-Table -Wrap | Out-String -Width 200
""")
print(dwm_errs if dwm_errs else "無 DWM 崩潰紀錄")
