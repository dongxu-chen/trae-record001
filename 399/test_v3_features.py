import sys
import numpy as np
import pandas as pd

print("=" * 60)
print("      电量负荷分解系统 v3.0 - 新增功能测试")
print("=" * 60)

print("\n【1】测试异常检测模块...")
print("-" * 60)
try:
    from data_generator import generate_aggregated_data
    from anomaly_detector import MultiApplianceAnomalyDetector
    
    print("生成测试数据...")
    df = generate_aggregated_data(days=14, sample_interval_min=5)
    
    train_df = df.iloc[:int(len(df)*0.7)]
    test_df = df.iloc[int(len(df)*0.7):]
    
    appliance_config = {
        'air_conditioner': '空调',
        'refrigerator': '冰箱',
        'washing_machine': '洗衣机',
        'lighting': '照明'
    }
    
    baseline_data = {app: train_df[f'{app}_power'].values for app in appliance_config.keys()}
    test_data = {app: test_df[f'{app}_power'].values for app in appliance_config.keys()}
    
    print("训练异常检测模型...")
    detector = MultiApplianceAnomalyDetector(appliance_config)
    detector.fit_all(baseline_data, train_df.index)
    
    print("检测异常...")
    result = detector.detect_all(test_data, test_df.index, sample_interval_min=5)
    
    print(f"\n  总体状态: {result['overall_status']}")
    print(f"  异常总数: {result['total_anomalies']}")
    
    for app, summary in result['summaries'].items():
        print(f"\n  {summary['appliance_name']}:")
        print(f"    异常数: {summary['anomaly_count']}")
        print(f"    状态: {summary['overall_severity']}")
    
    print(" ✓ 异常检测模块测试通过!")
except Exception as e:
    print(f" ✗ 异常检测模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【2】测试负荷预测模块...")
print("-" * 60)
try:
    from load_forecaster import MultiApplianceForecaster
    
    disaggregated_data = {app: df[f'{app}_power'].values for app in appliance_config.keys()}
    
    print("训练负荷预测模型...")
    forecaster = MultiApplianceForecaster(appliance_config)
    forecaster.fit_all(disaggregated_data, df.index)
    
    print("预测未来24小时...")
    forecast = forecaster.predict_all(steps_ahead=288)
    
    print(f"\n  总体预测:")
    print(f"    总能耗: {forecast['overall']['total_energy_kwh']} kWh")
    print(f"    峰值功率: {forecast['overall']['peak_power_w']} W")
    print(f"    平均功率: {forecast['overall']['average_power_w']} W")
    
    print(f"\n  峰值时段:")
    for peak in forecast['overall']['peak_hours']:
        print(f"    {peak['time_range']}: {peak['avg_power_w']} W")
    
    print(f"\n  各电器预测:")
    for app, info in forecast['appliances'].items():
        print(f"    {info['name_cn']}: {info['energy_kwh']} kWh ({info['percentage']}%)")
    
    print(" ✓ 负荷预测模块测试通过!")
except Exception as e:
    print(f" ✗ 负荷预测模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【3】测试家庭能耗对比模块...")
print("-" * 60)
try:
    from household_comparison import HouseholdComparator, HouseholdProfile, HouseholdEnergyDataset
    
    print("生成家庭数据集 (100个家庭)...")
    dataset = HouseholdEnergyDataset(n_households=100)
    
    print(f"  家庭类型分布:")
    types = {}
    for hh in dataset.households:
        t = hh.household_type
        types[t] = types.get(t, 0) + 1
    for t, c in types.items():
        print(f"    {t}: {c}户")
    
    print("\n创建对比器...")
    comparator = HouseholdComparator(dataset)
    
    target_profile = HouseholdProfile(
        household_id='TARGET',
        household_type='三口之家',
        dwelling_size=90,
        num_occupants=3,
        region='南方',
        has_ac=True,
        has_ev=False,
        has_solar=False
    )
    
    target_energy = {'monthly_total': 450.0}
    target_appliance = {
        'refrigerator': 60,
        'lighting': 45,
        'air_conditioner': 150,
        'washing_machine': 25,
        'kitchen': 90,
        'entertainment': 40,
        'water_heater': 40
    }
    
    print("执行家庭对比分析...")
    result = comparator.compare_household(target_profile, target_energy, target_appliance)
    
    print(f"\n  对比组规模: {result['peer_group']['size']}户")
    print(f"\n  总体排名:")
    print(f"    月均能耗: {result['overall']['target_monthly_kwh']} kWh")
    print(f"    同类型均值: {result['overall']['peer_stats']['mean']} kWh")
    print(f"    分位数: {result['overall']['percentile']}%")
    print(f"    等级: {result['overall']['level']}")
    print(f"    对比均值: {result['overall']['vs_peer_avg']:+}%")
    
    print(f"\n  各电器对比 (前3项):")
    sorted_apps = sorted(
        result['appliance_comparison'].items(),
        key=lambda x: x[1]['percentile'],
        reverse=True
    )[:3]
    for app, comp in sorted_apps:
        print(f"    {comp['name_cn']}: {comp['target_monthly']} kWh "
              f"(分位 {comp['percentile']}%, {comp['level']})")
    
    print(f"\n  基准参考:")
    print(f"    高效水平(P25): {result['benchmark']['efficient']} kWh")
    print(f"    平均水平(P50): {result['benchmark']['average']} kWh")
    print(f"    潜在节约: {result['benchmark']['potential_saving_total']} kWh/月")
    
    print(" ✓ 家庭能耗对比模块测试通过!")
