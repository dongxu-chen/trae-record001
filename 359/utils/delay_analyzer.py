import numpy as np
import pandas as pd
from datetime import datetime


class DelayAnalyzer:
    FACTOR_THRESHOLDS = {
        'weather': {
            'normal': {'precipitation': 0.5, 'wind': 3, 'description': '天气正常'},
            'mild': {'precipitation': 2.5, 'wind': 5, 'description': '轻微影响'},
            'moderate': {'precipitation': 8.0, 'wind': 7, 'description': '中等影响'},
            'severe': {'precipitation': 20.0, 'wind': 10, 'description': '严重影响'},
        },
        'congestion': {
            'normal': {'busy_score': 0.5, 'description': '交通正常'},
            'mild': {'busy_score': 0.7, 'description': '轻度拥堵'},
            'moderate': {'busy_score': 0.85, 'description': '中度拥堵'},
            'severe': {'busy_score': 1.0, 'description': '严重拥堵'},
        },
        'overload': {
            'normal': {'volume_factor': 1.3, 'description': '运转正常'},
            'mild': {'volume_factor': 1.8, 'description': '轻度爆仓'},
            'moderate': {'volume_factor': 2.5, 'description': '中度爆仓'},
            'severe': {'volume_factor': 3.5, 'description': '严重爆仓'},
        }
    }
    
    FACTOR_WEIGHTS = {
        'weather': 0.35,
        'congestion': 0.35,
        'overload': 0.30
    }
    
    def __init__(self):
        pass
    
    def analyze(self, features_dict, predicted_hours, expected_hours=None):
        if expected_hours is None:
            distance = features_dict.get('distance', 100)
            expected_hours = distance / 60 + 4
        
        delay_hours = max(0, predicted_hours - expected_hours)
        delay_pct = (delay_hours / max(expected_hours, 1)) * 100
        
        weather_score = self._calculate_weather_factor(features_dict)
        congestion_score = self._calculate_congestion_factor(features_dict)
        overload_score = self._calculate_overload_factor(features_dict)
        
        total_score = (weather_score + congestion_score + overload_score) / 3
        
        factors = {
            'weather_delay': {
                'score': weather_score,
                'weight': self.FACTOR_WEIGHTS['weather'],
                'level': self._get_factor_level('weather', features_dict),
                'delay_hours': delay_hours * weather_score * self.FACTOR_WEIGHTS['weather'] / max(total_score, 0.01),
                'description': self._get_weather_description(features_dict)
            },
            'congestion_delay': {
                'score': congestion_score,
                'weight': self.FACTOR_WEIGHTS['congestion'],
                'level': self._get_factor_level('congestion', features_dict),
                'delay_hours': delay_hours * congestion_score * self.FACTOR_WEIGHTS['congestion'] / max(total_score, 0.01),
                'description': self._get_congestion_description(features_dict)
            },
            'overload_delay': {
                'score': overload_score,
                'weight': self.FACTOR_WEIGHTS['overload'],
                'level': self._get_factor_level('overload', features_dict),
                'delay_hours': delay_hours * overload_score * self.FACTOR_WEIGHTS['overload'] / max(total_score, 0.01),
                'description': self._get_overload_description(features_dict)
            }
        }
        
        dominant_factor = max(factors, key=lambda k: factors[k]['delay_hours'])
        
        severity = self._get_severity_level(delay_pct)
        
        recommendations = self._generate_recommendations(factors, dominant_factor, severity)
        
        return {
            'predicted_hours': predicted_hours,
            'expected_hours': expected_hours,
            'delay_hours': delay_hours,
            'delay_pct': delay_pct,
            'severity': severity,
            'factors': factors,
            'dominant_factor': dominant_factor,
            'dominant_factor_name': self._translate_factor_name(dominant_factor),
            'recommendations': recommendations
        }
    
    def _calculate_weather_factor(self, features_dict):
        precip_rate = features_dict.get('precipitation_rate', 0)
        precip_intensity = features_dict.get('precipitation_intensity', 0)
        precip_coverage = features_dict.get('precipitation_coverage', 0)
        wind = features_dict.get('windpower', 2)
        weather_encoded = features_dict.get('weather_encoded', 0)
        
        score = 0.0
        score += min(precip_rate / 20, 1.0) * 0.4
        score += min(precip_intensity / 4, 1.0) * 0.2
        score += precip_coverage * 0.15
        score += min((wind - 2) / 8, 1.0) * 0.15
        score += min(weather_encoded / 12, 1.0) * 0.1
        
        return min(max(score, 0), 1.0)
    
    def _calculate_congestion_factor(self, features_dict):
        busy_score = features_dict.get('busy_score', 0.5)
        busy_impact = features_dict.get('busy_impact', 1.0)
        is_weekend = features_dict.get('is_weekend', 0)
        is_night = features_dict.get('is_night', 0)
        
        score = 0.0
        score += busy_score * 0.5
        score += (busy_impact - 1) / 0.3 * 0.3
        score += is_weekend * 0.1
        score += is_night * 0.1
        
        return min(max(score, 0), 1.0)
    
    def _calculate_overload_factor(self, features_dict):
        holiday_delay = features_dict.get('holiday_delay_factor', 1.0)
        holiday_volume = features_dict.get('holiday_volume_factor', 1.0)
        is_ecommerce = features_dict.get('is_ecommerce_promo', 0)
        is_spring_festival = features_dict.get('is_spring_festival', 0)
        
        score = 0.0
        score += (holiday_delay - 1) / 1.0 * 0.3
        score += (holiday_volume - 1) / 2.5 * 0.3
        score += is_ecommerce * 0.2
        score += is_spring_festival * 0.2
        
        return min(max(score, 0), 1.0)
    
    def _get_factor_level(self, factor_type, features_dict):
        thresholds = self.FACTOR_THRESHOLDS[factor_type]
        
        if factor_type == 'weather':
            precip = features_dict.get('precipitation_rate', 0)
            wind = features_dict.get('windpower', 2)
            if precip >= thresholds['severe']['precipitation'] or wind >= thresholds['severe']['wind']:
                return 'severe'
            elif precip >= thresholds['moderate']['precipitation'] or wind >= thresholds['moderate']['wind']:
                return 'moderate'
            elif precip >= thresholds['mild']['precipitation'] or wind >= thresholds['mild']['wind']:
                return 'mild'
            return 'normal'
        
        elif factor_type == 'congestion':
            busy = features_dict.get('busy_score', 0.5)
            if busy >= thresholds['severe']['busy_score']:
                return 'severe'
            elif busy >= thresholds['moderate']['busy_score']:
                return 'moderate'
            elif busy >= thresholds['mild']['busy_score']:
                return 'mild'
            return 'normal'
        
        elif factor_type == 'overload':
            volume = features_dict.get('holiday_volume_factor', 1.0)
            if volume >= thresholds['severe']['volume_factor']:
                return 'severe'
            elif volume >= thresholds['moderate']['volume_factor']:
                return 'moderate'
            elif volume >= thresholds['mild']['volume_factor']:
                return 'mild'
            return 'normal'
        
        return 'normal'
    
    def _get_weather_description(self, features_dict):
        weather = features_dict.get('weather', '晴')
        precip = features_dict.get('precipitation_rate', 0)
        wind = features_dict.get('windpower', 2)
        
        if precip == 0:
            return f"天气{weather}，无降水影响"
        elif precip < 0.5:
            return f"天气{weather}，有微量降水"
        elif precip < 2.5:
            return f"天气{weather}，小雨可能影响运输速度"
        elif precip < 8:
            return f"天气{weather}，中雨导致运输延误"
        else:
            return f"天气{weather}，大雨严重影响运输"
    
    def _get_congestion_description(self, features_dict):
        busy = features_dict.get('busy_score', 0.5)
        busy_levels = ['空闲', '正常', '繁忙', '非常繁忙']
        idx = min(int(busy * 4), 3)
        level = busy_levels[idx]
        
        if busy < 0.5:
            return f"网点{level}，运输顺畅"
        elif busy < 0.8:
            return f"网点{level}，略有延误"
        else:
            return f"网点{level}，严重拥堵"
    
    def _get_overload_description(self, features_dict):
        volume_factor = features_dict.get('holiday_volume_factor', 1.0)
        holiday_name = features_dict.get('holiday_name', None)
        
        if holiday_name:
            if volume_factor > 2:
                return f"{holiday_name}期间，快递量激增{volume_factor:.1f}倍，仓库爆仓"
            elif volume_factor > 1.3:
                return f"{holiday_name}期间，快递量增加{volume_factor:.1f}倍，处理延迟"
            else:
                return f"{holiday_name}期间，影响不大"
        else:
            days_until = features_dict.get('days_until_holiday', -1)
            if 0 < days_until <= 7:
                return f"临近节假日，预计快递量增加"
            return "正常运营"
    
    def _get_severity_level(self, delay_pct):
        if delay_pct <= 10:
            return 'normal'
        elif delay_pct <= 30:
            return 'mild'
        elif delay_pct <= 60:
            return 'moderate'
        else:
            return 'severe'
    
    def _translate_factor_name(self, factor_key):
        names = {
            'weather_delay': '天气因素',
            'congestion_delay': '交通/网点拥堵',
            'overload_delay': '仓库爆仓/节假日'
        }
        return names.get(factor_key, factor_key)
    
    def _generate_recommendations(self, factors, dominant_factor, severity):
        recommendations = []
        
        weather_factor = factors['weather_delay']
        congestion_factor = factors['congestion_delay']
        overload_factor = factors['overload_delay']
        
        if weather_factor['level'] in ['moderate', 'severe']:
            recommendations.append({
                'type': 'weather',
                'priority': 'high' if weather_factor['level'] == 'severe' else 'medium',
                'content': f"建议选择空运或高优先级服务，避免{weather_factor['level']}天气影响"
            })
        
        if congestion_factor['level'] in ['moderate', 'severe']:
            recommendations.append({
                'type': 'congestion',
                'priority': 'high' if congestion_factor['level'] == 'severe' else 'medium',
                'content': '建议避开高峰时段下单，或选择自提柜减少末端配送压力'
            })
        
        if overload_factor['level'] in ['moderate', 'severe']:
            recommendations.append({
                'type': 'overload',
                'priority': 'high' if overload_factor['level'] == 'severe' else 'medium',
                'content': '建议提前下单或选择京东/顺丰等运力充足的快递公司'
            })
        
        if severity in ['moderate', 'severe']:
            recommendations.append({
                'type': 'general',
                'priority': 'high',
                'content': '当前综合延误风险较高，建议预留充足时间或选择加急服务'
            })
        
        if not recommendations:
            recommendations.append({
                'type': 'general',
                'priority': 'low',
                'content': '当前条件下快递时效正常，可放心寄件'
            })
        
        return recommendations
    
    def get_factor_contribution(self, analysis_result):
        factors = analysis_result['factors']
        total_delay = sum(f['delay_hours'] for f in factors.values())
        
        contributions = []
        for key, factor in factors.items():
            pct = (factor['delay_hours'] / max(total_delay, 0.01)) * 100
            contributions.append({
                'factor': key,
                'factor_name': self._translate_factor_name(key),
                'contribution_pct': round(pct, 1),
                'delay_hours': round(factor['delay_hours'], 1),
                'level': factor['level']
            })
        
        return sorted(contributions, key=lambda x: x['contribution_pct'], reverse=True)
