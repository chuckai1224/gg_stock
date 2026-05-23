# 環境安裝說明（Windows）

---

## 一、安裝 Python

1. 前往 [https://www.python.org/downloads/](https://www.python.org/downloads/) 下載 **Python 3.11**（建議，3.9+ 皆可）
2. 執行安裝程式，**勾選「Add Python to PATH」**，再按 Install Now
3. 安裝完成後，開啟 **命令提示字元（CMD）** 確認版本：

```cmd
python --version
```

應顯示 `Python 3.11.x`。

---

## 二、建立虛擬環境（venv）

在 `D:\gg_stock` 目錄下建立獨立環境，避免影響系統 Python：

```cmd
cd D:\gg_stock
python -m venv venv
```

啟動虛擬環境：

```cmd
.\venv\Scripts\activate
```

提示字元前面出現 `(venv)` 表示成功。

> 之後每次開新視窗要操作都需要先 activate，或直接用 `.\venv\Scripts\python.exe` 完整路徑執行。

---

## 三、安裝核心套件

確認已在 venv 環境內（或使用完整路徑 `.\venv\Scripts\pip.exe`）：

```cmd
pip install python-dateutil pandas numpy scipy sqlalchemy beautifulsoup4 lxml requests matplotlib mplfinance seaborn kline Pillow flask
```

| 套件 | 用途 |
|------|------|
| `python-dateutil` | 日期計算（`relativedelta`） |
| `pandas` | 資料處理核心 |
| `numpy` | 數值運算 |
| `scipy` | 訊號處理（`scipy.signal`） |
| `sqlalchemy` | SQLite 資料庫存取 |
| `beautifulsoup4` | HTML 解析（爬蟲） |
| `lxml` | HTML/XML 解析器 |
| `requests` | HTTP 請求（下載資料） |
| `matplotlib` | 繪圖 |
| `mplfinance` | K 線圖 |
| `seaborn` | 統計視覺化 |
| `kline` | K 線 resample 工具 |
| `Pillow` | 圖片處理 |
| `flask` | 網頁控制台（`online.py`） |

---

## 四、建立必要資料夾

```cmd
cd D:\gg_stock
mkdir sql
mkdir data\stock_data
mkdir data\revenue
mkdir data\director
mkdir data\down_pe_networth_yield
mkdir final
mkdir error
mkdir out
mkdir log
```

| 資料夾 | 用途 |
|--------|------|
| `sql/` | SQLite 資料庫（股價、三大法人、集保等） |
| `data/stock_data/` | 個股日 K CSV |
| `data/revenue/` | 月營收資料 |
| `data/director/` | 董監事持股資料 |
| `data/down_pe_networth_yield/` | 本益比/淨值比資料 |
| `final/` | 選股結果 HTML / CSV 輸出 |
| `error/` | 異常 CSV 紀錄 |
| `log/` | 網頁控制台執行日誌 |

---

## 五、確認安裝

```cmd
.\venv\Scripts\python.exe -c "import pandas, numpy, scipy, sqlalchemy, bs4, lxml, requests, matplotlib, mplfinance, seaborn, kline, PIL, flask; from dateutil.relativedelta import relativedelta; print('所有核心套件安裝成功')"
```

---

## 六、選用套件（非核心，視需要安裝）

### TA-Lib（技術指標）

Windows 上**無法直接 pip install**，需先裝 C 函式庫：

1. 至 [https://github.com/cgohlke/talib-build/releases](https://github.com/cgohlke/talib-build/releases) 下載對應版本的 `.whl`
   - 例如：`TA_Lib-0.4.32-cp311-cp311-win_amd64.whl`（Python 3.11，64 位元）
2. 安裝：
   ```cmd
   .\venv\Scripts\pip.exe install TA_Lib-0.4.32-cp311-cp311-win_amd64.whl
   ```

> `good_stock.py` 中 `import talib` 已移除，目前可跳過。

### Selenium（自動化下載）

```cmd
pip install selenium
```

需另外安裝瀏覽器驅動：
- Firefox：下載 [geckodriver](https://github.com/mozilla/geckodriver/releases) 並加入 PATH
- Chrome：`pip install webdriver-manager`

### 其他

```cmd
pip install pyecharts        # 互動圖表（all_stock.py）
pip install backtrader       # 回測引擎（backtest.py）
pip install pandas-datareader
```

---

## 七、企業/公司網路 SSL 問題

若 pip 出現 `SSLError: CERTIFICATE_VERIFY_FAILED`，所有 pip 指令加上：

```cmd
--trusted-host pypi.org --trusted-host files.pythonhosted.org
```

範例：
```cmd
pip install flask --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

---

## 八、注意事項

- 所有腳本需在 `D:\gg_stock\` 目錄下執行（`stock_comm.py` 的資料路徑為相對路徑）
- 首次使用建議先下載資料快照（見 `data_sources.md`），省去數小時的歷史回補
- SQLite DB 檔案（`sql/*.db`）會在首次爬取時自動建立
