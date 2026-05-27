import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_data import generate_training_data
from model import DeliveryTimeModel
from config import Config

print("=" * 60)
print("快递时效预测系统 - 初始化 (升级版)")
print("=" * 60)

parser = argparse.ArgumentParser()
parser.add_argument('--samples', type=int, default=5000, help='训练数据量')
parser.add_argument('--use-cv', action='store_true', help='使用交叉验证')
parser.add_argument('--confidence-levels', type=str, default='0.8,0.9,0.95,0.99', 
                    help='置信水平列表，逗号分隔')
args = parser.parse_args()

confidence_levels = [float(x) for x in args.confidence_levels.split(',')]

print(f"\n配置:")
print(f"  训练数据量: {args.samples}")
print(f"  交叉验证: {'是' if args.use_cv else '否'}")
print(f"  置信水平: {confidence_levels}")

print("\n1. 生成训练数据 (含网格降水量特征)...")
df = generate_training_data(args.samples)
df.to_csv(Config.DATA_PATH, index=False, encoding='utf-8-sig')
print(f"   已生成 {len(df)} 条训练数据")
print(f"   新增列: precipitation_rate, precipitation_max, precipitation_coverage")

print("\n2. 训练LightGBM分位数回归模型 (含区间收窄)...")
model = DeliveryTimeModel(confidence_levels=confidence_levels)
metrics = model.train(df, use_cross_validation=args.use_cv)
model.save()

print("\n3. 初始化完成！")
print(f"   模型MAE: {metrics['mae']:.2f} 小时")
print(f"   模型R²: {metrics['r2']:.4f}")
for cl in sorted(confidence_levels, reverse=True):
    cl_int = int(cl * 100)
    cov = metrics.get(f'coverage_{cl_int}', 0)
    width = metrics.get(f'interval_width_{cl_int}', 0)
    print(f"   {cl_int}%置信区间: 覆盖率={cov:.2%}, 平均宽度={width:.2f}h")

print(f"\n   训练分位数点: {model.quantiles}")
print(f"   置信区间收窄: {'已启用 (KDE+自适应带宽)' if model._residual_kde else '未启用'}")

print("\n现在可以运行 streamlit run app.py 启动应用")
