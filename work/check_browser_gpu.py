import subprocess
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

print("=== 瀏覽器 GPU Process 檢查 ===")
ps_cmd = """
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'chrome|msedge' -and $_.CommandLine -match 'type=gpu-process' } | Select-Object ProcessId, Name, CommandLine | Format-List
"""
print(run_ps(ps_cmd))
