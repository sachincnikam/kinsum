@echo off
REM Development mode: backend reloads on code changes, screens update instantly.
REM Opens two windows (backend and frontend). Close both to stop.
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)

start "Kinsum backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "Kinsum frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; Start-Process 'http://localhost:5173'"

echo Development servers starting:  app at http://localhost:5173 , API at http://localhost:8000
