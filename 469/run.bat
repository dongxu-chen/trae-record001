@echo off
echo ========================================
echo    股票市场冲击成本模型
echo ========================================
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
if errorlevel 1 (
    echo 警告: 部分依赖安装可能失败，继续尝试启动...
)

echo.
echo 启动Streamlit应用...
echo 应用将在浏览器中打开，地址: http://localhost:8501
echo.
streamlit run app.py

pause
