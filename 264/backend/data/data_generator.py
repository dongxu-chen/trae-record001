import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

def generate_od_data():
    np.random.seed(42)
    
    grid_size = Config.GRID_SIZE
    time_slots = Config.TIME_SLOTS
    history_days = Config.HISTORY_DAYS
    total_records = history_days * time_slots * grid_size * grid_size
    
    records = []
    start_date = datetime(2024, 1, 1)
    
    center_lat, center_lon = Config.CITY_CENTER
    radius = Config.CITY_RADIUS
    
    for day in range(history_days):
        current_date = start_date + timedelta(days=day)
        is_weekend = current_date.weekday() >= 5
        
        for hour in range(time_slots):
            for origin_i in range(grid_size):
                for origin_j in range(grid_size):
                    origin_lat = center_lat - radius + (2 * radius / grid_size) * (origin_i + 0.5)
                    origin_lon = center_lon - radius + (2 * radius / grid_size) * (origin_j + 0.5)
                    
                    for dest_i in range(grid_size):
                        for dest_j in range(grid_size):
                            if origin_i == dest_i and origin_j == dest_j:
                                continue
                                
                            dest_lat = center_lat - radius + (2 * radius / grid_size) * (dest_i + 0.5)
                            dest_lon = center_lon - radius + (2 * radius / grid_size) * (dest_j + 0.5)
                            
                            distance = np.sqrt((origin_lat - dest_lat)**2 + (origin_lon - dest_lon)**2)
                            
                            base_demand = 5
                            
                            if 7 <= hour <= 9 or 17 <= hour <= 19:
                                base_demand *= 3
                            elif 10 <= hour <= 16:
                                base_demand *= 1.5
                            elif 22 <= hour or hour <= 5:
                                base_demand *= 0.3
                            
                            if is_weekend:
                                if 10 <= hour <= 20:
                                    base_demand *= 1.5
                                else:
                                    base_demand *= 0.7
                            
                            center_origin = abs(origin_i - grid_size//2) + abs(origin_j - grid_size//2)
                            center_dest = abs(dest_i - grid_size//2) + abs(dest_j - grid_size//2)
                            center_factor = (grid_size - center_origin) / grid_size * (grid_size - center_dest) / grid_size
                            base_demand *= (0.5 + center_factor)
                            
                            distance_factor = max(0.2, 1 - distance * 10)
                            base_demand *= distance_factor
                            
                            demand = max(0, int(np.random.poisson(base_demand)))
                            
                            records.append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'hour': hour,
                                'origin_i': origin_i,
                                'origin_j': origin_j,
                                'dest_i': dest_i,
                                'dest_j': dest_j,
                                'origin_lat': origin_lat,
                                'origin_lon': origin_lon,
                                'dest_lat': dest_lat,
                                'dest_lon': dest_lon,
                                'demand': demand
                            })
    
    df = pd.DataFrame(records)
    df.to_csv(Config.DATA_PATH, index=False)
    print(f"Data generated: {len(df)} records saved to {Config.DATA_PATH}")
    return df

if __name__ == '__main__':
    generate_od_data()
