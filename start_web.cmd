@echo off
cd /d "%~dp0"
start http://127.0.0.1:5000/online/
.\venv\Scripts\python.exe online.py
