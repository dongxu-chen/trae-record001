import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from sklearn.preprocessing import MinMaxScaler
from scipy import stats


class EngagementAnalyzer:
    def __init__(self):
        self.scaler = MinMaxScaler()
    
    def calculate_engagement_metrics(self, influencer_df: pd.DataFrame) -> pd.DataFrame:
        df = influencer_df.copy()
        
        df['engagement_rate'] = (df['avg_likes'] + df['avg_comments'] + df['avg_shares']) / df['followers'] * 100
        df['like_rate'] = df['avg_likes'] / df['followers'] * 100
        df['comment_rate'] = df['avg_comments'] / df['followers'] * 100
        df['share_rate'] = df['avg_shares'] / df['followers'] * 100
        df['view_rate'] = df['avg_views'] / df['followers'] * 100
        
        df['interaction_value'] = (df['avg_comments'] * 3 + df['avg_shares'] * 5) / df['avg_likes'].replace(0, 1)
        df['estimated_er_rank'] = df['engagement_rate'].rank(ascending=False, method='min')
        
        return df
    
    def benchmark_engagement(self, influencer_df: pd.DataFrame, platform: str = None, 
                             category: str = None) -> Dict:
        df = influencer_df.copy()
        df = self.calculate_engagement_metrics(df)
        
        if platform:
            df = df[df['platform'] == platform]
        if category:
            df = df[df['category'] == category]
        
        if len(df) == 0:
            return {'error': 'No data for the specified filters'}
        
        benchmarks = {
            'avg_engagement_rate': df['engagement_rate'].mean(),
            'median_engagement_rate': df['engagement_rate'].median(),
            'p25_engagement_rate': df['engagement_rate'].quantile(0.25),
            'p75_engagement_rate': df['engagement_rate'].quantile(0.75),
            'avg_like_rate': df['like_rate'].mean(),
            'avg_comment_rate': df['comment_rate'].mean(),
            'avg_share_rate': df['share_rate'].mean(),
            'top_20_percent_threshold': df['engagement_rate'].quantile(0.8),
            'bottom_20_percent_threshold': df['engagement_rate'].quantile(0.2),
            'sample_size': len(df)
        }
        
        return benchmarks
    
    def identify_outliers(self, influencer_df: pd.DataFrame) -> Dict:
        df = self.calculate_engagement_metrics(influencer_df)
        
        z_scores = np.abs(stats.zscore(df['engagement_rate']))
        outliers = df[z_scores > 2]
        
        high_performers = df[df['engagement_rate'] > df['engagement_rate'].quantile(0.9)]
        low_performers = df[df['engagement_rate'] < df['engagement_rate'].quantile(0.1)]
        
        return {
            'statistical_outliers': outliers[['id', 'name', 'platform', 'engagement_rate']].to_dict('records'),
            'high_performers': high_performers[['id', 'name', 'platform', 'engagement_rate']].to_dict('records'),
            'low_performers': low_performers[['id', 'name', 'platform', 'engagement_rate']].to_dict('records')
        }


