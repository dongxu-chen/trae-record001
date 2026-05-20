@echo off
cd /d "%~dp0frontend"
echo Starting Prometheus Alert Manager Frontend...
echo.
echo Installing dependencies...
call npm install
if errorlevel 1 (
    echo Failed to install dependencies
    pause
    exit /b 1
)
echo.
echo Starting development server on http://localhost:3000...
call npm run dev
pause
