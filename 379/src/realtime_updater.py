import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler


class RealtimeUpdater:
    def __init__(self, bg_nbd_model, gamma_gamma_model, analyzer):
        self.bg_nbd = bg_nbd_model
        self.gamma_gamma = gamma_gamma_model
        self.analyzer = analyzer
        self.scaler = StandardScaler()
        
        self.update_history = []
        self.model_version = 0
        
    def process_incremental_data(self, new_transactions, new_behavior_logs=None):
        if len(new_transactions) == 0:
            return None
        
        current_date = datetime.now()
        
        new_customers = new_transactions['customer_id'].unique()
        
        rfm_updates = {}
        
        for customer_id in new_customers:
            customer_trans = new_transactions[new_transactions['customer_id'] == customer_id]
            
            if len(customer_trans) > 0:
                last_purchase = customer_trans['transaction_date'].max()
                first_purchase = customer_trans['transaction_date'].min()
                total_amount = customer_trans['amount'].sum()
                count = len(customer_trans)
                
                rfm_updates[customer_id] = {
                    'last_purchase': last_purchase,
                    'first_purchase': first_purchase,
                    'frequency_delta': count,
                    'monetary_delta': total_amount,
                    'recency': (current_date - last_purchase).days
                }
        
        return rfm_updates
    
    def update_customer_metrics(self, existing_data, rfm_updates, observation_end_date=None):
        if observation_end_date is None:
            observation_end_date = datetime.now()
        
        updated_data = existing_data.copy()
        
        for customer_id, updates in rfm_updates.items():
            mask = updated_data['customer_id'] == customer_id
            
            if mask.any():
                idx = updated_data[mask].index[0]
                
                current_freq = updated_data.loc[idx, 'frequency']
                current_T = updated_data.loc[idx, 'T']
                
                updated_data.loc[idx, 'frequency'] = current_freq + updates['frequency_delta']
                updated_data.loc[idx, 'recency'] = updates['recency']
                updated_data.loc[idx, 'T'] = current_T + 30
                
                current_total = updated_data.loc[idx, 'total_amount'] if 'total_amount' in updated_data.columns else updated_data.loc[idx, 'avg_amount'] * current_freq
                new_total = current_total + updates['monetary_delta']
                new_freq = updated_data.loc[idx, 'frequency']
                
                if new_freq > 0:
                    updated_data.loc[idx, 'avg_amount'] = new_total / new_freq
        
        return updated_data
    
    def incremental_update(self, existing_ltv_data, new_transactions, future_months=12, discount_rate=0.01):
        rfm_updates = self.process_incremental_data(new_transactions)
        
        if rfm_updates is None or len(rfm_updates) == 0:
            return existing_ltv_data, False
        
        updated_ltv = self.analyzer.calculate_ltv(
            self.analyzer.bg_nbd.model,
            future_months=future_months,
            discount_rate=discount_rate
        )
        
        self.update_history.append({
            'timestamp': datetime.now(),
            'n_new_transactions': len(new_transactions),
            'n_updated_customers': len(rfm_updates),
            'model_version': self.model_version
        })
        
        return updated_ltv, True
    
    def batch_update(self, existing_data, new_data_batch, segment_thresholds=None):
        combined_data = pd.concat([existing_data, new_data_batch], ignore_index=True)
        
        combined_data = combined_data.drop_duplicates(subset=['customer_id'], keep='last')
        
        updated_ltv = self.analyzer.calculate_ltv(
            combined_data,
            future_months=12
        )
        
        if segment_thresholds:
            segment_names = ['低价值客户', '中价值客户', '高价值客户'][:len(segment_thresholds) + 1]
            updated_ltv, segment_stats = self.analyzer.segment_customers(
                combined_data,
                updated_ltv,
                thresholds=segment_thresholds,
                segment_names=segment_names
            )
        else:
            updated_ltv, segment_stats = self.analyzer.segment_customers(
                combined_data,
                updated_ltv,
                n_segments=4
            )
        
        self.model_version += 1
        
        self.update_history.append({
            'timestamp': datetime.now(),
            'update_type': 'batch',
            'n_customers': len(combined_data),
            'model_version': self.model_version
        })
        
        return combined_data, updated_ltv, segment_stats
    
    def generate_update_schedule(self, update_frequency='daily'):
        schedules = {
            'daily': {
                'description': '每日增量更新',
                'tasks': [
                    '收集前一日新增交易数据',
                    '更新客户RFM指标',
                    '重新计算LTV预测',
                    '检测显著变化客户',
                    '生成更新报告'
                ]
            },
            'weekly': {
                'description': '每周批量更新',
                'tasks': [
                    '汇总一周交易数据',
                    '批量更新RFM指标',
                    '重新训练模型(可选)',
                    '更新客户分群',
                    '生成周报'
                ]
            },
            'monthly': {
                'description': '每月全量更新',
                'tasks': [
                    '汇总全月交易数据',
                    '全量更新客户指标',
                    '重新训练BG/NBD和Gamma-Gamma模型',
                    '重新划分客户群',
                    '生成月度分析报告'
                ]
            }
        }
        
        return schedules.get(update_frequency, schedules['daily'])
    
    def get_update_status(self):
        if len(self.update_history) == 0:
            return {
                'last_update': None,
                'model_version': self.model_version,
                'total_updates': 0,
                'status': '初始化'
            }
        
        last_update = self.update_history[-1]
        return {
            'last_update': last_update['timestamp'],
            'model_version': self.model_version,
            'total_updates': len(self.update_history),
            'last_update_type': last_update.get('update_type', 'incremental'),
            'status': '运行中'
        }
    
    def simulate_daily_updates(self, transactions_df, n_days=7):
        daily_results = {}
        base_date = datetime.now()
        
        for day in range(n_days):
            current_date = base_date - timedelta(days=day)
            date_mask = transactions_df['transaction_date'].dt.date == current_date.date()
            day_transactions = transactions_df[date_mask]
            
            if len(day_transactions) > 0:
                daily_results[current_date.strftime('%Y-%m-%d')] = {
                    'n_transactions': len(day_transactions),
                    'n_customers': day_transactions['customer_id'].nunique(),
                    'total_amount': day_transactions['amount'].sum()
                }
        
        return daily_results


if __name__ == '__main__':
    print("实时LTV更新模块已加载")
