# gg_stock 使用者操作手冊

> 適合對象：不需了解程式細節，只想「每天操作、看結果」的使用者。

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

## 二、兩種操作方式

### 方式 A：網頁控制台（建議）

啟動後用瀏覽器操作，不需打指令。

```
.\venv\Scripts\python.exe online.py
```

開啟瀏覽器：`http://127.0.0.1:5000/online/`

### 方式 B：命令列

直接在終端機執行 Python 腳本（適合排程自動化）。

```powershell
.\venv\Scripts\python.exe gg_stock.py fund 20260522
```

---

## 三、每交易日盤後流程

> 盤後（下午 3:30 後）依序執行以下四步，當天選股就完成了。

### 步驟 1 — 抓股價日K

**網頁：** 在「每日盤後數據爬取」區塊，填入日期（如 `20260522`），點「抓取個股日K」。

**指令：**
```powershell
.\venv\Scripts\python.exe crawl.py
```

寫入：`data/stock_data/{股號}.csv`、`sql/stock_data.db`

---

### 步驟 2 — 抓三大法人

**網頁：** 點「抓取三大法人」。

**指令：**
```powershell
.\venv\Scripts\python.exe stock_big3.py
```

寫入：`sql/stock_big3.db`

---

### 步驟 3 — 抓本益比/淨值比

**網頁：** 點「抓取本益比淨值比」。

**指令：**
```powershell
.\venv\Scripts\python.exe pe_networth_yeild.py
```

寫入：`data/down_pe_networth_yield/tse{日期}.csv`

---

### 步驟 4 — 產出選股報表

**網頁：** 在「執行選股腳本」區塊，填入日期，選擇模式（fund / revenue / director / pointK），點「執行選股」。

**指令（4 種都跑）：**
```powershell
.\venv\Scripts\python.exe gg_stock.py fund     20260522
.\venv\Scripts\python.exe gg_stock.py revenue  20260522
.\venv\Scripts\python.exe gg_stock.py director 20260522
.\venv\Scripts\python.exe gg_stock.py pointK   20260522
```

輸出：`final/fund_good.html`、`final/revenue_good.html`、`final/director_good.html`、`final/pointK_good.html`

---

## 四、每週排程（約週四，集保更新後）

**網頁：** 在「特定指標數據爬取」點「抓取集保股權 (TDCC)」。

**指令：**
```powershell
.\venv\Scripts\python.exe tdcc_get.py
```

寫入：`sql/tdcc_dist.db`（大戶 / 散戶持股比例）

---

## 五、每月排程（每月 10 號後，月營收公布後）

**網頁：** 點「抓取月營收」和「抓取董監持股」。

**指令：**
```powershell
.\venv\Scripts\python.exe revenue.py    # 月營收
.\venv\Scripts\python.exe director.py  # 董監持股
```

寫入：
- `sql/stock/{股號}.db` → `revenue` table
- `data/director/final/{股號}.csv`

---

## 六、每季排程（財報公布後）

| 季別 | 公布期限 | 建議執行時間 |
|------|----------|-------------|
| Q1（1~3月） | 5/15 前 | 5 月中旬 |
| Q2（4~6月） | 8/14 前 | 8 月中旬 |
| Q3（7~9月） | 11/14 前 | 11 月中旬 |
| Q4（全年） | 3/31 前 | 4 月初 |

**網頁：** 填入財報公布後的日期，點「抓取單季盈餘 (EPS)」。系統會自動換算為對應的民國年/季。

**指令：**
```powershell
.\venv\Scripts\python.exe eps.py 115 1   # 民國115年Q1（2026 Q1）
```

寫入：`sql/stock/{股號}.db` → `mix_income` table

---

## 七、看懂選股報表

報表輸出在 `final/` 目錄，用瀏覽器開啟 `.html` 檔即可。

### 評分欄位說明（總分 = 9 項加總）

| 分數欄位 | 衡量什麼 | 滿分/最低分 |
|----------|----------|-------------|
| 分數:psrs/psr(3)-1 | PSR 相對三年最低的位置（越低估越好） | +2 / −2 |
| 分數:淨值比 | 股價淨值比（越低越好） | +2 / −2 |
| 分數:psrs | 市值/年營收比（越低越好） | +4 / −4 |
| 分數:prr | 市值/研發費用（越低越好，越重視研發） | +2 / −2 |
| 分數:毛利率 | 本季毛利率（越高越好） | +2 / −2 |
| 分數:營利率年增 | 本季營利率 vs 去年同季（向上加分） | +2 / −2 |
| 分數:營收年增20% | 單月營收年增率 + 累計年增加速 | +2 / −2 |
| 分數:營收月增80% | 單月營收月增率 | +2 / −2 |
| 分數:peg | PEG 本益成長比（越低越好） | +2 / −2 |

**總分理論最大值：+20（psrs 最大 +4）**。
實際好股通常落在 **+4 ~ +10**。分數為 NaN 代表該項資料不足，不影響其他項計算。

### fund 方法特殊欄位

`fund` 方法以「**投本比**」排序（= 投信買超股數 / 股本），數字越大代表投信買超力道相對股本越重。總分僅供參考。

---

## 八、一次性資料補齊（新環境必做）

第一次在新機器使用，需先補齊歷史資料（或直接下載快照）。

### 方法 A：下載資料快照（最快，約 5 分鐘）

參考 `data_sources.md` 開頭的「快速開始」章節，從 Google Drive 下載 `.tar.gz` 解壓即可。

### 方法 B：從頭爬取（需 1~2 天）

```powershell
# 股價日K（最重要）
.\venv\Scripts\python.exe crawl.py -b 20240101 20260522

# 三大法人歷史
.\venv\Scripts\python.exe stock_big3.py -d 20240101 20260522

# 季財報（需逐季手動或跑 FinMind 回補腳本）
.\venv\Scripts\python.exe finmind_backfill_fundament.py
```

---

## 九、常見問題

**Q：選股結果某些股票欄位是 NaN？**
A：該股缺少對應資料（例如 `mix_income` 不足 5 季），不影響其他股票。缺哪種資料補跑對應腳本即可。

**Q：`fund` 方法跑出來清單是空的？**
A：當天投信沒有買超任何股票，或當天非交易日（假日、停市）。

**Q：網頁執行日誌出現錯誤？**
A：查看右側終端日誌的完整訊息。常見原因：資料庫不存在（需先補資料）、網路問題（目標 API 暫停）。

**Q：報表看起來很舊？**
A：確認步驟 1~3（抓股價、三大法人、本益比）都已執行當天資料後，再重新執行步驟 4。

---

## 十、快速參考表

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
