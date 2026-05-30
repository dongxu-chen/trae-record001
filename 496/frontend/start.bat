@echo off
echo ========================================
echo 限流配置推荐工具 - 前端启动脚本
echo ========================================
echo.

where npm >nul 2>nul
if %errorlevel% equ 0 (
    echo 检测到npm已安装
    
    if not exist "node_modules" (
        echo 正在安装依赖...
        call npm install
    )
    
    echo.
    echo 正在启动前端服务...
    echo.
    npm start
) else (
    echo [警告] 未检测到npm，请先安装Node.js 16+
    echo.
    echo 下载地址: https://nodejs.org/
    echo 安装后请重启终端
)

pause
