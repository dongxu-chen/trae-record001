import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class DynamicThresholds:
    amount_high_quantile: float = 0.95
    amount_low_quantile: float = 0.05
    frequency_high_quantile: float = 0.90
    new_merchant_amount_quantile: float = 0.75
    unusual_hours: List[int] = field(default_factory=lambda: list(range(0, 6)) + list(range(23, 24)))
    unusual_hour_amount_threshold_quantile: float = 0.50

class AnomalyDetector:
    def __init__(self, use_dynamic_threshold: bool = True, default_quantile: float = 0.95):
        self.use_dynamic_threshold = use_dynamic_threshold
        self.default_quantile = default_quantile
        self.thresholds = DynamicThresholds()
        self.user_history_stats: Dict[str, Any] = {}
    
    def _calculate_dynamic_thresholds(self, df: pd.DataFrame) -> Dict[str, Any]:
        stats = {}
        
        all_amounts = df['amount'].dropna()
        if len(all_amounts) > 0:
            stats['global_amount_95'] = all_amounts.quantile(0.95)
            stats['global_amount_99'] = all_amounts.quantile(0.99)
            stats['global_amount_median'] = all_amounts.median()
            stats['global_amount_mean'] = all_amounts.mean()
            stats['global_amount_std'] = all_amounts.std()
        
        category_stats = {}
        for category, group in df.groupby('category'):
            amounts = group['amount'].dropna()
            if len(amounts) > 5:
                category_stats[category] = {
                    'quantile_90': amounts.quantile(0.90),
                    'quantile_95': amounts.quantile(0.95),
                    'quantile_99': amounts.quantile(0.99),
                    'median': amounts.median(),
                    'mean': amounts.mean(),
                    'std': amounts.std(),
                    'count': len(amounts)
                }
        stats['by_category'] = category_stats
        
        df['date_only'] = pd.to_datetime(df['date']).dt.date
        daily_counts = df.groupby('date_only').size()
        if len(daily_counts) > 7:
            stats['daily_count_90'] = daily_counts.quantile(0.90)
            stats['daily_count_95'] = daily_counts.quantile(0.95)
            stats['daily_count_mean'] = daily_counts.mean()
        
        if len(all_amounts) > 10:
            stats['new_merchant_threshold'] = all_amounts.quantile(0.75)
        else:
            stats['new_merchant_threshold'] = 1000
        
        if len(all_amounts) > 0:
            stats['unusual_hour_threshold'] = all_amounts.quantile(0.50)
        else:
            stats['unusual_hour_threshold'] = 200
        
        return stats
    
    def detect_anomalies(self, transactions: List[Dict]) -> List[Dict]:
        df = pd.DataFrame(transactions)
        if df.empty:
            return []
        
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df.get('time', '00:00:00'))
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        self.user_history_stats = self._calculate_dynamic_thresholds(df)
        
        anomalies = []
        
        amount_anomalies = self._detect_amount_anomalies(df)
        anomalies.extend(amount_anomalies)
        
        freq_anomalies = self._detect_frequency_anomalies(df)
        anomalies.extend(freq_anomalies)
        
        time_anomalies = self._detect_time_anomalies(df)
        anomalies.extend(time_anomalies)
        
        merchant_anomalies = self._detect_new_merchant_anomalies(df)
        anomalies.extend(merchant_anomalies)
        
        location_anomalies = self._detect_location_anomalies(df)
        anomalies.extend(location_anomalies)
        
        return self._merge_anomalies(anomalies, len(transactions))
    
    def _detect_amount_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        anomalies = []
        
        category_stats = self.user_history_stats.get('by_category', {})
        
        for category, group in df.groupby('category'):
            if len(group) < 5:
                continue
            
            cat_stat = category_stats.get(category)
            if cat_stat:
                threshold_95 = cat_stat['quantile_95']
                threshold_99 = cat_stat['quantile_99']
                median = cat_stat['median']
            else:
                threshold_95 = self.user_history_stats.get('global_amount_95', 1000)
                threshold_99 = self.user_history_stats.get('global_amount_99', 5000)
                median = self.user_history_stats.get('global_amount_median', 100)
            
            for _, row in group.iterrows():
                amount = row['amount']
                
                if amount > threshold_99:
                    severity = 'high'
                    threshold_used = '99分位数'
                    threshold_value = threshold_99
                elif amount > threshold_95:
                    severity = 'medium'
                    threshold_used = '95分位数'
                    threshold_value = threshold_95
                else:
                    continue
                
                anomalies.append({
                    'transaction_index': row.name,
                    'type': '异常金额',
                    'severity': severity,
                    'description': (
                        f"{category}类别下金额异常: {amount:.2f}元 "
                        f"(动态阈值{threshold_used}: {threshold_value:.2f}元, "
                        f"类别中位数: {median:.2f}元)"
                    ),
                    'category': category,
                    'merchant': row['merchant'],
                    'amount': amount,
                    'threshold_info': {
                        'type': 'quantile',
                        'value': threshold_value,
                        'quantile': 0.99 if severity == 'high' else 0.95
                    }
                })
        
        return anomalies
    
    def _detect_frequency_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        anomalies = []
        
        df['date_only'] = df['datetime'].dt.date
        
        daily_counts = df.groupby('date_only').size()
        
        if len(daily_counts) < 7:
            return anomalies
        
        threshold_90 = self.user_history_stats.get('daily_count_90', 10)
        threshold_95 = self.user_history_stats.get('daily_count_95', 15)
        mean_count = self.user_history_stats.get('daily_count_mean', 5)
        
        for date, count in daily_counts.items():
            if count > threshold_95:
                severity = 'high'
            elif count > threshold_90:
                severity = 'medium'
            else:
                continue
            
            day_transactions = df[df['date_only'] == date]
            for _, row in day_transactions.iterrows():
                anomalies.append({
                    'transaction_index': row.name,
                    'type': '高频消费',
                    'severity': severity,
                    'description': (
                        f"当日消费次数异常: {date} 共 {count} 笔 "
                        f"(动态95分位数阈值: {threshold_95:.0f}, "
                        f"日均: {mean_count:.1f})"
                    ),
                    'category': row['category'],
                    'merchant': row['merchant'],
                    'amount': row['amount'],
                    'threshold_info': {
                        'type': 'quantile',
                        'value': threshold_95,
                        'quantile': 0.95
                    }
                })
        
        return anomalies
    
    def _detect_time_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        anomalies = []
        
        df['hour'] = df['datetime'].dt.hour
        
        unusual_hours = self.thresholds.unusual_hours
        
        unusual_hour_threshold = self.user_history_stats.get('unusual_hour_threshold', 200)
        
        unusual_transactions = df[df['hour'].isin(unusual_hours)]
        
        for _, row in unusual_transactions.iterrows():
            amount = row['amount']
            
            if amount > unusual_hour_threshold:
                if amount > unusual_hour_threshold * 2:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                anomalies.append({
                    'transaction_index': row.name,
                    'type': '异常时段消费',
                    'severity': severity,
                    'description': (
                        f"深夜消费: {row['datetime'].strftime('%H:%M')} - {row['merchant']} "
                        f"({amount:.2f}元, 动态中位数阈值: {unusual_hour_threshold:.2f}元)"
                    ),
                    'category': row['category'],
                    'merchant': row['merchant'],
                    'amount': amount,
                    'threshold_info': {
                        'type': 'quantile',
                        'value': unusual_hour_threshold,
                        'quantile': 0.50
                    }
                })
        
        return anomalies
    
    def _detect_new_merchant_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        anomalies = []
        
        merchant_first_seen = {}
        df_sorted = df.sort_values('datetime')
        
        new_merchant_threshold = self.user_history_stats.get('new_merchant_threshold', 1000)
        
        for _, row in df_sorted.iterrows():
            merchant = row['merchant']
            amount = row['amount']
            
            if merchant not in merchant_first_seen:
                merchant_first_seen[merchant] = row['datetime']
                
                if amount > new_merchant_threshold:
                    if amount > new_merchant_threshold * 2:
                        severity = 'high'
                    else:
                        severity = 'medium'
                    
                    anomalies.append({
                        'transaction_index': row.name,
                        'type': '新商户大额消费',
                        'severity': severity,
                        'description': (
                            f"首次在新商户大额消费: {merchant} ({amount:.2f}元, "
                            f"动态75分位数阈值: {new_merchant_threshold:.2f}元)"
                        ),
                        'category': row['category'],
                        'merchant': merchant,
                        'amount': amount,
                        'threshold_info': {
                            'type': 'quantile',
                            'value': new_merchant_threshold,
                            'quantile': 0.75
                        }
                    })
        
        return anomalies
    
    def _detect_location_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        anomalies = []
        
        if 'location' not in df.columns:
            return anomalies
        
        df_sorted = df.sort_values('datetime')
        
        for i in range(1, len(df_sorted)):
            prev_row = df_sorted.iloc[i-1]
            curr_row = df_sorted.iloc[i]
            
            time_diff = (curr_row['datetime'] - prev_row['datetime']).total_seconds() / 3600
            
            if time_diff < 2 and prev_row.get('location') and curr_row.get('location'):
                prev_loc = prev_row['location']
                curr_loc = curr_row['location']
                
                if prev_loc != curr_loc:
                    anomalies.append({
                        'transaction_index': curr_row.name,
                        'type': '地理位置异常',
                        'severity': 'high',
                        'description': (
                            f"短时间内跨地域消费: {prev_loc} -> {curr_loc} "
                            f"({time_diff:.1f}小时内)"
                        ),
                        'category': curr_row['category'],
                        'merchant': curr_row['merchant'],
                        'amount': curr_row['amount'],
                        'threshold_info': {
                            'type': 'time_based',
                            'value': 2,
                            'unit': 'hours'
                        }
                    })
        
        return anomalies
    
    def _merge_anomalies(self, anomalies: List[Dict], total_transactions: int) -> List[Dict]:
        merged = defaultdict(list)
        
        for anomaly in anomalies:
            idx = anomaly.get('transaction_index', -1)
            merged[idx].append(anomaly)
        
        result = []
        for idx, anomaly_list in merged.items():
            if len(anomaly_list) > 1:
                combined = {
                    'transaction_index': idx,
                    'type': '多维度异常',
                    'severity': 'high',
                    'description': ' | '.join([a['description'] for a in anomaly_list]),
                    'category': anomaly_list[0]['category'],
                    'merchant': anomaly_list[0]['merchant'],
                    'amount': anomaly_list[0]['amount'],
                    'anomaly_count': len(anomaly_list)
                }
                result.append(combined)
            else:
                result.append(anomaly_list[0])
        
        result.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x['severity']])
        
        return result
    
    def get_threshold_summary(self) -> Dict[str, Any]:
        return {
            'use_dynamic_threshold': self.use_dynamic_threshold,
            'default_quantile': self.default_quantile,
            'calculated_stats': self.user_history_stats
        }
    
    def get_anomaly_summary(self, anomalies: List[Dict]) -> Dict:
        summary = {
            'total_anomalies': len(anomalies),
            'by_type': defaultdict(int),
            'by_severity': {'high': 0, 'medium': 0, 'low': 0},
            'high_risk_amount': 0.0,
            'threshold_used': {
                'amount_quantile': self.user_history_stats.get('global_amount_95'),
                'frequency_quantile': self.user_history_stats.get('daily_count_95'),
                'new_merchant_quantile': self.user_history_stats.get('new_merchant_threshold'),
                'unusual_hour_quantile': self.user_history_stats.get('unusual_hour_threshold')
            }
        }
        
        for anomaly in anomalies:
            summary['by_type'][anomaly['type']] += 1
            summary['by_severity'][anomaly['severity']] += 1
            if anomaly['severity'] == 'high':
                summary['high_risk_amount'] += anomaly.get('amount', 0)
        
        return dict(summary)
