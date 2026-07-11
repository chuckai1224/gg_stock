@echo off
rem ============================================================
rem Weekly update: TDCC shareholding distribution
rem   source: https://opendata.tdcc.com.tw/getOD.ashx?id=1-5
rem   target: sql/tdcc_dist.db  (data date = Friday)
rem Run after TDCC releases the new file (usually Sat, or next Mon).
rem If the data date has not changed yet, it is a no-op; retry later.
rem ============================================================
cd /d "%~dp0.."
"venv\Scripts\python.exe" tdcc_get.py
