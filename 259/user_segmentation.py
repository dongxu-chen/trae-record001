import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

class UserRiskSegmenter:
    def __init__(self, n_groups=3, method='kmeans', thresholds=None, quantiles=None):
        self.n_groups = n_groups
        self.method = method
        self.custom_thresholds = thresholds
        self.custom_quantiles = quantiles
        self.kmeans = None
        self.scaler = None
        self.group_labels = None
        self.thresholds = None
        self.risk_min = None
        self.risk_max = None
        
    def fit(self, risk_scores, churn_probs=None):
        self.risk_min = np.min(risk_scores)
        self.risk_max = np.max(risk_scores)
        
        if self.method == 'kmeans':
            return self._fit_kmeans(risk_scores)
        elif self.method == 'quantile':
            return self._fit_quantile(risk_scores)
        elif self.method == 'custom':
            return self._fit_custom(risk_scores)
        else:
            raise ValueError(f"Unknown method: {self.method}. Use 'kmeans', 'quantile', or 'custom'")
    
    def _fit_kmeans(self, risk_scores):
        risk_array = np.array(risk_scores).reshape(-1, 1)
        
        self.scaler = StandardScaler()
        risk_scaled = self.scaler.fit_transform(risk_array)
        
        self.kmeans = KMeans(n_clusters=self.n_groups, random_state=42, n_init=10)
        clusters = self.kmeans.fit_predict(risk_scaled)
        
        cluster_means = pd.DataFrame({
            'cluster': clusters,
            'risk': risk_scores
        }).groupby('cluster')['risk'].mean().sort_values()
        
        self.group_labels = {}
        for new_label, (cluster, _) in enumerate(cluster_means.items()):
            self.group_labels[cluster] = self.n_groups - 1 - new_label
        
        risk_sorted = np.sort(risk_scores)
        n = len(risk_sorted)
        self.thresholds = {
            'low': risk_sorted[int(n * 0.66)],
            'medium': risk_sorted[int(n * 0.33)]
        }
        
        return clusters
    
    def _fit_quantile(self, risk_scores):
        if self.custom_quantiles is None:
            self.custom_quantiles = [0.33, 0.66]
        
        self.thresholds = {}
        if self.n_groups == 3:
            self.thresholds['medium'] = np.quantile(risk_scores, self.custom_quantiles[0])
            self.thresholds['low'] = np.quantile(risk_scores, self.custom_quantiles[1])
        elif self.n_groups == 2:
            self.thresholds['low'] = np.quantile(risk_scores, self.custom_quantiles[0])
        
        return self.transform(risk_scores)
    
    def _fit_custom(self, risk_scores):
        if self.custom_thresholds is None:
            raise ValueError("Custom thresholds must be provided when method='custom'")
        
        self.thresholds = self.custom_thresholds
        return self.transform(risk_scores)
    
    def transform(self, risk_scores):
        if self.method == 'kmeans':
            return self._transform_kmeans(risk_scores)
        else:
            return self._transform_threshold(risk_scores)
    
    def _transform_kmeans(self, risk_scores):
        risk_array = np.array(risk_scores).reshape(-1, 1)
        risk_scaled = self.scaler.transform(risk_array)
        clusters = self.kmeans.predict(risk_scaled)
        
        mapped_clusters = np.array([self.group_labels[c] for c in clusters])
        
        group_names = []
        for c in mapped_clusters:
            if c == 0:
                group_names.append('低风险')
            elif c == 1:
                group_names.append('中风险')
            else:
                group_names.append('高风险')
        
        return group_names
    
    def _transform_threshold(self, risk_scores):
        risk_array = np.array(risk_scores)
        group_names = []
        
        if self.n_groups == 3:
            medium_thresh = self.thresholds.get('medium', self.thresholds.get('high_low', self.risk_min))
            low_thresh = self.thresholds.get('low', self.risk_max)
            
            for r in risk_array:
                if r >= low_thresh:
                    group_names.append('低风险')
                elif r >= medium_thresh:
                    group_names.append('中风险')
                else:
                    group_names.append('高风险')
        elif self.n_groups == 2:
            low_thresh = self.thresholds.get('low', self.thresholds.get('high_low', (self.risk_min + self.risk_max) / 2))
            
            for r in risk_array:
                if r >= low_thresh:
                    group_names.append('低风险')
                else:
                    group_names.append('高风险')
        
        return group_names
    
    def fit_transform(self, risk_scores):
        self.fit(risk_scores)
        return self.transform(risk_scores)
    
    def get_threshold_info(self):
        info = {
            'method': self.method,
            'n_groups': self.n_groups,
            'risk_range': [self.risk_min, self.risk_max]
        }
        
        if self.thresholds:
            info['thresholds'] = self.thresholds
        
        if self.method == 'quantile' and self.custom_quantiles:
            info['quantiles'] = self.custom_quantiles
        
        return info
    
    def get_user_segments(self, df, risk_scores, churn_probs_30d, churn_probs_90d):
        groups = self.fit_transform(risk_scores)
        
        result_df = df.copy()
        result_df['risk_score'] = risk_scores.values
        result_df['risk_group'] = groups
        result_df['churn_prob_30d'] = churn_probs_30d
        result_df['churn_prob_90d'] = churn_probs_90d
        
        return result_df
    
    def get_segment_statistics(self, segmented_df, feature_cols):
        stats = segmented_df.groupby('risk_group').agg({
            'risk_score': ['mean', 'median', 'min', 'max', 'std'],
            'churn_prob_30d': ['mean', 'median'],
            'churn_prob_90d': ['mean', 'median']
        }).round(4)
        
        stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
        stats = stats.reset_index()
        
        feature_stats = segmented_df.groupby('risk_group')[feature_cols].mean().round(4)
        feature_stats = feature_stats.reset_index()
        
        count_df = segmented_df.groupby('risk_group').size().reset_index(name='user_count')
        count_df['percentage'] = (count_df['user_count'] / len(segmented_df) * 100).round(2)
        
        stats = stats.merge(count_df, on='risk_group')
        stats = stats.merge(feature_stats, on='risk_group')
        
        return stats
    
    def get_top_features_by_group(self, segmented_df, feature_cols, coef_df, top_n=5):
        group_features = {}
        groups = ['高风险', '中风险', '低风险']
        
        for group in groups:
            group_data = segmented_df[segmented_df['risk_group'] == group]
            
            group_profile = group_data[feature_cols].mean()
            overall_profile = segmented_df[feature_cols].mean()
            
            deviation = (group_profile - overall_profile) / overall_profile.abs()
            deviation = deviation.sort_values(ascending=False)
            
            risk_factors = coef_df[coef_df['coef'] > 0]['feature'].tolist()
            protective_factors = coef_df[coef_df['coef'] < 0]['feature'].tolist()
            
            group_risk_features = [f for f in deviation.index if f in risk_factors][:top_n]
            group_protective_features = [f for f in deviation.index if f in protective_factors][-top_n:]
            
            group_features[group] = {
                'elevated_risk_features': group_risk_features,
                'weak_protective_features': group_protective_features,
                'deviation': deviation
            }
        
        return group_features
    
    def generate_segment_insights(self, group_features, coef_df):
        insights = {}
        
        for group, features in group_features.items():
            insight_text = []
            
            if features['elevated_risk_features']:
                risk_desc = []
                for f in features['elevated_risk_features']:
                    hr = coef_df[coef_df['feature'] == f]['hazard_ratio'].values[0]
                    dev = features['deviation'][f]
                    risk_desc.append(f"{f}(HR={hr:.2f}, 偏高{dev*100:.1f}%)")
                insight_text.append(f"⚠️ 高风险特征: {', '.join(risk_desc)}")
            
            if features['weak_protective_features']:
                prot_desc = []
                for f in features['weak_protective_features']:
                    hr = coef_df[coef_df['feature'] == f]['hazard_ratio'].values[0]
                    dev = features['deviation'][f]
                    prot_desc.append(f"{f}(HR={hr:.2f}, 偏低{abs(dev)*100:.1f}%)")
                insight_text.append(f"💡 缺失保护特征: {', '.join(prot_desc)}")
            
            if group == '高风险':
                action = "🔴 建议立即介入: 针对性优惠活动、客户关怀、产品体验优化"
            elif group == '中风险':
                action = "🟡 建议持续关注: 定期推送有价值内容、提升用户参与度"
            else:
                action = "🟢 建议保持维护: 忠诚度计划、社区建设、推荐激励"
            
            insight_text.append(action)
            insights[group] = '\n'.join(insight_text)
        
        return insights
