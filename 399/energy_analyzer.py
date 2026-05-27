import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


APPLIANCE_CN_NAMES = {
    'air_conditioner': '空调',
    'refrigerator': '冰箱',
    'washing_machine': '洗衣机',
    'lighting': '照明'
}


class EnergyAnalyzer:
    def __init__(self, 
                 sample_interval_min: int = 1):
        self.sample_interval_min = sample_interval_min
        self.sample_interval_hour = sample_interval_min / 60
    
    def calculate_energy_consumption(self, 
                                     power_series: np.ndarray) -> float:
        return np.sum(power_series) * self.sample_interval_hour / 1000
    
    def analyze_appliance_energy(self, 
                                 disaggregated_data: Dict[str, np.ndarray],
                                 timestamps: Optional[pd.DatetimeIndex] = None) -> Dict:
        results = {}
        
        for appliance, powers in disaggregated_data.items():
            total_kwh = self.calculate_energy_consumption(powers)
            mean_power = np.mean(powers)
            max_power = np.max(powers)
            std_power = np.std(powers)
            
            on_threshold = np.percentile(powers[powers > 0], 10) if np.any(powers > 0) else 10
            on_count = np.sum(powers > on_threshold)
            on_ratio = on_count / len(powers)
            
            results[appliance] = {
                'name_cn': APPLIANCE_CN_NAMES.get(appliance, appliance),
                'total_kwh': round(total_kwh, 3),
                'mean_power_w': round(mean_power, 2),
                'max_power_w': round(max_power, 2),
                'std_power_w': round(std_power, 2),
                'on_ratio': round(on_ratio, 3),
                'on_hours': round(on_count * self.sample_interval_hour, 2)
            }
        
        total_energy = sum(r['total_kwh'] for r in results.values())
        for appliance in results:
            results[appliance]['energy_ratio'] = round(results[appliance]['total_kwh'] / max(total_energy, 1e-6), 3)
        
        return results
    
    def get_energy_ratios(self, energy_results: Dict) -> Dict[str, float]:
        return {
            appliance: data['energy_ratio']
            for appliance, data in energy_results.items()
        }
    
    def analyze_daily_pattern(self,
                              power_series: np.ndarray,
                              timestamps: pd.DatetimeIndex) -> Dict:
        df = pd.DataFrame({'power': power_series}, index=timestamps)
        df['hour'] = df.index.hour
        
        hourly_mean = df.groupby('hour')['power'].mean()
        hourly_std = df.groupby('hour')['power'].std()
        
        peak_hours = hourly_mean.nlargest(3).index.tolist()
        off_peak_hours = hourly_mean.nsmallest(3).index.tolist()
        
        return {
            'hourly_mean': {h: round(float(hourly_mean[h]), 2) for h in range(24)},
            'hourly_std': {h: round(float(hourly_std[h]), 2) for h in range(24)},
            'peak_hours': peak_hours,
            'off_peak_hours': off_peak_hours,
            'peak_power': round(float(hourly_mean.max()), 2),
            'off_peak_power': round(float(hourly_mean.min()), 2)
        }
    
    def analyze_usage_habits(self,
                             disaggregated_data: Dict[str, np.ndarray],
                             timestamps: pd.DatetimeIndex) -> Dict:
        habits = {}
        
        for appliance, powers in disaggregated_data.items():
            on_threshold = np.percentile(powers[powers > 0], 10) if np.any(powers > 0) else 10
            is_on = powers > on_threshold
            
            df = pd.DataFrame({'is_on': is_on}, index=timestamps)
            df['hour'] = df.index.hour
            df['day_of_week'] = df.index.dayofweek
            
            hourly_usage = df.groupby('hour')['is_on'].mean()
            daily_usage = df.groupby('day_of_week')['is_on'].mean()
            
            peak_usage_hours = hourly_usage.nlargest(3).index.tolist()
            
            on_events = self._detect_on_events(is_on)
            
            habits[appliance] = {
                'name_cn': APPLIANCE_CN_NAMES.get(appliance, appliance),
                'hourly_usage': {h: round(float(hourly_usage[h]), 3) for h in range(24)},
                'daily_usage': {d: round(float(daily_usage[d]), 3) for d in range(7)},
                'peak_usage_hours': peak_usage_hours,
                'avg_event_duration_min': round(np.mean([e['duration'] for e in on_events]) * self.sample_interval_min, 1) if on_events else 0,
                'event_count': len(on_events),
                'usage_frequency_per_day': round(len(on_events) / (len(df) / (24 * 60 / self.sample_interval_min)), 2)
            }
        
        return habits
    
    def _detect_on_events(self, is_on: np.ndarray, min_duration: int = 3) -> List[Dict]:
        events = []
        in_event = False
        event_start = 0
        
        for i, on in enumerate(is_on):
            if on and not in_event:
                in_event = True
                event_start = i
            elif not on and in_event:
                duration = i - event_start
                if duration >= min_duration:
                    events.append({
                        'start': event_start,
                        'end': i,
                        'duration': duration
                    })
                in_event = False
        
        if in_event:
            duration = len(is_on) - event_start
            if duration >= min_duration:
                events.append({
                    'start': event_start,
                    'end': len(is_on),
                    'duration': duration
                })
        
        return events
    
    def analyze_weekly_pattern(self,
                               power_series: np.ndarray,
                               timestamps: pd.DatetimeIndex) -> Dict:
        df = pd.DataFrame({'power': power_series}, index=timestamps)
        df['day_of_week'] = df.index.dayofweek
        
        daily_mean = df.groupby('day_of_week')['power'].mean()
        
        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        return {
            'daily_mean': {day_names[d]: round(float(daily_mean[d]), 2) for d in range(7)},
            'weekday_avg': round(float(daily_mean[:5].mean()), 2),
            'weekend_avg': round(float(daily_mean[5:].mean()), 2),
            'weekend_weekday_ratio': round(float(daily_mean[5:].mean() / daily_mean[:5].mean()), 2)
        }
    
    def generate_comprehensive_report(self,
                                      disaggregated_data: Dict[str, np.ndarray],
                                      timestamps: pd.DatetimeIndex) -> Dict:
        energy_analysis = self.analyze_appliance_energy(disaggregated_data, timestamps)
        usage_habits = self.analyze_usage_habits(disaggregated_data, timestamps)
        
        total_power = np.sum(list(disaggregated_data.values()), axis=0)
        daily_pattern = self.analyze_daily_pattern(total_power, timestamps)
        weekly_pattern = self.analyze_weekly_pattern(total_power, timestamps)
        
        total_energy = sum(data['total_kwh'] for data in energy_analysis.values())
        
        return {
            'summary': {
                'total_energy_kwh': round(total_energy, 3),
                'analysis_period_days': round((timestamps[-1] - timestamps[0]).total_seconds() / 86400, 1),
                'sample_count': len(timestamps)
            },
            'energy_analysis': energy_analysis,
            'usage_habits': usage_habits,
            'daily_pattern': daily_pattern,
            'weekly_pattern': weekly_pattern
        }
    
    def get_energy_pie_data(self, energy_results: Dict) -> List[Dict]:
        pie_data = []
        for appliance, data in energy_results.items():
            pie_data.append({
                'name': data['name_cn'],
                'value': data['total_kwh'],
                'ratio': data['energy_ratio']
            })
        return sorted(pie_data, key=lambda x: -x['value'])


