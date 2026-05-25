import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scipy import signal
from scipy.stats import f_oneway


class ResourceAnalyzer:
    def __init__(self, config: Dict):
        self.config = config
        self.rules = config.get('optimization_rules', {})
        self.sampling_interval = self.rules.get('sampling', {}).get('interval_minutes', 1)

    def calculate_metric_statistics(self, metrics_df: pd.DataFrame, 
                                     metric_name: str,
                                     granularity: str = 'minute') -> Dict:
        if metrics_df.empty:
            return {
                'avg': 0,
                'max': 0,
                'min': 0,
                'p50': 0,
                'p75': 0,
                'p90': 0,
                'p95': 0,
                'p99': 0,
                'p999': 0,
                'std': 0,
                'cv': 0,
                'data_points': 0,
                'peak_hour_stats': {},
                'daily_stats': {}
            }

        metric_data = metrics_df[metrics_df['metric_name'] == metric_name].copy()
        if metric_data.empty:
            return {
                'avg': 0,
                'max': 0,
                'min': 0,
                'p50': 0,
                'p75': 0,
                'p90': 0,
                'p95': 0,
                'p99': 0,
                'p999': 0,
                'std': 0,
                'cv': 0,
                'data_points': 0,
                'peak_hour_stats': {},
                'daily_stats': {}
            }

        metric_data['timestamp'] = pd.to_datetime(metric_data['timestamp'])
        
        if granularity == 'minute':
            resampled = metric_data.set_index('timestamp').resample('1min')['value'].mean().dropna()
            values = resampled.values
        else:
            values = metric_data['value'].values

        mean_val = float(np.mean(values))
        std_val = float(np.std(values))
        
        peak_hour_stats = self._calculate_peak_hour_stats(metric_data)
        daily_stats = self._calculate_daily_stats(metric_data)
        
        return {
            'avg': mean_val,
            'max': float(np.max(values)),
            'min': float(np.min(values)),
            'p50': float(np.percentile(values, 50)),
            'p75': float(np.percentile(values, 75)),
            'p90': float(np.percentile(values, 90)),
            'p95': float(np.percentile(values, 95)),
            'p99': float(np.percentile(values, 99)),
            'p999': float(np.percentile(values, 99.9)),
            'std': std_val,
            'cv': std_val / mean_val if mean_val > 0 else 0,
            'data_points': len(values),
            'peak_hour_stats': peak_hour_stats,
            'daily_stats': daily_stats
        }

    def _calculate_peak_hour_stats(self, metric_data: pd.DataFrame) -> Dict:
        metric_data['hour'] = metric_data['timestamp'].dt.hour
        hour_stats = metric_data.groupby('hour')['value'].agg(['mean', 'max', 'count'])
        
        peak_hour = hour_stats['mean'].idxmax()
        off_peak_hour = hour_stats['mean'].idxmin()
        
        return {
            'peak_hour': int(peak_hour),
            'peak_hour_value': float(hour_stats.loc[peak_hour, 'mean']),
            'off_peak_hour': int(off_peak_hour),
            'off_peak_hour_value': float(hour_stats.loc[off_peak_hour, 'mean']),
            'peak_to_avg_ratio': float(hour_stats.loc[peak_hour, 'mean'] / (hour_stats['mean'].mean() + 0.001))
        }

    def _calculate_daily_stats(self, metric_data: pd.DataFrame) -> Dict:
        metric_data['date'] = metric_data['timestamp'].dt.date
        daily_stats = metric_data.groupby('date')['value'].agg(['mean', 'max', 'min'])
        
        return {
            'daily_avg_mean': float(daily_stats['mean'].mean()),
            'daily_max_mean': float(daily_stats['max'].mean()),
            'daily_variance': float(daily_stats['mean'].var())
        }

    def analyze_instance_utilization(self, instance_id: str, 
                                      metrics_df: pd.DataFrame) -> Dict:
        instance_metrics = metrics_df[metrics_df['instance_id'] == instance_id]
        
        cpu_stats = self.calculate_metric_statistics(instance_metrics, 'cpu_utilization')
        mem_stats = self.calculate_metric_statistics(instance_metrics, 'memory_utilization')
        net_stats = self.calculate_metric_statistics(instance_metrics, 'network_traffic')

        return {
            'instance_id': instance_id,
            'cpu': cpu_stats,
            'memory': mem_stats,
            'network': net_stats,
            'analysis_time': datetime.now().isoformat()
        }

    def analyze_all_instances(self, instances_df: pd.DataFrame, 
                               metrics_df: pd.DataFrame) -> pd.DataFrame:
        if instances_df.empty:
            return pd.DataFrame()

        analysis_results = []
        for _, instance in instances_df.iterrows():
            instance_id = instance['instance_id']
            utilization = self.analyze_instance_utilization(instance_id, metrics_df)
            
            result = {
                'instance_id': instance_id,
                'instance_name': instance.get('instance_name', ''),
                'instance_type': instance.get('instance_type', ''),
                'status': instance.get('status', ''),
                'region': instance.get('region', ''),
                'provider': instance.get('provider', ''),
                'cpu_avg': utilization['cpu']['avg'],
                'cpu_max': utilization['cpu']['max'],
                'cpu_p95': utilization['cpu']['p95'],
                'memory_avg': utilization['memory']['avg'],
                'memory_max': utilization['memory']['max'],
                'memory_p95': utilization['memory']['p95'],
                'network_avg': utilization['network']['avg'],
                'network_max': utilization['network']['max']
            }
            analysis_results.append(result)

        return pd.DataFrame(analysis_results)

    def generate_utilization_trend(self, metrics_df: pd.DataFrame,
                                    metric_name: str,
                                    instance_id: str = None,
                                    freq: str = 'H') -> pd.DataFrame:
        df = metrics_df[metrics_df['metric_name'] == metric_name].copy()
        
        if instance_id:
            df = df[df['instance_id'] == instance_id]

        if df.empty:
            return pd.DataFrame()

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        trend_df = df.resample(freq)['value'].agg(['mean', 'max', 'min']).reset_index()
        trend_df.columns = ['timestamp', f'{metric_name}_avg', f'{metric_name}_max', f'{metric_name}_min']
        
        return trend_df

    def detect_periodicity(self, metrics_df: pd.DataFrame, 
                           metric_name: str,
                           instance_id: str = None) -> Dict:
        df = metrics_df[metrics_df['metric_name'] == metric_name].copy()
        if instance_id:
            df = df[df['instance_id'] == instance_id]

        if len(df) < 288:
            return {
                'is_periodic': False,
                'period': None,
                'confidence': 0,
                'peak_hours': [],
                'trough_hours': [],
                'amplitude': 0
            }

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp').sort_index()
        df_resampled = df['value'].resample('1H').mean().dropna()
        
        values = df_resampled.values
        
        try:
            f, Pxx = signal.welch(values, fs=1, nperseg=min(len(values), 24*7))
            
            peak_indices = signal.find_peaks(Pxx, height=np.mean(Pxx))[0]
            
            if len(peak_indices) > 0:
                dominant_idx = peak_indices[np.argmax(Pxx[peak_indices])]
                dominant_freq = f[dominant_idx]
                
                if dominant_freq > 0:
                    period_hours = 1 / dominant_freq
                    
                    if abs(period_hours - 24) < 4 or abs(period_hours - 12) < 2:
                        confidence = min(1.0, Pxx[dominant_idx] / np.mean(Pxx) / 5)
                        
                        hourly_avg = df_resampled.groupby(df_resampled.index.hour).mean()
                        peak_hours = hourly_avg.nlargest(3).index.tolist()
                        trough_hours = hourly_avg.nsmallest(3).index.tolist()
                        
                        amplitude = (hourly_avg.max() - hourly_avg.min()) / (hourly_avg.mean() + 0.001)
                        
                        return {
                            'is_periodic': True,
                            'period': 'daily' if abs(period_hours - 24) < 4 else 'semi-daily',
                            'period_hours': float(period_hours),
                            'confidence': float(confidence),
                            'peak_hours': [int(h) for h in peak_hours],
                            'trough_hours': [int(h) for h in trough_hours],
                            'amplitude': float(amplitude),
                            'peak_to_trough_ratio': float(hourly_avg.max() / (hourly_avg.min() + 0.001))
                        }
        except Exception as e:
            print(f"Periodicity detection error: {e}")
        
        return {
            'is_periodic': False,
            'period': None,
            'confidence': 0,
            'peak_hours': [],
            'trough_hours': [],
            'amplitude': 0
        }

    def calculate_buffer_requirement(self, metrics_df: pd.DataFrame,
                                      metric_name: str,
                                      instance_id: str = None) -> Dict:
        periodicity = self.detect_periodicity(metrics_df, metric_name, instance_id)
        stats = self.calculate_metric_statistics(metrics_df, metric_name)
        
        if periodicity['is_periodic'] and periodicity['confidence'] > 0.3:
            peak_value = stats['p99']
            avg_value = stats['avg']
            buffer_ratio = peak_value / (avg_value + 0.001)
            
            safety_margin = 1.2 if periodicity['amplitude'] > 0.5 else 1.1
            
            return {
                'needs_buffer': True,
                'buffer_reason': f"Periodic {periodicity['period']} pattern detected",
                'peak_hours': periodicity['peak_hours'],
                'recommended_buffer_pct': int(max(30, min(100, (buffer_ratio - 1) * 100 * safety_margin))),
                'peak_to_avg_ratio': float(peak_value / (avg_value + 0.001)),
                'confidence': periodicity['confidence'],
                'baseline_capacity': float(avg_value),
                'peak_capacity_required': float(peak_value * safety_margin)
            }
        else:
            p99_value = stats['p99']
            avg_value = stats['avg']
            
            if p99_value > avg_value * 2:
                return {
                    'needs_buffer': True,
                    'buffer_reason': "High P99/P99.9 peaks detected",
                    'peak_hours': [],
                    'recommended_buffer_pct': int(min(100, (p99_value / (avg_value + 0.001) - 1) * 100)),
                    'peak_to_avg_ratio': float(p99_value / (avg_value + 0.001)),
                    'confidence': 0.5,
                    'baseline_capacity': float(avg_value),
                    'peak_capacity_required': float(p99_value)
                }
        
        return {
            'needs_buffer': False,
            'buffer_reason': "No significant periodic pattern or peaks",
            'peak_hours': [],
            'recommended_buffer_pct': 10,
            'peak_to_avg_ratio': float(stats['p95'] / (stats['avg'] + 0.001)),
            'confidence': 0,
            'baseline_capacity': float(stats['avg']),
            'peak_capacity_required': float(stats['p95'])
        }

    def analyze_all_instances(self, instances_df: pd.DataFrame, 
                               metrics_df: pd.DataFrame,
                               with_periodicity: bool = True) -> pd.DataFrame:
        if instances_df.empty:
            return pd.DataFrame()

        analysis_results = []
        for _, instance in instances_df.iterrows():
            instance_id = instance['instance_id']
            utilization = self.analyze_instance_utilization(instance_id, metrics_df)
            
            result = {
                'instance_id': instance_id,
                'instance_name': instance.get('instance_name', ''),
                'instance_type': instance.get('instance_type', ''),
                'status': instance.get('status', ''),
                'region': instance.get('region', ''),
                'provider': instance.get('provider', ''),
                'cpu_avg': utilization['cpu']['avg'],
                'cpu_max': utilization['cpu']['max'],
                'cpu_p50': utilization['cpu']['p50'],
                'cpu_p75': utilization['cpu']['p75'],
                'cpu_p90': utilization['cpu']['p90'],
                'cpu_p95': utilization['cpu']['p95'],
                'cpu_p99': utilization['cpu']['p99'],
                'cpu_p999': utilization['cpu']['p999'],
                'cpu_std': utilization['cpu']['std'],
                'cpu_cv': utilization['cpu']['cv'],
                'memory_avg': utilization['memory']['avg'],
                'memory_max': utilization['memory']['max'],
                'memory_p50': utilization['memory']['p50'],
                'memory_p75': utilization['memory']['p75'],
                'memory_p90': utilization['memory']['p90'],
                'memory_p95': utilization['memory']['p95'],
                'memory_p99': utilization['memory']['p99'],
                'network_avg': utilization['network']['avg'],
                'network_max': utilization['network']['max']
            }

            if with_periodicity:
                cpu_periodicity = self.detect_periodicity(metrics_df, 'cpu_utilization', instance_id)
                cpu_buffer = self.calculate_buffer_requirement(metrics_df, 'cpu_utilization', instance_id)
                
                result.update({
                    'is_periodic': cpu_periodicity['is_periodic'],
                    'period_type': cpu_periodicity['period'],
                    'period_confidence': cpu_periodicity['confidence'],
                    'peak_hours': str(cpu_periodicity['peak_hours']),
                    'needs_buffer': cpu_buffer['needs_buffer'],
                    'recommended_buffer_pct': cpu_buffer['recommended_buffer_pct'],
                    'buffer_reason': cpu_buffer['buffer_reason']
                })

            analysis_results.append(result)

        return pd.DataFrame(analysis_results)

    def get_utilization_summary(self, analysis_df: pd.DataFrame) -> Dict:
        if analysis_df.empty:
            return {
                'total_instances': 0,
                'running_instances': 0,
                'avg_cpu_utilization': 0,
                'avg_memory_utilization': 0,
                'high_cpu_count': 0,
                'low_cpu_count': 0,
                'periodic_count': 0,
                'needs_buffer_count': 0
            }

        running_df = analysis_df[analysis_df['status'] == 'Running']
        
        return {
            'total_instances': len(analysis_df),
            'running_instances': len(running_df),
            'avg_cpu_utilization': float(running_df['cpu_avg'].mean()) if len(running_df) > 0 else 0,
            'avg_memory_utilization': float(running_df['memory_avg'].mean()) if len(running_df) > 0 else 0,
            'avg_cpu_p99': float(running_df['cpu_p99'].mean()) if len(running_df) > 0 else 0,
            'high_cpu_count': len(running_df[running_df['cpu_avg'] > 70]),
            'low_cpu_count': len(running_df[running_df['cpu_avg'] < 20]),
            'periodic_count': len(running_df[running_df.get('is_periodic', False)]) if 'is_periodic' in running_df.columns else 0,
            'needs_buffer_count': len(running_df[running_df.get('needs_buffer', False)]) if 'needs_buffer' in running_df.columns else 0,
            'regions': analysis_df['region'].unique().tolist(),
            'providers': analysis_df['provider'].unique().tolist()
        }
