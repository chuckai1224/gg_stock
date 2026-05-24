# 資料來源與歷史資料取得

> 本文件記錄 `gg_stock.py` 各資料來源、如何下載/建庫、以及**如何取得歷史資料**。
> 2026-05 將所有失效的舊網址改接證交所 / 櫃買中心 / 集保的開放資料 API 後整理。

---

## 🚀 快速開始：直接下載資料快照

**不想花 10+ 小時自己跑回補腳本?** 下載已備好的資料快照,解壓即可使用。

### 📦 下載連結

> [**gg_stock_data_20260524.tar.gz**](https://drive.google.com/file/d/1cR1XEHJoLpbATuGrT8bgE2rnVf12kjiA/view?usp=drive_link) (35 MB，解壓後請自行確認)

包含內容:

| 路徑 | 內容 | 大小 |
|------|------|------|
| `sql/stock/*.db` | 1966 檔個股 mix_income + revenue (FinMind 已回補 8 季 + 24 月) | 24 MB |
| `sql/stock_data.db` | 上市股價(到 2026-05-22) | 8 MB |
| `sql/otc_exchange_data.db` | 上櫃股價 | 22 MB |
| `sql/stock_big3.db` | 三大法人 | 2.5 MB |
| `sql/tdcc_dist.db` | 集保股權分散 | 30 MB |
| `data/stock_data/*.csv` | 個股日K CSV | ~89 MB |
| `data/down_pe_networth_yield/` | 本益比/淨值比 | (內含) |
| `data/director/final/` | 董監持股 | (內含) |

### 🛠 解壓步驟

1. **下載檔案**:點上方連結 → Google Drive 右上角下載圖示

2. **clone repo** (如還沒):
   ```bash
   git clone git@github.com:chuckai1224/gg_stock.git
   cd gg_stock
   ```

3. **把 tar.gz 放到 repo 根目錄**(和 `gg_stock.py` 同層)

4. **解壓**:
   ```bash
   # Linux / macOS / WSL
   tar -xzf gg_stock_data_20260524.tar.gz

   # Windows PowerShell (內建 tar,Win10+)
   tar -xzf gg_stock_data_20260524.tar.gz

   # Windows 7-Zip / WinRAR 也支援
   ```

5. **驗證**:
   ```bash
   ls sql/stock | wc -l       # 應顯示 1966
   ls data/stock_data | wc -l # 應顯示 ~2000
   ```

6. **直接跑選股**:
   ```bash
   python gg_stock.py fund 20260522
   python gg_stock.py revenue 20260522
   python gg_stock.py director 20260522
   python gg_stock.py pointK 20260522
   ```

### ⚠️ 注意事項

- 解壓**會直接覆寫**現有的 `sql/` 和 `data/` 目錄,使用前先備份(如有需要)
- 快照日期為 **2026-05-24**,之後的每日新資料仍須執行 `crawl.py` / `stock_big3.py` / `pe_networth_yeild.py` 累積(見[第六節](#六建議的定期排程cron))
- `*.tar.gz` 已在 `.gitignore` 中,不會被 git 追蹤

### 🔧 更新快照（給維護者）

當資料累積到值得重新發布時,執行以下流程：

```cmd
:: 步驟 1：打包（生成 gg_stock_data_YYYYMMDD.tar.gz，約 1~2 分鐘）
.\venv\Scripts\python.exe make_snapshot.py

:: 步驟 2：手動上傳 .tar.gz 到 Google Drive
::   上傳後開啟「取得連結」，從 URL 複製 file_id
::   格式：https://drive.google.com/file/d/<file_id>/view

:: 步驟 3：自動更新 download_snapshot.py 與本文件的連結
.\venv\Scripts\python.exe make_snapshot.py --update <file_id>

:: 步驟 4：提交
git add download_snapshot.py data_sources.md
git commit -m "snapshot: update to YYYYMMDD"
git push
```

---

## 一、資料流總覽

```
各下載腳本 ──> 開放資料 API ──> 本機 SQLite / CSV ──> gg_stock.py 讀取選股
```

`gg_stock.py` 的 4 個選股方法都會呼叫 `gen_stock_info()`,後者需要以下所有資料。
缺哪一項,該檔個股就會被跳過或欄位留白。

---

## 二、各資料來源一覽

| 資料項目 | 下載腳本 | 來源 API | 可指定日期 | 輸出位置 |
|----------|----------|----------|:----------:|----------|
| 個股股價(日K) | `crawl.py` | TWSE `rwd/zh/afterTrading/MI_INDEX`<br>TPEX `afterTrading/dailyQuotes` | ✅ | `data/stock_data/*.csv`<br>`sql/stock_data.db`<br>`sql/{tse,otc}_exchange_data.db` |
| 三大法人(投信買超) | `stock_big3.py` | TWSE `rwd/zh/fund/T86`<br>TPEX `insti/dailyTrade` | ✅ | `sql/stock_big3.db` |
| 集保股權分散(TDCC) | `tdcc_dist.py` | TDCC `opendata/getOD.ashx?id=1-5` | ❌ 僅最新一週 | `sql/tdcc_dist.db` |
| 本益比/淨值比/殖利率 | `pe_networth_yeild.py` | 上市 TWSE `rwd/.../BWIBBU_d`<br>上櫃 TPEX `openapi/.../peratio` | ⚠️ 上市可,上櫃僅最新 | `data/down_pe_networth_yield/*.csv` |
| 月營收 | `revenue.py` | TWSE/TPEX `openapi .../t187ap05` | ❌ 僅最新一月 | `sql/income.db`<br>`sql/stock/*.db`(`revenue` 表) |
| 季財報/EPS | `eps.py` | TWSE/TPEX `openapi .../t187ap06_*_ci` | ❌ 僅最新一季 | `sql/stock/*.db`(`mix_income` 表) |
| 董監持股 | `director.py` | TWSE/TPEX `openapi .../t187ap11` | ❌ 僅最新一月 | `data/director/final/*.csv` |

---

## 三、可回補歷史 vs 僅能往前累積

開放資料 API 分兩種:

### A. 可指定日期 → 能回補任意歷史

| 資料 | 回補指令 |
|------|----------|
| 股價 | `python crawl.py YYYY MM DD`(逐日);或 `python crawl.py -b YYYY MM DD`(快速回補) |
| 投信買超 | `python stock_big3.py -d 起始日 結束日`(例:`-d 20240101 20260519`) |
| 本益比(**上市**) | `python pe_networth_yeild.py -d 起始日 結束日` |

### B. 僅提供「最新一期」→ 無法回補,只能往前累積

TDCC、月營收、季財報、董監持股、上櫃本益比 —— 官方開放資料只給**當前最新一筆**。
**沒有辦法把過去的補回來**,只能從現在開始定期執行,讓資料庫逐月/逐季累積:

- `sql/income.db`、`mix_income` 表、`director/final/` 都是「**append 累積**」設計
- 例如季財報每跑一次 `eps.py` 就多存一季,跑滿 8 次(約 2 年)才有完整 8 季可分析

> 若要回補這幾項的歷史,可改用第三方資料庫 **FinMind**(免費版能補月營收、
> 財報等,但**沒有**集保股權分散與董監持股)—— 評估詳見第七節。

---

## 四、回補歷史的實際操作

### 1. 股價(最重要,`pointK` 與 K 線欄位都靠它)

```bash
# 方式一:完整回補(含 sql/stock_data.db,pointK 需要)— 逐交易日,較慢
python crawl.py 2026 5 19      # 跑單日:下載 + exchange2sql + insert_daily_stock_data
#  ↑ 對每個要回補的交易日各跑一次

# 方式二:快速回補(只建 data/stock_data/*.csv,夠畫 K 線 / gen_stock_info 的 kline 欄位)
python crawl.py -b 2026 5 19   # 從指定日往回一路補到 2010-01-01(只做 get_data)
```

- `pointK` 方法的 `check_point_K` 需要近 122 個交易日、且讀 `sql/stock_data.db`
  → 必須用**方式一**逐日補滿約半年。
- `fund`/`revenue` 輸出裡的週K/日K 欄位讀 `data/stock_data/*.csv`
  → **方式二** `-b` 即可。
- **K線只需抓「日K」**:週K、月K 不另外下載,`kline.resample()` 會即時從日K換算;
  日K 回補得夠長(週K 取 60 根約需 300 個交易日),週K/月K 自然就有。

### 2. 投信買超(回補)

```bash
python stock_big3.py -d 20240101 20260519
```
逐日下載 T86 / dailyTrade,寫入 `sql/stock_big3.db`(每日一張表)。已存在的日期會自動略過。

### 3. 本益比(上市可回補,上櫃只有最新)

```bash
python pe_networth_yeild.py -d 20240101 20260519
```
上市 `tseYYYYMMDD.csv` 會是各日正確資料;上櫃 `otcYYYYMMDD.csv` 因 API 限制
一律寫入「最新一日」內容(檔名仍照查詢日期)。

---

## 五、各選股方法需要的資料深度

| 方法 | 需要的歷史深度 | 現況 |
|------|----------------|------|
| `fund` 投信買超 | 單一快照即可 | ✅ 可直接產出 |
| `revenue` 月營收 | 需 **2 個月**月營收(算月增減) | 累積 2 個月後產出 |
| `director` 董監持股 | 需 **2 個月**董監資料(算持股增減) | 累積 2 個月後產出 |
| `pointK` 紅K轉強 | 需 **約 122 個交易日**股價 | 回補股價後可用 |
| 季財報三率/EPS 評分 | 需 **約 8 季**(2 年) | 每季累積 |

> `fund` 之外的方法,資料深度不夠時會「優雅地回空、不崩潰」,不會產生 `final/xxx_good.html`。

---

## 六、建議的定期排程(cron)

開放資料是「最新快照」,要長期使用就靠定時累積:

| 頻率 | 指令 | 說明 |
|------|------|------|
| 每交易日盤後 | `python crawl.py <今天>` | 股價 |
| 每交易日盤後 | `python stock_big3.py`(無參數=今天) | 投信買超 |
| 每交易日盤後 | `python pe_networth_yeild.py` | 本益比 |
| 每週(集保更新後) | `python tdcc_dist.py` | TDCC 股權分散 |
| 每月(營收公布後,約 10 號) | `python revenue.py` | 月營收 |
| 每月 | `python director.py` | 董監持股 |
| 每季(財報公布後) | `python eps.py -d <今天> <今天>` | 季財報 |

跑完上述後再執行 `python gg_stock.py gg`(或無參數)即可產生 4 種選股清單。

---

## 七、FinMind 免費版評估(作為歷史資料源)

[FinMind](https://finmindtrade.com/) 是開源台股資料庫,提供**真歷史**資料
(不像官方開放資料只有最新一期)。2026-05 實測免費版(匿名、未帶 token):

### 免費版可取得(真歷史、可指定日期區間,需逐檔查詢)

| gg_stock 需求 | FinMind dataset |
|---------------|-----------------|
| 日K 股價 | `taiwan_stock_daily` |
| 三大法人(投信買超) | `taiwan_stock_institutional_investors` |
| 月營收 | `taiwan_stock_month_revenue` |
| 季財報(綜合損益表) | `taiwan_stock_financial_statement` |
| 本益比/淨值比/殖利率 | `taiwan_stock_per_pbr` |

### 免費版不能取得

| 項目 | 狀況 |
|------|------|
| 集保股權分散 | `taiwan_stock_holding_shares_per` → 需付費升級 |
| 依「日期」查全市場 | 需付費 → 免費版只能逐檔(帶 `stock_id`)查 |
| 董監持股餘額 | FinMind 無此 dataset |

### 限流與回補成本

- 免費版按小時計(官方約 300–600 requests/hr)
- 只能逐檔查 → 回補全市場 ≈ 2000 檔 × 5 種 dataset ≈ **10,000 requests**
- → 一次性回補約 **17–33 小時**(可背景分批跑);之後每日增量很少

### 結論:建議「混合架構」,不要當唯一資料源

| 用途 | 建議來源 |
|------|----------|
| 每日更新 | 證交所/櫃買開放資料 API(免費、不限流、一次抓全市場)|
| 歷史回補(日K/三大法人/月營收/財報/本益比) | FinMind 免費版逐檔補 |
| 集保股權分散 | TDCC 開放資料(往前累積)或付費 |
| 董監持股 | TWSE `t187ap11`(往前累積) |

> FinMind 很適合**一次性回補歷史**(補開放資料給不了的過去),
> 但因限流 + 逐檔查 + 缺集保/董監,不適合當每日主力。

安裝與用法:

```bash
pip install FinMind tqdm
```
```python
from FinMind.data import DataLoader
dl = DataLoader()
df = dl.taiwan_stock_daily(stock_id='2330',
                           start_date='2024-05-20', end_date='2026-05-20')
```

---

## 八、本次修復記錄(2026-05)

原本所有下載腳本都接已失效的舊網址,`gg_stock.py` 完全跑不動。修復後改接開放資料 API:

| Commit | 修復內容 |
|--------|----------|
| `f4d21da` | 投信買超 `stock_big3.py` → TWSE T86 / TPEX dailyTrade JSON |
| `bec439e` | 集保股權分散 `tdcc_dist.py` → TDCC 開放資料(並改抓 1~15 持股分級) |
| `869d896` | `np.NaN` → `np.nan`(NumPy 2.0 已移除);`get_market_value` 加固 |
| `8074bfb` | 股價 `crawl.py` → TWSE MI_INDEX / TPEX dailyQuotes;`datafolder()` 修正 |
| `e4e8e3a` | 本益比 `pe_networth_yeild.py` → TWSE BWIBBU_d / TPEX 開放資料 |
| `65944c1` | 月營收 `revenue.py` → TWSE/TPEX `t187ap05` 開放資料 |
| `7816112` | 季財報 `eps.py` → `t187ap06` 開放資料;薄資料防呆 |
| `0bd6f15` | revenue 數值型別修正;董監 `director.py` → `t187ap11` 開放資料 |

共同問題:
- 舊網址失效(TWSE/TPEX 改版、MOPS 擋爬蟲)→ 全面改開放資料 API
- SQLAlchemy 2.0 移除 `engine.table_names()` → 改 `inspect().get_table_names()`
- NumPy 2.0 移除 `np.NaN` → `np.nan`
- 開放資料多為「最新快照」→ 程式加防呆,薄資料不崩潰(見第五節)
