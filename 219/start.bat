@echo off
chcp 65001
echo ========================================
echo    交通流量热力图系统
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo Python环境检测通过
echo.

echo [2/3] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 依赖安装可能存在问题，请手动检查
)
echo.

echo [3/3] 启动服务...
echo.
echo 服务启动后，请在浏览器中访问: http://localhost:8000
echo 按 Ctrl+C 停止服务
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
