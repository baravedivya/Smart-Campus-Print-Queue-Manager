@echo off
setlocal
echo ========================================================
echo   SmartPrint - Campus Xerox & Print Queue System
echo ========================================================
echo.

cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Setting up .venv...
    py -m venv .venv || python -m venv .venv
    echo [INFO] Installing required dependencies...
    .\.venv\Scripts\pip.exe install -r requirements.txt
)

echo [INFO] Ensuring database and demo data exist...
.\.venv\Scripts\python.exe seed_data.py

echo.
echo ========================================================
echo   Starting SmartPrint Web Server at http://127.0.0.1:5000
echo ========================================================
echo   Student Demo Login: CS2026-084 / student123
echo   Admin Demo Login:   admin@smartprint.campus / admin123
echo ========================================================
echo.

.\.venv\Scripts\python.exe app.py

pause
