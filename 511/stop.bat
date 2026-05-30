@echo off
echo Stopping Data Lineage Tool...
cd /d "%~dp0docker"
docker-compose down
echo Services stopped.
pause
