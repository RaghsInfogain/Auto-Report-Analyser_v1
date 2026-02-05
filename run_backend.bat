@echo off
setlocal

echo ======================================
echo Auto Report Analyzer - Backend Only
echo ======================================
echo.

cd /d "%~dp0backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        py -3 -m venv venv
    )
)

call venv\Scripts\activate.bat

if not exist "venv\.dependencies_installed" (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo. > venv\.dependencies_installed
)

if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports

echo Starting Backend Server...
echo.
echo Server will be available at:
echo   - API:   http://localhost:8000
echo   - Docs:  http://localhost:8000/docs
echo   - ReDoc: http://localhost:8000/redoc
echo.
echo Press CTRL+C to stop the server
echo.

uvicorn app.main:app --reload --port 8000

pause
