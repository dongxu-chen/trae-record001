import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
from typing import List, Dict


class SampleDataGenerator:
    def __init__(self):
        self.events = [
            'page_view_home',
            'page_view_product',
            'page_view_category',
            'search',
            'add_to_cart',
            'view_cart',
            'checkout_start',
            'checkout_complete',
            'purchase',
            'login',
            'register',
            'logout'
        ]
        
        self.user_groups = ['new_user', 'returning_user', 'premium_user', 'vip_user']
        self.devices = ['mobile', 'desktop', 'tablet']
        self.oses = ['iOS', 'Android', 'Windows', 'macOS']
        self.browsers = ['Chrome', 'Safari', 'Firefox', 'Edge']

    def generate_user_id(self) -> str:
        return f"user_{uuid.uuid4().hex[:8]}"

    def generate_session_id(self) -> str:
        return f"sess_{uuid.uuid4().hex[:12]}"

    def generate_path(self, user_group: str) -> List[str]:
        paths = {
            'new_user': [
                ['page_view_home', 'register', 'page_view_product', 'add_to_cart', 'view_cart'],
                ['page_view_home', 'login', 'page_view_category', 'search'],
                ['page_view_home', 'page_view_product', 'page_view_category', 'search', 'add_to_cart'],
                ['page_view_home', 'register', 'page_view_home', 'logout'],
                ['page_view_home', 'login', 'page_view_product']
            ],
            'returning_user': [
                ['page_view_home', 'login', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'purchase'],
                ['page_view_home', 'search', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'purchase'],
                ['page_view_category', 'page_view_product', 'add_to_cart', 'checkout_complete'],
                ['page_view_home', 'page_view_product', 'page_view_product', 'add_to_cart', 'view_cart'],
                ['page_view_home', 'login', 'search', 'page_view_product', 'add_to_cart']
            ],
            'premium_user': [
                ['page_view_home', 'login', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'checkout_complete', 'purchase'],
                ['page_view_home', 'search', 'page_view_product', 'add_to_cart', 'checkout_start', 'purchase'],
                ['page_view_category', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_complete', 'purchase'],
                ['page_view_home', 'page_view_product', 'add_to_cart', 'checkout_start', 'checkout_complete', 'purchase']
            ],
            'vip_user': [
                ['page_view_home', 'login', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_start', 'checkout_complete', 'purchase'],
                ['page_view_home', 'search', 'page_view_product', 'page_view_product', 'add_to_cart', 'checkout_start', 'purchase'],
                ['page_view_category', 'page_view_product', 'add_to_cart', 'view_cart', 'checkout_complete', 'purchase'],
                ['page_view_home', 'page_view_category', 'search', 'page_view_product', 'add_to_cart', 'purchase']
            ]
        }
        
        return np.random.choice(paths.get(user_group, paths['new_user']))

    def generate_sample_data(self, 
                              num_users: int = 1000,
                              start_date: str = None,
                              end_date: str = None) -> pd.DataFrame:
        if start_date is None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        all_events = []
        
        for _ in range(num_users):
            user_id = self.generate_user_id()
            user_group = np.random.choice(self.user_groups, p=[0.4, 0.3, 0.2, 0.1])
            
            num_sessions = np.random.randint(1, 10)
            
            for _ in range(num_sessions):
                session_id = self.generate_session_id()
                device = np.random.choice(self.devices)
                os = np.random.choice(self.oses)
                browser = np.random.choice(self.browsers)
                
                path = self.generate_path(user_group)
                
                session_start = start_date + timedelta(
                    seconds=np.random.randint(0, int((end_date - start_date).total_seconds()))
                )
                
                for i, event in enumerate(path):
                    event_time = session_start + timedelta(seconds=i * np.random.randint(10, 120))
                    
                    all_events.append({
                        'user_id': user_id,
                        'session_id': session_id,
                        'event_name': event,
                        'event_time': event_time,
                        'page_url': f"/{event.replace('_', '/')}",
                        'referrer': '',
                        'device_type': device,
                        'os': os,
                        'browser': browser,
                        'user_group': user_group
                    })

        df = pd.DataFrame(all_events)
        df = df.sort_values('event_time')
        
        return df

    def save_to_csv(self, df: pd.DataFrame, filename: str = 'sample_data.csv'):
        df.to_csv(filename, index=False)
        print(f"样本数据已保存到 {filename}，共 {len(df)} 条记录")


if __name__ == "__main__":
    generator = SampleDataGenerator()
    df = generator.generate_sample_data(num_users=5000)
    generator.save_to_csv(df)
    print("\n数据概览:")
    print(f"用户数: {df['user_id'].nunique()}")
    print(f"会话数: {df['session_id'].nunique()}")
    print(f"事件数: {len(df)}")
    print(f"日期范围: {df['event_time'].min()} - {df['event_time'].max()}")
