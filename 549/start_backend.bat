@echo off
echo ========================================
echo 医疗知识问答系统 - 后端启动脚本
echo ========================================

cd backend

echo.
echo 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo 安装依赖包...
pip install -r requirements.txt

echo.
echo 启动FastAPI服务...
echo 后端API地址: http://localhost:8000
echo API文档地址: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo ========================================

uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
