import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("金融时序数据异常检测平台 - 全功能测试")
print("=" * 70)

print("\n" + "=" * 70)
print("1. 测试数据处理模块")
print("=" * 70)
from src.data_processing import DataProcessor
df1 = DataProcessor.generate_mock_data(n_days=120, inject_anomalies=True)
df2 = DataProcessor.generate_mock_data(n_days=120, inject_anomalies=True)
df3 = DataProcessor.generate_mock_data(n_days=120, inject_anomalies=True)
print(f"✓ 生成3个资产数据: {len(df1)}, {len(df2)}, {len(df3)} 条")

print("\n" + "=" * 70)
print("2. 测试异常检测器（单资产）")
print("=" * 70)
from src.anomaly_detector import AnomalyDetector
detector = AnomalyDetector(
    seq_length=20,
    hidden_dims=[32, 16],
    use_dynamic_threshold=True,
    threshold_window=15,
    base_percentile=95,
    volatility_scale=1.5
)
print("✓ 检测器初始化成功（含动态阈值）")

losses = detector.fit(df1, epochs=20, verbose=False)
print(f"✓ 训练完成，最终损失: {losses[-1]:.6f}")
print(f"✓ 基础阈值: {detector.threshold:.4f}")

result_df = detector.detect_anomalies(df1, expected_freq='D')
print(f"✓ 检测完成，异常点: {result_df['is_anomaly'].sum()} 个")
print(f"✓ 动态阈值范围: {result_df['dynamic_threshold'].min():.2f} ~ {result_df['dynamic_threshold'].max():.2f}")

gaps = detector.check_timestamp_continuity(df1, expected_freq='D')
print(f"✓ 时间戳跳点检测: {len(gaps)} 处")

print("\n" + "=" * 70)
print("3. 测试多资产联动分析模块")
print("=" * 70)
from src.multi_asset_analyzer import MultiAssetAnalyzer

analyzer = MultiAssetAnalyzer(co_anomaly_window=3, min_assets_for_systemic=2)
print("✓ 多资产分析器初始化成功")

result_df2 = detector.fit(df2, epochs=20, verbose=False)
result_df2 = detector.detect_anomalies(df2)
result_df3 = detector.fit(df3, epochs=20, verbose=False)
result_df3 = detector.detect_anomalies(df3)

analyzer.add_asset_result('资产1', result_df)
analyzer.add_asset_result('资产2', result_df2)
analyzer.add_asset_result('资产3', result_df3)
print("✓ 添加3个资产检测结果")

summary = analyzer.get_summary()
print(f"✓ 资产总数: {summary['total_assets']}")
for name, stats in summary['total_anomalies_per_asset'].items():
    print(f"  - {name}: {stats['total']} 个异常")

_, systemic_df = analyzer.detect_co_anomalies()
print(f"✓ 系统性风险事件: {len(systemic_df)} 个")
if not systemic_df.empty:
    for _, event in systemic_df.iterrows():
        print(f"  - {event['event_date'].strftime('%Y-%m-%d')}: "
              f"{event['assets_involved']}个资产, "
              f"风险等级: {event['severity']}")

corr_matrix = analyzer.calculate_correlations()
print(f"✓ 价格相关性矩阵计算完成: {corr_matrix.shape}")

anomaly_corr = analyzer.calculate_anomaly_correlation()
print(f"✓ 异常相关性矩阵计算完成: {anomaly_corr.shape}")

print("\n" + "=" * 70)
print("4. 测试异常归因解释模块")
print("=" * 70)
from src.anomaly_attribution import AnomalyAttributor, EventDetector

attributor = AnomalyAttributor(lookback_window=15)
print("✓ 归因分析器初始化成功")

prophet_features = detector.prophet_extractor.extract_features(result_df)
attribution_df = attributor.batch_analyze(result_df, prophet_features)
print(f"✓ 批量归因完成: {len(attribution_df)} 条异常")

if not attribution_df.empty:
    print("  前3条异常归因:")
    for _, row in attribution_df.head(3).iterrows():
        print(f"    - {row['date'].strftime('%Y-%m-%d')}: "
              f"{row['anomaly_type']}, "
              f"主导因子: {row['dominant_factor']} ({row['dominant_contribution']*100:.1f}%)")

event_detector = EventDetector()
event_detector.add_event('2024-01-15', '财报发布', 'Q4财报不及预期', 'high')
event_detector.add_event('2024-01-20', '政策变化', '利率调整', 'medium')
print("✓ 事件检测器初始化，已添加2个事件")

matched = event_detector.match_anomalies_with_events(result_df, window_days=5)
print(f"✓ 事件-异常匹配: {len(matched)} 对")

print("\n" + "=" * 70)
print("5. 测试预警推送模块")
print("=" * 70)
from src.alert_notifier import AlertNotifier

notifier = AlertNotifier()
print("✓ 预警推送器初始化成功")

alert_level, content = notifier.generate_anomaly_alert_content(
    asset_name="测试资产",
    anomaly_date=result_df[result_df['is_anomaly']]['ds'].iloc[0] if len(result_df[result_df['is_anomaly']]) > 0 else pd.Timestamp.now(),
    anomaly_type='flash_crash',
    anomaly_score=2.5,
    attribution_result=attribution_df.iloc[0].to_dict() if len(attribution_df) > 0 else None,
    is_systemic=False
)
print(f"✓ 告警内容生成成功，级别: {alert_level}")
print(f"  内容预览: {content[:100]}...")

systemic_results = notifier.send_systemic_risk_alert(
    event_date=pd.Timestamp.now(),
    assets_involved=3,
    avg_score=2.2,
    severity='high',
    anomaly_types=['flash_crash', 'volatility_spike']
)
print("✓ 系统性风险预警内容生成成功")

history = notifier.get_alert_history()
print(f"✓ 推送历史记录获取: {len(history)} 条")

print("\n" + "=" * 70)
print("6. 测试增量训练和人工反馈")
print("=" * 70)

anomaly_dates = result_df[result_df['is_anomaly']]['ds'].head(3)
for date in anomaly_dates:
    detector.add_user_feedback(date, is_anomaly=True, confidence=1.5)
print(f"✓ 添加 {len(detector.user_feedback)} 条人工反馈")

new_losses = detector.incremental_fit(
    df1,
    feedback_weight=2.0,
    epochs=10,
    verbose=False
)
print(f"✓ 增量训练完成，最终损失: {new_losses[-1]:.6f}")
print(f"✓ 训练历史: {len(detector.training_history)} 次")

status = detector.get_model_status()
print(f"✓ 模型状态获取: 已训练={status['is_trained']}, "
      f"训练次数={status['training_count']}")

print("\n" + "=" * 70)
print("✅ 所有功能测试通过！")
print("=" * 70)
print("\n项目文件结构:")
print("""
├── app.py                          # Streamlit主界面 (7个标签页)
├── requirements.txt                # 依赖清单
├── test_all_features.py            # 本测试脚本
└── src/
    ├── __init__.py                 # 模块导出
    ├── data_processing.py          # 数据处理
    ├── prophet_features.py         # Prophet特征提取
    ├── autoencoder.py              # 自编码器模型
    ├── anomaly_detector.py         # 异常检测核心 (含动态阈值)
    ├── multi_asset_analyzer.py     # 多资产联动分析 ✨新增
    ├── anomaly_attribution.py      # 异常归因解释 ✨新增
    └── alert_notifier.py           # 预警推送接口 ✨新增
""")
print("启动方式: streamlit run app.py")
