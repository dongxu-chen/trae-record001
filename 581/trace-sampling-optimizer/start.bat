@echo off
echo ========================================
echo  Distributed Trace Sampling Optimizer
echo  Build and Launch Script
echo ========================================

echo.
echo [1/3] Building backend...
cd /d "%~dp0"
call mvnw.cmd clean package -DskipTests -q
if %ERRORLEVEL% NEQ 0 (
    echo Backend build failed!
    pause
    exit /b 1
)
echo Backend build successful.

echo.
echo [2/3] Starting backend service...
start "Sampling Optimizer Backend" java -jar sampling-service/target/sampling-service-1.0.0-SNAPSHOT.jar
timeout /t 5 /nobreak >nul

echo.
echo [3/3] Installing frontend dependencies and starting...
cd sampling-dashboard
call npm install --legacy-peer-deps
call npm start

pause
