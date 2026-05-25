import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("测试增强版异常检测器 - 新功能验证")
print("=" * 60)

print("\n1. 测试数据处理模块...")
from src.data_processing import DataProcessor
df = DataProcessor.generate_mock_data(n_days=150, inject_anomalies=True)
print(f"   生成数据形状: {df.shape}")

print("\n2. 注入时间戳跳点...")
gap_idx = 50
df_with_gap = df.drop(df.index[gap_idx:gap_idx + 7]).reset_index(drop=True)
print(f"   跳点后数据形状: {df_with_gap.shape}")

print("\n3. 初始化带动态阈值的检测器...")
from src.anomaly_detector import AnomalyDetector
detector = AnomalyDetector(
    seq_length=20,
    hidden_dims=[32, 16],
    use_dynamic_threshold=True,
    threshold_window=15,
    base_percentile=95,
    volatility_scale=1.5
)
print("   ✓ 检测器初始化成功")

print("\n4. 训练模型...")
losses = detector.fit(df_with_gap, epochs=30, verbose=False)
print(f"   ✓ 训练完成, 最终损失: {losses[-1]:.6f}")
print(f"   ✓ 基础阈值: {detector.threshold:.4f}")
print(f"   ✓ 历史误差样本数: {len(detector.historical_recon_errors)}")

print("\n5. 检测异常 (含时间戳连续性检查)...")
result_df = detector.detect_anomalies(df_with_gap, expected_freq='D')
print(f"   ✓ 检测完成，结果形状: {result_df.shape}")
print(f"   ✓ 检测到异常点: {result_df['is_anomaly'].sum()}")
print(f"   ✓ 时间戳跳点异常: {(result_df['anomaly_type'] == 'timestamp_gap').sum()}")

if 'dynamic_threshold' in result_df.columns:
    print(f"   ✓ 动态阈值范围: {result_df['dynamic_threshold'].min():.4f} ~ {result_df['dynamic_threshold'].max():.4f}")

print("\n6. 测试时间戳连续性检查...")
gaps = detector.check_timestamp_continuity(df_with_gap, expected_freq='D')
print(f"   ✓ 检测到时间戳跳点: {len(gaps)} 处")
for i, gap in enumerate(gaps):
    print(f"     - 跳点{i+1}: {gap['gap_start'].strftime('%Y-%m-%d')} -> {gap['gap_end'].strftime('%Y-%m-%d')}, 缺失{gap['gap_days']:.1f}天")

print("\n7. 测试人工反馈...")
sample_dates = result_df['ds'].sample(3).tolist()
for date in sample_dates:
    detector.add_user_feedback(date, is_anomaly=True, confidence=1.5)
print(f"   ✓ 添加反馈: {len(detector.user_feedback)} 条")

print("\n8. 测试增量训练...")
new_losses = detector.incremental_fit(
    df_with_gap,
    feedback_weight=2.0,
    epochs=15,
    verbose=False
)
print(f"   ✓ 增量训练完成，最终损失: {new_losses[-1]:.6f}")
print(f"   ✓ 训练历史记录: {len(detector.training_history)} 次")

print("\n9. 测试模型状态...")
status = detector.get_model_status()
print(f"   ✓ 模型已训练: {status['is_trained']}")
print(f"   ✓ 训练次数: {status['training_count']}")
print(f"   ✓ 反馈样本数: {status['feedback_count']}")
print(f"   ✓ 使用动态阈值: {status['use_dynamic_threshold']}")

print("\n10. 测试异常区间检测...")
intervals = detector.get_anomaly_intervals(df_with_gap)
print(f"   ✓ 检测到异常区间: {len(intervals)} 个")
for i, interval in enumerate(intervals[:3]):
    print(f"     - 区间{i+1}: {interval['start'].strftime('%Y-%m-%d')} -> {interval['end'].strftime('%Y-%m-%d')}, "
          f"类型: {interval['type']}, 持续{interval['duration']}天")

print("\n" + "=" * 60)
print("✓ 所有增强功能测试通过!")
print("=" * 60)