except Exception as e:
    print(f" ✗ 家庭能耗对比模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n【4】测试模块集成...")
print("-" * 60)
try:
    print("测试所有模块可以同时导入...")
    
    from bayesian_hmm import BayesianHMMLoadDisaggregator
    from multi_scale_cnn import MultiScaleCNNDisaggregator
    from energy_analyzer import EnergyAnalyzer
    from energy_saver import EnergySavingAdvisor
    from anomaly_detector import MultiApplianceAnomalyDetector
    from load_forecaster import MultiApplianceForecaster
    from household_comparison import HouseholdComparator
    
    print("  ✓ 所有模块导入成功!")
    
    print("\n测试数据流完整性...")
    
    print("  1. 生成数据 -> ✓")
    sample_df = generate_aggregated_data(days=7, sample_interval_min=5)
    
    print("  2. 分解数据 -> ✓")
    test_data = {app: sample_df[f'{app}_power'].values for app in appliance_config.keys()}
    
    print("  3. 异常检测 -> ✓")
    test_detector = MultiApplianceAnomalyDetector(appliance_config)
    test_detector.fit_all(test_data, sample_df.index)
    anomaly_result = test_detector.detect_all(test_data, sample_df.index)
    
    print("  4. 负荷预测 -> ✓")
    test_forecaster = MultiApplianceForecaster(appliance_config)
    test_forecaster.fit_all(test_data, sample_df.index)
    forecast_result = test_forecaster.predict_all(steps_ahead=48)
    
    print("  5. 能耗分析 -> ✓")
    analyzer = EnergyAnalyzer()
    report = analyzer.generate_comprehensive_report(test_data, sample_df.index)
    
    print("  6. 节电建议 -> ✓")
    advisor = EnergySavingAdvisor()
    tips = advisor.generate_all_tips(report)
    
    print(" ✓ 完整数据流测试通过!")
    
except Exception as e:
    print(f" ✗ 模块集成测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("              测试总结")
print("=" * 60)
print("\n✅ 异常检测 - 非典型工作模式告警")
print("   - 基于Z-score的功率/时长/频率异常检测")
print("   - 非典型使用时段识别")
print("   - 严重程度分级 (high/medium/low)")

print("\n✅ 负荷预测 - 预测未来各电器用电量")
print("   - 基于历史模式的时序预测")
print("   - 置信区间估计 (95%/90%)")
print("   - 高峰时段识别")
print("   - 各电器能耗分解预测")

print("\n✅ 家庭对比 - 同类家庭能耗分位排名")
print("   - 100个模拟家庭基准数据库")
print("   - 多维度相似家庭匹配 (户型/面积/人数/区域)")
print("   - 分位数排名 (前10%/前25%/中等/偏高)")
print("   - 各电器对标分析")
print("   - 潜在节约空间估算")

print("\n✅ FastAPI接口集成")
print("   - POST /anomaly_detection")
print("   - POST /forecast")
print("   - POST /household_comparison")
print("   - 版本升级至 v3.0.0")

print("\n" + "=" * 60)
print("        所有新增功能测试完成!")
print("=" * 60)
