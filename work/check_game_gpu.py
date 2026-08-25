import subprocess
import winreg
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def run_ps(cmd):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout.strip()

print("=== 1. Windows 圖形效能設定偏好 (UserGpuPreferences) ===")
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\DirectX\UserGpuPreferences") as key:
        num_values = winreg.QueryInfoKey(key)[1]
        for i in range(num_values):
            name, val, _ = winreg.EnumValue(key, i)
            if any(k in name.lower() for k in ['lin', 'lineage', 'aipro', 'game']):
                print(f"程式: {name}")
                print(f"  設定值: {val}")
                # GpuPreference=1: 省電 (內顯 Intel)
                # GpuPreference=2: 高效能 (獨顯 NVIDIA)
                # GpuPreference=0: 讓 Windows 決定
except Exception as e:
    print("UserGpuPreferences 查詢失敗或無特定設定:", e)

print("\n=== 2. 當前正在運行的 Lin.bin 關聯 GPU 引擎 ===")
# 使用 Typeperf 或 Get-Counter 檢查 GPU Engine
ps_gpu = run_ps("""
Get-Process Lin -ErrorAction SilentlyContinue | ForEach-Object {
    $pid = $_.Id
    $counters = (Get-Counter -ListSet "GPU Engine").PathsWithInstances | Where-Object { $_ -match "pid_$pid" }
    $counters | ForEach-Object {
        $c = Get-Counter -Counter $_ -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue
        if ($c.CounterSamples.CookedValue -gt 0) {
            Write-Output "$($_.ToString()) : $($c.CounterSamples.CookedValue)%"
        }
    }
}
""")
print(ps_gpu if ps_gpu else "未偵測到即時 GPU 負載 Counter 或權限受限")

print("\n=== 3. 檢查系統預設與顯卡配對 ===")
# 檢查實體 GPU 索引
ps_adapters = run_ps("""
Get-CimInstance Win32_VideoController | Select-Object DeviceID, Name, AdapterRAM | Format-Table -AutoSize | Out-String
""")
print(ps_adapters)
