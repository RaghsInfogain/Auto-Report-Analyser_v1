@echo off
setlocal

echo Starting Auto Report Analyzer Frontend...
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo Starting React development server on http://localhost:3020
set PORT=3020
call npm start

pause
