@echo off
echo ========================================
echo 新闻话题演化追踪系统 - 后端启动脚本
echo ========================================

cd /d "%~dp0.."

if not exist "backend\venv" (
    echo 创建虚拟环境...
    cd backend
    python -m venv venv
    call venv\Scripts\activate
    echo 安装依赖...
    pip install -r requirements.txt
    cd ..
) else (
    cd backend
    call venv\Scripts\activate
    cd ..
)

echo 启动后端服务...
cd backend
python main.py

pause
