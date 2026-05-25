"""
蒙特卡洛模拟引擎 - 天气衍生品定价
支持参数模型和非参数Bootstrap两种模拟方法
希腊值计算使用自适应中心差分步长优化
"""

import numpy as np
import pandas as pd
from typing import Tuple, Callable, Optional, Dict, List
from dataclasses import dataclass, field

try:
    from bootstrap_engine import BootstrapWeatherSimulator, BootstrapConfig
    HAS_BOOTSTRAP = True
except ImportError:
    HAS_BOOTSTRAP = False


@dataclass
class WeatherOptionContract:
    """天气衍生品合约定义"""
    contract_type: str
    strike: float
    tick_size: float
    notional: float
    start_date: str
    end_date: str
    payment_date: str

    @property
    def days_to_maturity(self) -> int:
        from datetime import datetime
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        return (end - start).days

    @property
    def start_day_of_year(self) -> int:
        from datetime import datetime
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        return start.timetuple().tm_yday


@dataclass
class GreeksConfig:
    delta_shift: float = 1.0
    gamma_shift: float = 2.0
    use_adaptive_step: bool = True
    min_step: float = 0.1
    max_step: float = 10.0
    step_tolerance: float = 0.01


class MonteCarloPricingEngine:
    """蒙特卡洛模拟定价引擎 - 支持参数化和Bootstrap两种方法"""

    def __init__(self,
                 n_simulations: int = 10000,
                 n_time_steps: int = 365,
                 seed: Optional[int] = None,
                 bootstrap_simulator: Optional['BootstrapWeatherSimulator'] = None):
        self.n_simulations = n_simulations
        self.n_time_steps = n_time_steps
        self.rng = np.random.RandomState(seed)
        self.bootstrap_simulator = bootstrap_simulator
        self.greeks_config = GreeksConfig()

    def simulate_temperature_paths_parametric(self,
                                               initial_temp: float,
                                               mu: float,
                                               sigma: float,
                                               ar1_coeff: float,
                                               seasonal_amplitude: float,
                                               n_days: int) -> np.ndarray:
        n_sims = self.n_simulations

        Z = self.rng.normal(0, 1, (n_sims, n_days))
        paths = np.zeros((n_sims, n_days + 1))
        paths[:, 0] = initial_temp

        for t in range(1, n_days + 1):
            seasonal = -seasonal_amplitude * np.sin(2 * np.pi * t / 365 + np.pi/4)
            mean_reversion = ar1_coeff * (paths[:, t-1] - (initial_temp + seasonal))
            random_shock = sigma * Z[:, t-1]

            paths[:, t] = initial_temp + seasonal + mean_reversion + random_shock

        return paths

    def simulate_hdd_bootstrap(self,
                               start_day: int,
                               n_days: int,
                               method: str = 'seasonal_block') -> np.ndarray:
        if not HAS_BOOTSTRAP or self.bootstrap_simulator is None:
            raise ValueError("Bootstrap simulator not available")

        samples = self.bootstrap_simulator.generate_bootstrap_samples(
            start_day=start_day,
            n_days=n_days,
            n_samples=self.n_simulations,
            method=method
        )

        hdd_paths = samples[:, :, 1]
        return hdd_paths

    def simulate_temperature_bootstrap(self,
                                       start_day: int,
                                       n_days: int,
                                       method: str = 'seasonal_block') -> np.ndarray:
        if not HAS_BOOTSTRAP or self.bootstrap_simulator is None:
            raise ValueError("Bootstrap simulator not available")

        samples = self.bootstrap_simulator.generate_bootstrap_samples(
            start_day=start_day,
            n_days=n_days,
            n_samples=self.n_simulations,
            method=method
        )

        temp_paths = samples[:, :, 0]
        return temp_paths

    def simulate_rainfall_bootstrap(self,
                                    start_day: int,
                                    n_days: int,
                                    method: str = 'seasonal_block') -> np.ndarray:
        if not HAS_BOOTSTRAP or self.bootstrap_simulator is None:
            raise ValueError("Bootstrap simulator not available")

        samples = self.bootstrap_simulator.generate_bootstrap_samples(
            start_day=start_day,
            n_days=n_days,
            n_samples=self.n_simulations,
            method=method
        )

        rain_paths = samples[:, :, 3]
        return rain_paths

    def simulate_rainfall_paths(self,
                                mu_rain: float,
                                sigma_rain: float,
                                n_days: int) -> np.ndarray:
        n_sims = self.n_simulations
        paths = np.zeros((n_sims, n_days + 1))

        for t in range(1, n_days + 1):
            rain_days = self.rng.random(n_sims) < 0.3
            daily_rain = np.zeros(n_sims)
            daily_rain[rain_days] = self.rng.gamma(
                2.0, sigma_rain/2, rain_days.sum()
            )
            paths[:, t] = paths[:, t-1] + daily_rain

        return paths

    def calculate_hdd_from_paths(self,
                                 temp_paths: np.ndarray,
                                 threshold: float = 18.0) -> np.ndarray:
        daily_hdd = np.maximum(threshold - temp_paths, 0)
        return daily_hdd.sum(axis=1)

    def calculate_cdd_from_paths(self,
                                 temp_paths: np.ndarray,
                                 threshold: float = 18.0) -> np.ndarray:
        daily_cdd = np.maximum(temp_paths - threshold, 0)
        return daily_cdd.sum(axis=1)

    def price_hdd_option(self,
                         contract: WeatherOptionContract,
                         initial_temp: float = None,
                         mu: float = 0.0,
                         sigma: float = 8.0,
                         ar1_coeff: float = 0.85,
                         seasonal_amplitude: float = 15.0,
                         risk_free_rate: float = 0.03,
                         use_bootstrap: bool = False,
                         bootstrap_method: str = 'seasonal_block') -> Dict:
        n_days = contract.days_to_maturity

        if use_bootstrap and self.bootstrap_simulator is not None:
            hdd_paths = self.simulate_hdd_bootstrap(
                start_day=contract.start_day_of_year,
                n_days=n_days,
                method=bootstrap_method
            )
            hdd_values = hdd_paths.sum(axis=1)
        else:
            temp_paths = self.simulate_temperature_paths_parametric(
                initial_temp, mu, sigma, ar1_coeff, seasonal_amplitude, n_days
            )
            hdd_values = self.calculate_hdd_from_paths(temp_paths)

        dt = n_days / 365
        discount_factor = np.exp(-risk_free_rate * dt)

        if 'call' in contract.contract_type:
            payoffs = np.maximum(hdd_values - contract.strike, 0)
        else:
            payoffs = np.maximum(contract.strike - hdd_values, 0)

        discounted_payoffs = payoffs * contract.tick_size * discount_factor

        price = np.mean(discounted_payoffs)
        price_std = np.std(discounted_payoffs) / np.sqrt(self.n_simulations)
        price_ci = 1.96 * price_std

        in_the_money = np.mean(payoffs > 0)

        return {
            'price': price,
            'price_std': price_std,
            'price_ci': price_ci,
            'hdd_mean': np.mean(hdd_values),
            'hdd_std': np.std(hdd_values),
            'hdd_median': np.median(hdd_values),
            'hdd_q5': np.percentile(hdd_values, 5),
            'hdd_q95': np.percentile(hdd_values, 95),
            'probability_exercise': in_the_money,
            'expected_payoff': np.mean(payoffs * contract.tick_size),
            'all_payoffs': discounted_payoffs,
            'method': 'bootstrap' if use_bootstrap else 'parametric'
        }

    def price_cdd_option(self,
                         contract: WeatherOptionContract,
                         initial_temp: float = None,
                         mu: float = 0.0,
                         sigma: float = 8.0,
                         ar1_coeff: float = 0.85,
                         seasonal_amplitude: float = 15.0,
                         risk_free_rate: float = 0.03,
                         use_bootstrap: bool = False,
                         bootstrap_method: str = 'seasonal_block') -> Dict:
        n_days = contract.days_to_maturity

        if use_bootstrap and self.bootstrap_simulator is not None:
            temp_paths = self.simulate_temperature_bootstrap(
                start_day=contract.start_day_of_year,
                n_days=n_days,
                method=bootstrap_method
            )
            cdd_values = self.calculate_cdd_from_paths(temp_paths)
        else:
            temp_paths = self.simulate_temperature_paths_parametric(
                initial_temp, mu, sigma, ar1_coeff, seasonal_amplitude, n_days
            )
            cdd_values = self.calculate_cdd_from_paths(temp_paths)

        dt = n_days / 365
        discount_factor = np.exp(-risk_free_rate * dt)

        if 'call' in contract.contract_type:
            payoffs = np.maximum(cdd_values - contract.strike, 0)
        else:
            payoffs = np.maximum(contract.strike - cdd_values, 0)

        discounted_payoffs = payoffs * contract.tick_size * discount_factor

        price = np.mean(discounted_payoffs)
        price_std = np.std(discounted_payoffs) / np.sqrt(self.n_simulations)
        price_ci = 1.96 * price_std

        in_the_money = np.mean(payoffs > 0)

        return {
            'price': price,
            'price_std': price_std,
            'price_ci': price_ci,
            'cdd_mean': np.mean(cdd_values),
            'cdd_std': np.std(cdd_values),
            'probability_exercise': in_the_money,
            'expected_payoff': np.mean(payoffs * contract.tick_size),
            'all_payoffs': discounted_payoffs
        }

    def price_rainfall_option(self,
                              contract: WeatherOptionContract,
                              mu_rain: float = 2.0,
                              sigma_rain: float = 5.0,
                              risk_free_rate: float = 0.03,
                              use_bootstrap: bool = False,
                              bootstrap_method: str = 'seasonal_block') -> Dict:
        n_days = contract.days_to_maturity

        if use_bootstrap and self.bootstrap_simulator is not None:
            rain_paths = self.simulate_rainfall_bootstrap(
                start_day=contract.start_day_of_year,
                n_days=n_days,
                method=bootstrap_method
            )
            rain_values = rain_paths.sum(axis=1)
        else:
            rain_paths = self.simulate_rainfall_paths(mu_rain, sigma_rain, n_days)
            rain_values = rain_paths[:, -1]

        dt = n_days / 365
        discount_factor = np.exp(-risk_free_rate * dt)

        if 'call' in contract.contract_type:
            payoffs = np.maximum(rain_values - contract.strike, 0)
        else:
            payoffs = np.maximum(contract.strike - rain_values, 0)

        discounted_payoffs = payoffs * contract.tick_size * discount_factor

        price = np.mean(discounted_payoffs)
        price_std = np.std(discounted_payoffs) / np.sqrt(self.n_simulations)
        price_ci = 1.96 * price_std

        in_the_money = np.mean(payoffs > 0)

        return {
            'price': price,
            'price_std': price_std,
            'price_ci': price_ci,
            'rainfall_mean': np.mean(rain_values),
            'rainfall_std': np.std(rain_values),
            'probability_exercise': in_the_money,
            'expected_payoff': np.mean(payoffs * contract.tick_size),
            'all_payoffs': discounted_payoffs
        }

    def _adaptive_step_size(self,
                            base_value: float,
                            price_func: Callable,
                            shift: float,
                            min_step: float,
                            max_step: float,
                            tolerance: float) -> float:
        best_step = shift
        best_error = float('inf')

        for step in np.logspace(np.log10(min_step), np.log10(max_step), 20):
            p_up = price_func(step)
            p_down = price_func(-step)
            numerical_deriv = (p_up - p_down) / (2 * step)

            if abs(numerical_deriv) > 1e-10:
                error = abs((p_up - 2 * base_value + p_down) / (step ** 2))
                if error < best_error:
                    best_error = error
                    best_step = step

        return best_step

    def calculate_greeks(self,
                         contract: WeatherOptionContract,
                         initial_temp: float = None,
                         mu: float = 0.0,
                         sigma: float = 8.0,
                         ar1_coeff: float = 0.85,
                         seasonal_amplitude: float = 15.0,
                         risk_free_rate: float = 0.03,
                         use_bootstrap: bool = False,
                         bootstrap_method: str = 'seasonal_block',
                         config: GreeksConfig = None) -> Dict:
        if config is None:
            config = self.greeks_config

        base_result = self.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
        )
        base_price = base_result['price']

        def price_at_temp(temp_shift):
            if use_bootstrap:
                return self.price_hdd_option(
                    contract, initial_temp, mu, sigma, ar1_coeff,
                    seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
                )['price']
            else:
                return self.price_hdd_option(
                    contract, initial_temp + temp_shift, mu, sigma, ar1_coeff,
                    seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
                )['price']

        delta_shift = config.delta_shift
        gamma_shift = config.gamma_shift

        if config.use_adaptive_step and not use_bootstrap:
            delta_shift = self._adaptive_step_size(
                base_price, price_at_temp, config.delta_shift,
                config.min_step, config.max_step, config.step_tolerance
            )

            gamma_shift = max(delta_shift * 2, config.gamma_shift)

        price_up = price_at_temp(delta_shift)
        price_down = price_at_temp(-delta_shift)

        delta = (price_up - price_down) / (2 * delta_shift)

        price_up_gamma = price_at_temp(gamma_shift)
        price_down_gamma = price_at_temp(-gamma_shift)

        gamma = (price_up_gamma - 2 * base_price + price_down_gamma) / (gamma_shift ** 2)

        rates = [0.02, 0.03, 0.04]
        vega_prices = []
        for r in rates:
            p = self.price_hdd_option(
                contract, initial_temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, r, use_bootstrap, bootstrap_method
            )['price']
            vega_prices.append(p)

        if len(rates) >= 2:
            rho = (vega_prices[-1] - vega_prices[0]) / (rates[-1] - rates[0])
        else:
            rho = 0.0

        vega_base = self.price_hdd_option(
            contract, initial_temp, mu, sigma * 1.01, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
        )['price']
        vega = (vega_base - base_price) / (sigma * 0.01)

        return {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'rho': rho,
            'theta': self._calculate_theta(
                contract, initial_temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
            ),
            'base_price': base_price,
            'price_up': price_up,
            'price_down': price_down,
            'delta_shift': delta_shift,
            'gamma_shift': gamma_shift,
            'method': 'adaptive_central_difference'
        }

    def _calculate_theta(self,
                         contract: WeatherOptionContract,
                         initial_temp: float,
                         mu: float,
                         sigma: float,
                         ar1_coeff: float,
                         seasonal_amplitude: float,
                         risk_free_rate: float,
                         use_bootstrap: bool,
                         bootstrap_method: str) -> float:
        from datetime import datetime, timedelta

        base_price = self.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
        )['price']

        start = datetime.strptime(contract.start_date, '%Y-%m-%d')
        new_start = start + timedelta(days=1)

        new_contract = WeatherOptionContract(
            contract_type=contract.contract_type,
            strike=contract.strike,
            tick_size=contract.tick_size,
            notional=contract.notional,
            start_date=new_start.strftime('%Y-%m-%d'),
            end_date=contract.end_date,
            payment_date=contract.payment_date
        )

        new_price = self.price_hdd_option(
            new_contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
        )['price']

        return new_price - base_price

    def generate_pricing_curve(self,
                               contract: WeatherOptionContract,
                               temp_range: Tuple[float, float],
                               mu: float = 0.0,
                               sigma: float = 8.0,
                               ar1_coeff: float = 0.85,
                               seasonal_amplitude: float = 15.0,
                               n_points: int = 20,
                               risk_free_rate: float = 0.03,
                               use_bootstrap: bool = False,
                               bootstrap_method: str = 'seasonal_block') -> pd.DataFrame:
        temps = np.linspace(temp_range[0], temp_range[1], n_points)
        results = []

        for temp in temps:
            price_result = self.price_hdd_option(
                contract, temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap, bootstrap_method
            )
            results.append({
                'temperature': temp,
                'price': price_result['price'],
                'price_std': price_result['price_std'],
                'price_ci_low': price_result['price'] - price_result['price_ci'],
                'price_ci_high': price_result['price'] + price_result['price_ci'],
                'hdd_mean': price_result['hdd_mean'],
                'hdd_median': price_result.get('hdd_median', 0),
                'hdd_q5': price_result.get('hdd_q5', 0),
                'hdd_q95': price_result.get('hdd_q95', 0),
                'exercise_prob': price_result['probability_exercise']
            })

        return pd.DataFrame(results)

    def compare_methods(self,
                        contract: WeatherOptionContract,
                        initial_temp: float,
                        mu: float,
                        sigma: float,
                        ar1_coeff: float,
                        seasonal_amplitude: float,
                        risk_free_rate: float = 0.03) -> Dict:
        param_result = self.price_hdd_option(
            contract, initial_temp, mu, sigma, ar1_coeff,
            seasonal_amplitude, risk_free_rate, use_bootstrap=False
        )

        boot_result = None
        if self.bootstrap_simulator is not None:
            boot_result = self.price_hdd_option(
                contract, initial_temp, mu, sigma, ar1_coeff,
                seasonal_amplitude, risk_free_rate, use_bootstrap=True
            )

        return {
            'parametric': param_result,
            'bootstrap': boot_result
        }
