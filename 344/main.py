"""
天气衍生品定价模型 - 主程序
整合气象数据生成、蒙特卡洛模拟、QuantLib定价、希腊值计算和压力测试
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from weather_data import WeatherDataGenerator
from monte_carlo_engine import MonteCarloPricingEngine, WeatherOptionContract
from stress_testing import StressTesting
from visualizer import Visualizer

try:
    from quantlib_pricer import QuantLibPricer
    HAS_QUANTLIB = True
except ImportError:
    HAS_QUANTLIB = False
    print("Warning: QuantLib not available, will use Monte Carlo as primary pricing method")


def create_output_directory(base_dir: str = 'output'):
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    return base_dir


def main():
    print("=" * 70)
    print("天气衍生品定价模型 - Weather Derivatives Pricing Model")
    print("=" * 70)

    output_dir = create_output_directory()
    visualizer = Visualizer(output_dir)

    print("\n" + "=" * 70)
    print("第一步: 生成气象数据")
    print("=" * 70)

    weather_gen = WeatherDataGenerator(
        location="Beijing",
        base_temperature=15.0,
        temp_volatility=8.0,
        base_rainfall=2.0,
        rainfall_volatility=5.0,
        seed=42
    )

    historical_years = weather_gen.generate_historical_years(2015, 2024)
    print(f"历史气象数据生成完成: {len(historical_years)} 天数据")
    print(f"年份范围: 2015-2024")

    recent_data = weather_gen.generate_combined_data('2024-01-01', '2024-12-31')
    print(f"2024年数据生成完成: {len(recent_data)} 天")

    temp_model = WeatherDataGenerator.fit_temperature_model(recent_data['temperature'])
    seasonal_model = WeatherDataGenerator.analyze_seasonality(recent_data['temperature'])

    print("\n温度模型参数:")
    for key, value in temp_model.items():
        print(f"  {key}: {value:.4f}")

    print("\n季节性分析:")
    for key, value in seasonal_model.items():
        print(f"  {key}: {value:.4f}")

    visualizer.plot_temperature_data(recent_data, "2024年北京温度数据")
    visualizer.plot_rainfall_data(recent_data, "2024年北京降雨量数据")

    print("\n" + "=" * 70)
    print("第二步: 定义天气衍生品合约")
    print("=" * 70)

    contract = WeatherOptionContract(
        contract_type='HDD_call',
        strike=1200,
        tick_size=5000,
        notional=1000000,
        start_date='2024-11-01',
        end_date='2025-03-31',
        payment_date='2025-04-15'
    )

    print(f"\n合约类型: {contract.contract_type}")
    print(f"行权价 (HDD): {contract.strike}")
    print(f"合约乘数: ¥{contract.tick_size:,}/HDD点")
    print(f"合约期限: {contract.days_to_maturity} 天")
    print(f"起始日期: {contract.start_date}")
    print(f"到期日期: {contract.end_date}")

    print("\n" + "=" * 70)
    print("第三步: 蒙特卡洛模拟定价")
    print("=" * 70)

    mc_engine = MonteCarloPricingEngine(
        n_simulations=10000,
        n_time_steps=150,
        seed=12345
    )

    initial_temp = 5.0
    mu = 0.02
    sigma = 8.0
    ar1_coeff = 0.85
    seasonal_amplitude = 15.0

    print(f"\n初始温度: {initial_temp}°C")
    print(f"温度漂移 (mu): {mu:.4f}")
    print(f"温度波动率 (sigma): {sigma:.4f}")
    print(f"AR1系数: {ar1_coeff:.4f}")
    print(f"季节性振幅: {seasonal_amplitude:.4f}")

    mc_result = mc_engine.price_hdd_option(
        contract=contract,
        initial_temp=initial_temp,
        mu=mu,
        sigma=sigma,
        ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        risk_free_rate=0.03
    )

    print(f"\n蒙特卡洛定价结果:")
    print(f"  期权价格: ¥{mc_result['price']:,.2f}")
    print(f"  标准误差: ¥{mc_result['price_std']:,.2f}")
    print(f"  95%置信区间: [¥{mc_result['price'] - mc_result['price_ci']:,.2f}, "
          f"¥{mc_result['price'] + mc_result['price_ci']:,.2f}]")
    print(f"  预期HDD累计值: {mc_result['hdd_mean']:,.2f}")
    print(f"  HDD标准差: {mc_result['hdd_std']:,.2f}")
    print(f"  行权概率: {mc_result['probability_exercise']*100:.2f}%")
    print(f"  预期收益: ¥{mc_result['expected_payoff']:,.2f}")

    visualizer.plot_mc_convergence(mc_result['all_payoffs'][:5000], mc_result['price'])

    print("\n" + "=" * 70)
    print("第四步: 计算希腊值 (Delta, Gamma)")
    print("=" * 70)

    greeks = mc_engine.calculate_greeks(
        contract=contract,
        initial_temp=initial_temp,
        mu=mu,
        sigma=sigma,
        ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        risk_free_rate=0.03
    )

    print(f"\n希腊值计算结果:")
    print(f"  Delta: {greeks['delta']:.4f}")
    print(f"    (温度每变化1°C，期权价格变化 ¥{greeks['delta']*5000:,.2f})")
    print(f"  Gamma: {greeks['gamma']:.6f}")
    print(f"    (温度每变化1°C，Delta变化 {greeks['gamma']:.6f})")
    print(f"  Rho: {greeks['rho']:,.2f}")
    print(f"    (利率每变化1%，期权价格变化 ¥{greeks['rho']*100:,.2f})")

    print("\n" + "=" * 70)
    print("第五步: 生成定价曲线")
    print("=" * 70)

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

    print("\n定价曲线数据 (部分):")
    print(pricing_curve.head(10).to_string(index=False))

    visualizer.plot_pricing_curve(pricing_curve, "HDD看涨期权")
    visualizer.plot_greeks(greeks, pricing_curve)

    print("\n" + "=" * 70)
    print("第六步: QuantLib定价对比")
    print("=" * 70)

    if HAS_QUANTLIB:
        try:
            ql_pricer = QuantLibPricer()

            ql_result = ql_pricer.price_weather_derivative(
                contract_type=contract.contract_type,
                strike=contract.strike,
                index_value=mc_result['hdd_mean'],
                volatility=sigma / mc_result['hdd_mean'] * 100,
                risk_free_rate=0.03,
                tick_size=contract.tick_size,
                start_date=contract.start_date,
                end_date=contract.end_date
            )

            if 'error' not in ql_result:
                print(f"\nQuantLib定价结果:")
                print(f"  期权价格 (每单位): ¥{ql_result['price']:,.2f}")
                print(f"  合约价值: ¥{ql_result['contract_value']:,.2f}")
                print(f"  Delta: {ql_result['delta']:.4f}")
                print(f"  Gamma: {ql_result['gamma']:.6f}")
                print(f"  Vega: {ql_result['vega']:,.2f}")
                print(f"  Theta: {ql_result['theta']:,.2f}")
                print(f"  Rho: {ql_result['rho']:,.2f}")
                print(f"  行权概率: {ql_result['itm_probability']*100:.2f}%")

                print(f"\n定价对比:")
                print(f"  蒙特卡洛价格: ¥{mc_result['price']:,.2f}")
                print(f"  QuantLib价格: ¥{ql_result['contract_value']:,.2f}")
                print(f"  差异: ¥{abs(mc_result['price'] - ql_result['contract_value']):,.2f} "
                      f"({abs(mc_result['price'] - ql_result['contract_value'])/mc_result['price']*100:.2f}%)")
        except Exception as e:
            print(f"QuantLib定价出错: {e}")
            print("将使用蒙特卡洛结果作为主要定价参考")
    else:
        print("QuantLib未安装，跳过Black-Scholes定价对比")

    print("\n" + "=" * 70)
    print("第七步: 压力测试")
    print("=" * 70)

    stress_tester = StressTesting(mc_engine)

    stress_results = stress_tester.run_comprehensive_stress_test(
        contract=contract,
        initial_temp=initial_temp,
        mu=mu,
        sigma=sigma,
        ar1_coeff=ar1_coeff,
        seasonal_amplitude=seasonal_amplitude,
        risk_free_rate=0.03
    )

    print("\n极端情景测试结果:")
    print(stress_results['extreme_scenarios'].to_string(index=False))

    print("\n风险价值 (VaR) 分析:")
    for key, value in stress_results['value_at_risk'].items():
        if key.startswith('VaR'):
            print(f"  {key}: ¥{value:,.2f}")

    visualizer.plot_stress_test_results(stress_results)

    print("\n" + "=" * 70)
    print("第八步: 降雨量期权定价示例")
    print("=" * 70)

    rainfall_contract = WeatherOptionContract(
        contract_type='rainfall_call',
        strike=300,
        tick_size=1000,
        notional=500000,
        start_date='2024-06-01',
        end_date='2024-08-31',
        payment_date='2024-09-15'
    )

    print(f"\n降雨量期权合约:")
    print(f"  类型: {rainfall_contract.contract_type}")
    print(f"  行权价: {rainfall_contract.strike} mm")
    print(f"  合约乘数: ¥{rainfall_contract.tick_size:,}/mm")
    print(f"  期限: {rainfall_contract.days_to_maturity} 天")

    rain_result = mc_engine.price_rainfall_option(
        contract=rainfall_contract,
        mu_rain=2.0,
        sigma_rain=5.0,
        risk_free_rate=0.03
    )

    print(f"\n降雨量期权定价结果:")
    print(f"  期权价格: ¥{rain_result['price']:,.2f}")
    print(f"  标准误差: ¥{rain_result['price_std']:,.2f}")
    print(f"  预期累计降雨量: {rain_result['rainfall_mean']:,.2f} mm")
    print(f"  降雨量标准差: {rain_result['rainfall_std']:,.2f} mm")
    print(f"  行权概率: {rain_result['probability_exercise']*100:.2f}%")

    print("\n" + "=" * 70)
    print("第九步: 历史数据分析")
    print("=" * 70)

    yearly_hdd = historical_years.groupby('year').agg({
        'HDD': 'sum',
        'CDD': 'sum',
        'temperature': 'mean',
        'rainfall': 'sum'
    }).reset_index()

    print("\n历史年度统计:")
    print(yearly_hdd.to_string(index=False))

    hdd_stats = yearly_hdd['HDD'].describe()
    print(f"\nHDD统计特征:")
    print(f"  均值: {hdd_stats['mean']:,.2f}")
    print(f"  标准差: {hdd_stats['std']:,.2f}")
    print(f"  最小值: {hdd_stats['min']:,.2f}")
    print(f"  最大值: {hdd_stats['max']:,.2f}")

    print("\n" + "=" * 70)
    print("模型运行完成！所有结果已保存到output目录")
    print("=" * 70)

    print("\n生成的文件:")
    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        size = os.path.getsize(file_path)
        print(f"  {file} ({size:,} bytes)")

    return {
        'mc_price': mc_result['price'],
        'mc_delta': greeks['delta'],
        'mc_gamma': greeks['gamma'],
        'stress_results': stress_results,
        'pricing_curve': pricing_curve
    }


if __name__ == '__main__':
    results = main()
