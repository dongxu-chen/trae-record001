import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from scipy import stats

class FuelAnomalyDetector:
    def __init__(self, data_dir='user_data'):
        self.data_dir = data_dir
        self.trips_file = os.path.join(data_dir, 'trip_records.csv')
        self.anomalies_file = os.path.join(data_dir, 'anomaly_records.csv')
    
    def detect_anomalies(self, window_size=7, threshold_std=2.0, min_baseline_days=14):
        trips = pd.read_csv(self.trips_file, encoding='utf-8-sig')
        if len(trips) < 5:
            return []
        
        trips['date'] = pd.to_datetime(trips['date'])
        trips = trips.sort_values('date')
        
        anomalies = []
        
        baseline_period = datetime.now() - timedelta(days=min_baseline_days)
        baseline_trips = trips[trips['date'] >= baseline_period]
        
        if len(baseline_trips) < 5:
            baseline_trips = trips
        
        valid_trips = trips[trips['actual_fuel_consumption'] > 0].copy()
        
        if len(valid_trips) == 0:
            return []
        
        valid_trips['rolling_mean'] = valid_trips['actual_fuel_consumption'].rolling(window=window_size, min_periods=3).mean()
        valid_trips['rolling_std'] = valid_trips['actual_fuel_consumption'].rolling(window=window_size, min_periods=3).std()
        
        baseline_mean = baseline_trips['actual_fuel_consumption'].median()
        baseline_std = baseline_trips['actual_fuel_consumption'].std()
        
        for idx, trip in valid_trips.iterrows():
            current_fc = trip['actual_fuel_consumption']
            
            if pd.isna(trip['rolling_mean']):
                continue
            
            z_score = (current_fc - trip['rolling_mean']) / (trip['rolling_std'] if trip['rolling_std'] > 0 else 1)
            
            deviation_from_baseline = (current_fc - baseline_mean) / baseline_std if baseline_std > 0 else 0
            
            is_anomaly = False
            anomaly_type = None
            severity = None
            description = None
            
            if z_score > threshold_std and current_fc > baseline_mean * 1.15:
                is_anomaly = True
                if z_score > 3.0 or current_fc > baseline_mean * 1.4:
                    severity = 'high'
                    anomaly_type = 'sudden_spike'
                    description = f'油耗急剧上升超过基线 {((current_fc / baseline_mean - 1) * 100):.1f}%，显著高于正常水平'
                elif z_score > 2.0:
                    severity = 'medium'
                    anomaly_type = 'moderate_increase'
                    description = f'油耗较基线上升 {((current_fc / baseline_mean - 1) * 100):.1f}%'
            
            if is_anomaly:
                anomalies.append({
                    'trip_id': trip['trip_id'],
                    'date': trip['date'].strftime('%Y-%m-%d %H:%M:%S'),
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'description': description,
                    'fuel_consumption': current_fc,
                    'baseline_consumption': baseline_mean,
                    'deviation_percent': ((current_fc / baseline_mean - 1) * 100)
                })
        
        self._save_anomalies(anomalies)
        return anomalies
    
    def _save_anomalies(self, anomalies):
        if len(anomalies) == 0:
            return
        
        existing = pd.read_csv(self.anomalies_file, encoding='utf-8-sig')
        existing_trip_ids = set(existing['trip_id'].values) if len(existing) > 0 else set()
        
        new_anomalies = []
        for a in anomalies:
            if a['trip_id'] not in existing_trip_ids:
                a['anomaly_id'] = f"ANOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(new_anomalies)}"
                a['is_acknowledged'] = False
                new_anomalies.append(a)
        
        if len(new_anomalies) > 0:
            updated = pd.concat([existing, pd.DataFrame(new_anomalies)], ignore_index=True)
            updated.to_csv(self.anomalies_file, index=False, encoding='utf-8-sig')
    
    def get_anomalies(self, acknowledged=False):
        anomalies = pd.read_csv(self.anomalies_file, encoding='utf-8-sig')
        if not acknowledged:
            anomalies = anomalies[anomalies['is_acknowledged'] == False]
        return anomalies.sort_values('date', ascending=False)
    
    def acknowledge_anomaly(self, anomaly_id):
        anomalies = pd.read_csv(self.anomalies_file, encoding='utf-8-sig')
        if anomaly_id in anomalies['anomaly_id'].values:
            anomalies.loc[anomalies['anomaly_id'] == anomaly_id, 'is_acknowledged'] = True
            anomalies.to_csv(self.anomalies_file, index=False, encoding='utf-8-sig')
            return True
        return False
    
    def get_trend_analysis(self):
        trips = pd.read_csv(self.trips_file, encoding='utf-8-sig')
        if len(trips) < 10:
            return None
        
        trips['date'] = pd.to_datetime(trips['date'])
        trips = trips.sort_values('date')
        
        recent = trips.tail(10)
        earlier = trips.head(len(trips) - 10)
        
        recent_avg = recent['actual_fuel_consumption'].mean() if len(recent) > 0 else 0
        earlier_avg = earlier['actual_fuel_consumption'].mean() if len(earlier) > 0 else 0
        
        trend = 'stable'
        trend_change = 0
        
        if earlier_avg > 0:
            trend_change = (recent_avg - earlier_avg) / earlier_avg * 100
            if trend_change > 10:
                trend = 'rising'
            elif trend_change < -5:
                trend = 'falling'
        
        return {
            'trend': trend,
            'trend_percent': trend_change,
            'recent_avg': recent_avg,
            'earlier_avg': earlier_avg,
            'total_trips': len(trips)
        }
