import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from scipy.optimize import minimize, linprog
from sklearn.linear_model import LinearRegression


class BudgetOptimizer:
    def __init__(self):
        pass
    
    def optimize_budget(self, influencer_df: pd.DataFrame, total_budget: float,
                        campaign_df: pd.DataFrame = None,
                        min_budget_per_influencer: float = 1000,
                        risk_tolerance: str = 'medium') -> Dict:
        df = influencer_df.copy()
        
        if campaign_df is not None and len(campaign_df) > 0:
            df = self._add_historical_performance(df, campaign_df)
        else:
            df['predicted_roi'] = self._predict_roi_based_on_metrics(df)
        
        df['efficiency_score'] = df['predicted_roi'] * (df['influence_score'] / 100)
        
        if risk_tolerance == 'conservative':
            df['adjusted_score'] = df['efficiency_score'] * 0.7 + (1 / df['cooperation_price']) * 10000 * 0.3
        elif risk_tolerance == 'aggressive':
            df['adjusted_score'] = df['efficiency_score'] * 0.9 + df['influence_score'] * 0.01
        else:
            df['adjusted_score'] = df['efficiency_score']
        
        df = df.sort_values('adjusted_score', ascending=False)
        
        allocation = self._knapsack_allocation(df, total_budget, min_budget_per_influencer)
        
        return {
            'allocation': allocation,
            'total_allocated': sum(item['allocated_budget'] for item in allocation),
            'expected_roi': sum(item['expected_roi'] for item in allocation) / len(allocation),
            'number_of_influencers': len(allocation),
            'budget_utilization': sum(item['allocated_budget'] for item in allocation) / total_budget * 100
        }
    
    def _add_historical_performance(self, influencer_df: pd.DataFrame, 
                                     campaign_df: pd.DataFrame) -> pd.DataFrame:
        influencer_roi = campaign_df.groupby('influencer_id').agg({
            'roi': 'mean',
            'conversions': 'sum'
        }).reset_index()
        
        df = influencer_df.merge(influencer_roi, left_on='id', right_on='influencer_id', how='left')
        df['predicted_roi'] = df['roi'].fillna(self._predict_roi_based_on_metrics(df))
        return df
    
    def _predict_roi_based_on_metrics(self, df: pd.DataFrame) -> pd.Series:
        base_roi = 50
        engagement_factor = (df['engagement_rate'] / df['engagement_rate'].mean()) * 30
        influence_factor = (df['influence_score'] / 100) * 20
        price_factor = (1 / (df['cooperation_price'] / df['cooperation_price'].mean())) * 15
        
        predicted_roi = base_roi + engagement_factor + influence_factor + price_factor
        return predicted_roi.clip(0, 300)
    
    def _knapsack_allocation(self, df: pd.DataFrame, total_budget: float,
                              min_budget: float) -> List[Dict]:
        allocation = []
        remaining_budget = total_budget
        
        for _, row in df.iterrows():
            if remaining_budget <= 0:
                break
            
            influencer_budget = min(row['cooperation_price'] * 1.2, remaining_budget)
            
            if influencer_budget >= min_budget:
                allocation.append({
                    'influencer_id': row['id'],
                    'influencer_name': row['name'],
                    'platform': row['platform'],
                    'category': row['category'],
                    'followers': row['followers'],
                    'influence_score': row['influence_score'],
                    'base_price': row['cooperation_price'],
                    'allocated_budget': round(influencer_budget, 2),
                    'expected_roi': round(row['predicted_roi'] if 'predicted_roi' in row else 50, 2),
                    'budget_percentage': round(influencer_budget / total_budget * 100, 2)
                })
                remaining_budget -= influencer_budget
        
        return allocation
    
    def optimize_by_platform(self, influencer_df: pd.DataFrame, total_budget: float,
                             platform_weights: Dict[str, float] = None) -> Dict:
        if platform_weights is None:
            platform_weights = {
                'TikTok': 0.3,
                'Xiaohongshu': 0.25,
                'Weibo': 0.2,
                'Instagram': 0.15,
                'YouTube': 0.1
            }
        
        platform_allocation = {}
        
        for platform, weight in platform_weights.items():
            platform_influencers = influencer_df[influencer_df['platform'] == platform]
            if len(platform_influencers) > 0:
                platform_budget = total_budget * weight
                result = self.optimize_budget(platform_influencers, platform_budget)
                platform_allocation[platform] = {
                    'budget': platform_budget,
                    'weight': weight * 100,
                    'influencers': result['allocation'],
                    'expected_roi': result['expected_roi']
                }
        
        return platform_allocation
    
    def generate_budget_scenarios(self, influencer_df: pd.DataFrame, 
                                   base_budget: float) -> Dict:
        scenarios = {
            'conservative': self.optimize_budget(influencer_df, base_budget * 0.7, risk_tolerance='conservative'),
            'moderate': self.optimize_budget(influencer_df, base_budget, risk_tolerance='medium'),
            'aggressive': self.optimize_budget(influencer_df, base_budget * 1.5, risk_tolerance='aggressive')
        }
        
        return scenarios


