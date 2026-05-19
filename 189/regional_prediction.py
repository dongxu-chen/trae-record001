import numpy as np
import pandas as pd
from datetime import timedelta
from config import Config


class RegionalPrediction:
    def __init__(self):
        self.config = Config()
        self.city_network = {
            '北京': {
                'neighbors': ['天津', '廊坊', '保定', '张家口'],
                'distances': {'天津': 120, '廊坊': 60, '保定': 150, '张家口': 180},
                'wind_influence': {'天津': 0.3, '廊坊': 0.4, '保定': 0.25, '张家口': 0.2},
                'position': (39.9042, 116.4074)
            },
            '上海': {
                'neighbors': ['苏州', '嘉兴', '南通', '无锡'],
                'distances': {'苏州': 100, '嘉兴': 90, '南通': 120, '无锡': 140},
                'wind_influence': {'苏州': 0.35, '嘉兴': 0.3, '南通': 0.25, '无锡': 0.2},
                'position': (31.2304, 121.4737)
            },
            '广州': {
                'neighbors': ['佛山', '东莞', '深圳', '中山'],
                'distances': {'佛山': 30, '东莞': 50, '深圳': 120, '中山': 80},
                'wind_influence': {'佛山': 0.5, '东莞': 0.4, '深圳': 0.25, '中山': 0.3},
                'position': (23.1291, 113.2644)
            },
            '成都': {
                'neighbors': ['德阳', '绵阳', '资阳', '眉山'],
                'distances': {'德阳': 60, '绵阳': 100, '资阳': 80, '眉山': 70},
                'wind_influence': {'德阳': 0.4, '绵阳': 0.3, '资阳': 0.35, '眉山': 0.38},
                'position': (30.5728, 104.0668)
            }
        }

    def load_multi_city_data(self, data_path_pattern):
        city_data = {}
        for city in self.city_network.keys():
            file_path = data_path_pattern.format(city=city)
            try:
                df = pd.read_csv(file_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp').reset_index(drop=True)
                city_data[city] = df
            except FileNotFoundError:
                print(f"未找到城市 {city} 的数据文件: {file_path}")
        return city_data

    def calculate_diffusion_coefficient(self, wind_speed, wind_direction, distance, stability_class='D'):
        stability_factors = {
            'A': 0.2, 'B': 0.15, 'C': 0.1, 'D': 0.08, 'E': 0.06, 'F': 0.04
        }
        k = stability_factors.get(stability_class, 0.08)
        wind_factor = min(wind_speed / 5, 1)
        distance_decay = np.exp(-k * distance / 100)
        return wind_factor * distance_decay

    def calculate_regional_influence(self, target_city, city_data, target_time):
        if target_city not in self.city_network:
            return {}

        neighbors = self.city_network[target_city]['neighbors']
        influences = {}
        total_influence = 0

        for neighbor in neighbors:
            if neighbor in city_data:
                neighbor_df = city_data[neighbor]
                target_idx = neighbor_df[neighbor_df['timestamp'] <= target_time].index
                if len(target_idx) > 0:
                    latest_idx = target_idx[-1]
                    wind_speed = neighbor_df.iloc[latest_idx].get('WIND', 3)
                    distance = self.city_network[target_city]['distances'][neighbor]
                    base_influence = self.city_network[target_city]['wind_influence'][neighbor]

                    diffusion = self.calculate_diffusion_coefficient(wind_speed, 0, distance)
                    influence = base_influence * diffusion

                    time_lag = int(distance / (wind_speed * 3.6)) if wind_speed > 0 else 0
                    lagged_idx = max(0, latest_idx - time_lag)

                    neighbor_concentration = neighbor_df.iloc[lagged_idx][['PM2.5', 'PM10', 'SO2', 'NO2', 'O3']].values

                    influences[neighbor] = {
                        'influence_coefficient': influence,
                        'time_lag_hours': time_lag,
                        'contributed_concentrations': neighbor_concentration * influence,
                        'wind_speed': wind_speed,
                        'distance': distance
                    }
                    total_influence += influence

        if total_influence > 0:
            for neighbor in influences:
                influences[neighbor]['normalized_influence'] = influences[neighbor]['influence_coefficient'] / total_influence

        return influences

    def generate_regional_prediction(self, target_city, city_data, base_predictions):
        target_df = city_data.get(target_city)
        if target_df is None or len(base_predictions) == 0:
            return base_predictions

        adjusted_predictions = base_predictions.copy()
        regional_contributions = []

        for i, pred_row in adjusted_predictions.iterrows():
            pred_time = pred_row['timestamp']
            influences = self.calculate_regional_influence(target_city, city_data, pred_time)

            regional_influence = np.zeros(5)
            neighbor_details = []

            for neighbor, info in influences.items():
                if 'normalized_influence' in info:
                    contribution = info['contributed_concentrations'] * info['normalized_influence']
                    regional_influence += contribution
                    neighbor_details.append({
                        'neighbor': neighbor,
                        'contribution_pct': info['normalized_influence'] * 100,
                        'time_lag': info['time_lag_hours']
                    })

            weight = 0.15
            pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3']
            for j, pollutant in enumerate(pollutants):
                original = pred_row[pollutant]
                adjusted = original * (1 - weight) + regional_influence[j] * weight
                adjusted_predictions.at[i, pollutant] = max(0, adjusted)

            regional_contributions.append({
                'timestamp': pred_time,
                'neighbor_details': neighbor_details,
                'total_regional_influence': np.sum(regional_influence)
            })

        return adjusted_predictions, regional_contributions

    def analyze_transport_path(self, target_city, source_city, city_data, start_time, hours=24):
        if source_city not in self.city_network or target_city not in self.city_network:
            return None

        target_df = city_data.get(target_city)
        source_df = city_data.get(source_city)
        if target_df is None or source_df is None:
            return None

        distance = self.city_network[target_city]['distances'].get(source_city, 100)
        wind_influence = self.city_network[target_city]['wind_influence'].get(source_city, 0.3)

        transport_data = []
        for hour in range(hours):
            current_time = start_time + timedelta(hours=hour)

            source_idx = source_df[source_df['timestamp'] <= current_time].index
            target_idx = target_df[target_df['timestamp'] <= current_time].index

            if len(source_idx) > 0 and len(target_idx) > 0:
                source_data = source_df.iloc[source_idx[-1]]
                target_data = target_df.iloc[target_idx[-1]]

                wind_speed = source_data.get('WIND', 3)
                transport_time = distance / (wind_speed * 3.6) if wind_speed > 0 else float('inf')
                diffusion = self.calculate_diffusion_coefficient(wind_speed, 0, distance)

                transport_data.append({
                    'timestamp': current_time,
                    'source_aqi': source_data.get('AQI', 0),
                    'target_aqi': target_data.get('AQI', 0),
                    'wind_speed': wind_speed,
                    'transport_time_hours': transport_time,
                    'diffusion_coefficient': diffusion,
                    'expected_influence': wind_influence * diffusion
                })

        return pd.DataFrame(transport_data)

    def print_regional_report(self, target_city, regional_contributions, adjusted_predictions):
        print("\n" + "=" * 80)
        print(f" " * 20 + f"{target_city} 区域联动预测报告")
        print("=" * 80)

        print(f"\n📍 目标城市: {target_city}")
        print(f"🌐 相邻城市: {', '.join(self.city_network.get(target_city, {}).get('neighbors', []))}")

        if len(regional_contributions) > 0:
            first = regional_contributions[0]
            print(f"\n👥 周边城市影响分析:")
            for detail in first['neighbor_details']:
                print(f"  - {detail['neighbor']}: 贡献 {detail['contribution_pct']:.1f}%, 传输滞后 {detail['time_lag']} 小时")

            avg_influence = np.mean([c['total_regional_influence'] for c in regional_contributions])
            print(f"\n📊 平均区域贡献量: {avg_influence:.2f} μg/m³")

        print("\n📈 区域联动调整后预测:")
        print(f"{'时间':<16} {'AQI':<8} {'PM2.5':<8} {'PM10':<8} {'SO2':<8} {'NO2':<8} {'O3':<8}")
        print("-" * 70)

        for _, row in adjusted_predictions.head(6).iterrows():
            time_str = row['timestamp'].strftime('%m-%d %H:00')
            aqi = row.get('AQI', 0)
            print(f"{time_str:<16} {aqi:<8.0f} {row['PM2.5']:<8.1f} {row['PM10']:<8.1f} {row['SO2']:<8.1f} {row['NO2']:<8.1f} {row['O3']:<8.1f}")

        print("\n" + "=" * 80)
