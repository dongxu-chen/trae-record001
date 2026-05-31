#!/bin/bash

echo "========================================"
echo " DB Guardian - 数据库连接风暴防护系统"
echo "========================================"
echo ""

echo "[1/2] 启动后端服务..."
cd "$(dirname "$0")/.."
go run cmd/main.go &
BACKEND_PID=$!

sleep 3

echo "[2/2] 启动前端服务..."
cd web
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo " 服务启动中，请稍候..."
echo ""
echo " 后端地址: http://localhost:8080"
echo " 前端地址: http://localhost:3000"
echo " 代理端口: 3307"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
