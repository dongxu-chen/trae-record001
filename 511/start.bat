@echo off
echo Starting Data Lineage Tool...
echo.

echo Starting Docker services...
cd /d "%~dp0docker"
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 30 /nobreak

echo.
echo Services started!
echo.
echo Neo4j Browser: http://localhost:7474
echo Backend API: http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo Default Neo4j credentials: neo4j / password
echo.
pause
