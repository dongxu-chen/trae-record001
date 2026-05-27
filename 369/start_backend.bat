@echo off
echo ========================================
echo   启动召回率分析平台 - 后端服务
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装依赖...
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo [3/3] 启动后端服务...
echo 服务地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python main.py
