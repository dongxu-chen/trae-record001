import pandas as pd
import numpy as np
from datetime import datetime
from geopy.distance import geodesic
from collections import defaultdict
import json
import os

class CourierProfiler:
    def __init__(self, grid_size_km=2.0, city_center=(31.2304, 121.4737)):
        self.grid_size_km = grid_size_km
        self.city_center = city_center
        self.courier_profiles = {}
        self.region_speed_stats = {}
    
    def _get_region_key(self, lat, lon):
        lat_offset = (lat - self.city_center[0]) * 111
        lon_offset = (lon - self.city_center[1]) * 111 * np.cos(np.radians(self.city_center[0]))
        
        grid_lat = int(np.floor(lat_offset / self.grid_size_km))
        grid_lon = int(np.floor(lon_offset / self.grid_size_km))
        
        return f"R_{grid_lat}_{grid_lon}"
    
    def _get_region_bounds(self, region_key):
        parts = region_key.split('_')
        grid_lat = int(parts[1])
        grid_lon = int(parts[2])
        
        lat_min = self.city_center[0] + grid_lat * self.grid_size_km / 111
        lat_max = self.city_center[0] + (grid_lat + 1) * self.grid_size_km / 111
        lon_min = self.city_center[1] + grid_lon * self.grid_size_km / (111 * np.cos(np.radians(self.city_center[0])))
        lon_max = self.city_center[1] + (grid_lon + 1) * self.grid_size_km / (111 * np.cos(np.radians(self.city_center[0])))
        
        return {
            'lat_min': lat_min, 'lat_max': lat_max,
            'lon_min': lon_min, 'lon_max': lon_max,
            'center_lat': (lat_min + lat_max) / 2,
            'center_lon': (lon_min + lon_max) / 2
        }
    
    def build_profiles(self, historical_df):
        if isinstance(historical_df['order_datetime'].iloc[0], str):
            historical_df['order_datetime'] = pd.to_datetime(historical_df['order_datetime'])
        
        courier_regions = defaultdict(lambda: defaultdict(list))
        
        for _, row in historical_df.iterrows():
            courier_id = row['courier_id']
            
            pickup_region = self._get_region_key(row['pickup_lat'], row['pickup_lon'])
            dropoff_region = self._get_region_key(row['dropoff_lat'], row['dropoff_lon'])
            
            for region in [pickup_region, dropoff_region]:
                courier_regions[courier_id][region].append({
                    'speed': row['courier_avg_speed'],
                    'delivery_time': row['actual_delivery_minutes'],
                    'distance': row['distance_km'],
                    'on_time': row['on_time'],
                    'datetime': row['order_datetime']
                })
        
        for courier_id, regions_data in courier_regions.items():
            profile = {
                'courier_id': courier_id,
                'regions': {},
                'overall_stats': {
                    'avg_speed': 0,
                    'avg_delivery_time': 0,
                    'total_deliveries': 0,
                    'on_time_rate': 0
                },
                'preferred_regions': [],
                'avoid_regions': [],
                'time_period_preferences': {}
            }
            
            all_speeds = []
            all_times = []
            all_on_time = []
            
            for region_key, records in regions_data.items():
                speeds = [r['speed'] for r in records]
                times = [r['delivery_time'] for r in records]
                on_times = [r['on_time'] for r in records]
                
                region_stats = {
                    'delivery_count': len(records),
                    'avg_speed': np.mean(speeds),
                    'speed_std': np.std(speeds),
                    'avg_delivery_time': np.mean(times),
                    'on_time_rate': np.mean(on_times),
                    'total_distance': sum(r['distance'] for r in records)
                }
                
                profile['regions'][region_key] = region_stats
                
                all_speeds.extend(speeds)
                all_times.extend(times)
                all_on_time.extend(on_times)
                
                hour_counts = defaultdict(int)
                for r in records:
                    hour = r['datetime'].hour
                    hour_counts[hour] += 1
                
                if hour_counts:
                    peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
                    profile['time_period_preferences'][region_key] = peak_hour
            
            if all_speeds:
                profile['overall_stats'] = {
                    'avg_speed': np.mean(all_speeds),
                    'avg_delivery_time': np.mean(all_times),
                    'total_deliveries': len(all_speeds),
                    'on_time_rate': np.mean(all_on_time)
                }
            
            overall_avg_speed = profile['overall_stats']['avg_speed']
            overall_ot_rate = profile['overall_stats']['on_time_rate']
            
            for region_key, stats in profile['regions'].items():
                if stats['delivery_count'] >= 5:
                    speed_advantage = (stats['avg_speed'] - overall_avg_speed) / overall_avg_speed
                    ot_advantage = (stats['on_time_rate'] - overall_ot_rate)
                    
                    if speed_advantage > 0.1 and ot_advantage > 0:
                        profile['preferred_regions'].append({
                            'region_key': region_key,
                            'speed_advantage_pct': round(speed_advantage * 100, 1),
                            'ot_advantage': round(ot_advantage * 100, 1),
                            'delivery_count': stats['delivery_count'],
                            **self._get_region_bounds(region_key)
                        })
                    elif speed_advantage < -0.15 or ot_advantage < -0.1:
                        profile['avoid_regions'].append({
                            'region_key': region_key,
                            'speed_advantage_pct': round(speed_advantage * 100, 1),
                            'ot_advantage': round(ot_advantage * 100, 1),
                            'delivery_count': stats['delivery_count'],
                            **self._get_region_bounds(region_key)
                        })
            
            profile['preferred_regions'].sort(key=lambda x: x['speed_advantage_pct'], reverse=True)
            profile['avoid_regions'].sort(key=lambda x: x['speed_advantage_pct'])
            
            self.courier_profiles[courier_id] = profile
        
        self._build_region_speed_stats(historical_df)
        
        return self.courier_profiles
    
    def _build_region_speed_stats(self, historical_df):
        region_speeds = defaultdict(list)
        
        for _, row in historical_df.iterrows():
            pickup_region = self._get_region_key(row['pickup_lat'], row['pickup_lon'])
            dropoff_region = self._get_region_key(row['dropoff_lat'], row['dropoff_lon'])
            
            for region in [pickup_region, dropoff_region]:
                region_speeds[region].append({
                    'speed': row['courier_avg_speed'],
                    'delivery_time': row['actual_delivery_minutes'],
                    'courier_id': row['courier_id']
                })
        
        for region_key, records in region_speeds.items():
            if len(records) >= 10:
                speeds = [r['speed'] for r in records]
                self.region_speed_stats[region_key] = {
                    'avg_speed': np.mean(speeds),
                    'speed_std': np.std(speeds),
                    'delivery_count': len(records),
                    **self._get_region_bounds(region_key)
                }
    
    def get_courier_region_advantage(self, courier_id, lat, lon):
        if courier_id not in self.courier_profiles:
            return 1.0
        
        region_key = self._get_region_key(lat, lon)
        profile = self.courier_profiles[courier_id]
        
        for pref in profile['preferred_regions']:
            if pref['region_key'] == region_key:
                return 1.0 + pref['speed_advantage_pct'] / 100
        
        for avoid in profile['avoid_regions']:
            if avoid['region_key'] == region_key:
                return max(0.7, 1.0 + avoid['speed_advantage_pct'] / 100)
        
        return 1.0
    
    def get_courier_profile(self, courier_id):
        return self.courier_profiles.get(courier_id, None)
    
    def get_region_top_couriers(self, lat, lon, top_n=5):
        region_key = self._get_region_key(lat, lon)
        
        courier_advantages = []
        for courier_id, profile in self.courier_profiles.items():
            advantage = self.get_courier_region_advantage(courier_id, lat, lon)
            courier_advantages.append({
                'courier_id': courier_id,
                'advantage_factor': advantage,
                'overall_on_time_rate': profile['overall_stats']['on_time_rate'],
                'region_experience': profile['regions'].get(region_key, {}).get('delivery_count', 0)
            })
        
        courier_advantages.sort(key=lambda x: x['advantage_factor'], reverse=True)
        return courier_advantages[:top_n]
    
    def save_profiles(self, filepath='models/courier_profiles.json'):
        serializable = {}
        for cid, profile in self.courier_profiles.items():
            serializable[cid] = {
                'courier_id': profile['courier_id'],
                'regions': profile['regions'],
                'overall_stats': profile['overall_stats'],
                'preferred_regions': profile['preferred_regions'],
                'avoid_regions': profile['avoid_regions'],
                'time_period_preferences': profile['time_period_preferences']
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        
        print(f'配送员画像已保存到 {filepath}')
    
    def load_profiles(self, filepath='models/courier_profiles.json'):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self.courier_profiles = json.load(f)
            print(f'配送员画像已从 {filepath} 加载')
            return True
        return False

class RealTimeETARefresher:
    def __init__(self, eta_predictor, feature_engineer, courier_profiler=None):
        self.eta_predictor = eta_predictor
        self.feature_engineer = feature_engineer
        self.courier_profiler = courier_profiler
        self.active_deliveries = {}
        self.refresh_interval_seconds = 60
    
    def start_delivery(self, delivery_id, initial_features, initial_eta):
        self.active_deliveries[delivery_id] = {
            'features': initial_features,
            'initial_eta': initial_eta,
            'current_eta': initial_eta,
            'checkpoints': [],
            'start_time': datetime.now(),
            'last_refresh': datetime.now(),
            'eta_history': [(datetime.now(), initial_eta)]
        }
    
    def update_trajectory(self, delivery_id, current_lat, current_lon, current_time=None):
        if delivery_id not in self.active_deliveries:
            return None
        
        if current_time is None:
            current_time = datetime.now()
        
        delivery = self.active_deliveries[delivery_id]
        
        elapsed_seconds = (current_time - delivery['start_time']).total_seconds()
        elapsed_minutes = elapsed_seconds / 60
        
        delivery['checkpoints'].append({
            'time': current_time,
            'lat': current_lat,
            'lon': current_lon,
            'elapsed_minutes': elapsed_minutes
        })
        
        delivery['last_refresh'] = current_time
        
        new_eta = self._recalculate_eta(delivery, current_lat, current_lon, current_time)
        
        eta_change_pct = (new_eta - delivery['current_eta']) / delivery['current_eta'] * 100
        
        delivery['current_eta'] = new_eta
        delivery['eta_history'].append((current_time, new_eta))
        
        return {
            'delivery_id': delivery_id,
            'new_eta': new_eta,
            'previous_eta': delivery['eta_history'][-2][1] if len(delivery['eta_history']) > 1 else new_eta,
            'eta_change_pct': round(eta_change_pct, 1),
            'elapsed_minutes': round(elapsed_minutes, 1),
            'remaining_minutes': round(max(0, new_eta - elapsed_minutes), 1),
            'total_checkpoints': len(delivery['checkpoints'])
        }
    
    def _recalculate_eta(self, delivery, current_lat, current_lon, current_time):
        features = delivery['features'].copy()
        
        dropoff_lat = features.get('dropoff_lat', current_lat)
        dropoff_lon = features.get('dropoff_lon', current_lon)
        
        remaining_distance = geodesic((current_lat, current_lon), (dropoff_lat, dropoff_lon)).km
        
        features['distance_km'] = remaining_distance
        features['hour'] = current_time.hour
        features['day_of_week'] = current_time.weekday()
        features['is_weekend'] = 1 if current_time.weekday() >= 5 else 0
        features['hour_sin'] = np.sin(2 * np.pi * current_time.hour / 24)
        features['hour_cos'] = np.cos(2 * np.pi * current_time.hour / 24)
        features['day_sin'] = np.sin(2 * np.pi * current_time.weekday() / 7)
        features['day_cos'] = np.cos(2 * np.pi * current_time.weekday() / 7)
        features['is_rush_hour'] = 1 if (7 <= current_time.hour < 10 or 17 <= current_time.hour < 20) else 0
        
        if self.courier_profiler:
            courier_id = features.get('courier_id')
            if courier_id:
                pickup_advantage = self.courier_profiler.get_courier_region_advantage(
                    courier_id, current_lat, current_lon
                )
                dropoff_advantage = self.courier_profiler.get_courier_region_advantage(
                    courier_id, dropoff_lat, dropoff_lon
                )
                region_factor = (pickup_advantage + dropoff_advantage) / 2
            else:
                region_factor = 1.0
        else:
            region_factor = 1.0
        
        features_for_pred = {k: v for k, v in features.items() if k in self.eta_predictor.feature_cols}
        
        for col in self.eta_predictor.feature_cols:
            if col not in features_for_pred:
                features_for_pred[col] = features.get(col, 0)
        
        eta_result = self.eta_predictor.predict_single(features_for_pred, confidence_level=0.8)
        
        adjusted_eta = eta_result['predicted_minutes'] / region_factor
        
        return max(5.0, adjusted_eta)
    
    def should_refresh(self, delivery_id, current_time=None):
        if current_time is None:
            current_time = datetime.now()
        
        if delivery_id not in self.active_deliveries:
            return False
        
        delivery = self.active_deliveries[delivery_id]
        elapsed = (current_time - delivery['last_refresh']).total_seconds()
        
        return elapsed >= self.refresh_interval_seconds
    
    def get_delivery_status(self, delivery_id):
        if delivery_id not in self.active_deliveries:
            return None
        
        return self.active_deliveries[delivery_id]

class ETAAnomalyMonitor:
    def __init__(self, warning_threshold_pct=20, critical_threshold_pct=40):
        self.warning_threshold = warning_threshold_pct / 100
        self.critical_threshold = critical_threshold_pct / 100
        self.anomaly_log = []
        self.delivery_baselines = {}
    
    def set_baseline(self, delivery_id, initial_eta, upper_bound=None):
        self.delivery_baselines[delivery_id] = {
            'initial_eta': initial_eta,
            'upper_bound': upper_bound if upper_bound else initial_eta * 1.3,
            'max_allowed_eta': initial_eta * (1 + self.critical_threshold),
            'creation_time': datetime.now()
        }
    
    def check_anomaly(self, delivery_id, current_eta, actual_elapsed=None, progress_pct=None):
        if delivery_id not in self.delivery_baselines:
            return {'anomaly': False, 'level': 'normal'}
        
        baseline = self.delivery_baselines[delivery_id]
        
        eta_change_pct = (current_eta - baseline['initial_eta']) / baseline['initial_eta']
        
        upper_violation = current_eta > baseline['upper_bound']
        critical_violation = current_eta > baseline['max_allowed_eta']
        
        deviation_from_expected = 0
        if actual_elapsed is not None and progress_pct is not None and progress_pct > 0:
            expected_elapsed = baseline['initial_eta'] * (progress_pct / 100)
            deviation_from_expected = (actual_elapsed - expected_elapsed) / expected_elapsed
        
        anomalies = []
        level = 'normal'
        
        if critical_violation or eta_change_pct > self.critical_threshold:
            level = 'critical'
            anomalies.append(f'ETA超出临界阈值 (+{eta_change_pct*100:.1f}%)')
        elif upper_violation or eta_change_pct > self.warning_threshold:
            level = 'warning'
            anomalies.append(f'ETA超出预测上限 (+{eta_change_pct*100:.1f}%)')
        
        if deviation_from_expected > 0.3 and progress_pct < 80:
            level = max(level, 'warning')
            anomalies.append(f'配送进度偏差过大 (+{deviation_from_expected*100:.1f}%)')
        
        if deviation_from_expected > 0.5 and progress_pct < 60:
            level = 'critical'
            anomalies.append(f'配送进度严重滞后 (+{deviation_from_expected*100:.1f}%)')
        
        anomaly_event = {
            'delivery_id': delivery_id,
            'timestamp': datetime.now(),
            'level': level,
            'anomalies': anomalies,
            'eta_change_pct': round(eta_change_pct * 100, 1),
            'initial_eta': baseline['initial_eta'],
            'current_eta': current_eta,
            'progress_pct': progress_pct,
            'deviation_from_expected': round(deviation_from_expected * 100, 1)
        }
        
        if level != 'normal':
            self.anomaly_log.append(anomaly_event)
        
        return {
            'anomaly': level != 'normal',
            'level': level,
            'anomalies': anomalies,
            'eta_change_pct': round(eta_change_pct * 100, 1),
            'deviation_from_expected': round(deviation_from_expected * 100, 1),
            'event': anomaly_event if level != 'normal' else None
        }
    
    def get_active_alerts(self, delivery_id=None):
        if delivery_id:
            return [a for a in self.anomaly_log if a['delivery_id'] == delivery_id and a['level'] != 'normal']
        return [a for a in self.anomaly_log if a['level'] != 'normal']
    
    def get_recent_anomalies(self, minutes=30):
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [a for a in self.anomaly_log if a['timestamp'] >= cutoff]

if __name__ == '__main__':
    from data_generator import generate_historical_data
    
    print('生成测试数据...')
    df = generate_historical_data(2000)
    
    print('构建配送员画像...')
    profiler = CourierProfiler()
    profiles = profiler.build_profiles(df)
    
    sample_courier = list(profiles.keys())[0]
    profile = profiles[sample_courier]
    print(f'\n配送员 {sample_courier} 画像:')
    print(f'  总配送次数: {profile["overall_stats"]["total_deliveries"]}')
    print(f'  平均速度: {profile["overall_stats"]["avg_speed"]:.1f} km/h')
    print(f'  准时率: {profile["overall_stats"]["on_time_rate"]:.1%}')
    print(f'  偏好区域数: {len(profile["preferred_regions"])}')
    print(f'  规避区域数: {len(profile["avoid_regions"])}')
    
    if profile['preferred_regions']:
        pref = profile['preferred_regions'][0]
        print(f'  最佳区域: {pref["region_key"]} (速度+{pref["speed_advantage_pct"]}%)')
    
    print('\n异常监控测试...')
    monitor = ETAAnomalyMonitor()
    monitor.set_baseline('TEST001', 30.0, upper_bound=40.0)
    
    result = monitor.check_anomaly('TEST001', 38.0, progress_pct=50, actual_elapsed=20)
    print(f'测试结果: {result}')
