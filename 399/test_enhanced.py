import numpy as np
import pandas as pd
import time
from data_generator import generate_aggregated_data, split_data
from bayesian_hmm import BayesianHMMLoadDisaggregator
from multi_scale_cnn import MultiScaleCNNDisaggregator
from energy_analyzer import EnergyAnalyzer
from energy_saver import EnergySavingAdvisor, ACTION_CATEGORIES


APPLIANCE_NAMES = ['air_conditioner', 'refrigerator', 'washing_machine', 'lighting']
APPLIANCE_CN = {
    'air_conditioner': '空调',
    'refrigerator': '冰箱',
    'washing_machine': '洗衣机',
    'lighting': '照明'
}


def test_bayesian_hmm():
    print("=" * 70)
    print("测试1: 贝叶斯非参数HMM (自动学习状态数)")
    print("=" * 70)
    
    df = generate_aggregated_data(days=3, sample_interval_min=5)
    
    individual_powers = {}
    for app in APPLIANCE_NAMES:
        individual_powers[app] = df[f'{app}_power'].values
    
    print("\n训练贝叶斯HMM...")
    start_time = time.time()
    disaggregator = BayesianHMMLoadDisaggregator(APPLIANCE_NAMES, max_states_per_appliance=10)
    disaggregator.fit(df['total_power'].values, individual_powers)
    train_time = time.time() - start_time
    
    print(f"\n✓ 训练完成, 耗时: {train_time:.2f}秒")
    
    print("\n各电器学习到的状态数:")
    model_info = disaggregator.get_model_info()
    for app, info in model_info.items():
        print(f"  {APPLIANCE_CN[app]}: {info['effective_states']} 个状态")
        print(f"    功率等级: {[round(p, 0) for p in info['power_levels']]} W")
    
    print("\n执行多尺度负荷分解...")
    start_time = time.time()
    results = disaggregator.disaggregate(df['total_power'].values, method='multi_scale')
    infer_time = time.time() - start_time
    print(f"✓ 分解完成, 耗时: {infer_time:.3f}秒")
    
    print("\n分解结果统计:")
    for app, powers in results.items():
        true_mean = np.mean(individual_powers[app])
        pred_mean = np.mean(powers)
        error = abs(true_mean - pred_mean) / true_mean * 100
        print(f"  {APPLIANCE_CN[app]}: 预测平均={pred_mean:.1f}W, 实际={true_mean:.1f}W, 误差={error:.1f}%")
    
    return results, model_info


def test_multi_scale_cnn():
    print("\n" + "=" * 70)
    print("测试2: 多尺度CNN (捕捉不同时长电器特征)")
    print("=" * 70)
    
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    train_df, val_df, test_df = split_data(df, train_ratio=0.7, val_ratio=0.15)
    
    def create_targets(data_df):
        n = len(data_df)
        y = []
        for i in range(n):
            y.append([data_df[f'{app}_power'].values[i] for app in APPLIANCE_NAMES])
        return np.array(y)
    
    window_size = 60
    y_train = create_targets(train_df)[window_size-1:]
    y_val = create_targets(val_df)[window_size-1:]
    
    print(f"\n训练数据: {len(train_df)} 样本")
    print(f"目标形状: {y_train.shape}")
    
    print("\n构建多尺度CNN模型...")
    cnn = MultiScaleCNNDisaggregator(
        window_size=window_size,
        n_appliances=4,
        appliance_names=APPLIANCE_NAMES,
        scales=[5, 15, 30]
    )
    cnn.build_model(n_filters=16)
    cnn.compile(learning_rate=0.001)
    
    print(f"  时间尺度: {cnn.scales} 个样本窗口")
    print(f"  模型参数: {cnn.model.count_params()} 个")
    
    print("\n训练模型...")
    start_time = time.time()
    history = cnn.train(
        train_df['total_power'].values, y_train,
        val_df['total_power'].values, y_val,
        batch_size=32,
        epochs=5
    )
    train_time = time.time() - start_time
    print(f"✓ 训练完成, 耗时: {train_time:.2f}秒")
    print(f"  最终训练损失: {history['loss'][-1]:.4f}")
    
    print("\n测试多尺度分解...")
    start_time = time.time()
    results = cnn.disaggregate(test_df['total_power'].values[:500])
    infer_time = time.time() - start_time
    print(f"✓ 分解完成, 耗时: {infer_time:.3f}秒")
    
    print("\n分解结果统计:")
    for app, powers in results.items():
        true_powers = test_df[f'{app}_power'].values[:500]
        true_mean = np.mean(true_powers)
        pred_mean = np.mean(powers)
        print(f"  {APPLIANCE_CN[app]}: 预测={pred_mean:.1f}W, 实际={true_mean:.1f}W")
    
    return results