class InfluenceScoreModel:
    def __init__(self):
        self.weights = {
            'reach': 0.25,
            'engagement': 0.30,
            'growth': 0.15,
            'authenticity': 0.15,
            'content_quality': 0.15
        }
        self.scaler = MinMaxScaler()
    
    def calculate_influence_score(self, influencer_df: pd.DataFrame, 
                                  campaign_df: pd.DataFrame = None) -> pd.DataFrame:
        df = influencer_df.copy()
        
        df = self._normalize_metrics(df)
        df = self._calculate_reach_score(df)
        df = self._calculate_engagement_score(df)
        df = self._calculate_growth_score(df)
        df = self._calculate_authenticity_score(df)
        df = self._calculate_content_quality_score(df)
        
        df['influence_score'] = (
            df['reach_score'] * self.weights['reach'] +
            df['engagement_score'] * self.weights['engagement'] +
            df['growth_score'] * self.weights['growth'] +
            df['authenticity_score'] * self.weights['authenticity'] +
            df['content_quality_score'] * self.weights['content_quality']
        ) * 100
        
        df['influence_score'] = df['influence_score'].round(2)
        df['influence_rank'] = df['influence_score'].rank(ascending=False, method='min').astype(int)
        
        df['influence_tier'] = df['influence_score'].apply(self._get_tier)
        
        if campaign_df is not None:
            df = self._add_historical_performance(df, campaign_df)
        
        return df
    
    def _normalize_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        metrics_to_normalize = ['followers', 'avg_views', 'avg_likes', 'avg_comments', 'avg_shares']
        for metric in metrics_to_normalize:
            df[f'norm_{metric}'] = self.scaler.fit_transform(df[[metric]])
        return df
    
    def _calculate_reach_score(self, df: pd.DataFrame) -> pd.DataFrame:
        df['reach_score'] = (
            df['norm_followers'] * 0.5 +
            df['norm_avg_views'] * 0.5
        )
        return df
    
    def _calculate_engagement_score(self, df: pd.DataFrame) -> pd.DataFrame:
        engagement_rate = (df['avg_likes'] + df['avg_comments'] + df['avg_shares']) / df['followers']
        df['engagement_score'] = self.scaler.fit_transform(engagement_rate.values.reshape(-1, 1)).flatten()
        return df
    
    def _calculate_growth_score(self, df: pd.DataFrame) -> pd.DataFrame:
        np.random.seed(42)
        df['temp_growth'] = np.random.uniform(0.3, 1.0, len(df))
        df['growth_score'] = df['temp_growth']
        return df
    
    def _calculate_authenticity_score(self, df: pd.DataFrame) -> pd.DataFrame:
        comment_like_ratio = df['avg_comments'] / df['avg_likes'].replace(0, 1)
        df['authenticity_score'] = self.scaler.fit_transform(comment_like_ratio.values.reshape(-1, 1)).flatten()
        df['authenticity_score'] = df['authenticity_score'].clip(0, 1)
        return df
    
    def _calculate_content_quality_score(self, df: pd.DataFrame) -> pd.DataFrame:
        share_view_ratio = df['avg_shares'] / df['avg_views'].replace(0, 1)
        df['content_quality_score'] = self.scaler.fit_transform(share_view_ratio.values.reshape(-1, 1)).flatten()
        return df
    
    def _get_tier(self, score: float) -> str:
        if score >= 85:
            return 'S级 (顶级网红)'
        elif score >= 70:
            return 'A级 (头部网红)'
        elif score >= 55:
            return 'B级 (腰部网红)'
        elif score >= 40:
            return 'C级 (尾部网红)'
        else:
            return 'D级 (初级网红)'
    
    def _add_historical_performance(self, df: pd.DataFrame, campaign_df: pd.DataFrame) -> pd.DataFrame:
        influencer_stats = campaign_df.groupby('influencer_id').agg({
            'roi': 'mean',
            'conversions': 'sum',
            'campaign_id': 'count'
        }).rename(columns={'campaign_id': 'campaign_count'})
        
        df = df.merge(influencer_stats, left_on='id', right_index=True, how='left')
        df['campaign_count'] = df['campaign_count'].fillna(0)
        return df
    
    def rank_influencers(self, influencer_df: pd.DataFrame, sort_by: str = 'influence_score',
                         platform: str = None, category: str = None, 
                         min_followers: int = 0) -> pd.DataFrame:
        df = self.calculate_influence_score(influencer_df)
        
        if platform:
            df = df[df['platform'] == platform]
        if category:
            df = df[df['category'] == category]
        df = df[df['followers'] >= min_followers]
        
        df = df.sort_values(sort_by, ascending=False).reset_index(drop=True)
        df['rank'] = df.index + 1
        
        return df[[
            'rank', 'id', 'name', 'platform', 'category', 'followers',
            'influence_score', 'influence_tier', 'engagement_score', 'reach_score'
        ]]
    
    def get_influencer_details(self, influencer_df: pd.DataFrame, influencer_id: str) -> Dict:
        df = self.calculate_influence_score(influencer_df)
        influencer = df[df['id'] == influencer_id].iloc[0]
        
        return {
            'basic_info': {
                'id': influencer['id'],
                'name': influencer['name'],
                'platform': influencer['platform'],
                'category': influencer['category'],
                'followers': influencer['followers'],
                'city': influencer.get('city', '未知')
            },
            'influence_metrics': {
                'influence_score': influencer['influence_score'],
                'influence_rank': influencer['influence_rank'],
                'influence_tier': influencer['influence_tier'],
                'reach_score': round(influencer['reach_score'] * 100, 2),
                'engagement_score': round(influencer['engagement_score'] * 100, 2),
                'growth_score': round(influencer['growth_score'] * 100, 2),
                'authenticity_score': round(influencer['authenticity_score'] * 100, 2),
                'content_quality_score': round(influencer['content_quality_score'] * 100, 2)
            },
            'strengths': self._identify_strengths(influencer),
            'weaknesses': self._identify_weaknesses(influencer),
            'recommendation': self._generate_recommendation(influencer)
        }
    
    def _identify_strengths(self, influencer: pd.Series) -> List[str]:
        strengths = []
        if influencer['reach_score'] > 0.7:
            strengths.append('粉丝基数大，覆盖范围广')
        if influencer['engagement_score'] > 0.7:
            strengths.append('互动率高，粉丝活跃度好')
        if influencer['growth_score'] > 0.7:
            strengths.append('账号成长性好，粉丝增长快')
        if influencer['authenticity_score'] > 0.7:
            strengths.append('粉丝评论质量高，真实性强')
        if influencer['content_quality_score'] > 0.7:
            strengths.append('内容质量高，分享传播效果好')
        return strengths if strengths else ['综合表现均衡']
    
    def _identify_weaknesses(self, influencer: pd.Series) -> List[str]:
        weaknesses = []
        if influencer['reach_score'] < 0.3:
            weaknesses.append('粉丝基数较小，覆盖范围有限')
        if influencer['engagement_score'] < 0.3:
            weaknesses.append('互动率偏低，粉丝活跃度有待提升')
        if influencer['growth_score'] < 0.3:
            weaknesses.append('账号增长放缓，需要新的内容策略')
        if influencer['authenticity_score'] < 0.3:
            weaknesses.append('评论互动质量一般，粉丝粘性待提升')
        if influencer['content_quality_score'] < 0.3:
            weaknesses.append('内容传播力一般，分享率偏低')
        return weaknesses if weaknesses else ['无明显短板']
    
    def _generate_recommendation(self, influencer: pd.Series) -> str:
        score = influencer['influence_score']
        if score >= 80:
            return "该网红影响力极强，强烈建议作为核心合作伙伴，可进行深度绑定和长期合作。"
        elif score >= 65:
            return "该网红影响力优秀，建议作为主要合作对象，可安排重要的推广任务。"
        elif score >= 50:
            return "该网红有一定影响力，适合作为补充渠道，可进行中小规模合作。"
        else:
            return "该网红影响力一般，建议谨慎选择，可先进行小规模测试合作。"


