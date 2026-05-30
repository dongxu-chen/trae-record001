@echo off
echo ========================================
echo 地形图等高线提取工具
echo ========================================
echo.

echo [1/2] 启动后端服务 (http://localhost:3001)
start "后端服务" cmd /k "cd /d %~dp0backend && npm install && npm start"

timeout /t 5 /nobreak >nul

echo.
echo [2/2] 启动前端服务 (http://localhost:3000)
start "前端服务" cmd /k "cd /d %~dp0frontend && npm install && npm start"

echo.
echo ========================================
echo 服务启动中，请稍候...
echo 后端: http://localhost:3001
echo 前端: http://localhost:3000
echo ========================================
pause
