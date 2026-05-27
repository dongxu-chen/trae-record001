@echo off
chcp 65001 >nul
echo ==========================================
echo   定时任务依赖管理系统
echo   Airflow + Celery + Redis + Flower + MySQL
echo ==========================================
echo.

echo [1/4] 检查Docker环境...
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Docker，请先安装Docker
    pause
    exit /b 1
)
echo   OK - Docker环境就绪
echo.

echo [2/4] 创建必要目录...
if not exist logs mkdir logs
if not exist dags mkdir dags
if not exist celery_app\tasks mkdir celery_app\tasks
if not exist flower_app\templates mkdir flower_app\templates
if not exist flower_app\static mkdir flower_app\static
if not exist models mkdir models
if not exist scripts mkdir scripts
if not exist db mkdir db
echo   OK - 目录创建完成
echo.

echo [3/4] 构建并启动服务...
docker compose build
docker compose up -d
echo.

echo [4/4] 等待服务就绪...
echo   等待MySQL启动...
timeout /t 10 /nobreak >nul
echo   等待Redis启动...
timeout /t 5 /nobreak >nul
echo   等待Airflow初始化...
timeout /t 15 /nobreak >nul
echo.

echo ==========================================
echo   系统启动完成！
echo ==========================================
echo.
echo   访问地址:
echo     - 监控面板:    http://localhost:5000
echo     - Airflow UI:  http://localhost:8080
echo     - Flower监控:  http://localhost:5555
echo.
echo   默认账号:
echo     - Airflow:    admin / admin
echo     - Flower:     admin / admin123
echo.
echo   查看服务状态: docker compose ps
echo   查看服务日志: docker compose logs -f
echo   停止系统:       docker compose down
echo.
pause
