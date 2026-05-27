import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class MarketingSimulator:
    def __init__(self, bg_nbd_model, gamma_gamma_model, ltv_data):
        self.bg_nbd = bg_nbd_model
        self.gamma_gamma = gamma_gamma_model
        self.ltv_data = ltv_data
        
        self.coupon_types = {
            '满减券': {'discount_pct': 0.1, 'min_purchase': 100, 'purchase_boost': 1.2},
            '折扣券': {'discount_pct': 0.15, 'min_purchase': 0, 'purchase_boost': 1.15},
            '免邮券': {'discount_pct': 0, 'min_purchase': 0, 'purchase_boost': 1.05},
            '满赠券': {'discount_pct': 0, 'min_purchase': 200, 'purchase_boost': 1.25},
            '新人券': {'discount_pct': 0.2, 'min_purchase': 50, 'purchase_boost': 1.3}
        }
        
        self.segment_response_rates = {
            '高价值客户': {'purchase_intent_boost': 1.1, 'avg_amount_boost': 1.05},
            '中高价值客户': {'purchase_intent_boost': 1.2, 'avg_amount_boost': 1.08},
            '中价值客户': {'purchase_intent_boost': 1.3, 'avg_amount_boost': 1.1},
            '中低价值客户': {'purchase_intent_boost': 1.35, 'avg_amount_boost': 1.12},
            '低价值客户': {'purchase_intent_boost': 1.4, 'avg_amount_boost': 1.15}
        }
    
    def simulate_coupon_impact(self, coupon_type='满减券', target_segment=None, 
                               coverage_rate=0.3, future_months=3):
        if coupon_type not in self.coupon_types:
            raise ValueError(f"不支持的优惠券类型: {coupon_type}")
        
        coupon_config = self.coupon_types[coupon_type]
        
        if target_segment:
            target_mask = self.ltv_data['segment_name'] == target_segment
        else:
            target_mask = pd.Series(True, index=self.ltv_data.index)
        
        n_target = target_mask.sum()
        n_coupon = int(n_target * coverage_rate)
        
        selected_indices = self.ltv_data[target_mask].sample(
            n=min(n_coupon, n_target), random_state=42).index
        
        coupon_received = pd.Series(False, index=self.ltv_data.index)
        coupon_received.loc[selected_indices] = True
        
        baseline_purchases = self.ltv_data['predicted_purchases'].values
        baseline_amount = self.ltv_data['predicted_avg_amount'].values
        
        adjusted_purchases = baseline_purchases.copy()
        adjusted_amount = baseline_amount.copy()
        adjusted_ltv = self.ltv_data['ltv'].values.copy()
        
        segment_column = 'segment_name' if 'segment_name' in self.ltv_data.columns else 'segment'
        
        for idx in self.ltv_data.index:
            if coupon_received[idx]:
                segment_name = self.ltv_data.loc[idx, segment_column]
                if segment_name in self.segment_response_rates:
                    response = self.segment_response_rates[segment_name]
                    
                    purchase_boost = coupon_config['purchase_boost'] * response['purchase_intent_boost']
                    amount_boost = 1 + coupon_config['discount_pct'] * response['avg_amount_boost']
                    
                    adjusted_purchases[idx] = baseline_purchases[idx] * purchase_boost
                    adjusted_amount[idx] = baseline_amount[idx] * amount_boost
                    
                    monthly_factor = 1 + (future_months - 1) * 0.1
                    adjusted_ltv[idx] = adjusted_purchases[idx] * adjusted_amount[idx] * monthly_factor
        
        result = pd.DataFrame({
            'customer_id': self.ltv_data['customer_id'].values,
            'coupon_received': coupon_received.values,
            'baseline_ltv': self.ltv_data['ltv'].values,
            'adjusted_ltv': adjusted_ltv,
            'ltv_change': adjusted_ltv - self.ltv_data['ltv'].values,
            'ltv_change_pct': (adjusted_ltv - self.ltv_data['ltv'].values) / self.ltv_data['ltv'].values * 100,
            'baseline_purchases': baseline_purchases,
            'adjusted_purchases': adjusted_purchases,
            'baseline_amount': baseline_amount,
            'adjusted_amount': adjusted_amount,
            'segment': self.ltv_data[segment_column].values if segment_column in self.ltv_data.columns else self.ltv_data['segment'].values
        })
        
        return result
    
    def compare_coupon_strategies(self, strategies, future_months=3):
        results = []
        
        for strategy in strategies:
            sim_result = self.simulate_coupon_impact(
                coupon_type=strategy.get('coupon_type', '满减券'),
                target_segment=strategy.get('target_segment'),
                coverage_rate=strategy.get('coverage_rate', 0.3),
                future_months=future_months
            )
            
            coupon_users = sim_result[sim_result['coupon_received'] == True]
            
            results.append({
                'strategy_name': strategy.get('name', strategy.get('coupon_type', '默认策略')),
                'coupon_type': strategy.get('coupon_type', '满减券'),
                'target_segment': strategy.get('target_segment', '全部'),
                'coverage_rate': strategy.get('coverage_rate', 0.3),
                'coupon_users': len(coupon_users),
                'total_ltv_change': sim_result['ltv_change'].sum(),
                'avg_ltv_change_pct': coupon_users['ltv_change_pct'].mean() if len(coupon_users) > 0 else 0,
                'total_incremental_ltv': sim_result['ltv_change'].sum(),
                'coupon_cost': len(coupon_users) * 20
            })
        
        results_df = pd.DataFrame(results)
        results_df['roi'] = results_df['total_incremental_ltv'] / results_df['coupon_cost']
        
        return results_df
    
    def generate_coupon_recommendations(self, segment_stats):
        recommendations = []
        
        for _, row in segment_stats.iterrows():
            segment_name = row['segment_name']
            churn_rate = row.get('churn_rate', 0)
            
            if '高价值' in segment_name:
                if churn_rate > 0.1:
                    recommendations.append({
                        'segment': segment_name,
                        'suggested_coupon': '满减券',
                        'reason': '高价值客户流失率较高，需维护忠诚度',
                        'coverage_rate': 0.5,
                        'priority': '高'
                    })
                else:
                    recommendations.append({
                        'segment': segment_name,
                        'suggested_coupon': 'None',
                        'reason': '高价值客户活跃度良好，无需额外激励',
                        'coverage_rate': 0,
                        'priority': '低'
                    })
            elif '中价值' in segment_name:
                recommendations.append({
                    'segment': segment_name,
                    'suggested_coupon': '满赠券',
                    'reason': '中价值客户有提升空间，建议促活',
                    'coverage_rate': 0.4,
                    'priority': '中'
                })
            else:
                recommendations.append({
                    'segment': segment_name,
                    'suggested_coupon': '新人券',
                    'reason': '低价值客户转化率低，建议促转化',
                    'coverage_rate': 0.3,
                    'priority': '中低'
                })
        
        return recommendations
    
    def simulate_marketing_campaign(self, campaign_config, future_months=6):
        target_segment = campaign_config.get('target_segment')
        coupon_type = campaign_config.get('coupon_type', '满减券')
        campaign_duration = campaign_config.get('duration_months', 1)
        coverage_rate = campaign_config.get('coverage_rate', 0.3)
        additional_features = campaign_config.get('additional_features', {})
        
        sim_result = self.simulate_coupon_impact(
            coupon_type=coupon_type,
            target_segment=target_segment,
            coverage_rate=coverage_rate,
            future_months=campaign_duration
        )
        
        campaign_impact = {
            'campaign_name': campaign_config.get('name', '未命名活动'),
            'target_segment': target_segment or '全部',
            'coupon_type': coupon_type,
            'duration_months': campaign_duration,
            'coverage_rate': coverage_rate,
            'total_reach': len(sim_result[sim_result['coupon_received'] == True]),
            'total_ltv_increase': sim_result['ltv_change'].sum(),
            'avg_ltv_increase_pct': sim_result[sim_result['coupon_received'] == True]['ltv_change_pct'].mean(),
            'estimated_cost': len(sim_result[sim_result['coupon_received'] == True]) * 15,
            'estimated_roi': sim_result['ltv_change'].sum() / (len(sim_result[sim_result['coupon_received'] == True]) * 15)
        }
        
        return sim_result, campaign_impact


if __name__ == '__main__':
    print("营销活动模拟模块已加载")
