# 環境安裝說明

## 系統需求

- Python 3.9 ~ 3.11（建議 3.11）
- Windows 10/11 或 Linux

---

## 安裝套件

### 公司/企業網路 SSL 問題

若 pip 出現 `SSLError: CERTIFICATE_VERIFY_FAILED`，需加 `--trusted-host` 參數：

```bash
pip install <套件名> --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

以下所有 `pip install` 指令若有 SSL 問題，請加上此參數。

---

### 核心套件（執行 gg_stock.py 必要）

```bash
pip install python-dateutil pandas numpy scipy sqlalchemy beautifulsoup4 lxml requests matplotlib mplfinance seaborn kline Pillow
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
| `mplfinance` | K 線圖（`candlestick_ohlc`） |
| `seaborn` | 統計視覺化 |
| `kline` | K 線 resample 工具 |
| `Pillow` | 圖片處理（`PIL.Image`） |

---

### TA-Lib（技術指標，`good_stock.py` / `stock_comm.py` 部分功能）

TA-Lib 在 Windows 上**無法直接 pip install**，需先安裝 C 函式庫：

**方法一：用非官方 whl（推薦）**

1. 至 https://github.com/cgohlke/talib-build/releases 下載對應版本的 `.whl`
   - 例如：`TA_Lib-0.4.32-cp311-cp311-win_amd64.whl`（Python 3.11，64位元）
2. 安裝：
   ```bash
   pip install TA_Lib-0.4.32-cp311-cp311-win_amd64.whl
   ```

**方法二：conda**
```bash
conda install -c conda-forge ta-lib
```

> 若不需要技術指標功能，可跳過，相關 `import talib` 在 `good_stock.py` 中已移除。

---

### Selenium（自動化下載，`good_stock.py` / `morning.py`）

```bash
pip install selenium
```

需另外安裝瀏覽器驅動：
- Firefox：下載 [geckodriver](https://github.com/mozilla/geckodriver/releases) 並加入 PATH
- Chrome：`pip install webdriver-manager`

---

### 選用套件（特定功能才需要）

```bash
# pyecharts — 互動圖表（all_stock.py，目前大部分已改為 mplfinance）
pip install pyecharts

# flask — Web API（部分腳本）
pip install flask

# backtrader — 回測引擎（backtest.py）
pip install backtrader

# pdfkit — 輸出 PDF（all_stock.py）
# 需另安裝 wkhtmltopdf：https://wkhtmltopdf.org/downloads.html
pip install pdfkit

# pandas-datareader — 抓取外部金融資料
pip install pandas-datareader

# pygame — 遊戲模式（game.py，非核心）
pip install pygame
```

---

## 建立必要資料夾

首次執行前需建立以下目錄（或直接執行以下指令）：

```bash
mkdir sql data data\stock_data final error out
```

| 資料夾 | 用途 |
|--------|------|
| `sql/` | SQLite 資料庫（股價、三大法人、集保等） |
| `data/stock_data/` | 個股日 K CSV（`{stock_id}.csv`） |
| `data/revenue/` | 月營收資料（爬蟲下載後存放） |
| `data/director/` | 董監事持股資料 |
| `data/down_pe_networth_yield/` | 本益比/淨值比資料 |
| `final/` | 選股結果 HTML / CSV 輸出 |
| `error/` | 異常 CSV 紀錄 |

---

## 一鍵安裝腳本

```bash
pip install python-dateutil pandas numpy scipy sqlalchemy beautifulsoup4 lxml requests matplotlib mplfinance seaborn kline Pillow --trusted-host pypi.org --trusted-host files.pythonhosted.org

mkdir -p sql data/stock_data data/revenue data/director data/down_pe_networth_yield final error out
```

---

## 確認安裝

```bash
python -c "
import pandas, numpy, scipy, sqlalchemy, bs4, lxml, requests
import matplotlib, mplfinance, seaborn, kline, PIL
from dateutil.relativedelta import relativedelta
print('所有核心套件安裝成功')
"
```

---

## 注意事項

- `stock_comm.py` 的 `datafolder()` 在 Windows 上回傳 `'data'`（相對路徑），執行時需在 `D:\gg_stock\` 目錄下執行
- 系統需先執行各爬蟲腳本（`revenue.py`、`stock_big3.py`、`tdcc_dist.py` 等）下載資料後，`gg_stock.py` 才能產生有效選股結果
- SQLite DB 檔案（`sql/*.db`）會在首次執行時自動建立
