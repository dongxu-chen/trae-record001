import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class SupplyDemandAnalyzer:
    def __init__(self):
        self.grid_size = Config.GRID_SIZE
        self.num_grids = self.grid_size * self.grid_size
        
    def generate_supply_distribution(self, date, hour, base_supply=100):
        supply = np.ones(self.num_grids) * base_supply
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                idx = i * self.grid_size + j
                
                dist_from_center = np.sqrt((i - self.grid_size//2)**2 + (j - self.grid_size//2)**2)
                center_factor = 1 + 0.5 * (1 - dist_from_center / (self.grid_size/2))
                
                if 7 <= hour <= 9:
                    residential_factor = 1.5 if (i > self.grid_size//2) else 1.0
                    center_factor *= residential_factor
                elif 17 <= hour <= 19:
                    commercial_factor = 1.5 if (i <= self.grid_size//2) else 1.0
                    center_factor *= commercial_factor
                
                supply[idx] *= center_factor
        
        return supply
    
    def generate_empty_trip_distribution(self, date, hour, od_matrix):
        empty_trips = np.zeros((self.num_grids, self.num_grids))
        
        dest_demands = np.sum(od_matrix, axis=0)
        origin_demands = np.sum(od_matrix, axis=1)
        
        for i in range(self.num_grids):
            surplus = max(0, dest_demands[i] - origin_demands[i]) * 0.3
            
            if surplus > 0:
                nearby_grids = self._get_nearby_grids(i, 2)
                for j in nearby_grids:
                    if origin_demands[j] > dest_demands[j]:
                        empty_trips[i, j] = surplus / len(nearby_grids)
        
        return empty_trips
    
    def _get_nearby_grids(self, grid_idx, radius=2):
        i = grid_idx // self.grid_size
        j = grid_idx % self.grid_size
        
        nearby = []
        for di in range(-radius, radius + 1):
            for dj in range(-radius, radius + 1):
                ni, nj = i + di, j + dj
                if 0 <= ni < self.grid_size and 0 <= nj < self.grid_size:
                    nearby.append(ni * self.grid_size + nj)
        
        return nearby
    
    def analyze_supply_demand_balance(self, date, hour, od_matrix):
        demand = np.sum(od_matrix, axis=1)
        
        supply = self.generate_supply_distribution(date, hour)
        empty_trips = self.generate_empty_trip_distribution(date, hour, od_matrix)
        
        empty_origin = np.sum(empty_trips, axis=1)
        empty_dest = np.sum(empty_trips, axis=0)
        
        effective_supply = supply + empty_dest - empty_origin
        
        balance_ratio = demand / (effective_supply + 1e-6)
        gap = demand - effective_supply
        
        gap_levels = []
        for i in range(self.num_grids):
            if gap[i] > 20:
                level = 'critical'
            elif gap[i] > 10:
                level = 'high'
            elif gap[i] > 0:
                level = 'medium'
            elif gap[i] < -20:
                level = 'surplus'
            else:
                level = 'balanced'
            gap_levels.append(level)
        
        total_gap = np.sum(np.maximum(0, gap))
        total_surplus = np.sum(np.maximum(0, -gap))
        
        return {
            'demand': demand.tolist(),
            'supply': effective_supply.tolist(),
            'raw_supply': supply.tolist(),
            'empty_origin': empty_origin.tolist(),
            'empty_dest': empty_dest.tolist(),
            'empty_trips': empty_trips.tolist(),
            'balance_ratio': balance_ratio.tolist(),
            'gap': gap.tolist(),
            'gap_levels': gap_levels,
            'total_gap': float(total_gap),
            'total_surplus': float(total_surplus),
            'critical_grids': [int(i) for i, g in enumerate(gap_levels) if g == 'critical'],
            'surplus_grids': [int(i) for i, g in enumerate(gap_levels) if g == 'surplus']
        }
    
    def suggest_relocation(self, balance_analysis, top_k=5):
        gap = np.array(balance_analysis['gap'])
        empty_trips = np.array(balance_analysis['empty_trips'])
        
        critical_indices = np.argsort(-gap)[:top_k]
        surplus_indices = np.argsort(gap)[:top_k]
        
        suggestions = []
        for crit_idx in critical_indices:
            if gap[crit_idx] <= 0:
                continue
                
            nearby_surplus = []
            for surp_idx in surplus_indices:
                if gap[surp_idx] < 0:
                    dist = self._grid_distance(crit_idx, surp_idx)
                    nearby_surplus.append((surp_idx, dist, -gap[surp_idx]))
            
            nearby_surplus.sort(key=lambda x: x[1])
            
            if nearby_surplus:
                suggestions.append({
                    'from_grid': int(nearby_surplus[0][0]),
                    'to_grid': int(crit_idx),
                    'estimated_gap': float(gap[crit_idx]),
                    'available_supply': float(nearby_surplus[0][2]),
                    'distance': float(nearby_surplus[0][1])
                })
        
        return suggestions
    
    def _grid_distance(self, idx1, idx2):
        i1, j1 = idx1 // self.grid_size, idx1 % self.grid_size
        i2, j2 = idx2 // self.grid_size, idx2 % self.grid_size
        return np.sqrt((i1 - i2)**2 + (j1 - j2)**2)