class RecommendationEngine:
    def __init__(self):
        pass
    
    def generate_cooperation_recommendation(self, influencer_details: Dict,
                                              target_demographics: Dict = None) -> Dict:
        score = influencer_details['influence_metrics']['influence_score']
        tier = influencer_details['influence_metrics']['influence_tier']
        
        recommendations = {
            'cooperation_type': self._recommend_cooperation_type(score, tier),
            'recommended_budget': self._recommend_budget(score, influencer_details['basic_info']['followers']),
            'content_suggestions': self._suggest_content_types(influencer_details),
            'cooperation_priority': self._determine_priority(score),
            'expected_outcomes': self._predict_outcomes(influencer_details),
            'risk_assessment': self._assess_risk(influencer_details)
        }
        
        if target_demographics:
            recommendations['demographic_fit'] = self._assess_demographic_fit(
                influencer_details, target_demographics
            )
        
        return recommendations
    
    def _recommend_cooperation_type(self, score: float, tier: str) -> List[str]:
        types = []
        
        if 'S级' in tier or score >= 80:
            types.extend(['年度品牌大使', '系列内容合作', '直播专场', '新品首发'])
        elif 'A级' in tier or score >= 65:
            types.extend(['季度合作', '主题内容植入', '联合直播', '产品评测'])
        elif 'B级' in tier or score >= 50:
            types.extend(['单次内容合作', '产品置换', '合集推荐', '短平快推广'])
        else:
            types.extend(['试用测评', '图文种草', '小红书笔记', '朋友圈分享'])
        
        return types
    
    def _recommend_budget(self, score: float, followers: int) -> Dict:
        base_price = followers * 0.02
        
        if score >= 80:
            multiplier = 1.5
        elif score >= 65:
            multiplier = 1.2
        elif score >= 50:
            multiplier = 1.0
        else:
            multiplier = 0.8
        
        return {
            'recommended_single_budget': int(base_price * multiplier),
            'budget_range': f"{int(base_price * multiplier * 0.7)} - {int(base_price * multiplier * 1.3)}",
            'price_per_1000_followers': round(base_price * multiplier / followers * 1000, 2)
        }
    
    def _suggest_content_types(self, influencer_details: Dict) -> List[str]:
        suggestions = []
        category = influencer_details['basic_info']['category']
        platform = influencer_details['basic_info']['platform']
        
        category_content_map = {
            '美妆': ['妆容教程', '产品测评', '好物分享', '妆教视频'],
            '时尚': ['穿搭分享', 'OOTD', '品牌开箱', '潮流解析'],
            '美食': ['探店vlog', '美食测评', '食谱分享', '做饭教程'],
            '旅行': ['旅行vlog', '攻略分享', '酒店测评', '景点推荐'],
            '科技': ['产品开箱', '深度评测', '对比视频', '技巧教程'],
            '健身': ['健身教程', '训练计划', '饮食分享', '装备测评']
        }
        
        platform_content_map = {
            'TikTok': ['短视频', '挑战赛', '直播', '合拍'],
            'Xiaohongshu': ['图文笔记', '好物合集', '教程分享', '评测'],
            'Weibo': ['话题互动', '长图文', '直播', '抽奖活动'],
            'Instagram': ['美图分享', '故事互动', 'Reels', '直播'],
            'YouTube': ['长视频', 'vlog', '深度评测', '教程系列']
        }
        
        if category in category_content_map:
            suggestions.extend(category_content_map[category])
        if platform in platform_content_map:
            suggestions.extend(platform_content_map[platform])
        
        return list(set(suggestions))[:6]
    
    def _determine_priority(self, score: float) -> str:
        if score >= 80:
            return "P0 - 最高优先级，优先锁定合作"
        elif score >= 65:
            return "P1 - 高优先级，重点合作对象"
        elif score >= 50:
            return "P2 - 中优先级，补充合作渠道"
        else:
            return "P3 - 低优先级，测试性合作"
    
    def _predict_outcomes(self, influencer_details: Dict) -> Dict:
        score = influencer_details['influence_metrics']['influence_score']
        followers = influencer_details['basic_info']['followers']
        
        base_views = followers * 0.2
        base_engagement = base_views * 0.05
        base_conversions = base_engagement * 0.02
        
        score_factor = score / 60
        
        return {
            'expected_views': int(base_views * score_factor),
            'expected_engagement': int(base_engagement * score_factor),
            'expected_conversions': int(base_conversions * score_factor),
            'expected_reach_rate': round(base_views / followers * 100 * score_factor, 2),
            'confidence_level': '高' if score > 60 else '中' if score > 40 else '低'
        }
    
    def _assess_risk(self, influencer_details: Dict) -> Dict:
        risks = []
        risk_level = '低'
        
        engagement_score = influencer_details['influence_metrics']['engagement_score']
        growth_score = influencer_details['influence_metrics']['growth_score']
        
        if engagement_score < 30:
            risks.append('互动率偏低，可能存在粉丝质量问题')
            risk_level = '中'
        
        if growth_score < 30:
            risks.append('账号增长放缓，影响力可能下降')
            risk_level = '中'
        
        if not risks:
            risks.append('无明显风险点')
        
        return {
            'overall_risk_level': risk_level,
            'risk_factors': risks,
            'mitigation_suggestions': [
                '建议先进行小规模测试合作',
                '签订详细的合作协议保障权益',
                '建立效果监控机制'
            ]
        }
    
    def _assess_demographic_fit(self, influencer_details: Dict, 
                                 target_demographics: Dict) -> Dict:
        return {
            'fit_score': 75,
            'matching_characteristics': ['年龄层匹配', '地域分布匹配'],
            'gaps': ['性别比例略有差异'],
            'recommendation': '整体匹配度良好，适合合作'
        }


