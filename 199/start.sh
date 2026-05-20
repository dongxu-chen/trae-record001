#!/bin/bash

echo "========================================"
echo "   电商直播数据大屏系统 - 启动脚本"
echo "========================================"
echo ""

echo "[1/3] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.8+"
    exit 1
fi
echo "[OK] Python环境正常"
echo ""

echo "[2/3] 安装依赖包..."
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

echo "[3/3] 启动系统..."
echo ""
echo "========================================"
echo " 请选择启动模式:"
echo "    1. 仅启动Kafka数据生产者"
echo "    2. 仅启动流处理作业"
echo "    3. 仅启动WebSocket服务"
echo "    4. 启动全部组件（推荐）"
echo "    5. 退出"
echo "========================================"
echo ""

read -p "请输入选项 (1-5): " choice

case $choice in
    1) python3 main.py producer ;;
    2) python3 main.py stream ;;
    3) python3 main.py server ;;
    4) python3 main.py all ;;
    5) exit 0 ;;
    *) echo "无效选项，退出" ;;
esac
