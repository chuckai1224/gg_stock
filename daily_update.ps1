param(
    [string]$Date = ""
)

Set-Location D:\gg_stock

$python = "D:\gg_stock\venv\Scripts\python.exe"

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

"===== daily_update $today =====" | Out-File $log -Encoding utf8

Write-Host "[1/5] crawl $today ..."
if ($isToday) {
    & $python crawl.py 2>&1 | Tee-Object -Append $log
} else {
    & $python crawl.py $y $m $d 2>&1 | Tee-Object -Append $log
}

Write-Host "[2/5] twse_big3 $today ..."
if ($isToday) {
    & $python twse_big3.py 2>&1 | Tee-Object -Append $log
} else {
    & $python twse_big3.py -d $today 2>&1 | Tee-Object -Append $log
}

Write-Host "[3/5] otc_big3 $today ..."
if ($isToday) {
    & $python otc_big3.py 2>&1 | Tee-Object -Append $log
} else {
    & $python otc_big3.py -d $today $today 2>&1 | Tee-Object -Append $log
}

Write-Host "[4/5] pe_networth $today ..."
if ($isToday) {
    & $python pe_networth_yeild.py 2>&1 | Tee-Object -Append $log
} else {
    & $python pe_networth_yeild.py -d $today 2>&1 | Tee-Object -Append $log
}

# TDCC: run manually on Fridays
# & $python tdcc_get.py 2>&1 | Tee-Object -Append $log

Write-Host "[5/5] gg_stock $today ..."
if ($isToday) {
    & $python gg_stock.py 2>&1 | Tee-Object -Append $log
} else {
    & $python gg_stock.py gg $today 2>&1 | Tee-Object -Append $log
}

"===== done =====" | Tee-Object -Append $log
Write-Host "done. log: $log"
Start-Process "final\revenue_good.html"
