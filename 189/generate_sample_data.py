import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from config import Config


def generate_air_quality_data(start_date, days=730, seed=42, city='北京'):
    np.random.seed(seed)
    config = Config()

    city_factors = {
        '北京': {'pm25': 1.2, 'pm10': 1.15, 'so2': 1.1, 'no2': 1.2, 'o3': 0.95, 'temp': 1.0, 'hum': 0.9},
        '上海': {'pm25': 0.9, 'pm10': 0.85, 'so2': 0.8, 'no2': 1.0, 'o3': 1.05, 'temp': 1.1, 'hum': 1.1},
        '广州': {'pm25': 0.85, 'pm10': 0.8, 'so2': 0.75, 'no2': 0.9, 'o3': 1.15, 'temp': 1.2, 'hum': 1.2},
        '成都': {'pm25': 1.1, 'pm10': 1.05, 'so2': 0.95, 'no2': 1.0, 'o3': 0.9, 'temp': 1.05, 'hum': 1.15}
    }
    factors = city_factors.get(city, {k: 1.0 for k in ['pm25', 'pm10', 'so2', 'no2', 'o3', 'temp', 'hum']})

    total_hours = days * 24
    timestamps = [start_date + timedelta(hours=i) for i in range(total_hours)]

    data = {
        'timestamp': timestamps,
        'PM2.5': [],
        'PM10': [],
        'SO2': [],
        'NO2': [],
        'O3': [],
        'WIND': [],
        'TEMP': [],
        'HUM': []
    }

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        month = ts.month

        seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * (month - 1) / 12)
        diurnal_factor = 1 + 0.2 * np.sin(2 * np.pi * (hour - 6) / 24)

        base_pm25 = 35 * factors['pm25'] * seasonal_factor * diurnal_factor
        pm25 = np.clip(np.random.normal(base_pm25, base_pm25 * 0.3), 5, 250)

        base_pm10 = 70 * factors['pm10'] * seasonal_factor * diurnal_factor
        pm10 = np.clip(np.random.normal(base_pm10, base_pm10 * 0.25), 10, 400)

        base_so2 = 20 * factors['so2'] * seasonal_factor
        so2 = np.clip(np.random.normal(base_so2, base_so2 * 0.4), 2, 200)

        base_no2 = 30 * factors['no2'] * seasonal_factor * (1 + 0.3 * (1 if 7 <= hour <= 9 or 17 <= hour <= 19 else 0))
        no2 = np.clip(np.random.normal(base_no2, base_no2 * 0.3), 5, 150)

        base_o3 = 60 * factors['o3'] * (1 - 0.5 * seasonal_factor) * (1 + 0.4 * np.sin(2 * np.pi * (hour - 12) / 24))
        o3 = np.clip(np.random.normal(base_o3, base_o3 * 0.3), 20, 300)

        base_wind = 3 + 2 * np.random.random()
        wind = np.clip(base_wind + 0.5 * np.sin(2 * np.pi * (hour - 10) / 24), 0.5, 15)

        base_temp = 15 * factors['temp'] + 10 * np.sin(2 * np.pi * (month - 4) / 12)
        temp = np.clip(base_temp + 5 * np.sin(2 * np.pi * (hour - 14) / 24) + np.random.normal(0, 2), -10, 45)

        base_hum = 60 * factors['hum'] - 20 * np.sin(2 * np.pi * (month - 7) / 12)
        hum = np.clip(base_hum - 10 * np.sin(2 * np.pi * (hour - 14) / 24) + np.random.normal(0, 5), 20, 95)

        data['PM2.5'].append(round(pm25, 1))
        data['PM10'].append(round(pm10, 1))
        data['SO2'].append(round(so2, 1))
        data['NO2'].append(round(no2, 1))
        data['O3'].append(round(o3, 1))
        data['WIND'].append(round(wind, 1))
        data['TEMP'].append(round(temp, 1))
        data['HUM'].append(round(hum, 1))

    df = pd.DataFrame(data)

    for col in ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3']:
        mask = np.random.random(len(df)) < 0.02
        df.loc[mask, col] = np.nan

    return df


def generate_multi_city_data(start_date, days=730, base_seed=42):
    config = Config()
    cities = config.CITIES

    os.makedirs('data', exist_ok=True)

    for i, city in enumerate(cities):
        seed = base_seed + i * 100
        print(f"正在生成 {city} 的空气质量数据...")
        df = generate_air_quality_data(start_date, days=days, seed=seed, city=city)

        output_path = f'data/air_quality_{city}.csv'
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"  已保存到: {output_path}, 数据量: {len(df)} 条")

    default_path = 'data/air_quality_data.csv'
    default_df = generate_air_quality_data(start_date, days=days, seed=base_seed, city=config.DEFAULT_CITY)
    default_df.to_csv(default_path, index=False, encoding='utf-8-sig')
    print(f"\n默认城市数据已保存到: {default_path}")

    return default_df


def main():
    config = Config()
    start_date = datetime(2023, 1, 1, 0, 0, 0)
    print("正在生成多城市示例空气质量数据...")
    print(f"城市列表: {', '.join(config.CITIES)}")
    print(f"默认城市: {config.DEFAULT_CITY}")
    print()

    df = generate_multi_city_data(start_date, days=730)

    print(f"\n默认城市数据统计:")
    print(df[config.FEATURE_COLS].describe())

    return df


if __name__ == '__main__':
    main()