if __name__ == '__main__':
    from data_generator import generate_aggregated_data
    
    print("Generating test data...")
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    
    disaggregated_data = {
        'air_conditioner': df['air_conditioner_power'].values,
        'refrigerator': df['refrigerator_power'].values,
        'washing_machine': df['washing_machine_power'].values,
        'lighting': df['lighting_power'].values
    }
    
    analyzer = EnergyAnalyzer(sample_interval_min=5)
    
    print("\nAnalyzing energy consumption...")
    report = analyzer.generate_comprehensive_report(disaggregated_data, df.index)
    
    print(f"\nSummary:")
    print(f"  Total energy: {report['summary']['total_energy_kwh']:.2f} kWh")
    print(f"  Period: {report['summary']['analysis_period_days']} days")
    
    print(f"\nEnergy analysis:")
    for appliance, data in report['energy_analysis'].items():
        print(f"\n  {data['name_cn']}:")
        print(f"    Total energy: {data['total_kwh']:.3f} kWh ({data['energy_ratio']*100:.1f}%)")
        print(f"    Mean power: {data['mean_power_w']:.1f} W")
        print(f"    On ratio: {data['on_ratio']*100:.1f}%")
    
    print(f"\nDaily peak hours: {report['daily_pattern']['peak_hours']}")
