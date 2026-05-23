import pandas as pd
import numpy as np
from prophet import Prophet
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error
from datetime import datetime, timedelta
import pickle
import os
import holidays
from config import STATIONS, MODEL_DIR, CONFIDENCE_INTERVAL


class HybridPredictionModel:
    def __init__(self):
        self.prophet_models = {}
        self.gbdt_models = {}
        self.stations = STATIONS
        self.cn_holidays = holidays.CN()
        self.holiday_df = self._prepare_holidays()

    def _prepare_holidays(self, years=None):
        if years is None:
            current_year = datetime.now().year
            years = [current_year - 1, current_year, current_year + 1]
        
        holiday_data = []
        for year in years:
            for date, name in holidays.CN(years=year).items():
                holiday_data.append({
                    'holiday': name,
                    'ds': pd.to_datetime(date),
                    'lower_window': -1,
                    'upper_window': 1
                })
        
        return pd.DataFrame(holiday_data)

    def train_prophet(self, df, station, flow_type='in_flow'):
        prophet_df = df[df['station'] == station][['timestamp', flow_type]].rename(
            columns={'timestamp': 'ds', flow_type: 'y'}
        )
        
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            interval_width=CONFIDENCE_INTERVAL,
            holidays=self.holiday_df,
            holidays_prior_scale=10.0
        )
        
        model.add_seasonality(name='hourly', period=1/24, fourier_order=8)
        model.add_seasonality(name='weekend', period=7, fourier_order=3, condition_name='is_weekend')
        
        prophet_df['is_weekend'] = prophet_df['ds'].dt.weekday >= 5
        
        model.fit(prophet_df)
        
        return model

    def train_gbdt(self, df, station, flow_type='in_flow'):
        station_df = df[df['station'] == station].copy()
        
        features = ['hour', 'weekday', 'is_holiday', 'weather_code', 'temperature',
                   'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos']
        
        X = station_df[features].values
        y = station_df[flow_type].values
        
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        model = lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42,
            verbose=-1
        )
        model.fit(X_train, y_train)
        
        return model

    def train_all(self, df):
        for station in self.stations:
            for flow_type in ['in_flow', 'out_flow']:
                key = f"{station}_{flow_type}"
                
                prophet_model = self.train_prophet(df, station, flow_type)
                self.prophet_models[key] = prophet_model
                
                gbdt_model = self.train_gbdt(df, station, flow_type)
                self.gbdt_models[key] = gbdt_model
                
                print(f"Trained models for {key}")

    def predict_hybrid(self, station, flow_type, future_df, features_df):
        key = f"{station}_{flow_type}"
        
        prophet_model = self.prophet_models[key]
        gbdt_model = self.gbdt_models[key]
        
        prophet_forecast = prophet_model.predict(future_df)
        prophet_pred = prophet_forecast['yhat'].values
        
        features = ['hour', 'weekday', 'is_holiday', 'weather_code', 'temperature',
                   'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos']
        X = features_df[features].values
        gbdt_pred = gbdt_model.predict(X)
        
        hybrid_pred = 0.6 * prophet_pred + 0.4 * gbdt_pred
        
        lower_bound = prophet_forecast['yhat_lower'].values
        upper_bound = prophet_forecast['yhat_upper'].values
        
        return {
            'prediction': hybrid_pred,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'prophet_pred': prophet_pred,
            'gbdt_pred': gbdt_pred
        }

    def predict_next_hours(self, df, start_time, hours=1):
        from data_processor import DataProcessor
        processor = DataProcessor()
        
        future_times = pd.date_range(start=start_time, periods=hours, freq='h')
        
        future_df_prophet = pd.DataFrame({'ds': future_times})
        future_df_prophet['is_weekend'] = future_df_prophet['ds'].dt.weekday >= 5
        
        future_data = []
        for dt in future_times:
            future_data.append({
                'timestamp': dt,
                'hour': dt.hour,
                'weekday': dt.weekday(),
                'is_holiday': dt in processor.cn_holidays,
                'weather_code': np.random.randint(0, 7),
                'temperature': 20 + np.random.normal(0, 3)
            })
        
        future_df = pd.DataFrame(future_data)
        future_df = processor.add_time_features(future_df)
        
        results = {}
        for station in self.stations:
            results[station] = {}
            for flow_type in ['in_flow', 'out_flow']:
                pred_result = self.predict_hybrid(station, flow_type, future_df_prophet, future_df)
                results[station][flow_type] = {
                    'timestamps': [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in future_times],
                    'prediction': pred_result['prediction'].tolist(),
                    'lower_bound': pred_result['lower_bound'].tolist(),
                    'upper_bound': pred_result['upper_bound'].tolist()
                }
        
        return results

    def apply_station_closure(self, predictions, closed_stations):
        return self.apply_event_adjustment(predictions, {
            'type': 'closure',
            'stations': closed_stations
        })

    def apply_event_adjustment(self, predictions, event_config):
        adjusted = predictions.copy()
        event_type = event_config.get('type', 'closure')
        stations = event_config.get('stations', [])
        in_factor = event_config.get('in_factor', 0.0)
        out_factor = event_config.get('out_factor', 0.0)
        affect_neighbors = event_config.get('affect_neighbors', False)
        neighbor_factor = event_config.get('neighbor_factor', 1.2)
        
        for idx, station in enumerate(self.stations):
            if station in stations:
                for flow_type in ['in_flow', 'out_flow']:
                    factor = in_factor if flow_type == 'in_flow' else out_factor
                    adjusted[station][flow_type]['prediction'] = [
                        max(0, int(v * factor)) for v in adjusted[station][flow_type]['prediction']
                    ]
                    adjusted[station][flow_type]['lower_bound'] = [
                        max(0, int(v * factor)) for v in adjusted[station][flow_type]['lower_bound']
                    ]
                    adjusted[station][flow_type]['upper_bound'] = [
                        max(0, int(v * factor)) for v in adjusted[station][flow_type]['upper_bound']
                    ]
                
                if affect_neighbors:
                    neighbor_indices = [idx - 1, idx + 1]
                    for n_idx in neighbor_indices:
                        if 0 <= n_idx < len(self.stations):
                            neighbor_station = self.stations[n_idx]
                            for flow_type in ['in_flow', 'out_flow']:
                                adjusted[neighbor_station][flow_type]['prediction'] = [
                                    int(v * neighbor_factor) for v in adjusted[neighbor_station][flow_type]['prediction']
                                ]
                                adjusted[neighbor_station][flow_type]['lower_bound'] = [
                                    int(v * neighbor_factor) for v in adjusted[neighbor_station][flow_type]['lower_bound']
                                ]
                                adjusted[neighbor_station][flow_type]['upper_bound'] = [
                                    int(v * neighbor_factor) for v in adjusted[neighbor_station][flow_type]['upper_bound']
                                ]
        
        return adjusted

    def save_models(self, path=MODEL_DIR):
        os.makedirs(path, exist_ok=True)
        
        with open(os.path.join(path, 'prophet_models.pkl'), 'wb') as f:
            pickle.dump(self.prophet_models, f)
        
        with open(os.path.join(path, 'gbdt_models.pkl'), 'wb') as f:
            pickle.dump(self.gbdt_models, f)

    def load_models(self, path=MODEL_DIR):
        with open(os.path.join(path, 'prophet_models.pkl'), 'rb') as f:
            self.prophet_models = pickle.load(f)
        
        with open(os.path.join(path, 'gbdt_models.pkl'), 'rb') as f:
            self.gbdt_models = pickle.load(f)
