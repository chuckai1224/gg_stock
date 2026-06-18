# gg_stock.py 程式邏輯與流程說明

## 一、用途總覽

`gg_stock.py` 是一支**台股選股 / 評分工具**。它依照不同的「選股入口」(method) 先篩出候選清單,
再為每一檔股票蒐集基本面、籌碼面、技術面資料,計算一個 **9 項加總的「總分」**,
最後輸出排序後的 HTML 與 CSV 報表。

支援 4 種選股入口:

| method     | 候選來源                                   | 排序依據 |
|------------|--------------------------------------------|----------|
| `pointK`   | 當日「紅 K 強度」進前 10 名的個股           | 總分     |
| `revenue`  | 月營收成長優選清單 (`revenue` 模組)         | 總分     |
| `director` | 董監持股變動優選清單 (`director` 模組)      | 總分     |
| `fund`     | 投信買超的個股                              | 投本比   |

---

## 二、外部相依模組

| 模組                         | 角色 |
|------------------------------|------|
| `pandas` / `numpy`           | 資料處理 |
| `datetime` / `dateutil`      | 日期運算 |
| `kline`                      | K 線重新取樣 (日 → 週) |
| `stock_comm` (別名 `comm`)   | 共用資料存取層:股價、股本、本益比、營收、財報、股權分散… |
| `stock_big3`                 | 三大法人買賣超資料 |
| `revenue`                    | 月營收選股清單 |
| `director`                   | 董監持股選股清單與董監持股明細 |
| `seaborn` / `matplotlib`     | 繪圖樣式 / 中文字型設定 |

---

## 三、程式進入點與主流程 (`__main__`)

```
啟動
 │
 ├─ 設定 seaborn 樣式 + matplotlib 中文字型 (simhei)
 │
 ├─ 解析命令列參數 sys.argv
 │   ├─ 無參數            → 4 種 method 全跑 (pointK, revenue, director, fund)
 │   ├─ "gg"  [date] [rev]→ 4 種 method 全跑
 │   ├─ "director" [...]  → 只跑 director
 │   ├─ "fund" [...]      → 只跑 fund
 │   └─ "revenue" [...]   → 只跑 revenue
 │
 ├─ nowdate  : 第 2 個參數 (YYYYMMDD),失敗則用 comm.get_date()
 ├─ rev_date : 第 3 個參數 (YYYYMMDD),失敗則用 nowdate 往前推 1 個月
 │
 └─ 呼叫 gen_gg_buy_list(nowdate, rev_date, method)
```

執行方式範例:

```bash
python gg_stock.py                       # 全部 method,日期自動
python gg_stock.py gg 20260520            # 全部 method,指定日期
python gg_stock.py fund 20260520 20260430 # 只跑 fund
```

---

## 四、核心流程:`gen_gg_buy_list(date, rev_date, method)`

這是整支程式的主控函式。

```
gen_gg_buy_list(date, rev_date, method)
 │
 ① 依 method 取得候選清單 d1
 │     revenue  → revenue.gen_revenue_good_list(rev_date)
 │     pointK   → gen_pointK_list(date)
 │     fund     → gen_fund_ratio_list(date)
 │     其他      → director.gen_director_good_list(rev_date)
 │     (空清單 → 直接 return)
 │
 ② 補上 date 欄;以 get_market_value 算出 [收盤價, 股本, 市值]
 │
 ③ 市值過濾
 │     市值 >= 3000 (百萬)            ← 共用門檻
 │     fund 以外:市值 <= 15000        ← 排除過大型股
 │
 ④ 逐檔處理 (for 迴圈)
 │     ├─ 股號開頭為 25/28/55/58 → 跳過 (金融/保險類)
 │     ├─ d = gen_stock_info(該檔)   ← 蒐集所有資料 + 評分
 │     ├─ d 為空 → 跳過
 │     └─ fund:額外計算「投本比」= 投信買賣超股數 / (股本 × 100000)
 │
 ⑤ 全部結果 concat 成 out
 │
 ⑥ 排序
 │     fund 以外 → 依「總分」由大到小
 │     fund     → 依「投本比」由大到小,並把該欄移到第 16 欄
 │
 └─ ⑦ 輸出到 final/ 目錄
        final/{method}_good.html
        final/{method}_good_{YYYYMMDD}.csv
```

---

## 五、候選清單產生器

### `gen_pointK_list(date)` — 紅 K 強度選股
1. 取當日所有上市櫃個股 `comm.get_tse_otc_stock_df_by_date`。
2. `check_skip_stock` 過濾:股號需 4 碼、排除 `00*`/`25*`/`28*`/`55*`/`58*`、成交金額需 ≥ 300 萬。
3. `check_point_K` 判斷:取近 122 日資料 (需 ≥ 90 筆),計算每日 `red_K_ratio`,
   若最新一日的紅 K 強度 ≥ 歷史第 10 高 → 標記 `point_K = 1`。
