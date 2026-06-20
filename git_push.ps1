param(
    [string]$Message = ""
)

Set-Location $PSScriptRoot

if ($Message -eq "") {
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $Message = "update $today"
}

git add -A
git commit -m $Message
git push

$cf_html = "final\chip_fund_good.html"
if (Test-Path $cf_html) {
    Start-Process $cf_html
}
