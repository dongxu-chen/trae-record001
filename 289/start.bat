@echo off
echo ========================================
echo 城市公交车到站时间预测系统
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo Python环境检查通过
echo.

echo [2/3] 检查依赖包...
python -c "import xgboost, redis, websockets, aiohttp" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖包安装失败
        pause
        exit /b 1
    )
)
echo 依赖包检查通过
echo.

echo [3/3] 启动系统...
echo.
echo HTTP服务器: http://localhost:8080
echo WebSocket服务器: ws://localhost:8765
echo.
echo 按 Ctrl+C 停止系统
echo ========================================
echo.

python main.py

pause
