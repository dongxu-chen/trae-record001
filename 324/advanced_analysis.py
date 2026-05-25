import os
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
from config import (
    COMPETITION_PARAMS, ADVERTISING_PARAMS, AUDIENCE_PROFILE_PARAMS,
    GENRES, PLATFORMS, TIME_SLOTS, ACTOR_POPULARITY, SEASON_EFFECT
)
from utils import get_season

class CompetitionAnalyzer:
    """
    竞争对手分析模块
    
    分析同期播出的其他剧集对本剧收视的影响
    """
    
    def __init__(self, params=None):
        self.params = params or COMPETITION_PARAMS
    
    def generate_competing_dramas(self, target_drama, num_competitors=5):
        """
        生成同期竞争剧集数据
        """
        competitors = []
        start_date = target_drama['start_date']
        end_date = start_date + timedelta(days=target_drama['num_episodes'])
        
        for i in range(num_competitors):
            other_genres = [g for g in GENRES if g != target_drama['genre']]
            other_platforms = [p for p in PLATFORMS if p != target_drama['platform']]
            
            same_timeslot = np.random.random() < 0.4
            same_genre = np.random.random() < 0.3
            
            competitor = {
                'drama_id': f'COMP_{i+1:02d}',
                'name': f'竞争剧集_{i+1}',
                'genre': target_drama['genre'] if same_genre else np.random.choice(other_genres),
                'platform': target_drama['platform'] if not same_timeslot else np.random.choice(other_platforms),
                'time_slot': target_drama['time_slot'] if same_timeslot else np.random.choice(TIME_SLOTS),
                'actor_level': np.random.choice(['顶级', '一线', '二线', '三线'],
                                              p=[0.15, 0.3, 0.35, 0.2]),
                'num_episodes': np.random.randint(30, 50),
                'production_budget': np.random.randint(10000, 50000),
                'director_reputation': round(np.random.uniform(0.5, 1.0), 2),
                'is_sequel': np.random.random() < 0.2,
                'start_date': start_date + timedelta(days=np.random.randint(-10, 10)),
                'expected_avg_rating': round(np.random.uniform(0.8, 3.5), 2)
            }
            competitor['end_date'] = competitor['start_date'] + timedelta(days=competitor['num_episodes'])
            
            overlap_days = max(0, (min(end_date, competitor['end_date']) - max(start_date, competitor['start_date'])).days)
            competitor['overlap_days'] = overlap_days
            competitor['overlap_ratio'] = overlap_days / target_drama['num_episodes']
            
            competitors.append(competitor)
        
        return sorted(competitors, key=lambda x: x['overlap_ratio'], reverse=True)
    
    def calculate_competition_impact(self, target_drama, competitors):
        """
        计算竞争对手对本剧的影响
        
        返回每个播出日期维度的影响
        """
        impact_data = []
        total_penalty = 0
        
        for comp in competitors:
            if comp['overlap_days'] <= 0:
                continue
            
            penalty = 0
            
            if comp['time_slot'] == target_drama['time_slot']:
                penalty += self.params['same_timeslot_penalty']
            
            if comp['genre'] == target_drama['genre']:
                penalty += self.params['same_genre_penalty']
            
            if comp['platform'] == target_drama['platform']:
                penalty += self.params['same_platform_penalty']
            
            if ACTOR_POPULARITY[comp['actor_level']] >= ACTOR_POPULARITY[target_drama['actor_level']]:
                penalty += self.params['strong_cast_penalty']
            
            if comp['is_sequel'] and not target_drama['is_sequel']:
                penalty += self.params['direct_competitor_penalty']
            
            if target_drama['is_sequel'] and not comp['is_sequel']:
                penalty -= self.params['sequel_bonus_vs_competitor']
            
            expected_rating_ratio = comp['expected_avg_rating'] / max(target_drama.get('expected_rating', 2.0), 0.5)
            penalty *= min(penalty * expected_rating_ratio, self.params['max_competition_penalty'])
            
            overlap_factor = comp['overlap_ratio']
            penalty *= overlap_factor
            
            total_penalty += penalty
            
            impact_data.append({
                'competitor_id': comp['drama_id'],
                'competitor_name': comp['name'],
                'genre': comp['genre'],
                'platform': comp['platform'],
                'time_slot': comp['time_slot'],
                'actor_level': comp['actor_level'],
                'overlap_days': comp['overlap_days'],
                'overlap_ratio': round(comp['overlap_ratio'], 3),
                'penalty': round(penalty, 4),
                'penalty_percent': f"{penalty*100:.2f}%"
            })
        
        active_competitors = len([c for c in competitors if c['overlap_days'] > 0])
        saturation_penalty = 0
        if active_competitors >= self.params['market_saturation_threshold']:
            saturation_penalty = (active_competitors - self.params['market_saturation_threshold'] + 1) * 0.03
            saturation_penalty = min(saturation_penalty, 0.1)
            total_penalty += saturation_penalty
        
        total_penalty = min(total_penalty, self.params['max_competition_penalty'])
        
        impact_df = pd.DataFrame(impact_data)
        
        return {
            'total_competitors': len(competitors),
            'active_competitors': active_competitors,
            'total_penalty': round(total_penalty, 4),
            'total_penalty_percent': f"{total_penalty*100:.2f}%",
            'saturation_penalty': round(saturation_penalty, 4),
            'impact_details': impact_df,
            'adjustment_factor': round(1 - total_penalty, 4)
        }
    
    def get_daily_competition_impact(self, target_drama, competitors, dates):
        """
        计算每日的竞争影响
        """
        daily_impact = []
        
        for date_idx, current_date in enumerate(dates):
            day_penalty = 0
            active_competitors = []
            
            for comp in competitors:
                if comp['start_date'] <= current_date <= comp['end_date']:
                    active_competitors.append(comp)
                    
                    penalty = 0
                    
                    if comp['time_slot'] == target_drama['time_slot']:
                        penalty += self.params['same_timeslot_penalty'] * 0.5
                    if comp['genre'] == target_drama['genre']:
                        penalty += self.params['same_genre_penalty'] * 0.5
                    
                    expected_rating_ratio = comp['expected_avg_rating'] / max(target_drama.get('expected_rating', 2.0), 0.5)
                    penalty *= expected_rating_ratio
                    
                    day_penalty += penalty
            
            day_penalty = min(day_penalty, self.params['max_competition_penalty'] * 0.5)
            
            daily_impact.append({
                'date': current_date,
                'episode': date_idx + 1,
                'active_competitors': len(active_competitors),
                'competition_names': [c['name'] for c in active_competitors],
                'daily_penalty': round(day_penalty, 4),
                'adjustment_factor': round(1 - day_penalty, 4)
            })
        
        return pd.DataFrame(daily_impact)

