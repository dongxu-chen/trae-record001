@echo off
echo 正在启动数据库连接池优化工具前端服务...
echo.

cd frontend

if not exist node_modules (
    echo 首次运行，正在安装依赖...
    npm install
)

npm start

if %errorlevel% neq 0 (
    echo.
    echo 启动失败，请检查 Node.js 环境
    pause
)
