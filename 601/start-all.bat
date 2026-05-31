@echo off
echo ========================================
echo Starting Data Sync Checker - All Services
echo ========================================
echo.

echo [1/3] Starting backend service...
start "Data Sync Checker Backend" cmd /k call start-backend.bat

timeout /t 5 /nobreak >nul

echo [2/3] Starting frontend service...
start "Data Sync Checker Frontend" cmd /k call start-frontend.bat

timeout /t 3 /nobreak >nul

echo [3/3] All services started!
echo.
echo Backend API: http://localhost:8080/api
echo Frontend UI:  http://localhost:3000
echo.
echo Press any key to exit...
pause >nul
