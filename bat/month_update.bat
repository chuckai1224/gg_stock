@echo off
rem ============================================================
rem Monthly update: director/supervisor shareholding
rem   source: TWSE/TPEX OpenAPI t187ap11 (monthly filings)
rem   target: data/director/final/{roc}-{m}.csv + per-stock csv
rem Companies must file last month's holdings by the 15th,
rem so run this after ~the 16th. If the OpenAPI still shows the
rem previous month (it often lags to the 20th+), backfill from
rem MOPS directly instead:
rem   venv\Scripts\python.exe director_mops_bulk.py
rem ============================================================
cd /d "%~dp0.."
"venv\Scripts\python.exe" director.py
