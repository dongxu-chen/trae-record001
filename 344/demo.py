"""
天气衍生品定价模型 - 简化演示脚本
快速演示核心功能
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime

from weather_data import WeatherDataGenerator
from monte_carlo_engine import MonteCarloPricingEngine, WeatherOptionContract
from stress_testing import StressTesting
from visualizer import Visualizer


def main():
    print("=" * 60)
    print("天气衍生品定价模型 - 快速演示")
    print("=" * 60)

    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    visualizer = Visualizer(output_dir)

    print("\n1. 生成气象数据...")
    weather_gen = WeatherDataGenerator(
        location="Beijing",
        base_temperature=5.0,
        temp_volatility=8.0,
        base_rainfall=2.0,
        rainfall_volatility=5.0,
        seed=42
    )

    weather_data = weather_gen.generate_combined_data('2024-11-01', '2025-03-31')
    print(f"   生成 {len(weather_data)} 天数据")
    print(f"   平均温度: {weather_data['temperature'].mean():.2f}°C")
    print(f"   累计HDD: {weather_data['HDD'].sum():.2f}")

    visualizer.plot_temperature_data(weather_data, "冬季温度数据 (2024/11 - 2025/03)")
    visualizer.plot_rainfall_data(weather_data, "冬季降雨量数据")

    print("\n2. 定义HDD看涨期权合约...")
    contract = WeatherOptionContract(
        contract_type='HDD_call',
        strike=1200,
        tick_size=5000,
        notional=1000000,
        start_date='2024-11-01',
        end_date='2025-03-31',
        payment_date='2025-04-15'
    )
    print(f"   合约: HDD看涨期权")
    print(f"   行权价: {contract.strike} HDD")
    print(f"   乘数: ¥{contract.tick_size:,}/HDD点")
    print(f"   期限: {contract.days_to_maturity}天")

    print("\n3. 蒙特卡洛模拟定价 (5000次模拟)...")
    mc_engine = MonteCarloPricingEngine(
        n_simulations=5000,
        n_time_steps=150,
        seed=12345
    )

    initial_temp = 5.0
    mu = 0.02
    sigma = 8.0
    ar1_coeff = 0.85
    seasonal_amplitude = 15.0

    mc_result = mc_engine.price_hdd_option(
        contract=contract,
        initial_temp=initial_temp,
        mu=mu,
        sigma=sigma,
        ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        risk_free_rate=0.03
    )

    print(f"\n   定价结果:")
    print(f"   期权价格: ¥{mc_result['price']:,.2f}")
    print(f"   标准误差: ¥{mc_result['price_std']:,.2f}")
    print(f"   预期HDD: {mc_result['hdd_mean']:,.2f}")
    print(f"   行权概率: {mc_result['probability_exercise']*100:.2f}%")

    print("\n4. 计算希腊值...")
    greeks = mc_engine.calculate_greeks(
        contract=contract,
        initial_temp=initial_temp,
        mu=mu,
        sigma=sigma,
        ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        risk_free_rate=0.03
    )

    print(f"   Delta: {greeks['delta']:.4f}")
    print(f"   Gamma: {greeks['gamma']:.6f}")

    print("\n5. 生成定价曲线...")
    pricing_curve = mc_engine.generate_pricing_curve(
        contract=contract,
        temp_range=(0, 15),
        mu=mu,
        sigma=sigma,
        ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        n_points=15,
        risk_free_rate=0.03
    )

    visualizer.plot_pricing_curve(pricing_curve, "HDD看涨期权定价曲线")
    visualizer.plot_greeks(greeks, pricing_curve)

    print("\n6. 压力测试...")
    stress_tester = StressTesting(mc_engine)

    print("   - 温度压力测试...")
    temp_stress = stress_tester.run_temp_stress_test(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, base_temp_range=(-10, 10),
        n_scenarios=10, risk_free_rate=0.03
    )

    print("   - 波动率压力测试...")
    vol_stress = stress_tester.run_volatility_stress_test(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03
    )

    print("   - 极端情景测试...")
    extreme_test = stress_tester.run_extreme_scenario_test(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03
    )

    print("   - VaR分析...")
    var_results = stress_tester.calculate_var(
        contract, initial_temp, mu, sigma, ar1_coeff,
        seasonal_amplitude, risk_free_rate=0.03
    )

    stress_results = {
        'temperature_stress': temp_stress,
        'volatility_stress': vol_stress,
        'extreme_scenarios': extreme_test,
        'value_at_risk': var_results
    }

    visualizer.plot_stress_test_results(stress_results)

    print("\n" + "=" * 60)
    print("演示完成！结果保存在 output/ 目录")
    print("=" * 60)

    print("\n生成的文件:")
    for file in sorted(os.listdir(output_dir)):
        file_path = os.path.join(output_dir, file)
        size = os.path.getsize(file_path)
        print(f"  {file} ({size:,} bytes)")

    print("\n压力测试极端情景结果:")
    print(extreme_test[['scenario', 'temp_shift', 'vol_multiplier', 'price', 'price_change_pct']].to_string(index=False))

    print("\nVaR分析结果:")
    for key, value in var_results.items():
        if key.startswith('VaR'):
            print(f"  {key}: ¥{value:,.2f}")


if __name__ == '__main__':
    main()
