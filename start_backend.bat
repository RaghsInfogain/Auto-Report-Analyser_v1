@echo off
setlocal

echo Starting Auto Report Analyzer Backend...
echo.

cd /d "%~dp0backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        py -3 -m venv venv
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist "uploads" mkdir uploads

echo Starting FastAPI server on http://localhost:8000
uvicorn app.main:app --reload --port 8000

pause
