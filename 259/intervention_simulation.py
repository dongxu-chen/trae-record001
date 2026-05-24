import pandas as pd
import numpy as np

class InterventionSimulator:
    def __init__(self, analyzer, df, feature_cols):
        self.analyzer = analyzer
        self.df = df
        self.feature_cols = feature_cols
        self.feature_stats = self._calculate_feature_stats()
        
    def _calculate_feature_stats(self):
        stats = {}
        for col in self.feature_cols:
            stats[col] = {
                'min': self.df[col].min(),
                'max': self.df[col].max(),
                'mean': self.df[col].mean(),
                'median': self.df[col].median(),
                'std': self.df[col].std(),
                'p25': self.df[col].quantile(0.25),
                'p75': self.df[col].quantile(0.75)
            }
        return stats
    
    def get_risk_factors(self, coef_df, top_n=10):
        risk_factors = coef_df[coef_df['coef'] > 0].copy()
        risk_factors = risk_factors.sort_values('coef', ascending=False)
        return risk_factors.head(top_n)
    
    def get_protective_factors(self, coef_df, top_n=10):
        protective_factors = coef_df[coef_df['coef'] < 0].copy()
        protective_factors = protective_factors.sort_values('coef', ascending=True)
        return protective_factors.head(top_n)
    
    def simulate_intervention(self, user_idx, feature_name, adjustment_value, adjustment_type='absolute'):
        if user_idx not in self.df.index:
            user_idx = self.df.index[user_idx]
        
        original_row = self.df.loc[user_idx].copy()
        modified_row = original_row.copy()
        
        if adjustment_type == 'absolute':
            modified_row[feature_name] += adjustment_value
        elif adjustment_type == 'percentage':
            modified_row[feature_name] *= (1 + adjustment_value / 100)
        elif adjustment_type == 'set_value':
            modified_row[feature_name] = adjustment_value
        
        feature_min = self.feature_stats[feature_name]['min']
        feature_max = self.feature_stats[feature_name]['max']
        modified_row[feature_name] = np.clip(modified_row[feature_name], feature_min, feature_max)
        
        original_df = pd.DataFrame([original_row[self.feature_cols]])
        modified_df = pd.DataFrame([modified_row[self.feature_cols]])
        
        original_risk = self.analyzer.predict_risk_scores(original_df).values[0]
        modified_risk = self.analyzer.predict_risk_scores(modified_df).values[0]
        
        original_surv = self.analyzer.predict_survival_function(original_df)
        modified_surv = self.analyzer.predict_survival_function(modified_df)
        
        times = original_surv.index.values
        
        original_churn_30 = 1 - original_surv.iloc[min(29, len(original_surv)-1)].values[0]
        modified_churn_30 = 1 - modified_surv.iloc[min(29, len(modified_surv)-1)].values[0]
        
        original_churn_90 = 1 - original_surv.iloc[min(89, len(original_surv)-1)].values[0]
        modified_churn_90 = 1 - modified_surv.iloc[min(89, len(modified_surv)-1)].values[0]
        
        result = {
            'user_id': user_idx,
            'feature': feature_name,
            'original_value': original_row[feature_name],
            'modified_value': modified_row[feature_name],
            'adjustment': adjustment_value,
            'adjustment_type': adjustment_type,
            'original_risk_score': original_risk,
            'modified_risk_score': modified_risk,
            'risk_change': modified_risk - original_risk,
            'risk_change_pct': (modified_risk - original_risk) / original_risk * 100 if original_risk != 0 else 0,
            'original_churn_30d': original_churn_30,
            'modified_churn_30d': modified_churn_30,
            'churn_reduction_30d': original_churn_30 - modified_churn_30,
            'original_churn_90d': original_churn_90,
            'modified_churn_90d': modified_churn_90,
            'churn_reduction_90d': original_churn_90 - modified_churn_90,
            'times': times,
            'original_survival': original_surv.values.flatten(),
            'modified_survival': modified_surv.values.flatten()
        }
        
        return result
    
    def simulate_bulk_intervention(self, user_indices, feature_name, adjustment_value, adjustment_type='absolute'):
        results = []
        for idx in user_indices:
            result = self.simulate_intervention(idx, feature_name, adjustment_value, adjustment_type)
            results.append(result)
        return pd.DataFrame(results)
    
    def find_optimal_intervention(self, user_idx, coef_df, budget_constraint=None):
        risk_factors = self.get_risk_factors(coef_df)
        protective_factors = self.get_protective_factors(coef_df)
        
        intervention_options = []
        
        for _, row in risk_factors.iterrows():
            feature = row['feature']
            coef = row['coef']
            
            current_val = self.df.loc[user_idx, feature]
            mean_val = self.feature_stats[feature]['mean']
            p25_val = self.feature_stats[feature]['p25']
            
            if current_val > p25_val:
                target_val = p25_val
                adjustment = target_val - current_val
                
                result = self.simulate_intervention(user_idx, feature, target_val, 'set_value')
                intervention_options.append({
                    'feature': feature,
                    'intervention_type': '降低风险因素',
                    'current_value': current_val,
                    'target_value': target_val,
                    'adjustment': adjustment,
                    'churn_reduction_30d': result['churn_reduction_30d'],
                    'churn_reduction_90d': result['churn_reduction_90d'],
                    'risk_reduction': result['risk_change_pct'],
                    'coefficient': coef
                })
        
        for _, row in protective_factors.iterrows():
            feature = row['feature']
            coef = row['coef']
            
            current_val = self.df.loc[user_idx, feature]
            mean_val = self.feature_stats[feature]['mean']
            p75_val = self.feature_stats[feature]['p75']
            
            if current_val < p75_val:
                target_val = p75_val
                adjustment = target_val - current_val
                
                result = self.simulate_intervention(user_idx, feature, target_val, 'set_value')
                intervention_options.append({
                    'feature': feature,
                    'intervention_type': '提升保护因素',
                    'current_value': current_val,
                    'target_value': target_val,
                    'adjustment': adjustment,
                    'churn_reduction_30d': result['churn_reduction_30d'],
                    'churn_reduction_90d': result['churn_reduction_90d'],
                    'risk_reduction': result['risk_change_pct'],
                    'coefficient': coef
                })
        
        options_df = pd.DataFrame(intervention_options)
        if not options_df.empty:
            options_df = options_df.sort_values('churn_reduction_30d', ascending=False)
        
        return options_df
    
    def calculate_roi(self, intervention_result, acquisition_cost, retention_value):
        churn_reduction = intervention_result['churn_reduction_30d']
        users_saved = churn_reduction
        revenue_gain = users_saved * retention_value
        roi = (revenue_gain - acquisition_cost) / acquisition_cost if acquisition_cost > 0 else float('inf')
        
        return {
            'churn_reduction': churn_reduction,
            'users_saved': users_saved,
            'revenue_gain': revenue_gain,
            'acquisition_cost': acquisition_cost,
            'roi': roi,
            'payback_period': acquisition_cost / (revenue_gain / 12) if revenue_gain > 0 else float('inf')
        }