class AdvertisingValueEvaluator:
    """
    广告价值评估模块
    
    根据收视率预测各时段广告价位
    """
    
    def __init__(self, params=None):
        self.params = params or ADVERTISING_PARAMS
    
    def calculate_ad_value(self, rating, episode_info, drama_info, social_df=None):
        """
        计算单集广告价值
        
        公式：
        广告价值 = 基础CPM × 收视率倍数 × 时段系数 × 周末系数 × 情感系数
        """
        base_cpm = self.params['base_cpm']
        rating_mult = 1 + (rating - 1) * self.params['rating_multiplier'] / 100
        
        is_prime = '黄金档' in drama_info['time_slot']
        time_bonus = self.params['prime_time_bonus'] if is_prime else 1.0
        
        episode_date = episode_info.get('date')
        if hasattr(episode_date, 'weekday'):
            is_weekend = episode_date.weekday() >= 5
        else:
            is_weekend = False
        weekend_bonus = self.params['weekend_bonus'] if is_weekend else 1.0
        
        season = get_season(episode_date) if hasattr(episode_date, 'month') else '春季'
        season_mult = self.params['seasonal_multipliers'].get(season, 1.0)
        
        sentiment_bonus = 1.0
        if social_df is not None and 'sentiment_score' in social_df.columns:
            episode_idx = episode_info.get('episode', 1) - 1
            if episode_idx < len(social_df):
                sentiment = social_df.iloc[episode_idx]['sentiment_score']
                sentiment_bonus = 1 + (sentiment - 0.5) * self.params['sentiment_bonus']
        
        peak_bonus = 1.0
        if episode_info.get('is_peak', False):
            peak_bonus = self.params['peak_episode_bonus']
        
        base_value = base_cpm * rating_mult * time_bonus * weekend_bonus * season_mult * sentiment_bonus * peak_bonus
        
        ad_slots_value = {}
        total_ad_value = 0
        
        for slot_key, slot_info in self.params['ad_slots'].items():
            slot_value = base_value * slot_info['multiplier']
            slot_duration = slot_info['duration']
            
            if slot_duration > 0:
                slot_total = slot_value * slot_duration / 15
            else:
                slot_total = slot_value * 2
            
            ad_slots_value[slot_key] = {
                'name': slot_info['name'],
                'duration': slot_info['duration'],
                'price_per_15s': round(slot_value, 2),
                'total_value': round(slot_total, 2),
                'multiplier': slot_info['multiplier']
            }
            total_ad_value += slot_total
        
        audience_value = self.calculate_audience_value(drama_info, rating)
        
        return {
            'base_cpm': round(base_cpm, 2),
            'rating_multiplier': round(rating_mult, 4),
            'time_slot_bonus': round(time_bonus, 2),
            'weekend_bonus': round(weekend_bonus, 2),
            'season_multiplier': round(season_mult, 2),
            'sentiment_bonus': round(sentiment_bonus, 2),
            'peak_bonus': round(peak_bonus, 2),
            'base_value_per_15s': round(base_value, 2),
            'ad_slots': ad_slots_value,
            'total_episode_ad_value': round(total_ad_value, 2),
            'audience_value_multiplier': round(audience_value, 2),
            'total_ad_value_with_audience': round(total_ad_value * audience_value, 2)
        }
    
    def calculate_audience_value(self, drama_info, rating):
        """
        计算观众人口统计学价值
        """
        genre_pref = AUDIENCE_PROFILE_PARAMS['genre_audience_preference'].get(drama_info['genre'], {})
        demo_values = self.params['audience_demographic_value']
        
        weighted_value = 0
        for age_group, pref_ratio in genre_pref.items():
            demo_val = demo_values.get(age_group, 1.0)
            weighted_value += pref_ratio * demo_val
        
        return weighted_value
    
    def generate_full_ad_report(self, drama_info, predictions, social_df=None, dates=None):
        """
        生成完整的广告价值报告
        """
        ad_report = []
        total_value = 0
        
        for i, rating in enumerate(predictions):
            episode_info = {
                'episode': i + 1,
                'date': dates[i] if dates else None,
                'is_peak': False
            }
            
            if len(predictions) >= 3:
                if rating == max(predictions):
                    episode_info['is_peak'] = True
            
            ad_value = self.calculate_ad_value(rating, episode_info, drama_info, social_df)
            total_value += ad_value['total_ad_value_with_audience']
            
            ad_report.append({
                'episode': i + 1,
                'date': dates[i] if dates else None,
                'rating': round(rating, 4),
                'base_value_per_15s': ad_value['base_value_per_15s'],
                'mid_ad_value': ad_value['total_episode_ad_value'],
                'total_value': ad_value['total_ad_value_with_audience'],
                'ad_slots': ad_value['ad_slots']
            })
        
        ad_df = pd.DataFrame(ad_report)
        
        summary = {
            'total_ad_value': round(total_value, 2),
            'avg_episode_ad_value': round(total_value / len(predictions), 2),
            'max_episode_ad_value': round(ad_df['total_value'].max(), 2),
            'min_episode_ad_value': round(ad_df['total_value'].min(), 2),
            'avg_base_cpm': round(ad_df['base_value_per_15s'].mean(), 2),
            'ad_slot_summary': self.summarize_ad_slots(ad_report)
        }
        
        return {
            'detailed': ad_df,
            'summary': summary
        }
    
    def summarize_ad_slots(self, ad_report):
        """
        汇总各广告位的价值
        """
        slot_totals = defaultdict(float)
        
        for ep in ad_report:
            for slot_key, slot_data in ep['ad_slots'].items():
                slot_totals[slot_key] += slot_data['total_value']
        
        return {
            slot_key: round(total, 2) for slot_key, total in slot_totals.items()
        }

