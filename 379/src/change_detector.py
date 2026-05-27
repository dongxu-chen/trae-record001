import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict


class ChangeDetector:
    def __init__(self):
        self.change_history = defaultdict(list)
        
    def calculate_change_metrics(self, current_data, historical_data=None):
        metrics = pd.DataFrame({
            'customer_id': current_data['customer_id'].values,
            'current_ltv': current_data['ltv'].values,
            'current_purchases': current_data['predicted_purchases'].values,
            'current_amount': current_data['predicted_avg_amount'].values,
            'current_alive': current_data['probability_alive'].values
        })
        
        if historical_data is not None:
            merged = metrics.merge(
                historical_data[['customer_id', 'ltv', 'predicted_purchases', 'predicted_avg_amount', 'probability_alive']],
                on='customer_id',
                suffixes=('_current', '_previous')
            )
            
            merged['ltv_change'] = merged['ltv_current'] - merged['ltv_previous']
            merged['ltv_change_pct'] = (merged['ltv_change'] / merged['ltv_previous']) * 100
            merged['purchase_change'] = merged['predicted_purchases_current'] - merged['predicted_purchases_previous']
            merged['amount_change'] = merged['predicted_avg_amount_current'] - merged['predicted_avg_amount_previous']
            merged['alive_change'] = merged['probability_alive_current'] - merged['probability_alive_previous']
            
            return merged
        
        return metrics
    
    def detect_significant_changes(self, data, ltv_threshold_pct=20, alive_threshold=0.1):
        if 'ltv_change_pct' not in data.columns:
            data['ltv_change_pct'] = 0
            data['alive_change'] = 0
            
        significant_increases = data[
            (data['ltv_change_pct'] >= ltv_threshold_pct) |
            (data['alive_change'] >= alive_threshold)
        ]
        
        significant_decreases = data[
            (data['ltv_change_pct'] <= -ltv_threshold_pct) |
            (data['alive_change'] <= -alive_threshold)
        ]
        
        return {
            'increases': significant_increases,
            'decreases': significant_decreases,
            'n_increases': len(significant_increases),
            'n_decreases': len(significant_decreases)
        }
    
    def analyze_change_segments(self, changes, segment_column='segment'):
        increase_segments = changes['increases'].groupby(segment_column).agg({
            'customer_id': 'count',
            'ltv_change': 'sum',
            'ltv_change_pct': 'mean',
            'alive_change': 'mean'
        }).reset_index()
        
        decrease_segments = changes['decreases'].groupby(segment_column).agg({
            'customer_id': 'count',
            'ltv_change': 'sum',
            'ltv_change_pct': 'mean',
            'alive_change': 'mean'
        }).reset_index()
        
        return {
            'increase_by_segment': increase_segments,
            'decrease_by_segment': decrease_segments
        }
    
    def identify_churn_risk_customers(self, current_data, historical_data=None):
        if historical_data is None:
            churn_risk = current_data[current_data['probability_alive'] < 0.3].copy()
            churn_risk['risk_level'] = pd.cut(
                churn_risk['probability_alive'],
                bins=[0, 0.1, 0.2, 0.3],
                labels=['高风险', '中高风险', '中风险']
            )
            return churn_risk
        
        merged = current_data.merge(
            historical_data[['customer_id', 'probability_alive']],
            on='customer_id',
            suffixes=('_current', '_previous')
        )
        
        merged['alive_decline'] = merged['probability_alive_previous'] - merged['probability_alive_current']
        
        churn_risk = merged[
            (merged['probability_alive_current'] < 0.4) &
            (merged['alive_decline'] > 0.1)
        ].copy()
        
        churn_risk['risk_level'] = pd.cut(
            churn_risk['probability_alive_current'],
            bins=[0, 0.1, 0.2, 0.4],
            labels=['高风险', '中高风险', '中风险']
        )
        
        return churn_risk
    
    def generate_change_report(self, current_data, historical_data=None, ltv_threshold_pct=20):
        change_metrics = self.calculate_change_metrics(current_data, historical_data)
        
        if historical_data is not None:
            changes = self.detect_significant_changes(change_metrics, ltv_threshold_pct)
            segment_analysis = self.analyze_change_segments(changes)
            churn_risk = self.identify_churn_risk_customers(current_data, historical_data)
            
            report = {
                'total_customers': len(current_data),
                'n_increases': changes['n_increases'],
                'n_decreases': changes['n_decreases'],
                'increase_pct': changes['n_increases'] / len(current_data) * 100,
                'decrease_pct': changes['n_decreases'] / len(current_data) * 100,
                'total_ltv_increase': changes['increases']['ltv_change'].sum() if len(changes['increases']) > 0 else 0,
                'total_ltv_decrease': changes['decreases']['ltv_change'].sum() if len(changes['decreases']) > 0 else 0,
                'net_ltv_change': (changes['increases']['ltv_change'].sum() if len(changes['increases']) > 0 else 0) +
                                  (changes['decreases']['ltv_change'].sum() if len(changes['decreases']) > 0 else 0),
                'top_increases': changes['increases'].nlargest(10, 'ltv_change'),
                'top_decreases': changes['decreases'].nsmallest(10, 'ltv_change'),
                'segment_increases': segment_analysis['increase_by_segment'],
                'segment_decreases': segment_analysis['decrease_by_segment'],
                'churn_risk_customers': churn_risk,
                'churn_risk_count': len(churn_risk)
            }
        else:
            churn_risk = self.identify_churn_risk_customers(current_data)
            
            report = {
                'total_customers': len(current_data),
                'n_increases': 0,
                'n_decreases': 0,
                'increase_pct': 0,
                'decrease_pct': 0,
                'total_ltv_increase': 0,
                'total_ltv_decrease': 0,
                'net_ltv_change': 0,
                'top_increases': pd.DataFrame(),
                'top_decreases': pd.DataFrame(),
                'segment_increases': pd.DataFrame(),
                'segment_decreases': pd.DataFrame(),
                'churn_risk_customers': churn_risk,
                'churn_risk_count': len(churn_risk)
            }
        
        return report
    
    def monitor_daily_changes(self, daily_data):
        for date, data in daily_data.items():
            self.change_history[date] = {
                'total_ltv': data['ltv'].sum(),
                'avg_ltv': data['ltv'].mean(),
                'active_customers': (data['probability_alive'] > 0.5).sum(),
                'churn_risk_customers': (data['probability_alive'] < 0.3).sum()
            }
        
        history_df = pd.DataFrame.from_dict(self.change_history, orient='index')
        history_df.index = pd.to_datetime(history_df.index)
        
        trends = {
            'ltv_trend': history_df['total_ltv'].pct_change().tolist(),
            'active_trend': history_df['active_customers'].pct_change().tolist(),
            'churn_trend': history_df['churn_risk_customers'].pct_change().tolist()
        }
        
        return history_df, trends


if __name__ == '__main__':
    print("异动分析模块已加载")
