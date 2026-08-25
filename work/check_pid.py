import subprocess
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

ps_cmd = """
$p = Get-Process -Id 12048 -ErrorAction SilentlyContinue
if ($p) {
    Write-Output "Name: $($p.ProcessName), PID: $($p.Id)"
    try {
        $mods = $p.Modules
        Write-Output "總模組數: $($mods.Count)"
        $mods | Select-Object -ExpandProperty FileName | Out-File -FilePath work/lin_modules.txt -Encoding utf8
    } catch {
        Write-Output "無法讀取 Modules (可能受遊戲防護保護): $_"
    }
}
"""
print(run_ps(ps_cmd))
