import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')


class LoyaltyIndexCalculator:
    def __init__(self):
        self.weights = {
            'repurchase': 0.30,
            'nps': 0.25,
            'complaint': 0.15,
            'engagement': 0.15,
            'value': 0.15
        }
        
    def calculate_repurchase_score(self, df):
        metrics = df.copy()
        
        scaler = MinMaxScaler()
        
        metrics['freq_score'] = scaler.fit_transform(metrics[['frequency']])
        metrics['recency_score'] = 1 - scaler.fit_transform(metrics[['recency_days']])
        metrics['tenure_score'] = scaler.fit_transform(metrics[['tenure_days']])
        
        metrics['repurchase_prob_score'] = metrics['repurchase_probability'].fillna(metrics['repurchase_probability'].mean())
        
        metrics['repurchase_subscore'] = (
            metrics['freq_score'] * 0.35 +
            metrics['recency_score'] * 0.25 +
            metrics['tenure_score'] * 0.20 +
            metrics['repurchase_prob_score'] * 0.20
        )
        
        return metrics['repurchase_subscore']
    
    def calculate_nps_score(self, df):
        metrics = df.copy()
        
        scaler = MinMaxScaler()
        
        def classify_nps(score):
            if pd.isna(score):
                return 0
            elif score >= 9:
                return 1
            elif score >= 7:
                return 0
            else:
                return -1
        
        metrics['nps_category'] = metrics['avg_nps'].apply(classify_nps)
        
        total = len(metrics)
        promoters = (metrics['nps_category'] == 1).sum()
        detractors = (metrics['nps_category'] == -1).sum()
        passives = (metrics['nps_category'] == 0).sum()
        
        nps_overall = ((promoters - detractors) / total) * 100
        
        metrics['raw_nps_score'] = metrics['avg_nps'].fillna(metrics['avg_nps'].mean())
        metrics['nps_raw_score'] = scaler.fit_transform(metrics[['raw_nps_score']])
        
        metrics['ease_score'] = scaler.fit_transform(metrics[['avg_ease_of_use']].fillna(3))
        metrics['quality_score'] = scaler.fit_transform(metrics[['avg_product_quality']].fillna(3))
        metrics['service_score'] = scaler.fit_transform(metrics[['avg_customer_service']].fillna(3))
        
        metrics['nps_subscore'] = (
            metrics['nps_raw_score'] * 0.50 +
            metrics['ease_score'] * 0.18 +
            metrics['quality_score'] * 0.18 +
            metrics['service_score'] * 0.14
        )
        
        return metrics['nps_subscore']
    
    def calculate_complaint_score(self, df):
        metrics = df.copy()
        
        scaler = MinMaxScaler()
        
        metrics['complaint_count'] = metrics['complaint_count'].fillna(0)
        metrics['unresolved_complaints'] = metrics['unresolved_complaints'].fillna(0)
        metrics['unresolved_rate'] = metrics['unresolved_rate'].fillna(0)
        metrics['avg_resolution_time'] = metrics['avg_resolution_time'].fillna(0)
        
        metrics['has_complaint'] = (metrics['complaint_count'] > 0).astype(int)
        
        metrics['complaint_count_norm'] = 1 - scaler.fit_transform(metrics[['complaint_count']])
        metrics['unresolved_norm'] = 1 - scaler.fit_transform(metrics[['unresolved_complaints']])
        metrics['unresolved_rate_norm'] = 1 - scaler.fit_transform(metrics[['unresolved_rate']])
        
        max_time = metrics['avg_resolution_time'].max()
        if max_time > 0:
            metrics['resolution_time_norm'] = 1 - (metrics['avg_resolution_time'] / max_time)
        else:
            metrics['resolution_time_norm'] = 1
        
        metrics['no_complaint_bonus'] = (1 - metrics['has_complaint']) * 0.3
        
        metrics['complaint_subscore'] = (
            metrics['complaint_count_norm'] * 0.30 +
            metrics['unresolved_norm'] * 0.30 +
            metrics['unresolved_rate_norm'] * 0.20 +
            metrics['resolution_time_norm'] * 0.20
        ) + metrics['no_complaint_bonus']
        
        metrics['complaint_subscore'] = metrics['complaint_subscore'].clip(0, 1)
        
        return metrics['complaint_subscore']
    
    def calculate_engagement_score(self, df):
        metrics = df.copy()
        
        scaler = MinMaxScaler()
        
        metrics['total_interactions'] = metrics['total_interactions'].fillna(0)
        metrics['avg_duration'] = metrics['avg_duration'].fillna(0)
        
        interaction_cols = ['Email Open', 'Click-Through', 'Social Media', 'Support Call', 'App Visit']
        for col in interaction_cols:
            if col not in metrics.columns:
                metrics[col] = 0
            else:
                metrics[col] = metrics[col].fillna(0)
        
        metrics['interaction_score'] = scaler.fit_transform(metrics[['total_interactions']])
        metrics['duration_score'] = scaler.fit_transform(metrics[['avg_duration']])
        
        quality_interactions = metrics['Click-Through'] + metrics['App Visit']
        total_interactions = metrics['total_interactions'].replace(0, 1)
        metrics['interaction_quality'] = quality_interactions / total_interactions
        
        metrics['diversity_score'] = (metrics[interaction_cols] > 0).sum(axis=1) / len(interaction_cols)
        
        metrics['engagement_subscore'] = (
            metrics['interaction_score'] * 0.40 +
            metrics['duration_score'] * 0.20 +
            metrics['interaction_quality'] * 0.25 +
            metrics['diversity_score'] * 0.15
        )
        
        return metrics['engagement_subscore']
    
    def calculate_value_score(self, df):
        metrics = df.copy()
        
        scaler = MinMaxScaler()
        
        metrics['total_spend'] = metrics['total_spend'].fillna(metrics['total_spend'].mean())
        metrics['avg_order_value'] = metrics['avg_order_value'].fillna(metrics['avg_order_value'].mean())
        metrics['return_rate'] = metrics['return_rate'].fillna(0)
        metrics['discount_usage'] = metrics['discount_usage'].fillna(metrics['discount_usage'].mean())
        
        metrics['spend_score'] = scaler.fit_transform(metrics[['total_spend']])
        metrics['aov_score'] = scaler.fit_transform(metrics[['avg_order_value']])
        metrics['return_score'] = 1 - scaler.fit_transform(metrics[['return_rate']])
        metrics['premium_score'] = 1 - scaler.fit_transform(metrics[['discount_usage']])
        
        if 'spend_growth_rate' in metrics.columns:
            metrics['spend_growth_rate'] = metrics['spend_growth_rate'].fillna(0)
            metrics['growth_score'] = scaler.fit_transform(metrics[['spend_growth_rate']].clip(-1, 1))
        else:
            metrics['growth_score'] = 0.5
        
        metrics['value_subscore'] = (
            metrics['spend_score'] * 0.35 +
            metrics['aov_score'] * 0.25 +
            metrics['return_score'] * 0.15 +
            metrics['premium_score'] * 0.15 +
            metrics['growth_score'] * 0.10
        )
        
        return metrics['value_subscore']
    
    def calculate_loyalty_index(self, df, survival_data=None):
        metrics = df.copy()
        
        if survival_data is not None:
            survival_cols = ['repurchase_probability', 'avg_inter_purchase_days']
            for col in survival_cols:
                if col in survival_data.columns:
                    metrics = metrics.merge(
                        survival_data[['customer_id', col]],
                        on='customer_id',
                        how='left'
                    )
        
        if 'repurchase_probability' not in metrics.columns:
            metrics['repurchase_probability'] = metrics['repurchase_rate']
        
        if 'spend_growth_rate' not in metrics.columns:
            metrics['spend_growth_rate'] = 0
        
        print("Calculating repurchase score...")
        metrics['repurchase_score'] = self.calculate_repurchase_score(metrics)
        
        print("Calculating NPS score...")
        metrics['nps_score'] = self.calculate_nps_score(metrics)
        
        print("Calculating complaint score...")
        metrics['complaint_score'] = self.calculate_complaint_score(metrics)
        
        print("Calculating engagement score...")
        metrics['engagement_score'] = self.calculate_engagement_score(metrics)
        
        print("Calculating value score...")
        metrics['value_score'] = self.calculate_value_score(metrics)
        
        print("Computing overall loyalty index...")
        metrics['loyalty_index'] = (
            metrics['repurchase_score'] * self.weights['repurchase'] +
            metrics['nps_score'] * self.weights['nps'] +
            metrics['complaint_score'] * self.weights['complaint'] +
            metrics['engagement_score'] * self.weights['engagement'] +
            metrics['value_score'] * self.weights['value']
        )
        
        metrics['loyalty_index'] = metrics['loyalty_index'] * 100
        
        metrics['loyalty_tier'] = pd.cut(
            metrics['loyalty_index'],
            bins=[-1, 40, 70, 101],
            labels=['低忠诚度', '中忠诚度', '高忠诚度']
        )
        
        return metrics
    
    def get_index_summary(self, metrics_df):
        overall_summary = {
            'avg_loyalty_index': metrics_df['loyalty_index'].mean(),
            'median_loyalty_index': metrics_df['loyalty_index'].median(),
            'std_loyalty_index': metrics_df['loyalty_index'].std(),
            'min_loyalty_index': metrics_df['loyalty_index'].min(),
            'max_loyalty_index': metrics_df['loyalty_index'].max()
        }
        
        tier_distribution = metrics_df['loyalty_tier'].value_counts().reset_index()
        tier_distribution.columns = ['tier', 'count']
        tier_distribution['percentage'] = tier_distribution['count'] / len(metrics_df) * 100
        
        tier_summary = metrics_df.groupby('loyalty_tier').agg({
            'loyalty_index': ['mean', 'std', 'min', 'max'],
            'repurchase_score': 'mean',
            'nps_score': 'mean',
            'complaint_score': 'mean',
            'engagement_score': 'mean',
            'value_score': 'mean',
            'customer_id': 'count'
        }).reset_index()
        
        tier_summary.columns = [
            '忠诚度层级', '平均指数', '指数标准差', '最小指数', '最大指数',
            '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分', '用户数量'
        ]
        tier_summary['用户占比'] = tier_summary['用户数量'] / tier_summary['用户数量'].sum()
        
        return {
            'overall': overall_summary,
            'tier_distribution': tier_distribution,
            'tier_summary': tier_summary
        }
    
    def get_segment_indices(self, metrics_df, segment_col='segment'):
        segment_indices = metrics_df.groupby(segment_col).agg({
            'loyalty_index': ['mean', 'std', 'count'],
            'repurchase_score': 'mean',
            'nps_score': 'mean',
            'complaint_score': 'mean',
            'engagement_score': 'mean',
            'value_score': 'mean'
        }).reset_index()
        
        segment_indices.columns = [
            '细分群体', '平均忠诚度指数', '指数标准差', '用户数量',
            '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分'
        ]
        
        segment_indices = segment_indices.sort_values('平均忠诚度指数', ascending=False)
        
        return segment_indices
    
    def get_channel_indices(self, metrics_df, channel_col='channel'):
        channel_indices = metrics_df.groupby(channel_col).agg({
            'loyalty_index': ['mean', 'std', 'count'],
            'repurchase_score': 'mean',
            'nps_score': 'mean',
            'complaint_score': 'mean',
            'engagement_score': 'mean',
            'value_score': 'mean'
        }).reset_index()
        
        channel_indices.columns = [
            '渠道', '平均忠诚度指数', '指数标准差', '用户数量',
            '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分'
        ]
        
        channel_indices = channel_indices.sort_values('平均忠诚度指数', ascending=False)
        
        return channel_indices
    
    def identify_at_risk_customers(self, metrics_df, threshold=40):
        at_risk = metrics_df[metrics_df['loyalty_index'] < threshold].copy()
        
        at_risk = at_risk.sort_values('loyalty_index')
        
        return at_risk
    
    def identify_loyalty_leaders(self, metrics_df, threshold=80):
        leaders = metrics_df[metrics_df['loyalty_index'] >= threshold].copy()
        
        leaders = leaders.sort_values('loyalty_index', ascending=False)
        
        return leaders
    
    def _identify_user_preferences(self, user_row, purchases_df, interactions_df):
        customer_id = user_row['customer_id']
        
        user_purchases = purchases_df[purchases_df['customer_id'] == customer_id]
        user_interactions = interactions_df[interactions_df['customer_id'] == customer_id]
        
        preferences = {}
        
        if len(user_purchases) > 0:
            category_counts = user_purchases['product_category'].value_counts()
            preferences['top_categories'] = category_counts.head(3).index.tolist()
            
            total_category_spend = user_purchases.groupby('product_category')['purchase_amount'].sum()
            preferences['top_spend_categories'] = total_category_spend.sort_values(ascending=False).head(3).index.tolist()
            
            avg_discount = user_purchases['discount_pct'].mean()
            promo_rate = user_purchases['is_promotion'].mean()
            preferences['price_sensitivity_level'] = 'high' if user_row.get('price_sensitivity', 0.5) > 0.7 else (
                'low' if user_row.get('price_sensitivity', 0.5) < 0.3 else 'medium'
            )
            preferences['promotion_responsiveness'] = 'high' if user_row.get('promotion_responsiveness', 0.5) > 0.7 else (
                'low' if user_row.get('promotion_responsiveness', 0.5) < 0.3 else 'medium'
            )
            preferences['avg_discount_used'] = avg_discount
            preferences['promotion_purchase_rate'] = promo_rate
            preferences['only_promo_buyer'] = promo_rate >= 0.8
            preferences['never_promo_buyer'] = promo_rate <= 0.1
            
            if len(user_purchases) >= 2:
                user_purchases_sorted = user_purchases.sort_values('purchase_date')
                inter_purchase_days = (user_purchases_sorted['purchase_date'] - user_purchases_sorted['purchase_date'].shift(1)).dt.days
                preferences['avg_inter_purchase_days'] = inter_purchase_days.mean()
                preferences['purchase_frequency_level'] = 'frequent' if inter_purchase_days.mean() < 30 else (
                    'infrequent' if inter_purchase_days.mean() > 90 else 'moderate'
                )
            else:
                preferences['purchase_frequency_level'] = 'new'
            
            if 'promotion_type' in user_purchases.columns:
                promo_type_counts = user_purchases[user_purchases['is_promotion'] == 1]['promotion_type'].value_counts()
                if len(promo_type_counts) > 0:
                    preferences['preferred_promo_types'] = promo_type_counts.head(2).index.tolist()
                else:
                    preferences['preferred_promo_types'] = []
            
            avg_order_value = user_purchases['purchase_amount'].mean()
            preferences['avg_order_value'] = avg_order_value
            preferences['spending_level'] = 'high' if avg_order_value > 200 else (
                'low' if avg_order_value < 50 else 'medium'
            )
            preferences['total_spend'] = user_purchases['purchase_amount'].sum()
            
            return_rate = user_purchases['is_returned'].mean()
            preferences['return_rate'] = return_rate
            
            last_purchase = user_purchases['purchase_date'].max()
            days_since_last = (pd.to_datetime('2025-12-31') - last_purchase).days
            preferences['days_since_last_purchase'] = days_since_last
            preferences['activity_level'] = 'active' if days_since_last < 30 else (
                'inactive' if days_since_last > 90 else 'moderate'
            )
        
        if len(user_interactions) > 0:
            interaction_types = user_interactions['interaction_type'].value_counts()
            preferences['preferred_interaction_types'] = interaction_types.head(2).index.tolist()
            
            avg_duration = user_interactions['duration_seconds'].mean()
            preferences['engagement_level'] = 'high' if avg_duration > 120 else (
                'low' if avg_duration < 30 else 'medium'
            )
        
        return preferences
    
    def _generate_single_user_recommendation(self, user_row, preferences, attribution_results):
        tier = user_row['loyalty_tier']
        price_sensitivity = preferences.get('price_sensitivity_level', 'medium')
        promo_responsiveness = preferences.get('promotion_responsiveness', 'medium')
        top_categories = preferences.get('top_categories', [])
        spending_level = preferences.get('spending_level', 'medium')
        activity_level = preferences.get('activity_level', 'moderate')
        purchase_frequency = preferences.get('purchase_frequency_level', 'moderate')
        preferred_promo_types = preferences.get('preferred_promo_types', [])
        
        recommendations = {
            'customer_id': user_row['customer_id'],
            'loyalty_tier': tier,
            'loyalty_index': user_row['loyalty_index'],
            'user_segment': self._classify_user_segment(user_row, preferences),
            'preferences': preferences,
            'personalized_strategies': [],
            'product_recommendations': [],
            'promotion_recommendations': [],
            'communication_recommendations': [],
            'expected_outcome': '',
            'priority_score': 0
        }
        
        strategies = []
        
        if tier == '高忠诚度':
            if spending_level == 'high':
                strategies.append({
                    'type': 'upsell',
                    'strategy': '邀请加入VIP尊享计划，提供专属定制服务和高端产品优先体验权',
                    'expected_impact': '提升客单价 20-30%'
                })
            if len(top_categories) >= 2:
                cross_sell_msg = f"基于您对{top_categories[0]}和{top_categories[1]}的偏好，推荐配套组合产品"
                strategies.append({
                    'type': 'cross_sell',
                    'strategy': cross_sell_msg,
                    'expected_impact': '增加购买品类广度'
                })
            if activity_level == 'active':
                strategies.append({
                    'type': 'advocacy',
                    'strategy': '邀请成为品牌大使，享受推荐奖励和专属社群权益',
                    'expected_impact': '获得3-5个新客户推荐'
                })
            strategies.append({
                'type': 'retention',
                'strategy': '定期寄送专属会员杂志和新品小样，强化品牌归属感',
                'expected_impact': '降低流失率 5-10%'
            })
            
        elif tier == '中忠诚度':
            if purchase_frequency == 'moderate' or purchase_frequency == 'infrequent':
                category_msg = f"针对您偏好的{top_categories[0] if top_categories else '热门'}品类，发送补货提醒和专属优惠"
                strategies.append({
                    'type': 'repurchase',
                    'strategy': category_msg,
                    'expected_impact': '提升复购频次 15-25%'
                })
            
            if price_sensitivity == 'high':
                strategies.append({
                    'type': 'promotion',
                    'strategy': '加入价格保护计划，降价自动退差价，享受会员专享折扣',
                    'expected_impact': '提升转化率 10-20%'
                })
            elif price_sensitivity == 'low':
                strategies.append({
                    'type': 'premium',
                    'strategy': '推荐品质升级路线，提供新品优先购买和免费试用机会',
                    'expected_impact': '提升客单价 15-25%'
                })
            
            if promo_responsiveness == 'high':
                preferred_promo = preferred_promo_types[0] if preferred_promo_types else '满减优惠'
                strategies.append({
                    'type': 'promotion',
                    'strategy': f'定期发送{preferred_promo}信息，提升购买频次',
                    'expected_impact': '提升促销响应率 20-30%'
                })
            
            strategies.append({
                'type': 'upgrade',
                'strategy': '设置成长目标，达成后升级至高忠诚度会员，解锁更多权益',
                'expected_impact': '30%概率升级至高忠诚度'
            })
            
        else:
            if activity_level == 'inactive':
                days_since = preferences.get('days_since_last_purchase', 90)
                winback_msg = f"您已{days_since}天未购买，专属回归礼包等您领取"
                strategies.append({
                    'type': 'winback',
                    'strategy': winback_msg,
                    'expected_impact': '召回率 15-25%'
                })
            
            if preferences.get('return_rate', 0) > 0.1:
                strategies.append({
                    'type': 'service',
                    'strategy': '主动回访了解退货原因，提供一对一产品咨询服务',
                    'expected_impact': '降低退货率 10-15%'
                })
            
            if price_sensitivity == 'high' or preferences.get('only_promo_buyer', False):
                strategies.append({
                    'type': 'value',
                    'strategy': '推荐高性价比组合套装，提供首次购买免息分期',
                    'expected_impact': '提升首单转化率 20-30%'
                })
            elif price_sensitivity == 'low':
                strategies.append({
                    'type': 'trial',
                    'strategy': '提供高端产品线免费试用，建立品质认知',
                    'expected_impact': '提升转化率 15-20%'
                })
            
            strategies.append({
                'type': 'onboarding',
                'strategy': '完善新客户引导流程，首次购买后7天内主动跟进使用体验',
                'expected_impact': '提升留存率 10-20%'
            })
        
        product_recs = []
        for category in top_categories[:3]:
            product_recs.append({
                'category': category,
                'recommendation_type': 'personalized',
                'rationale': f'基于您{category}品类的历史购买偏好'
            })
            if len(top_categories) >= 2 and top_categories.index(category) == 0:
                product_recs.append({
                    'category': top_categories[1],
                    'recommendation_type': 'complementary',
                    'rationale': f'与{category}搭配购买的用户推荐'
                })
        
        promo_recs = []
        if promo_responsiveness == 'high':
            if preferred_promo_types:
                for promo_type in preferred_promo_types[:2]:
                    promo_recs.append({
                        'promo_type': promo_type,
                        'target_category': top_categories[0] if top_categories else '全部',
                        'rationale': f'您对{promo_type}促销响应率最高'
                    })
            else:
                promo_recs.append({
                    'promo_type': 'Direct Discount',
                    'target_category': top_categories[0] if top_categories else '全部',
                    'rationale': '推荐直接折扣促销'
                })
        
        comm_recs = []
        preferred_channels = preferences.get('preferred_interaction_types', [])
        if 'App Visit' in preferred_channels:
            comm_recs.append({'channel': 'APP推送', 'frequency': '每周1-2次', 'best_time': '工作日晚间'})
        if 'Email Open' in preferred_channels:
            comm_recs.append({'channel': '电子邮件', 'frequency': '每周1次', 'best_time': '周二上午'})
        if 'Social Media' in preferred_channels:
            comm_recs.append({'channel': '社交媒体', 'frequency': '每周2-3次', 'best_time': '周末下午'})
        
        if tier == '高忠诚度':
            expected_outcome = '预计在3个月内客户终身价值提升15-25%'
            priority = 5
        elif tier == '中忠诚度':
            expected_outcome = '预计在3个月内20-30%的概率升级至高忠诚度'
            priority = 4
        else:
            expected_outcome = '预计在3个月内15-20%的概率被成功激活'
            priority = 3 if activity_level == 'inactive' else 2
        
        recommendations['personalized_strategies'] = strategies
        recommendations['product_recommendations'] = product_recs[:3]
        recommendations['promotion_recommendations'] = promo_recs[:2]
        recommendations['communication_recommendations'] = comm_recs[:2]
        recommendations['expected_outcome'] = expected_outcome
        recommendations['priority_score'] = priority
        
        return recommendations
    
    def _classify_user_segment(self, user_row, preferences):
        price_sens = preferences.get('price_sensitivity_level', 'medium')
        promo_resp = preferences.get('promotion_responsiveness', 'medium')
        spending = preferences.get('spending_level', 'medium')
        frequency = preferences.get('purchase_frequency_level', 'moderate')
        engagement = preferences.get('engagement_level', 'medium')
        
        if price_sens == 'low' and spending == 'high' and engagement == 'high':
            return '高价值品质追求型'
        elif price_sens == 'high' and promo_resp == 'high':
            return '价格敏感促销驱动型'
        elif frequency == 'frequent' and spending == 'medium':
            return '稳定复购理性消费型'
        elif engagement == 'high' and spending == 'medium':
            return '深度互动潜力成长型'
        elif preferences.get('only_promo_buyer', False):
            return '纯促销薅羊毛型'
        elif preferences.get('activity_level', '') == 'inactive':
            return '沉睡待激活型'
        elif preferences.get('return_rate', 0) > 0.15:
            return '高退货风险犹豫型'
        else:
            return '普通大众消费型'
    
    def generate_personalized_recommendations(self, metrics_df, data_dict, attribution_results, top_n=100):
        purchases_df = data_dict['purchases']
        interactions_df = data_dict['interactions']
        
        purchases_df['purchase_date'] = pd.to_datetime(purchases_df['purchase_date'])
        interactions_df['interaction_date'] = pd.to_datetime(interactions_df['interaction_date'])
        
        all_recommendations = []
        
        sample_users = metrics_df.sort_values('loyalty_index', ascending=False).head(top_n // 3)
        sample_users = pd.concat([
            sample_users,
            metrics_df[metrics_df['loyalty_tier'] == '中忠诚度'].sample(min(top_n // 3, len(metrics_df[metrics_df['loyalty_tier'] == '中忠诚度'])), random_state=42),
            metrics_df[metrics_df['loyalty_tier'] == '低忠诚度'].sort_values('loyalty_index').head(top_n // 3)
        ])
        
        print(f"Generating personalized recommendations for {len(sample_users)} users...")
        
        for _, user_row in sample_users.iterrows():
            preferences = self._identify_user_preferences(user_row, purchases_df, interactions_df)
            recommendation = self._generate_single_user_recommendation(user_row, preferences, attribution_results)
            all_recommendations.append(recommendation)
        
        return pd.DataFrame(all_recommendations)
    
    def generate_segment_recommendations(self, metrics_df, data_dict, attribution_results):
        segment_strategies = {}
        
        price_sensitivity_segments = ['high', 'medium', 'low']
        promo_responsiveness_segments = ['high', 'medium', 'low']
        
        for price_seg in price_sensitivity_segments:
            for promo_seg in promo_responsiveness_segments:
                segment_name = f'价格{price_seg}_促销{promo_seg}'
                
                price_mask = metrics_df['price_sensitivity'] > 0.7 if price_seg == 'high' else (
                    metrics_df['price_sensitivity'] < 0.3 if price_seg == 'low' else 
                    (metrics_df['price_sensitivity'] >= 0.3) & (metrics_df['price_sensitivity'] <= 0.7)
                )
                
                promo_mask = metrics_df['promotion_responsiveness'] > 0.7 if promo_seg == 'high' else (
                    metrics_df['promotion_responsiveness'] < 0.3 if promo_seg == 'low' else 
                    (metrics_df['promotion_responsiveness'] >= 0.3) & (metrics_df['promotion_responsiveness'] <= 0.7)
                )
                
                segment_users = metrics_df[price_mask & promo_mask]
                
                if len(segment_users) >= 50:
                    avg_loyalty = segment_users['loyalty_index'].mean()
                    avg_spend = segment_users['total_spend'].mean()
                    
                    strategies = []
                    
                    if price_seg == 'high' and promo_seg == 'high':
                        strategies = [
                            '建立价格提醒机制，降价时第一时间通知',
                            '推出组合优惠套装，提升单次购买金额',
                            '设置积分兑换体系，增强用户粘性',
                            '定期发送优惠券和促销活动信息'
                        ]
                    elif price_seg == 'low' and promo_seg == 'low':
                        strategies = [
                            '强调产品品质和品牌价值，弱化价格因素',
                            '提供高端产品线和限量版产品',
                            '建立专属服务团队，提供个性化服务',
                            '邀请参加品牌活动和新品发布会'
                        ]
                    elif price_seg == 'high' and promo_seg == 'low':
                        strategies = [
                            '推出每日低价策略，减少促销频率',
                            '建立价格匹配保障，消除用户比价顾虑',
                            '推荐高性价比产品，强调物超所值',
                            '提供会员专享价，区别于普通用户'
                        ]
                    elif price_seg == 'low' and promo_seg == 'high':
                        strategies = [
                            '推出会员专享礼遇和生日礼物',
                            '利用促销活动推荐高端产品试用',
                            '建立VIP积分体系，兑换独家权益',
                            '邀请参加产品试用和评测活动'
                        ]
                    elif price_seg == 'medium' and promo_seg == 'medium':
                        strategies = [
                            '提供多样化的产品选择，覆盖不同价位',
                            '组合使用促销活动和品质宣传',
                            '建立完善的客户反馈机制',
                            '提供灵活的购买方式和付款选项'
                        ]
                    
                    segment_strategies[segment_name] = {
                        'user_count': len(segment_users),
                        'avg_loyalty_index': avg_loyalty,
                        'avg_total_spend': avg_spend,
                        'segment_description': f'价格敏感度{price_seg}，促销响应度{promo_seg}',
                        'targeted_strategies': strategies,
                        'tier_distribution': segment_users['loyalty_tier'].value_counts().to_dict()
                    }
        
        return segment_strategies
    
    def generate_tiered_strategies(self, metrics_df, attribution_results):
        strategies = {}
        
        high_loyal = metrics_df[metrics_df['loyalty_tier'] == '高忠诚度']
        medium_loyal = metrics_df[metrics_df['loyalty_tier'] == '中忠诚度']
        low_loyal = metrics_df[metrics_df['loyalty_tier'] == '低忠诚度']
        
        high_price_sens = high_loyal['price_sensitivity'].mean() if 'price_sensitivity' in high_loyal.columns else 0.5
        high_promo_resp = high_loyal['promotion_responsiveness'].mean() if 'promotion_responsiveness' in high_loyal.columns else 0.5
        
        strategies['高忠诚度'] = {
            'count': len(high_loyal),
            'avg_index': high_loyal['loyalty_index'].mean(),
            'avg_price_sensitivity': high_price_sens,
            'avg_promotion_responsiveness': high_promo_resp,
            'focus': '维持与增值',
            'key_strategies': [
                '推出专属会员计划和VIP礼遇，按价格敏感度分层服务',
                '建立品牌大使计划，鼓励口碑传播，给予推荐奖励',
                '提供早鸟优惠和限量产品优先购买权，针对高价值用户',
                '定期收集反馈，优化产品和服务体验，提升NPS',
                '推出交叉销售和向上销售策略，基于品类偏好推荐',
                '对价格敏感的高忠诚用户提供专属价格保护'
            ],
            'expected_impact': '提升客户终身价值 15-25%',
            'key_metrics': ['推荐率', '消费增长', '互动频率', '品类扩展率']
        }
        
        med_price_sens = medium_loyal['price_sensitivity'].mean() if 'price_sensitivity' in medium_loyal.columns else 0.5
        med_promo_resp = medium_loyal['promotion_responsiveness'].mean() if 'promotion_responsiveness' in medium_loyal.columns else 0.5
        
        strategies['中忠诚度'] = {
            'count': len(medium_loyal),
            'avg_index': medium_loyal['loyalty_index'].mean(),
            'avg_price_sensitivity': med_price_sens,
            'avg_promotion_responsiveness': med_promo_resp,
            'focus': '提升与转化',
            'key_strategies': [
                '分析购买模式和品类偏好，推送个性化产品推荐',
                '提供忠诚度积分和奖励计划，根据价格敏感度差异化设置',
                '开展针对性的促销活动提升复购，匹配用户促销响应度',
                '主动跟进客户满意度，解决潜在问题，降低流失风险',
                '优化关键触点体验，提升NPS评分',
                '对价格敏感用户重点推送折扣信息，对品质用户推荐高端产品'
            ],
            'expected_impact': '20-30% 的用户可升级至高忠诚度',
            'key_metrics': ['复购率', 'NPS提升', '投诉率下降', '升级转化率']
        }
        
        low_price_sens = low_loyal['price_sensitivity'].mean() if 'price_sensitivity' in low_loyal.columns else 0.5
        low_promo_resp = low_loyal['promotion_responsiveness'].mean() if 'promotion_responsiveness' in low_loyal.columns else 0.5
        
        strategies['低忠诚度'] = {
            'count': len(low_loyal),
            'avg_index': low_loyal['loyalty_index'].mean(),
            'avg_price_sensitivity': low_price_sens,
            'avg_promotion_responsiveness': low_promo_resp,
            'focus': '挽回与激活',
            'key_strategies': [
                '开展赢回活动，根据价格敏感度提供差异化优惠',
                '深入分析流失原因，针对性改进产品和服务',
                '简化购买流程，降低首次购买门槛，提供新人礼遇',
                '主动联系，了解不满并快速解决，提升服务体验',
                '提供试用或小样，重新建立信任，对品质用户重点推荐',
                '对促销响应度高的用户发送限时优惠，促活转化'
            ],
            'expected_impact': '可挽回 15-20% 的低忠诚度用户',
            'key_metrics': ['召回率', '首单转化率', '投诉解决率', '激活率']
        }
        
        if 'factor_impact' in attribution_results:
            factor_impact = attribution_results['factor_impact']
            
            positive_factors = factor_impact[factor_impact['correlation_with_loyalty'] > 0.2]['factor'].tolist()
            negative_factors = factor_impact[factor_impact['correlation_with_loyalty'] < -0.1]['factor'].tolist()
            
            for tier in strategies:
                strategies[tier]['positive_drivers'] = positive_factors[:3]
                strategies[tier]['negative_drivers'] = negative_factors[:2]
        
        return strategies
    
    def run_full_index_calculation(self, features_with_clusters, data_dict, survival_data=None, attribution_results=None):
        print("Preparing metrics data with price and promotion features...")
        
        attribution_df = attribution_results.get('attribution_df', None) if attribution_results else None
        
        if attribution_df is not None:
            merge_cols = ['customer_id', 'spend_growth_rate', 'price_sensitivity', 
                          'promotion_responsiveness', 'avg_discount_pct', 'promotion_purchase_rate',
                          'deal_hunter_score', 'savings_consciousness', 'promo_sensitivity',
                          'only_promo_buyer', 'high_price_sensitivity', 'low_price_sensitivity']
            merge_cols = [col for col in merge_cols if col in attribution_df.columns]
            metrics_df = features_with_clusters.merge(
                attribution_df[merge_cols],
                on='customer_id',
                how='left'
            )
        else:
            metrics_df = features_with_clusters.copy()
            metrics_df['spend_growth_rate'] = 0
            metrics_df['price_sensitivity'] = 0.5
            metrics_df['promotion_responsiveness'] = 0.5
            metrics_df['avg_discount_pct'] = 0
            metrics_df['promotion_purchase_rate'] = 0
            metrics_df['deal_hunter_score'] = 0
            metrics_df['savings_consciousness'] = 0
            metrics_df['promo_sensitivity'] = 0
            metrics_df['only_promo_buyer'] = 0
            metrics_df['high_price_sensitivity'] = 0
            metrics_df['low_price_sensitivity'] = 0
        
        if survival_data is not None:
            survival_additional = ['dynamic_churn_threshold', 'active_categories', 
                                   'primary_category', 'threshold_group']
            survival_merge = [col for col in survival_additional if col in survival_data.columns]
            if survival_merge:
                metrics_df = metrics_df.merge(
                    survival_data[['customer_id'] + survival_merge],
                    on='customer_id',
                    how='left'
                )
        
        print("Calculating loyalty index...")
        metrics_with_index = self.calculate_loyalty_index(metrics_df, survival_data)
        
        print("Generating summary statistics...")
        index_summary = self.get_index_summary(metrics_with_index)
        
        print("Calculating segment indices...")
        segment_indices = self.get_segment_indices(metrics_with_index)
        
        print("Calculating channel indices...")
        channel_indices = self.get_channel_indices(metrics_with_index)
        
        print("Identifying at-risk customers...")
        at_risk_customers = self.identify_at_risk_customers(metrics_with_index)
        
        print("Identifying loyalty leaders...")
        loyalty_leaders = self.identify_loyalty_leaders(metrics_with_index)
        
        print("Generating tiered strategies with price/promotion insights...")
        tiered_strategies = self.generate_tiered_strategies(metrics_with_index, attribution_results or {})
        
        print("Generating price/promotion segment strategies...")
        segment_recommendations = self.generate_segment_recommendations(
            metrics_with_index, data_dict, attribution_results or {}
        )
        
        print("Generating personalized user recommendations (top 100 users)...")
        personalized_recommendations = self.generate_personalized_recommendations(
            metrics_with_index, data_dict, attribution_results or {}, top_n=100
        )
        
        return {
            'metrics_with_index': metrics_with_index,
            'index_summary': index_summary,
            'segment_indices': segment_indices,
            'channel_indices': channel_indices,
            'at_risk_customers': at_risk_customers,
            'loyalty_leaders': loyalty_leaders,
            'tiered_strategies': tiered_strategies,
            'segment_recommendations': segment_recommendations,
            'personalized_recommendations': personalized_recommendations
        }
