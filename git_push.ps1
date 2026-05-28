param(
    [string]$Message = ""
)

Set-Location D:\gg_stock

if ($Message -eq "") {
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $Message = "update $today"
}

git add -A
git commit -m $Message
git push

$htmls = @(
    "final\revenue_good.html",
    "final\pointK_good.html",
    "final\director_good.html",
    "final\fund_good.html"
)
foreach ($f in $htmls) {
    if (Test-Path $f) { Start-Process $f }
}
