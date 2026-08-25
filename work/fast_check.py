import subprocess
import json

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

print("=== 系統版本 ===")
print(run_ps("Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion' | Select-Object ProductName, DisplayVersion, CurrentBuild | Format-List | Out-String"))

print("=== 正在運行的相關程式 ===")
print(run_ps("Get-Process | Where-Object { $_.ProcessName -match 'chrome|msedge|AIPro|Lin|MSI|dwm' } | Select-Object ProcessName, Id, WS, CPU | Format-Table -AutoSize | Out-String"))

print("=== 磁碟 SMART 狀態 ===")
print(run_ps("Get-PhysicalDisk | Select-Object DeviceId, FriendlyName, MediaType, OperationalStatus, HealthStatus | Format-Table -AutoSize | Out-String"))
