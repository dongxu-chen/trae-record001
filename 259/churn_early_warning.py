import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ChurnEarlyWarningSystem:
    def __init__(self, segmented_df, feature_cols, coef_df):
        self.segmented_df = segmented_df.copy()
        self.feature_cols = feature_cols
        self.coef_df = coef_df
        self.risk_thresholds = {
            'high': 0.7,
            'medium': 0.4
        }
        
    def generate_warning_list(self, min_churn_prob=0.3, top_n=None, risk_group=None):
        df = self.segmented_df.copy()
        
        if risk_group:
            df = df[df['risk_group'] == risk_group]
        
        df = df[df['churn_prob_30d'] >= min_churn_prob]
        df = df.sort_values('churn_prob_30d', ascending=False)
        
        if top_n:
            df = df.head(top_n)
        
        df['warning_level'] = df['churn_prob_30d'].apply(
            lambda p: '🔴 高危' if p >= self.risk_thresholds['high'] 
            else '🟡 中危' if p >= self.risk_thresholds['medium'] 
            else '🟢 低危'
        )
        
        df['estimated_churn_date'] = df.apply(
            lambda row: self._estimate_churn_date(row), axis=1
        )
        
        df['days_to_churn'] = df['estimated_churn_date'].apply(
            lambda x: (x - datetime.now()).days
        )
        
        priority_features = self._get_priority_features(df)
        df = df.merge(priority_features, left_index=True, right_index=True, how='left')
        
        return df.reset_index()
    
    def _estimate_churn_date(self, row):
        churn_prob = row['churn_prob_30d']
        tenure = row['tenure_days'] if 'tenure_days' in row else 30
        
        hazard_rate = -np.log(1 - churn_prob) / 30
        expected_lifetime = 1 / hazard_rate
        
        estimated_days = min(max(int(expected_lifetime), 7), 180)
        churn_date = datetime.now() + timedelta(days=estimated_days)
        
        return churn_date
    
    def _get_priority_features(self, warning_df):
        risk_factors = self.coef_df[self.coef_df['coef'] > 0]['feature'].tolist()
        protective_factors = self.coef_df[self.coef_df['coef'] < 0]['feature'].tolist()
        
        priority_data = []
        
        for idx, row in warning_df.iterrows():
            user_features = {}
            
            high_risk_features = []
            for f in risk_factors[:5]:
                if f in self.feature_cols:
                    user_val = row[f]
                    overall_mean = self.segmented_df[f].mean()
                    if user_val > overall_mean:
                        high_risk_features.append(f"{f}(↑{(user_val/overall_mean-1)*100:.0f}%)")
            
            low_protective_features = []
            for f in protective_factors[:5]:
                if f in self.feature_cols:
                    user_val = row[f]
                    overall_mean = self.segmented_df[f].mean()
                    if user_val < overall_mean:
                        low_protective_features.append(f"{f}(↓{(1-user_val/overall_mean)*100:.0f}%)")
            
            user_features['high_risk_features'] = ', '.join(high_risk_features[:3]) if high_risk_features else '无'
            user_features['weak_protective_features'] = ', '.join(low_protective_features[:3]) if low_protective_features else '无'
            user_features['intervention_priority'] = min(len(high_risk_features) + len(low_protective_features), 5)
            
            priority_data.append(user_features)
        
        return pd.DataFrame(priority_data, index=warning_df.index)
    
    def generate_daily_report(self, warning_df):
        report = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_high_risk': len(warning_df[warning_df['warning_level'] == '🔴 高危']),
            'total_medium_risk': len(warning_df[warning_df['warning_level'] == '🟡 中危']),
            'total_low_risk': len(warning_df[warning_df['warning_level'] == '🟢 低危']),
            'avg_churn_prob_30d': warning_df['churn_prob_30d'].mean(),
            'avg_risk_score': warning_df['risk_score'].mean(),
            'top_risk_features': self._get_top_risk_features(warning_df, top_n=5)
        }
        
        report['total_warnings'] = report['total_high_risk'] + report['total_medium_risk'] + report['total_low_risk']
        
        return report
    
    def _get_top_risk_features(self, warning_df, top_n=5):
        risk_factors = self.coef_df[self.coef_df['coef'] > 0].head(top_n)
        
        feature_stats = []
        for _, row in risk_factors.iterrows():
            feature = row['feature']
            if feature in warning_df.columns:
                avg_val = warning_df[feature].mean()
                overall_avg = self.segmented_df[feature].mean()
                feature_stats.append({
                    'feature': feature,
                    'hazard_ratio': row['hazard_ratio'],
                    'avg_in_warning': avg_val,
                    'overall_avg': overall_avg,
                    'deviation_pct': (avg_val / overall_avg - 1) * 100 if overall_avg != 0 else 0
                })
        
        return pd.DataFrame(feature_stats)
    
    def export_for_push(self, warning_df, platform='email'):
        if platform == 'email':
            export_cols = ['user_id', 'warning_level', 'churn_prob_30d', 'churn_prob_90d', 
                          'risk_score', 'days_to_churn', 'high_risk_features', 'weak_protective_features']
            export_cols = [c for c in export_cols if c in warning_df.columns]
            return warning_df[export_cols]
        
        elif platform == 'sms':
            sms_df = warning_df[['user_id', 'warning_level', 'churn_prob_30d', 'days_to_churn']].copy()
            sms_df['message'] = sms_df.apply(
                lambda row: f"【流失预警】用户{row['user_id']}30天流失概率{row['churn_prob_30d']:.1%}，预计{row['days_to_churn']}天内流失",
                axis=1
            )
            return sms_df
        
        elif platform == 'webhook':
            webhook_data = []
            for _, row in warning_df.iterrows():
                webhook_data.append({
                    'user_id': row['user_id'],
                    'warning_level': row['warning_level'],
                    'churn_prob_30d': float(row['churn_prob_30d']),
                    'churn_prob_90d': float(row['churn_prob_90d']),
                    'risk_score': float(row['risk_score']),
                    'days_to_churn': int(row['days_to_churn']),
                    'timestamp': datetime.now().isoformat()
                })
            return webhook_data
        
        else:
            return warning_df
    
    def get_risk_trend(self, days=30):
        dates = [datetime.now() - timedelta(days=i) for i in range(days, 0, -1)]
        
        trend_data = []
        for date in dates:
            simulated_high = np.random.randint(50, 150)
            simulated_medium = np.random.randint(100, 300)
            simulated_low = np.random.randint(200, 500)
            
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'high_risk': simulated_high,
                'medium_risk': simulated_medium,
                'low_risk': simulated_low,
                'total': simulated_high + simulated_medium + simulated_low
            })
        
        return pd.DataFrame(trend_data)
    
    def calculate_cost_benefit(self, warning_df, intervention_cost_per_user=50, retention_value=500):
        high_risk = warning_df[warning_df['warning_level'] == '🔴 高危']
        medium_risk = warning_df[warning_df['warning_level'] == '🟡 中危']
        
        intervention_rate_high = 0.6
        intervention_rate_medium = 0.3
        
        users_saved_high = len(high_risk) * intervention_rate_high * high_risk['churn_prob_30d'].mean()
        users_saved_medium = len(medium_risk) * intervention_rate_medium * medium_risk['churn_prob_30d'].mean()
        total_users_saved = users_saved_high + users_saved_medium
        
        total_intervention_cost = (len(high_risk) + len(medium_risk)) * intervention_cost_per_user
        total_revenue_saved = total_users_saved * retention_value
        roi = (total_revenue_saved - total_intervention_cost) / total_intervention_cost if total_intervention_cost > 0 else float('inf')
        
        return {
            'users_to_intervene': len(high_risk) + len(medium_risk),
            'estimated_users_saved': total_users_saved,
            'intervention_cost': total_intervention_cost,
            'revenue_saved': total_revenue_saved,
            'roi': roi,
            'roi_multiple': f"{roi:.1f}x" if roi != float('inf') else "∞"
        }
