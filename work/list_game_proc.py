import subprocess
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

print("=== 正在運行的所有 Lineage / AIPro / 遊戲程序 ===")
ps_cmd = """
Get-Process | Where-Object { $_.ProcessName -match 'lin|aip|game' } | Select-Object Id, ProcessName, Path | Format-Table -AutoSize
"""
print(run_ps(ps_cmd))