class PerformanceForecaster:
    def __init__(self):
        pass
    
    def forecast_campaign_performance(self, influencer_df: pd.DataFrame,
                                       budget_allocation: List[Dict],
                                       campaign_duration: int = 30) -> Dict:
        total_reach = 0
        total_engagement = 0
        total_conversions = 0
        total_cost = 0
        
        for allocation in budget_allocation:
            influencer = influencer_df[influencer_df['id'] == allocation['influencer_id']].iloc[0]
            
            budget_factor = allocation['allocated_budget'] / allocation['base_price']
            duration_factor = campaign_duration / 30
            
            reach = influencer['avg_views'] * budget_factor * duration_factor * np.random.uniform(0.8, 1.2)
            engagement = reach * (influencer['engagement_rate'] / 100)
            conversions = engagement * np.random.uniform(0.02, 0.08)
            
            total_reach += reach
            total_engagement += engagement
            total_conversions += conversions
            total_cost += allocation['allocated_budget']
        
        forecast = {
            'total_expected_reach': int(total_reach),
            'total_expected_impressions': int(total_reach * np.random.uniform(1.3, 1.8)),
            'total_expected_engagement': int(total_engagement),
            'total_expected_conversions': int(total_conversions),
            'total_cost': total_cost,
            'expected_roi': round((total_conversions * 300 - total_cost) / total_cost * 100, 2),
            'expected_cpa': round(total_cost / total_conversions, 2) if total_conversions > 0 else 0,
            'confidence_interval': {
                'lower_bound': 0.7,
                'upper_bound': 1.4
            }
        }
        
        return forecast
    
    def compare_strategies(self, influencer_df: pd.DataFrame, 
                            strategies: Dict[str, List[Dict]]) -> pd.DataFrame:
        comparison = []
        
        for strategy_name, allocation in strategies.items():
            forecast = self.forecast_campaign_performance(influencer_df, allocation)
            comparison.append({
                'strategy': strategy_name,
                'number_of_influencers': len(allocation),
                'total_budget': sum(item['allocated_budget'] for item in allocation),
                'expected_reach': forecast['total_expected_reach'],
                'expected_engagement': forecast['total_expected_engagement'],
                'expected_conversions': forecast['total_expected_conversions'],
                'expected_roi': forecast['expected_roi']
            })
        
        return pd.DataFrame(comparison)


