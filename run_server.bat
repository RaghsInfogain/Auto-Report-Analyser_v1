@echo off
setlocal

echo ======================================
echo Auto Report Analyzer - Full Stack Setup
echo ======================================
echo.

set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

:: Start Backend Server (in new window)
echo Setting up Backend...
cd /d "%PROJECT_ROOT%\backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        py -3 -m venv venv
    )
)

if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment creation failed.
    pause
    exit /b 1
)

if not exist "venv\.dependencies_installed" (
    echo Installing backend dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo. > venv\.dependencies_installed
)

if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports

echo Starting Backend Server on http://localhost:8000
start "Auto Report Analyzer - Backend" cmd /k "cd /d \"%PROJECT_ROOT%\backend\" && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

:: Start Frontend Server (in new window)
echo.
echo Setting up Frontend...
cd /d "%PROJECT_ROOT%\frontend"

if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

echo Starting Frontend Server on http://localhost:3020
start "Auto Report Analyzer - Frontend" cmd /k "cd /d \"%PROJECT_ROOT%\frontend\" && set PORT=3020 && npm start"

:: Display status
echo.
echo ======================================
echo Servers are starting up!
echo ======================================
echo.
echo Backend:
echo   - API Server: http://localhost:8000
echo   - API Docs:   http://localhost:8000/docs
echo.
echo Frontend:
echo   - Web App:    http://localhost:3020
echo.
echo Close the Backend and Frontend windows to stop the servers.
echo.
pause
