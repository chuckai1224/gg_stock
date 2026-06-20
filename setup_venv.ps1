# Windows PowerShell Script to Set Up Python Virtual Environment (venv)
# Usage: .\setup_venv.ps1

$ErrorActionPreference = "Stop"

# Define colors for output
function Write-Header ($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Write-Success ($msg) {
    Write-Host "[SUCCESS] $msg" -ForegroundColor Green
}

function Write-Info ($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor White
}

function Write-WarningMsg ($msg) {
    Write-Host "[WARNING] $msg" -ForegroundColor Yellow
}

function Write-ErrorMsg ($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

Write-Header "開始建立 Python 虛擬環境與安裝套件"

# 1. 檢查系統是否已安裝 Python
try {
    $pythonPath = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonPath) {
        Write-ErrorMsg "找不到 python 指令，請確認 Python 是否已安裝並已加入環境變數 PATH 中。"
        exit 1
    }

    $pythonVersion = python --version 2>&1
    Write-Info "偵測到系統 Python 版本: $pythonVersion"
    Write-Info "Python 路徑: $($pythonPath.Source)"
}
catch {
    Write-ErrorMsg "檢查 Python 時發生錯誤: $_"
    exit 1
}

# 2. 建立 venv 虛擬環境
Write-Header "建立虛擬環境 (venv)"
$venvDir = Join-Path $PSScriptRoot "venv"

if (Test-Path $venvDir) {
    Write-WarningMsg "偵測到已存在 venv 資料夾。"
    Write-Info "正在更新/重建虛擬環境..."
} else {
    Write-Info "正在建立全新的虛擬環境於 $venvDir..."
}

try {
    python -m venv "$venvDir"
    Write-Success "虛擬環境建立成功！"
}
catch {
    Write-ErrorMsg "建立虛擬環境失敗: $_"
    exit 1
}

# 3. 確保虛擬環境中的 pip 為最新版本
Write-Header "升級 pip 工具"
$pipExe = Join-Path $venvDir "Scripts\pip.exe"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-ErrorMsg "找不到虛擬環境中的 Python 執行檔: $pythonExe"
    exit 1
}

try {
    Write-Info "正在升級 pip..."
    & $pythonExe -m pip install --upgrade pip
    Write-Success "pip 升級完成！"
}
catch {
    Write-WarningMsg "升級 pip 失敗 (可能是網路或權限問題)，將繼續嘗試安裝套件: $_"
}

# 4. 安裝 required 套件
Write-Header "安裝專案依賴套件"
$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-ErrorMsg "找不到 requirements.txt 檔案，無法安裝套件。"
    exit 1
}

try {
    Write-Info "正在從 requirements.txt 安裝套件..."
    & $pipExe install -r $requirementsFile --trusted-host pypi.org --trusted-host files.pythonhosted.org
    Write-Success "所有套件安裝成功！"
}
catch {
    Write-ErrorMsg "套件安裝失敗: $_"
    exit 1
}

# 5. 驗證安裝結果
Write-Header "驗證套件安裝"
try {
    $verifyCmd = "import pandas, numpy, scipy, sqlalchemy, bs4, lxml, requests, matplotlib, mplfinance, seaborn, PIL, flask; from dateutil.relativedelta import relativedelta; print('OK')"
    $verifyResult = & $pythonExe -c $verifyCmd 2>&1
    if ($verifyResult -eq "OK") {
        Write-Success "核心套件驗證成功，所有模組皆可正常載入！"
    } else {
        Write-WarningMsg "驗證程式輸出異常: $verifyResult"
    }
}
catch {
    Write-ErrorMsg "驗證套件時發生錯誤: $_"
}

Write-Header "設定完成"
Write-Host "您可以使用以下指令啟動虛擬環境：" -ForegroundColor Green
Write-Host "  .\venv\Scripts\activate" -ForegroundColor Yellow
Write-Host "或者直接使用虛擬環境的執行檔執行腳本，例如：" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe online.py" -ForegroundColor Yellow
Write-Host ""
