import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class RetentionStrategyEngine:
    def __init__(self, segmented_df, feature_cols, coef_df):
        self.segmented_df = segmented_df
        self.feature_cols = feature_cols
        self.coef_df = coef_df
        
        self.strategy_templates = {
            '高风险': [
                {
                    'id': 'discount_20_off',
                    'name': '20元专属优惠券',
                    'type': 'coupon',
                    'description': '针对高风险用户的专属优惠券，刺激立即使用可降低流失风险',
                    'target_features': ['total_purchases', 'discount_usage_ratio'],
                    'expected_churn_reduction': 0.15,
                    'cost_per_user': 20,
                    'roi': 3.5,
                    'channels': ['push', 'email', 'sms'],
                    'duration_days': 7,
                    'urgency': 'high'
                },
                {
                    'id': 'vip_trial',
                    'name': '7天VIP会员体验',
                    'type': 'membership',
                    'description': '免费体验VIP会员服务，提升用户体验付费功能和专属服务',
                    'target_features': ['has_subscription', 'avg_session_duration'],
                    'expected_churn_reduction': 0.20,
                    'cost_per_user': 50,
                    'roi': 4.0,
                    'channels': ['push', 'email'],
                    'duration_days': 7,
                    'urgency': 'high'
                },
                {
                    'id': 'customer_care',
                    'name': '专属客户关怀',
                    'type': 'service',
                    'description': '一对一客户关怀，了解流失原因，解决问题',
                    'target_features': ['customer_service_calls', 'days_since_last_activity'],
                    'expected_churn_reduction': 0.25,
                    'cost_per_user': 100,
                    'roi': 2.8,
                    'channels': ['phone', 'email'],
                    'duration_days': 14,
                    'urgency': 'high'
                },
                {
                    'id': 'bundled_offer',
                    'name': '限时捆绑优惠',
                    'type': 'bundle',
                    'description': '热门商品捆绑销售，享受额外折扣',
                    'target_features': ['total_purchases', 'avg_order_value'],
                    'expected_churn_reduction': 0.18,
                    'cost_per_user': 35,
                    'roi': 3.2,
                    'channels': ['push', 'email', 'app'],
                    'duration_days': 10,
                    'urgency': 'medium'
                }
            ],
            '中风险': [
                {
                    'id': 'discount_10_off',
                    'name': '10元满减优惠券',
                    'type': 'coupon',
                    'description': '满减优惠券，鼓励继续消费',
                    'target_features': ['login_frequency', 'pages_per_session'],
                    'expected_churn_reduction': 0.10,
                    'cost_per_user': 10,
                    'roi': 4.0,
                    'channels': ['push', 'email'],
                    'duration_days': 14,
                    'urgency': 'medium'
                },
                {
                    'id': 'points_bonus',
                    'name': '积分双倍活动',
                    'type': 'points',
                    'description': '指定时间段内消费积分双倍，增强粘性',
                    'target_features': ['product_reviews_count', 'social_shares'],
                    'expected_churn_reduction': 0.12,
                    'cost_per_user': 15,
                    'roi': 4.5,
                    'channels': ['push', 'app'],
                    'duration_days': 30,
                    'urgency': 'medium'
                },
                {
                    'id': 'exclusive_content',
                    'name': '专属内容推荐',
                    'type': 'content',
                    'description': '个性化内容和精选商品推荐，提升活跃度',
                    'target_features': ['pages_per_session', 'login_frequency'],
                    'expected_churn_reduction': 0.08,
                    'cost_per_user': 5,
                    'roi': 6.0,
                    'channels': ['email', 'app'],
                    'duration_days': 21,
                    'urgency': 'low'
                },
                {
                    'id': 'referral_program',
                    'name': '好友推荐奖励',
                    'type': 'referral',
                    'description': '推荐好友获得奖励，建立社区归属感',
                    'target_features': ['social_shares', 'has_subscription'],
                    'expected_churn_reduction': 0.10,
                    'cost_per_user': 25,
                    'roi': 5.0,
                    'channels': ['push', 'app'],
                    'duration_days': 60,
                    'urgency': 'low'
                }
            ],
            '低风险': [
                {
                    'id': 'loyalty_program',
                    'name': '忠诚度计划升级',
                    'type': 'loyalty',
                    'description': '升级会员等级，享受更多特权',
                    'target_features': ['total_purchases', 'has_subscription'],
                    'expected_churn_reduction': 0.05,
                    'cost_per_user': 30,
                    'roi': 5.5,
                    'channels': ['email', 'app'],
                    'duration_days': 90,
                    'urgency': 'low'
                },
                {
                    'id': 'early_access',
                    'name': '新品优先体验',
                    'type': 'exclusive',
                    'description': '新品优先购买权和专属折扣',
                    'target_features': ['product_reviews_count', 'avg_order_value'],
                    'expected_churn_reduction': 0.06,
                    'cost_per_user': 20,
                    'roi': 4.8,
                    'channels': ['email'],
                    'duration_days': 30,
                    'urgency': 'low'
                },
                {
                    'id': 'community_invite',
                    'name': '高端社区邀请',
                    'type': 'community',
                    'description': '邀请加入专属用户社区',
                    'target_features': ['social_shares', 'has_subscription'],
                    'expected_churn_reduction': 0.04,
                    'cost_per_user': 10,
                    'roi': 7.0,
                    'channels': ['email'],
                    'duration_days': 60,
                    'urgency': 'low'
                }
            ]
        }
        
        self.campaign_templates = [
            {
                'id': 'new_user_onboarding',
                'name': '新用户专享活动',
                'description': '针对新注册用户的引导和激励活动',
                'target_segment': '高风险',
                'trigger_condition': 'account_age_days < 60',
                'duration_days': 30,
                'strategies': ['discount_20_off', 'vip_trial'],
                'expected_roi': 4.2
            },
            {
                'id': 'dormant_reactivation',
                'name': '沉睡用户唤醒',
                'description': '针对长时间未活跃用户的召回活动',
                'target_segment': '高风险',
                'trigger_condition': 'days_since_last_activity > 30',
                'duration_days': 14,
                'strategies': ['discount_20_off', 'customer_care'],
                'expected_roi': 3.8
            },
            {
                'id': 'holiday_promotion',
                'name': '节日促销活动',
                'description': '节假日全员促销活动',
                'target_segment': '全部',
                'trigger_condition': None,
                'duration_days': 7,
                'strategies': ['discount_10_off', 'points_bonus', 'bundled_offer'],
                'expected_roi': 5.0
            },
            {
                'id': 'membership_renewal',
                'name': '会员续费优惠',
                'description': '会员到期前的续费提醒和优惠',
                'target_segment': '中风险',
                'trigger_condition': 'has_subscription == 1',
                'duration_days': 14,
                'strategies': ['vip_trial', 'loyalty_program'],
                'expected_roi': 4.5
            }
        ]
    
    def get_strategies_for_segment(self, risk_group, top_n=None):
        strategies = self.strategy_templates.get(risk_group, [])
        if top_n:
            strategies = sorted(strategies, key=lambda x: x['roi'], reverse=True)[:top_n]
        return strategies
    
    def recommend_strategies_for_user(self, user_row, top_n=3):
        risk_group = user_row['risk_group']
        strategies = self.get_strategies_for_segment(risk_group)
        
        user_features = user_row[self.feature_cols]
        scored_strategies = []
        
        for strategy in strategies:
            score = 0
            for feature in strategy['target_features']:
                if feature in user_features:
                    feature_coef = self.coef_df[self.coef_df['feature'] == feature]['coef'].values
                    if len(feature_coef) > 0:
                        user_val = user_row[feature]
                        feature_mean = self.segmented_df[feature].mean()
                        if feature_coef[0] > 0:
                            if user_val > feature_mean:
                                score += 1
                        else:
                            if user_val < feature_mean:
                                score += 1
            
            final_score = score / len(strategy['target_features']) if strategy['target_features'] else 0
            strategy_with_score = strategy.copy()
            strategy_with_score['match_score'] = final_score
            strategy_with_score['adjusted_roi'] = strategy['roi'] * (0.5 + final_score * 0.5)
            scored_strategies.append(strategy_with_score)
        
        scored_strategies = sorted(scored_strategies, key=lambda x: x['adjusted_roi'], reverse=True)
        
        return scored_strategies[:top_n]
    
    def generate_campaign_plan(self, risk_group, budget=10000):
        segment_users = self.segmented_df[self.segmented_df['risk_group'] == risk_group]
        n_users = len(segment_users)
        
        strategies = self.get_strategies_for_segment(risk_group)
        
        plan = []
        remaining_budget = budget
        total_reach = 0
        expected_saved = 0
        
        for strategy in strategies:
            if remaining_budget >= strategy['cost_per_user']:
                max_users = int(remaining_budget / strategy['cost_per_user'])
                users_reach = min(max_users, n_users)
                cost = users_reach * strategy['cost_per_user']
                users_saved = users_reach * strategy['expected_churn_reduction']
                
                plan.append({
                    'strategy': strategy['name'],
                    'strategy_id': strategy['id'],
                    'users_reached': users_reach,
                    'total_cost': cost,
                    'expected_users_saved': users_saved,
                    'expected_roi': strategy['roi']
                })
                
                remaining_budget -= cost
                total_reach += users_reach
                expected_saved += users_saved
                
                if remaining_budget < min([s['cost_per_user'] for s in strategies]):
                    break
        
        return {
            'risk_group': risk_group,
            'total_budget': budget,
            'used_budget': budget - remaining_budget,
            'remaining_budget': remaining_budget,
            'total_users_reached': total_reach,
            'total_expected_users_saved': expected_saved,
            'overall_expected_roi': (expected_saved * 500) / (budget - remaining_budget) if (budget - remaining_budget) > 0 else 0,
            'strategies': plan
        }
    
    def simulate_campaign_impact(self, strategy_id, user_indices=None):
        if user_indices is None:
            target_users = self.segmented_df[self.segmented_df['risk_group'] == '高风险']
        else:
            target_users = self.segmented_df.loc[user_indices]
        
        all_strategies = []
        for strategies in self.strategy_templates.values():
            all_strategies.extend(strategies)
        
        strategy = next((s for s in all_strategies if s['id'] == strategy_id), None)
        
        if strategy is None:
            return None
        
        n_users = len(target_users)
        original_churn = target_users['churn_prob_30d'].mean()
        expected_reduction = strategy['expected_churn_reduction']
        new_churn = max(0, original_churn - expected_reduction)
        
        return {
            'strategy': strategy,
            'target_users': n_users,
            'original_avg_churn_30d': original_churn,
            'expected_avg_churn_30d': new_churn,
            'churn_reduction': expected_reduction,
            'total_cost': n_users * strategy['cost_per_user'],
            'expected_roi': strategy['roi']
        }
    
    def get_segment_profile(self, risk_group):
        segment_users = self.segmented_df[self.segmented_df['risk_group'] == risk_group]
        
        profile = {
            'user_count': len(segment_users),
            'avg_churn_30d': segment_users['churn_prob_30d'].mean(),
            'avg_risk_score': segment_users['risk_score'].mean(),
            'key_characteristics': []
        }
        
        risk_factors = self.coef_df[self.coef_df['coef'] > 0]['feature'].tolist()
        protective_factors = self.coef_df[self.coef_df['coef'] < 0]['feature'].tolist()
        
        for f in risk_factors[:5]:
            if f in self.feature_cols:
                segment_mean = segment_users[f].mean()
                overall_mean = self.segmented_df[f].mean()
                deviation = (segment_mean - overall_mean) / overall_mean if overall_mean != 0 else 0
                if abs(deviation) > 0.1:
                    profile['key_characteristics'].append({
                        'feature': f,
                        'segment_mean': segment_mean,
                        'overall_mean': overall_mean,
                        'deviation_pct': deviation * 100,
                        'type': 'risk'
                    })
        
        for f in protective_factors[:3]:
            if f in self.feature_cols:
                segment_mean = segment_users[f].mean()
                overall_mean = self.segmented_df[f].mean()
                deviation = (segment_mean - overall_mean) / overall_mean if overall_mean != 0 else 0
                if abs(deviation) > 0.1:
                    profile['key_characteristics'].append({
                        'feature': f,
                        'segment_mean': segment_mean,
                        'overall_mean': overall_mean,
                        'deviation_pct': deviation * 100,
                        'type': 'protective'
                    })
        
        return profile
    
    def generate_action_items(self, risk_group):
        profile = self.get_segment_profile(risk_group)
        strategies = self.get_strategies_for_segment(risk_group)
        
        actions = []
        
        for char in profile['key_characteristics'][:3]:
            if char['type'] == 'risk' and char['deviation_pct'] > 0:
                actions.append({
                    'priority': 'high',
                    'action': f"降低{char['feature']}相关的用户",
                    'description': f"该群体{char['feature']}均值超出整体{char['deviation_pct']:.1f}%，建议针对性优化",
                    'suggested_strategies': [s['name'] for s in strategies[:2]]
                })
            elif char['type'] == 'protective' and char['deviation_pct'] < 0:
                actions.append({
                    'priority': 'medium',
                    'action': f"提升{char['feature']}相关的用户",
                    'description': f"该群体{char['feature']}低于整体{abs(char['deviation_pct']):.1f}%，建议加强引导",
                    'suggested_strategies': [s['name'] for s in strategies[1:3]]
                })
        
        return actions
