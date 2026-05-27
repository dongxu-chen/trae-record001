@echo off
chcp 65001 >nul
echo ============================================
echo    电力负荷预测平台 - 启动脚本
echo ============================================
echo.

echo [1/3] 检查并安装依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo 依赖安装失败，请检查网络连接或手动安装
    pause
    exit /b 1
)
echo 依赖安装完成!

echo.
echo [2/3] 准备数据目录...
if not exist "data" mkdir data
if not exist "model" mkdir model
echo 目录准备完成!

echo.
echo [3/3] 启动服务...
echo.
echo ============================================
echo  服务启动后，请访问: http://127.0.0.1:5000
echo  首次启动需要训练模型，请耐心等待...
echo ============================================
echo.

python app.py
pause