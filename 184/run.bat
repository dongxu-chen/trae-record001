@echo off
chcp 65001
echo ================================================
echo 商品评论情感分析仪表板 - 启动脚本
echo ================================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未检测到Python环境，请先安装Python 3.7+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装依赖包...
pip install -r requirements.txt

echo.
echo [3/3] 初始化数据并启动服务...
python init_data.py
if errorlevel 1 (
    echo 数据初始化失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo ================================================
echo 启动完成！请在浏览器中访问: http://localhost:5000
echo ================================================
echo.

python app.py
pause
