@echo off
echo ========================================
echo   启动召回率分析平台 - 前端服务
echo ========================================
echo.

cd /d "%~dp0frontend"

echo [1/2] 检查 Node.js 环境...
node --version
if errorlevel 1 (
    echo 错误: 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo.
echo [2/2] 安装依赖并启动...
if not exist "node_modules" (
    echo 安装依赖...
    npm install
)

echo 前端地址: http://localhost:5173
echo.
echo 按 Ctrl+C 停止服务
echo.

npm run dev
