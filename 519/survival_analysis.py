import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test
import warnings
warnings.filterwarnings('ignore')


class SurvivalAnalyzer:
    def __init__(self):
        self.kmf = KaplanMeierFitter()
        self.cph = CoxPHFitter()
        self.category_churn_thresholds = {}
        self.category_inter_purchase_medians = {}
        
    def calculate_category_medians(self, purchases_df):
        purchases_df = purchases_df.copy()
        purchases_df['purchase_date'] = pd.to_datetime(purchases_df['purchase_date'])
        
        purchases_sorted = purchases_df.sort_values(['customer_id', 'product_category', 'purchase_date'])
        purchases_sorted['prev_purchase'] = purchases_sorted.groupby(
            ['customer_id', 'product_category']
        )['purchase_date'].shift(1)
        purchases_sorted['inter_purchase_days'] = (
            purchases_sorted['purchase_date'] - purchases_sorted['prev_purchase']
        ).dt.days
        
        category_stats = purchases_sorted.dropna(subset=['inter_purchase_days']).groupby(
            'product_category'
        )['inter_purchase_days'].agg(['median', 'mean', 'std', 'count']).reset_index()
        
        category_stats.columns = [
            'product_category', 'median_inter_purchase', 
            'mean_inter_purchase', 'std_inter_purchase', 'purchase_count'
        ]
        
        for _, row in category_stats.iterrows():
            category = row['product_category']
            median_days = row['median_inter_purchase']
            std_days = row['std_inter_purchase']
            
            churn_threshold = median_days + 2 * std_days
            churn_threshold = max(churn_threshold, median_days * 1.5)
            
            self.category_inter_purchase_medians[category] = median_days
            self.category_churn_thresholds[category] = churn_threshold
        
        return category_stats
    
    def prepare_survival_data(self, purchases_df, profiles_df, end_date=None):
        if end_date is None:
            end_date = pd.to_datetime('2025-12-31')
        
        purchases_df = purchases_df.copy()
        purchases_df['purchase_date'] = pd.to_datetime(purchases_df['purchase_date'])
        
        category_stats = self.calculate_category_medians(purchases_df)
        
        customer_category_metrics = purchases_df.groupby(
            ['customer_id', 'product_category']
        ).agg(
            first_purchase=('purchase_date', 'min'),
            last_purchase=('purchase_date', 'max'),
            total_purchases=('purchase_date', 'count'),
            total_spend=('purchase_amount', 'sum'),
            avg_discount_pct=('discount_pct', 'mean'),
            promotion_rate=('is_promotion', 'mean'),
            avg_base_price=('base_price', 'mean')
        ).reset_index()
        
        customer_category_metrics = customer_category_metrics.merge(
            category_stats, on='product_category', how='left'
        )
        
        customer_category_metrics['category_churn_threshold'] = customer_category_metrics[
            'product_category'
        ].map(self.category_churn_thresholds)
        
        observation_end = end_date
        customer_category_metrics['days_since_last'] = (
            observation_end - customer_category_metrics['last_purchase']
        ).dt.days
        
        customer_category_metrics['churned'] = (
            customer_category_metrics['days_since_last'] > 
            customer_category_metrics['category_churn_threshold']
        ).astype(int)
        
        customer_category_metrics['duration_days'] = (
            observation_end - customer_category_metrics['first_purchase']
        ).dt.days
        
        overall_metrics = self._calculate_overall_metrics(
            purchases_df, profiles_df, customer_category_metrics, end_date
        )
        
        return overall_metrics, customer_category_metrics, category_stats
    
    def _calculate_overall_metrics(self, purchases_df, profiles_df, category_metrics, end_date):
        customer_metrics = purchases_df.groupby('customer_id').agg(
            first_purchase=('purchase_date', 'min'),
            last_purchase=('purchase_date', 'max'),
            total_purchases=('purchase_date', 'count'),
            total_spend=('purchase_amount', 'sum'),
            avg_order_value=('purchase_amount', 'mean'),
            avg_discount_pct=('discount_pct', 'mean'),
            promotion_rate=('is_promotion', 'mean'),
            avg_base_price=('base_price', 'mean')
        ).reset_index()
        
        customer_metrics = customer_metrics.merge(profiles_df, on='customer_id', how='left')
        
        observation_end = end_date
        customer_metrics['duration_days'] = (observation_end - customer_metrics['first_purchase']).dt.days
        customer_metrics['days_since_last'] = (observation_end - customer_metrics['last_purchase']).dt.days
        
        user_categories = category_metrics.groupby('customer_id').agg(
            active_categories=('product_category', 'nunique'),
            primary_category=('product_category', lambda x: x.value_counts().index[0]),
            avg_category_threshold=('category_churn_threshold', 'mean'),
            max_category_threshold=('category_churn_threshold', 'max'),
            weighted_churn_threshold=('category_churn_threshold', lambda x: x.mean())
        ).reset_index()
        
        customer_metrics = customer_metrics.merge(user_categories, on='customer_id', how='left')
        
        primary_thresholds = category_metrics[
            category_metrics.groupby('customer_id')['total_purchases'].transform('max') == 
            category_metrics['total_purchases']
        ][['customer_id', 'product_category', 'category_churn_threshold']].drop_duplicates('customer_id')
        primary_thresholds.columns = ['customer_id', 'primary_category', 'primary_churn_threshold']
        
        customer_metrics = customer_metrics.merge(
            primary_thresholds[['customer_id', 'primary_churn_threshold']], 
            on='customer_id', how='left'
        )
        
        customer_metrics['dynamic_churn_threshold'] = customer_metrics['primary_churn_threshold'].fillna(
            customer_metrics['avg_category_threshold']
        )
        
        customer_metrics['churned'] = (
            customer_metrics['days_since_last'] > customer_metrics['dynamic_churn_threshold']
        ).astype(int)
        
        avg_inter_purchase = self._calculate_inter_purchase_time(purchases_df)
        customer_metrics = customer_metrics.merge(avg_inter_purchase, on='customer_id', how='left')
        
        customer_metrics['time_to_next_purchase'] = customer_metrics['avg_inter_purchase_days']
        
        customer_metrics['repurchase_rate'] = customer_metrics['total_purchases'].apply(
            lambda x: 1 if x > 1 else 0
        )
        
        return customer_metrics
    
    def _calculate_inter_purchase_time(self, purchases_df):
        purchases_sorted = purchases_df.sort_values(['customer_id', 'purchase_date'])
        purchases_sorted['prev_purchase'] = purchases_sorted.groupby('customer_id')['purchase_date'].shift(1)
        purchases_sorted['inter_purchase_days'] = (purchases_sorted['purchase_date'] - purchases_sorted['prev_purchase']).dt.days
        
        avg_inter_purchase = purchases_sorted.groupby('customer_id')['inter_purchase_days'].mean().reset_index()
        avg_inter_purchase.columns = ['customer_id', 'avg_inter_purchase_days']
        
        return avg_inter_purchase
    
    def kaplan_meier_analysis(self, survival_data, group_col=None):
        results = {}
        
        if group_col is None:
            self.kmf.fit(survival_data['duration_days'], event_observed=survival_data['churned'])
            results['overall'] = {
                'survival_function': self.kmf.survival_function_,
                'median_survival_time': self.kmf.median_survival_time_,
                'confidence_interval': self.kmf.confidence_interval_
            }
        else:
            groups = survival_data[group_col].unique()
            results['groups'] = {}
            
            for group in groups:
                group_data = survival_data[survival_data[group_col] == group]
                if len(group_data) > 0:
                    kmf_group = KaplanMeierFitter()
                    kmf_group.fit(group_data['duration_days'], event_observed=group_data['churned'], label=str(group))
                    results['groups'][str(group)] = {
                        'survival_function': kmf_group.survival_function_,
                        'median_survival_time': kmf_group.median_survival_time_,
                        'confidence_interval': kmf_group.confidence_interval_,
                        'fitter': kmf_group
                    }
            
            if len(groups) >= 2:
                results['logrank_test'] = self._pairwise_logrank_test(survival_data, group_col)
        
        return results
    
    def _pairwise_logrank_test(self, survival_data, group_col):
        groups = survival_data[group_col].unique()
        results = []
        
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                group1_data = survival_data[survival_data[group_col] == groups[i]]
                group2_data = survival_data[survival_data[group_col] == groups[j]]
                
                if len(group1_data) > 0 and len(group2_data) > 0:
                    result = logrank_test(
                        group1_data['duration_days'], group2_data['duration_days'],
                        group1_data['churned'], group2_data['churned']
                    )
                    results.append({
                        'group1': str(groups[i]),
                        'group2': str(groups[j]),
                        'p_value': result.p_value,
                        'test_statistic': result.test_statistic,
                        'significant': result.p_value < 0.05
                    })
        
        return pd.DataFrame(results)
    
    def prepare_cox_data(self, survival_data):
        cox_data = survival_data.copy()
        
        cox_data['duration'] = cox_data['duration_days']
        cox_data['event'] = cox_data['churned']
        
        cox_data['is_female'] = (cox_data['gender'] == 'Female').astype(int)
        cox_data['is_hybrid_channel'] = (cox_data['channel'] == 'Hybrid').astype(int)
        cox_data['is_online_channel'] = (cox_data['channel'] == 'Online').astype(int)
        
        segment_dummies = pd.get_dummies(cox_data['segment'], prefix='segment', drop_first=True)
        cox_data = pd.concat([cox_data, segment_dummies], axis=1)
        
        region_dummies = pd.get_dummies(cox_data['region'], prefix='region', drop_first=True)
        cox_data = pd.concat([cox_data, region_dummies], axis=1)
        
        feature_cols = [
            'duration', 'event', 'age', 'total_purchases', 'total_spend', 
            'avg_order_value', 'loyalty_tendency', 'is_female', 
            'is_hybrid_channel', 'is_online_channel',
            'price_sensitivity', 'promotion_responsiveness',
            'avg_discount_pct', 'promotion_rate', 'avg_base_price',
            'active_categories', 'dynamic_churn_threshold'
        ]
        feature_cols += [col for col in cox_data.columns if col.startswith('segment_') or col.startswith('region_')]
        
        return cox_data[feature_cols]
    
    def cox_proportional_hazards(self, cox_data):
        feature_cols = [col for col in cox_data.columns if col not in ['duration', 'event']]
        
        try:
            self.cph.fit(cox_data, duration_col='duration', event_col='event')
            
            results = {
                'model_summary': self.cph.summary,
                'hazard_ratios': np.exp(self.cph.params_),
                'concordance_index': self.cph.concordance_index_,
                'aic': self.cph.AIC_,
                'params': self.cph.params_,
                'standard_errors': self.cph.standard_errors_,
                'converged': True
            }
            
            return results
        except Exception as e:
            print(f"  Cox model convergence issue, trying with reduced features...")
            
            core_features = ['age', 'total_purchases', 'total_spend', 'loyalty_tendency', 
                             'price_sensitivity', 'promotion_responsiveness']
            core_features = [f for f in core_features if f in cox_data.columns]
            
            reduced_cols = ['duration', 'event'] + core_features
            reduced_data = cox_data[reduced_cols].copy()
            
            try:
                self.cph.fit(reduced_data, duration_col='duration', event_col='event')
                
                results = {
                    'model_summary': self.cph.summary,
                    'hazard_ratios': np.exp(self.cph.params_),
                    'concordance_index': self.cph.concordance_index_,
                    'aic': self.cph.AIC_,
                    'params': self.cph.params_,
                    'standard_errors': self.cph.standard_errors_,
                    'converged': True,
                    'used_reduced_features': True
                }
                
                return results
            except Exception as e2:
                print(f"  Cox model still failing, returning baseline results...")
                
                simple_results = {
                    'model_summary': pd.DataFrame(),
                    'hazard_ratios': pd.Series(dtype=float),
                    'concordance_index': 0.5,
                    'aic': None,
                    'params': pd.Series(dtype=float),
                    'standard_errors': pd.Series(dtype=float),
                    'converged': False,
                    'error': str(e)
                }
                
                return simple_results
    
    def predict_survival(self, customer_data, time_points):
        survival_curves = self.cph.predict_survival_function(customer_data, times=time_points)
        return survival_curves
    
    def calculate_repurchase_probability(self, customer_metrics, purchases_df):
        purchases_sorted = purchases_df.sort_values(['customer_id', 'purchase_date'])
        purchases_sorted['prev_purchase'] = purchases_sorted.groupby('customer_id')['purchase_date'].shift(1)
        purchases_sorted['inter_purchase_days'] = (purchases_sorted['purchase_date'] - purchases_sorted['prev_purchase']).dt.days
        
        inter_purchase_times = purchases_sorted.dropna(subset=['inter_purchase_days'])
        
        overall_mean = inter_purchase_times['inter_purchase_days'].mean()
        overall_std = inter_purchase_times['inter_purchase_days'].std()
        
        customer_metrics['expected_next_purchase_days'] = customer_metrics['avg_inter_purchase_days'].fillna(overall_mean)
        
        today = pd.to_datetime('2025-12-31')
        customer_metrics['days_since_last'] = (today - customer_metrics['last_purchase']).dt.days
        
        from scipy.stats import norm
        
        def calc_prob(row):
            if pd.isna(row['avg_inter_purchase_days']):
                z = (row['days_since_last'] - overall_mean) / overall_std
            else:
                z = (row['days_since_last'] - row['avg_inter_purchase_days']) / overall_std
            prob = 1 - norm.cdf(z)
            return max(0, min(1, prob))
        
        customer_metrics['repurchase_probability'] = customer_metrics.apply(calc_prob, axis=1)
        
        return customer_metrics
    
    def run_full_survival_analysis(self, purchases_df, profiles_df):
        print("Preparing survival data with category-based thresholds...")
        survival_data, category_survival_data, category_stats = self.prepare_survival_data(
            purchases_df, profiles_df
        )
        
        print("Running overall Kaplan-Meier analysis...")
        km_results = self.kaplan_meier_analysis(survival_data)
        
        print("Running segment-wise Kaplan-Meier...")
        km_segment = self.kaplan_meier_analysis(survival_data, group_col='segment')
        
        print("Running channel-wise Kaplan-Meier...")
        km_channel = self.kaplan_meier_analysis(survival_data, group_col='channel')
        
        print("Running category-wise Kaplan-Meier...")
        km_category = self.kaplan_meier_analysis(category_survival_data, group_col='product_category')
        
        print("Running churn threshold group analysis...")
        thresholds = survival_data['dynamic_churn_threshold']
        q25 = thresholds.quantile(0.33)
        q75 = thresholds.quantile(0.67)
        
        def assign_group(x):
            if x <= q25:
                return 'Short Cycle'
            elif x <= q75:
                return 'Medium Cycle'
            else:
                return 'Long Cycle'
        
        survival_data['threshold_group'] = survival_data['dynamic_churn_threshold'].apply(assign_group)
        km_threshold = self.kaplan_meier_analysis(survival_data, group_col='threshold_group')
        
        print("Preparing Cox PH data with price and promotion features...")
        cox_data = self.prepare_cox_data(survival_data)
        
        print("Running Cox Proportional Hazards...")
        cox_results = self.cox_proportional_hazards(cox_data)
        
        print("Calculating repurchase probabilities...")
        survival_data = self.calculate_repurchase_probability(survival_data, purchases_df)
        
        print("Calculating category-level repurchase probabilities...")
        category_repurchase = self._calculate_category_repurchase(
            category_survival_data, purchases_df
        )
        
        return {
            'survival_data': survival_data,
            'category_survival_data': category_survival_data,
            'category_stats': category_stats,
            'category_churn_thresholds': self.category_churn_thresholds,
            'category_inter_purchase_medians': self.category_inter_purchase_medians,
            'km_overall': km_results,
            'km_segment': km_segment,
            'km_channel': km_channel,
            'km_category': km_category,
            'km_threshold': km_threshold,
            'cox_results': cox_results,
            'category_repurchase': category_repurchase
        }
    
    def _calculate_category_repurchase(self, category_survival_data, purchases_df):
        purchases_sorted = purchases_df.sort_values(['customer_id', 'product_category', 'purchase_date'])
        purchases_sorted['prev_purchase'] = purchases_sorted.groupby(
            ['customer_id', 'product_category']
        )['purchase_date'].shift(1)
        purchases_sorted['inter_purchase_days'] = (
            purchases_sorted['purchase_date'] - purchases_sorted['prev_purchase']
        ).dt.days
        
        inter_purchase_times = purchases_sorted.dropna(subset=['inter_purchase_days'])
        
        category_stats = inter_purchase_times.groupby('product_category')['inter_purchase_days'].agg(
            ['mean', 'std']
        ).to_dict('index')
        
        from scipy.stats import norm
        
        today = pd.to_datetime('2025-12-31')
        
        def calc_category_prob(row):
            cat = row['product_category']
            if cat in category_stats:
                mean_days = category_stats[cat]['mean']
                std_days = category_stats[cat]['std']
                if std_days > 0:
                    z = (row['days_since_last'] - mean_days) / std_days
                    prob = 1 - norm.cdf(z)
                    return max(0, min(1, prob))
            return 0.5
        
        category_survival_data['category_repurchase_prob'] = category_survival_data.apply(
            calc_category_prob, axis=1
        )
        
        return category_survival_data
