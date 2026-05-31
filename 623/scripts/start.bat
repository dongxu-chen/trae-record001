@echo off
echo ========================================
echo  DB Guardian - 数据库连接风暴防护系统
echo ========================================
echo.

echo [1/2] 启动后端服务...
start "DB Guardian Backend" cmd /k "cd /d %~dp0 && go run cmd/main.go"

timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务...
start "DB Guardian Frontend" cmd /k "cd /d %~dp0web && npm run dev"

echo.
echo ========================================
echo  服务启动中，请稍候...
echo.
echo  后端地址: http://localhost:8080
echo  前端地址: http://localhost:3000
echo  代理端口: 3307
echo ========================================
echo.
pause
