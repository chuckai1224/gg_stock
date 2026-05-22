# 執行排程手冊 — 何時跑哪支 py、資料寫到哪

> 詳細 API 來源與歷史回補說明見 `data_sources.md`。
> 本文件聚焦在「**操作節奏**」：誰、何時跑、產出什麼。

---

## 一、全貌速查表

| 頻率 | 腳本 | 指令（無日期=今天） | 資料產出 | 寫入位置 |
|------|------|---------------------|----------|----------|
| **每交易日盤後** | `crawl.py` | `python crawl.py` | 個股日K、大盤指數 | `data/stock_data/{id}.csv`<br>`sql/stock_data.db`<br>`sql/tse_exchange_data.db`<br>`sql/otc_exchange_data.db` |
| **每交易日盤後** | `stock_big3.py` | `python stock_big3.py` | 三大法人買賣超 | `sql/stock_big3.db`<br>`csv/stock_big3/json/{date}.json` |
| **每交易日盤後** | `pe_networth_yeild.py` | `python pe_networth_yeild.py` | 本益比 / 淨值比 / 殖利率 | `data/down_pe_networth_yield/tse{date}.csv`<br>`data/down_pe_networth_yield/otc{date}.csv` |
| **每週**（集保更新後，約週四） | `tdcc_get.py` | `python tdcc_get.py` | 集保股權分散（大戶/散戶比例） | `sql/tdcc_dist.db`（每檔一 table） |
| **每月**（10 號後，營收公布） | `revenue.py` | `python revenue.py` | 月營收（含年增率/月增率） | `sql/stock/{id}.db` → `revenue` table |
| **每月** | `director.py` | `python director.py` | 董監事持股餘額 | `data/director/final/{id}.csv` |
| **每季**（財報公布後）| `eps.py` | `python eps.py` | 季損益表 EPS / 毛利 / 營利 / 淨利（**累計值**） | `sql/stock/{id}.db` → `mix_income` table |
| **選股輸出（隨時）** | `gg_stock.py` | `python gg_stock.py fund 20260521`<br>`python gg_stock.py revenue 20260521`<br>`python gg_stock.py director 20260521`<br>`python gg_stock.py pointK 20260521` | 選股排行 HTML + CSV | `final/{method}_good.html`<br>`final/{method}_good_{date}.csv` |

---

## 二、每交易日盤後流程（依序執行）

```bash
DATE=$(date +%Y%m%d)   # 或手動填 20260521

# 1. 股價日K（最重要，其他腳本可能依賴它）
python crawl.py

# 2. 三大法人
python stock_big3.py

# 3. 本益比/淨值比/殖利率
python pe_networth_yeild.py

# 4. 產出當日選股清單
python gg_stock.py fund $DATE
python gg_stock.py revenue $DATE
python gg_stock.py director $DATE
python gg_stock.py pointK $DATE
```

> `gg_stock.py` 無參數也可，預設取今天，但 `comm.get_date()` 讀 `sys.argv[1]`，
> 搭配子命令時需明確帶日期，例如 `python gg_stock.py fund 20260521`。

---

## 三、每月排程（營收公布後，通常每月 10 號後）

```bash
# 月營收（上個月的，自動偵測當月日期 <= 12 才下載上月）
python revenue.py

# 董監持股
python director.py
```

---

## 四、每季排程（財報公布後）

| 季別 | 公布期限 | 建議執行時間 |
|------|----------|-------------|
| Q1（1~3月） | 5/15 前 | 5 月中旬 |
| Q2（4~6月） | 8/14 前 | 8 月中旬 |
| Q3（7~9月） | 11/14 前 | 11 月中旬 |
| Q4（全年） | 3/31 前 | 4 月初 |

```bash
# 季財報（EPS / 毛利率 / 營利率 / 淨利率）
python eps.py
```

寫入 `sql/stock/{id}.db` 的 `mix_income` 表，每季 append 一筆，
`get_stock_season_df()` 相減算出**單季值**，需累積 **8 季以上**分析才完整。

