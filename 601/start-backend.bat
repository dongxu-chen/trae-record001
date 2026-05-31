@echo off
echo ========================================
echo Starting Data Sync Checker Backend
echo ========================================
echo.

where mvn >nul 2>nul
if %errorlevel% neq 0 (
    echo Maven is not installed or not in PATH.
    echo Please install Maven and add it to your PATH.
    pause
    exit /b 1
)

echo Building project...
call mvn clean compile -DskipTests
if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Starting Spring Boot application...
echo Application will be available at: http://localhost:8080/api
echo.
call mvn spring-boot:run -Dspring-boot.run.profiles=dev
