@echo off
title TRACEFLOW launcher
echo Installing backend dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt
start "TRACEFLOW backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload"
cd /d "%~dp0frontend"
if not exist node_modules call npm install
start "TRACEFLOW frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 6 >nul
start http://localhost:5173
