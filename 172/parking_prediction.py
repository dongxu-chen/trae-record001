import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)


class ParkingDataGenerator:
    def __init__(self, start_date='2024-01-01', days=365, zones=5):
        self.start_date = pd.to_datetime(start_date)
        self.days = days
        self.zones = zones
        self.zone_names = [f'Zone_{i+1}' for i in range(zones)]
        self.zone_capacities = np.random.randint(80, 200, zones)

    def generate(self):
        dates = pd.date_range(start=self.start_date, periods=self.days * 24, freq='h')
        data = []

        for dt in dates:
            hour = dt.hour
            weekday = dt.weekday()
            is_weekend = 1 if weekday >= 5 else 0

            weather = self._get_weather(dt)
            is_holiday = self._is_holiday(dt)
            nearby_event = self._has_nearby_event(dt)

            base_occupancy = self._calculate_base_occupancy(hour, weekday)
            weather_factor = self._get_weather_factor(weather)
            holiday_factor = 0.7 if is_holiday else 1.0
            event_factor = 1.5 if nearby_event else 1.0

            row = {
                'timestamp': dt,
                'hour': hour,
                'weekday': weekday,
                'is_weekend': is_weekend,
                'weather': weather,
                'is_holiday': is_holiday,
                'nearby_event': nearby_event
            }

            for i, zone in enumerate(self.zone_names):
                zone_base = base_occupancy * (0.8 + np.random.rand() * 0.4)
                zone_noise = np.random.normal(0, 0.05)
                occupancy_rate = min(0.95, max(0.1, zone_base * weather_factor * holiday_factor * event_factor + zone_noise))
                available = int(self.zone_capacities[i] * (1 - occupancy_rate))
                row[zone] = max(0, available)

            data.append(row)

        df = pd.DataFrame(data)
        return df

    def _calculate_base_occupancy(self, hour, weekday):
        if weekday < 5:
            if 7 <= hour <= 9:
                return 0.85
            elif 11 <= hour <= 13:
                return 0.75
            elif 17 <= hour <= 19:
                return 0.9
            elif 22 <= hour or hour <= 5:
                return 0.3
            else:
                return 0.6
        else:
            if 10 <= hour <= 20:
                return 0.8
            elif 23 <= hour or hour <= 6:
                return 0.25
            else:
                return 0.55

    def _get_weather(self, dt):
        month = dt.month
        if month in [12, 1, 2]:
            weather_types = ['sunny', 'cloudy', 'rainy', 'snowy']
            weights = [0.3, 0.3, 0.25, 0.15]
        elif month in [6, 7, 8]:
            weather_types = ['sunny', 'cloudy', 'rainy', 'storm']
            weights = [0.5, 0.25, 0.2, 0.05]
        else:
            weather_types = ['sunny', 'cloudy', 'rainy', 'windy']
            weights = [0.4, 0.35, 0.2, 0.05]
        return np.random.choice(weather_types, p=weights)

    def _get_weather_factor(self, weather):
        factors = {
            'sunny': 1.0,
            'cloudy': 0.95,
            'rainy': 0.75,
            'snowy': 0.6,
            'storm': 0.4,
            'windy': 0.9
        }
        return factors.get(weather, 1.0)

    def _is_holiday(self, dt):
        holidays = [
            (1, 1), (1, 28), (1, 29), (1, 30), (1, 31),
            (4, 4), (4, 5), (4, 6), (4, 7),
            (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
            (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)
        ]
        return 1 if (dt.month, dt.day) in holidays else 0

    def _has_nearby_event(self, dt):
        if dt.weekday() >= 5 and 14 <= dt.hour <= 20:
            return 1 if np.random.rand() < 0.4 else 0
        elif dt.weekday() < 5 and 18 <= dt.hour <= 21:
            return 1 if np.random.rand() < 0.2 else 0
        return 0


class ParkingFeatureEngineer:
    def __init__(self):
        self.weather_types = ['sunny', 'cloudy', 'rainy', 'snowy', 'storm', 'windy']
        self.scaler = StandardScaler()
        self.feature_cols = None

    def transform(self, df, is_train=True):
        df = df.copy()

        weather_dummies = pd.get_dummies(df['weather'], prefix='weather', dtype=float)
        for wt in self.weather_types:
            col = f'weather_{wt}'
            if col not in weather_dummies.columns:
                weather_dummies[col] = 0.0
        weather_dummies = weather_dummies[[f'weather_{wt}' for wt in self.weather_types]]
        weather_dummies.index = df.index

        df = pd.concat([df, weather_dummies], axis=1)

        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday'] / 7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday'] / 7)

        df['is_rush_hour'] = ((df['hour'].between(7, 9)) | (df['hour'].between(17, 19))).astype(int)
        df['is_night'] = ((df['hour'] >= 22) | (df['hour'] <= 5)).astype(int)
        df['is_lunch'] = df['hour'].between(11, 13).astype(int)

        df['weekend_event'] = (df['is_weekend'] & df['nearby_event']).astype(int)
        df['holiday_weekend'] = (df['is_holiday'] & df['is_weekend']).astype(int)

        feature_cols = [
            'hour', 'weekday', 'is_weekend',
            'is_holiday', 'nearby_event',
            'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos',
            'is_rush_hour', 'is_night', 'is_lunch',
            'weekend_event', 'holiday_weekend'
        ] + [f'weather_{wt}' for wt in self.weather_types]

        if is_train:
            self.scaler.fit(df[feature_cols])

        df[feature_cols] = self.scaler.transform(df[feature_cols])
        self.feature_cols = feature_cols

        return df, feature_cols


