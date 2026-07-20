@echo off
:: =========================================================
:: AGY CLI Bypass & Admin Elevation Script (CMD)
:: =========================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [Info] Requesting Administrator Privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\" %*' -Verb RunAs"
    exit /b
)

echo [Success] Running AGY CLI with Full Privileges...
echo ---------------------------------------------------------

powershell -NoProfile -ExecutionPolicy Bypass -Command "agy %*"
