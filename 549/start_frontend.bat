@echo off
echo ========================================
echo 医疗知识问答系统 - 前端启动脚本
echo ========================================

cd frontend

echo.
echo 检查Node.js环境...
node --version
if errorlevel 1 (
    echo 错误: 未找到Node.js，请先安装Node.js 16+
    pause
    exit /b 1
)

echo.
echo 安装依赖包...
call npm install

echo.
echo 启动React开发服务器...
echo 前端访问地址: http://localhost:3000
echo.
echo 按 Ctrl+C 停止服务
echo ========================================

call npm start

pause
