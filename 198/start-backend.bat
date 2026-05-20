@echo off
cd /d "%~dp0backend"
echo Starting Prometheus Alert Manager Backend...
echo.
echo Installing dependencies...
go mod tidy
if errorlevel 1 (
    echo Failed to install dependencies
    pause
    exit /b 1
)
echo.
echo Starting server on http://localhost:8080...
go run main.go
pause
