import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import time


class SocialMediaAPI:
    def __init__(self, use_simulated_data: bool = True):
        self.use_simulated_data = use_simulated_data
        self.rate_limit_remaining = 100
        self.last_request_time = 0
        
    def _check_rate_limit(self):
        current_time = time.time()
        if current_time - self.last_request_time < 1:
            time.sleep(0.5)
        self.last_request_time = time.time()
        self.rate_limit_remaining -= 1
        
    def get_influencer_profile(self, influencer_id: str, influencer_data: pd.DataFrame) -> Dict:
        self._check_rate_limit()
        if self.use_simulated_data:
            profile = influencer_data[influencer_data['id'] == influencer_id].iloc[0].to_dict()
            return {
                'success': True,
                'data': profile,
                'rate_limit_remaining': self.rate_limit_remaining
            }
        return {'success': False, 'error': 'Real API not implemented'}
    
    def get_influencer_metrics(self, influencer_id: str, influencer_data: pd.DataFrame) -> Dict:
        self._check_rate_limit()
        if self.use_simulated_data:
            row = influencer_data[influencer_data['id'] == influencer_id].iloc[0]
            
            engagement_rate = (row['avg_likes'] + row['avg_comments'] + row['avg_shares']) / row['followers'] * 100
            growth_rate = np.random.uniform(-2, 10)
            
            metrics = {
                'influencer_id': influencer_id,
                'followers': row['followers'],
                'followers_growth_30d': int(row['followers'] * growth_rate / 100),
                'followers_growth_rate': round(growth_rate, 2),
                'avg_views': row['avg_views'],
                'avg_likes': row['avg_likes'],
                'avg_comments': row['avg_comments'],
                'avg_shares': row['avg_shares'],
                'engagement_rate': round(engagement_rate, 2),
                'view_rate': round(row['avg_views'] / row['followers'] * 100, 2),
                'like_rate': round(row['avg_likes'] / row['followers'] * 100, 2),
                'comment_rate': round(row['avg_comments'] / row['followers'] * 100, 2),
                'share_rate': round(row['avg_shares'] / row['followers'] * 100, 2),
                'post_frequency': row['post_frequency'],
                'estimated_reach_per_post': int(row['followers'] * np.random.uniform(0.15, 0.4)),
                'authenticity_score': np.random.randint(60, 95)
            }
            
            return {
                'success': True,
                'data': metrics,
                'rate_limit_remaining': self.rate_limit_remaining
            }
        return {'success': False, 'error': 'Real API not implemented'}
    
    def batch_get_metrics(self, influencer_ids: List[str], influencer_data: pd.DataFrame) -> Dict:
        all_metrics = []
        for influencer_id in influencer_ids:
            result = self.get_influencer_metrics(influencer_id, influencer_data)
            if result['success']:
                all_metrics.append(result['data'])
        
        return {
            'success': True,
            'data': pd.DataFrame(all_metrics),
            'count': len(all_metrics)
        }