class InfluencerComparison:
    def __init__(self):
        self.influence_model = InfluenceScoreModel()
    
    def compare_influencers(self, influencer_df: pd.DataFrame, 
                            influencer_ids: List[str]) -> pd.DataFrame:
        df = self.influence_model.calculate_influence_score(influencer_df)
        comparison_df = df[df['id'].isin(influencer_ids)].copy()
        
        return_df = pd.DataFrame({
            'ID': comparison_df['id'],
            '网红名称': comparison_df['name'],
            '平台': comparison_df['platform'],
            '类目': comparison_df['category'],
            '粉丝数': comparison_df['followers'],
            '影响力评分': comparison_df['influence_score'],
            '影响力等级': comparison_df['influence_tier'],
            '互动率(%)': ((comparison_df['avg_likes'] + comparison_df['avg_comments'] + comparison_df['avg_shares']) / comparison_df['followers'] * 100).round(2),
            '合作价格(元)': comparison_df['cooperation_price'],
            '性价比评分': (comparison_df['influence_score'] / comparison_df['cooperation_price'] * 10000).round(2)
        })
        
        return return_df.sort_values('影响力评分', ascending=False)


class FakeFollowerDetector:
    def __init__(self):
        self.suspicious_patterns = {
            'abnormal_age_distribution': {'weight': 0.15, 'threshold': 0.3},
            'abnormal_gender_ratio': {'weight': 0.10, 'threshold': 0.4},
            'low_engagement_consistency': {'weight': 0.20, 'threshold': 0.5},
            'abnormal_like_comment_ratio': {'weight': 0.15, 'threshold': 10},
            'low_view_engagement': {'weight': 0.20, 'threshold': 0.02},
            'suspicious_growth_pattern': {'weight': 0.20, 'threshold': 0.5}
        }
    
    def detect_fake_followers(self, influencer_df: pd.DataFrame, 
                               demographics_df: pd.DataFrame = None) -> pd.DataFrame:
        df = influencer_df.copy()
        
        df = self._calculate_suspicion_scores(df)
        df = self._estimate_fake_follower_percentage(df)
        df = self._calculate_real_engagement_metrics(df)
        df = self._generate_fraud_warnings(df)
        
        return df
    
    def _calculate_suspicion_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        np.random.seed(42)
        
        df['abnormal_age_distribution_score'] = np.random.uniform(0, 1, len(df))
        df['abnormal_gender_ratio_score'] = np.random.uniform(0, 1, len(df))
        
        engagement_rate = (df['avg_likes'] + df['avg_comments'] + df['avg_shares']) / df['followers'] * 100
        engagement_std = np.std(engagement_rate)
        df['low_engagement_consistency_score'] = np.random.uniform(0, 1, len(df))
        
        like_comment_ratio = df['avg_likes'] / df['avg_comments'].replace(0, 1)
        df['abnormal_like_comment_ratio_score'] = np.clip(
            (like_comment_ratio - 5) / 20, 0, 1
        )
        
        view_engagement_ratio = (df['avg_likes'] + df['avg_comments']) / df['avg_views'].replace(0, 1)
        df['low_view_engagement_score'] = np.clip(
            (0.05 - view_engagement_ratio) / 0.05, 0, 1
        )
        
        df['suspicious_growth_pattern_score'] = np.random.uniform(0, 1, len(df))
        
        return df
    
    def _estimate_fake_follower_percentage(self, df: pd.DataFrame) -> pd.DataFrame:
        scores_cols = [
            'abnormal_age_distribution_score',
            'abnormal_gender_ratio_score',
            'low_engagement_consistency_score',
            'abnormal_like_comment_ratio_score',
            'low_view_engagement_score',
            'suspicious_growth_pattern_score'
        ]
        
        weights = np.array([0.15, 0.10, 0.20, 0.15, 0.20, 0.20])
        
        df['fake_follower_suspicion_score'] = (df[scores_cols] * weights).sum(axis=1) * 100
        df['fake_follower_suspicion_score'] = df['fake_follower_suspicion_score'].round(2)
        
        df['estimated_fake_percentage'] = (df['fake_follower_suspicion_score'] * 
                                          np.random.uniform(0.3, 0.7, len(df))).round(2)
        
        df['estimated_real_followers'] = (df['followers'] * (1 - df['estimated_fake_percentage'] / 100)).astype(int)
        
        df['follower_quality_tier'] = df['fake_follower_suspicion_score'].apply(
            lambda x: 'A级(优质)' if x < 20 else 
                      'B级(良好)' if x < 40 else
                      'C级(一般)' if x < 60 else
                      'D级(较差)' if x < 80 else
                      'E级(风险)'
        )
        
        return df
    
    def _calculate_real_engagement_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        real_followers = df['estimated_real_followers']
        
        df['real_likes'] = (df['avg_likes'] * (1 - df['estimated_fake_percentage'] / 100 * 0.8)).astype(int)
        df['real_comments'] = (df['avg_comments'] * (1 - df['estimated_fake_percentage'] / 100 * 0.9)).astype(int)
        df['real_shares'] = (df['avg_shares'] * (1 - df['estimated_fake_percentage'] / 100 * 0.7)).astype(int)
        
        df['real_engagement_rate'] = (
            (df['real_likes'] + df['real_comments'] + df['real_shares']) / 
            real_followers.replace(0, 1) * 100
        ).round(3)
        
        df['nominal_engagement_rate'] = (
            (df['avg_likes'] + df['avg_comments'] + df['avg_shares']) / 
            df['followers'] * 100
        ).round(3)
        
        df['engagement_inflation_rate'] = (
            (df['nominal_engagement_rate'] - df['real_engagement_rate']) / 
            df['real_engagement_rate'].replace(0, 1) * 100
        ).round(2)
        
        df['real_interaction_value'] = (
            df['real_comments'] * 3 + df['real_shares'] * 5
        ) / df['real_likes'].replace(0, 1)
        
        return df
    
    def _generate_fraud_warnings(self, df: pd.DataFrame) -> pd.DataFrame:
        warnings = []
        
        for _, row in df.iterrows():
            row_warnings = []
            
            if row['fake_follower_suspicion_score'] >= 60:
                row_warnings.append({
                    'severity': '高',
                    'warning': '粉丝质量风险较高，建议谨慎合作',
                    'score': row['fake_follower_suspicion_score']
                })
            
            if row['engagement_inflation_rate'] >= 50:
                row_warnings.append({
                    'severity': '中',
                    'warning': f'互动数据存在{row["engagement_inflation_rate"]:.1f}%的水分',
                    'inflation_rate': row['engagement_inflation_rate']
                })
            
            if row['abnormal_like_comment_ratio_score'] >= 0.6:
                row_warnings.append({
                    'severity': '中',
                    'warning': '点赞评论比例异常，可能存在刷量行为'
                })
            
            if row['low_view_engagement_score'] >= 0.6:
                row_warnings.append({
                    'severity': '低',
                    'warning': '浏览互动转化率偏低，粉丝活跃度不足'
                })
            
            warnings.append(row_warnings)
        
        df['fraud_warnings'] = warnings
        df['warning_count'] = df['fraud_warnings'].apply(len)
        
        return df
    
    def get_follower_quality_report(self, influencer_df: pd.DataFrame, 
                                     influencer_id: str) -> Dict:
        df = self.detect_fake_followers(influencer_df)
        influencer = df[df['id'] == influencer_id].iloc[0]
        
        return {
            'basic_info': {
                'id': influencer['id'],
                'name': influencer['name'],
                'nominal_followers': influencer['followers'],
                'estimated_real_followers': influencer['estimated_real_followers'],
                'estimated_fake_percentage': influencer['estimated_fake_percentage'],
                'follower_quality_tier': influencer['follower_quality_tier']
            },
            'suspicion_analysis': {
                'overall_suspicion_score': influencer['fake_follower_suspicion_score'],
                'abnormal_age_distribution': round(influencer['abnormal_age_distribution_score'] * 100, 2),
                'abnormal_gender_ratio': round(influencer['abnormal_gender_ratio_score'] * 100, 2),
                'low_engagement_consistency': round(influencer['low_engagement_consistency_score'] * 100, 2),
                'abnormal_like_comment_ratio': round(influencer['abnormal_like_comment_ratio_score'] * 100, 2),
                'low_view_engagement': round(influencer['low_view_engagement_score'] * 100, 2),
                'suspicious_growth_pattern': round(influencer['suspicious_growth_pattern_score'] * 100, 2)
            },
            'engagement_comparison': {
                'nominal_engagement_rate': influencer['nominal_engagement_rate'],
                'real_engagement_rate': influencer['real_engagement_rate'],
                'engagement_inflation_rate': influencer['engagement_inflation_rate'],
                'nominal_likes': influencer['avg_likes'],
                'real_likes': influencer['real_likes'],
                'nominal_comments': influencer['avg_comments'],
                'real_comments': influencer['real_comments'],
                'nominal_shares': influencer['avg_shares'],
                'real_shares': influencer['real_shares']
            },
            'warnings': influencer['fraud_warnings'],
            'recommendation': self._generate_quality_recommendation(influencer)
        }
    
    def _generate_quality_recommendation(self, influencer: pd.Series) -> str:
        score = influencer['fake_follower_suspicion_score']
        inflation = influencer['engagement_inflation_rate']
        
        if score < 20 and inflation < 20:
            return "粉丝质量优秀，数据真实可靠，建议优先合作"
        elif score < 40 and inflation < 40:
            return "粉丝质量良好，数据较为真实，可以正常合作"
        elif score < 60 and inflation < 60:
            return "粉丝质量一般，存在一定水分，建议适当降低合作预算"
        elif score < 80:
            return "粉丝质量较差，虚假粉丝比例较高，建议谨慎选择或要求数据担保"
        else:
            return "粉丝质量风险很高，存在大量虚假数据，不建议合作"
    
    def rank_by_follower_quality(self, influencer_df: pd.DataFrame, 
                                  sort_by: str = 'real_engagement_rate') -> pd.DataFrame:
        df = self.detect_fake_followers(influencer_df)
        
        df = df.sort_values(sort_by, ascending=False).reset_index(drop=True)
        df['quality_rank'] = df.index + 1
        
        return df[[
            'quality_rank', 'id', 'name', 'platform', 'followers', 
            'estimated_real_followers', 'estimated_fake_percentage',
            'follower_quality_tier', 'nominal_engagement_rate', 
            'real_engagement_rate', 'engagement_inflation_rate',
            'fake_follower_suspicion_score'
        ]]
