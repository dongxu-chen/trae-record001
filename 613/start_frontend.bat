@echo off
echo ========================================
echo  SkyWalking 告警规则优化工具 - 前端启动
echo ========================================
echo.

cd /d "%~dp0frontend"

echo [1/3] 检查Node.js环境...
node --version
if errorlevel 1 (
    echo 错误: 未找到Node.js，请先安装Node.js 18+
    pause
    exit /b 1
)

npm --version
if errorlevel 1 (
    echo 错误: 未找到npm
    pause
    exit /b 1
)

echo.
echo [2/3] 安装依赖...
if not exist "node_modules" (
    echo 正在安装npm依赖，这可能需要几分钟...
    npm install
    if errorlevel 1 (
        echo 警告: 依赖安装可能遇到问题，请手动检查
    )
) else (
    echo 依赖已存在，跳过安装
)

echo.
echo [3/3] 启动开发服务器...
echo.
echo 服务地址: http://localhost:3000
echo 后端代理: http://localhost:8000
echo.
echo 按 Ctrl+C 停止服务
echo.

npm run dev

pause
