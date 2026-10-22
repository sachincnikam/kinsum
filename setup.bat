@echo off
REM Kinsum one-time setup: installs backend and frontend packages and builds the app.
setlocal
cd /d "%~dp0"
echo.
echo === Kinsum setup ===
echo.

REM ---- Find Python 3 (py launcher first, then python) ----
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [!] Python 3 was not found.
  echo     Install Python 3.13 from https://www.python.org/downloads/ and tick
  echo     "Add python.exe to PATH", then close and reopen VS Code and run setup.bat again.
  goto fail
)
for /f "delims=" %%v in ('%PY% --version') do echo Found %%v

REM ---- Check Node ----
node --version >nul 2>nul || (
  echo [!] Node.js was not found. Install the LTS version from https://nodejs.org/ and try again.
  goto fail
)
for /f "delims=" %%v in ('node --version') do echo Found Node %%v
echo.

REM ---- Backend ----
if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating Python environment in backend\.venv ...
  %PY% -m venv backend\.venv || goto fail
)
echo Installing backend packages ...
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet || goto fail
"backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements-dev.txt --quiet || goto fail

REM ---- Frontend ----
echo Installing frontend packages (first time takes a minute) ...
pushd frontend
call npm install --no-fund --no-audit || (popd & goto fail)
echo Building the app screens ...
call npm run build || (popd & goto fail)
popd

REM ---- Settings file ----
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env from .env.example
)

REM ---- Quick self-test ----
echo Running tests ...
pushd backend
".venv\Scripts\python.exe" -m pytest -q || (popd & goto fail)
popd

echo.
echo === Setup complete. Run start.bat to open Kinsum. ===
echo.
exit /b 0

:fail
echo.
echo === Setup did not finish. Copy the messages above and share them with Claude. ===
echo.
exit /b 1
