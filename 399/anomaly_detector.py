import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import mahalanobis
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


ANOMALY_CATEGORIES = {
    'abnormal_power': '功率异常',
    'abnormal_duration': '运行时长异常',
    'abnormal_pattern': '使用模式异常',
    'abnormal_frequency': '使用频率异常',
    'unusual_time': '非典型时段使用',
    'energy_spike': '能耗突增'
}


class ApplianceAnomalyDetector:
    def __init__(self, 
                 appliance_name: str,
                 name_cn: str,
                 threshold_zscore: float = 2.5):
        self.appliance_name = appliance_name
        self.name_cn = name_cn
        self.threshold_zscore = threshold_zscore
        
        self.baseline_power_mean = None
        self.baseline_power_std = None
        self.baseline_duration_mean = None
        self.baseline_duration_std = None
        self.baseline_daily_pattern = None
        self.baseline_hourly_dist = None
        self.baseline_frequency_mean = None
        self.baseline_frequency_std = None
        
        self.is_trained = False
    
    def _detect_on_events(self, 
                           power_series: np.ndarray, 
                            threshold: float = None) -> List[Dict]:
        if threshold is None:
            threshold = np.percentile(power_series[power_series > 0], 25) if np.any(power_series > 0) else 10
        
        events = []
        in_event = False
        event_start = 0
        
        for i, p in enumerate(power_series):
            if p > threshold and not in_event:
                in_event = True
                event_start = i
            elif p <= threshold and in_event:
                duration = i - event_start
                if duration >= 3:
                    events.append({
                        'start_idx': event_start,
                        'end_idx': i,
                        'duration': duration,
                        'max_power': np.max(power_series[event_start:i]),
                        'avg_power': np.mean(power_series[event_start:i]),
                        'total_energy': np.sum(power_series[event_start:i])
                    })
                in_event = False
        
        if in_event:
            duration = len(power_series) - event_start
            if duration >= 3:
                events.append({
                    'start_idx': event_start,
                    'end_idx': len(power_series),
                    'duration': duration,
                    'max_power': np.max(power_series[event_start:]),
                    'avg_power': np.mean(power_series[event_start:]),
                    'total_energy': np.sum(power_series[event_start:])
                })
        
        return events
    
    def fit_baseline(self, 
                       power_series: np.ndarray,
                       timestamps: pd.DatetimeIndex) -> 'ApplianceAnomalyDetector':
        
        on_events = self._detect_on_events(power_series)
        
        if not on_events:
            self.is_trained = False
            return self
        
        powers = [e['avg_power'] for e in on_events]
        durations = [e['duration'] for e in on_events]
        
        self.baseline_power_mean = np.mean(powers)
        self.baseline_power_std = np.std(powers) + 1e-8
        self.baseline_duration_mean = np.mean(durations)
        self.baseline_duration_std = np.std(durations) + 1e-8
        
        self.baseline_frequency_mean = len(on_events) / (len(power_series) / (24 * 12))
        self.baseline_frequency_std = 2.0
        
        hourly_counts = np.zeros(24)
        for event in on_events:
            start_hour = timestamps[event['start_idx']].hour
            hourly_counts[start_hour] += 1
        
        self.baseline_hourly_dist = hourly_counts / (np.sum(hourly_counts) + 1e-8)
        
        self.is_trained = True
        return self
    
    def detect_anomalies(self,
                          power_series: np.ndarray,
                          timestamps: pd.DatetimeIndex,
                          sample_interval_min: int = 5) -> List[Dict]:
        if not self.is_trained:
            raise RuntimeError("Baseline not fitted. Call fit_baseline() first.")
        
        anomalies = []
        on_events = self._detect_on_events(power_series)
        
        for event in on_events:
            event_anomalies = []
            
            power_z = (event['avg_power'] - self.baseline_power_mean) / self.baseline_power_std
            if abs(power_z) > self.threshold_zscore:
                event_anomalies.append({
                    'type': 'abnormal_power',
                    'type_name': '功率异常',
                    'severity': min(abs(power_z) / self.threshold_zscore, 3.0),
                    'description': f"平均功率{event['avg_power']:.1f}W，偏离基线{self.baseline_power_mean:.1f}W",
                    'z_score': power_z
                })
            
            duration_min = event['duration'] * sample_interval_min
            baseline_duration_min = self.baseline_duration_mean * sample_interval_min
            duration_z = (event['duration'] - self.baseline_duration_mean) / self.baseline_duration_std
            if duration_z > self.threshold_zscore:
                event_anomalies.append({
                    'type': 'abnormal_duration',
                    'type_name': '运行时长异常',
                    'severity': min(duration_z / self.threshold_zscore, 3.0),
                    'description': f"运行时长{duration_min:.1f}分钟，基线{baseline_duration_min:.1f}分钟",
                    'z_score': duration_z
                })
            
            start_hour = timestamps[event['start_idx']].hour
            if self.baseline_hourly_dist[start_hour] < 0.02 and event['duration'] > 10:
                event_anomalies.append({
                    'type': 'unusual_time',
                    'type_name': '非典型时段使用',
                    'severity': 1.5,
                    'description': f"在{start_hour}点使用，该时段使用频率较低",
                    'hour': start_hour
                })
            
            if event_anomalies:
                max_severity = max(a['severity'] for a in event_anomalies)
                anomalies.append({
                    'appliance': self.appliance_name,
                    'appliance_name': self.name_cn,
                    'event_start': timestamps[event['start_idx']].strftime('%Y-%m-%d %H:%M:%S'),
                    'event_duration_min': round(event['duration'] * sample_interval_min, 1),
                    'avg_power': round(event['avg_power'], 1),
                    'anomalies': event_anomalies,
                    'max_severity': round(max_severity, 2),
                    'severity_level': 'high' if max_severity > 1.5 else 'medium' if max_severity > 1.0 else 'low'
                })
        
        n_events = len(on_events)
        expected_events = max(1, int(self.baseline_frequency_mean * (len(power_series) / (24 * 12))))
        
        if n_events > expected_events * 2:
            anomalies.append({
                'appliance': self.appliance_name,
                'appliance_name': self.name_cn,
                'event_start': timestamps[0].strftime('%Y-%m-%d %H:%M:%S'),
                'event_duration_min': 0,
                'avg_power': 0,
                'anomalies': [{
                    'type': 'abnormal_frequency',
                    'type_name': '使用频率异常',
                    'severity': 1.5,
                    'description': f"检测期间使用{n_events}次，预期约{expected_events}次"
                }],
                'max_severity': 1.5,
                'severity_level': 'medium'
            })
        
        return anomalies
    
    def get_summary(self, anomalies: List[Dict]) -> Dict:
        if not anomalies:
            return {
                'appliance': self.appliance_name,
                'appliance_name': self.name_cn,
                'anomaly_count': 0,
                'overall_severity': 'normal',
                'message': '未检测到异常'
            }
        
        high_count = sum(1 for a in anomalies if a['severity_level'] == 'high')
        medium_count = sum(1 for a in anomalies if a['severity_level'] == 'medium')
        
        if high_count > 0:
            overall_severity = 'high'
        elif medium_count > 0:
            overall_severity = 'medium'
        else:
            overall_severity = 'low'
        
        anomaly_types = {}
        for event in anomalies:
            for anom in event.get('anomalies', []):
                atype = anom['type']
                if atype not in anomaly_types:
                    anomaly_types[atype] = 0
                anomaly_types[atype] += 1
        
        return {
            'appliance': self.appliance_name,
            'appliance_name': self.name_cn,
            'anomaly_count': len(anomalies),
            'high_severity_count': high_count,
            'medium_severity_count': medium_count,
            'anomaly_types': anomaly_types,
            'overall_severity': overall_severity,
            'message': f'检测到 {len(anomalies)} 个异常事件'
        }


