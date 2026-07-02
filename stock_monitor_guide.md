# 股票即時雙週期 (日K / 30分K) 看盤系統指南

本指南說明如何配置與使用在 `d:\gg_stock` 專案中開發的股票即時看盤軟體。該軟體使用永豐金 `shioaji` API 獲取即時與歷史行情，並使用 PyQt5 與 `pyqtgraph` 呈現流暢的圖表。

---

## 系統架構

看盤軟體採用 **單進程多執行緒 (Single Process, Multi-threaded)** 架構，確保網路請求（Shioaji 行情下載與訂閱）不阻塞 PyQt 介面繪圖主執行緒。

```mermaid
graph TD
    subgraph 單一 Python 進程 (stock_monitor_gg.py)
        A[主執行緒: GUI 介面與輸入框] 
        B[背景執行緒: Shioaji 行情 & 歷史 K 線 Worker]
        A -->|查詢代號| B
        B -->|歷史 K 線資料 (日K, 30m)| A
        B -->|即時 K 線更新訊號| A
    end
    shioaji[shioaji API / 永豐金報價源] -->|歷史 KBars & 即時 Ticks| B
```

---

## 檔案結構說明

1. **[stock_monitor_gg.py](stock_monitor_gg.py)**  
   主程式進入點。處理指令列參數，初始化 PyQt5 應用程式，串接 UI 的查詢訊號與背景 Worker 的處理槽，並在視窗關閉時觸發 Worker 的安全退出與 Shioaji API 登出。
2. **[stock_worker_gg.py](stock_worker_gg.py)**  
   行情與 K 線處理背景執行緒 (`QThread`)。負責 Shioaji API 的連線、動態切換代號的訂閱/取消訂閱、歷史 K 線下載（日K 180天、30分K 20天）、以及即時報價的增量 K 線更新。
3. **[gui_stock_main_gg.py](gui_stock_main_gg.py)**  
   GUI 視窗介面。包含頂部股票代號查詢輸入框與查詢按鈕。畫面分為兩大圖表區塊（上半部日K，下半部30分K）。內含自定義的 `TimeIndexAxis`（跨天分K自動日期標記）與 K 線圖層。

---

## 安裝與依賴環境

此看盤系統除了專案原本的 Pandas 與 NumPy 外，額外依賴以下套件（若您尚未安裝，請使用專案內虛擬環境進行安裝）：

```bash
# 安裝看盤系統需要的 GUI 與行情套件
.\venv\Scripts\pip.exe install PyQt5 pyqtgraph shioaji
```

---

## 憑證與金鑰配置

為了能登入永豐金 API，請選擇以下方式之一進行配置：

### 方式 1：使用家目錄全域憑證 (推薦)
若您的家目錄下已建立全域設定，系統會自動載入：
- 登入帳密：`~/.fut/login.json`
- CA 憑證：`~/.fut/ca.json`

### 方式 2：本專案本機配置
直接編輯本專案資料夾下的本機設定檔。這兩個檔案可能包含 API key、憑證密碼與身分證字號，請勿提交到 Git：
- **登入設定** [trade/login.txt](trade/login.txt)：
  ```json
  {
    "api_key": "YOUR_API_KEY",
    "secret_key": "YOUR_SECRET_KEY"
  }
  ```
- **憑證設定** [trade/ca.txt](trade/ca.txt)：
  ```json
  {
    "ca_path": "C:\\path\\to\\SinoPac.pfx",
    "ca_passwd": "YOUR_CA_PASSWORD",
    "person_id": "YOUR_PERSON_ID"
  }
  ```

---

## 啟動與操作指南

### 1. 啟動軟體
開啟 PowerShell 終端機，執行以下命令：

* **使用預設股票 (2330 台積電) 啟動**：
  ```powershell
  .\venv\Scripts\python.exe stock_monitor_gg.py
  ```

* **指定特定股票代號啟動** (例如 2454 聯發科)：
  ```powershell
  .\venv\Scripts\python.exe stock_monitor_gg.py --symbol 2454
  ```

---

### 2. 介面操作
- **動態切換股票**：於頂部「股票代號」輸入框中輸入新的股票代號（例如 `2603` 陽明），按 `Enter` 鍵或點擊 **「查詢股票」** 按鈕，背景執行緒會自動切換並在 1 秒內更新所有週期之 K 線。
- **圖表縮放與移動**：
  - **移動**：在任一主圖上拖曳**滑鼠左鍵**即可平移視圖。
  - **縮放**：使用**滑鼠滾輪**可對時間軸進行縮放。
  - **主副圖同歩**：上方的 K 線圖與下方的成交量圖在縮放時會自動同歩對齊。
- **跨日自動標記**：於 30分K 中，當 K 線時間跨越到新的一天時，時間軸上的第一個 K 棒會標示日期（如 `07/02 09:00`），隨後顯示時間（如 `09:30`），方便您快速定位跨天走勢。
- **即時更新節流**：為防盤中極快行情導致介面卡頓，Worker 會每 100ms（每秒最多 10 次）定時刷新 GUI，確保圖表維持極高流暢度。

---

## 常見檢查項目

- **PowerShell 顯示中文亂碼**：先執行 `chcp 65001`，或使用支援 UTF-8 的終端機開啟本文件。
- **缺少套件**：若啟動時出現 `ModuleNotFoundError`，請重新執行 `.\venv\Scripts\pip.exe install -r requirements.txt`。
- **登入失敗**：確認 `~/.fut/login.json`、`~/.fut/ca.json` 或 `trade/login.txt`、`trade/ca.txt` 的 JSON 格式與 CA 路徑正確。
- **歷史 K 線有資料但即時不更新**：優先檢查 Shioaji 股票 Tick callback 與訂閱版本是否與目前安裝的 `shioaji` 版本相符。
