import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

class AnomalyPredictor:
    def __init__(self, forecast_periods: int = 288, interval_width: float = 0.95):
        self.forecast_periods = forecast_periods
        self.interval_width = interval_width
        self.models = {}
        self.forecasts = {}
        
    def _prepare_data(self, df: pd.DataFrame, metric: str) -> pd.DataFrame:
        prophet_df = df[['timestamp', metric]].copy()
        prophet_df.columns = ['ds', 'y']
        return prophet_df
    
    def train_model(self, df: pd.DataFrame, metric: str) -> Prophet:
        prophet_df = self._prepare_data(df, metric)
        
        model = Prophet(
            interval_width=self.interval_width,
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=True,
            changepoint_prior_scale=0.05
        )
        
        model.add_seasonality(name='hourly', period=1/24, fourier_order=5)
        
        model.fit(prophet_df)
        self.models[metric] = model
        
        return model
    
    def forecast(self, df: pd.DataFrame, metric: str, 
                 periods: int = None) -> pd.DataFrame:
        periods = periods or self.forecast_periods
        
        if metric not in self.models:
            self.train_model(df, metric)
        
        model = self.models[metric]
        prophet_df = self._prepare_data(df, metric)
        
        future = model.make_future_dataframe(
            periods=periods,
            freq='5min',
            include_history=True
        )
        
        forecast = model.predict(future)
        self.forecasts[metric] = forecast
        
        return forecast
    
    def detect_pending_anomalies(self, df: pd.DataFrame, metric: str,
                                   threshold_hours: int = 6,
                                   alert_score_threshold: float = 0.6) -> List[Dict]:
        forecast = self.forecast(df, metric)
        
        future_forecast = forecast[forecast['ds'] > df['timestamp'].max()].copy()
        
        alerts = []
        current_time = df['timestamp'].max()
        
        for i, row in future_forecast.iterrows():
            time_diff = (row['ds'] - current_time).total_seconds() / 3600
            
            if time_diff > threshold_hours:
                break
            
            trend_slope = self._calculate_trend_slope(forecast, row['ds'])
            volatility = self._calculate_volatility(forecast, row['ds'])
            
            anomaly_score = self._calculate_anomaly_risk(
                row, trend_slope, volatility, df[metric].mean()
            )
            
            if anomaly_score >= alert_score_threshold:
                alerts.append({
                    'metric': metric,
                    'predicted_time': row['ds'],
                    'hours_ahead': time_diff,
                    'predicted_value': row['yhat'],
                    'upper_bound': row['yhat_upper'],
                    'lower_bound': row['yhat_lower'],
                    'anomaly_score': anomaly_score,
                    'risk_level': self._get_risk_level(anomaly_score),
                    'trend_direction': 'up' if trend_slope > 0 else 'down',
                    'alert_type': self._determine_alert_type(row, trend_slope, df[metric].mean())
                })
        
        alerts.sort(key=lambda x: x['anomaly_score'], reverse=True)
        
        return alerts
    
    def _calculate_trend_slope(self, forecast: pd.DataFrame, 
                                point_time: datetime) -> float:
        window_start = point_time - timedelta(hours=2)
        window_end = point_time + timedelta(hours=2)
        
        window_data = forecast[
            (forecast['ds'] >= window_start) &
            (forecast['ds'] <= window_end)
        ]
        
        if len(window_data) < 2:
            return 0
        
        x = np.arange(len(window_data))
        y = window_data['yhat'].values
        slope = np.polyfit(x, y, 1)[0]
        
        return slope
    
    def _calculate_volatility(self, forecast: pd.DataFrame, 
                               point_time: datetime) -> float:
        window_start = point_time - timedelta(hours=6)
        
        window_data = forecast[forecast['ds'] <= point_time]
        window_data = window_data.tail(72)
        
        if len(window_data) < 10:
            return 0
        
        return window_data['yhat_upper'].sub(window_data['yhat_lower']).mean()
    
    def _calculate_anomaly_risk(self, forecast_row: pd.Series, 
                                 trend_slope: float, volatility: float,
                                 historical_mean: float) -> float:
        score = 0.0
        
        deviation_ratio = abs(forecast_row['yhat'] - historical_mean) / (historical_mean + 1e-10)
        score += min(0.4, deviation_ratio * 0.5)
        
        bound_width = forecast_row['yhat_upper'] - forecast_row['yhat_lower']
        bound_ratio = bound_width / (historical_mean + 1e-10)
        score += min(0.3, bound_ratio * 0.3)
        
        trend_strength = abs(trend_slope) / (historical_mean + 1e-10)
        score += min(0.3, trend_strength * 10)
        
        return min(1.0, score)
    
    def _get_risk_level(self, score: float) -> str:
        if score >= 0.8:
            return 'CRITICAL'
        elif score >= 0.6:
            return 'HIGH'
        elif score >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _determine_alert_type(self, forecast_row: pd.Series, 
                               trend_slope: float, historical_mean: float) -> str:
        predicted = forecast_row['yhat']
        
        if predicted > historical_mean * 1.3:
            if trend_slope > 0:
                return 'impending_spike'
            else:
                return 'sustained_high'
        elif predicted < historical_mean * 0.7:
            if trend_slope < 0:
                return 'impending_drop'
            else:
                return 'sustained_low'
        elif abs(trend_slope) > historical_mean * 0.01:
            return 'trend_change'
        else:
            return 'uncertainty'
    
    def predict_all_metrics(self, df: pd.DataFrame, metrics: List[str],
                            threshold_hours: int = 6) -> Dict[str, List[Dict]]:
        all_alerts = {}
        
        for metric in metrics:
            alerts = self.detect_pending_anomalies(df, metric, threshold_hours)
            all_alerts[metric] = alerts
        
        return all_alerts
    
    def get_combined_alerts(self, df: pd.DataFrame, metrics: List[str],
                            threshold_hours: int = 6,
                            min_score: float = 0.5,
                            alert_score_threshold: float = None) -> List[Dict]:
        all_alerts = []
        
        if alert_score_threshold is None:
            alert_score_threshold = min_score
        
        for metric in metrics:
            alerts = self.detect_pending_anomalies(
                df, metric, threshold_hours, alert_score_threshold
            )
            for alert in alerts:
                if alert['anomaly_score'] >= min_score:
                    all_alerts.append(alert)
        
        all_alerts.sort(key=lambda x: (x['hours_ahead'], -x['anomaly_score']))
        
        combined_alerts = self._correlate_alerts(all_alerts)
        
        return combined_alerts
    
    def _correlate_alerts(self, alerts: List[Dict]) -> List[Dict]:
        if not alerts:
            return []
        
        time_windows = {}
        
        for alert in alerts:
            time_key = int(alert['hours_ahead'] * 12)
            
            if time_key not in time_windows:
                time_windows[time_key] = {
                    'time_window_hours': alert['hours_ahead'],
                    'alerts': [],
                    'metrics_affected': set(),
                    'max_score': 0,
                    'combined_risk': 'LOW'
                }
            
            time_windows[time_key]['alerts'].append(alert)
            time_windows[time_key]['metrics_affected'].add(alert['metric'])
            time_windows[time_key]['max_score'] = max(
                time_windows[time_key]['max_score'],
                alert['anomaly_score']
            )
        
        combined = []
        for time_key, window_data in time_windows.items():
            window_data['metrics_affected'] = list(window_data['metrics_affected'])
            window_data['is_joint_alert'] = len(window_data['metrics_affected']) > 1
            
            if window_data['max_score'] >= 0.8:
                window_data['combined_risk'] = 'CRITICAL'
            elif window_data['max_score'] >= 0.6:
                window_data['combined_risk'] = 'HIGH'
            elif window_data['max_score'] >= 0.4:
                window_data['combined_risk'] = 'MEDIUM'
            
            combined.append(window_data)
        
        combined.sort(key=lambda x: x['time_window_hours'])
        
        return combined
    
    def get_forecast_dataframe(self, metric: str) -> Optional[pd.DataFrame]:
        return self.forecasts.get(metric)
    
    def generate_warning_message(self, alert: Dict) -> str:
        risk_colors = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }
        
        type_messages = {
            'impending_spike': '即将发生突增',
            'impending_drop': '即将发生突降',
            'sustained_high': '持续高位运行',
            'sustained_low': '持续低位运行',
            'trend_change': '趋势发生变化',
            'uncertainty': '不确定性增加'
        }
        
        color = risk_colors.get(alert['risk_level'], '⚪')
        type_msg = type_messages.get(alert['alert_type'], '异常风险')
        
        return (f"{color} 预警: {alert['metric'].upper()} {type_msg} "
                f"(预计 {alert['hours_ahead']:.1f} 小时后, "
                f"风险值: {alert['anomaly_score']:.0%})")
