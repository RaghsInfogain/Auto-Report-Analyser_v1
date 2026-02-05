@echo off
setlocal

echo ======================================
echo Run ID Migration Tool
echo ======================================
echo.
echo This script will convert all existing Run IDs
echo to sequential format (Run-1, Run-2, etc.)
echo where the oldest run becomes Run-1.
echo.

cd /d "%~dp0backend"

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found!
    echo Please run run_backend.bat or start_backend.bat first to set up the environment.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo Starting migration...
echo.

python migrate_run_ids.py

echo.
echo Migration process completed!
echo.
pause