class AudienceProfiler:
    """
    观众画像分析模块
    
    分析观众构成、重叠度、交叉推广推荐
    """
    
    def __init__(self, params=None):
        self.params = params or AUDIENCE_PROFILE_PARAMS
    
    def generate_audience_profile(self, drama_info, predictions=None, social_df=None):
        """
        生成剧集观众画像
        """
        genre = drama_info['genre']
        genre_pref = self.params['genre_audience_preference'].get(genre, {})
        
        avg_rating = np.mean(predictions) if predictions is not None and len(predictions) > 0 else 2.0
        
        base_viewership = self.estimate_viewership(drama_info, avg_rating)
        
        age_distribution = {}
        for age_group, pref_ratio in genre_pref.items():
            age_distribution[age_group] = {
                'viewers': int(base_viewership * pref_ratio),
                'ratio': round(pref_ratio, 4),
                'value_multiplier': ADVERTISING_PARAMS['audience_demographic_value'].get(age_group, 1.0)
            }
        
        gender_distribution = {
            'male': int(base_viewership * self.params['gender_split']['male']),
            'female': int(base_viewership * self.params['gender_split']['female'])
        }
        
        platform_pref = self.analyze_platform_preference(genre_pref)
        
        income_distribution = self.estimate_income_distribution(genre_pref)
        
        engagement_level = self.calculate_engagement_level(social_df)
        
        return {
            'total_viewers_estimate': base_viewership,
            'avg_rating': avg_rating,
            'age_distribution': age_distribution,
            'gender_distribution': gender_distribution,
            'platform_preference': platform_pref,
            'income_distribution': income_distribution,
            'engagement_level': engagement_level,
            'key_audience_segments': self.identify_key_segments(age_distribution)
        }
    
    def estimate_viewership(self, drama_info, avg_rating):
        """
        估算观众规模
        """
        platform_mult = {
            '湖南卫视': 1.5, '浙江卫视': 1.3, '东方卫视': 1.35,
            '江苏卫视': 1.2, '北京卫视': 1.15,
            '腾讯视频': 2.0, '爱奇艺': 1.8, '优酷': 1.7
        }.get(drama_info['platform'], 1.0)
        
        base_viewers = avg_rating * 1000000 * platform_mult
        return int(base_viewers)
    
    def analyze_platform_preference(self, genre_pref):
        """
        分析社交媒体平台偏好
        """
        platform_pref = defaultdict(float)
        
        for age_group, pref_ratio in genre_pref.items():
            age_platforms = self.params['social_platform_preference'].get(age_group, {})
            for platform, platform_p in age_platforms.items():
                platform_pref[platform] += pref_ratio * platform_p
        
        total = sum(platform_pref.values())
        return {
            platform: round(score / total, 4) for platform, score in platform_pref.items()
        }
    
    def estimate_income_distribution(self, genre_pref):
        """
        估算收入分布
        """
        income_map = {
            '18-24': {'low': 0.6, 'medium': 0.3, 'high': 0.1},
            '25-34': {'low': 0.3, 'medium': 0.5, 'high': 0.2},
            '35-44': {'low': 0.2, 'medium': 0.5, 'high': 0.3},
            '45-54': {'low': 0.25, 'medium': 0.5, 'high': 0.25},
            '55+': {'low': 0.4, 'medium': 0.45, 'high': 0.15}
        }
        
        income_dist = {'low': 0, 'medium': 0, 'high': 0}
        for age_group, pref_ratio in genre_pref.items():
            age_income = income_map.get(age_group, {})
            for inc_level, inc_ratio in age_income.items():
                income_dist[inc_level] += pref_ratio * inc_ratio
        
        return {k: round(v, 4) for k, v in income_dist.items()}
    
    def calculate_engagement_level(self, social_df):
        """
        计算观众参与度
        """
        if social_df is None:
            return {'level': '中等', 'score': 0.5}
        
        avg_post = social_df['post_volume'].mean() if 'post_volume' in social_df.columns else 1000
        avg_like = social_df['like_volume'].mean() if 'like_volume' in social_df.columns else 5000
        avg_sentiment = social_df['sentiment_score'].mean() if 'sentiment_score' in social_df.columns else 0.5
        
        post_score = min(1.0, avg_post / 5000)
        like_score = min(1.0, avg_like / 20000)
        sentiment_score = avg_sentiment
        
        total_score = (post_score * 0.3 + like_score * 0.4 + sentiment_score * 0.3)
        
        if total_score >= 0.7:
            level = '高'
        elif total_score >= 0.4:
            level = '中等'
        else:
            level = '低'
        
        return {'level': level, 'score': round(total_score, 4)}
    
    def identify_key_segments(self, age_distribution):
        """
        识别核心观众群体
        """
        segments = []
        for age_group, data in age_distribution.items():
            if data['ratio'] >= 0.25:
                segments.append({
                    'age_group': age_group,
                    'description': f"{age_group}岁",
                    'importance': '核心',
                    'value_index': round(data['ratio'] * data['value_multiplier'], 4)
                })
            elif data['ratio'] >= 0.15:
                segments.append({
                    'age_group': age_group,
                    'description': f"{age_group}岁",
                    'importance': '重要',
                    'value_index': round(data['ratio'] * data['value_multiplier'], 4)
                })
        
        return sorted(segments, key=lambda x: x['value_index'], reverse=True)
    
    def calculate_audience_overlap(self, profile1, profile2):
        """
        计算两个剧集的观众重叠度
        
        使用余弦相似度计算年龄分布的重叠度
        """
        age_groups = self.params['age_groups']
        
        vec1 = np.array([profile1['age_distribution'].get(age, {}).get('ratio', 0) for age in age_groups])
        vec2 = np.array([profile2['age_distribution'].get(age, {}).get('ratio', 0) for age in age_groups])
        
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            overlap = 0.0
        else:
            overlap = np.dot(vec1, vec2) / (norm1 * norm2)
        
        gender_overlap = 1 - abs(
            profile1['gender_distribution']['female'] / sum(profile1['gender_distribution'].values()) -
            profile2['gender_distribution']['female'] / sum(profile2['gender_distribution'].values())
        )
        
        combined_overlap = overlap * 0.7 + gender_overlap * 0.3
        
        if combined_overlap >= self.params['overlap_threshold_high']:
            level = '极高'
        elif combined_overlap >= self.params['overlap_threshold_medium']:
            level = '中等'
        else:
            level = '较低'
        
        return {
            'age_overlap': round(overlap, 4),
            'gender_overlap': round(gender_overlap, 4),
            'combined_overlap': round(combined_overlap, 4),
            'overlap_level': level
        }
    
    def recommend_cross_promotion(self, target_profile, other_profiles):
        """
        推荐交叉推广的剧集
        
        基于观众重叠度和剧集特征推荐最合适的交叉推广对象
        """
        recommendations = []
        
        for other_id, other_profile in other_profiles.items():
            overlap = self.calculate_audience_overlap(target_profile, other_profile)
            
            platform_match = 0.5
            if other_profile.get('platform_preference') and target_profile.get('platform_preference'):
                platforms1 = set(other_profile['platform_preference'].keys())
                platforms2 = set(target_profile['platform_preference'].keys())
                if platforms1 & platforms2:
                    platform_match = 0.8
            
            promo_score = overlap['combined_overlap'] * 0.6 + platform_match * 0.4
            
            if promo_score >= self.params['cross_promotion_score_threshold']:
                recommendations.append({
                    'drama_id': other_id,
                    'drama_name': other_profile.get('name', other_id),
                    'overlap_score': overlap['combined_overlap'],
                    'overlap_level': overlap['overlap_level'],
                    'promotion_score': round(promo_score, 4),
                    'promotion_strength': '强' if promo_score >= 0.8 else ('中' if promo_score >= 0.6 else '弱'),
                    'recommended_actions': self.generate_promotion_actions(overlap, target_profile, other_profile)
                })
        
        return sorted(recommendations, key=lambda x: x['promotion_score'], reverse=True)
    
    def generate_promotion_actions(self, overlap, profile1, profile2):
        """
        生成具体的交叉推广建议
        """
        actions = []
        
        if overlap['overlap_level'] == '极高':
            actions.append('联合制作联动剧情，角色跨剧客串')
            actions.append('共享演员资源，互相宣传')
        
        if overlap['age_overlap'] >= 0.6:
            common_ages = []
            for age in self.params['age_groups']:
                r1 = profile1['age_distribution'].get(age, {}).get('ratio', 0)
                r2 = profile2['age_distribution'].get(age, {}).get('ratio', 0)
                if r1 >= 0.2 and r2 >= 0.2:
                    common_ages.append(age)
            if common_ages:
                actions.append(f"针对{', '.join(common_ages)}岁群体进行定向营销")
        
        if profile1.get('platform_preference') and profile2.get('platform_preference'):
            best_platform = max(
                profile1['platform_preference'].items(),
                key=lambda x: x[1] * profile2['platform_preference'].get(x[0], 0)
            )[0]
            actions.append(f"在{best_platform}平台进行联合推广活动")
        
        if not actions:
            actions.append('社交媒体互相宣传，发布联合海报')
        
        return actions

