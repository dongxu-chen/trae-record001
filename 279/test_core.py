import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== 测试数据处理模块 ===")
from src.data_processing import DataProcessor
df = DataProcessor.generate_mock_data(n_days=100, inject_anomalies=True)
print(f"生成数据形状: {df.shape}")
print(f"数据列: {df.columns.tolist()}")
print(f"前5行:\n{df.head()}")
print(f"缺失值数量: {df['y'].isna().sum()}")

print("\n=== 测试数据预处理 ===")
df_processed = DataProcessor.preprocess_data(df)
print(f"预处理后缺失值数量: {df_processed['y'].isna().sum()}")

print("\n=== 测试Prophet特征提取 ===")
from src.prophet_features import ProphetFeatureExtractor
prophet_extractor = ProphetFeatureExtractor()
features = prophet_extractor.extract_features(df_processed)
print(f"提取特征形状: {features.shape}")
print(f"特征列: {features.columns.tolist()}")

scores = prophet_extractor.get_anomaly_scores_from_prophet(df_processed)
print(f"Prophet异常评分形状: {scores.shape}")

print("\n=== 所有核心模块测试通过! ===")
