#!/bin/bash

echo "💰 多云费用分析优化工具"
echo "========================"

if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

echo "🔧 激活虚拟环境..."
source venv/bin/activate

echo "📚 安装依赖..."
pip install -r requirements.txt

echo "🚀 启动 Streamlit 仪表板..."
streamlit run streamlit_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.enableCORS=true
