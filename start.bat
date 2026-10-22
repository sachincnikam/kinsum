@echo off
REM Start Kinsum and open it in the browser. Close this window (or press Ctrl+C) to stop.
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo Kinsum is not set up yet. Run setup.bat first.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo Building the app screens ...
  pushd frontend
  call npm run build || (popd & pause & exit /b 1)
  popd
)

echo.
echo Kinsum is starting at http://localhost:8000  (only this computer can connect)
echo Close this window to stop Kinsum.
echo.

REM Open the browser a few seconds after the server starts
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:8000'"

cd backend
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
