import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class ApplianceLoadForecaster:
    def __init__(self, 
                 appliance_name: str,
                 name_cn: str,
                 seasonal_periods: int = 288):
        self.appliance_name = appliance_name
        self.name_cn = name_cn
        self.seasonal_periods = seasonal_periods
        
        self.daily_pattern = None
        self.hourly_means = None
        self.weekly_pattern = None
        self.trend = None
        self.level = None
        self.is_fitted = False
    
    def fit(self, 
            power_series: np.ndarray,
            timestamps: pd.DatetimeIndex) -> 'ApplianceLoadForecaster':
        
        df = pd.DataFrame({
            'power': power_series,
            'hour': timestamps.hour,
            'minute': timestamps.minute,
            'dayofweek': timestamps.dayofweek,
            'day': timestamps.date
        })
        
        df['time_of_day'] = df['hour'] + df['minute'] / 60
        
        hourly_stats = df.groupby('hour')['power'].agg(['mean', 'std', 'max', 'min'])
        self.hourly_means = hourly_stats['mean'].values
        self.hourly_stds = hourly_stats['std'].values
        
        n_samples_per_day = 24 * 12
        n_days = len(power_series) // n_samples_per_day
        
        if n_days >= 1:
            daily_data = power_series[:n_days * n_samples_per_day].reshape(n_days, n_samples_per_day)
            self.daily_pattern = np.mean(daily_data, axis=0)
        else:
            self.daily_pattern = np.tile(self.hourly_means.repeat(12)[:n_samples_per_day], 1)
        
        self.level = np.mean(power_series[power_series > np.percentile(power_series, 75)]) if np.any(power_series > 0) else 0
        
        self.is_fitted = True
        return self
    
    def predict(self, 
                steps_ahead: int = 288,
                start_datetime: Optional[datetime] = None,
                confidence_level: float = 0.95) -> Dict:
        
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        if start_datetime is None:
            start_datetime = datetime.now()
        
        n_samples_per_day = 288
        
        predictions = np.zeros(steps_ahead)
        lower_bounds = np.zeros(steps_ahead)
        upper_bounds = np.zeros(steps_ahead)
        
        timestamps = []
        
        for i in range(steps_ahead):
            current_dt = start_datetime + timedelta(minutes=i * 5)
            timestamps.append(current_dt)
            
            idx = i % n_samples_per_day
            hour = current_dt.hour
            
            base_power = self.daily_pattern[idx] if idx < len(self.daily_pattern) else self.hourly_means[hour]
            
            noise_std = self.hourly_stds[hour] if hour < len(self.hourly_stds) else np.mean(self.hourly_stds)
            noise_std = max(noise_std, self.level * 0.1)
            
            z_score = 1.96 if confidence_level == 0.95 else 1.645
            
            predictions[i] = max(0, base_power)
            lower_bounds[i] = max(0, base_power - z_score * noise_std)
            upper_bounds[i] = max(0, base_power + z_score * noise_std)
        
        total_energy_predicted = np.sum(predictions) * 5 / 60 / 1000
        
        return {
            'appliance': self.appliance_name,
            'appliance_name': self.name_cn,
            'timestamps': [dt.strftime('%Y-%m-%d %H:%M:%S') for dt in timestamps],
            'forecast': predictions.round(2).tolist(),
            'lower_bound': lower_bounds.round(2).tolist(),
            'upper_bound': upper_bounds.round(2).tolist(),
            'total_energy_kwh': round(total_energy_predicted, 3),
            'peak_power_w': round(np.max(predictions), 1),
            'average_power_w': round(np.mean(predictions), 1),
            'confidence_level': confidence_level
        }