4. 回傳 `point_K >= 1` 的個股。

> `red_K_ratio_calc`:開盤價高於昨收 → `(收 − 昨收)/昨收`;否則 → `(收 − 開)/昨收`。

### `gen_fund_ratio_list(date)` — 投信買超選股
1. 取當日三大法人資料 `stock_big3.get_stock_big3_date_df`。
2. 過濾:股號 4 碼、排除 `00*`、且「投信買賣超股數 > 0」。
3. 回傳 `stock_id / stock_name / 投信買賣超股數 / date / market`。

### `revenue` / `director`
直接呼叫對應模組的 `gen_revenue_good_list` / `gen_director_good_list`。

---

## 六、單一個股資料蒐集:`gen_stock_info(r)`

針對一檔股票建立一個單列 DataFrame `d`(欄位由 `cols` 清單定義,涵蓋約 100 欄),
依序填入各面向資料:

```
gen_stock_info(r)
 │
 ├─ 基本:date / stock_id / stock_name / market(tse 或 otc)
 ├─ 收盤價、股數(萬張)、市值(百萬) = 收盤價 × 股數 × 10
 │
 ├─ get_stock_director(d)            董監持股 (前 0~5 月、增減、日期明細)
 ├─ get_stock_tdcc_dist(d)           股權分散 → 大戶/散戶持股比、近周/近月增加比
 ├─ get_stock_pe_networth_yield(d)   本益比、股價淨值比、殖利率、股利年度
 │       └─ 取不到資料 → 回傳空 DataFrame (該檔放棄)
 ├─ get_stock_industry_status(d)     產業 / 細產業 / 產業地位
 ├─ get_stock_revenue(d)             本年累計營收年增率、最新單月年增率（已移至 psrS 前並於前端折行美化）、月增率、備註，以及近 12 個月營收金額與 YoY 資料字串（用於 Modal 趨勢圖）
 ├─ get_stock_season_composite_income_sheet(d)
 │       3 年 EPS/營收、psrS、psr 三年高低、近 8 季三率與升降
 │       └─ 取不到資料 → 回傳空 DataFrame (該檔放棄)
 ├─ get_stock_prr(d)                 prr = 市值 / 研發費用
 │
 ├─ 計算 9 項分數 (見第七節),總分 = 9 項加總
 │
 ├─ 近 300 日股價 → 週 K (kline.resample 'W-FRI', 60 根)
 │       週 K 需 >= 60 根才填入,否則留空
 ├─ 近 60 日日 K
 ├─ stock_big3.get_stock_3big  近 10 筆外資/投信/自營商買賣超
 │
 └─ 回傳依 cols 排序好的單列 DataFrame d
```

---

## 七、評分系統(總分 = 9 項相加)

`gen_stock_info` 會呼叫 9 個 `*_score` 函式,各自輸出一個分數,加總成「總分」。

| 分數欄位            | 函式                                | 衡量重點 | 分數區間 |
|---------------------|-------------------------------------|----------|----------|
| 分數:psrs/psr(3)-1  | `get_psrs_div_psr3y_score`          | psrS 相對三年最低 PSR 的位置 | −2 ~ +2 |
| 分數:淨值比         | `get_networth_score`                | 股價淨值比越低越好 | ≤ +? ~ −2 |
| 分數:psrs           | `get_psrs_score`                    | 市值/營收比 (PSR),越低越好 | −4 ~ +4 |
| 分數:prr            | `get_prr_score`                     | 市值/研發費用比,越低越好 | −2 ~ +2 |
| 分數:毛利率         | `get_Gross_margin_score`            | 本季毛利率越高越好 | −2 ~ +2 |
| 分數:營利率年增     | `get_Operating_Profit_margin_score` | 本季 vs 前 4 季營利率變化 | −2 ~ +2 |
| 分數:營收年增20%    | `get_revenue_year_20_score`         | 單月營收年增率 + 累計年增加速 | −2 ~ +2 |
| 分數:營收月增80%    | `get_revenue_month_80_score`        | 單月營收月增率 | −2 ~ +2 |
| 分數:peg            | `get_peg_score`                     | PEG (本益成長比),越低越好 | −2 ~ +2 |

### 評分邏輯細節

