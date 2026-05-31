@echo off
echo ========================================
echo  SkyWalking 告警规则优化工具 - 后端启动
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 依赖安装可能遇到问题，请手动检查
)

echo.
echo [3/3] 启动后端服务...
echo.
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
