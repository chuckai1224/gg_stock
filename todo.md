# TODO — 系統修復清單

## 🔴 嚴重錯誤（直接 crash）

- [ ] **1. `cm1` 模組未 import 但仍被呼叫**
  - `good_stock.py:47` — `from stocktool import comm as cm1` 被註解掉
  - 仍被呼叫的位置：L757 `cm1.get_long_red_ratio()`、L950/954/958/1552/1556/1560 `cm1.calc_profit()`
  - 修法：找回 stocktool 套件安裝路徑，或將 `cm1.get_long_red_ratio` / `cm1.calc_profit` 改用本地實作

- [ ] **2. `pd.np` 已在 pandas 2.0 移除**
  - `all_stock.py:424,489`
  - `stock_comm.py:252`
  - `good_stock.py:221,224,244,247`
  - `fut.py:439,442,462,465`
  - `tdcc_dist.py:811`
  - 修法：全部改為 `np.nan` / `np.empty()`

- [ ] **3. `engine.table_names()` 已在 SQLAlchemy 2.0 移除**
  - `good_stock.py:508,590,858,1033`
  - `director.py:108`
  - `stock_big3.py:502,546`
  - `stock_comm.py:810,932,1068,1084,1099`
  - `tdcc_dist.py:1177,1228,1280`
  - 修法：改為 `sqlalchemy.inspect(engine).get_table_names()`

- [ ] **4. `df.append()` 已在 pandas 2.0 移除**
  - `gg_stock.py:798` — 主流程輸出 loop `out=out.append(d,ignore_index=True)`
  - `stock_comm.py:1088`
  - 修法：改為 `pd.concat([out, d], ignore_index=True)`

---

## 🟠 邏輯 Bug（計算結果錯誤）

- [ ] **5. `calc_spwr()` copy-paste 公式錯誤**
  - `stock_comm.py:87-88` 和 `all_stock.py:113-114`
  - `sell_pwr` 與 `buy_pwr` 公式相同（都用 `total_buy`），`sell_pwr` 應改為 `total_sell`
  ```python
  # 修正前
  sell_pwr = vol * total_buy / (total_buy + total_sell)
  # 修正後
  sell_pwr = vol * total_sell / (total_buy + total_sell)
  ```

- [ ] **6. `get_revenue_year_20_score()` 缺少下限 clamp**
  - `gg_stock.py:463-466`
  - 只有上限 `>2 → 2`，缺少 `<-2 → -2`，可能輸出超出範圍的負分
  ```python
  # 修正後
  y = (x*100-10)*0.025 + w*0.25
  y = max(-2, min(2, y))
  ```

- [ ] **7. 市值下限過濾遺漏**
  - `gg_stock.py:772-773`
  - 只過濾 `市值 ≤ 15000`（150億），缺少 `≥ 3000`（30億）下限
  ```python
  # 修正後（fund 方法無上限，但仍需下限）
  d1 = d1[d1['市值'] >= 3000].reset_index(drop=True)
  if 'fund' != method:
      d1 = d1[d1['市值'] <= 15000].reset_index(drop=True)
  ```

---

## 🟡 API 過時（deprecation warning 或未來 crash）

- [ ] **8. `rolling(axis=0)` 在 pandas 2.1 移除**
  - `good_stock.py:915`
  - 修法：移除 `axis=0` 參數（預設即為沿 row）

- [ ] **9. Selenium 4 廢棄 API**
  - `good_stock.py:89` — `webdriver.Firefox(firefox_profile=profile)` 已棄用
    - 修法：改用 `Options`：`options = webdriver.FirefoxOptions(); options.set_preference(...); webdriver.Firefox(options=options)`
  - `good_stock.py:93,95,100` — `find_element_by_id()` Selenium 4 已移除
    - 修法：改為 `find_element(By.ID, "...")`，並 `from selenium.webdriver.common.by import By`

- [ ] **10. `pd.set_option('display.max_colwidth', -1)`**
  - `gg_stock.py:806`
  - pandas 新版 `-1` 無效，改為 `None`

---

## 🔵 系統完整性

- [ ] **11. `get_psrs_score()` 無上限 clamp**
  - `gg_stock.py:408-412` — PSR 極低時分數可超過 +4，HTML 文件說範圍 `-4 ~ +4`
  ```python
  y = max(-4, min(4, (1.5 - psrs) / 0.375))
  ```

- [ ] **12. `final/` 資料夾不存在時未自動建立**
  - `gg_stock.py:808-810` — 輸出 HTML/CSV 前無 `check_dst_folder` 防呼叫，若 `final/` 不存在會 crash
  - 修法：在 `gen_gg_buy_list()` 開頭加 `check_dst_folder('final')`
