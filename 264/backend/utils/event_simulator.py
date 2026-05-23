import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class EventSimulator:
    def __init__(self):
        self.grid_size = Config.GRID_SIZE
        self.num_grids = self.grid_size * self.grid_size
        
    def simulate_event(self, event_type, event_params, base_od_matrix, date, hour):
        if event_type == 'concert':
            return self._simulate_concert(event_params, base_od_matrix, date, hour)
        elif event_type == 'rainstorm':
            return self._simulate_rainstorm(event_params, base_od_matrix, date, hour)
        elif event_type == 'traffic_accident':
            return self._simulate_traffic_accident(event_params, base_od_matrix, date, hour)
        else:
            return base_od_matrix
    
    def _simulate_concert(self, params, base_od, date, hour):
        venue_grid = params.get('venue_grid', 45)
        start_hour = params.get('start_hour', 19)
        end_hour = params.get('end_hour', 22)
        attendance = params.get('attendance', 5000)
        
        affected_od = base_od.copy()
        
        if hour == start_hour - 1:
            inflow_factor = 2.5
            for i in range(self.num_grids):
                dist = self._grid_distance(i, venue_grid)
                dist_factor = max(0.3, 1 - dist / (self.grid_size / 2))
                affected_od[i, venue_grid] = base_od[i, venue_grid] * inflow_factor * dist_factor
                
        elif hour == start_hour:
            inflow_factor = 4.0
            for i in range(self.num_grids):
                dist = self._grid_distance(i, venue_grid)
                dist_factor = max(0.3, 1 - dist / (self.grid_size / 2))
                affected_od[i, venue_grid] = base_od[i, venue_grid] * inflow_factor * dist_factor
                
        elif start_hour < hour < end_hour:
            inflow_factor = 1.5
            for i in range(self.num_grids):
                dist = self._grid_distance(i, venue_grid)
                dist_factor = max(0.3, 1 - dist / (self.grid_size / 2))
                affected_od[i, venue_grid] = base_od[i, venue_grid] * inflow_factor * dist_factor
                affected_od[venue_grid, i] = base_od[venue_grid, i] * 0.3
                
        elif hour == end_hour or hour == end_hour + 1:
            outflow_factor = 3.5
            for i in range(self.num_grids):
                dist = self._grid_distance(i, venue_grid)
                dist_factor = max(0.3, 1 - dist / (self.grid_size / 2))
                affected_od[venue_grid, i] = base_od[venue_grid, i] * outflow_factor * dist_factor
        
        event_impact = {
            'type': 'concert',
            'venue_grid': venue_grid,
            'affected_od': affected_od.tolist(),
            'increase_ratio': float(np.sum(affected_od) / np.sum(base_od)) if np.sum(base_od) > 0 else 1.0,
            'affected_grids': self._get_affected_grids(venue_grid, 3)
        }
        
        return event_impact
    
    def _simulate_rainstorm(self, params, base_od, date, hour):
        intensity = params.get('intensity', 'heavy')
        affected_grids = params.get('affected_grids', list(range(self.num_grids)))
        
        intensity_factors = {
            'light': {'general': 0.9, 'peak': 1.1},
            'moderate': {'general': 0.7, 'peak': 1.3},
            'heavy': {'general': 0.5, 'peak': 1.5}
        }
        
        factors = intensity_factors.get(intensity, intensity_factors['moderate'])
        
        affected_od = base_od.copy()
        
        is_peak = 7 <= hour <= 9 or 17 <= hour <= 19
        
        for i in range(self.num_grids):
            for j in range(self.num_grids):
                if i in affected_grids or j in affected_grids:
                    if is_peak:
                        affected_od[i, j] = base_od[i, j] * factors['peak']
                    else:
                        affected_od[i, j] = base_od[i, j] * factors['general']
        
        event_impact = {
            'type': 'rainstorm',
            'intensity': intensity,
            'affected_od': affected_od.tolist(),
            'increase_ratio': float(np.sum(affected_od) / np.sum(base_od)) if np.sum(base_od) > 0 else 1.0,
            'affected_grids': affected_grids
        }
        
        return event_impact
    
    def _simulate_traffic_accident(self, params, base_od, date, hour):
        accident_grid = params.get('accident_grid', 50)
        severity = params.get('severity', 'medium')
        duration = params.get('duration', 2)
        
        severity_factors = {
            'minor': 0.8,
            'medium': 0.5,
            'severe': 0.2
        }
        
        factor = severity_factors.get(severity, severity_factors['medium'])
        
        affected_od = base_od.copy()
        
        nearby_grids = self._get_affected_grids(accident_grid, 2)
        
        for i in nearby_grids:
            for j in nearby_grids:
                affected_od[i, j] = base_od[i, j] * factor
        
        detour_grids = self._get_affected_grids(accident_grid, 4)
        for i in detour_grids:
            for j in detour_grids:
                if i not in nearby_grids and j not in nearby_grids:
                    affected_od[i, j] = base_od[i, j] * 1.2
        
        event_impact = {
            'type': 'traffic_accident',
            'accident_grid': accident_grid,
            'severity': severity,
            'affected_od': affected_od.tolist(),
            'increase_ratio': float(np.sum(affected_od) / np.sum(base_od)) if np.sum(base_od) > 0 else 1.0,
            'blocked_grids': nearby_grids,
            'detour_grids': detour_grids
        }
        
        return event_impact
    
    def _grid_distance(self, idx1, idx2):
        i1, j1 = idx1 // self.grid_size, idx1 % self.grid_size
        i2, j2 = idx2 // self.grid_size, idx2 % self.grid_size
        return np.sqrt((i1 - i2)**2 + (j1 - j2)**2)
    
    def _get_affected_grids(self, center_grid, radius):
        grids = []
        ci, cj = center_grid // self.grid_size, center_grid % self.grid_size
        
        for i in range(max(0, ci - radius), min(self.grid_size, ci + radius + 1)):
            for j in range(max(0, cj - radius), min(self.grid_size, cj + radius + 1)):
                dist = np.sqrt((i - ci)**2 + (j - cj)**2)
                if dist <= radius:
                    grids.append(i * self.grid_size + j)
        
        return grids
    
    def compare_od_diff(self, base_od, affected_od):
        diff = affected_od - base_od
        
        diff_stats = {
            'total_increase': float(np.sum(np.maximum(0, diff))),
            'total_decrease': float(np.sum(np.maximum(0, -diff))),
            'net_change': float(np.sum(diff)),
            'max_increase': float(np.max(diff)),
            'max_decrease': float(np.min(diff)),
            'changed_pairs': int(np.sum(diff != 0)),
            'diff_matrix': diff.tolist()
        }
        
        return diff_stats
    
    def get_available_events(self):
        return [
            {
                'type': 'concert',
                'name': '演唱会',
                'icon': '🎵',
                'description': '大型演唱会散场/入场高峰',
                'params': [
                    {'name': 'venue_grid', 'label': '场馆位置', 'type': 'grid', 'default': 45},
                    {'name': 'start_hour', 'label': '开始时间', 'type': 'number', 'default': 19},
                    {'name': 'end_hour', 'label': '结束时间', 'type': 'number', 'default': 22},
                    {'name': 'attendance', 'label': '观众人数', 'type': 'number', 'default': 5000}
                ]
            },
            {
                'type': 'rainstorm',
                'name': '暴雨天气',
                'icon': '🌧️',
                'description': '不同强度暴雨对打车需求的影响',
                'params': [
                    {'name': 'intensity', 'label': '暴雨强度', 'type': 'select', 
                     'options': ['light', 'moderate', 'heavy'], 
                     'labels': ['小雨', '中雨', '暴雨'],
                     'default': 'heavy'}
                ]
            },
            {
                'type': 'traffic_accident',
                'name': '交通事故',
                'icon': '🚨',
                'description': '道路交通事故造成的拥堵',
                'params': [
                    {'name': 'accident_grid', 'label': '事故位置', 'type': 'grid', 'default': 50},
                    {'name': 'severity', 'label': '严重程度', 'type': 'select',
                     'options': ['minor', 'medium', 'severe'],
                     'labels': ['轻微', '中等', '严重'],
                     'default': 'medium'},
                    {'name': 'duration', 'label': '持续时间(小时)', 'type': 'number', 'default': 2}
                ]
            }
        ]
