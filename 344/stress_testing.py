"""
压力测试模块 - 天气衍生品风险分析
包含历史极值事件回放、合成极端场景和传统压力测试
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from monte_carlo_engine import MonteCarloPricingEngine, WeatherOptionContract

try:
    from bootstrap_engine import BootstrapWeatherSimulator
    HAS_BOOTSTRAP = True
except ImportError:
    HAS_BOOTSTRAP = False


@dataclass
class StressScenario:
    name: str
    description: str
    temp_shift: float = 0.0
    volatility_mult: float = 1.0
    rainfall_mult: float = 1.0
    trend_shift: float = 0.0
    risk_free_rate: float = 0.03
    scenario_type: str = 'synthetic'


@dataclass
class HistoricalExtremeEvent:
    name: str
    year: int
    start_date: str
    end_date: str
    avg_temp: float
    min_temp: float
    total_HDD: float
    total_rainfall: float
    severity: str


class StressTesting:
    """天气衍生品压力测试 - 包含历史回放和合成极端场景"""

    def __init__(self,
                 pricing_engine: MonteCarloPricingEngine,
                 bootstrap_simulator: Optional['BootstrapWeatherSimulator'] = None):
        self.pricing_engine = pricing_engine
        self.bootstrap_simulator = bootstrap_simulator

    def run_temp_stress_test(self,
                             contract: WeatherOptionContract,
                             initial_temp: float,
                             mu: float,
                             sigma: float,
                             ar1_coeff: float,
                             seasonal_amplitude: float,
                             base_temp_range: Tuple[float, float] = (-20, 20),
                             n_scenarios: int = 10,
                             risk_free_rate: float = 0.03,
                             use_bootstrap: bool = False) -> pd.DataFrame:
        temp_shifts = np.linspace(base_temp_range[0], base_temp_range[1], n_scenarios)
        results = []

        for shift in temp_shifts:
            adjusted_temp = initial_temp + shift
            price_result = self.pricing_engine.price_hdd_option(
                contract, adjusted_temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap
            )
            results.append({
                'temp_shift': shift,
                'adjusted_temp': adjusted_temp,
                'price': price_result['price'],
                'price_std': price_result['price_std'],
                'price_change_pct': 0.0,
                'hdd_mean': price_result['hdd_mean'],
                'exercise_prob': price_result['probability_exercise']
            })

        df = pd.DataFrame(results)
        base_price = df.loc[df['temp_shift'] == 0, 'price'].values[0] if any(df['temp_shift'] == 0) else df['price'].iloc[0]
        df['price_change_pct'] = (df['price'] - base_price) / base_price * 100 if base_price != 0 else 0
        df['price_change_abs'] = df['price'] - base_price

        return df

    def run_volatility_stress_test(self,
                                   contract: WeatherOptionContract,
                                   initial_temp: float,
                                   mu: float,
                                   sigma: float,
                                   ar1_coeff: float,
                                   seasonal_amplitude: float,
                                   vol_multipliers: List[float] = None,
                                   risk_free_rate: float = 0.03,
                                   use_bootstrap: bool = False) -> pd.DataFrame:
        if vol_multipliers is None:
            vol_multipliers = [0.3, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 5.0]

        results = []
        for vol_mult in vol_multipliers:
            adjusted_sigma = sigma * vol_mult
            price_result = self.pricing_engine.price_hdd_option(
                contract, initial_temp, mu, adjusted_sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap
            )
            results.append({
                'vol_multiplier': vol_mult,
                'adjusted_vol': adjusted_sigma,
                'price': price_result['price'],
                'price_ci': price_result['price_ci'],
                'hdd_mean': price_result['hdd_mean'],
                'hdd_std': price_result['hdd_std']
            })

        df = pd.DataFrame(results)
        base_price = df.loc[df['vol_multiplier'] == 1.0, 'price'].values[0]
        df['price_change_pct'] = (df['price'] - base_price) / base_price * 100 if base_price != 0 else 0

        return df

    def run_extreme_scenario_test(self,
                                  contract: WeatherOptionContract,
                                  initial_temp: float,
                                  mu: float,
                                  sigma: float,
                                  ar1_coeff: float,
                                  seasonal_amplitude: float,
                                  risk_free_rate: float = 0.03,
                                  use_bootstrap: bool = False) -> pd.DataFrame:
        scenarios = [
            StressScenario("极寒天气", "温度下降10度，波动率增加50%",
                          temp_shift=-10, volatility_mult=1.5),
            StressScenario("极热天气", "温度上升10度，波动率增加50%",
                          temp_shift=10, volatility_mult=1.5),
            StressScenario("高波动期", "波动率翻倍",
                          temp_shift=0, volatility_mult=2.0),
            StressScenario("严寒+高波动", "温度下降15度，波动率翻倍",
                          temp_shift=-15, volatility_mult=2.0),
            StressScenario("酷暑+高波动", "温度上升15度，波动率翻倍",
                          temp_shift=15, volatility_mult=2.0),
            StressScenario("温和天气", "温度接近基准，波动率降低",
                          temp_shift=0, volatility_mult=0.5),
            StressScenario("暖冬情景", "温度上升5度，波动率降低",
                          temp_shift=5, volatility_mult=0.75),
            StressScenario("冷冬情景", "温度下降5度，波动率增加25%",
                          temp_shift=-5, volatility_mult=1.25),
            StressScenario("超级严寒", "温度下降20度，波动率3倍",
                          temp_shift=-20, volatility_mult=3.0, scenario_type='extreme'),
            StressScenario("气候突变", "温度骤降15度，波动率5倍",
                          temp_shift=-15, volatility_mult=5.0, scenario_type='extreme'),
        ]

        results = []
        base_result = self.pricing_engine.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap
        )
        base_price = base_result['price']

        for scenario in scenarios:
            adjusted_temp = initial_temp + scenario.temp_shift
            adjusted_sigma = sigma * scenario.volatility_mult

            price_result = self.pricing_engine.price_hdd_option(
                contract, adjusted_temp, mu, adjusted_sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap
            )

            results.append({
                'scenario': scenario.name,
                'description': scenario.description,
                'temp_shift': scenario.temp_shift,
                'vol_multiplier': scenario.volatility_mult,
                'scenario_type': scenario.scenario_type,
                'price': price_result['price'],
                'price_change': price_result['price'] - base_price,
                'price_change_pct': (price_result['price'] - base_price) / base_price * 100 if base_price != 0 else 0,
                'hdd_mean': price_result['hdd_mean'],
                'hdd_std': price_result['hdd_std'],
                'exercise_prob': price_result['probability_exercise']
            })

        return pd.DataFrame(results)

    def run_historical_extreme_replay(self,
                                      contract: WeatherOptionContract,
                                      historical_data: pd.DataFrame,
                                      initial_temp: float,
                                      mu: float,
                                      sigma: float,
                                      ar1_coeff: float,
                                      seasonal_amplitude: float,
                                      risk_free_rate: float = 0.03) -> pd.DataFrame:
        if 'year' not in historical_data.columns:
            historical_data['year'] = pd.to_datetime(historical_data['date']).dt.year

        if 'HDD' not in historical_data.columns:
            historical_data['HDD'] = np.maximum(18.0 - historical_data['temperature'], 0)

        yearly_hdd = historical_data.groupby('year').agg({
            'HDD': 'sum',
            'temperature': 'mean',
            'rainfall': 'sum'
        }).reset_index()

        extreme_years = yearly_hdd.nlargest(5, 'HDD')['year'].tolist() + \
                       yearly_hdd.nsmallest(5, 'HDD')['year'].tolist()

        results = []
        base_result = self.pricing_engine.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate
        )
        base_price = base_result['price']

        contract_start = datetime.strptime(contract.start_date, '%Y-%m-%d')
        contract_end = datetime.strptime(contract.end_date, '%Y-%m-%d')

        for year in extreme_years:
            year_data = historical_data[historical_data['year'] == year].copy()
            year_data['date'] = pd.to_datetime(year_data['date'])
            year_data['day_of_year'] = year_data['date'].dt.dayofyear

            start_day = contract_start.timetuple().tm_yday
            end_day = contract_end.timetuple().tm_yday

            if end_day < start_day:
                period_data = year_data[
                    (year_data['day_of_year'] >= start_day) |
                    (year_data['day_of_year'] <= end_day)
                ]
            else:
                period_data = year_data[
                    (year_data['day_of_year'] >= start_day) &
                    (year_data['day_of_year'] <= end_day)
                ]

            if len(period_data) > 0:
                year_hdd = period_data['HDD'].sum()
                year_avg_temp = period_data['temperature'].mean()
                year_min_temp = period_data['temperature'].min()
                year_rainfall = period_data['rainfall'].sum()

                temp_diff = year_avg_temp - initial_temp

                price_result = self.pricing_engine.price_hdd_option(
                    contract, year_avg_temp, mu, sigma, ar1_coeff,
                    seasonal_amplitude, risk_free_rate
                )

                severity = 'extreme_cold' if year_hdd > yearly_hdd['HDD'].quantile(0.9) else \
                          'extreme_warm' if year_hdd < yearly_hdd['HDD'].quantile(0.1) else \
                          'normal'

                results.append({
                    'scenario': f"历史回放-{year}年",
                    'description': f"{year}年同期天气条件",
                    'year': year,
                    'historical_HDD': year_hdd,
                    'historical_avg_temp': year_avg_temp,
                    'historical_min_temp': year_min_temp,
                    'historical_rainfall': year_rainfall,
                    'temp_shift': temp_diff,
                    'scenario_type': 'historical_replay',
                    'severity': severity,
                    'price': price_result['price'],
                    'price_change': price_result['price'] - base_price,
                    'price_change_pct': (price_result['price'] - base_price) / base_price * 100 if base_price != 0 else 0,
                    'hdd_mean': price_result['hdd_mean'],
                    'exercise_prob': price_result['probability_exercise']
                })

        return pd.DataFrame(results)

    def run_synthetic_extreme_scenarios(self,
                                        contract: WeatherOptionContract,
                                        initial_temp: float,
                                        mu: float,
                                        sigma: float,
                                        ar1_coeff: float,
                                        seasonal_amplitude: float,
                                        risk_free_rate: float = 0.03,
                                        use_bootstrap: bool = False) -> pd.DataFrame:
        if self.bootstrap_simulator is None:
            return pd.DataFrame()

        hdd_dist = self.bootstrap_simulator.estimate_hdd_distribution(
            start_day=contract.start_day_of_year,
            n_days=contract.days_to_maturity,
            n_samples=5000
        )

        hdd_values = hdd_dist['hdd']['all_values']

        extreme_percentiles = [1, 5, 10, 90, 95, 99]
        results = []

        base_result = self.pricing_engine.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap
        )
        base_price = base_result['price']

        for pct in extreme_percentiles:
            hdd_value = np.percentile(hdd_values, pct)

            if 'call' in contract.contract_type:
                payoff = max(hdd_value - contract.strike, 0) * contract.tick_size
            else:
                payoff = max(contract.strike - hdd_value, 0) * contract.tick_size

            dt = contract.days_to_maturity / 365
            discount_factor = np.exp(-risk_free_rate * dt)
            discounted_payoff = payoff * discount_factor

            results.append({
                'scenario': f"合成极端-{pct}%分位",
                'description': f"基于Bootstrap分布的{pct}%分位数HDD情景",
                'percentile': pct,
                'hdd_value': hdd_value,
                'scenario_type': 'synthetic_bootstrap',
                'price': discounted_payoff,
                'price_change': discounted_payoff - base_price,
                'price_change_pct': (discounted_payoff - base_price) / base_price * 100 if base_price != 0 else 0,
                'is_extreme': pct <= 10 or pct >= 90
            })

        return pd.DataFrame(results)

    def run_combined_stress_test(self,
                                 contract: WeatherOptionContract,
                                 initial_temp: float,
                                 mu: float,
                                 sigma: float,
                                 ar1_coeff: float,
                                 seasonal_amplitude: float,
                                 risk_free_rate: float = 0.03,
                                 use_bootstrap: bool = False) -> pd.DataFrame:
        synthetic = self.run_extreme_scenario_test(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap
        )

        synthetic_bootstrap = pd.DataFrame()
        if use_bootstrap and self.bootstrap_simulator is not None:
            synthetic_bootstrap = self.run_synthetic_extreme_scenarios(
                contract, initial_temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap
            )

        all_scenarios = pd.concat([synthetic, synthetic_bootstrap], ignore_index=True)

        return all_scenarios

    def run_rainfall_stress_test(self,
                                 contract: WeatherOptionContract,
                                 mu_rain: float,
                                 sigma_rain: float,
                                 rainfall_multipliers: List[float] = None,
                                 risk_free_rate: float = 0.03,
                                 use_bootstrap: bool = False) -> pd.DataFrame:
        if rainfall_multipliers is None:
            rainfall_multipliers = [0.1, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]

        results = []
        for rain_mult in rainfall_multipliers:
            adjusted_sigma = sigma_rain * rain_mult
            price_result = self.pricing_engine.price_rainfall_option(
                contract, mu_rain, adjusted_sigma, risk_free_rate, use_bootstrap
            )
            results.append({
                'rainfall_multiplier': rain_mult,
                'adjusted_sigma': adjusted_sigma,
                'price': price_result['price'],
                'rainfall_mean': price_result['rainfall_mean'],
                'rainfall_std': price_result['rainfall_std']
            })

        df = pd.DataFrame(results)
        base_price = df.loc[df['rainfall_multiplier'] == 1.0, 'price'].values[0]
        df['price_change_pct'] = (df['price'] - base_price) / base_price * 100 if base_price != 0 else 0

        return df

    def calculate_var(self,
                      contract: WeatherOptionContract,
                      initial_temp: float,
                      mu: float,
                      sigma: float,
                      ar1_coeff: float,
                      seasonal_amplitude: float,
                      confidence_levels: List[float] = None,
                      risk_free_rate: float = 0.03,
                      use_bootstrap: bool = False) -> Dict:
        if confidence_levels is None:
            confidence_levels = [0.90, 0.95, 0.975, 0.99, 0.995, 0.999]

        price_result = self.pricing_engine.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap
        )

        all_payoffs = price_result['all_payoffs']
        base_price = price_result['price']

        var_results = {}
        for cl in confidence_levels:
            percentile = np.percentile(all_payoffs, (1 - cl) * 100)
            var = base_price - percentile
            var_results[f'VaR_{int(cl*100)}%'] = var

        var_results['expected_payoff'] = base_price
        var_results['worst_case'] = np.min(all_payoffs)
        var_results['best_case'] = np.max(all_payoffs)
        var_results['cvars'] = {}

        for cl in [0.95, 0.99]:
            threshold = np.percentile(all_payoffs, (1 - cl) * 100)
            tail_losses = all_payoffs[all_payoffs <= threshold]
            if len(tail_losses) > 0:
                var_results['cvars'][f'CVaR_{int(cl*100)}%'] = np.mean(tail_losses)
            else:
                var_results['cvars'][f'CVaR_{int(cl*100)}%'] = threshold

        return var_results

    def run_comprehensive_stress_test(self,
                                      contract: WeatherOptionContract,
                                      initial_temp: float,
                                      mu: float,
                                      sigma: float,
                                      ar1_coeff: float,
                                      seasonal_amplitude: float,
                                      risk_free_rate: float = 0.03,
                                      use_bootstrap: bool = False,
                                      historical_data: pd.DataFrame = None) -> Dict:
        print("=" * 60)
        print("开始综合压力测试")
        print("=" * 60)

        temp_test = self.run_temp_stress_test(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate=risk_free_rate,
            use_bootstrap=use_bootstrap
        )

        vol_test = self.run_volatility_stress_test(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate=risk_free_rate,
            use_bootstrap=use_bootstrap
        )

        extreme_test = self.run_extreme_scenario_test(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate=risk_free_rate,
            use_bootstrap=use_bootstrap
        )

        historical_replay = pd.DataFrame()
        if historical_data is not None:
            historical_replay = self.run_historical_extreme_replay(
                contract, historical_data, initial_temp, mu, sigma,
                ar1_coeff, seasonal_amplitude, risk_free_rate
            )

        synthetic_bootstrap = pd.DataFrame()
        if use_bootstrap and self.bootstrap_simulator is not None:
            synthetic_bootstrap = self.run_synthetic_extreme_scenarios(
                contract, initial_temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap
            )

        var_results = self.calculate_var(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate=risk_free_rate,
            use_bootstrap=use_bootstrap
        )

        return {
            'temperature_stress': temp_test,
            'volatility_stress': vol_test,
            'extreme_scenarios': extreme_test,
            'historical_replay': historical_replay,
            'synthetic_bootstrap': synthetic_bootstrap,
            'value_at_risk': var_results
        }

    def generate_stress_report(self, stress_results: Dict) -> str:
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("天气衍生品压力测试报告")
        report_lines.append("=" * 70)

        if 'extreme_scenarios' in stress_results:
            report_lines.append("\n1. 合成极端情景测试:")
            report_lines.append("-" * 50)
            for _, row in stress_results['extreme_scenarios'].iterrows():
                report_lines.append(
                    f"  {row['scenario']:20s} | "
                    f"价格变化: {row['price_change_pct']:8.2f}% | "
                    f"HDD均值: {row['hdd_mean']:8.2f}"
                )

        if 'historical_replay' in stress_results and len(stress_results['historical_replay']) > 0:
            report_lines.append("\n2. 历史极值回放:")
            report_lines.append("-" * 50)
            for _, row in stress_results['historical_replay'].iterrows():
                report_lines.append(
                    f"  {row['scenario']:20s} | "
                    f"历史HDD: {row['historical_HDD']:8.2f} | "
                    f"价格变化: {row['price_change_pct']:8.2f}%"
                )

        if 'synthetic_bootstrap' in stress_results and len(stress_results['synthetic_bootstrap']) > 0:
            report_lines.append("\n3. Bootstrap合成极端情景:")
            report_lines.append("-" * 50)
            for _, row in stress_results['synthetic_bootstrap'].iterrows():
                report_lines.append(
                    f"  {row['scenario']:20s} | "
                    f"HDD值: {row['hdd_value']:8.2f} | "
                    f"价格: {row['price']:12.2f}"
                )

        if 'value_at_risk' in stress_results:
            report_lines.append("\n4. 风险价值分析:")
            report_lines.append("-" * 50)
            for key, value in stress_results['value_at_risk'].items():
                if key.startswith('VaR'):
                    report_lines.append(f"  {key}: ¥{value:,.2f}")

        return "\n".join(report_lines)
