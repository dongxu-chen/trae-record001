@echo off
echo ========================================
echo 校园心理健康预约系统 - FastAPI版本
echo ========================================

echo [1/3] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

echo [2/3] 安装依赖包...
pip install -r fastapi_app\requirements.txt
if %errorlevel% neq 0 (
    echo 警告: 部分依赖安装失败，尝试继续...
)

echo [3/3] 启动FastAPI服务器...
echo.
echo 服务启动后请访问: http://localhost:5000
echo API文档地址: http://localhost:5000/docs
echo.
python -m uvicorn fastapi_app.main:app --host 0.0.0.0 --port 5000 --reload --ws websockets

pause