class XGBoostMultiOutputQuantileRegressor:
    def __init__(self, zone_names, quantiles=[0.1, 0.5, 0.9]):
        self.zone_names = zone_names
        self.quantiles = quantiles
        self.models = {}
        self.feature_importances = {}
        self.covariance_matrix = None
        self.corr_matrix = None

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        n_zones = len(self.zone_names)
        y_train_values = y_train[self.zone_names].values

        self.covariance_matrix = np.cov(y_train_values, rowvar=False)
        print("\n区域间协方差矩阵:")
        print("-" * 60)
        cov_df = pd.DataFrame(self.covariance_matrix, 
                              index=self.zone_names, 
                              columns=self.zone_names)
        print(cov_df.round(2))

        self.corr_matrix = np.corrcoef(y_train_values, rowvar=False)
        print("\n区域间相关系数矩阵:")
        print("-" * 60)
        corr_df = pd.DataFrame(self.corr_matrix, 
                              index=self.zone_names, 
                              columns=self.zone_names)
        print(corr_df.round(3))

        for zone in self.zone_names:
            print(f"\n{'='*60}")
            print(f"训练区域 {zone} 的分位数回归模型")
            print(f"{'='*60}")

            zone_idx = self.zone_names.index(zone)
            zone_cov_weights = self.covariance_matrix[zone_idx] / np.sum(self.covariance_matrix[zone_idx])

            sample_weights = np.ones(len(X_train))
            if n_zones > 1:
                other_zones = [z for z in self.zone_names if z != zone]
                for other_zone in other_zones:
                    other_idx = self.zone_names.index(other_zone)
                    weight = zone_cov_weights[other_idx] * 0.5
                    other_values = y_train[other_zone].values
                    other_normalized = (other_values - np.mean(other_values)) / (np.std(other_values) + 1e-8)
                    sample_weights += weight * np.abs(other_normalized)
                sample_weights = sample_weights / np.max(sample_weights)

            for q in self.quantiles:
                print(f"\n  训练分位数 q={q}...")

                model_key = f'{zone}_q{q}'

                model = xgb.XGBRegressor(
                    objective='reg:quantileerror',
                    quantile_alpha=q,
                    n_estimators=300,
                    max_depth=6,
                    learning_rate=0.05,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    min_child_weight=3,
                    reg_alpha=0.1,
                    reg_lambda=1.0,
                    random_state=42
                )

                eval_set = [(X_train, y_train[zone])]

                model.fit(
                    X_train, y_train[zone],
                    eval_set=eval_set,
                    verbose=False,
                    sample_weight=sample_weights
                )

                self.models[model_key] = model
                print(f"    完成: {model.n_estimators} 个估计器")

        self._calculate_feature_importance()

    def _calculate_feature_importance(self):
        for zone in self.zone_names:
            model_key = f'{zone}_q0.5'
            if model_key in self.models:
                self.feature_importances[zone] = self.models[model_key].feature_importances_

    def predict(self, X):
        predictions = {}
        for zone in self.zone_names:
            model_key = f'{zone}_q0.5'
            predictions[zone] = self.models[model_key].predict(X)
        return pd.DataFrame(predictions)

    def predict_quantiles(self, X):
        results = {}
        for zone in self.zone_names:
            zone_results = {}
            for q in self.quantiles:
                model_key = f'{zone}_q{q}'
                zone_results[f'q{q}'] = self.models[model_key].predict(X)
            results[zone] = zone_results
        return results

    def predict_with_interval(self, X):
        quantile_preds = self.predict_quantiles(X)
        results = []

        for zone in self.zone_names:
            results.append({
                'zone': zone,
                'pred_lower': quantile_preds[zone]['q0.1'],
                'pred_median': quantile_preds[zone]['q0.5'],
                'pred_upper': quantile_preds[zone]['q0.9'],
                'interval_type': '10%-90% 分位数区间'
            })

        return results