class FollowerAnalyzer:
    def __init__(self):
        self.age_groups = ['18-24', '25-34', '35-44', '45+']
        self.genders = ['男性', '女性']
        self.location_tiers = ['一线城市', '二线城市', '三线及以下']
    
    def analyze_demographics(self, demographics_df: pd.DataFrame, influencer_id: Optional[str] = None) -> Dict:
        if influencer_id:
            demo_data = demographics_df[demographics_df['influencer_id'] == influencer_id].iloc[0]
        else:
            demo_data = demographics_df.mean()
        
        age_distribution = {
            '18-24': demo_data['age_18_24'] * 100,
            '25-34': demo_data['age_25_34'] * 100,
            '35-44': demo_data['age_35_44'] * 100,
            '45+': demo_data['age_45_plus'] * 100
        }
        
        gender_distribution = {
            '男性': demo_data['gender_male'] * 100,
            '女性': demo_data['gender_female'] * 100
        }
        
        location_distribution = {
            '一线城市': demo_data['location_tier1'] * 100,
            '二线城市': demo_data['location_tier2'] * 100,
            '三线及以下': demo_data['location_tier3_plus'] * 100
        }
        
        interest_columns = [col for col in demographics_df.columns if col.startswith('interest_')]
        interest_distribution = {}
        for col in interest_columns:
            interest_name = col.replace('interest_', '')
            interest_distribution[interest_name] = demo_data[col] * 100
        
        return {
            'age_distribution': age_distribution,
            'gender_distribution': gender_distribution,
            'location_distribution': location_distribution,
            'interest_distribution': interest_distribution
        }
    
    def calculate_audience_quality_score(self, demographics_df: pd.DataFrame, influencer_id: str, 
                                         target_demographics: Dict) -> Dict:
        demo_data = demographics_df[demographics_df['influencer_id'] == influencer_id].iloc[0]
        
        age_match_score = self._calculate_age_match(demo_data, target_demographics.get('age', []))
        gender_match_score = self._calculate_gender_match(demo_data, target_demographics.get('gender', []))
        location_match_score = self._calculate_location_match(demo_data, target_demographics.get('location', []))
        
        overall_score = (age_match_score * 0.35 + gender_match_score * 0.3 + location_match_score * 0.35)
        
        return {
            'overall_score': round(overall_score, 2),
            'age_match_score': round(age_match_score, 2),
            'gender_match_score': round(gender_match_score, 2),
            'location_match_score': round(location_match_score, 2),
            'recommendation': self._get_recommendation(overall_score)
        }
    
    def _calculate_age_match(self, demo_data: pd.Series, target_ages: List[str]) -> float:
        if not target_ages:
            return 70.0
        
        age_map = {
            '18-24': 'age_18_24',
            '25-34': 'age_25_34',
            '35-44': 'age_35_44',
            '45+': 'age_45_plus'
        }
        
        target_percentage = sum([demo_data[age_map[age]] for age in target_ages if age in age_map])
        return min(100, target_percentage * 100)
    
    def _calculate_gender_match(self, demo_data: pd.Series, target_genders: List[str]) -> float:
        if not target_genders:
            return 70.0
        
        score = 0
        if '男性' in target_genders:
            score += demo_data['gender_male'] * 100
        if '女性' in target_genders:
            score += demo_data['gender_female'] * 100
        
        return min(100, score / max(1, len(target_genders)))
    
    def _calculate_location_match(self, demo_data: pd.Series, target_locations: List[str]) -> float:
        if not target_locations:
            return 70.0
        
        location_map = {
            '一线城市': 'location_tier1',
            '二线城市': 'location_tier2',
            '三线及以下': 'location_tier3_plus'
        }
        
        target_percentage = sum([demo_data[location_map[loc]] for loc in target_locations if loc in location_map])
        return min(100, target_percentage * 100)
    
    def _get_recommendation(self, score: float) -> str:
        if score >= 80:
            return "粉丝画像与目标受众高度匹配，强烈推荐合作"
        elif score >= 60:
            return "粉丝画像与目标受众较为匹配，推荐合作"
        elif score >= 40:
            return "粉丝画像与目标受众部分匹配，可考虑合作"
        else:
            return "粉丝画像与目标受众匹配度较低，建议谨慎选择"
    
    def compare_influencers_audience(self, demographics_df: pd.DataFrame, 
                                     influencer_ids: List[str]) -> pd.DataFrame:
        comparison_data = []
        
        for influencer_id in influencer_ids:
            demo_data = demographics_df[demographics_df['influencer_id'] == influencer_id].iloc[0]
            
            data = {
                'influencer_id': influencer_id,
                'influencer_name': demo_data['influencer_name'],
                '18-24占比(%)': round(demo_data['age_18_24'] * 100, 1),
                '25-34占比(%)': round(demo_data['age_25_34'] * 100, 1),
                '35-44占比(%)': round(demo_data['age_35_44'] * 100, 1),
                '45+占比(%)': round(demo_data['age_45_plus'] * 100, 1),
                '女性占比(%)': round(demo_data['gender_female'] * 100, 1),
                '一线城市占比(%)': round(demo_data['location_tier1'] * 100, 1)
            }
            comparison_data.append(data)
        
        return pd.DataFrame(comparison_data)


