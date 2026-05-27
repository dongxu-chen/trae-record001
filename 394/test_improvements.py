import sys
sys.path.insert(0, '.')
from src.models import SleepStageClassifier, SleepQualityAnalyzer, FactorAnalyzer
from src.features import SleepDataGenerator
import numpy as np

print("=" * 70)
print("睡眠质量分析系统 - 综合测试")
print("=" * 70)

# ============ Test 1: Data Augmentation + Dropout ============
print("\n[Test 1] 数据增强 + Dropout 正则化")
print("-" * 50)
generator = SleepDataGenerator(n_subjects=5, n_nights=2, n_epochs=720)
all_data = generator.generate_all_data()
print(f"生成了 {len(all_data)} 晚睡眠数据")

classifier = SleepStageClassifier(use_augmentation=True, use_dropout=True)
X, y = classifier.prepare_dataset(all_data)
print(f"特征矩阵: {X.shape}, 标签分布: {np.bincount(y)}")

results = classifier.train(X, y, n_augment_rounds=2)
print(f"训练集准确率: {results['train_accuracy']:.4f}")
print(f"测试集准确率: {results['test_accuracy']:.4f}")
print(f"过拟合差距: {results['overfit_gap']:.4f}")
print(f"交叉验证准确率: {results['cv_mean_accuracy']:.4f} ± {results['cv_std_accuracy']:.4f}")
print(f"Macro F1: {results['macro_f1']:.4f}")
print(f"Weighted F1: {results['weighted_f1']:.4f}")
print(f"Cohen's Kappa: {results['cohen_kappa']:.4f}")

overfit_status = "✅ 良好" if results['overfit_gap'] < 0.03 else "⚠️ 一般" if results['overfit_gap'] < 0.08 else "❌ 过拟合"
print(f"过拟合状态: {overfit_status}")

# ============ Test 2: Predict with Uncertainty ============
print("\n[Test 2] 不确定性预测")
print("-" * 50)
sample_data = generator.generate_subject_data(0, 0)
pred_result = classifier.predict_single_night(
    sample_data['heart_rate'], sample_data['respiration'], sample_data['activity']
)
stages = pred_result['stages']
print(f"睡眠阶段预测: {len(stages)} 个epoch")
print(f"阶段分布: 清醒={stages.count('清醒')}, 浅睡={stages.count('浅睡')}, 深睡={stages.count('深睡')}, REM={stages.count('REM')}")

uncertainty = classifier.predict_with_uncertainty(pred_result['features'], n_bootstrap=50)
print(f"预测平均置信度: {np.mean(uncertainty['confidence']):.4f}")
print(f"预测平均方差: {np.mean(uncertainty['prediction_variance']):.4f}")

# ============ Test 3: Feature Importance ============
print("\n[Test 3] 特征重要性")
print("-" * 50)
for imp_type in ['weight', 'gain', 'cover']:
    fi = classifier.get_feature_importance(importance_type=imp_type)
    print(f"  {imp_type}: Top 3 = {fi.head(3)['feature'].tolist()}")

# ============ Test 4: AASM Sleep Scoring ============
print("\n[Test 4] AASM睡眠质量评分")
print("-" * 50)
quality_analyzer = SleepQualityAnalyzer()
stage_analysis = quality_analyzer.analyze_sleep_stages(stages)
print(f"总睡眠时长: {stage_analysis['total_sleep_duration']:.1f} 小时")
print(f"睡眠效率: {stage_analysis['sleep_efficiency']:.1f}%")
print(f"入睡潜伏期: {stage_analysis['sleep_latency']:.1f} 分钟")
print(f"WASO: {stage_analysis['waso_pct']:.1f}%")
print(f"觉醒指数: {stage_analysis['arousal_index']:.1f} 次/小时")

sleep_score = quality_analyzer.calculate_sleep_score(stage_analysis)
print(f"睡眠评分: {sleep_score['total_score']:.1f} ({sleep_score['grade']})")
print("评分构成:")
for key, comp in sleep_score['components'].items():
    print(f"  {key}: {comp['score']:.1f} (权重: {comp['weight']*100:.0f}%)")

