@echo off
echo ========================================
echo 新闻话题演化追踪系统 - 完整启动
echo ========================================

echo [1/3] 启动Neo4j数据库...
docker start news-topic-neo4j 2>nul || (
    echo Neo4j容器不存在，请先运行 docker-compose up -d neo4j
)

timeout /t 5 /nobreak >nul

echo [2/3] 启动后端服务...
start "后端服务" cmd /k "%~dp0start-backend.bat"

timeout /t 3 /nobreak >nul

echo [3/3] 启动前端服务...
start "前端服务" cmd /k "%~dp0start-frontend.bat"

echo.
echo 系统启动中，请等待...
echo - 后端: http://localhost:8000
echo - 前端: http://localhost:3000
echo - Neo4j: http://localhost:7474
echo.
pause
