# gg_stock 使用者操作手冊

> 從安裝到每日操作，一份文件搞定。

---

## 一、系統是什麼？

**gg_stock** 是一套台股自動選股系統，透過爬取公開資料（股價、三大法人、財報、月營收、董監持股…），對每一檔股票算出一個**總分**，輸出排序後的 HTML 報表。

支援 4 種選股角度：

| 方法 | 選誰進來 | 排序依據 |
|------|----------|----------|
| `fund` | 當日**投信買超**的股票 | 投本比（買超力道） |
| `revenue` | 月營收成長優選 | 總分 |
| `director` | 董監近期**加碼買進**的股票 | 總分 |
| `pointK` | 當日**紅 K 強度**進歷史前 10 名 | 總分 |

---

## 二、首次安裝（Windows）

> 已安裝過可跳到第三節。

### 步驟 1 — 安裝 Python

1. 前往 [https://www.python.org/downloads/](https://www.python.org/downloads/) 下載 **Python 3.11**
2. 執行安裝程式，**務必勾選「Add Python to PATH」**，再按 Install Now
3. 開啟命令提示字元（CMD）確認：
   ```cmd
   python --version
   ```
   顯示 `Python 3.11.x` 即成功。

### 步驟 2 — 建立虛擬環境

```cmd
cd D:\gg_stock
python -m venv venv
```

### 步驟 3 — 安裝套件

```cmd
.\venv\Scripts\pip.exe install python-dateutil pandas numpy scipy sqlalchemy beautifulsoup4 lxml requests matplotlib mplfinance seaborn kline Pillow flask
```

> 企業網路出現 SSL 錯誤時，指令後加：
> `--trusted-host pypi.org --trusted-host files.pythonhosted.org`

### 步驟 4 — 建立必要資料夾

```cmd
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

### 步驟 5 — 確認安裝

```cmd
.\venv\Scripts\python.exe -c "import pandas, numpy, flask, sqlalchemy, requests; print('安裝成功')"
```

---

## 三、首次補齊歷史資料

第一次使用需先補資料，選一種方式：

### 方法 A：下載快照（建議，約 5 分鐘）

參考 `data_sources.md` 開頭的「快速開始」章節，從 Google Drive 下載 `.tar.gz` 解壓即可。

### 方法 B：從頭爬取（需 1~2 天）

```cmd
.\venv\Scripts\python.exe crawl.py -b 20240101 20260522
.\venv\Scripts\python.exe stock_big3.py -d 20240101 20260522
.\venv\Scripts\python.exe finmind_backfill_fundament.py
```

---

## 四、啟動網頁控制台

**雙擊 `start_web.cmd`** — 自動啟動伺服器並開啟瀏覽器，一步完成。

> - 黑色命令視窗**不能關**，關掉後網頁即失效。
> - 若瀏覽器比伺服器早開，重新整理一次即可。
> - 網址：`http://127.0.0.1:5000/online/`

也可用命令列直接執行腳本（適合自動化排程）：

```cmd
.\venv\Scripts\python.exe gg_stock.py fund 20260522
```

---

## 五、每交易日盤後流程

> 盤後（下午 3:30 後）依序執行以下四步，當天選股就完成了。

### 步驟 1 — 抓股價日K

**網頁：** 填入日期（如 `20260522`），點「抓取個股日K」。

**指令：**
```cmd
.\venv\Scripts\python.exe crawl.py
```

### 步驟 2 — 抓三大法人

**網頁：** 點「抓取三大法人」。

**指令：**
```cmd
.\venv\Scripts\python.exe stock_big3.py
```

### 步驟 3 — 抓本益比/淨值比

**網頁：** 點「抓取本益比淨值比」。

**指令：**
```cmd
.\venv\Scripts\python.exe pe_networth_yeild.py
```

### 步驟 4 — 產出選股報表

**網頁：** 填入日期，選擇模式，點「執行選股」。

**指令：**
```cmd
.\venv\Scripts\python.exe gg_stock.py fund     20260522
.\venv\Scripts\python.exe gg_stock.py revenue  20260522
.\venv\Scripts\python.exe gg_stock.py director 20260522
.\venv\Scripts\python.exe gg_stock.py pointK   20260522
```

輸出：`final/fund_good.html`、`final/revenue_good.html`、`final/director_good.html`、`final/pointK_good.html`

---

## 六、每週排程（約週四，集保更新後）

**網頁：** 點「抓取集保股權 (TDCC)」。

**指令：**
```cmd
.\venv\Scripts\python.exe tdcc_get.py
```

---

## 七、每月排程（每月 10 號後）

**網頁：** 點「抓取月營收」和「抓取董監持股」。

**指令：**
```cmd
.\venv\Scripts\python.exe revenue.py
.\venv\Scripts\python.exe director.py
```

---

## 八、每季排程（財報公布後）

| 季別 | 公布期限 | 建議執行時間 |
|------|----------|-------------|
| Q1（1~3月） | 5/15 前 | 5 月中旬 |
| Q2（4~6月） | 8/14 前 | 8 月中旬 |
| Q3（7~9月） | 11/14 前 | 11 月中旬 |
| Q4（全年） | 3/31 前 | 4 月初 |

**網頁：** 填入財報公布後的日期，點「抓取單季盈餘 (EPS)」。系統會自動換算民國年/季。

**指令：**
```cmd
.\venv\Scripts\python.exe eps.py 115 1
```

---

## 九、看懂選股報表

報表在 `final/` 目錄，用瀏覽器開啟 `.html` 檔。

### 評分欄位（總分 = 9 項加總）

| 分數欄位 | 衡量什麼 | 範圍 |
|----------|----------|------|
| 分數:psrs/psr(3)-1 | PSR 相對三年最低（越低估越好） | −2 ~ +2 |
| 分數:淨值比 | 股價淨值比（越低越好） | −2 ~ +2 |
| 分數:psrs | 市值/年營收比（越低越好） | −4 ~ +4 |
| 分數:prr | 市值/研發費用（越低越好） | −2 ~ +2 |
| 分數:毛利率 | 本季毛利率（越高越好） | −2 ~ +2 |
| 分數:營利率年增 | 本季營利率 vs 去年同季 | −2 ~ +2 |
| 分數:營收年增20% | 單月營收年增率 + 累計加速 | −2 ~ +2 |
| 分數:營收月增80% | 單月營收月增率 | −2 ~ +2 |
| 分數:peg | PEG 本益成長比（越低越好） | −2 ~ +2 |

總分實際好股通常落在 **+4 ~ +10**。欄位為 NaN 代表資料不足，不影響其他項。

`fund` 方法以「**投本比**」（投信買超股數／股本）排序，數字越大力道越重。

---

## 十、常見問題

**Q：某些股票欄位是 NaN？**
A：該股缺少對應資料，補跑對應腳本即可，不影響其他股票。

**Q：`fund` 清單是空的？**
A：當天投信未買超任何股票，或當天非交易日。

**Q：網頁日誌出現錯誤？**
A：常見原因：資料庫不存在（先補資料）、網路問題（目標 API 暫停）。

**Q：報表資料很舊？**
A：先確認步驟 1~3 都已執行當天資料，再重跑步驟 4。

---

## 十一、快速參考表

| 頻率 | 要做什麼 | 腳本 |
|------|----------|------|
| 每交易日盤後 | 抓股價 | `crawl.py` |
| 每交易日盤後 | 抓三大法人 | `stock_big3.py` |
| 每交易日盤後 | 抓本益比 | `pe_networth_yeild.py` |
| 每交易日盤後 | 產選股報表 | `gg_stock.py fund/revenue/director/pointK YYYYMMDD` |
| 每週（約週四） | 抓集保分散 | `tdcc_get.py` |
| 每月（10號後） | 抓月營收 | `revenue.py` |
| 每月 | 抓董監持股 | `director.py` |
| 每季（財報後） | 抓季財報 EPS | `eps.py` |
