import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class CompetitorAnalyzer:
    def __init__(self):
        self.competitors = {
            'competitor_1': {
                'name': '完美日记',
                'category': '美妆',
                'market_position': '大众美妆',
                'monthly_budget_estimate': 5000000,
                'primary_platforms': ['Xiaohongshu', 'TikTok', 'Weibo']
            },
            'competitor_2': {
                'name': '花西子',
                'category': '美妆',
                'market_position': '中高端美妆',
                'monthly_budget_estimate': 8000000,
                'primary_platforms': ['Xiaohongshu', 'TikTok', 'Weibo']
            },
            'competitor_3': {
                'name': '元气森林',
                'category': '食品饮料',
                'market_position': '健康饮品',
                'monthly_budget_estimate': 6000000,
                'primary_platforms': ['TikTok', 'Weibo', 'Xiaohongshu']
            },
            'competitor_4': {
                'name': '小米',
                'category': '科技数码',
                'market_position': '性价比科技',
                'monthly_budget_estimate': 10000000,
                'primary_platforms': ['TikTok', 'Weibo', 'Bilibili']
            },
            'competitor_5': {
                'name': 'Keep',
                'category': '健身运动',
                'market_position': '运动健康',
                'monthly_budget_estimate': 3000000,
                'primary_platforms': ['Xiaohongshu', 'TikTok', 'Weibo']
            }
        }
        
        self.campaign_types = [
            '产品测评', '开箱体验', '好物分享', '品牌故事', 
            '使用教程', '对比评测', '限时优惠', '挑战赛'
        ]

    def generate_competitor_campaigns(self, influencer_df: pd.DataFrame, 
                                       competitor_id: str, 
                                       months_back: int = 6) -> pd.DataFrame:
        competitor = self.competitors.get(competitor_id, self.competitors['competitor_1'])
        
        np.random.seed(hash(competitor_id) % 10000)
        
        campaigns = []
        n_campaigns = np.random.randint(20, 50)
        
        candidate_influencers = influencer_df[
            influencer_df['platform'].isin(competitor['primary_platforms'])
        ].sample(min(n_campaigns * 2, len(influencer_df)))
        
        for i in range(n_campaigns):
            influencer = candidate_influencers.iloc[i % len(candidate_influencers)]
            days_ago = np.random.randint(1, months_back * 30)
            campaign_date = datetime.now() - timedelta(days=days_ago)
            
            campaign_type = np.random.choice(self.campaign_types)
            base_budget = influencer['cooperation_price']
            budget_variance = np.random.uniform(0.8, 1.3)
            actual_budget = int(base_budget * budget_variance)
            
            base_views = influencer['followers'] * np.random.uniform(0.05, 0.3)
            base_engagement = base_views * np.random.uniform(0.02, 0.08)
            base_conversions = int(base_engagement * np.random.uniform(0.01, 0.05))
            
            performance_score = np.random.uniform(0.5, 1.2)
            
            campaigns.append({
                'campaign_id': f'CMP_{competitor_id}_{i}',
                'competitor_name': competitor['name'],
                'competitor_id': competitor_id,
                'influencer_id': influencer['id'],
                'influencer_name': influencer['name'],
                'platform': influencer['platform'],
                'category': influencer['category'],
                'followers': influencer['followers'],
                'campaign_type': campaign_type,
                'campaign_date': campaign_date.strftime('%Y-%m-%d'),
                'campaign_month': campaign_date.strftime('%Y-%m'),
                'estimated_budget': actual_budget,
                'estimated_views': int(base_views * performance_score),
                'estimated_engagement': int(base_engagement * performance_score),
                'estimated_conversions': int(base_conversions * performance_score),
                'estimated_roi': round(np.random.uniform(50, 200), 1),
                'performance_rating': np.random.choice(['优秀', '良好', '一般', '较差']),
                'content_tags': self._generate_content_tags(campaign_type, competitor['category'])
            })
        
        return pd.DataFrame(campaigns).sort_values('campaign_date', ascending=False)

    def _generate_content_tags(self, campaign_type: str, category: str) -> List[str]:
        base_tags = [campaign_type]
        
        category_tags = {
            '美妆': ['底妆', '口红', '眼影', '护肤', '面膜'],
            '食品饮料': ['健康', '低糖', '好喝', '零食', '代餐'],
            '科技数码': ['性价比', '黑科技', '体验', '评测', '开箱'],
            '健身运动': ['减脂', '增肌', '瑜伽', '跑步', '装备']
        }
        
        base_tags.extend(np.random.choice(category_tags.get(category, ['好物', '推荐']), 2))
        return base_tags

    def get_competitor_summary(self, influencer_df: pd.DataFrame, competitor_id: str) -> Dict:
        competitor = self.competitors.get(competitor_id, self.competitors['competitor_1'])
        campaigns_df = self.generate_competitor_campaigns(influencer_df, competitor_id)
        
        total_spent = campaigns_df['estimated_budget'].sum()
        total_views = campaigns_df['estimated_views'].sum()
        total_engagement = campaigns_df['estimated_engagement'].sum()
        total_conversions = campaigns_df['estimated_conversions'].sum()
        
        platform_breakdown = campaigns_df.groupby('platform').agg({
            'estimated_budget': 'sum',
            'estimated_views': 'sum',
            'campaign_id': 'count'
        }).reset_index()
        
        type_breakdown = campaigns_df.groupby('campaign_type').agg({
            'estimated_budget': 'sum',
            'estimated_roi': 'mean'
        }).sort_values('estimated_budget', ascending=False).reset_index()
        
        top_influencers = campaigns_df.groupby(['influencer_id', 'influencer_name']).agg({
            'estimated_budget': 'sum',
            'estimated_roi': 'mean',
            'campaign_id': 'count'
        }).sort_values('estimated_budget', ascending=False).head(10).reset_index()
        
        monthly_trend = campaigns_df.groupby('campaign_month').agg({
            'estimated_budget': 'sum',
            'estimated_views': 'sum',
            'campaign_id': 'count'
        }).sort_index().reset_index()
        
        return {
            'competitor_info': competitor,
            'summary_metrics': {
                'total_campaigns': len(campaigns_df),
                'total_spent': total_spent,
                'total_views': total_views,
                'total_engagement': total_engagement,
                'total_conversions': total_conversions,
                'avg_roi': round(campaigns_df['estimated_roi'].mean(), 1),
                'cpm': round(total_spent / total_views * 1000, 2),
                'cpe': round(total_spent / total_engagement, 2),
                'unique_influencers': campaigns_df['influencer_id'].nunique()
            },
            'platform_breakdown': platform_breakdown.to_dict('records'),
            'type_breakdown': type_breakdown.to_dict('records'),
            'top_influencers': top_influencers.to_dict('records'),
            'monthly_trend': monthly_trend.to_dict('records'),
            'campaigns_data': campaigns_df
        }

    def compare_competitors(self, influencer_df: pd.DataFrame, 
                            competitor_ids: List[str]) -> pd.DataFrame:
        comparison = []
        
        for comp_id in competitor_ids:
            summary = self.get_competitor_summary(influencer_df, comp_id)
            metrics = summary['summary_metrics']
            comp_info = summary['competitor_info']
            
            comparison.append({
                '竞品名称': comp_info['name'],
                '所属类目': comp_info['category'],
                '市场定位': comp_info['market_position'],
                '投放网红数': metrics['unique_influencers'],
                '总投放次数': metrics['total_campaigns'],
                '预估总花费(元)': metrics['total_spent'],
                '预估总触达': metrics['total_views'],
                '平均ROI(%)': metrics['avg_roi'],
                'CPM(元/千次)': metrics['cpm'],
                '主要投放平台': ', '.join(comp_info['primary_platforms'])
            })
        
        return pd.DataFrame(comparison)

    def analyze_competitor_strategy(self, influencer_df: pd.DataFrame, 
                                     competitor_id: str) -> Dict:
        summary = self.get_competitor_summary(influencer_df, competitor_id)
        campaigns_df = summary['campaigns_data']
        
        platform_pref = campaigns_df.groupby('platform').agg({
            'estimated_budget': 'sum'
        }).reset_index()
        platform_pref['budget_percentage'] = platform_pref['estimated_budget'] / platform_pref['estimated_budget'].sum() * 100
        
        influencer_tiers = []
        for _, row in campaigns_df.iterrows():
            followers = row['followers']
            if followers >= 1000000:
                tier = '头部(100万+)'
            elif followers >= 100000:
                tier = '腰部(10-100万)'
            else:
                tier = '尾部(10万以下)'
            influencer_tiers.append(tier)
        campaigns_df['influencer_tier'] = influencer_tiers
        
        tier_breakdown = campaigns_df.groupby('influencer_tier').agg({
            'estimated_budget': ['sum', 'count'],
            'estimated_roi': 'mean'
        }).reset_index()
        tier_breakdown.columns = ['网红层级', '总预算', '投放次数', '平均ROI']
        
        content_focus = campaigns_df.groupby('campaign_type').agg({
            'estimated_budget': 'sum',
            'estimated_roi': 'mean'
        }).sort_values('estimated_budget', ascending=False).head(5)
        
        strategy_insights = []
        top_platform = platform_pref.sort_values('budget_percentage', ascending=False).iloc[0]
        strategy_insights.append(
            f"主要投放平台：{top_platform['platform']}，占比 {top_platform['budget_percentage']:.1f}%"
        )
        
        top_tier = tier_breakdown.sort_values('总预算', ascending=False).iloc[0]
        strategy_insights.append(
            f"偏好网红层级：{top_tier['网红层级']}，投放 {top_tier['投放次数']} 次"
        )
        
        top_content = content_focus.iloc[0]
        strategy_insights.append(
            f"重点内容类型：{content_focus.index[0]}，ROI {top_content['estimated_roi']:.1f}%"
        )
        
        avg_roi = campaigns_df['estimated_roi'].mean()
        if avg_roi >= 120:
            strategy_insights.append("竞品整体投放效果优秀，ROI处于较高水平")
        elif avg_roi >= 80:
            strategy_insights.append("竞品投放效果中等，有优化空间")
        else:
            strategy_insights.append("竞品投放效果一般，可能存在策略调整机会")
        
        return {
            'competitor_name': summary['competitor_info']['name'],
            'platform_preference': platform_pref.to_dict('records'),
            'influencer_tier_strategy': tier_breakdown.to_dict('records'),
            'content_focus': content_focus.reset_index().to_dict('records'),
            'strategy_insights': strategy_insights,
            'monthly_budget_estimate': summary['competitor_info']['monthly_budget_estimate']
        }

    def find_competitor_overlap(self, my_influencer_ids: List[str], 
                                 influencer_df: pd.DataFrame, 
                                 competitor_id: str) -> Dict:
        summary = self.get_competitor_summary(influencer_df, competitor_id)
        competitor_influencers = set(summary['campaigns_data']['influencer_id'].unique())
        my_influencers = set(my_influencer_ids)
        
        overlap = my_influencers & competitor_influencers
        overlap_data = []
        
        for inf_id in overlap:
            inf_data = influencer_df[influencer_df['id'] == inf_id].iloc[0]
            comp_campaigns = summary['campaigns_data'][
                summary['campaigns_data']['influencer_id'] == inf_id
            ]
            
            overlap_data.append({
                'id': inf_id,
                'name': inf_data['name'],
                'platform': inf_data['platform'],
                'followers': inf_data['followers'],
                'competitor_campaign_count': len(comp_campaigns),
                'total_spent_by_competitor': comp_campaigns['estimated_budget'].sum(),
                'avg_roi_for_competitor': comp_campaigns['estimated_roi'].mean(),
                'last_collaboration': comp_campaigns['campaign_date'].max(),
                'risk_level': '高' if len(comp_campaigns) >= 3 else '中' if len(comp_campaigns) >= 2 else '低'
            })
        
        return {
            'competitor_name': summary['competitor_info']['name'],
            'total_influencers_used': len(competitor_influencers),
            'overlap_count': len(overlap),
            'overlap_percentage': round(len(overlap) / len(my_influencer_ids) * 100 if my_influencer_ids else 0, 1),
            'overlap_influencers': pd.DataFrame(overlap_data) if overlap_data else pd.DataFrame(),
            'recommendations': [
                f"与竞品 {summary['competitor_info']['name']} 重叠网红 {len(overlap)} 位",
                f"重叠占比：{len(overlap) / len(my_influencer_ids) * 100 if my_influencer_ids else 0:.1f}%",
                "建议：评估重叠网红的独家合作价值，考虑挖掘竞品未覆盖的优质网红"
            ]
        }

    def get_market_intelligence(self, influencer_df: pd.DataFrame) -> Dict:
        all_campaigns = []
        for comp_id in self.competitors.keys():
            campaigns = self.generate_competitor_campaigns(influencer_df, comp_id)
            all_campaigns.append(campaigns)
        
        all_campaigns_df = pd.concat(all_campaigns, ignore_index=True)
        
        market_summary = {
            'total_competitors': len(self.competitors),
            'total_campaigns_tracked': len(all_campaigns_df),
            'total_market_spend': all_campaigns_df['estimated_budget'].sum(),
            'avg_market_roi': round(all_campaigns_df['estimated_roi'].mean(), 1),
            'active_influencers': all_campaigns_df['influencer_id'].nunique()
        }
        
        platform_market_share = all_campaigns_df.groupby('platform').agg({
            'estimated_budget': 'sum'
        }).reset_index()
        platform_market_share['market_share'] = platform_market_share['estimated_budget'] / platform_market_share['estimated_budget'].sum() * 100
        
        category_breakdown = all_campaigns_df.groupby('competitor_name').agg({
            'estimated_budget': 'sum',
            'estimated_roi': 'mean'
        }).sort_values('estimated_budget', ascending=False).reset_index()
        
        trending_types = all_campaigns_df.groupby('campaign_type').agg({
            'estimated_budget': 'sum',
            'estimated_roi': 'mean'
        }).sort_values('estimated_budget', ascending=False).head(5)
        
        return {
            'market_summary': market_summary,
            'platform_market_share': platform_market_share.to_dict('records'),
            'category_breakdown': category_breakdown.to_dict('records'),
            'trending_content_types': trending_types.reset_index().to_dict('records'),
            'raw_data': all_campaigns_df
        }
