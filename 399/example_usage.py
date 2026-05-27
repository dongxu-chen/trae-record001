import numpy as np
import pandas as pd

from data_generator import generate_aggregated_data
from hmm_model import HMMLoadDisaggregator
from cnn_model import CNNDisaggregator
from energy_analyzer import EnergyAnalyzer
from energy_saver import EnergySavingAdvisor


def example_hmm_disaggregation():
    print("=" * 50)
    print("示例1: HMM 负荷分解")
    print("=" * 50)
    
    df = generate_aggregated_data(days=3, sample_interval_min=5)
    
    appliance_config = {
        'air_conditioner': 4,
        'refrigerator': 2,
        'washing_machine': 3,
        'lighting': 3
    }
    
    individual_powers = {}
    for app in appliance_config.keys():
        individual_powers[app] = df[f'{app}_power'].values
    
    print("训练HMM模型...")
    hmm = HMMLoadDisaggregator(appliance_config)
    hmm.fit(df['total_power'].values, individual_powers)
    
    print("执行分解...")
    results = hmm.disaggregate(df['total_power'].values, method='viterbi_combinatorial')
    
    print("\n分解结果 (前10个样本):")
    print("时间\t\t\t总功率\t空调\t冰箱\t洗衣机\t照明")
    for i in range(10):
        print(f"{df.index[i].strftime('%H:%M')}\t"
              f"{df['total_power'].values[i]:.0f}\t"
              f"{results['air_conditioner'][i]:.0f}\t"
              f"{results['refrigerator'][i]:.0f}\t"
              f"{results['washing_machine'][i]:.0f}\t"
              f"{results['lighting'][i]:.0f}")
    
    return results


def example_energy_analysis():
    print("\n" + "=" * 50)
    print("示例2: 能耗分析与占比统计")
    print("=" * 50)
    
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    
    disaggregated_data = {
        'air_conditioner': df['air_conditioner_power'].values,
        'refrigerator': df['refrigerator_power'].values,
        'washing_machine': df['washing_machine_power'].values,
        'lighting': df['lighting_power'].values
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=5)
    report = analyzer.generate_comprehensive_report(disaggregated_data, df.index)
    
    print(f"\n总能耗: {report['summary']['total_energy_kwh']:.2f} kWh")
    print(f"分析周期: {report['summary']['analysis_period_days']} 天\n")
    
    print("各电器能耗占比:")
    print("-" * 50)
    pie_data = analyzer.get_energy_pie_data(report['energy_analysis'])
    for item in pie_data:
        bar = '█' * int(item['ratio'] * 30)
        print(f"{item['name']:6s} |{bar:<30}| {item['ratio']*100:5.1f}% ({item['value']:.2f} kWh)")
    
    return report


def example_saving_tips():
    print("\n" + "=" * 50)
    print("示例3: 节电建议生成")
    print("=" * 50)
    
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    
    disaggregated_data = {
        'air_conditioner': df['air_conditioner_power'].values,
        'refrigerator': df['refrigerator_power'].values,
        'washing_machine': df['washing_machine_power'].values,
        'lighting': df['lighting_power'].values
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
    print(f"预估月均电费: {grade['monthly_estimate'] * 0.6:.2f} 元\n")
    
    print("高优先级节电建议:")
    print("-" * 50)
    high_priority_tips = [t for t in tips['appliance_tips'] if t['priority'] == 'high']
    for i, tip in enumerate(high_priority_tips, 1):
        print(f"\n{i}. [{tip['appliance_name']}]")
        print(f"   {tip['tip']}")
        print(f"   预计节省: {tip['estimated_saving_money']:.2f} 元/月")
    
    print(f"\n预计总月节电: {tips['summary']['estimated_monthly_saving_kwh']:.2f} kWh")
    print(f"预计总月节约: {tips['summary']['estimated_monthly_saving_money']:.2f} 元")
    
    return tips


def example_complete_workflow():
    print("\n" + "=" * 50)
    print("示例4: 完整工作流程")
    print("=" * 50)
    
    print("\n步骤1: 生成模拟用电数据")
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    print(f"  ✓ 生成 {len(df)} 条数据记录")
    
    print("\n步骤2: HMM负荷分解")
    appliance_config = {
        'air_conditioner': 4,
        'refrigerator': 2,
        'washing_machine': 3,
        'lighting': 3
    }
    
    individual_powers = {app: df[f'{app}_power'].values for app in appliance_config}
    
    hmm = HMMLoadDisaggregator(appliance_config)
    hmm.fit(df['total_power'].values, individual_powers)
    disaggregated = hmm.disaggregate(df['total_power'].values)
    print("  ✓ 完成负荷分解")
    
    print("\n步骤3: 能耗分析")
    analyzer = EnergyAnalyzer(sample_interval_min=5)
    report = analyzer.generate_comprehensive_report(disaggregated, df.index)
    print("  ✓ 完成能耗分析")
    
    print("\n步骤4: 生成节电建议")
    advisor = EnergySavingAdvisor(electricity_price=0.6)
    tips = advisor.generate_all_tips(report)
    grade = advisor.get_energy_grade(
        report['summary']['total_energy_kwh'],
        report['summary']['analysis_period_days']
    )
    print("  ✓ 生成节电建议")
    
    print("\n" + "=" * 50)
    print("最终结果摘要")
    print("=" * 50)
    print(f"\n分析周期: {report['summary']['analysis_period_days']} 天")
    print(f"总能耗: {report['summary']['total_energy_kwh']:.2f} kWh")
    print(f"能耗等级: {grade['grade']}")
    print(f"可优化建议数: {tips['summary']['total_tips_count']} 条")
    print(f"月度节电潜力: {tips['summary']['estimated_monthly_saving_kwh']:.2f} kWh")
    print(f"月度节约费用: {tips['summary']['estimated_monthly_saving_money']:.2f} 元")
    
    print("\n各电器能耗占比:")
    for app, data in report['energy_analysis'].items():
        print(f"  {data['name_cn']}: {data['energy_ratio']*100:.1f}%")


if __name__ == '__main__':
    print("电量负荷分解系统 - 使用示例")
    print("选择要运行的示例:")
    print("1. HMM 负荷分解示例")
    print("2. 能耗分析示例")
    print("3. 节电建议示例")
    print("4. 完整工作流程")
    print("5. 运行所有示例")
    
    choice = input("\n请输入选择 (1-5): ").strip()
    
    if choice == '1':
        example_hmm_disaggregation()
    elif choice == '2':
        example_energy_analysis()
    elif choice == '3':
        example_saving_tips()
    elif choice == '4':
        example_complete_workflow()
    elif choice == '5':
        example_hmm_disaggregation()
        example_energy_analysis()
        example_saving_tips()
        example_complete_workflow()
    else:
        print("运行完整工作流程...")
        example_complete_workflow()