if __name__ == '__main__':
    print("Testing Advanced Analysis Modules...")
    
    from data_generator import generate_drama_basic_info
    
    target_drama = generate_drama_basic_info()
    target_drama['name'] = '测试剧集'
    target_drama['num_episodes'] = 40
    target_drama['start_date'] = date(2024, 6, 1)
    target_drama['expected_rating'] = 2.0
    target_drama['production_budget'] = 30000
    target_drama['director_reputation'] = 0.85
    target_drama['is_sequel'] = False
    
    print("\n" + "="*80)
    print("  1. Testing Competition Analyzer")
    print("="*80)
    
    comp_analyzer = CompetitionAnalyzer()
    competitors = comp_analyzer.generate_competing_dramas(target_drama, num_competitors=5)
    
    print(f"\n  Generated {len(competitors)} competing dramas")
    print(f"  {'ID':<8} {'名称':<12} {'题材':<6} {'平台':<8} {'时段':<10} {'重叠天数':<8} {'影响':<8}")
    print(f"  {'-'*8} {'-'*12} {'-'*6} {'-'*8} {'-'*10} {'-'*8} {'-'*8}")
    
    for comp in competitors[:3]:
        print(f"  {comp['drama_id']:<8} {comp['name']:<12} {comp['genre']:<6} {comp['platform']:<8} {comp['time_slot']:<10} {comp['overlap_days']:<8} {comp['overlap_ratio']*100:>6.1f}%")
    
    impact = comp_analyzer.calculate_competition_impact(target_drama, competitors)
    print(f"\n  Total Competition Penalty: {impact['total_penalty_percent']}")
    print(f"  Adjustment Factor: {impact['adjustment_factor']}")
    print(f"  Active Competitors: {impact['active_competitors']}")
    
    print("\n" + "="*80)
    print("  2. Testing Advertising Value Evaluator")
    print("="*80)
    
    ad_evaluator = AdvertisingValueEvaluator()
    sample_rating = 2.5
    episode_info = {'episode': 10, 'date': date(2024, 6, 10), 'is_peak': True}
    
    ad_value = ad_evaluator.calculate_ad_value(sample_rating, episode_info, target_drama)
    print(f"\n  Rating: {sample_rating}%")
    print(f"  Base CPM (15s): {ad_value['base_value_per_15s']:.2f} 元")
    print(f"  Total Episode Ad Value: {ad_value['total_ad_value_with_audience']:.2f} 元")
    print(f"\n  Ad Slots:")
    for slot_key, slot_data in ad_value['ad_slots'].items():
        print(f"    {slot_data['name']:<10} ({slot_data['duration']:>2}s): {slot_data['total_value']:>10.2f} 元")
    
    print("\n" + "="*80)
    print("  3. Testing Audience Profiler")
    print("="*80)
    
    profiler = AudienceProfiler()
    predictions = np.random.uniform(1.5, 3.5, 40)
    profile = profiler.generate_audience_profile(target_drama, predictions)
    
    print(f"\n  Total Viewers Estimate: {profile['total_viewers_estimate']:,}")
    print(f"  Engagement Level: {profile['engagement_level']['level']} ({profile['engagement_level']['score']:.2f})")
    print(f"\n  Age Distribution:")
    for age, data in profile['age_distribution'].items():
        bar = '█' * int(data['ratio'] * 50)
        print(f"    {age:<6}: {bar} {data['ratio']*100:>5.1f}% ({data['viewers']:,}人)")
    
    print(f"\n  Gender Distribution:")
    print(f"    Male: {profile['gender_distribution']['male']:,}")
    print(f"    Female: {profile['gender_distribution']['female']:,}")
    
    print(f"\n  Social Platform Preference:")
    for platform, pref in sorted(profile['platform_preference'].items(), key=lambda x: x[1], reverse=True):
        bar = '█' * int(pref * 50)
        print(f"    {platform:<6}: {bar} {pref*100:>5.1f}%")
    
    print(f"\n  Key Audience Segments:")
    for seg in profile['key_audience_segments']:
        print(f"    {seg['description']:<10} - {seg['importance']} (价值指数: {seg['value_index']:.3f})")
    
    print("\n" + "="*80)
    print("  All Tests Passed!")
    print("="*80)
