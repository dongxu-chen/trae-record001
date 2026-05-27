import numpy as np
import pandas as pd
import time
from data_generator import generate_aggregated_data, split_data
from hmm_model import HMMLoadDisaggregator, estimate_performance
from cnn_model import CNNDisaggregator
from energy_analyzer import EnergyAnalyzer
from energy_saver import EnergySavingAdvisor


APPLIANCE_CONFIG = {
    'air_conditioner': 4,
    'refrigerator': 2,
    'washing_machine': 3,
    'lighting': 3
}

APPLIANCE_NAMES = list(APPLIANCE_CONFIG.keys())
APPLIANCE_CN = {
    'air_conditioner': '空调',
    'refrigerator': '冰箱',
    'washing_machine': '洗衣机',
    'lighting': '照明'
}


def test_data_generation():
    print("=" * 60)
    print("测试1: 数据生成模块")
    print("=" * 60)
    
    start_time = time.time()
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    elapsed = time.time() - start_time
    
    print(f"✓ 数据生成成功")
    print(f"  - 数据形状: {df.shape}")
    print(f"  - 时间跨度: {df.index[0]} 至 {df.index[-1]}")
    print(f"  - 总功率范围: {df['total_power'].min():.1f} - {df['total_power'].max():.1f} W")
    print(f"  - 生成耗时: {elapsed:.2f}秒")
    print()
    
    return df


def test_hmm_model(df):
    print("=" * 60)
    print("测试2: HMM负荷分解模型")
    print("=" * 60)
    
    train_df, _, test_df = split_data(df, train_ratio=0.7, val_ratio=0.15)
    
    individual_powers_train = {}
    individual_powers_test = {}
    
    for app in APPLIANCE_NAMES:
        individual_powers_train[app] = train_df[f'{app}_power'].values
        individual_powers_test[app] = test_df[f'{app}_power'].values
    
    print("训练HMM模型...")
    start_time = time.time()
    hmm = HMMLoadDisaggregator(APPLIANCE_CONFIG)
    hmm.fit(train_df['total_power'].values, individual_powers_train)
    train_time = time.time() - start_time
    print(f"✓ HMM训练完成, 耗时: {train_time:.2f}秒")
    
    print("执行负荷分解...")
    start_time = time.time()
    results = hmm.disaggregate(test_df['total_power'].values, method='viterbi_combinatorial')
    infer_time = time.time() - start_time
    print(f"✓ 分解完成, 耗时: {infer_time:.3f}秒")
    
    print("\n分解性能评估:")
    performance = estimate_performance(individual_powers_test, results)
    for app, metrics in performance.items():
        print(f"\n  {APPLIANCE_CN[app]}:")
        print(f"    MAE: {metrics['MAE']:.2f} W")
        print(f"    RMSE: {metrics['RMSE']:.2f} W")
        print(f"    R2: {metrics['R2']:.3f}")
    
    print()
    return hmm, results


def test_cnn_model(df):
    print("=" * 60)
    print("测试3: CNN负荷分解模型")
    print("=" * 60)
    
    window_size = 60
    
    train_df, val_df, test_df = split_data(df, train_ratio=0.7, val_ratio=0.15)
    
    def create_windows(data_df):
        n = len(data_df)
        X = []
        y = []
        for i in range(window_size - 1, n):
            X.append(data_df['total_power'].values[i - window_size + 1:i + 1])
            y.append([data_df[f'{app}_power'].values[i] for app in APPLIANCE_NAMES])
        return np.array(X), np.array(y)
    
    X_train, y_train = create_windows(train_df)
    X_val, y_val = create_windows(val_df)
    
    print(f"训练数据形状: X={X_train.shape}, y={y_train.shape}")
    
    print("构建并训练CNN模型...")
    start_time = time.time()
    cnn = CNNDisaggregator(
        window_size=window_size,
        n_appliances=4,
        appliance_names=APPLIANCE_NAMES
    )
    cnn.build_unet_model(n_filters=16)
    cnn.compile(learning_rate=0.001)
    
    history = cnn.train(
        X_train[:2000], y_train[:2000],
        X_val[:500], y_val[:500],
        batch_size=32,
        epochs=5
    )
    train_time = time.time() - start_time
    print(f"✓ CNN训练完成, 耗时: {train_time:.2f}秒")
    print(f"  最终训练损失: {history['loss'][-1]:.4f}")
    
    print("执行负荷分解...")
    start_time = time.time()
    results = cnn.disaggregate(test_df['total_power'].values[:1000])
    infer_time = time.time() - start_time
    print(f"✓ 分解完成, 耗时: {infer_time:.3f}秒")
    
    print("\n分解结果统计:")
    for app, powers in results.items():
        print(f"  {APPLIANCE_CN[app]}: 平均功率 = {np.mean(powers):.1f} W")
    
    print()
    return cnn, results


