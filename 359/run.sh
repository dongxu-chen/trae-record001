#!/bin/bash
echo "============================================"
echo "快递时效预测系统 - 启动脚本"
echo "============================================"

echo ""
echo "正在检查模型文件..."
if [ ! -f "models/delivery_model.pkl" ]; then
    echo "模型文件不存在，正在初始化..."
    python init.py
fi

echo ""
echo "正在启动 Streamlit 应用..."
python -m streamlit run app.py --server.port 8501
