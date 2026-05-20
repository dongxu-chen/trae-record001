@echo off
chcp 65001
echo 💰 多云费用分析优化工具
echo ========================

if not exist venv (
    echo 📦 创建虚拟环境...
    python -m venv venv
)

echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

echo 📚 安装依赖...
pip install -r requirements.txt

echo 🚀 启动 Streamlit 仪表板...
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.enableCORS=true

pause