---

## 五、每週排程（集保更新後，約週四）

```bash
python tdcc_get.py
```

TDCC 開放資料每週更新一次（週三收盤後），下載後寫入 `sql/tdcc_dist.db`。
`gen_stock_info()` 用此計算大戶 / 散戶近一週、近一月增減比。

---

## 六、一次性歷史回補（已完成項目）

| 腳本 | 指令 | 說明 | 完成狀態 |
|------|------|------|----------|
| `finmind_backfill.py` | `python finmind_backfill.py` | FinMind 日K 回補 2 年（1975 檔） | ✅ 2026-05-21 完成 |
| `finmind_backfill_fundament.py` | `python finmind_backfill_fundament.py` | FinMind 月營收 + 季財報回補 2 年（8 季） | ⏳ 執行中 |
| `stock_big3.py -d` | `python stock_big3.py -d 20240101 20260519` | 三大法人歷史回補 | 視需要 |
| `pe_networth_yeild.py -d` | `python pe_networth_yeild.py -d 20240101 20260519` | 本益比歷史回補（上市可，上櫃僅最新） | 視需要 |

---

## 七、各選股方法的資料依賴

`gg_stock.py` 的 4 種方法都會呼叫 `gen_stock_info()`，任何一項缺資料只會讓該股跳過，不崩潰。

| 資料 | 讀取位置 | 影響的欄位/評分 |
|------|----------|----------------|
| 日K 股價 | `data/stock_data/{id}.csv` | 收盤價、市值、週K/日K、pointK 判斷 |
| 三大法人 | `sql/stock_big3.db` | 外資/投信/自營商買賣超（最近10日） |
| 集保分散 | `sql/tdcc_dist.db` | 大戶近一月增加比、散戶近一月增加比 |
| 本益比 | `data/down_pe_networth_yield/*.csv` | 本益比、股價淨值比、殖利率 |
| 月營收 | `sql/stock/{id}.db` → `revenue` | 最新單月年增率、月增率、本年累計年增率 |
| 季財報 | `sql/stock/{id}.db` → `mix_income` | 8 季 EPS、毛利率、營利率、淨利率、psr 計算 |
| 董監持股 | `data/director/final/{id}.csv` | 董監持股增減（近 6 月） |

### 各選股方法額外資料

| 方法 | 額外使用 | 資料來源 |
|------|----------|----------|
| `fund` | 投信買賣超股數 | `sql/stock_big3.db` |
| `revenue` | 月營收篩選 | `sql/stock/{id}.db` → `revenue` |
| `director` | 董監買超篩選 | `data/director/final/{id}.csv` |
| `pointK` | 近 122 日收盤、紅K 強度 | `sql/stock_data.db` |

---

## 八、資料深度對選股的影響

| 資料深度不足 | 結果 |
|-------------|------|
| `mix_income` < 5 季 | `psrs/psr三年低`、PEG、三率年增 無法計算（NaN） |
| `mix_income` < 8 季 | `前4~7季EPS` 缺，PEG 計算退化 |
| `revenue` 只有 1 筆 | 月增率、年增率 皆 NaN（評分 0） |
| `tdcc_dist` < 4 週 | 大戶/散戶近一月增加比 NaN |
| `sql/stock_data.db` < 122 日 | `pointK` 方法無法判斷，該股跳過 |

---

## 九、`mix_income` ys 欄位說明

`ys = 民國年 × 4 + (季 − 1)`，例如：

| ys | 民國年/季 | 西元 |
|----|-----------|------|
| 452 | 113Q1 | 2024 Q1 |
| 453 | 113Q2 | 2024 Q2 |
| 454 | 113Q3 | 2024 Q3 |
| 455 | 113Q4 | 2024 Q4 |
| 456 | 114Q1 | 2025 Q1 |
| 460 | 115Q1 | 2026 Q1 |

存的是**累計值**（YTD），`get_stock_season_df()` 用相鄰季相減得出單季值；
Q1（ys%4==0）直接等於單季值。
