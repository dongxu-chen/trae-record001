import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 60)
print("出租车OD需求预测可视化平台 - 初始化")
print("=" * 60)

print("\n[1/4] 检查数据文件...")
from config import Config
if os.path.exists(Config.DATA_PATH):
    print(f"    ✓ 数据文件已存在: {Config.DATA_PATH}")
else:
    print("    ✗ 数据文件不存在，正在生成...")
    from data.data_generator import generate_od_data
    generate_od_data()
    print("    ✓ 数据生成完成!")

print("\n[2/4] 检查模型文件...")
if os.path.exists(Config.MODEL_PATH):
    print(f"    ✓ 模型文件已存在: {Config.MODEL_PATH}")
else:
    print("    ✗ 模型文件不存在，将在首次预测时训练")

print("\n[3/4] 导入依赖...")
try:
    import flask
    import flask_cors
    import torch
    import numpy
    import pandas
    print("    ✓ 所有依赖已安装")
except ImportError as e:
    print(f"    ✗ 缺少依赖: {e}")
    print("    请运行: pip install flask flask-cors torch numpy pandas scikit-learn geopy")
    sys.exit(1)

print("\n[4/4] 启动Flask服务器...")
print("    服务器地址: http://localhost:5000")
print("    按 Ctrl+C 停止服务器")
print("=" * 60 + "\n")

from app import app, initialize_data
initialize_data()
app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
