@echo off
echo ========================================
echo 新闻话题演化追踪系统 - 前端启动脚本
echo ========================================

cd /d "%~dp0.."
cd frontend

if not exist "node_modules" (
    echo 安装依赖...
    npm install
)

echo 启动前端服务...
npm start

pause
