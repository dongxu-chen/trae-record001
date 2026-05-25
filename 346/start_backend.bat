@echo off
echo ========================================
echo  社交关系图分析平台 - 后端服务启动
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查Python依赖...
pip list | findstr -i "flask" >nul
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
) else (
    echo 依赖已安装
)

echo.
echo [2/3] 启动Neo4j检查...
echo 提示: 如果没有启动Neo4j，请先运行 docker-compose up -d
echo.

echo [3/3] 启动Flask服务...
echo 服务地址: http://localhost:5000
echo API文档: http://localhost:5000/api/health
echo.
python run.py

pause
