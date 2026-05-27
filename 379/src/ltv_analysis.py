import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture


class LTVAnalyzer:
    def __init__(self, bg_nbd_model, gamma_gamma_model):
        self.bg_nbd = bg_nbd_model
        self.gamma_gamma = gamma_gamma_model
        self.scaler = StandardScaler()
        self.kmeans = None
        self.segment_labels = None
        self.segment_thresholds = None
    
    def calculate_ltv(self, data, future_months=12, discount_rate=0.01, with_ci=False, 
                      churn_threshold=0.3, include_reactivation=True):
        prob_alive = self.bg_nbd.calculate_probability_alive(data)
        predicted_avg_amount = self.gamma_gamma.predict_expected_average_profit(data)
        
        if include_reactivation:
            reactivation_data = self.bg_nbd.predict_reactivated_purchases(
                data, future_months, churn_threshold
            )
            predicted_purchases = reactivation_data['adjusted_purchases'].values
            reactivation_prob = reactivation_data['reactivation_prob'].values
            is_churned = reactivation_data['is_churned'].values
        else:
            predicted_purchases = self.bg_nbd.predict_purchases(data, future_months).values
            reactivation_prob = np.ones(len(data))
            is_churned = prob_alive < churn_threshold
        
        ltv = predicted_purchases * predicted_avg_amount
        
        if with_ci:
            purchase_predictions_ci = self.bg_nbd.predict_purchases_with_ci(data, future_months)
            profit_predictions_ci = self.gamma_gamma.predict_expected_profit_with_ci(data)
            
            n_samples = 1000
            clv_samples = []
            bg_params = self.bg_nbd.model._unload_params()
            gg_params = self.gamma_gamma.model._unload_params()
            
            r, alpha, a, b = bg_params
            p, q, v = gg_params
            
            days = future_months * 30
            
            for _ in range(n_samples):
                r_s = np.random.gamma(r, 1)
                alpha_s = np.random.gamma(alpha, 1)
                a_s = np.random.gamma(a, 1)
                b_s = np.random.gamma(b, 1)
                
                from lifetimes import BetaGeoFitter
                bg_temp = BetaGeoFitter()
                bg_temp.params_ = {'r': r_s, 'alpha': alpha_s, 'a': a_s, 'b': b_s}
                
                p_s = np.random.gamma(p, 1)
                q_s = np.random.gamma(q, 1)
                v_s = np.random.gamma(v, 1)
                
                from lifetimes import GammaGammaFitter
                gg_temp = GammaGammaFitter()
                gg_temp.params_ = {'p': p_s, 'q': q_s, 'v': v_s}
                
                clv_sample = gg_temp.customer_lifetime_value(
                    bg_temp,
                    data[self.bg_nbd.frequency_col],
                    data[self.bg_nbd.recency_col],
                    data[self.bg_nbd.age_col],
                    data[self.gamma_gamma.amount_col],
                    time=future_months,
                    discount_rate=discount_rate,
                    freq='D'
                )
                clv_samples.append(clv_sample)
            
            clv_samples = np.array(clv_samples)
            clv_lower = np.percentile(clv_samples, 5, axis=0)
            clv_upper = np.percentile(clv_samples, 95, axis=0)
            
            result = pd.DataFrame({
                'customer_id': data['customer_id'].values if 'customer_id' in data.columns else data.index,
                'ltv': ltv,
                'ltv_lower': clv_lower,
                'ltv_upper': clv_upper,
                'predicted_purchases': predicted_purchases,
                'predicted_avg_amount': predicted_avg_amount.values,
                'probability_alive': prob_alive.values,
                'reactivation_prob': reactivation_prob,
                'is_churned': is_churned
            }, index=data.index)
        else:
            result = pd.DataFrame({
                'customer_id': data['customer_id'].values if 'customer_id' in data.columns else data.index,
                'ltv': ltv,
                'predicted_purchases': predicted_purchases,
                'predicted_avg_amount': predicted_avg_amount.values,
                'probability_alive': prob_alive.values,
                'reactivation_prob': reactivation_prob,
                'is_churned': is_churned
            }, index=data.index)
        
        return result
    
    def calculate_ltv_quantiles(self, ltv_data, quantiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]):
        ltv_values = ltv_data['ltv']
        
        quantile_values = ltv_values.quantile(quantiles)
        
        quantile_df = pd.DataFrame({
            'quantile': [f'{int(q * 100)}%' for q in quantiles],
            'ltv_value': quantile_values.values
        })
        
        return quantile_df
    
    def segment_customers(self, data, ltv_data, n_segments=4, method='kmeans', 
                          thresholds=None, segment_names=None):
        if thresholds is not None:
            return self._segment_by_thresholds(data, ltv_data, thresholds, segment_names)
        else:
            return self._segment_by_clustering(data, ltv_data, n_segments, method)
    
    def _segment_by_thresholds(self, data, ltv_data, thresholds, segment_names=None):
        if segment_names is None:
            segment_names = ['低价值客户', '中价值客户', '高价值客户']
        
        if len(thresholds) != len(segment_names) - 1:
            raise ValueError(f"阈值数量应为 {len(segment_names) - 1} 个")
        
        ltv_values = ltv_data['ltv'].values
        labels = np.zeros(len(ltv_values), dtype=int)
        
        for i, threshold in enumerate(thresholds):
            labels[ltv_values >= threshold] = i + 1
        
        ltv_data['segment'] = labels
        
        self.segment_thresholds = thresholds
        
        segment_stats = ltv_data.groupby('segment').agg({
            'ltv': ['mean', 'median', 'count'],
            'predicted_purchases': 'mean',
            'predicted_avg_amount': 'mean',
            'probability_alive': 'mean',
            'reactivation_prob': 'mean',
            'is_churned': 'mean'
        }).reset_index()
        
        segment_stats.columns = ['segment', 'ltv_mean', 'ltv_median', 'customer_count',
                                 'avg_purchases', 'avg_amount', 'avg_prob_alive',
                                 'avg_reactivation_prob', 'churn_rate']
        
        segment_stats = segment_stats.sort_values('ltv_mean', ascending=False).reset_index(drop=True)
        segment_stats['segment_name'] = list(reversed(segment_names))[:len(segment_stats)]
        
        return ltv_data, segment_stats
    
    def _segment_by_clustering(self, data, ltv_data, n_segments=4, method='kmeans'):
        features = pd.DataFrame({
            'ltv': ltv_data['ltv'].values,
            'frequency': data[self.bg_nbd.frequency_col].values,
            'recency': data[self.bg_nbd.recency_col].values,
            'avg_amount': data[self.gamma_gamma.amount_col].values,
            'probability_alive': ltv_data['probability_alive'].values
        })
        
        features_scaled = self.scaler.fit_transform(features)
        
        if method == 'kmeans':
            self.kmeans = KMeans(n_clusters=n_segments, random_state=42, n_init=10)
            labels = self.kmeans.fit_predict(features_scaled)
        elif method == 'gmm':
            gmm = GaussianMixture(n_components=n_segments, random_state=42)
            labels = gmm.fit_predict(features_scaled)
        else:
            raise ValueError(f"不支持的聚类方法: {method}")
        
        ltv_data['segment'] = labels
        
        segment_stats = ltv_data.groupby('segment').agg({
            'ltv': ['mean', 'median', 'count'],
            'predicted_purchases': 'mean',
            'predicted_avg_amount': 'mean',
            'probability_alive': 'mean',
            'reactivation_prob': 'mean',
            'is_churned': 'mean'
        }).reset_index()
        
        segment_stats.columns = ['segment', 'ltv_mean', 'ltv_median', 'customer_count',
                                 'avg_purchases', 'avg_amount', 'avg_prob_alive',
                                 'avg_reactivation_prob', 'churn_rate']
        
        segment_stats = segment_stats.sort_values('ltv_mean', ascending=False).reset_index(drop=True)
        
        default_names = ['高价值客户', '中高价值客户', '中价值客户', '中低价值客户', '低价值客户']
        segment_stats['segment_name'] = default_names[:n_segments]
        
        return ltv_data, segment_stats
    
    def get_segment_profile(self, original_data, ltv_data, segment_id):
        segment_customers = ltv_data[ltv_data['segment'] == segment_id]
        
        customer_ids = segment_customers['customer_id'].values
        
        segment_data = original_data[original_data['customer_id'].isin(customer_ids)]
        
        churn_count = segment_customers['is_churned'].sum() if 'is_churned' in segment_customers.columns else 0
        
        profile = {
            'customer_count': len(segment_customers),
            'avg_ltv': segment_customers['ltv'].mean(),
            'avg_frequency': segment_data[self.bg_nbd.frequency_col].mean(),
            'avg_recency': segment_data[self.bg_nbd.recency_col].mean(),
            'avg_amount': segment_data[self.gamma_gamma.amount_col].mean(),
            'avg_prob_alive': segment_customers['probability_alive'].mean(),
            'avg_reactivation_prob': segment_customers['reactivation_prob'].mean() if 'reactivation_prob' in segment_customers.columns else 1.0,
            'churn_count': churn_count,
            'churn_rate': churn_count / len(segment_customers) if len(segment_customers) > 0 else 0,
            'age_distribution': segment_data['age'].describe().to_dict() if 'age' in segment_data.columns else None,
            'gender_distribution': segment_data['gender'].value_counts().to_dict() if 'gender' in segment_data.columns else None,
            'region_distribution': segment_data['region'].value_counts().to_dict() if 'region' in segment_data.columns else None,
            'membership_distribution': segment_data['membership_level'].value_counts().to_dict() if 'membership_level' in segment_data.columns else None
        }
        
        return profile
    
    def generate_ltv_distribution_report(self, ltv_data):
        report = {
            'total_customers': len(ltv_data),
            'total_ltv': ltv_data['ltv'].sum(),
            'avg_ltv': ltv_data['ltv'].mean(),
            'median_ltv': ltv_data['ltv'].median(),
            'ltv_std': ltv_data['ltv'].std(),
            'ltv_min': ltv_data['ltv'].min(),
            'ltv_max': ltv_data['ltv'].max(),
            'top_10_percent_ltv': ltv_data['ltv'].nlargest(int(len(ltv_data) * 0.1)).sum(),
            'bottom_50_percent_ltv': ltv_data['ltv'].nsmallest(int(len(ltv_data) * 0.5)).sum()
        }
        
        report['top_10_contribution'] = report['top_10_percent_ltv'] / report['total_ltv']
        report['bottom_50_contribution'] = report['bottom_50_percent_ltv'] / report['total_ltv']
        
        return report


