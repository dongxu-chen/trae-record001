@echo off
echo ========================================
echo  法律文书相似案例检索系统 - 前端启动
echo ========================================
echo.

echo [1/2] 检查 Node.js 环境...
node --version
if errorlevel 1 (
    echo 错误: 未找到 Node.js，请先安装 Node.js 16+
    pause
    exit /b 1
)

echo.
echo [2/2] 安装依赖并启动...
if not exist node_modules (
    echo 安装依赖包...
    npm install
)

echo.
echo 启动 React 开发服务器...
echo 服务地址: http://localhost:3000
echo 按 Ctrl+C 停止服务
echo.

npm start

pause
