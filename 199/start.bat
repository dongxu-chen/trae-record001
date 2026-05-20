@echo off
chcp 65001 >nul
title 电商直播数据大屏系统

echo ========================================
echo    电商直播数据大屏系统 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python环境正常
echo.

echo [2/3] 安装依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [警告] 部分依赖安装失败，请手动检查
)
echo.

echo [3/3] 启动系统...
echo.
echo ========================================
echo  请选择启动模式:
echo    1. 仅启动Kafka数据生产者
echo    2. 仅启动流处理作业
echo    3. 仅启动WebSocket服务
echo    4. 启动全部组件（推荐）
echo    5. 退出
echo ========================================
echo.

set /p choice=请输入选项 (1-5):

if "%choice%"=="1" (
    python main.py producer
) else if "%choice%"=="2" (
    python main.py stream
) else if "%choice%"=="3" (
    python main.py server
) else if "%choice%"=="4" (
    python main.py all
) else if "%choice%"=="5" (
    exit /b 0
) else (
    echo 无效选项，退出
    pause
    exit /b 1
)

pause