class MultiApplianceForecaster:
    def __init__(self, appliance_config: Dict[str, str]):
        self.appliance_config = appliance_config
        self.forecasters: Dict[str, ApplianceLoadForecaster] = {}
        
        for app, name_cn in appliance_config.items():
            self.forecasters[app] = ApplianceLoadForecaster(app, name_cn)
    
    def fit_all(self,
                 disaggregated_data: Dict[str, np.ndarray],
                 timestamps: pd.DatetimeIndex) -> 'MultiApplianceForecaster':
        for app, powers in disaggregated_data.items():
            if app in self.forecasters:
                self.forecasters[app].fit(powers, timestamps)
        return self
    
    def predict_all(self,
                     steps_ahead: int = 288,
                     start_datetime: Optional[datetime] = None,
                     confidence_level: float = 0.95) -> Dict:
        
        individual_forecasts = {}
        total_forecast = np.zeros(steps_ahead)
        total_lower = np.zeros(steps_ahead)
        total_upper = np.zeros(steps_ahead)
        
        for app, forecaster in self.forecasters.items():
            if forecaster.is_fitted:
                fc = forecaster.predict(steps_ahead, start_datetime, confidence_level)
                individual_forecasts[app] = fc
                
                total_forecast += np.array(fc['forecast'])
                total_lower += np.array(fc['lower_bound'])
                total_upper += np.array(fc['upper_bound'])
        
        total_energy = np.sum(total_forecast) * 5 / 60 / 1000
        
        peak_hours = self._find_peak_hours(total_forecast)
        
        appliance_breakdown = {
            app: {
                'name_cn': fc['appliance_name'],
                'energy_kwh': fc['total_energy_kwh'],
                'percentage': round(fc['total_energy_kwh'] / total_energy * 100, 1) if total_energy > 0 else 0
            }
            for app, fc in individual_forecasts.items()
        }
        
        return {
            'overall': {
                'total_energy_kwh': round(total_energy, 3),
                'peak_power_w': round(np.max(total_forecast), 1),
                'average_power_w': round(np.mean(total_forecast), 1),
                'peak_hours': peak_hours,
                'forecast_timestamps': individual_forecasts[list(individual_forecasts.keys())[0]]['timestamps'] if individual_forecasts else [],
                'total_forecast': total_forecast.round(2).tolist(),
                'total_lower_bound': total_lower.round(2).tolist(),
                'total_upper_bound': total_upper.round(2).tolist(),
                'confidence_level': confidence_level
            },
            'appliances': appliance_breakdown,
            'detailed_forecasts': individual_forecasts
        }
    
    def _find_peak_hours(self, forecast: np.ndarray, top_n: int = 3) -> List[Dict]:
        n_samples_per_hour = 12
        hourly_means = []
        
        for hour in range(24):
            start = hour * n_samples_per_hour
            end = start + n_samples_per_hour
            if end <= len(forecast):
                hourly_means.append({
                    'hour': hour,
                    'avg_power': np.mean(forecast[start:end])
                })
        
        hourly_means.sort(key=lambda x: x['avg_power'], reverse=True)
        
        return [
            {
                'hour': h['hour'],
                'time_range': f"{h['hour']:02d}:00-{h['hour']+1:02d}:00",
                'avg_power_w': round(h['avg_power'], 1)
            }
            for h in hourly_means[:top_n]
        ]


def predict_daily_energy(disaggregated_data: Dict[str, np.ndarray],
                          days_ahead: int = 7,
                          sample_interval_min: int = 5) -> Dict:
    
    n_samples_per_day = 24 * 60 // sample_interval_min
    
    daily_energy = {}
    for app, powers in disaggregated_data.items():
        n_days = len(powers) // n_samples_per_day
        if n_days > 0:
            daily = []
            for d in range(n_days):
                start = d * n_samples_per_day
                end = start + n_samples_per_day
                energy = np.sum(powers[start:end]) * sample_interval_min / 60 / 1000
                daily.append(energy)
            daily_energy[app] = daily
    
    predictions = {}
    for app, daily in daily_energy.items():
        if len(daily) >= 3:
            mean_energy = np.mean(daily[-7:])
            std_energy = np.std(daily[-7:])
            
            pred = []
            for d in range(days_ahead):
                day_of_week_factor = 1.0
                if d >= 5:
                    day_of_week_factor = 1.1
                
                pred.append(round(mean_energy * day_of_week_factor, 3))
            
            predictions[app] = {
                'daily_predictions': pred,
                'total_predicted': round(sum(pred), 2),
                'historical_avg': round(mean_energy, 3),
                'historical_std': round(std_energy, 3),
                'trend': 'increasing' if len(daily) >= 7 and np.mean(daily[-3:]) > np.mean(daily[:3]) else 'stable'
            }
    
    return predictions


if __name__ == '__main__':
    from data_generator import generate_aggregated_data
    
    print("Generating test data...")
    df = generate_aggregated_data(days=14, sample_interval_min=5)
    
    appliance_config = {
        'air_conditioner': '空调',
        'refrigerator': '冰箱',
        'washing_machine': '洗衣机',
        'lighting': '照明'
    }
    
    disaggregated_data = {
        app: df[f'{app}_power'].values
        for app in appliance_config.keys()
    }
    
    print("\nTraining forecasters...")
    forecaster = MultiApplianceForecaster(appliance_config)
    forecaster.fit_all(disaggregated_data, df.index)
    
    print("Forecasting next 24 hours...")
    forecast = forecaster.predict_all(steps_ahead=288)
    
    print(f"\nOverall Forecast:")
    print(f"  Total Energy: {forecast['overall']['total_energy_kwh']} kWh")
    print(f"  Peak Power: {forecast['overall']['peak_power_w']} W")
    print(f"  Average Power: {forecast['overall']['average_power_w']} W")
    
    print(f"\n  Peak Hours:")
    for peak in forecast['overall']['peak_hours']:
        print(f"    {peak['time_range']}: {peak['avg_power_w']} W")
    
    print(f"\nAppliance Breakdown:")
    for app, info in forecast['appliances'].items():
        print(f"  {info['name_cn']}: {info['energy_kwh']} kWh ({info['percentage']}%)")
    
    print(f"\nDaily Energy Prediction (7 days):")
    daily_pred = predict_daily_energy(disaggregated_data, days_ahead=7)
    for app, pred in daily_pred.items():
        print(f"\n  {appliance_config[app]}:")
        print(f"    Historical Avg: {pred['historical_avg']} kWh/day")
        print(f"    Next 7 days total: {pred['total_predicted']} kWh")
        print(f"    Trend: {pred['trend']}")