class MultiApplianceAnomalyDetector:
    def __init__(self, appliance_config: Dict[str, str]):
        self.appliance_config = appliance_config
        self.detectors: Dict[str, ApplianceAnomalyDetector] = {}
        
        for app, name_cn in appliance_config.items():
            self.detectors[app] = ApplianceAnomalyDetector(app, name_cn)
    
    def fit_all(self,
                 disaggregated_data: Dict[str, np.ndarray],
                 timestamps: pd.DatetimeIndex) -> 'MultiApplianceAnomalyDetector':
        for app, powers in disaggregated_data.items():
            if app in self.detectors:
                self.detectors[app].fit_baseline(powers, timestamps)
        return self
    
    def detect_all(self,
                    disaggregated_data: Dict[str, np.ndarray],
                    timestamps: pd.DatetimeIndex,
                    sample_interval_min: int = 5) -> Dict:
        all_anomalies = {}
        all_summaries = {}
        
        for app, powers in disaggregated_data.items():
            if app in self.detectors and self.detectors[app].is_trained:
                anomalies = self.detectors[app].detect_anomalies(
                    powers, timestamps, sample_interval_min)
                all_anomalies[app] = anomalies
                all_summaries[app] = self.detectors[app].get_summary(anomalies)
        
        overall_status = 'normal'
        for summary in all_summaries.values():
            if summary['overall_severity'] == 'high':
                overall_status = 'high'
                break
            elif summary['overall_severity'] == 'medium' and overall_status == 'normal':
                overall_status = 'medium'
        
        return {
            'overall_status': overall_status,
            'anomalies': all_anomalies,
            'summaries': all_summaries,
            'total_anomalies': sum(len(a) for a in all_anomalies.values())
        }


