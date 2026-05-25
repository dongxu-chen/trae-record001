"""
天气衍生品定价模型 - 气象数据生成模块
生成温度指数(HDD/CDD)和降雨量时间序列
"""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime, timedelta
from typing import Tuple, Optional


class WeatherDataGenerator:
    """气象数据生成器 - 基于历史统计特性生成模拟数据"""

    def __init__(self,
                 location: str = "Beijing",
                 base_temperature: float = 15.0,
                 temp_volatility: float = 8.0,
                 base_rainfall: float = 2.0,
                 rainfall_volatility: float = 5.0,
                 seed: Optional[int] = None):
        self.location = location
        self.base_temperature = base_temperature
        self.temp_volatility = temp_volatility
        self.base_rainfall = base_rainfall
        self.rainfall_volatility = rainfall_volatility
        self.rng = np.random.RandomState(seed)

    def generate_temperature(self,
                             start_date: str,
                             end_date: str,
                             trend: float = 0.0,
                             seasonality: bool = True) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        n = len(dates)

        t = np.arange(n)
        seasonal = np.zeros(n)
        if seasonality:
            seasonal = 15 * np.sin(2 * np.pi * (t - 80) / 365)

        trend_component = trend * t
        mean_temp = self.base_temperature + seasonal + trend_component

        ar1_coeff = 0.7
        noise = np.zeros(n)
        noise[0] = self.rng.normal(0, self.temp_volatility)

        for i in range(1, n):
            noise[i] = ar1_coeff * noise[i-1] + \
                       self.rng.normal(0, self.temp_volatility * np.sqrt(1 - ar1_coeff**2))

        temperature = mean_temp + noise

        return pd.DataFrame({
            'date': dates,
            'temperature': temperature,
            'seasonal': seasonal
        })

    def generate_rainfall(self,
                          start_date: str,
                          end_date: str) -> pd.DataFrame:
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        n = len(dates)

        rainy_days = self.rng.random(n) < 0.3
        rainfall = np.zeros(n)
        rainfall[rainy_days] = self.rng.gamma(2.0, self.rainfall_volatility/2,
                                                rainy_days.sum())

        return pd.DataFrame({
            'date': dates,
            'rainfall': rainfall
        })

    def calculate_hdd(self, temperature: pd.Series,
                      threshold: float = 18.0) -> pd.Series:
        return np.maximum(threshold - temperature, 0)

    def calculate_cdd(self, temperature: pd.Series,
                      threshold: float = 18.0) -> pd.Series:
        return np.maximum(temperature - threshold, 0)

    def generate_combined_data(self,
                               start_date: str,
                               end_date: str) -> pd.DataFrame:
        temp_df = self.generate_temperature(start_date, end_date)
        rain_df = self.generate_rainfall(start_date, end_date)

        df = temp_df.merge(rain_df, on='date', how='inner')
        df['HDD'] = self.calculate_hdd(df['temperature'])
        df['CDD'] = self.calculate_cdd(df['temperature'])
        df['cum_HDD'] = df['HDD'].cumsum()
        df['cum_CDD'] = df['CDD'].cumsum()
        df['cum_rainfall'] = df['rainfall'].cumsum()

        return df

    def generate_historical_years(self,
                                  start_year: int = 2010,
                                  end_year: int = 2024) -> pd.DataFrame:
        all_data = []
        for year in range(start_year, end_year + 1):
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            year_data = self.generate_combined_data(start_date, end_date)
            year_data['year'] = year
            all_data.append(year_data)

        return pd.concat(all_data, ignore_index=True)

    @staticmethod
    def fit_temperature_model(temperature: pd.Series) -> dict:
        values = temperature.values
        diff = np.diff(values)

        mu = np.mean(diff)
        sigma = np.std(diff)

        ar1_coeff = np.corrcoef(values[:-1], values[1:])[0, 1]

        return {
            'mu': mu,
            'sigma': sigma,
            'ar1_coeff': ar1_coeff,
            'mean': np.mean(values),
            'std': np.std(values)
        }

    @staticmethod
    def analyze_seasonality(temperature: pd.Series) -> dict:
        values = temperature.values
        n = len(values)

        t = np.arange(n)
        sin_component = np.sin(2 * np.pi * t / 365)
        cos_component = np.cos(2 * np.pi * t / 365)

        X = np.column_stack([np.ones(n), t, sin_component, cos_component])
        coeffs, _, _, _ = np.linalg.lstsq(X, values, rcond=None)

        return {
            'intercept': coeffs[0],
            'trend': coeffs[1],
            'sin_amplitude': coeffs[2],
            'cos_amplitude': coeffs[3],
            'seasonal_amplitude': np.sqrt(coeffs[2]**2 + coeffs[3]**2)
        }
