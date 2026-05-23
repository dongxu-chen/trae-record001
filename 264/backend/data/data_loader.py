import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

class ODDataLoader:
    def __init__(self, data_path=None):
        self.data_path = data_path or Config.DATA_PATH
        self.grid_size = Config.GRID_SIZE
        self.time_slots = Config.TIME_SLOTS
        self.df = None
        
    def load_data(self):
        if not os.path.exists(self.data_path):
            print(f"Data file not found. Generating new data...")
            from data_generator import generate_od_data
            self.df = generate_od_data()
        else:
            self.df = pd.read_csv(self.data_path)
        return self.df
    
    def get_od_matrix(self, date, hour):
        if self.df is None:
            self.load_data()
            
        filtered = self.df[(self.df['date'] == date) & (self.df['hour'] == hour)]
        od_matrix = np.zeros((self.grid_size, self.grid_size, self.grid_size, self.grid_size))
        
        for _, row in filtered.iterrows():
            oi, oj, di, dj = int(row['origin_i']), int(row['origin_j']), int(row['dest_i']), int(row['dest_j'])
            od_matrix[oi, oj, di, dj] = row['demand']
            
        return od_matrix
    
    def get_flattened_od(self, date, hour):
        od_matrix = self.get_od_matrix(date, hour)
        return od_matrix.reshape(self.grid_size * self.grid_size, self.grid_size * self.grid_size)
    
    def get_grid_centers(self):
        center_lat, center_lon = Config.CITY_CENTER
        radius = Config.CITY_RADIUS
        
        centers = []
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                lat = center_lat - radius + (2 * radius / self.grid_size) * (i + 0.5)
                lon = center_lon - radius + (2 * radius / self.grid_size) * (j + 0.5)
                centers.append({'grid_id': i * self.grid_size + j, 'lat': lat, 'lon': lon, 'i': i, 'j': j})
        
        return pd.DataFrame(centers)
    
    def get_flow_data(self, date, hour, top_k=50):
        if self.df is None:
            self.load_data()
            
        filtered = self.df[(self.df['date'] == date) & (self.df['hour'] == hour)]
        filtered = filtered.sort_values('demand', ascending=False).head(top_k)
        
        flows = []
        for _, row in filtered.iterrows():
            flows.append({
                'from': [row['origin_lon'], row['origin_lat']],
                'to': [row['dest_lon'], row['dest_lat']],
                'demand': int(row['demand']),
                'origin_grid': int(row['origin_i'] * self.grid_size + row['origin_j']),
                'dest_grid': int(row['dest_i'] * self.grid_size + row['dest_j'])
            })
        
        return flows
    
    def get_time_series(self, origin_i, origin_j, dest_i, dest_j):
        if self.df is None:
            self.load_data()
            
        filtered = self.df[
            (self.df['origin_i'] == origin_i) & 
            (self.df['origin_j'] == origin_j) & 
            (self.df['dest_i'] == dest_i) & 
            (self.df['dest_j'] == dest_j)
        ]
        
        return filtered[['date', 'hour', 'demand']].sort_values(['date', 'hour'])
