@echo off
echo ========================================
echo   招聘岗位薪资预测系统 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/3] 安装依赖包...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [3/3] 启动Streamlit应用...
echo.
echo 应用启动后，请在浏览器中访问显示的URL
echo 按 Ctrl+C 可以停止应用
echo.
streamlit run app.py --server.port=8501

pause
