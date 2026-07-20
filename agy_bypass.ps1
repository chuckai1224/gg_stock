# =========================================================
# AGY CLI Bypass & Admin Elevation Script (PowerShell)
# =========================================================

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[Info] Requesting Administrator Elevation..." -ForegroundColor Yellow
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File '$scriptPath' $args" -Verb RunAs
    exit
}

Write-Host "[Success] Running with Administrator Privileges & ExecutionPolicy Bypass!" -ForegroundColor Green
Write-Host "---------------------------------------------------------"

if ($args.Count -gt 0) {
    & agy $args
} else {
    & agy
}
