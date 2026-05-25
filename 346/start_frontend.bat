@echo off
echo ========================================
echo  社交关系图分析平台 - 前端服务启动
echo ========================================
echo.

cd /d "%~dp0frontend"

echo [1/2] 检查Node.js依赖...
if not exist "node_modules" (
    echo 正在安装依赖...
    npm install
) else (
    echo 依赖已安装
)

echo.
echo [2/2] 启动Vite开发服务...
echo 服务地址: http://localhost:5173
echo.
npm run dev

pause
