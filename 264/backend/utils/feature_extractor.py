import numpy as np
import pandas as pd
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class SpatialTemporalFeatureExtractor:
    def __init__(self):
        self.grid_size = Config.GRID_SIZE
        self.time_slots = Config.TIME_SLOTS
        self.history_days = Config.HISTORY_DAYS
        
    def extract_temporal_features(self, date, hour):
        dt = datetime.strptime(date, '%Y-%m-%d')
        day_of_week = dt.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        
        is_peak = 1 if (7 <= hour <= 9 or 17 <= hour <= 19) else 0
        
        return np.array([hour, hour_sin, hour_cos, day_of_week, day_sin, day_cos, is_weekend, is_peak])
    
    def extract_spatial_features(self, grid_i, grid_j):
        center_i = self.grid_size // 2
        center_j = self.grid_size // 2
        
        dist_from_center = np.sqrt((grid_i - center_i)**2 + (grid_j - center_j)**2) / (self.grid_size / 2)
        
        norm_i = grid_i / self.grid_size
        norm_j = grid_j / self.grid_size
        
        is_border = 1 if (grid_i == 0 or grid_i == self.grid_size - 1 or 
                          grid_j == 0 or grid_j == self.grid_size - 1) else 0
        
        return np.array([norm_i, norm_j, dist_from_center, is_border])
    
    def extract_pair_spatial_features(self, origin_i, origin_j, dest_i, dest_j):
        origin_feat = self.extract_spatial_features(origin_i, origin_j)
        dest_feat = self.extract_spatial_features(dest_i, dest_j)
        
        distance = np.sqrt((origin_i - dest_i)**2 + (origin_j - dest_j)**2) / self.grid_size
        same_row = 1 if origin_i == dest_i else 0
        same_col = 1 if origin_j == dest_j else 0
        
        direction = np.arctan2(dest_i - origin_i, dest_j - origin_j)
        dir_sin = np.sin(direction)
        dir_cos = np.cos(direction)
        
        return np.concatenate([origin_feat, dest_feat, [distance, same_row, same_col, dir_sin, dir_cos]])
    
    def extract_history_features(self, od_matrix_sequence):
        if len(od_matrix_sequence) == 0:
            return np.zeros((self.grid_size, self.grid_size, 10))
        
        features = []
        for oi in range(self.grid_size):
            row_features = []
            for oj in range(self.grid_size):
                history_demands = []
                for od_matrix in od_matrix_sequence:
                    total_demand = np.sum(od_matrix[oi, oj, :, :])
                    history_demands.append(total_demand)
                
                history_demands = np.array(history_demands)
                
                if len(history_demands) > 0:
                    mean_demand = np.mean(history_demands)
                    std_demand = np.std(history_demands)
                    max_demand = np.max(history_demands)
                    min_demand = np.min(history_demands)
                    last_demand = history_demands[-1]
                    trend = history_demands[-1] - history_demands[0] if len(history_demands) > 1 else 0
                else:
                    mean_demand = std_demand = max_demand = min_demand = last_demand = trend = 0
                
                row_features.append([
                    mean_demand, std_demand, max_demand, min_demand,
                    last_demand, trend,
                    np.percentile(history_demands, 25) if len(history_demands) > 0 else 0,
                    np.percentile(history_demands, 50) if len(history_demands) > 0 else 0,
                    np.percentile(history_demands, 75) if len(history_demands) > 0 else 0,
                    len(history_demands)
                ])
            features.append(row_features)
        
        return np.array(features)
    
    def create_model_input(self, od_matrix_sequence, date, hour):
        temporal_feat = self.extract_temporal_features(date, hour)
        history_feat = self.extract_history_features(od_matrix_sequence)
        
        temporal_feat_expanded = np.tile(
            temporal_feat.reshape(1, 1, -1),
            (self.grid_size, self.grid_size, 1)
        )
        
        spatial_feat_map = np.zeros((self.grid_size, self.grid_size, 4))
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                spatial_feat_map[i, j] = self.extract_spatial_features(i, j)
        
        combined_features = np.concatenate([
            temporal_feat_expanded,
            spatial_feat_map,
            history_feat
        ], axis=-1)
        
        return combined_features
    
    def create_od_pair_features(self, date, hour):
        features = []
        labels = []
        
        temporal_feat = self.extract_temporal_features(date, hour)
        
        for oi in range(self.grid_size):
            for oj in range(self.grid_size):
                for di in range(self.grid_size):
                    for dj in range(self.grid_size):
                        if oi == di and oj == dj:
                            continue
                        spatial_pair_feat = self.extract_pair_spatial_features(oi, oj, di, dj)
                        combined_feat = np.concatenate([temporal_feat, spatial_pair_feat])
                        features.append(combined_feat)
        
        return np.array(features)
