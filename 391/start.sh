#!/bin/bash
# =====================================================
# 定时任务依赖管理系统 - 启动脚本
# =====================================================

set -e

echo "=========================================="
echo "  定时任务依赖管理系统"
echo "  Airflow + Celery + Redis + Flower + MySQL"
echo "=========================================="
echo ""

echo "[1/4] 检查Docker环境..."
if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到Docker，请先安装Docker"
    exit 1
fi
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: 未检测到Docker Compose，请先安装Docker Compose"
    exit 1
fi
echo "  ✓ Docker环境就绪"

echo ""
echo "[2/4] 创建必要目录..."
mkdir -p logs
mkdir -p dags
mkdir -p celery_app/tasks
mkdir -p flower_app/templates
mkdir -p flower_app/static
mkdir -p models
mkdir -p scripts
mkdir -p db
echo "  ✓ 目录创建完成"

echo ""
echo "[3/4] 构建并启动服务..."
docker compose build --no-cache
docker compose up -d

echo ""
echo "[4/4] 等待服务就绪..."
echo "  等待MySQL启动..."
sleep 10
echo "  等待Redis启动..."
sleep 5
echo "  等待Airflow初始化..."
sleep 15

echo ""
echo "=========================================="
echo "  ✓ 系统启动完成！"
echo "=========================================="
echo ""
echo "  访问地址:"
echo "    - 监控面板:    http://localhost:5000"
echo "    - Airflow UI:  http://localhost:8080"
echo "    - Flower监控:  http://localhost:5555"
echo ""
echo "  默认账号:"
echo "    - Airflow:    admin / admin"
echo "    - Flower:     admin / admin123"
echo ""
echo "  查看服务状态: docker compose ps"
echo "  查看服务日志: docker compose logs -f"
echo "  停止系统:       docker compose down"
echo ""
