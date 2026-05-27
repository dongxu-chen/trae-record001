@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo   Gray Release Platform - Local Start Script
echo ============================================

set DOCKER_COMPOSE=docker compose
docker compose version >nul 2>&1
if errorlevel 1 set DOCKER_COMPOSE=docker-compose

echo [1/4] Building all modules...
call mvn clean package -DskipTests -q

echo [2/4] Building Docker images...
call %DOCKER_COMPOSE% build release-service gateway-service monitor-service

echo [3/4] Starting infrastructure (Kafka, Prometheus)...
call %DOCKER_COMPOSE% up -d zookeeper kafka prometheus

echo Waiting for Kafka to be ready...
timeout /t 15 /nobreak >nul

echo [4/4] Starting services...
call %DOCKER_COMPOSE% up -d release-service gateway-service monitor-service

echo.
echo ============================================
echo   Services Started!
echo ============================================
echo   Gateway Service:  http://localhost:8080
echo   Release Service:  http://localhost:8081/release-service/actuator/health
echo   Monitor Service:  http://localhost:8082/monitor-service/actuator/health
echo   Prometheus:       http://localhost:9090
echo ============================================

call %DOCKER_COMPOSE% ps
endlocal