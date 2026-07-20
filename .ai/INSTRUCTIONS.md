# gg_stock 專案規則（唯一正本）

> 本檔是這個專案 AI 規則的**唯一正本**（single source of truth）。
> `CLAUDE.md`（Claude Code 入口）與 `AGENTS.md`（Codex 入口）都只是指向本檔的入口，內容一律改這裡，不要改入口檔。
> 注意：D: 槽是 **exFAT**，不支援 symlink/hardlink，所以入口檔用「引用/指示」方式而非軟連結。

## 專案簡介

台股資料抓取、分析與監控系統。日K/籌碼/財報資料存於 `sql/stock/{股票代號}.db`（每檔一個 SQLite），即時行情走 Shioaji API，財報/月營收回補走 FinMind 與 TWSE。

## 環境

- Windows 11、PowerShell；工作目錄 `D:\gg_stock`（從 Linux `/home/rd1/gg_stock` 遷移而來）
- **必須在 `D:\gg_stock` 目錄下執行程式** — `stock_comm.py` 的 `datafolder()` 回傳相對路徑 `data`
- 這台機器的網路有 SSL 憑證攔截：`pip install` 必須加 `--trusted-host pypi.org --trusted-host files.pythonhosted.org`
- 中文 CSV 一律 UTF-8；cmd 顯示亂碼先 `chcp 65001`
- D: 槽是 exFAT：不能建 symlink、hardlink、junction，權限指令（icacls 等）行為也和 NTFS 不同

## 資料與快取（未經同意不要刪除或重建）

- `sql/stock/*.db` — 個股資料庫（約 2000 檔），重抓成本極高
- `kbar_cache/` — Shioaji K 線增量快取（parquet），設計目的是降低 API 用量
- `tick_cache/` — 歷史逐筆 tick 的日K Volume Profile 快取
- `data/`、`csv/` — 每日更新的行情與清單資料

## 已知地雷

- Shioaji 的 `tick.close` 是 `Decimal`，直接寫入 float64 ndarray 會拋 TypeError 且被吞掉，造成盤中 K 棒不更新 — 寫入前必須轉 `float`
- NaN 比較（`x != np.nan` 恆為 True）在舊碼中出過多次 bug，改碼時一律用 `pd.notna()` / `np.isnan()`

## 工作習慣

- 不要主動 commit / push；使用者要求才做。commit 訊息沿用現有風格（如 `update 2026-07-20`）
- 臨時檔案放 session scratchpad 或 `work/`，不要散落在專案根目錄
- 密碼、API key 不寫死在程式裡