if __name__ == '__main__':
    from data_generator import generate_customer_profiles, generate_transaction_history, generate_behavior_logs, prepare_model_data
    from bg_nbd_model import BGNBDModel
    from gamma_gamma_model import GammaGammaModel
    
    profiles = generate_customer_profiles(n_customers=500)
    transactions = generate_transaction_history(profiles)
    behavior_logs = generate_behavior_logs(profiles)
    model_data = prepare_model_data(profiles, transactions, behavior_logs)
    
    bg_nbd = BGNBDModel()
    bg_nbd.fit(model_data)
    
    gg = GammaGammaModel()
    gg.fit(model_data)
    
    analyzer = LTVAnalyzer(bg_nbd, gg)
    
    ltv_data = analyzer.calculate_ltv(model_data, future_months=12)
    print("LTV预测结果前5行:")
    print(ltv_data.head())
    
    quantiles = analyzer.calculate_ltv_quantiles(ltv_data)
    print("\nLTV分位数:")
    print(quantiles)
    
    ltv_data_with_segments, segment_stats = analyzer.segment_customers(model_data, ltv_data, n_segments=4)
    print("\n客户分群统计:")
    print(segment_stats)
    
    report = analyzer.generate_ltv_distribution_report(ltv_data)
    print("\nLTV分布报告:")
    for k, v in report.items():
        print(f"  {k}: {v}")