- **psrs/psr(3)-1**:`x = psrs/psr三年最低-1`,分數 `= (0.2 − x) × 2`,夾限 ±2。
- **淨值比**:`x ≥ 3.3 → −2`;`1.3 ≤ x < 3.3 → 1.3 − x`;`x < 1.3 → (1.3 − x) × 2`。
- **psrs**:`psrs ≥ 3 → −4`;否則 `(1.5 − psrs)/0.375`,夾限 ±4。
- **prr**:`prr ≥ 15 或 ≤ 0 → −2`;否則 `(15 − prr)/7.5`。
- **毛利率**:`< 10 → −2`;`≥ 60 → +2`;否則 `(x − 30)/15`。
- **營利率年增**:`x = 本季營利率 − 前4季營利率`,分數 `= x/2.5`,夾限 ±2。
- **營收年增20%**:結合單月年增率 (`x`) 與「累計年增率 − 去年營收年增率」(`w`),
  `y = (x×100 − 10)×0.025 + w×0.25`,夾限 ±2。
- **營收月增80%**:`月增率 > 0.8 → +2`;`< −0.8 → −2`;否則 `月增率 × 2.5`。
- **peg**:由近 8 季 EPS 推估「今年 EPS」與「去年 EPS」算出成長率與 PEG;
  `peg > 1.34 → −2`;`peg < 0.66 → +2`;否則 `(1 − peg) × 2/0.34`。

> 設計理念:偏好**低估值**(低 PSR / 低 PEG / 低淨值比)、**高成長**(營收與三率向上)的個股。

---

## 八、輔助函式索引

| 函式 | 說明 |
|------|------|
| `lno()` | 回傳「檔名-L(行號)」字串,供 debug 列印定位 |
| `check_dst_folder(path)` | 目錄不存在則建立 |
| `time642str(x)` / `date2str(x)` | 日期轉 `yy-mm-dd` 字串 |
| `get_market_value(r)` | 回傳 (收盤價, 股數萬張, 市值百萬) |
| `get_stock_market(r)` | 判斷個股屬 `tse` 或 `otc` |
| `check_skip_stock(r)` | pointK 用的個股過濾條件 |
| `red_K_ratio_calc(r)` | 計算單日紅 K 強度 |
| `check_point_K(r)` | 判斷最新紅 K 是否進歷史前 10 強 |
| `get_gg_income_ratio(r)` | (未被主流程使用) 月營收年增率連續轉強的篩選 |
| `get_director_change(r)` | (未被主流程使用) 近 6 月董監持股增減總和 |
| `get_stock_psrS(r)` | (未被主流程使用) 以最近一年營收估算 PSR |

> 註:`get_gg_income_ratio` / `get_director_change` / `get_stock_psrS` 目前在主流程中未被呼叫,
> 屬於保留或實驗性函式。

---

## 九、輸入 / 輸出

**輸入**:透過 `stock_comm` / `stock_big3` / `revenue` / `director` 模組存取的本地股市資料庫
(股價、股本、財報、月營收、董監持股、股權分散、三大法人)。

**輸出**(寫入 `final/` 目錄):

| 檔案 | 內容 |
|------|------|
| `final/{method}_good.html` | 排序後的選股結果,HTML 表格(含 K 線等字串欄位) |
| `final/{method}_good_{YYYYMMDD}.csv` | 同上的 CSV(UTF-8) |

錯誤資料另存於 `error/{stock_id}_revenue.csv`。

---

### 網頁前端顯示優化 (HTML)
- **長欄位表頭自動折行**：為維持排版整齊，前端 JavaScript 載入時會自動將「最新單月營收年增率」、「大戶近一月增加比」、「投信增減」、「外資增減」、「董監持股增減」等較長表頭欄位拆分成兩行。
- **欄位位置與美化**：「最新單月營收年增率」已被移至 `psrS` 之前，方便對比估值，並在前端以紅（正成長）綠（負成長）膠囊框高亮呈現。
- **個股月營收趨勢圖**：當使用者點擊個股的「K線圖」時，詳細彈窗 (Modal) 會載入隱藏的近 12 個月營收與年增率 YoY 資料，並使用 ApexCharts 渲染出直條+折線雙軸趨勢圖，與單季 EPS、歷季三率等共同構成 2x4 的完整對稱版面。

---

## 十、整體資料流圖

```
命令列參數
   │
   ▼
gen_gg_buy_list(date, rev_date, method)
   │
   ├── 候選清單 ── revenue / pointK / fund / director
   │
   ├── get_market_value → 市值過濾 (3000 ~ 15000 百萬)
   │
   ├── 逐檔 gen_stock_info()
   │      ├─ 董監持股 / 股權分散 / 本益比淨值比殖利率
   │      ├─ 產業地位 / 月營收 / 季財報三率 / prr
   │      ├─ 9 項評分 → 總分
   │      └─ 週K / 日K / 三大法人
   │
   ├── concat → 依 總分(或投本比) 排序
   │
   ▼
final/{method}_good.html  +  final/{method}_good_{date}.csv
```
