import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')


class LoyaltyClusterer:
    def __init__(self, n_clusters=3, method='kmeans'):
        self.n_clusters = n_clusters
        self.method = method
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.model = None
        self.feature_names = None
        
    def prepare_features(self, data_dict):
        profiles = data_dict['profiles']
        purchases = data_dict['purchases']
        nps = data_dict['nps']
        complaints = data_dict['complaints']
        interactions = data_dict['interactions']
        
        purchase_date = pd.to_datetime(purchases['purchase_date'])
        end_date = pd.to_datetime('2025-12-31')
        
        agg_dict = {
            'frequency': ('purchase_date', 'count'),
            'total_spend': ('purchase_amount', 'sum'),
            'avg_order_value': ('purchase_amount', 'mean'),
            'last_purchase': ('purchase_date', 'max'),
            'first_purchase': ('purchase_date', 'min'),
            'return_rate': ('is_returned', 'mean'),
            'discount_usage': ('discount_used', 'mean')
        }
        
        if 'price_sensitivity' in purchases.columns:
            agg_dict['price_sensitivity'] = ('price_sensitivity', 'mean')
        if 'promotion_responsiveness' in purchases.columns:
            agg_dict['promotion_responsiveness'] = ('promotion_responsiveness', 'mean')
        if 'discount_pct' in purchases.columns:
            agg_dict['avg_discount_pct'] = ('discount_pct', 'mean')
            agg_dict['max_discount_pct'] = ('discount_pct', 'max')
        if 'is_promotion' in purchases.columns:
            agg_dict['promotion_purchase_rate'] = ('is_promotion', 'mean')
            agg_dict['promotion_purchase_count'] = ('is_promotion', 'sum')
        if 'base_price' in purchases.columns:
            agg_dict['avg_base_price'] = ('base_price', 'mean')
            agg_dict['total_base_value'] = ('base_price', 'sum')
        
        customer_metrics = purchases.groupby('customer_id').agg(**agg_dict).reset_index()
        
        if 'discount_amount' in purchases.columns:
            total_discount = purchases.groupby('customer_id')['discount_amount'].sum().reset_index()
            customer_metrics = customer_metrics.merge(total_discount, on='customer_id', how='left')
            customer_metrics.rename(columns={'discount_amount': 'total_discount_amount'}, inplace=True)
            customer_metrics['total_discount_amount'] = customer_metrics['total_discount_amount'].fillna(0)
        
        customer_metrics['recency_days'] = (end_date - pd.to_datetime(customer_metrics['last_purchase'])).dt.days
        customer_metrics['tenure_days'] = (pd.to_datetime(customer_metrics['last_purchase']) - pd.to_datetime(customer_metrics['first_purchase'])).dt.days
        
        customer_metrics['repurchase_rate'] = customer_metrics['frequency'].apply(lambda x: 1 if x > 1 else 0)
        
        if 'avg_discount_pct' in customer_metrics.columns and 'promotion_purchase_rate' in customer_metrics.columns:
            customer_metrics['deal_hunter_score'] = customer_metrics['promotion_purchase_rate'] * customer_metrics['price_sensitivity']
            customer_metrics['savings_consciousness'] = customer_metrics['total_discount_amount'] / (customer_metrics['total_base_value'] + 1)
            customer_metrics['promo_sensitivity'] = customer_metrics['promotion_purchase_rate'] * customer_metrics['promotion_responsiveness']
            customer_metrics['price_value_ratio'] = customer_metrics['avg_base_price'] / (customer_metrics['avg_order_value'] + 0.01)
        
        if 'product_category' in purchases.columns:
            category_pref = pd.get_dummies(
                purchases.groupby(['customer_id', 'product_category']).size().unstack(fill_value=0),
                prefix='prefers'
            ).reset_index()
            customer_metrics = customer_metrics.merge(category_pref, on='customer_id', how='left')
        
        if 'promotion_type' in purchases.columns:
            promo_type_pref = pd.get_dummies(
                purchases[purchases['is_promotion'] == 1].groupby(
                    ['customer_id', 'promotion_type']
                ).size().unstack(fill_value=0),
                prefix='promo_used'
            ).reset_index()
            customer_metrics = customer_metrics.merge(promo_type_pref, on='customer_id', how='left')
            for col in promo_type_pref.columns:
                if col != 'customer_id':
                    customer_metrics[col] = customer_metrics[col].fillna(0)
        
        nps_avg = nps.groupby('customer_id').agg(
            avg_nps=('nps_score', 'mean'),
            avg_ease_of_use=('ease_of_use', 'mean'),
            avg_product_quality=('product_quality', 'mean'),
            avg_customer_service=('customer_service', 'mean'),
            nps_surveys=('nps_score', 'count')
        ).reset_index()
        
        def classify_nps(score):
            if score >= 9:
                return 'promoter'
            elif score >= 7:
                return 'passive'
            else:
                return 'detractor'
        
        nps['nps_category'] = nps['nps_score'].apply(classify_nps)
        nps_category = nps.groupby('customer_id')['nps_category'].apply(
            lambda x: x.value_counts().index[0]
        ).reset_index()
        nps_category.columns = ['customer_id', 'nps_mode_category']
        
        complaint_metrics = complaints.groupby('customer_id').agg(
            complaint_count=('complaint_date', 'count'),
            unresolved_complaints=('is_resolved', lambda x: sum(x == 0)),
            avg_resolution_time=('resolution_time_days', 'mean')
        ).reset_index()
        
        complaint_metrics['complaint_rate'] = complaint_metrics['complaint_count']
        complaint_metrics['unresolved_rate'] = complaint_metrics['unresolved_complaints'] / complaint_metrics['complaint_count'].replace(0, 1)
        
        interaction_metrics = interactions.groupby('customer_id').agg(
            total_interactions=('interaction_date', 'count'),
            avg_duration=('duration_seconds', 'mean')
        ).reset_index()
        
        interaction_types = pd.pivot_table(
            interactions, 
            index='customer_id', 
            columns='interaction_type', 
            values='interaction_date',
            aggfunc='count',
            fill_value=0
        ).reset_index()
        
        features = customer_metrics.merge(profiles, on='customer_id', how='left')
        features = features.merge(nps_avg, on='customer_id', how='left')
        features = features.merge(nps_category, on='customer_id', how='left')
        features = features.merge(complaint_metrics, on='customer_id', how='left')
        features = features.merge(interaction_metrics, on='customer_id', how='left')
        features = features.merge(interaction_types, on='customer_id', how='left')
        
        features = features.fillna({
            'avg_nps': 5,
            'avg_ease_of_use': 3,
            'avg_product_quality': 3,
            'avg_customer_service': 3,
            'nps_surveys': 0,
            'complaint_count': 0,
            'unresolved_complaints': 0,
            'avg_resolution_time': 0,
            'complaint_rate': 0,
            'unresolved_rate': 0,
            'total_interactions': 0,
            'avg_duration': 0,
            'Email Open': 0,
            'Click-Through': 0,
            'Social Media': 0,
            'Support Call': 0,
            'App Visit': 0
        })
        
        def nps_to_numeric(category):
            if category == 'promoter':
                return 1
            elif category == 'passive':
                return 0
            else:
                return -1
        
        features['nps_category_numeric'] = features['nps_mode_category'].apply(nps_to_numeric)
        
        features.columns = features.columns.astype(str)
        return features
    
    def select_features(self, features):
        base_features = [
            'frequency', 'total_spend', 'avg_order_value', 'recency_days',
            'tenure_days', 'repurchase_rate', 'return_rate', 'discount_usage',
            'avg_nps', 'avg_ease_of_use', 'avg_product_quality', 'avg_customer_service',
            'complaint_count', 'unresolved_complaints', 'unresolved_rate',
            'avg_resolution_time', 'total_interactions', 'avg_duration',
            'Email Open', 'Click-Through', 'Social Media', 'Support Call', 'App Visit',
            'nps_category_numeric', 'loyalty_tendency'
        ]
        
        price_promotion_features = [
            'price_sensitivity', 'promotion_responsiveness',
            'avg_discount_pct', 'max_discount_pct',
            'promotion_purchase_rate', 'promotion_purchase_count',
            'avg_base_price', 'total_base_value', 'total_discount_amount',
            'deal_hunter_score', 'savings_consciousness',
            'promo_sensitivity', 'price_value_ratio'
        ]
        
        numeric_features = base_features + price_promotion_features
        
        available_features = [f for f in numeric_features if f in features.columns]
        self.feature_names = available_features
        
        result = features[available_features].copy()
        result.columns = result.columns.astype(str)
        return result
    
    def find_optimal_clusters(self, features_scaled, max_k=10):
        inertia = []
        silhouette_scores = []
        calinski_scores = []
        davies_scores = []
        
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(features_scaled)
            
            inertia.append(kmeans.inertia_)
            silhouette_scores.append(silhouette_score(features_scaled, labels))
            calinski_scores.append(calinski_harabasz_score(features_scaled, labels))
            davies_scores.append(davies_bouldin_score(features_scaled, labels))
        
        results = {
            'k': list(range(2, max_k + 1)),
            'inertia': inertia,
            'silhouette_score': silhouette_scores,
            'calinski_harabasz_score': calinski_scores,
            'davies_bouldin_score': davies_scores
        }
        
        return results
    
    def fit(self, features_df):
        features_selected = self.select_features(features_df)
        
        features_selected.columns = features_selected.columns.astype(str)
        
        features_array = features_selected.values
        features_scaled = self.scaler.fit_transform(features_array)
        
        if self.method == 'kmeans':
            self.model = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
            labels = self.model.fit_predict(features_scaled)
        elif self.method == 'gmm':
            self.model = GaussianMixture(n_components=self.n_clusters, random_state=42)
            labels = self.model.fit_predict(features_scaled)
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        features_df['cluster'] = labels
        self.pca_features = self.pca.fit_transform(features_scaled)
        features_df['pca_x'] = self.pca_features[:, 0]
        features_df['pca_y'] = self.pca_features[:, 1]
        
        self.cluster_labels = self._assign_loyalty_labels(features_df)
        features_df['loyalty_level'] = features_df['cluster'].map(self.cluster_labels)
        
        return features_df
    
    def _assign_loyalty_labels(self, features_df):
        cluster_metrics = features_df.groupby('cluster').agg({
            'frequency': 'mean',
            'total_spend': 'mean',
            'recency_days': 'mean',
            'avg_nps': 'mean',
            'complaint_count': 'mean',
            'loyalty_tendency': 'mean'
        }).reset_index()
        
        cluster_metrics['score'] = (
            (cluster_metrics['frequency'] / cluster_metrics['frequency'].max()) * 0.2 +
            (cluster_metrics['total_spend'] / cluster_metrics['total_spend'].max()) * 0.2 +
            (1 - cluster_metrics['recency_days'] / cluster_metrics['recency_days'].max()) * 0.15 +
            (cluster_metrics['avg_nps'] / cluster_metrics['avg_nps'].max()) * 0.25 +
            (1 - cluster_metrics['complaint_count'] / cluster_metrics['complaint_count'].max()) * 0.1 +
            (cluster_metrics['loyalty_tendency'] / cluster_metrics['loyalty_tendency'].max()) * 0.1
        )
        
        cluster_metrics = cluster_metrics.sort_values('score', ascending=False)
        labels = ['高', '中', '低'][:self.n_clusters]
        if self.n_clusters > 3:
            labels = ['极高', '高', '中', '低', '极低'][:self.n_clusters]
        
        return dict(zip(cluster_metrics['cluster'], labels))
    
    def get_cluster_profiles(self, features_df):
        agg_dict = {
            'customer_id': 'count',
            'frequency': 'mean',
            'total_spend': 'mean',
            'avg_order_value': 'mean',
            'recency_days': 'mean',
            'tenure_days': 'mean',
            'repurchase_rate': 'mean',
            'avg_nps': 'mean',
            'complaint_count': 'mean',
            'unresolved_complaints': 'mean',
            'total_interactions': 'mean',
            'return_rate': 'mean'
        }
        
        price_promo_columns = [
            'price_sensitivity', 'promotion_responsiveness',
            'avg_discount_pct', 'promotion_purchase_rate',
            'deal_hunter_score', 'savings_consciousness',
            'promo_sensitivity'
        ]
        
        for col in price_promo_columns:
            if col in features_df.columns:
                agg_dict[col] = 'mean'
        
        numeric_cols = features_df.select_dtypes(include=[np.number]).columns.tolist()
        valid_cols = [col for col in agg_dict.keys() if col in features_df.columns]
        
        count_col = 'customer_id'
        mean_cols = [col for col in valid_cols if col != count_col and col in numeric_cols]
        
        agg_dict_final = {}
        if count_col in valid_cols:
            agg_dict_final[count_col] = 'count'
        for col in mean_cols:
            agg_dict_final[col] = 'mean'
        
        cluster_profiles = features_df.groupby('loyalty_level').agg(agg_dict_final).reset_index()
        
        column_mapping = {
            'customer_id': '用户数量',
            'frequency': '平均购买频次',
            'total_spend': '平均总消费',
            'avg_order_value': '平均客单价',
            'recency_days': '平均最近购买天数',
            'tenure_days': '平均客户留存天数',
            'repurchase_rate': '复购率',
            'avg_nps': '平均NPS',
            'complaint_count': '平均投诉次数',
            'unresolved_complaints': '平均未解决投诉',
            'total_interactions': '平均互动次数',
            'return_rate': '平均退货率',
            'price_sensitivity': '平均价格敏感度',
            'promotion_responsiveness': '平均促销响应度',
            'avg_discount_pct': '平均折扣率',
            'promotion_purchase_rate': '促销购买占比',
            'deal_hunter_score': '淘优惠指数',
            'savings_consciousness': '省钱意识指数',
            'promo_sensitivity': '促销敏感度'
        }
        
        cluster_profiles.columns = ['忠诚度层级'] + [
            column_mapping.get(col, col) for col in cluster_profiles.columns[1:]
        ]
        
        total_customers = cluster_profiles['用户数量'].sum()
        cluster_profiles['用户占比'] = cluster_profiles['用户数量'] / total_customers
        
        return cluster_profiles
    
    def predict(self, new_features_df):
        features_selected = self.select_features(new_features_df)
        features_selected.columns = features_selected.columns.astype(str)
        features_array = features_selected.values
        features_scaled = self.scaler.transform(features_array)
        
        labels = self.model.predict(features_scaled)
        new_features_df['cluster'] = labels
        new_features_df['loyalty_level'] = new_features_df['cluster'].map(self.cluster_labels)
        
        return new_features_df
    
    def get_cluster_characteristics(self, features_df):
        cluster_characteristics = {}
        
        for level in ['高', '中', '低']:
            if level in features_df['loyalty_level'].values:
                cluster_data = features_df[features_df['loyalty_level'] == level]
                
                characteristics = {
                    'size': len(cluster_data),
                    'percentage': len(cluster_data) / len(features_df),
                    'avg_frequency': cluster_data['frequency'].mean(),
                    'avg_spend': cluster_data['total_spend'].mean(),
                    'avg_nps': cluster_data['avg_nps'].mean(),
                    'top_segments': cluster_data['segment'].value_counts().head(3).to_dict(),
                    'top_channels': cluster_data['channel'].value_counts().head(3).to_dict(),
                    'avg_complaints': cluster_data['complaint_count'].mean(),
                    'repurchase_rate': cluster_data['repurchase_rate'].mean()
                }
                
                if 'price_sensitivity' in cluster_data.columns:
                    characteristics['avg_price_sensitivity'] = cluster_data['price_sensitivity'].mean()
                    characteristics['avg_promotion_responsiveness'] = cluster_data['promotion_responsiveness'].mean()
                    characteristics['avg_discount_pct'] = cluster_data['avg_discount_pct'].mean()
                    characteristics['promotion_purchase_rate'] = cluster_data['promotion_purchase_rate'].mean()
                    characteristics['deal_hunter_score'] = cluster_data['deal_hunter_score'].mean()
                
                prefers_cols = [col for col in cluster_data.columns if col.startswith('prefers_')]
                if prefers_cols:
                    category_totals = cluster_data[prefers_cols].sum()
                    top_categories = category_totals.sort_values(ascending=False).head(3)
                    characteristics['top_categories'] = {
                        col.replace('prefers_', ''): int(val) 
                        for col, val in top_categories.items()
                    }
                
                cluster_characteristics[level] = characteristics
        
        return cluster_characteristics
    
    def run_clustering_analysis(self, data_dict, find_optimal_k=False):
        print("Preparing features...")
        features = self.prepare_features(data_dict)
        
        if find_optimal_k:
            print("Finding optimal number of clusters...")
            features_selected = self.select_features(features)
            features_selected.columns = features_selected.columns.astype(str)
            features_array = features_selected.values
            features_scaled = self.scaler.fit_transform(features_array)
            optimal_results = self.find_optimal_clusters(features_scaled)
        else:
            optimal_results = None
        
        print(f"Fitting {self.method} with {self.n_clusters} clusters...")
        features_with_clusters = self.fit(features)
        
        print("Generating cluster profiles...")
        cluster_profiles = self.get_cluster_profiles(features_with_clusters)
        
        print("Getting cluster characteristics...")
        cluster_characteristics = self.get_cluster_characteristics(features_with_clusters)
        
        return {
            'features_with_clusters': features_with_clusters,
            'cluster_profiles': cluster_profiles,
            'cluster_characteristics': cluster_characteristics,
            'optimal_k_results': optimal_results,
            'pca_features': self.pca_features
        }