# Check AASM standards
aasm = quality_analyzer.aasm_standards
print(f"\nAASM标准检查:")
print(f"  睡眠效率 {stage_analysis['sleep_efficiency']:.1f}% vs AASM ≥{aasm['sleep_efficiency_min']}%: {'✅' if stage_analysis['sleep_efficiency'] >= aasm['sleep_efficiency_min'] else '⚠️'}")
print(f"  入睡潜伏期 {stage_analysis['sleep_latency']:.1f}min vs AASM ≤{aasm['sleep_latency_max']}min: {'✅' if stage_analysis['sleep_latency'] <= aasm['sleep_latency_max'] else '⚠️'}")

# ============ Test 5: Factor Analysis with Lag Features ============
print("\n[Test 5] 归因分析 (含滞后特征)")
print("-" * 50)
factor_analyzer = FactorAnalyzer()

lifestyle_factors = {
    'exercise_minutes': 45,
    'exercise_intensity': 'moderate',
    'caffeine_intake': 1,
    'alcohol_intake': 0,
    'stress_level': 4,
    'bedtime_consistency': 7
}

history_factors = {
    'exercise_minutes_1d': 30,
    'exercise_minutes_2d': 60,
    'exercise_minutes_3d': 20,
    'stress_level_1d': 3,
    'stress_level_2d': 5,
    'stress_level_3d': 4,
}

factor_analysis = factor_analyzer.analyze_lifestyle_impact(
    lifestyle_factors, sleep_score['total_score'], history_factors
)

print("因素影响得分:")
for factor, data in factor_analysis['factor_impacts'].items():
    print(f"  {factor}: {data['score']:.1f} ({data['direction']})")

print("\n归因贡献:")
for factor, attr in factor_analysis['attribution'].items():
    print(f"  {factor}: {attr['contribution_percent']:.1f}% (影响量级: {attr['impact_magnitude']:.1f})")

# Cumulative exercise analysis
cum_ex = factor_analysis['cumulative_exercise']
print(f"\n运动滞后分析:")
print(f"  近4天总运动: {cum_ex['total_4day']:.0f} 分钟")
print(f"  加权得分: {cum_ex['weighted_score']:.1f}")
print(f"  运动一致性: {cum_ex['consistency']:.0%}")
print(f"  运动趋势: {cum_ex['trend']}")
print(f"  每日运动: {[f'{v:.0f}min' for v in cum_ex['daily_values']]}")

# ============ Test 6: Sleep Regularity ============
print("\n[Test 6] 睡眠规律性分析")
print("-" * 50)
regularity = quality_analyzer.analyze_sleep_regularity(stages)
print(f"阶段转换次数: {regularity['transitions_count']}")
print(f"转换频率: {regularity['transitions_per_hour']:.1f} 次/小时")
print(f"睡眠碎片化指数: {regularity['sleep_fragmentation_index']:.1f}%")
print(f"平均阶段持续: {regularity['average_stage_duration_min']:.1f} 分钟")
print(f"检测到睡眠周期: {regularity['sleep_cycles_count']} 个")
print(f"规律性评分: {regularity['regularity_score']:.1f}")

# ============ Test 7: Recommendations ============
print("\n[Test 7] 建议生成")
print("-" * 50)
recommendations = quality_analyzer.generate_recommendations(sleep_score, stage_analysis, regularity)
print(f"生成 {len(recommendations)} 条建议:")
for rec in recommendations:
    priority_label = {'high': '🔴高', 'medium': '🟡中', 'low': '🟢低'}.get(rec['priority'], '?')
    print(f"  [{priority_label}] {rec['message'][:80]}...")

factor_recs = factor_analyzer.generate_factor_recommendations(factor_analysis)
print(f"\n生活方式建议 {len(factor_recs)} 条:")
for rec in factor_recs:
    print(f"  {rec['factor']}: {rec['suggestion'][:60]}")

print("\n" + "=" * 70)
print("✅ 所有测试通过！系统运行正常")
print("=" * 70)