# bat/ 更新腳本說明

三個批次檔對應三種更新頻率，都可以直接雙擊或在終端機執行，
內部自動切到 repo 根目錄並使用 `venv\Scripts\python.exe`，不需先 activate。

## day_update.bat — 每日更新（收盤後 ~16:00）

包一層 `daily_update.ps1`，依序執行：
`crawl.py` → `revenue.py` → `stock_big3.py` → `pe_networth_yeild.py` → `gg_stock.py`
→ 複製 `final/chip_fund_good.html` 到 `D:\to_google` → `git_push.ps1` 推 repo。

```bat
bat\day_update.bat              :: 更新今天
bat\day_update.bat 20260708     :: 補跑指定日期 (YYYYMMDD)
```

- log 寫在 `logs\daily_YYYYMMDD.log`。
- 補跑歷史日期時各腳本會帶 `-d` 參數抓該日資料，遇到假日基本上是空跑。

## week_update.bat — 每週更新（TDCC 集保戶股權分散）

執行 `tdcc_get.py`：從 TDCC 開放資料 (`opendata.tdcc.com.tw` id=1-5)
下載當週檔案，寫入 `sql/tdcc_dist.db`（每檔股票一張表）。

```bat
bat\week_update.bat             :: 無參數
```

- 資料日期＝每週五；TDCC 通常**週六或下週一**才換新檔。
- 已存在的日期會自動跳過，資料還沒換檔時重跑無害（顯示 `0 stocks`），晚點再跑即可。
- 執行完可看輸出的 `date YYYYMMDD` 確認抓到哪一週。

## month_update.bat — 每月更新（董監持股）

執行 `director.py`（無參數）：從 TWSE/TPEX OpenAPI (t187ap11) 抓全體董監持股，
寫入 `data/director/final/{民國年}-{月}.csv` 與個股 csv。

```bat
bat\month_update.bat            :: 無參數
```

- 公司須在**次月 15 日前**申報，所以每月 **16 號以後**再跑。
- OpenAPI 常再拖幾天（過去紀錄約 20 號後才有上個月資料）。跑完檢查
  `data/director/final/` 有沒有長出新月份檔；還是舊月份就改用 MOPS 直抓備援：

```bat
venv\Scripts\python.exe director_mops_bulk.py                :: 補上個月
venv\Scripts\python.exe director_mops_bulk.py 20260601       :: 指定月份 (取 YYYYMM)
venv\Scripts\python.exe director_mops_bulk.py 20260601 8     :: 第2參數=隨機延遲上限秒數 (預設 6)
```

- `director_mops_bulk.py` 逐股向 MOPS 請求（每股延遲 4~N 秒防封鎖，全部跑完約 2~4 小時），
  已在月檔的股票自動跳過，中斷後重跑會接著補。

## 排程建議（Windows 工作排程器）

| 腳本 | 觸發 |
|---|---|
| `day_update.bat` | 週一~週五 16:00 |
| `week_update.bat` | 週六 10:00（沒抓到新資料週一再自動跑一次也行） |
| `month_update.bat` | 每月 17 號 10:00 |

排程動作填「啟動程式」，程式選 bat 檔完整路徑即可（bat 內已自行 cd）。
