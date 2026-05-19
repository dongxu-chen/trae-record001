#!/bin/bash

echo "========================================"
echo " Nginx Log Analyzer - Linux/Mac启动脚本"
echo "========================================"
echo ""

echo "[1/3] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi
echo "Python环境正常"
echo ""

echo "[2/3] 安装依赖包..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "警告: 依赖安装可能失败，请手动检查"
fi
echo ""

echo "[3/3] 启动Flask应用..."
echo ""
echo "应用将在 http://localhost:5000 启动"
echo "按 Ctrl+C 停止应用"
echo ""

python3 app.py
