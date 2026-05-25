"""
天气衍生品定价模型 - 增强版演示
包含：非参数Bootstrap、历史极值回放、合成极端场景、自适应希腊值计算
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime

from weather_data import WeatherDataGenerator
from bootstrap_engine import BootstrapWeatherSimulator, BootstrapConfig
from monte_carlo_engine import MonteCarloPricingEngine, WeatherOptionContract, GreeksConfig
from stress_testing import StressTesting
from visualizer import Visualizer

try:
    from quantlib_pricer import QuantLibPricer
    HAS_QUANTLIB = True
except ImportError:
    HAS_QUANTLIB = False


def main():
    print("=" * 70)
    print("天气衍生品定价模型 - 增强版演示")
    print("包含: 非参数Bootstrap | 历史极值回放 | 自适应希腊值")
    print("=" * 70)

    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    visualizer = Visualizer(output_dir)

    print("\n" + "=" * 70)
    print("1. 生成历史气象数据 (2015-2024)")
    print("=" * 70)

    weather_gen = WeatherDataGenerator(
        location="Beijing",
        base_temperature=15.0,
        temp_volatility=10.0,
        base_rainfall=2.0,
        rainfall_volatility=5.0,
        seed=42
    )

    historical_data = weather_gen.generate_historical_years(2015, 2024)
    print(f"生成 {len(historical_data)} 天历史数据 (2015-2024)")

    print("\n历史年度HDD统计:")
    yearly_stats = historical_data.groupby('year').agg({
        'HDD': 'sum',
        'temperature': 'mean',
        'rainfall': 'sum'
    }).reset_index()
    print(yearly_stats.to_string(index=False))

    print("\n" + "=" * 70)
    print("2. 初始化Bootstrap模拟器")
    print("=" * 70)

    bootstrap_config = BootstrapConfig(
        block_size=7,
        n_bootstrap_samples=10000,
        preserve_seasonality=True,
        preserve_autocorrelation=True,
        seasonal_window=15,
        random_seed=12345
    )

    bootstrap_sim = BootstrapWeatherSimulator(historical_data, bootstrap_config)
    print("Bootstrap模拟器初始化完成")

    print("\nBootstrap HDD分布估计:")
    hdd_dist = bootstrap_sim.estimate_hdd_distribution(
        start_day=305,
        n_days=151,
        n_samples=5000
    )
    print(f"  均值: {hdd_dist['hdd']['mean']:,.2f}")
    print(f"  标准差: {hdd_dist['hdd']['std']:,.2f}")
    print(f"  5%分位: {hdd_dist['hdd']['q5']:,.2f}")
    print(f"  95%分位: {hdd_dist['hdd']['q95']:,.2f}")
    print(f"  偏度: {hdd_dist['hdd']['skewness']:.4f}")
    print(f"  峰度: {hdd_dist['hdd']['kurtosis']:.4f}")

    print("\n" + "=" * 70)
    print("3. 定义HDD看涨期权合约")
    print("=" * 70)

    contract = WeatherOptionContract(
        contract_type='HDD_call',
        strike=1500,
        tick_size=5000,
        notional=1000000,
        start_date='2024-11-01',
        end_date='2025-03-31',
        payment_date='2025-04-15'
    )

    print(f"合约类型: {contract.contract_type}")
    print(f"行权价: {contract.strike} HDD")
    print(f"乘数: ¥{contract.tick_size:,}/HDD点")
    print(f"期限: {contract.days_to_maturity}天")

    print("\n" + "=" * 70)
    print("4. 蒙特卡洛定价 (参数化 vs Bootstrap)")
    print("=" * 70)

    mc_engine = MonteCarloPricingEngine(
        n_simulations=5000,
        n_time_steps=150,
        seed=12345,
        bootstrap_simulator=bootstrap_sim
    )

    initial_temp = 5.0
    mu = 0.02
    sigma = 10.0
    ar1_coeff = 0.85
    seasonal_amplitude = 15.0

    print("\n4.1 参数化模型定价:")
    param_result = mc_engine.price_hdd_option(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03, use_bootstrap=False
    )
    print(f"  价格: ¥{param_result['price']:,.2f}")
    print(f"  标准误差: ¥{param_result['price_std']:,.2f}")
    print(f"  预期HDD: {param_result['hdd_mean']:,.2f}")
    print(f"  行权概率: {param_result['probability_exercise']*100:.2f}%")

    print("\n4.2 Bootstrap定价:")
    boot_result = mc_engine.price_hdd_option(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03, use_bootstrap=True
    )
    print(f"  价格: ¥{boot_result['price']:,.2f}")
    print(f"  标准误差: ¥{boot_result['price_std']:,.2f}")
    print(f"  预期HDD: {boot_result['hdd_mean']:,.2f}")
    print(f"  行权概率: {boot_result['probability_exercise']*100:.2f}%")

    print(f"\n定价差异: ¥{abs(param_result['price'] - boot_result['price']):,.2f} "
          f"({abs(param_result['price'] - boot_result['price'])/param_result['price']*100:.2f}%)")

    print("\n" + "=" * 70)
    print("5. 自适应中心差分希腊值计算")
    print("=" * 70)

    greeks_config = GreeksConfig(
        delta_shift=1.0,
        gamma_shift=2.0,
        use_adaptive_step=True,
        min_step=0.1,
        max_step=10.0,
        step_tolerance=0.01
    )

    print("\n5.1 参数化希腊值:")
    greeks_param = mc_engine.calculate_greeks(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03,
        use_bootstrap=False, config=greeks_config
    )
    print(f"  Delta: {greeks_param['delta']:.4f}")
    print(f"  Gamma: {greeks_param['gamma']:.6f}")
    print(f"  Vega: {greeks_param['vega']:,.2f}")
    print(f"  Theta: {greeks_param['theta']:,.2f}")
    print(f"  Rho: {greeks_param['rho']:,.2f}")
    print(f"  最优Delta步长: {greeks_param['delta_shift']:.4f}°C")
    print(f"  最优Gamma步长: {greeks_param['gamma_shift']:.4f}°C")

    print("\n5.2 Bootstrap希腊值:")
    greeks_boot = mc_engine.calculate_greeks(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03,
        use_bootstrap=True, config=greeks_config
    )
    print(f"  Delta: {greeks_boot['delta']:.4f}")
    print(f"  Gamma: {greeks_boot['gamma']:.6f}")
    print(f"  Vega: {greeks_boot['vega']:,.2f}")
    print(f"  Theta: {greeks_boot['theta']:,.2f}")
    print(f"  Rho: {greeks_boot['rho']:,.2f}")

    print("\n" + "=" * 70)
    print("6. 生成Bootstrap定价曲线")
    print("=" * 70)

    pricing_curve_boot = mc_engine.generate_pricing_curve(
        contract, temp_range=(0, 15),
        mu=mu, sigma=sigma, ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        n_points=15, risk_free_rate=0.03,
        use_bootstrap=True
    )

    print("\nBootstrap定价曲线数据:")
    print(pricing_curve_boot[['temperature', 'price', 'hdd_mean', 'exercise_prob']].to_string(index=False))

    visualizer.plot_pricing_curve(pricing_curve_boot, "HDD看涨期权 (Bootstrap)")
    visualizer.plot_greeks(greeks_boot, pricing_curve_boot)

    print("\n" + "=" * 70)
    print("7. 压力测试 - 综合分析")
    print("=" * 70)

    stress_tester = StressTesting(mc_engine, bootstrap_sim)

    stress_results = stress_tester.run_comprehensive_stress_test(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03,
        use_bootstrap=True,
        historical_data=historical_data
    )

    print("\n7.1 合成极端情景测试:")
    if len(stress_results['extreme_scenarios']) > 0:
        print(stress_results['extreme_scenarios'][
            ['scenario', 'temp_shift', 'vol_multiplier', 'price', 'price_change_pct']
        ].to_string(index=False))

    print("\n7.2 历史极值回放:")
    if len(stress_results['historical_replay']) > 0:
        print(stress_results['historical_replay'][
            ['scenario', 'historical_HDD', 'historical_avg_temp', 'price', 'price_change_pct']
        ].to_string(index=False))

    print("\n7.3 Bootstrap合成极端情景:")
    if len(stress_results['synthetic_bootstrap']) > 0:
        print(stress_results['synthetic_bootstrap'][
            ['scenario', 'hdd_value', 'price', 'is_extreme']
        ].to_string(index=False))

    print("\n7.4 VaR分析 (Bootstrap):")
    for key, value in stress_results['value_at_risk'].items():
        if key.startswith('VaR'):
            print(f"  {key}: ¥{value:,.2f}")

    print("\n7.5 CVaR分析:")
    if 'cvars' in stress_results['value_at_risk']:
        for key, value in stress_results['value_at_risk']['cvars'].items():
            print(f"  {key}: ¥{value:,.2f}")

    visualizer.plot_stress_test_results(stress_results)

    print("\n" + "=" * 70)
    print("8. 历史极端天气事件识别")
    print("=" * 70)

    extreme_events = bootstrap_sim.get_extreme_weather_events(
        metric='HDD',
        threshold=historical_data['HDD'].quantile(0.95),
        n_days=7
    )

    print(f"\n发现 {len(extreme_events)} 个极端HDD事件:")
    for i, event in enumerate(extreme_events[:10]):
        print(f"  {i+1}. {event['start_date'].strftime('%Y-%m-%d')} ~ {event['end_date'].strftime('%Y-%m-%d')} "
              f"({event['duration_days']}天) | "
              f"平均温度: {event['avg_temperature']:.2f}°C | "
              f"累计HDD: {event['total_HDD']:.2f}")

    print("\n" + "=" * 70)
    print("9. 历史类比法预测")
    print("=" * 70)

    analogs = bootstrap_sim.simulate_with_historical_analog(
        target_start_date='2024-11-01',
        n_days=151,
        n_analogs=5
    )

    print("\n历史类比年份:")
    for analog in analogs:
        print(f"  {analog['year']}年: 起始温度={analog['start_temp']:.2f}°C, "
              f"累计HDD={analog['total_HDD']:,.2f}, "
              f"平均温度={analog['avg_temp']:.2f}°C")

    print("\n" + "=" * 70)
    print("10. 对比不同Bootstrap方法")
    print("=" * 70)

    methods = ['seasonal_block', 'moving_block', 'circular_block', 'iid']
    print("\n不同Bootstrap方法的HDD分布比较:")
    for method in methods:
        dist = bootstrap_sim.estimate_hdd_distribution(
            start_day=305, n_days=151, n_samples=3000, method=method
        )
        print(f"  {method:20s}: 均值={dist['hdd']['mean']:,.2f}, "
              f"标准差={dist['hdd']['std']:,.2f}, "
              f"偏度={dist['hdd']['skewness']:.4f}")

    print("\n" + "=" * 70)
    print("11. 生成压力测试报告")
    print("=" * 70)

    report = stress_tester.generate_stress_report(stress_results)
    print(report)

    print("\n" + "=" * 70)
    print("完成！所有结果已保存到 output/ 目录")
    print("=" * 70)

    print("\n生成的文件:")
    for file in sorted(os.listdir(output_dir)):
        file_path = os.path.join(output_dir, file)
        size = os.path.getsize(file_path)
        print(f"  {file} ({size:,} bytes)")

    return {
        'parametric_price': param_result['price'],
        'bootstrap_price': boot_result['price'],
        'parametric_greeks': greeks_param,
        'bootstrap_greeks': greeks_boot,
        'stress_results': stress_results
    }


if __name__ == '__main__':
    results = main()