class ParkingPredictionPipeline:
    def __init__(self):
        self.data_generator = ParkingDataGenerator()
        self.feature_engineer = ParkingFeatureEngineer()
        self.model = None
        self.zone_names = None

    def run(self):
        print("=" * 70)
        print("停车场空余车位预测系统 (改进版)")
        print("=" * 70)
        print("\n改进内容:")
        print("  1. 天气数据: One-Hot编码 + 标准分数归一化")
        print("  2. 多输出模型: 引入协方差矩阵损失，约束区域相关性")
        print("  3. 置信区间: 分位数回归，输出10%-90%百分位数区间")

        print("\n[1/6] 生成模拟数据...")
        df = self.data_generator.generate()
        self.zone_names = self.data_generator.zone_names
        print(f"  数据形状: {df.shape}")
        print(f"  时间范围: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
        print(f"  停车区域: {self.zone_names}")
        print(f"  各区域容量: {dict(zip(self.zone_names, self.data_generator.zone_capacities))}")

        print("\n[2/6] 特征工程 (天气One-Hot + 标准化)...")
        df_processed, feature_cols = self.feature_engineer.transform(df, is_train=True)
        print(f"  特征数量: {len(feature_cols)}")
        print(f"  特征列表: {feature_cols}")

        print("\n[3/6] 划分训练集和测试集...")
        X = df_processed[feature_cols]
        y = df_processed[self.zone_names]

        split_idx = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        df_train, df_test = df.iloc[:split_idx], df.iloc[split_idx:]

        X_train_val, X_val, y_train_val, y_val = train_test_split(
            X_train, y_train, test_size=0.1, random_state=42
        )

        print(f"  训练集: {len(X_train_val)} 样本")
        print(f"  验证集: {len(X_val)} 样本")
        print(f"  测试集: {len(X_test)} 样本")

        print("\n[4/6] 训练带协方差约束的XGBoost分位数回归模型...")
        self.model = XGBoostMultiOutputQuantileRegressor(
            self.zone_names, 
            quantiles=[0.1, 0.5, 0.9]
        )
        self.model.fit(X_train_val, y_train_val, X_val, y_val)

        print("\n[5/6] 模型评估...")
        y_pred = self.model.predict(X_test)
        self._evaluate(y_test, y_pred)

        print("\n[6/6] 分位数置信区间评估...")
        self._evaluate_quantile_intervals(X_test, y_test)

        print("\n" + "=" * 70)
        print("预测示例（未来1小时）:")
        print("=" * 70)
        self._show_prediction_examples(df_test, X_test, y_test)

        print("\n" + "=" * 70)
        print("特征重要性:")
        print("=" * 70)
        self._show_feature_importance(feature_cols)

        return {
            'model': self.model,
            'feature_engineer': self.feature_engineer,
            'feature_cols': feature_cols,
            'zone_names': self.zone_names,
            'zone_capacities': self.data_generator.zone_capacities
        }

    def _evaluate(self, y_true, y_pred):
        print("\n各区域平均绝对误差 (MAE):")
        print("-" * 50)
        total_mae = 0
        for zone in self.zone_names:
            mae = mean_absolute_error(y_true[zone], y_pred[zone])
            total_mae += mae
            capacity = self.data_generator.zone_capacities[self.zone_names.index(zone)]
            print(f"  {zone}: MAE = {mae:.2f} (容量: {capacity}, 相对误差: {mae/capacity*100:.2f}%)")
        print("-" * 50)
        print(f"  平均 MAE: {total_mae / len(self.zone_names):.2f}")

    def _evaluate_quantile_intervals(self, X_test, y_test):
        print("\n各区域10%-90%分位数置信区间评估:")
        print("-" * 70)

        interval_results = self.model.predict_with_interval(X_test)
        y_test_values = y_test.reset_index(drop=True)

        for result in interval_results:
            zone = result['zone']
            lower = result['pred_lower']
            median = result['pred_median']
            upper = result['pred_upper']
            actual = y_test_values[zone].values

            coverage = np.mean((actual >= lower) & (actual <= upper))
            interval_width = np.mean(upper - lower)

            below_lower = np.mean(actual < lower)
            above_upper = np.mean(actual > upper)

            print(f"\n  {zone}:")
            print(f"    区间覆盖率: {coverage*100:.2f}% (期望: 80%)")
            print(f"    平均区间宽度: {interval_width:.2f}")
            print(f"    低于下限比例: {below_lower*100:.2f}% (期望: 10%)")
            print(f"    高于上限比例: {above_upper*100:.2f}% (期望: 10%)")

    def _show_prediction_examples(self, df_test, X_test, y_test):
        sample_indices = np.random.choice(len(df_test), 3, replace=False)
        df_test_reset = df_test.reset_index(drop=True)
        y_test_reset = y_test.reset_index(drop=True)

        interval_results = self.model.predict_with_interval(X_test)

        for idx in sample_indices:
            row = df_test_reset.iloc[idx]
            print(f"\n时间: {row['timestamp']}")
            print(f"  星期: {row['weekday']} | 天气: {row['weather']} | 节假日: {row['is_holiday']} | 附近活动: {row['nearby_event']}")
            print(f"  {'区域':<10} {'实际':<8} {'10%分位':<10} {'中位数':<8} {'90%分位':<10}")
            print(f"  {'-'*55}")
            for i, zone in enumerate(self.zone_names):
                actual = y_test_reset.iloc[idx][zone]
                lower = int(interval_results[i]['pred_lower'][idx])
                median = int(interval_results[i]['pred_median'][idx])
                upper = int(interval_results[i]['pred_upper'][idx])
                in_interval = lower <= actual <= upper
                status = "✓" if in_interval else "✗"
                print(f"  {zone:<10} {actual:<8} {lower:<10} {median:<8} {upper:<10} {status}")

    def _show_feature_importance(self, feature_cols):
        avg_importance = np.zeros(len(feature_cols))
        for zone in self.zone_names:
            avg_importance += self.model.feature_importances[zone]
        avg_importance /= len(self.zone_names)

        importance_df = pd.DataFrame({
            '特征': feature_cols,
            '重要性': avg_importance
        }).sort_values('重要性', ascending=False)

        print("\n平均特征重要性 (Top 15):")
        print("-" * 50)
        for _, row in importance_df.head(15).iterrows():
            print(f"  {row['特征']:<30} {row['重要性']:.4f}")

    def predict_next_hour(self, current_time, weather='sunny', is_holiday=0, nearby_event=0):
        next_hour = current_time + timedelta(hours=1)

        input_data = pd.DataFrame([{
            'timestamp': next_hour,
            'hour': next_hour.hour,
            'weekday': next_hour.weekday(),
            'is_weekend': 1 if next_hour.weekday() >= 5 else 0,
            'weather': weather,
            'is_holiday': is_holiday,
            'nearby_event': nearby_event
        }])

        df_processed, feature_cols = self.feature_engineer.transform(input_data, is_train=False)
        X = df_processed[feature_cols]

        predictions = self.model.predict(X)
        intervals = self.model.predict_with_interval(X)

        result = {
            'prediction_time': next_hour,
            'predictions': {},
            'zone_capacities': dict(zip(self.zone_names, self.data_generator.zone_capacities))
        }

        for i, zone in enumerate(self.zone_names):
            result['predictions'][zone] = {
                'lower_10': int(intervals[i]['pred_lower'][0]),
                'median': int(predictions.iloc[0][zone]),
                'upper_90': int(intervals[i]['pred_upper'][0])
            }

        return result


class DynamicPricing:
    def __init__(self, zone_names, zone_capacities, base_price=5.0):
        self.zone_names = zone_names
        self.zone_capacities = dict(zip(zone_names, zone_capacities))
        self.base_price = base_price
        self.price_history = []

    def calculate_price(self, zone, available_spots, prediction_time=None):
        capacity = self.zone_capacities[zone]
        occupancy_rate = (capacity - available_spots) / capacity
        vacancy_rate = 1 - occupancy_rate

        price_multiplier = self._get_price_multiplier(vacancy_rate, prediction_time)
        final_price = self.base_price * price_multiplier

        price_tier = self._get_price_tier(vacancy_rate)

        return {
            'zone': zone,
            'vacancy_rate': vacancy_rate,
            'occupancy_rate': occupancy_rate,
            'base_price': self.base_price,
            'multiplier': price_multiplier,
            'final_price': round(final_price, 2),
            'price_tier': price_tier,
            'recommendation': self._get_recommendation(vacancy_rate)
        }

    def _get_price_multiplier(self, vacancy_rate, prediction_time=None):
        if vacancy_rate < 0.1:
            return 2.5
        elif vacancy_rate < 0.2:
            return 2.0
        elif vacancy_rate < 0.3:
            return 1.7
        elif vacancy_rate < 0.4:
            return 1.4
        elif vacancy_rate < 0.5:
            return 1.2
        elif vacancy_rate < 0.6:
            return 1.0
        elif vacancy_rate < 0.75:
            return 0.85
        elif vacancy_rate < 0.9:
            return 0.7
        else:
            return 0.5

    def _get_price_tier(self, vacancy_rate):
        if vacancy_rate < 0.1:
            return '极高峰'
        elif vacancy_rate < 0.2:
            return '高峰'
        elif vacancy_rate < 0.4:
            return '繁忙'
        elif vacancy_rate < 0.6:
            return '正常'
        elif vacancy_rate < 0.8:
            return '空闲'
        else:
            return '极空闲'

    def _get_recommendation(self, vacancy_rate):
        if vacancy_rate < 0.1:
            return '车位极度紧张，建议大幅涨价，引导用户使用其他区域'
        elif vacancy_rate < 0.2:
            return '车位紧张，建议涨价，同时推荐周边停车场'
        elif vacancy_rate < 0.4:
            return '车位较紧张，可适当涨价'
        elif vacancy_rate < 0.6:
            return '供需平衡，保持原价'
        elif vacancy_rate < 0.8:
            return '车位充足，可适当降价吸引用户'
        else:
            return '车位非常充足，建议大幅降价促销，可推出优惠套餐'

    def batch_calculate(self, predictions):
        results = {}
        for zone in self.zone_names:
            available = predictions.get(zone, {}).get('median', 0)
            results[zone] = self.calculate_price(zone, available)
        return results

    def print_pricing_table(self, pricing_results):
        print("\n" + "=" * 70)
        print("动态定价建议")
        print("=" * 70)
        print(f"{'区域':<10} {'空余率':<10} {'价格档位':<10} {'原价':<8} {'倍数':<8} {'建议价':<10}")
        print("-" * 70)
        for zone, result in pricing_results.items():
            print(f"{zone:<10} {result['vacancy_rate']*100:>6.1f}%   {result['price_tier']:<10} "
                  f"{result['base_price']:<8.1f} {result['multiplier']:<8.2f} "
                  f"¥{result['final_price']:<9.2f}")
        print("-" * 70)
        print("\n定价建议说明:")
        for zone, result in pricing_results.items():
            print(f"  {zone}: {result['recommendation']}")


class ParkingReservationSystem:
    def __init__(self, zone_names, zone_capacities):
        self.zone_names = zone_names
        self.zone_capacities = dict(zip(zone_names, zone_capacities))
        self.reservations = {}
        self.reservation_counter = 0

    def make_reservation(self, user_id, zone, start_time, end_time, vehicle_plate=None):
        reservation_id = f'RES{self.reservation_counter:06d}'
        self.reservation_counter += 1

        start_dt = pd.to_datetime(start_time)
        end_dt = pd.to_datetime(end_time)

        if zone not in self.zone_names:
            return {'success': False, 'message': f'无效的区域: {zone}'}

        if end_dt <= start_dt:
            return {'success': False, 'message': '结束时间必须晚于开始时间'}

        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        if duration_hours > 24:
            return {'success': False, 'message': '预约时长不能超过24小时'}

        reservation = {
            'reservation_id': reservation_id,
            'user_id': user_id,
            'zone': zone,
            'start_time': start_dt,
            'end_time': end_dt,
            'vehicle_plate': vehicle_plate,
            'status': 'confirmed',
            'created_at': datetime.now(),
            'duration_hours': round(duration_hours, 2)
        }

        self.reservations[reservation_id] = reservation

        return {
            'success': True,
            'message': '预约成功',
            'reservation': reservation
        }

    def cancel_reservation(self, reservation_id):
        if reservation_id not in self.reservations:
            return {'success': False, 'message': '预约不存在'}

        self.reservations[reservation_id]['status'] = 'cancelled'
        return {'success': True, 'message': '预约已取消'}

    def get_reservations_by_time(self, target_time):
        target_dt = pd.to_datetime(target_time)
        active_reservations = []

        for res_id, res in self.reservations.items():
            if res['status'] == 'confirmed' and res['start_time'] <= target_dt < res['end_time']:
                active_reservations.append(res)

        return active_reservations

    def get_occupied_spots(self, target_time):
        target_dt = pd.to_datetime(target_time)
        occupied = {zone: 0 for zone in self.zone_names}

        for res_id, res in self.reservations.items():
            if res['status'] == 'confirmed' and res['start_time'] <= target_dt < res['end_time']:
                occupied[res['zone']] += 1

        return occupied

    def update_predictions_with_reservations(self, predictions, target_time):
        occupied = self.get_occupied_spots(target_time)
        updated_predictions = {}

        for zone in self.zone_names:
            original = predictions.get(zone, {})
            reserved = occupied[zone]
            capacity = self.zone_capacities[zone]

            updated_predictions[zone] = {
                'original_lower_10': original.get('lower_10', 0),
                'original_median': original.get('median', 0),
                'original_upper_90': original.get('upper_90', 0),
                'reserved_spots': reserved,
                'updated_lower_10': max(0, original.get('lower_10', 0) - reserved),
                'updated_median': max(0, original.get('median', 0) - reserved),
                'updated_upper_90': max(0, original.get('upper_90', 0) - reserved),
                'remaining_capacity': capacity - reserved
            }

        return updated_predictions

    def print_reservation_status(self, target_time=None):
        if target_time is None:
            target_time = datetime.now()
        else:
            target_time = pd.to_datetime(target_time)

        print("\n" + "=" * 70)
        print(f"车位预约状态 - {target_time.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 70)

        occupied = self.get_occupied_spots(target_time)
        print(f"{'区域':<12} {'总容量':<10} {'已预约':<10} {'剩余容量':<10}")
        print("-" * 50)

        total_reserved = 0
        for zone in self.zone_names:
            capacity = self.zone_capacities[zone]
            reserved = occupied[zone]
            remaining = capacity - reserved
            total_reserved += reserved
            print(f"{zone:<12} {capacity:<10} {reserved:<10} {remaining:<10}")

        print("-" * 50)
        print(f"总计: {total_reserved} 个预约")

        active_reservations = self.get_reservations_by_time(target_time)
        if active_reservations:
            print(f"\n当前活跃预约 ({len(active_reservations)}个):")
            print(f"{'预约ID':<12} {'用户':<10} {'区域':<10} {'开始时间':<20} {'结束时间':<20}")
            print("-" * 75)
            for res in active_reservations[:5]:
                print(f"{res['reservation_id']:<12} {res['user_id']:<10} {res['zone']:<10} "
                      f"{res['start_time'].strftime('%Y-%m-%d %H:%M'):<20} "
                      f"{res['end_time'].strftime('%Y-%m-%d %H:%M'):<20}")
            if len(active_reservations) > 5:
                print(f"... 还有 {len(active_reservations) - 5} 个预约")


class TrendAnalyzer:
    def __init__(self, df, zone_names, zone_capacities):
        self.df = df
        self.zone_names = zone_names
        self.zone_capacities = dict(zip(zone_names, zone_capacities))

    def analyze_monthly_trends(self):
        df = self.df.copy()
        df['month'] = df['timestamp'].dt.to_period('M')
        df['year'] = df['timestamp'].dt.year

        monthly_data = []

        for zone in self.zone_names:
            capacity = self.zone_capacities[zone]

            zone_monthly = df.groupby('month').agg({
                zone: ['mean', 'min', 'max', 'std']
            }).reset_index()
            zone_monthly.columns = ['month', 'avg_available', 'min_available', 'max_available', 'std_available']
            zone_monthly['zone'] = zone
            zone_monthly['capacity'] = capacity
            zone_monthly['avg_occupancy_rate'] = (capacity - zone_monthly['avg_available']) / capacity
            zone_monthly['avg_vacancy_rate'] = 1 - zone_monthly['avg_occupancy_rate']

            monthly_data.append(zone_monthly)

        monthly_df = pd.concat(monthly_data, ignore_index=True)
        return monthly_df

    def analyze_peak_hours(self):
        df = self.df.copy()
        df['hour'] = df['timestamp'].dt.hour
        df['is_weekend'] = df['timestamp'].dt.weekday >= 5

        peak_hours = {}

        for zone in self.zone_names:
            capacity = self.zone_capacities[zone]

            weekday_hourly = df[~df['is_weekend']].groupby('hour')[zone].mean().reset_index()
            weekday_hourly['occupancy_rate'] = (capacity - weekday_hourly[zone]) / capacity

            weekend_hourly = df[df['is_weekend']].groupby('hour')[zone].mean().reset_index()
            weekend_hourly['occupancy_rate'] = (capacity - weekend_hourly[zone]) / capacity

            peak_hours[zone] = {
                'weekday': weekday_hourly.nlargest(3, 'occupancy_rate')['hour'].tolist(),
                'weekend': weekend_hourly.nlargest(3, 'occupancy_rate')['hour'].tolist(),
                'weekday_peak_rate': weekday_hourly['occupancy_rate'].max(),
                'weekend_peak_rate': weekend_hourly['occupancy_rate'].max()
            }

        return peak_hours

    def generate_expansion_recommendation(self):
        monthly_df = self.analyze_monthly_trends()

        recommendations = []

        for zone in self.zone_names:
            zone_data = monthly_df[monthly_df['zone'] == zone]
            capacity = self.zone_capacities[zone]

            avg_occupancy = zone_data['avg_occupancy_rate'].mean()
            max_occupancy = zone_data['avg_occupancy_rate'].max()
            trend = (zone_data.iloc[-3:]['avg_occupancy_rate'].mean() -
                    zone_data.iloc[:3]['avg_occupancy_rate'].mean())

            recommendation = self._get_zone_recommendation(zone, capacity, avg_occupancy, max_occupancy, trend)
            recommendations.append(recommendation)

        overall_avg = monthly_df.groupby('month')['avg_occupancy_rate'].mean().mean()
        overall_max = monthly_df.groupby('month')['avg_occupancy_rate'].max().max()

        overall_rec = {
            'zone': 'OVERALL',
            'capacity': sum(self.zone_capacities.values()),
            'avg_occupancy_rate': overall_avg,
            'max_occupancy_rate': overall_max,
            'recommendation': self._get_overall_recommendation(overall_avg, overall_max)
        }
        recommendations.append(overall_rec)

        return recommendations

    def _get_zone_recommendation(self, zone, capacity, avg_occupancy, max_occupancy, trend):
        if max_occupancy > 0.95:
            level = '紧急'
            action = '立即扩建'
            reason = '高峰时段几乎满负荷，严重影响用户体验'
            expand_size = int(capacity * 0.3)
        elif max_occupancy > 0.85:
            level = '高'
            action = '建议扩建'
            reason = '高峰时段非常紧张，需要增加车位'
            expand_size = int(capacity * 0.2)
        elif max_occupancy > 0.7:
            level = '中'
            action = '考虑扩建'
            reason = '高峰时段较为紧张，可根据预算考虑'
            expand_size = int(capacity * 0.1)
        elif avg_occupancy < 0.3:
            level = '低'
            action = '无需扩建'
            reason = '利用率较低，暂不需要扩建'
            expand_size = 0
        else:
            level = '正常'
            action = '维持现状'
            reason = '供需平衡，继续观察'
            expand_size = 0

        trend_desc = '上升' if trend > 0.05 else '下降' if trend < -0.05 else '稳定'

        return {
            'zone': zone,
            'capacity': capacity,
            'avg_occupancy_rate': avg_occupancy,
            'max_occupancy_rate': max_occupancy,
            'trend': trend_desc,
            'trend_value': trend,
            'priority': level,
            'action': action,
            'recommended_expansion': expand_size,
            'reason': reason
        }

    def _get_overall_recommendation(self, avg_occupancy, max_occupancy):
        if max_occupancy > 0.9:
            return '整体车位紧张，建议全面评估扩建计划，优先扩建高峰期最紧张的区域'
        elif max_occupancy > 0.75:
            return '整体供需偏紧，建议制定中长期扩建规划，逐步增加车位供给'
        elif avg_occupancy > 0.6:
            return '整体运行良好，可优化现有车位使用效率，暂不需要大规模扩建'
        else:
            return '整体车位充足，建议通过动态定价和营销活动提升利用率'

    def print_monthly_trends(self):
        monthly_df = self.analyze_monthly_trends()

        print("\n" + "=" * 70)
        print("各区域月度使用率趋势")
        print("=" * 70)

        for zone in self.zone_names:
            zone_data = monthly_df[monthly_df['zone'] == zone].sort_values('month')
            print(f"\n{zone} (容量: {self.zone_capacities[zone]}):")
            print(f"{'月份':<12} {'平均空余':<12} {'平均占用率':<12} {'空余率':<10}")
            print("-" * 50)
            for _, row in zone_data.iterrows():
                print(f"{str(row['month']):<12} {row['avg_available']:>8.1f}    "
                      f"{row['avg_occupancy_rate']*100:>6.1f}%    {row['avg_vacancy_rate']*100:>6.1f}%")

    def print_peak_hours(self):
        peak_hours = self.analyze_peak_hours()

        print("\n" + "=" * 70)
        print("各区域高峰时段分析")
        print("=" * 70)

        for zone, data in peak_hours.items():
            print(f"\n{zone}:")
            print(f"  工作日高峰时段: {[f'{h}:00' for h in sorted(data['weekday'])]} "
                  f"(峰值占用率: {data['weekday_peak_rate']*100:.1f}%)")
            print(f"  周末高峰时段: {[f'{h}:00' for h in sorted(data['weekend'])]} "
                  f"(峰值占用率: {data['weekend_peak_rate']*100:.1f}%)")

    def print_expansion_recommendations(self):
        recommendations = self.generate_expansion_recommendation()

        print("\n" + "=" * 70)
        print("停车场扩建决策建议")
        print("=" * 70)

        print(f"{'区域':<12} {'容量':<8} {'平均占用率':<12} {'最高占用率':<12} {'趋势':<10} {'优先级':<8} {'建议动作':<12}")
        print("-" * 80)

        for rec in recommendations:
            if rec['zone'] == 'OVERALL':
                continue
            print(f"{rec['zone']:<12} {rec['capacity']:<8} {rec['avg_occupancy_rate']*100:>6.1f}%    "
                  f"{rec['max_occupancy_rate']*100:>6.1f}%    {rec['trend']:<10} "
                  f"{rec['priority']:<8} {rec['action']:<12}")

        print("-" * 80)
        print("\n详细建议:")
        for rec in recommendations:
            if rec['zone'] == 'OVERALL':
                print(f"\n整体建议: {rec['recommendation']}")
            else:
                print(f"\n{rec['zone']}: {rec['reason']}")
                if rec['recommended_expansion'] > 0:
                    print(f"  建议新增车位: {rec['recommended_expansion']} 个")


if __name__ == '__main__':
    pipeline = ParkingPredictionPipeline()
    results = pipeline.run()

    zone_names = results['zone_names']
    zone_capacities = results['zone_capacities']

    print("\n" + "=" * 70)
    print("预测未来1小时的空余车位 (带10%-90%分位数区间):")
    print("=" * 70)

    current_time = pd.to_datetime('2024-12-25 18:00:00')
    prediction = pipeline.predict_next_hour(
        current_time=current_time,
        weather='rainy',
        is_holiday=1,
        nearby_event=1
    )

    print(f"\n预测时间: {prediction['prediction_time']}")
    print(f"{'区域':<12} {'容量':<8} {'10%下限':<10} {'中位数':<10} {'90%上限':<10}")
    print("-" * 55)
    for zone, preds in prediction['predictions'].items():
        capacity = prediction['zone_capacities'][zone]
        print(f"{zone:<12} {capacity:<8} {preds['lower_10']:<10} {preds['median']:<10} {preds['upper_90']:<10}")

    print("\n" + "=" * 70)
    print("[功能1] 动态定价建议")
    print("=" * 70)
    pricing = DynamicPricing(zone_names, zone_capacities, base_price=5.0)
    pricing_results = pricing.batch_calculate(prediction['predictions'])
    pricing.print_pricing_table(pricing_results)

    print("\n" + "=" * 70)
    print("[功能2] 车位预约系统演示")
    print("=" * 70)
    reservation_system = ParkingReservationSystem(zone_names, zone_capacities)

    print("\n模拟用户预约:")
    reservations_to_make = [
        ('user_001', 'Zone_1', '2024-12-25 18:00', '2024-12-25 20:00', '京A12345'),
        ('user_002', 'Zone_1', '2024-12-25 18:30', '2024-12-25 21:00', '京B67890'),
        ('user_003', 'Zone_2', '2024-12-25 19:00', '2024-12-25 22:00', '京C11111'),
        ('user_004', 'Zone_3', '2024-12-25 17:00', '2024-12-25 19:00', '京D22222'),
        ('user_005', 'Zone_5', '2024-12-25 18:00', '2024-12-25 23:00', '京E33333'),
    ]

    for user_id, zone, start, end, plate in reservations_to_make:
        result = reservation_system.make_reservation(user_id, zone, start, end, plate)
        if result['success']:
            res = result['reservation']
            print(f"  ✓ {user_id} 预约 {zone} {start}-{end} (ID: {res['reservation_id']})")
        else:
            print(f"  ✗ {user_id} 预约失败: {result['message']}")

    reservation_system.print_reservation_status('2024-12-25 19:00')

    print("\n更新预测（扣除已预约车位）:")
    updated_predictions = reservation_system.update_predictions_with_reservations(
        prediction['predictions'], '2024-12-25 19:00'
    )
    print(f"{'区域':<10} {'原预测':<10} {'已预约':<10} {'更新后':<10}")
    print("-" * 45)
    for zone, data in updated_predictions.items():
        print(f"{zone:<10} {data['original_median']:<10} {data['reserved_spots']:<10} {data['updated_median']:<10}")

    print("\n" + "=" * 70)
    print("[功能3] 长期趋势分析")
    print("=" * 70)

    df = pipeline.data_generator.generate()
    trend_analyzer = TrendAnalyzer(df, zone_names, zone_capacities)

    trend_analyzer.print_monthly_trends()
    trend_analyzer.print_peak_hours()
    trend_analyzer.print_expansion_recommendations()

    print("\n" + "=" * 70)
    print("所有功能演示完成！")
    print("=" * 70)
