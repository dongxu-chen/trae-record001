import os
import pickle
import numpy as np
import pandas as pd
import config


class ColdStartHandler:
    def __init__(self):
        self.user_stats = {}
        self.global_stats = {
            'avg_ctr': config.GLOBAL_AVERAGE_CTR,
            'total_samples': 0,
            'total_clicks': 0
        }
        self.default_user_embedding = None
        self.category_avg_ctr = {}
        
    def fit(self, df):
        self.global_stats['total_samples'] = len(df)
        self.global_stats['total_clicks'] = df['click'].sum()
        self.global_stats['avg_ctr'] = df['click'].mean()
        
        for category in config.VIDEO_CATEGORIES:
            category_data = df[df['category'] == category]
            if len(category_data) > 0:
                self.category_avg_ctr[category] = category_data['click'].mean()
            else:
                self.category_avg_ctr[category] = self.global_stats['avg_ctr']
        
        user_group = df.groupby('user_id').agg({
            'click': ['count', 'sum', 'mean']
        }).reset_index()
        user_group.columns = ['user_id', 'view_count', 'click_count', 'avg_ctr']
        
        for _, row in user_group.iterrows():
            self.user_stats[row['user_id']] = {
                'view_count': row['view_count'],
                'click_count': row['click_count'],
                'avg_ctr': row['avg_ctr'],
                'history_length': self._get_history_length(df, row['user_id'])
            }
        
        self._compute_default_user_embedding()
        
        print(f"ColdStartHandler fitted:")
        print(f"  Global average CTR: {self.global_stats['avg_ctr']:.4f}")
        print(f"  Users with stats: {len(self.user_stats)}")
        print(f"  Categories: {len(self.category_avg_ctr)}")
    
    def _get_history_length(self, df, user_id):
        user_data = df[df['user_id'] == user_id]
        if len(user_data) > 0:
            history = user_data['user_history'].iloc[0]
            if isinstance(history, str):
                return len(history.split(','))
        return 0
    
    def _compute_default_user_embedding(self):
        active_users = [
            stats['avg_ctr'] for uid, stats in self.user_stats.items()
            if stats['view_count'] >= config.COLD_START_THRESHOLD
        ]
        if active_users:
            self.default_user_embedding = {
                'avg_ctr': np.mean(active_users),
                'confidence': 0.5
            }
        else:
            self.default_user_embedding = {
                'avg_ctr': self.global_stats['avg_ctr'],
                'confidence': 0.3
            }
    
    def is_cold_start_user(self, user_id, history_count=0):
        if user_id not in self.user_stats:
            return True
        
        user_stat = self.user_stats[user_id]
        if user_stat['view_count'] < config.COLD_START_THRESHOLD:
            return True
        
        if history_count < config.COLD_START_THRESHOLD // 2:
            return True
        
        return False
    
    def get_user_prediction(self, user_id, category=None, history_count=0):
        is_cold = self.is_cold_start_user(user_id, history_count)
        
        if not is_cold and user_id in self.user_stats:
            return {
                'predicted_ctr': self.user_stats[user_id]['avg_ctr'],
                'confidence': min(1.0, self.user_stats[user_id]['view_count'] / 50),
                'source': 'user_history',
                'is_cold_start': False
            }
        
        if category and category in self.category_avg_ctr:
            return {
                'predicted_ctr': self.category_avg_ctr[category],
                'confidence': 0.6,
                'source': 'category_average',
                'is_cold_start': True
            }
        
        return {
            'predicted_ctr': self.global_stats['avg_ctr'],
            'confidence': 0.3,
            'source': 'global_average',
            'is_cold_start': True
        }
    
    def blend_predictions(self, model_prediction, cold_start_info, alpha=0.7):
        if not cold_start_info['is_cold_start']:
            return model_prediction
        
        confidence = cold_start_info['confidence']
        blended = (
            alpha * model_prediction +
            (1 - alpha) * cold_start_info['predicted_ctr']
        )
        
        return blended * confidence + cold_start_info['predicted_ctr'] * (1 - confidence)
    
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump({
                'user_stats': self.user_stats,
                'global_stats': self.global_stats,
                'default_user_embedding': self.default_user_embedding,
                'category_avg_ctr': self.category_avg_ctr
            }, f)
        print(f"ColdStartHandler saved to {path}")
    
    def load(self, path):
        if not os.path.exists(path):
            print(f"ColdStartHandler file not found: {path}")
            return False
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.user_stats = data['user_stats']
            self.global_stats = data['global_stats']
            self.default_user_embedding = data['default_user_embedding']
            self.category_avg_ctr = data['category_avg_ctr']
        
        print(f"ColdStartHandler loaded from {path}")
        return True


def handle_cold_start_for_prediction(cold_start_handler, user_id, category, model_prediction, history_count=0):
    cold_start_info = cold_start_handler.get_user_prediction(
        user_id, category, history_count
    )
    
    final_prediction = cold_start_handler.blend_predictions(
        model_prediction, cold_start_info
    )
    
    return {
        'final_ctr': final_prediction,
        'model_ctr': model_prediction,
        'cold_start_info': cold_start_info
    }