class AudienceOverlapOptimizer:
    def __init__(self):
        self.platform_overlap_matrix = {
            ('TikTok', 'Xiaohongshu'): 0.35,
            ('TikTok', 'Weibo'): 0.25,
            ('TikTok', 'Instagram'): 0.15,
            ('TikTok', 'YouTube'): 0.20,
            ('Xiaohongshu', 'Weibo'): 0.40,
            ('Xiaohongshu', 'Instagram'): 0.25,
            ('Xiaohongshu', 'YouTube'): 0.15,
            ('Weibo', 'Instagram'): 0.30,
            ('Weibo', 'YouTube'): 0.20,
            ('Instagram', 'YouTube'): 0.35
        }
        
        self.category_overlap_matrix = {
            ('美妆', '时尚'): 0.45,
            ('美妆', '美食'): 0.25,
            ('美妆', '旅行'): 0.20,
            ('美妆', '健身'): 0.30,
            ('时尚', '美食'): 0.25,
            ('时尚', '旅行'): 0.30,
            ('时尚', '健身'): 0.35,
            ('美食', '旅行'): 0.35,
            ('美食', '生活方式'): 0.40,
            ('旅行', '生活方式'): 0.35,
            ('科技', '游戏'): 0.45,
            ('科技', '教育'): 0.30,
            ('母婴', '生活方式'): 0.50,
            ('母婴', '美食'): 0.30
        }
    
    def calculate_audience_overlap(self, influencer1: pd.Series, 
                                    influencer2: pd.Series, 
                                    demographics_df: pd.DataFrame = None) -> Dict:
        platform_overlap = self._get_platform_overlap(
            influencer1['platform'], influencer2['platform']
        )
        
        category_overlap = self._get_category_overlap(
            influencer1['category'], influencer2['category']
        )
        
        demographic_overlap = 0.5
        if demographics_df is not None:
            demographic_overlap = self._calculate_demographic_overlap(
                influencer1['id'], influencer2['id'], demographics_df
            )
        
        follower_size_factor = self._calculate_size_overlap_factor(
            influencer1['followers'], influencer2['followers']
        )
        
        overall_overlap = (
            platform_overlap * 0.35 +
            category_overlap * 0.35 +
            demographic_overlap * 0.20 +
            follower_size_factor * 0.10
        )
        
        unique_audience_ratio = 1 - overall_overlap
        
        return {
            'influencer1_id': influencer1['id'],
            'influencer2_id': influencer2['id'],
            'platform_overlap': round(platform_overlap * 100, 2),
            'category_overlap': round(category_overlap * 100, 2),
            'demographic_overlap': round(demographic_overlap * 100, 2),
            'overall_overlap_rate': round(overall_overlap * 100, 2),
            'unique_audience_ratio': round(unique_audience_ratio * 100, 2),
            'waste_warning': overall_overlap > 0.5,
            'recommendation': self._get_overlap_recommendation(overall_overlap)
        }
    
    def _get_platform_overlap(self, platform1: str, platform2: str) -> float:
        if platform1 == platform2:
            return 0.6
        
        key = tuple(sorted([platform1, platform2]))
        return self.platform_overlap_matrix.get(key, 0.2)
    
    def _get_category_overlap(self, category1: str, category2: str) -> float:
        if category1 == category2:
            return 0.7
        
        key = tuple(sorted([category1, category2]))
        return self.category_overlap_matrix.get(key, 0.15)
    
    def _calculate_demographic_overlap(self, influencer1_id: str, 
                                        influencer2_id: str, 
                                        demographics_df: pd.DataFrame) -> float:
        demo1 = demographics_df[demographics_df['influencer_id'] == influencer1_id].iloc[0]
        demo2 = demographics_df[demographics_df['influencer_id'] == influencer2_id].iloc[0]
        
        age_cols = ['age_18_24', 'age_25_34', 'age_35_44', 'age_45_plus']
        age_overlap = sum(min(demo1[col], demo2[col]) for col in age_cols)
        
        gender_cols = ['gender_male', 'gender_female']
        gender_overlap = sum(min(demo1[col], demo2[col]) for col in gender_cols)
        
        location_cols = ['location_tier1', 'location_tier2', 'location_tier3_plus']
        location_overlap = sum(min(demo1[col], demo2[col]) for col in location_cols)
        
        return (age_overlap * 0.4 + gender_overlap * 0.3 + location_overlap * 0.3)
    
    def _calculate_size_overlap_factor(self, followers1: int, followers2: int) -> float:
        ratio = min(followers1, followers2) / max(followers1, followers2)
        return 1 - (1 - ratio) * 0.5
    
    def _get_overlap_recommendation(self, overlap_rate: float) -> str:
        if overlap_rate >= 0.7:
            return "受众高度重叠，不建议同时选择，会造成预算严重浪费"
        elif overlap_rate >= 0.5:
            return "受众重叠度较高，建议减少其中一位的预算或更换人选"
        elif overlap_rate >= 0.3:
            return "受众有一定重叠，可考虑但需控制预算分配"
        else:
            return "受众重叠度低，组合效果好，建议同时选择"
    
    def calculate_group_overlap(self, selected_influencers: List[pd.Series], 
                                 demographics_df: pd.DataFrame = None) -> Dict:
        if len(selected_influencers) < 2:
            return {
                'total_unique_reach': sum(inf['followers'] for inf in selected_influencers),
                'total_duplicated_reach': 0,
                'overlap_rate': 0,
                'efficiency_score': 100,
                'pairwise_overlaps': [],
                'recommendations': ['单网红无需考虑重叠问题']
            }
        
        pairwise_overlaps = []
        total_followers = sum(inf['followers'] for inf in selected_influencers)
        total_duplicated = 0
        
        for i in range(len(selected_influencers)):
            for j in range(i + 1, len(selected_influencers)):
                overlap = self.calculate_audience_overlap(
                    selected_influencers[i], 
                    selected_influencers[j],
                    demographics_df
                )
                pairwise_overlaps.append(overlap)
                
                min_followers = min(
                    selected_influencers[i]['followers'],
                    selected_influencers[j]['followers']
                )
                total_duplicated += min_followers * overlap['overall_overlap_rate'] / 100
        
        unique_reach = total_followers - total_duplicated
        overlap_rate = (total_duplicated / total_followers * 100) if total_followers > 0 else 0
        efficiency_score = 100 - overlap_rate
        
        high_overlap_pairs = [o for o in pairwise_overlaps if o['waste_warning']]
        recommendations = []
        
        if high_overlap_pairs:
            recommendations.append(f"发现 {len(high_overlap_pairs)} 对高重叠组合，建议调整")
            for pair in high_overlap_pairs:
                recommendations.append(
                    f"{pair['influencer1_id']} 与 {pair['influencer2_id']} 重叠率达 {pair['overall_overlap_rate']}%"
                )
        else:
            recommendations.append("当前组合受众重叠度合理，预算浪费风险较低")
        
        return {
            'total_nominal_reach': total_followers,
            'total_unique_reach': int(unique_reach),
            'total_duplicated_reach': int(total_duplicated),
            'overlap_rate': round(overlap_rate, 2),
            'efficiency_score': round(efficiency_score, 2),
            'pairwise_overlaps': pairwise_overlaps,
            'high_overlap_count': len(high_overlap_pairs),
            'recommendations': recommendations
        }
    
    def optimize_allocation_with_deduplication(self, 
                                                influencer_df: pd.DataFrame,
                                                total_budget: float,
                                                campaign_df: pd.DataFrame = None,
                                                demographics_df: pd.DataFrame = None,
                                                min_budget_per_influencer: float = 1000,
                                                max_overlap_rate: float = 0.5,
                                                risk_tolerance: str = 'medium') -> Dict:
        base_optimizer = BudgetOptimizer()
        base_result = base_optimizer.optimize_budget(
            influencer_df, total_budget, campaign_df, 
            min_budget_per_influencer, risk_tolerance
        )
        
        initial_allocation = base_result['allocation']
        selected_ids = [item['influencer_id'] for item in initial_allocation]
        selected_influencers = [
            influencer_df[influencer_df['id'] == id].iloc[0] 
            for id in selected_ids
        ]
        
        overlap_analysis = self.calculate_group_overlap(
            selected_influencers, demographics_df
        )
        
        optimized_allocation = self._deduplicate_allocation(
            initial_allocation, influencer_df, overlap_analysis, 
            total_budget, max_overlap_rate
        )
        
        adjusted_forecast = self._calculate_adjusted_forecast(
            optimized_allocation, influencer_df, overlap_analysis
        )
        
        return {
            'original_allocation': initial_allocation,
            'optimized_allocation': optimized_allocation,
            'overlap_analysis': overlap_analysis,
            'adjusted_forecast': adjusted_forecast,
            'budget_savings': total_budget - sum(item['allocated_budget'] for item in optimized_allocation),
            'efficiency_improvement': overlap_analysis['efficiency_score']
        }
    
    def _deduplicate_allocation(self, allocation: List[Dict], 
                                 influencer_df: pd.DataFrame,
                                 overlap_analysis: Dict,
                                 total_budget: float,
                                 max_overlap_rate: float) -> List[Dict]:
        optimized = allocation.copy()
        
        high_overlap_pairs = [
            o for o in overlap_analysis['pairwise_overlaps'] 
            if o['overall_overlap_rate'] / 100 > max_overlap_rate
        ]
        
        for pair in high_overlap_pairs:
            id1, id2 = pair['influencer1_id'], pair['influencer2_id']
            
            item1 = next((item for item in optimized if item['influencer_id'] == id1), None)
            item2 = next((item for item in optimized if item['influencer_id'] == id2), None)
            
            if item1 and item2:
                if item1['influence_score'] >= item2['influence_score']:
                    item2['allocated_budget'] = item2['allocated_budget'] * 0.5
                else:
                    item1['allocated_budget'] = item1['allocated_budget'] * 0.5
        
        optimized = [item for item in optimized if item['allocated_budget'] >= 1000]
        
        total_allocated = sum(item['allocated_budget'] for item in optimized)
        if total_allocated < total_budget:
            remaining = total_budget - total_allocated
            for item in optimized:
                item['allocated_budget'] += remaining * (item['allocated_budget'] / total_allocated)
        
        for item in optimized:
            item['allocated_budget'] = round(item['allocated_budget'], 2)
            item['budget_percentage'] = round(item['allocated_budget'] / total_budget * 100, 2)
        
        return optimized
    
    def _calculate_adjusted_forecast(self, allocation: List[Dict],
                                      influencer_df: pd.DataFrame,
                                      overlap_analysis: Dict) -> Dict:
        forecaster = PerformanceForecaster()
        base_forecast = forecaster.forecast_campaign_performance(influencer_df, allocation)
        
        efficiency_factor = overlap_analysis['efficiency_score'] / 100
        
        adjusted_forecast = {
            'nominal_reach': base_forecast['total_expected_reach'],
            'unique_reach': int(base_forecast['total_expected_reach'] * efficiency_factor),
            'duplicated_reach': int(base_forecast['total_expected_reach'] * (1 - efficiency_factor)),
            'effective_reach': int(base_forecast['total_expected_reach'] * efficiency_factor),
            'effective_engagement': int(base_forecast['total_expected_engagement'] * efficiency_factor),
            'effective_conversions': int(base_forecast['total_expected_conversions'] * efficiency_factor),
            'reach_deduplication_rate': round((1 - efficiency_factor) * 100, 2),
            'adjusted_roi': round(
                (base_forecast['total_expected_conversions'] * efficiency_factor * 300 - 
                 base_forecast['total_cost']) / base_forecast['total_cost'] * 100, 2
            ),
            'waste_avoidance': round(
                base_forecast['total_expected_reach'] * (1 - efficiency_factor) * 0.01, 2
            )
        }
        
        return adjusted_forecast
    
    def compare_allocation_strategies(self, influencer_df: pd.DataFrame,
                                       total_budget: float,
                                       demographics_df: pd.DataFrame = None) -> pd.DataFrame:
        base_optimizer = BudgetOptimizer()
        strategies = ['conservative', 'moderate', 'aggressive']
        
        comparison_data = []
        
        for strategy in strategies:
            base_result = base_optimizer.optimize_budget(
                influencer_df, total_budget, risk_tolerance=strategy
            )
            
            selected_influencers = [
                influencer_df[influencer_df['id'] == item['influencer_id']].iloc[0]
                for item in base_result['allocation']
            ]
            
            overlap_analysis = self.calculate_group_overlap(
                selected_influencers, demographics_df
            )
            
            comparison_data.append({
                '策略类型': {
                    'conservative': '保守策略',
                    'moderate': '中等策略',
                    'aggressive': '激进策略'
                }[strategy],
                '网红数量': base_result['number_of_influencers'],
                '总预算(元)': total_budget,
                '名义触达': base_result['total_allocated'],
                '去重后触达': int(base_result['total_allocated'] * overlap_analysis['efficiency_score'] / 100),
                '重叠率(%)': overlap_analysis['overlap_rate'],
                '效率评分': overlap_analysis['efficiency_score'],
                '高重叠对数': overlap_analysis['high_overlap_count'],
                '预期ROI(%)': base_result['expected_roi']
            })
        
        return pd.DataFrame(comparison_data)
    
    def calculate_overlap_matrix(self, influencer_df: pd.DataFrame, 
                                  selected_ids: List[str], 
                                  demo_df: pd.DataFrame = None) -> pd.DataFrame:
        names = []
        for inf_id in selected_ids:
            inf_data = influencer_df[influencer_df['id'] == inf_id].iloc[0]
            names.append(f"{inf_data['name']}")
        
        matrix_data = []
        for i, id1 in enumerate(selected_ids):
            row = {'网红ID': id1, '网红名称': names[i]}
            for j, id2 in enumerate(selected_ids):
                if i == j:
                    row[names[j]] = 100.0
                else:
                    inf1 = influencer_df[influencer_df['id'] == id1].iloc[0]
                    inf2 = influencer_df[influencer_df['id'] == id2].iloc[0]
                    overlap = self.calculate_audience_overlap(inf1, inf2, demo_df)
                    row[names[j]] = overlap['overall_overlap_rate']
            matrix_data.append(row)
        
        return pd.DataFrame(matrix_data)
    
    def get_high_overlap_warnings(self, overlap_matrix: pd.DataFrame) -> List[Dict]:
        warnings = []
        names = overlap_matrix['网红名称'].tolist()
        
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                overlap_val = overlap_matrix.iloc[i][names[j]]
                if overlap_val >= 50:
                    severity = '高' if overlap_val >= 70 else '中'
                    pair = f"{names[i]} ↔ {names[j]}"
                    recommendation = self._get_overlap_recommendation(overlap_val / 100)
                    warnings.append({
                        'pair': pair,
                        'overlap_percentage': overlap_val,
                        'severity': severity,
                        'recommendation': recommendation
                    })
        
        return sorted(warnings, key=lambda x: x['overlap_percentage'], reverse=True)
    
    def optimize_allocation_with_deduplication(self, 
                                                influencer_df: pd.DataFrame,
                                                total_budget: float,
                                                overlap_matrix: pd.DataFrame = None,
                                                original_allocation_result: Dict = None,
                                                campaign_df: pd.DataFrame = None,
                                                demographics_df: pd.DataFrame = None,
                                                min_budget_per_influencer: float = 1000,
                                                max_overlap_rate: float = 0.5,
                                                risk_tolerance: str = 'moderate') -> Dict:
        if original_allocation_result is None:
            base_optimizer = BudgetOptimizer()
            original_allocation_result = base_optimizer.optimize_budget(
                influencer_df, total_budget, campaign_df, 
                min_budget_per_influencer, risk_tolerance
            )
        
        initial_allocation = original_allocation_result['allocation']
        selected_ids = [item['influencer_id'] for item in initial_allocation]
        selected_influencers = [
            influencer_df[influencer_df['id'] == id].iloc[0] 
            for id in selected_ids
        ]
        
        if overlap_matrix is None:
            overlap_analysis = self.calculate_group_overlap(
                selected_influencers, demographics_df
            )
        else:
            overlap_analysis = self._analyze_from_matrix(overlap_matrix, selected_influencers)
        
        optimized_allocation = self._deduplicate_allocation(
            initial_allocation, influencer_df, overlap_analysis, 
            total_budget, max_overlap_rate
        )
        
        adjusted_forecast = self._calculate_adjusted_forecast(
            optimized_allocation, influencer_df, overlap_analysis
        )
        
        comparison = []
        for orig, opt in zip(initial_allocation, optimized_allocation):
            inf_id = orig['influencer_id']
            inf_data = influencer_df[influencer_df['id'] == inf_id].iloc[0]
            budget_change = opt['allocated_budget'] - orig['allocated_budget']
            
            overlap_score = 0
            if overlap_matrix is not None:
                name = inf_data['name']
                if name in overlap_matrix.columns:
                    idx = overlap_matrix[overlap_matrix['网红名称'] == name].index
                    if len(idx) > 0:
                        row = overlap_matrix.iloc[idx[0]]
                        other_cols = [c for c in overlap_matrix.columns if c not in ['网红ID', '网红名称', name]]
                        if other_cols:
                            overlap_score = row[other_cols].mean()
            
            reason = ''
            if budget_change < 0:
                reason = '受众重叠度高，削减预算避免浪费'
            elif budget_change > 0:
                reason = '受众重叠度低，增加预算提升覆盖'
            else:
                reason = '预算分配合理，无需调整'
            
            comparison.append({
                'influencer_id': inf_id,
                'influencer_name': inf_data['name'],
                'platform': inf_data['platform'],
                'category': inf_data['category'],
                'original_budget': orig['allocated_budget'],
                'optimized_budget': opt['allocated_budget'],
                'budget_change': round(budget_change, 2),
                'overlap_adjustment_reason': reason
            })
        
        original_reach = sum(
            influencer_df[influencer_df['id'] == item['influencer_id']]['followers'].iloc[0]
            for item in initial_allocation
        )
        dedup_rate = overlap_analysis['overlap_rate']
        dedup_reach = int(original_reach * (1 - dedup_rate / 100))
        budget_wasted = int(total_budget * dedup_rate / 100)
        roi_improvement = round(dedup_rate * 0.5, 1)
        
        recommendations = []
        high_overlaps = self.get_high_overlap_warnings(overlap_matrix) if overlap_matrix is not None else []
        if high_overlaps:
            recommendations.append(f"发现 {len(high_overlaps)} 对高重叠组合")
            for pair in high_overlaps[:3]:
                recommendations.append(
                    f"警告：{pair['pair']} 受众重叠达 {pair['overlap_percentage']:.1f}%"
                )
        
        total_saved = sum(
            max(0, item['original_budget'] - item['optimized_budget'])
            for item in comparison
        )
        if total_saved > 0:
            recommendations.append(f"通过去重优化，预计节省预算 ¥{total_saved:,.0f}")
            recommendations.append(f"去重后有效触达提升 {roi_improvement:.1f}%")
        else:
            recommendations.append("当前组合受众重叠度低，预算分配已优化")
        
        for item in optimized_allocation:
            inf_id = item['influencer_id']
            inf_data = influencer_df[influencer_df['id'] == inf_id].iloc[0]
            overlap_score = 0
            if overlap_matrix is not None:
                name = inf_data['name']
                if name in overlap_matrix.columns:
                    idx = overlap_matrix[overlap_matrix['网红名称'] == name].index
                    if len(idx) > 0:
                        row = overlap_matrix.iloc[idx[0]]
                        other_cols = [c for c in overlap_matrix.columns if c not in ['网红ID', '网红名称', name]]
                        if other_cols:
                            overlap_score = round(row[other_cols].mean(), 1)
            item['audience_overlap_score'] = overlap_score
            item['platform'] = inf_data['platform']
            item['category'] = inf_data['category']
            item['followers'] = inf_data['followers']
        
        return {
            'original_allocation': initial_allocation,
            'optimized_allocation': optimized_allocation,
            'overlap_analysis': overlap_analysis,
            'adjusted_forecast': adjusted_forecast,
            'comparison': comparison,
            'net_effect': {
                'original_reach': original_reach,
                'dedup_reach': dedup_reach,
                'dedup_rate': round(dedup_rate, 1),
                'budget_wasted': budget_wasted,
                'roi_improvement': roi_improvement
            },
            'recommendations': recommendations,
            'budget_savings': total_budget - sum(item['allocated_budget'] for item in optimized_allocation)
        }
    
    def _analyze_from_matrix(self, overlap_matrix: pd.DataFrame, 
                              selected_influencers: List[pd.Series]) -> Dict:
        names = [inf['name'] for inf in selected_influencers]
        total_followers = sum(inf['followers'] for inf in selected_influencers)
        
        pairwise_overlaps = []
        total_duplicated = 0
        
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                overlap_val = overlap_matrix.iloc[i][names[j]]
                min_followers = min(
                    selected_influencers[i]['followers'],
                    selected_influencers[j]['followers']
                )
                total_duplicated += min_followers * overlap_val / 100
                
                pairwise_overlaps.append({
                    'influencer1_id': selected_influencers[i]['id'],
                    'influencer2_id': selected_influencers[j]['id'],
                    'overall_overlap_rate': overlap_val,
                    'waste_warning': overlap_val >= 50
                })
        
        unique_reach = total_followers - total_duplicated
        overlap_rate = (total_duplicated / total_followers * 100) if total_followers > 0 else 0
        efficiency_score = 100 - overlap_rate
        
        high_overlap_pairs = [o for o in pairwise_overlaps if o['waste_warning']]
        
        return {
            'total_nominal_reach': total_followers,
            'total_unique_reach': int(unique_reach),
            'total_duplicated_reach': int(total_duplicated),
            'overlap_rate': round(overlap_rate, 2),
            'efficiency_score': round(efficiency_score, 2),
            'pairwise_overlaps': pairwise_overlaps,
            'high_overlap_count': len(high_overlap_pairs),
            'recommendations': [f"发现 {len(high_overlap_pairs)} 对高重叠组合"] if high_overlap_pairs else ["组合重叠度合理"]
        }
