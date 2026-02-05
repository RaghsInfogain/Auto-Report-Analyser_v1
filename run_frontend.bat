@echo off
setlocal

echo ======================================
echo Auto Report Analyzer - Frontend Only
echo ======================================
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo Starting Frontend Server...
echo.
echo Server will be available at:
echo   - Web App: http://localhost:3020
echo.
echo Press CTRL+C to stop the server
echo.

set PORT=3020
call npm start

pause