def test_energy_analysis(df, disaggregated_data):
    print("=" * 60)
    print("测试4: 能耗分析模块")
    print("=" * 60)
    
    analyzer = EnergyAnalyzer(sample_interval_min=5)
    
    start_time = time.time()
    report = analyzer.generate_comprehensive_report(disaggregated_data, df.index)
    elapsed = time.time() - start_time
    
    print(f"✓ 能耗分析完成, 耗时: {elapsed:.2f}秒")
    
    print(f"\n总能耗: {report['summary']['total_energy_kwh']:.2f} kWh")
    print(f"分析周期: {report['summary']['analysis_period_days']} 天")
    
    print("\n各电器能耗占比:")
    for app, data in report['energy_analysis'].items():
        print(f"  {data['name_cn']}: {data['total_kwh']:.3f} kWh ({data['energy_ratio']*100:.1f}%)")
    
    print(f"\n每日用电高峰时段: {report['daily_pattern']['peak_hours']}")
    print(f"周末/工作日用电比: {report['weekly_pattern']['weekend_weekday_ratio']:.2f}")
    
    print("\n使用习惯分析:")
    for app, habit in report['usage_habits'].items():
        print(f"  {habit['name_cn']}:")
        print(f"    每日使用次数: {habit['usage_frequency_per_day']:.1f}")
        print(f"    平均单次时长: {habit['avg_event_duration_min']:.1f} 分钟")
        print(f"    高峰使用时段: {habit['peak_usage_hours']}")
    
    print()
    return report


def test_saving_advisor(report):
    print("=" * 60)
    print("测试5: 节电建议生成模块")
    print("=" * 60)
    
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    
    start_time = time.time()
    tips = advisor.generate_all_tips(report)
    elapsed = time.time() - start_time
    
    print(f"✓ 节电建议生成完成, 耗时: {elapsed:.2f}秒")
    print(f"共生成 {tips['summary']['total_tips_count']} 条建议")
    
    print(f"\n预计月度节电: {tips['summary']['estimated_monthly_saving_kwh']:.2f} kWh")
    print(f"预计月度节约费用: {tips['summary']['estimated_monthly_saving_money']:.2f} 元")
    print(f"预计年度节电: {tips['summary']['estimated_yearly_saving_kwh']:.2f} kWh")
    print(f"预计年度节约费用: {tips['summary']['estimated_yearly_saving_money']:.2f} 元")
    
    grade = advisor.get_energy_grade(
        report['summary']['total_energy_kwh'],
        report['summary']['analysis_period_days']
    )
    print(f"\n能耗等级: {grade['grade']} - {grade['description']}")
    print(f"月度预估能耗: {grade['monthly_estimate']:.1f} kWh")
    
    print("\n重点节电建议:")
    for i, tip in enumerate(tips['appliance_tips'][:3], 1):
        priority_mark = "★" if tip['priority'] == 'high' else "☆" if tip['priority'] == 'medium' else "·"
        print(f"\n  {priority_mark} {tip['appliance_name']}:")
        print(f"    {tip['tip']}")
        print(f"    预计节省: {tip['estimated_saving_kwh']:.2f} kWh/月 ({tip['estimated_saving_money']:.2f} 元/月)")
    
    print()
    return tips, grade


def main():
    print("\n" + "=" * 60)
    print("电量负荷分解系统 - 完整测试")
    print("=" * 60 + "\n")
    
    total_start = time.time()
    
    try:
        df = test_data_generation()
        
        hmm, hmm_results = test_hmm_model(df)
        
        cnn, cnn_results = test_cnn_model(df)
        
        disaggregated_data = {
            app: df[f'{app}_power'].values
            for app in APPLIANCE_NAMES
        }
        
        report = test_energy_analysis(df, disaggregated_data)
        
        tips, grade = test_saving_advisor(report)
        
        print("=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        print(f"总耗时: {time.time() - total_start:.2f}秒")
        print(f"能耗等级: {grade['grade']}")
        print(f"可生成 {tips['summary']['total_tips_count']} 条节电建议")
        print(f"预计月度节电潜力: {tips['summary']['estimated_monthly_saving_kwh']:.2f} kWh")
        
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
