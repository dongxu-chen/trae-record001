import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_generator import generate_all_data
from feature_engineering import prepare_training_data
from eta_model import train_and_save_model

os.makedirs('data', exist_ok=True)
os.makedirs('models', exist_ok=True)

print("=" * 50)
print("外卖配送时间预测平台 - 初始化")
print("=" * 50)

print("\n1. 生成模拟数据...")
data = generate_all_data()
for name, df in data.items():
    df.to_csv(f'data/{name}.csv', index=False, encoding='utf-8-sig')
    print(f"  ✓ {name}: {len(df)} 条记录")

print("\n2. 特征工程...")
X, y, fe = prepare_training_data(data['orders'])
fe.save('models/feature_engineer.pkl')
print(f"  ✓ 特征数量: {len(fe.feature_names)}")
print(f"  ✓ 训练数据形状: {X.shape}")

print("\n3. 训练XGBoost模型...")
model, metrics = train_and_save_model(X, y, 'models/eta_model.pkl')

print("\n" + "=" * 50)
print("初始化完成!")
print("=" * 50)
print("\n运行以下命令启动应用:")
print("  streamlit run app.py")