class MultiSourceValidator:
    def __init__(self):
        self.data_sources = [
            {'name': '平台API', 'weight': 0.35, 'reliability': 0.9},
            {'name': '第三方数据', 'weight': 0.25, 'reliability': 0.8},
            {'name': '抽样调研', 'weight': 0.20, 'reliability': 0.85},
            {'name': '历史数据', 'weight': 0.20, 'reliability': 0.75}
        ]
        
    def generate_multi_source_data(self, base_demo_data: pd.Series) -> Dict:
        np.random.seed(42)
        source_data = {}
        
        for source in self.data_sources:
            noise_level = (1 - source['reliability']) * 0.15
            source_variation = {}
            
            for col in base_demo_data.index:
                if isinstance(base_demo_data[col], (int, float)) and col not in ['influencer_id', 'influencer_name']:
                    base_value = base_demo_data[col]
                    noise = np.random.uniform(-noise_level, noise_level)
                    source_variation[col] = max(0, min(1, base_value * (1 + noise)))
            
            source_data[source['name']] = source_variation
        
        return source_data
    
    def cross_validate_demographics(self, demographics_df: pd.DataFrame, 
                                     influencer_id: str) -> Dict:
        demo_data = demographics_df[demographics_df['influencer_id'] == influencer_id].iloc[0]
        source_data = self.generate_multi_source_data(demo_data)
        
        validation_result = self._weighted_aggregation(source_data, demo_data)
        
        return {
            'influencer_id': influencer_id,
            'influencer_name': demo_data['influencer_name'],
            'data_sources': source_data,
            'validated_demographics': validation_result['validated_data'],
            'confidence_scores': validation_result['confidence_scores'],
            'overall_confidence': validation_result['overall_confidence'],
            'bias_analysis': validation_result['bias_analysis'],
            'deviation_warnings': validation_result['deviation_warnings']
        }
    
    def _weighted_aggregation(self, source_data: Dict, base_data: pd.Series) -> Dict:
        validated_data = {}
        confidence_scores = {}
        deviation_warnings = []
        
        numeric_cols = [col for col in base_data.index 
                       if isinstance(base_data[col], (int, float)) 
                       and col not in ['influencer_id', 'influencer_name']]
        
        for col in numeric_cols:
            values = []
            weights = []
            
            for source_info in self.data_sources:
                source_name = source_info['name']
                if col in source_data[source_name]:
                    values.append(source_data[source_name][col])
                    weights.append(source_info['weight'])
            
            if values:
                weights = np.array(weights) / sum(weights)
                weighted_mean = np.average(values, weights=weights)
                std_dev = np.std(values)
                
                validated_data[col] = weighted_mean
                
                if std_dev > 0.08:
                    deviation_warnings.append({
                        'metric': col,
                        'std_dev': round(std_dev * 100, 2),
                        'warning': f'{col} 数据源间差异较大，建议核实'
                    })
                
                max_value = max(values)
                min_value = min(values)
                if max_value > 0 and (max_value - min_value) / max_value > 0.3:
                    deviation_warnings.append({
                        'metric': col,
                        'max_min_ratio': round(max_value / max(min_value, 0.001), 2),
                        'warning': f'{col} 极值差异超过30%，存在偏差风险'
                    })
                
                confidence = 1 - min(std_dev / 0.1, 1)
                confidence_scores[col] = round(confidence * 100, 2)
        
        overall_confidence = np.mean(list(confidence_scores.values())) if confidence_scores else 70
        
        bias_analysis = self._detect_bias(source_data, base_data)
        
        return {
            'validated_data': validated_data,
            'confidence_scores': confidence_scores,
            'overall_confidence': round(overall_confidence, 2),
            'bias_analysis': bias_analysis,
            'deviation_warnings': deviation_warnings
        }
    
    def _detect_bias(self, source_data: Dict, base_data: pd.Series) -> Dict:
        biases = []
        numeric_cols = [col for col in base_data.index 
                       if isinstance(base_data[col], (int, float)) 
                       and col not in ['influencer_id', 'influencer_name']]
        
        for col in numeric_cols:
            source_values = {}
            for source_info in self.data_sources:
                source_name = source_info['name']
                if col in source_data[source_name]:
                    source_values[source_name] = source_data[source_name][col]
            
            if len(source_values) >= 2:
                values = list(source_values.values())
                mean_val = np.mean(values)
                
                for source_name, val in source_values.items():
                    if mean_val > 0:
                        deviation = (val - mean_val) / mean_val
                        if abs(deviation) > 0.15:
                            biases.append({
                                'metric': col,
                                'source': source_name,
                                'deviation_percent': round(deviation * 100, 2),
                                'direction': '偏高' if deviation > 0 else '偏低',
                                'severity': '高' if abs(deviation) > 0.25 else '中'
                            })
        
        return {
            'detected_biases': biases,
            'bias_count': len(biases),
            'overall_bias_level': '低' if len(biases) == 0 else '中' if len(biases) <= 3 else '高'
        }
    
    def compare_source_consistency(self, demographics_df: pd.DataFrame, 
                                    influencer_ids: List[str]) -> pd.DataFrame:
        comparison_data = []
        
        for influencer_id in influencer_ids:
            validation = self.cross_validate_demographics(demographics_df, influencer_id)
            
            data = {
                'influencer_id': influencer_id,
                'influencer_name': validation['influencer_name'],
                '整体置信度(%)': validation['overall_confidence'],
                '数据偏差等级': validation['bias_analysis']['overall_bias_level'],
                '偏差项数量': validation['bias_analysis']['bias_count'],
                '异常警告数': len(validation['deviation_warnings'])
            }
            comparison_data.append(data)
        
        return pd.DataFrame(comparison_data)