def test_actionable_saving_tips():
    print("\n" + "=" * 70)
    print("测试3: 具体可操作节电建议 (关电源/换节能/错峰)")
    print("=" * 70)
    
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    
    disaggregated_data = {
        app: df[f'{app}_power'].values
        for app in APPLIANCE_NAMES
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=5)
    report = analyzer.generate_comprehensive_report(disaggregated_data, df.index)
    
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    tips = advisor.generate_all_tips(report)
    
    grade = advisor.get_energy_grade(
        report['summary']['total_energy_kwh'],
        report['summary']['analysis_period_days']
    )
    
    print(f"\n能耗等级: {grade['grade']} - {grade['description']}")
    print(f"预估月均电费: {grade['monthly_estimate'] * 0.6:.2f} 元")
    
    print(f"\n共生成 {tips['summary']['total_tips_count']} 条节电建议")
    print(f"预计月度节电: {tips['summary']['estimated_monthly_saving_kwh']:.2f} kWh")
    print(f"预计月度节约: {tips['summary']['estimated_monthly_saving_money']:.2f} 元")
    
    print("\n" + "-" * 70)
    print("按类别分组的节电建议:")
    print("-" * 70)
    
    tips_by_category = {}
    for tip in tips['appliance_tips']:
        cat = tip['category']
        if cat not in tips_by_category:
            tips_by_category[cat] = []
        tips_by_category[cat].append(tip)
    
    for cat, cat_tips in tips_by_category.items():
        cat_name = ACTION_CATEGORIES.get(cat, cat)
        print(f"\n【{cat_name}】 - 共 {len(cat_tips)} 条建议:")
        
        for i, tip in enumerate(cat_tips[:2], 1):
            priority_mark = "★" if tip['priority'] == 'high' else "☆" if tip['priority'] == 'medium' else "·"
            print(f"\n  {priority_mark} [{tip['appliance_name']}] {tip['action']}")
            print(f"    操作步骤:")
            for step in tip['steps']:
                print(f"      • {step}")
            print(f"    预计节省: {tip['estimated_saving_kwh']:.2f} kWh/月 ({tip['estimated_saving_money']:.2f} 元/月)")
    
    print("\n" + "-" * 70)
    print("通用节电建议:")
    print("-" * 70)
    
    for tip in tips['general_tips']:
        priority_mark = "★" if tip['priority'] == 'high' else "☆" if tip['priority'] == 'medium' else "·"
        print(f"\n  {priority_mark} [{tip['category_name']}] {tip['action']}")
        print(f"    操作步骤:")
        for step in tip['steps']:
            print(f"      • {step}")
    
    return tips


def main():
    print("\n" + "=" * 70)
    print("电量负荷分解系统 - 增强功能测试")
    print("=" * 70)
    print("\n新功能:")
    print("  1. 贝叶斯非参数HMM - 自动学习状态数")
    print("  2. 多尺度时间窗口 - 捕捉不同时长电器特征")
    print("  3. 具体操作建议 - 关电源/换节能/错峰使用")
    print("")
    
    total_start = time.time()
    
    try:
        hmm_results, model_info = test_bayesian_hmm()
        
        cnn_results = test_multi_scale_cnn()
        
        tips = test_actionable_saving_tips()
        
        print("\n" + "=" * 70)
        print("所有增强功能测试完成!")
        print("=" * 70)
        print(f"总耗时: {time.time() - total_start:.2f}秒")
        
        print("\n功能总结:")
        print("  ✓ 贝叶斯HMM: 自动学习状态数，无需预先设定")
        print("  ✓ 多尺度CNN: 多时间尺度特征提取，提高分解精度")
        print("  ✓ 可操作建议: 提供具体步骤指导用户节电")
        
        print("\n建议类别:")
        for cat, name in ACTION_CATEGORIES.items():
            print(f"  - {name}")
        
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
