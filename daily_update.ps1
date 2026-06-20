param(
    [string]$Date = ""
)

# 使用腳本所在的資料夾路徑作為工作目錄，不再鎖死 D:\gg_stock
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

if ($Date -eq "") {
    $today = (Get-Date).ToString("yyyyMMdd")
    $isToday = $true
} else {
    $today = $Date
    $isToday = $false
}

$y = $today.Substring(0, 4)
$m = $today.Substring(4, 2)
$d = $today.Substring(6, 2)

if (-not (Test-Path logs)) { New-Item -ItemType Directory logs | Out-Null }
$log = "logs\daily_$today.log"

# PS 5.1 Tee-Object lacks -Encoding; use a filter to write UTF-8 and echo to console
filter Tee-Utf8 { $_ | Out-File -Append -FilePath $log -Encoding utf8; $_ }

"===== daily_update $today =====" | Out-File $log -Encoding utf8

Write-Host "[1/5] crawl $today ..."
if ($isToday) {
    & $python crawl.py 2>&1 | Tee-Utf8
} else {
    & $python crawl.py $y $m $d 2>&1 | Tee-Utf8
}

Write-Host "[2/5] revenue $today ..."
if ($isToday) {
    & $python revenue.py 2>&1 | Tee-Utf8
} else {
    & $python revenue.py -d $today 2>&1 | Tee-Utf8
}

Write-Host "[3/5] stock_big3 $today ..."
if ($isToday) {
    & $python stock_big3.py 2>&1 | Tee-Utf8
} else {
    & $python stock_big3.py -d $today $today 2>&1 | Tee-Utf8
}

Write-Host "[4/5] pe_networth $today ..."
if ($isToday) {
    & $python pe_networth_yeild.py 2>&1 | Tee-Utf8
} else {
    & $python pe_networth_yeild.py -d $today 2>&1 | Tee-Utf8
}

# TDCC: run manually on Fridays
# & $python tdcc_get.py 2>&1 | Tee-Utf8

Write-Host "[5/5] gg_stock $today ..."
if ($isToday) {
    & $python gg_stock.py 2>&1 | Tee-Utf8
} else {
    & $python gg_stock.py gg $today 2>&1 | Tee-Utf8
}

# Copy chip_fund_good.html to D:\to_google
$cf_src = "final\chip_fund_good.html"
if (Test-Path $cf_src) {
    if (-not (Test-Path "d:\to_google")) {
        New-Item -ItemType Directory "d:\to_google" | Out-Null
    }
    Copy-Item $cf_src "d:\to_google\chip_fund_good.html" -Force
    Write-Host "Copied $cf_src to d:\to_google" | Tee-Utf8
} else {
    Write-Host "Warning: $cf_src not found" | Tee-Utf8
}

"===== done =====" | Tee-Utf8
Write-Host "done. log: $log"

Write-Host "Running git_push.ps1 ..."
& .\git_push.ps1 2>&1 | Tee-Utf8
