@echo off
rem ============================================================
rem Daily update (after market close, ~16:00)
rem   crawl.py / revenue.py / stock_big3.py / pe_networth_yeild.py
rem   / gg_stock.py + copy html + git push
rem   (steps live in daily_update.ps1, log: logs\daily_YYYYMMDD.log)
rem Usage: day_update.bat [YYYYMMDD]   (default: today)
rem ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\daily_update.ps1" %*
