import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance, partial_dependence
import shap
import warnings
warnings.filterwarnings('ignore')


class AttributionAnalyzer:
    def __init__(self):
        self.feature_importance = None
        self.model = None
        self.feature_names = None
        
    def prepare_attribution_data(self, features_with_clusters, data_dict):
        profiles = data_dict['profiles']
        purchases = data_dict['purchases']
        nps = data_dict['nps']
        complaints = data_dict['complaints']
        interactions = data_dict['interactions']
        
        df = features_with_clusters.copy()
        df.columns = df.columns.astype(str)
        
        loyalty_mapping = {'高': 2, '中': 1, '低': 0}
        df['loyalty_numeric'] = df['loyalty_level'].map(loyalty_mapping)
        
        purchase_dates = pd.to_datetime(purchases['purchase_date'])
        purchases['month'] = purchase_dates.dt.to_period('M')
        monthly_spend = purchases.groupby(['customer_id', 'month'])['purchase_amount'].sum().reset_index()
        spend_growth = monthly_spend.groupby('customer_id')['purchase_amount'].apply(
            lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] if x.iloc[0] > 0 else 0
        ).reset_index()
        spend_growth.columns = ['customer_id', 'spend_growth_rate']
        df = df.merge(spend_growth, on='customer_id', how='left')
        
        complaint_type_dummies = pd.get_dummies(
            complaints.groupby(['customer_id', 'complaint_type']).size().unstack(fill_value=0),
            prefix='complaint'
        ).reset_index()
        df = df.merge(complaint_type_dummies, on='customer_id', how='left')
        for col in complaint_type_dummies.columns:
            if col != 'customer_id':
                df[col] = df[col].fillna(0)
        
        severity_dummies = pd.get_dummies(
            complaints.groupby(['customer_id', 'severity']).size().unstack(fill_value=0),
            prefix='severity'
        ).reset_index()
        df = df.merge(severity_dummies, on='customer_id', how='left')
        for col in severity_dummies.columns:
            if col != 'customer_id':
                df[col] = df[col].fillna(0)
        
        product_pref = pd.get_dummies(
            purchases.groupby(['customer_id', 'product_category']).size().unstack(fill_value=0),
            prefix='prefers'
        ).reset_index()
        df = df.merge(product_pref, on='customer_id', how='left')
        
        price_promotion_features = purchases.groupby('customer_id').agg(
            price_sensitivity=('price_sensitivity', 'mean'),
            promotion_responsiveness=('promotion_responsiveness', 'mean'),
            avg_discount_pct=('discount_pct', 'mean'),
            max_discount_pct=('discount_pct', 'max'),
            total_discount_amount=('discount_amount', 'sum'),
            promotion_purchase_rate=('is_promotion', 'mean'),
            promotion_purchase_count=('is_promotion', 'sum'),
            avg_base_price=('base_price', 'mean'),
            total_base_value=('base_price', 'sum'),
            avg_final_price=('purchase_amount', 'mean'),
            price_value_ratio=('base_price', lambda x: (x / purchases.loc[x.index, 'purchase_amount']).mean())
        ).reset_index()
        
        df = df.merge(price_promotion_features, on='customer_id', how='left')
        
        required_cols = ['total_discount_amount', 'total_base_value', 'promotion_purchase_rate', 
                        'price_sensitivity', 'price_value_ratio', 'avg_discount_pct']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
        
        promotion_type_counts = purchases[purchases['is_promotion'] == 1].groupby(
            ['customer_id', 'promotion_type']
        ).size().unstack(fill_value=0).reset_index()
        
        promotion_type_counts.columns = [
            'customer_id' if col == 'customer_id' else f'promotion_used_{str(col)}' 
            for col in promotion_type_counts.columns
        ]
        promotion_type_counts.columns = promotion_type_counts.columns.astype(str)
        
        df = df.merge(promotion_type_counts, on='customer_id', how='left')
        for col in promotion_type_counts.columns:
            col_str = str(col)
            if col_str != 'customer_id':
                df[col_str] = df[col_str].fillna(0)
        
        category_price_sensitivity = purchases.groupby(
            ['customer_id', 'product_category']
        ).agg(
            category_avg_discount=('discount_pct', 'mean'),
            category_promo_rate=('is_promotion', 'mean'),
            category_spend=('purchase_amount', 'sum'),
            category_purchases=('purchase_date', 'count')
        ).reset_index()
        
        for category in purchases['product_category'].unique():
            category_str = str(category)
            cat_data = category_price_sensitivity[
                category_price_sensitivity['product_category'] == category
            ]
            cat_data = cat_data[['customer_id', 'category_avg_discount', 'category_promo_rate', 'category_spend']].copy()
            cat_data.columns = [
                'customer_id', 
                f'{category_str}_avg_discount',
                f'{category_str}_promo_rate',
                f'{category_str}_spend'
            ]
            cat_data.columns = cat_data.columns.astype(str)
            df = df.merge(cat_data, on='customer_id', how='left')
            df[f'{category_str}_avg_discount'] = df[f'{category_str}_avg_discount'].fillna(0)
            df[f'{category_str}_promo_rate'] = df[f'{category_str}_promo_rate'].fillna(0)
            df[f'{category_str}_spend'] = df[f'{category_str}_spend'].fillna(0)
        
        df['savings_consciousness'] = df['total_discount_amount'] / (df['total_base_value'] + 1)
        df['deal_hunter_score'] = df['promotion_purchase_rate'] * df['price_sensitivity']
        df['value_seeker_score'] = df['price_value_ratio'] * df['savings_consciousness']
        df['promo_sensitivity'] = df['promotion_purchase_rate'] * df['promotion_responsiveness']
        
        df['only_promo_buyer'] = (df['promotion_purchase_rate'] >= 0.8).astype(int)
        df['never_promo_buyer'] = (df['promotion_purchase_rate'] <= 0.1).astype(int)
        df['high_price_sensitivity'] = (df['price_sensitivity'] >= 0.7).astype(int)
        df['low_price_sensitivity'] = (df['price_sensitivity'] <= 0.3).astype(int)
        
        segment_dummies = pd.get_dummies(df['segment'], prefix='segment', drop_first=False)
        channel_dummies = pd.get_dummies(df['channel'], prefix='channel', drop_first=False)
        region_dummies = pd.get_dummies(df['region'], prefix='region', drop_first=False)
        gender_dummies = pd.get_dummies(df['gender'], prefix='gender', drop_first=False)
        
        df = pd.concat([df, segment_dummies, channel_dummies, region_dummies, gender_dummies], axis=1)
        
        df['is_high_loyalty'] = (df['loyalty_level'] == '高').astype(int)
        df['is_low_loyalty'] = (df['loyalty_level'] == '低').astype(int)
        
        df.columns = df.columns.astype(str)
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)
        
        return df
    
    def identify_key_features(self, df, target='loyalty_numeric', top_n=15):
        exclude_cols = [
            'customer_id', 'cluster', 'loyalty_level', 'loyalty_numeric',
            'is_high_loyalty', 'is_low_loyalty', 'pca_x', 'pca_y',
            'first_purchase', 'last_purchase', 'nps_mode_category',
            'segment', 'channel', 'region', 'gender', 'loyalty_tendency'
        ]
        
        feature_cols = [col for col in df.columns if col not in exclude_cols and df[col].dtype in ['int64', 'float64', 'uint8', 'bool']]
        
        feature_cols = [str(col) for col in feature_cols]
        X = df[feature_cols].copy()
        X.columns = X.columns.astype(str)
        y = df[target]
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X.values)
        
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_scaled, y)
        
        gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        gb_model.fit(X_scaled, y)
        
        lr_model = LinearRegression()
        lr_model.fit(X_scaled, y)
        
        rf_importance = pd.DataFrame({
            'feature': feature_cols,
            'rf_importance': rf_model.feature_importances_
        })
        
        gb_importance = pd.DataFrame({
            'feature': feature_cols,
            'gb_importance': gb_model.feature_importances_
        })
        
        lr_importance = pd.DataFrame({
            'feature': feature_cols,
            'lr_importance': np.abs(lr_model.coef_) / np.sum(np.abs(lr_model.coef_))
        })
        
        importance_df = rf_importance.merge(gb_importance, on='feature').merge(lr_importance, on='feature')
        
        importance_df['normalized_rf'] = importance_df['rf_importance'] / importance_df['rf_importance'].sum()
        importance_df['normalized_gb'] = importance_df['gb_importance'] / importance_df['gb_importance'].sum()
        
        importance_df['ensemble_score'] = (
            importance_df['normalized_rf'] * 0.4 +
            importance_df['normalized_gb'] * 0.4 +
            importance_df['lr_importance'] * 0.2
        )
        
        importance_df = importance_df.sort_values('ensemble_score', ascending=False)
        importance_df['cumulative_score'] = importance_df['ensemble_score'].cumsum()
        
        self.feature_importance = importance_df
        self.feature_names = feature_cols
        self.model = gb_model
        self.scaler = scaler
        
        return {
            'importance_df': importance_df.head(top_n),
            'top_features': importance_df['feature'].head(top_n).tolist(),
            'all_importance': importance_df
        }
    
    def shap_analysis(self, df, target='loyalty_numeric'):
        exclude_cols = [
            'customer_id', 'cluster', 'loyalty_level', 'loyalty_numeric',
            'is_high_loyalty', 'is_low_loyalty', 'pca_x', 'pca_y',
            'first_purchase', 'last_purchase', 'nps_mode_category',
            'segment', 'channel', 'region', 'gender', 'loyalty_tendency'
        ]
        
        feature_cols = [str(col) for col in df.columns if col not in exclude_cols and df[col].dtype in ['int64', 'float64', 'uint8', 'bool']]
        
        X = df[feature_cols].copy()
        X.columns = X.columns.astype(str)
        y = df[target]
        
        X_scaled = self.scaler.transform(X.values)
        
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X_scaled)
        
        shap_summary = pd.DataFrame({
            'feature': feature_cols,
            'mean_abs_shap_value': np.mean(np.abs(shap_values), axis=0),
            'mean_shap_value': np.mean(shap_values, axis=0)
        })
        
        shap_summary = shap_summary.sort_values('mean_abs_shap_value', ascending=False)
        
        return {
            'shap_summary': shap_summary,
            'shap_values': shap_values,
            'expected_value': explainer.expected_value,
            'features': feature_cols
        }
    
    def analyze_factor_impact(self, df, importance_results, segment=None):
        if segment:
            df = df[df['segment'] == segment]
        
        top_features = importance_results['top_features'][:10]
        
        factor_impact = []
        
        for feature in top_features:
            high_loyal_avg = df[df['loyalty_level'] == '高'][feature].mean()
            medium_loyal_avg = df[df['loyalty_level'] == '中'][feature].mean()
            low_loyal_avg = df[df['loyalty_level'] == '低'][feature].mean()
            
            high_low_diff = high_loyal_avg - low_loyal_avg
            
            if df[feature].std() > 0:
                corr = df[feature].corr(df['loyalty_numeric'])
            else:
                corr = 0
            
            factor_impact.append({
                'factor': feature,
                'high_loyalty_avg': high_loyal_avg,
                'medium_loyalty_avg': medium_loyal_avg,
                'low_loyalty_avg': low_loyal_avg,
                'high_low_difference': high_low_diff,
                'correlation_with_loyalty': corr,
                'impact_direction': 'positive' if corr > 0 else 'negative'
            })
        
        return pd.DataFrame(factor_impact)
    
    def attribute_churn_drivers(self, df):
        churn_drivers = []
        
        df_churned = df[df['is_low_loyalty'] == 1]
        df_loyal = df[df['is_high_loyalty'] == 1]
        
        key_factors = [
            'complaint_count', 'unresolved_complaints', 'avg_nps',
            'recency_days', 'frequency', 'avg_customer_service',
            'return_rate', 'unresolved_rate', 'total_interactions',
            'price_sensitivity', 'promotion_responsiveness',
            'promotion_purchase_rate', 'avg_discount_pct',
            'deal_hunter_score', 'savings_consciousness',
            'only_promo_buyer', 'high_price_sensitivity'
        ]
        
        for factor in key_factors:
            churned_mean = df_churned[factor].mean()
            loyal_mean = df_loyal[factor].mean()
            
            if loyal_mean > 0:
                percent_diff = ((churned_mean - loyal_mean) / loyal_mean) * 100
            else:
                percent_diff = 0
            
            from scipy.stats import ttest_ind
            t_stat, p_value = ttest_ind(df_churned[factor], df_loyal[factor], equal_var=False)
            
            churn_drivers.append({
                'factor': factor,
                'churned_mean': churned_mean,
                'loyal_mean': loyal_mean,
                'percent_difference': percent_diff,
                'p_value': p_value,
                'is_significant': p_value < 0.05
            })
        
        return pd.DataFrame(churn_drivers).sort_values('percent_difference', key=lambda x: abs(x), ascending=False)
    
    def analyze_price_promotion_impact(self, df, data_dict):
        purchases = data_dict['purchases']
        
        price_promotion_analysis = {}
        
        price_promotion_analysis['overall'] = {
            'price_sensitivity_by_tier': df.groupby('loyalty_level')['price_sensitivity'].mean().to_dict(),
            'promotion_responsiveness_by_tier': df.groupby('loyalty_level')['promotion_responsiveness'].mean().to_dict(),
            'promo_purchase_rate_by_tier': df.groupby('loyalty_level')['promotion_purchase_rate'].mean().to_dict(),
            'avg_discount_by_tier': df.groupby('loyalty_level')['avg_discount_pct'].mean().to_dict(),
            'only_promo_by_tier': df.groupby('loyalty_level')['only_promo_buyer'].mean().to_dict()
        }
        
        price_sensitivity_correlation = df[['loyalty_numeric', 'price_sensitivity', 'promotion_responsiveness',
                                            'promotion_purchase_rate', 'avg_discount_pct',
                                            'deal_hunter_score', 'savings_consciousness',
                                            'total_spend', 'frequency']].corr()['loyalty_numeric'].to_dict()
        price_promotion_analysis['correlations'] = price_sensitivity_correlation
        
        category_analysis = {}
        for category in purchases['product_category'].unique():
            cat_discount_col = f'{category}_avg_discount'
            cat_promo_col = f'{category}_promo_rate'
            cat_spend_col = f'{category}_spend'
            
            if cat_discount_col in df.columns:
                high_loyal_cat = df[df['loyalty_level'] == '高']
                low_loyal_cat = df[df['loyalty_level'] == '低']
                
                category_analysis[category] = {
                    'high_loyal_avg_discount': high_loyal_cat[cat_discount_col].mean(),
                    'low_loyal_avg_discount': low_loyal_cat[cat_discount_col].mean(),
                    'high_loyal_promo_rate': high_loyal_cat[cat_promo_col].mean(),
                    'low_loyal_promo_rate': low_loyal_cat[cat_promo_col].mean(),
                    'high_loyal_spend': high_loyal_cat[cat_spend_col].mean(),
                    'low_loyal_spend': low_loyal_cat[cat_spend_col].mean(),
                    'discount_correlation': df[cat_discount_col].corr(df['loyalty_numeric']),
                    'promo_correlation': df[cat_promo_col].corr(df['loyalty_numeric'])
                }
        price_promotion_analysis['category'] = category_analysis
        
        promo_types = [col for col in df.columns if col.startswith('promotion_used_')]
        promo_analysis = {}
        for promo_type in promo_types:
            promo_name = promo_type.replace('promotion_used_', '')
            promo_analysis[promo_name] = {
                'high_loyal_usage': df[df['loyalty_level'] == '高'][promo_type].mean(),
                'low_loyal_usage': df[df['loyalty_level'] == '低'][promo_type].mean(),
                'correlation': df[promo_type].corr(df['loyalty_numeric'])
            }
        price_promotion_analysis['promotion_types'] = promo_analysis
        
        segment_price_analysis = {}
        for segment in df['segment'].unique():
            seg_df = df[df['segment'] == segment]
            segment_price_analysis[segment] = {
                'avg_price_sensitivity': seg_df['price_sensitivity'].mean(),
                'avg_promo_responsiveness': seg_df['promotion_responsiveness'].mean(),
                'promo_purchase_rate': seg_df['promotion_purchase_rate'].mean(),
                'high_loyal_ratio': (seg_df['loyalty_level'] == '高').mean()
            }
        price_promotion_analysis['segments'] = segment_price_analysis
        
        return price_promotion_analysis
    
    def partial_dependence_analysis(self, df, features):
        feature_names = [str(col) for col in self.feature_names]
        X = df[feature_names].copy()
        X.columns = X.columns.astype(str)
        X_scaled = self.scaler.transform(X.values)
        
        pd_results = {}
        
        for feature in features[:5]:
            feature_idx = self.feature_names.index(feature)
            
            pdp, values = partial_dependence(
                self.model, X_scaled, features=[feature_idx],
                grid_resolution=20, method='auto'
            )
            
            original_values = df[feature].quantile(np.linspace(0, 1, 20)).values
            
            pd_results[feature] = {
                'values': original_values,
                'partial_dependence': pdp[0]
            }
        
        return pd_results
    
    def segment_attribution_analysis(self, df, importance_results):
        segments = df['segment'].unique()
        segment_results = {}
        
        for segment in segments:
            segment_df = df[df['segment'] == segment]
            if len(segment_df) > 50:
                segment_results[segment] = self.analyze_factor_impact(
                    segment_df, importance_results, segment
                )
        
        return segment_results
    
    def generate_strategy_recommendations(self, importance_df, factor_impact_df, churn_drivers_df):
        recommendations = []
        
        positive_drivers = factor_impact_df[factor_impact_df['correlation_with_loyalty'] > 0.1]
        negative_drivers = factor_impact_df[factor_impact_df['correlation_with_loyalty'] < -0.1]
        
        for _, row in positive_drivers.head(5).iterrows():
            recommendations.append({
                'type': 'enhance',
                'factor': row['factor'],
                'impact': row['correlation_with_loyalty'],
                'strategy': f"提升 {self._translate_feature_name(row['factor'])}，每提升1单位可提升忠诚度 {row['correlation_with_loyalty']:.2f}",
                'priority': 'high' if abs(row['correlation_with_loyalty']) > 0.3 else 'medium'
            })
        
        for _, row in negative_drivers.head(3).iterrows():
            recommendations.append({
                'type': 'mitigate',
                'factor': row['factor'],
                'impact': row['correlation_with_loyalty'],
                'strategy': f"降低 {self._translate_feature_name(row['factor'])}，每降低1单位可提升忠诚度 {-row['correlation_with_loyalty']:.2f}",
                'priority': 'high' if abs(row['correlation_with_loyalty']) > 0.3 else 'medium'
            })
        
        significant_churn = churn_drivers_df[churn_drivers_df['is_significant']]
        for _, row in significant_churn.head(3).iterrows():
            recommendations.append({
                'type': 'churn_prevention',
                'factor': row['factor'],
                'impact': row['percent_difference'],
                'strategy': f"重点关注 {self._translate_feature_name(row['factor'])}，低忠诚度用户比高忠诚度用户高出 {row['percent_difference']:.1f}%",
                'priority': 'high'
            })
        
        return pd.DataFrame(recommendations)
    
    def _translate_feature_name(self, feature_name):
        translations = {
            'frequency': '购买频次',
            'total_spend': '总消费金额',
            'avg_nps': 'NPS评分',
            'recency_days': '最近购买天数',
            'complaint_count': '投诉次数',
            'unresolved_complaints': '未解决投诉数',
            'avg_customer_service': '客户服务评分',
            'return_rate': '退货率',
            'unresolved_rate': '未解决投诉率',
            'total_interactions': '互动次数',
            'tenure_days': '客户留存天数',
            'avg_order_value': '平均客单价',
            'repurchase_rate': '复购率',
            'avg_product_quality': '产品质量评分',
            'avg_ease_of_use': '易用性评分',
            'spend_growth_rate': '消费增长率',
            'App Visit': 'APP访问次数',
            'Click-Through': '点击率',
            'Email Open': '邮件打开率',
            'Social Media': '社交媒体互动',
            'Support Call': '客服电话次数',
            'price_sensitivity': '价格敏感度',
            'promotion_responsiveness': '促销响应度',
            'avg_discount_pct': '平均折扣率',
            'max_discount_pct': '最高折扣率',
            'total_discount_amount': '累计折扣金额',
            'promotion_purchase_rate': '促销购买占比',
            'promotion_purchase_count': '促销购买次数',
            'avg_base_price': '平均基准价格',
            'total_base_value': '累计基准价值',
            'avg_final_price': '平均实际支付价格',
            'price_value_ratio': '价格价值比',
            'savings_consciousness': '省钱意识指数',
            'deal_hunter_score': '淘优惠倾向指数',
            'value_seeker_score': '价值寻求指数',
            'promo_sensitivity': '促销敏感度',
            'only_promo_buyer': '纯促销购买者',
            'never_promo_buyer': '非促销购买者',
            'high_price_sensitivity': '高价格敏感型',
            'low_price_sensitivity': '低价格敏感型'
        }
        return translations.get(feature_name, feature_name)
    
    def run_full_attribution_analysis(self, features_with_clusters, data_dict):
        print("Preparing attribution data with price and promotion features...")
        attribution_df = self.prepare_attribution_data(features_with_clusters, data_dict)
        
        print("Identifying key features...")
        importance_results = self.identify_key_features(attribution_df)
        
        print("Running SHAP analysis...")
        shap_results = self.shap_analysis(attribution_df)
        
        print("Analyzing factor impact...")
        factor_impact = self.analyze_factor_impact(attribution_df, importance_results)
        
        print("Analyzing churn drivers with price and promotion factors...")
        churn_drivers = self.attribute_churn_drivers(attribution_df)
        
        print("Analyzing price and promotion impact...")
        price_promotion_impact = self.analyze_price_promotion_impact(attribution_df, data_dict)
        
        print("Running segment-wise attribution...")
        segment_attribution = self.segment_attribution_analysis(attribution_df, importance_results)
        
        print("Generating strategy recommendations...")
        recommendations = self.generate_strategy_recommendations(
            importance_results['importance_df'],
            factor_impact,
            churn_drivers
        )
        
        return {
            'attribution_df': attribution_df,
            'importance_results': importance_results,
            'shap_results': shap_results,
            'factor_impact': factor_impact,
            'churn_drivers': churn_drivers,
            'price_promotion_impact': price_promotion_impact,
            'segment_attribution': segment_attribution,
            'recommendations': recommendations
        }