def detect_energy_spike(daily_energy: np.ndarray, 
                       threshold: float = 2.0) -> List[Dict]:
    mean_energy = np.mean(daily_energy)
    std_energy = np.std(daily_energy) + 1e-8
    
    spikes = []
    for i, energy in enumerate(daily_energy):
        z_score = (energy - mean_energy) / std_energy
        if z_score > threshold:
            spikes.append({
                'day_idx': i,
                'energy': round(energy, 2),
                'z_score': round(z_score, 2),
                'severity': 'high' if z_score > 3 else 'medium',
                'description': f'第{i+1}天能耗突增，超过均值{z_score:.1f}个标准差'
            })
    
    return spikes


if __name__ == '__main__':
    from data_generator import generate_aggregated_data
    
    print("Generating test data...")
    df = generate_aggregated_data(days=14, sample_interval_min=5)
    
    train_df = df.iloc[:int(len(df)*0.7)]
    test_df = df.iloc[int(len(df)*0.7):]
    
    appliance_config = {
        'air_conditioner': '空调',
        'refrigerator': '冰箱',
        'washing_machine': '洗衣机',
        'lighting': '照明'
    }
    
    baseline_data = {
        app: train_df[f'{app}_power'].values
        for app in appliance_config.keys()
    }
    
    test_data = {
        app: test_df[f'{app}_power'].values
        for app in appliance_config.keys()
    }
    
    print("\nTraining anomaly detectors...")
    detector = MultiApplianceAnomalyDetector(appliance_config)
    detector.fit_all(baseline_data, train_df.index)
    
    print("Detecting anomalies...")
    result = detector.detect_all(test_data, test_df.index, sample_interval_min=5)
    
    print(f"\nOverall status: {result['overall_status']}")
    print(f"Total anomalies: {result['total_anomalies']}")
    
    print("\nAnomaly summaries:")
    for app, summary in result['summaries'].items():
        print(f"\n  {summary['appliance_name']}:")
        print(f"    Anomalies: {summary['anomaly_count']}")
        print(f"    Status: {summary['overall_severity']}")
        if summary['anomaly_types']:
            print(f"    Types: {summary['anomaly_types']}")
    
    if result['overall_status'] != 'normal':
        print("\nDetailed anomalies:")
        for app, anomalies in result['anomalies'].items():
            if anomalies:
                print(f"\n  {appliance_config[app]}:")
                for anom in anomalies[:3]:
                    print(f"    - {anom['event_start']} - {anom['severity_level']}")
                    for detail in anom['anomalies']:
                        print(f"      * {detail['type_name']}: {detail['description']}")
