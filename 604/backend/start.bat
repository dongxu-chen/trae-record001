@echo off
echo ========================================
echo  法律文书相似案例检索系统 - 后端启动
echo ========================================
echo.

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/3] 检查虚拟环境...
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

echo.
echo [3/3] 激活虚拟环境并启动服务...
call venv\Scripts\activate.bat

echo 安装/更新依赖...
pip install -r requirements.txt -q

echo.
echo 启动 FastAPI 服务...
echo 服务地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo 按 Ctrl+C 停止服务
echo.

python app.py

pause
