#!/bin/bash

set -e

echo "============================================"
echo "  Gray Release Platform - 本地启动脚本"
echo "============================================"

DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

echo "[1/4] 构建所有模块..."
mvn clean package -DskipTests -q

echo "[2/4] 构建 Docker 镜像..."
$DOCKER_COMPOSE build release-service gateway-service monitor-service

echo "[3/4] 启动基础设施 (Kafka, Prometheus)..."
$DOCKER_COMPOSE up -d zookeeper kafka prometheus

echo "等待 Kafka 就绪..."
sleep 15

echo "[4/4] 启动服务..."
$DOCKER_COMPOSE up -d release-service gateway-service monitor-service

echo ""
echo "============================================"
echo "  服务启动完成!"
echo "============================================"
echo "  Gateway Service:  http://localhost:8080"
echo "  Release Service:  http://localhost:8081/release-service/actuator/health"
echo "  Monitor Service:  http://localhost:8082/monitor-service/actuator/health"
echo "  Prometheus:       http://localhost:9090"
echo "============================================"

$DOCKER_COMPOSE ps