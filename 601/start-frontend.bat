@echo off
echo ========================================
echo Starting Data Sync Checker Frontend
echo ========================================
echo.

cd /d "%~dp0frontend"

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js is not installed or not in PATH.
    echo Please install Node.js and add it to your PATH.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo.
echo Starting Vite development server...
echo Application will be available at: http://localhost:3000
echo.
call npm run dev
