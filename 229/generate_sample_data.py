import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_sample_data(output_file='sample_orders.csv'):
    np.random.seed(42)
    random.seed(42)
    
    start_date = datetime.now() - timedelta(days=14)
    
    hotspots = [
        {'lat': 39.9042, 'lng': 116.4074, 'weight': 1.5},
        {'lat': 39.9163, 'lng': 116.3972, 'weight': 1.3},
        {'lat': 39.9847, 'lng': 116.3056, 'weight': 1.2},
        {'lat': 39.8653, 'lng': 116.4483, 'weight': 1.4},
        {'lat': 39.9087, 'lng': 116.3912, 'weight': 1.6},
        {'lat': 39.9299, 'lng': 116.4427, 'weight': 1.1},
        {'lat': 39.8617, 'lng': 116.3729, 'weight': 1.0},
        {'lat': 39.9930, 'lng': 116.4618, 'weight': 0.9},
    ]
    
    data = []
    
    for day in range(14):
        current_date = start_date + timedelta(days=day)
        is_weekend = current_date.weekday() >= 5
        
        for hour in range(24):
            if hour < 6:
                time_factor = 0.2
            elif hour < 9:
                time_factor = 1.8
            elif hour < 12:
                time_factor = 1.2
            elif hour < 14:
                time_factor = 1.5
            elif hour < 18:
                time_factor = 1.0
            elif hour < 22:
                time_factor = 1.6
            else:
                time_factor = 0.8
            
            if is_weekend:
                time_factor *= 0.8 if hour < 10 else 1.2
            
            for hotspot in hotspots:
                for _ in range(3):
                    lat_offset = np.random.normal(0, 0.02)
                    lng_offset = np.random.normal(0, 0.02)
                    lat = hotspot['lat'] + lat_offset
                    lng = hotspot['lng'] + lng_offset
                    
                    if 39.8 <= lat <= 40.1 and 116.2 <= lng <= 116.6:
                        base_orders = int(10 * hotspot['weight'] * time_factor)
                        order_count = max(1, int(np.random.poisson(base_orders)))
                        
                        timestamp = current_date + timedelta(hours=hour)
                        
                        data.append({
                            'lat': round(lat, 6),
                            'lng': round(lng, 6),
                            'timestamp': timestamp.isoformat(),
                            'order_count': order_count
                        })
    
    df = pd.DataFrame(data)
    df = df.sort_values('timestamp')
    df.to_csv(output_file, index=False)
    
    print(f"生成样本数据: {output_file}")
    print(f"数据条数: {len(df)}")
    print(f"时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
    print(f"平均订单量: {df['order_count'].mean():.2f}")
    
    return df

if __name__ == '__main__':
    generate_sample_data()
