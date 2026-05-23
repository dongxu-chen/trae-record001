@echo off
echo ========================================
echo 销售数据可视化仪表板 - 启动脚本
echo ========================================

echo [1/4] 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/4] 安装依赖包...
pip install -r requirements.txt

echo.
echo [3/4] 请确保MySQL服务已启动，并在.env文件中配置正确的数据库连接信息
echo.
echo 数据库配置:
echo   主机: %MYSQL_HOST%
echo   端口: 3306
echo   数据库: sales_dashboard
echo.
echo 如果是首次运行，请先执行: python generate_data.py
echo.

echo [4/4] 启动FastAPI服务器...
echo.
echo 服务器启动后，请在浏览器访问: http://localhost:8000
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
python main.py

pause
