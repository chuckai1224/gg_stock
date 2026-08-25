import subprocess
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

print("=== Lin.bin 載入的顯卡模組 DLL ===")
ps_cmd = """
$p = Get-Process Lin -ErrorAction SilentlyContinue | Select-Object -First 1
if ($p) {
    $modules = $p.Modules | Select-Object -ExpandProperty FileName
    $nv = $modules | Where-Object { $_ -match 'nv(api|wgf2|d3d|oglv|lddm)' }
    $intel = $modules | Where-Object { $_ -match 'igd(10|11|12|9|gmm|umd)' }
    Write-Output "PID: $($p.Id)"
    Write-Output "--- NVIDIA 相關 DLL ---"
    if ($nv) { $nv } else { "無" }
    Write-Output "--- Intel 相關 DLL ---"
    if ($intel) { $intel } else { "無" }
} else {
    Write-Output "Lin.bin 目前未在運行"
}
"""
print(run_ps(ps_cmd))
