@echo off
echo ========================================
echo  Nginx Log Analyzer - Windows启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo Python环境正常
echo.

echo [2/3] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 依赖安装可能失败，请手动检查
)
echo.

echo [3/3] 启动Flask应用...
echo.
echo 应用将在 http://localhost:5000 启动
echo 按 Ctrl+C 停止应用
echo.
python app.py

pause
