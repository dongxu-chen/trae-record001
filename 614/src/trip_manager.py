import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from scipy import stats

class TripRecordManager:
    def __init__(self, data_dir='user_data'):
        self.data_dir = data_dir
        self.trips_file = os.path.join(data_dir, 'trip_records.csv')
        self.refuels_file = os.path.join(data_dir, 'refuel_records.csv')
        self.vehicle_file = os.path.join(data_dir, 'vehicle_profile.json')
        self.anomalies_file = os.path.join(data_dir, 'anomaly_records.csv')
        self.dtc_file = os.path.join(data_dir, 'dtc_records.csv')
        
        os.makedirs(data_dir, exist_ok=True)
        self._init_files()
        
    def _init_files(self):
        if not os.path.exists(self.trips_file):
            pd.DataFrame(columns=[
                'trip_id', 'date', 'distance_km', 'fuel_used_l', 'actual_fuel_consumption',
                'predicted_fuel_consumption', 'avg_speed', 'max_speed', 'duration_min',
                'road_type', 'traffic_condition', 'weather_condition',
                'longitudinal_accel_mean', 'lateral_accel_mean',
                'hard_accel_count', 'hard_brake_count', 'hard_turn_count',
                'idle_time_ratio', 'cruise_ratio', 'notes'
            ]).to_csv(self.trips_file, index=False, encoding='utf-8-sig')
        
        if not os.path.exists(self.refuels_file):
            pd.DataFrame(columns=[
                'refuel_id', 'date', 'fuel_amount_l', 'fuel_price', 'total_cost',
                'odometer_km', 'previous_odometer', 'distance_since_last_refuel',
                'calculated_fuel_consumption', 'is_full_tank', 'station_name', 'notes'
            ]).to_csv(self.refuels_file, index=False, encoding='utf-8-sig')
        
        if not os.path.exists(self.anomalies_file):
            pd.DataFrame(columns=[
                'anomaly_id', 'date', 'trip_id', 'anomaly_type', 'severity',
                'description', 'fuel_consumption', 'baseline_consumption',
                'deviation_percent', 'is_acknowledged'
            ]).to_csv(self.anomalies_file, index=False, encoding='utf-8-sig')
        
        if not os.path.exists(self.dtc_file):
            pd.DataFrame(columns=[
                'dtc_id', 'date', 'dtc_code', 'description', 'severity',
                'status', 'cleared_date', 'fuel_impact_estimate', 'notes'
            ]).to_csv(self.dtc_file, index=False, encoding='utf-8-sig')
        
        if not os.path.exists(self.vehicle_file):
            default_vehicle = {
                'vin': 'UNKNOWN',
                'make': '未知',
                'model': '未知',
                'year': 2020,
                'engine_displacement': 2.0,
                'engine_type': '自然吸气',
                'fuel_type': '汽油',
                'tank_capacity': 50,
                'initial_odometer': 0,
                'baseline_fuel_consumption': 8.0,
                'calibration_factor': 1.0
            }
            with open(self.vehicle_file, 'w', encoding='utf-8') as f:
                json.dump(default_vehicle, f, ensure_ascii=False, indent=2)
    
    def add_trip(self, trip_data):
        trips = pd.read_csv(self.trips_file, encoding='utf-8-sig')
        trip_id = f"TRIP_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if 'trip_id' not in trip_data else trip_data['trip_id']
        
        new_trip = {
            'trip_id': trip_id,
            'date': trip_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'distance_km': trip_data.get('distance_km', 0),
            'fuel_used_l': trip_data.get('fuel_used_l', 0),
            'actual_fuel_consumption': trip_data.get('actual_fuel_consumption', 0),
            'predicted_fuel_consumption': trip_data.get('predicted_fuel_consumption', 0),
            'avg_speed': trip_data.get('avg_speed', 0),
            'max_speed': trip_data.get('max_speed', 0),
            'duration_min': trip_data.get('duration_min', 0),
            'road_type': trip_data.get('road_type', '城市道路'),
            'traffic_condition': trip_data.get('traffic_condition', '畅通'),
            'weather_condition': trip_data.get('weather_condition', '晴天'),
            'longitudinal_accel_mean': trip_data.get('longitudinal_accel_mean', 0),
            'lateral_accel_mean': trip_data.get('lateral_accel_mean', 0),
            'hard_accel_count': trip_data.get('hard_accel_count', 0),
            'hard_brake_count': trip_data.get('hard_brake_count', 0),
            'hard_turn_count': trip_data.get('hard_turn_count', 0),
            'idle_time_ratio': trip_data.get('idle_time_ratio', 0),
            'cruise_ratio': trip_data.get('cruise_ratio', 0),
            'notes': trip_data.get('notes', '')
        }
        
        trips = pd.concat([trips, pd.DataFrame([new_trip])], ignore_index=True)
        trips.to_csv(self.trips_file, index=False, encoding='utf-8-sig')
        return trip_id
    
    def add_refuel(self, refuel_data):
        refuels = pd.read_csv(self.refuels_file, encoding='utf-8-sig')
        refuel_id = f"REFUEL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        odometer = refuel_data.get('odometer_km', 0)
        prev_refuels = refuels[refuels['odometer_km'] < odometer].sort_values('odometer_km')
        prev_odometer = prev_refuels.iloc[-1]['odometer_km'] if len(prev_refuels) > 0 else 0
        distance = odometer - prev_odometer
        
        fuel_consumption = (refuel_data.get('fuel_amount_l', 0) / distance * 100) if distance > 0 and refuel_data.get('is_full_tank', True) else 0
        
        new_refuel = {
            'refuel_id': refuel_id,
            'date': refuel_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'fuel_amount_l': refuel_data.get('fuel_amount_l', 0),
            'fuel_price': refuel_data.get('fuel_price', 0),
            'total_cost': refuel_data.get('total_cost', 0),
            'odometer_km': odometer,
            'previous_odometer': prev_odometer,
            'distance_since_last_refuel': distance,
            'calculated_fuel_consumption': round(fuel_consumption, 2),
            'is_full_tank': refuel_data.get('is_full_tank', True),
            'station_name': refuel_data.get('station_name', ''),
            'notes': refuel_data.get('notes', '')
        }
        
        refuels = pd.concat([refuels, pd.DataFrame([new_refuel])], ignore_index=True)
        refuels.to_csv(self.refuels_file, index=False, encoding='utf-8-sig')
        return refuel_id, fuel_consumption
    
    def get_recent_trips(self, n=10):
        trips = pd.read_csv(self.trips_file, encoding='utf-8-sig')
        return trips.sort_values('date', ascending=False).head(n)
    
    def get_all_refuels(self):
        return pd.read_csv(self.refuels_file, encoding='utf-8-sig').sort_values('date', ascending=False)
    
    def get_statistics(self):
        trips = pd.read_csv(self.trips_file, encoding='utf-8-sig')
        refuels = pd.read_csv(self.refuels_file, encoding='utf-8-sig')
        
        stats = {
            'total_trips': len(trips),
            'total_distance_km': trips['distance_km'].sum() if len(trips) > 0 else 0,
            'total_fuel_l': refuels['fuel_amount_l'].sum() if len(refuels) > 0 else 0,
            'total_cost': refuels['total_cost'].sum() if len(refuels) > 0 else 0,
            'avg_fuel_consumption': trips['actual_fuel_consumption'].mean() if len(trips) > 0 else 0,
            'calibrated_consumption': self.get_calibrated_consumption()
        }
        return stats
    
    def get_calibrated_consumption(self):
        refuels = pd.read_csv(self.refuels_file, encoding='utf-8-sig')
        valid_refuels = refuels[(refuels['is_full_tank'] == True) & 
                               (refuels['distance_since_last_refuel'] > 50) &
                               (refuels['calculated_fuel_consumption'] > 0)]
        
        if len(valid_refuels) >= 3:
            return valid_refuels['calculated_fuel_consumption'].median()
        return 0
    
    def update_calibration_factor(self, model_baseline):
        actual = self.get_calibrated_consumption()
        if actual > 0 and model_baseline > 0:
            factor = actual / model_baseline
            with open(self.vehicle_file, 'r', encoding='utf-8') as f:
                vehicle = json.load(f)
            vehicle['calibration_factor'] = factor
            with open(self.vehicle_file, 'w', encoding='utf-8') as f:
                json.dump(vehicle, f, ensure_ascii=False, indent=2)
            return factor
        return 1.0
    
    def get_calibration_factor(self):
        with open(self.vehicle_file, 'r', encoding='utf-8') as f:
            vehicle = json.load(f)
        return vehicle.get('calibration_factor', 1.0)
    
    def get_vehicle_profile(self):
        with open(self.vehicle_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_vehicle_profile(self, profile_data):
        current = self.get_vehicle_profile()
        current.update(profile_data)
        with open(self.vehicle_file, 'w', encoding='utf-8') as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        return current
