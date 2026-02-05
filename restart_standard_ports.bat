@echo off
setlocal

echo ======================================
echo Restarting with Standard Ports
echo ======================================
echo.

echo Stopping existing servers...

:: Kill processes listening on ports 6000, 7001, 8000, 3000, 3020
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":6000 "') do taskkill /PID %%a /F 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7001 "') do taskkill /PID %%a /F 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 "') do taskkill /PID %%a /F 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 "') do taskkill /PID %%a /F 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3020 "') do taskkill /PID %%a /F 2>nul

timeout /t 3 /nobreak >nul

echo Servers stopped
echo.

set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

:: Start backend on port 8000
echo Starting backend on port 8000...
start "Auto Report Analyzer - Backend" cmd /k "cd /d \"%PROJECT_ROOT%\backend\" && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"
echo Backend started

timeout /t 3 /nobreak >nul

:: Start frontend on port 3020
echo Starting frontend on port 3020...
start "Auto Report Analyzer - Frontend" cmd /k "cd /d \"%PROJECT_ROOT%\frontend\" && set PORT=3020 && npm start"
echo Frontend started

echo.
echo ======================================
echo Servers Running:
echo ======================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3020
echo.
echo Close the Backend and Frontend windows to stop.
echo.
pause
