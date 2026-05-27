import numpy as np
import pandas as pd
from datetime import timedelta


class CourierComparison:
    COURIER_DATA = {
        '顺丰速运': {
            'base_fee': 23,
            'fee_per_kg': 10,
            'speed_multiplier': 0.75,
            'reliability': 0.95,
            'coverage': ['全国', '港澳台', '国际'],
            'max_weight': 100,
            'features': ['空运优先', '时效稳定', '上门取件', '保价服务'],
            'best_for': '急件、贵重物品、高价值商品',
            'holiday_impact': 0.85,
            'weather_impact': 0.90,
            'congestion_impact': 0.88,
        },
        '京东物流': {
            'base_fee': 18,
            'fee_per_kg': 8,
            'speed_multiplier': 0.80,
            'reliability': 0.92,
            'coverage': ['全国', '港澳台'],
            'max_weight': 50,
            'features': ['自有物流', '211限时达', '仓储一体', '大件专送'],
            'best_for': '大件家电、电商急件、当日达',
            'holiday_impact': 0.75,
            'weather_impact': 0.88,
            'congestion_impact': 0.82,
        },
        '圆通速递': {
            'base_fee': 12,
            'fee_per_kg': 5,
            'speed_multiplier': 1.05,
            'reliability': 0.85,
            'coverage': ['全国', '港澳台'],
            'max_weight': 30,
            'features': ['价格实惠', '网点密集', '电商合作'],
            'best_for': '普通快递、电商批量发货',
            'holiday_impact': 1.35,
            'weather_impact': 1.10,
            'congestion_impact': 1.20,
        },
        '中通快递': {
            'base_fee': 12,
            'fee_per_kg': 5,
            'speed_multiplier': 1.08,
            'reliability': 0.86,
            'coverage': ['全国', '港澳台'],
            'max_weight': 30,
            'features': ['价格便宜', '网点广', '乡镇可达'],
            'best_for': '普通包裹、偏远地区',
            'holiday_impact': 1.30,
            'weather_impact': 1.12,
            'congestion_impact': 1.22,
        },
        '韵达速递': {
            'base_fee': 12,
            'fee_per_kg': 5,
            'speed_multiplier': 1.10,
            'reliability': 0.84,
            'coverage': ['全国', '港澳台'],
            'max_weight': 30,
            'features': ['价格低', '服务全'],
            'best_for': '轻量小件、日常寄送',
            'holiday_impact': 1.40,
            'weather_impact': 1.15,
            'congestion_impact': 1.25,
        },
        '百世快递': {
            'base_fee': 11,
            'fee_per_kg': 5,
            'speed_multiplier': 1.12,
            'reliability': 0.82,
            'coverage': ['全国', '港澳台'],
            'max_weight': 30,
            'features': ['经济实惠', '代收点多'],
            'best_for': '经济型快递、不急用物品',
            'holiday_impact': 1.45,
            'weather_impact': 1.18,
            'congestion_impact': 1.28,
        },
        '邮政EMS': {
            'base_fee': 21,
            'fee_per_kg': 6,
            'speed_multiplier': 1.00,
            'reliability': 0.90,
            'coverage': ['全国', '港澳台', '国际'],
            'max_weight': 50,
            'features': ['官方背书', '全境可达', '安全可靠', '文件专递'],
            'best_for': '证件文件、偏远地区、政府公文',
            'holiday_impact': 1.05,
            'weather_impact': 0.95,
            'congestion_impact': 1.08,
        },
        '德邦快递': {
            'base_fee': 50,
            'fee_per_kg': 3,
            'speed_multiplier': 1.15,
            'reliability': 0.88,
            'coverage': ['全国'],
            'max_weight': 300,
            'features': ['大件快递', '送货上楼', '上门取件'],
            'best_for': '大件重物、搬家运输',
            'holiday_impact': 1.20,
            'weather_impact': 1.05,
            'congestion_impact': 1.15,
        },
    }
    
    SERVICE_TYPES = {
        'standard': {'name': '标准快递', 'speed_factor': 1.0, 'fee_factor': 1.0},
        'express': {'name': '特快专递', 'speed_factor': 0.7, 'fee_factor': 1.5},
        'economy': {'name': '经济快递', 'speed_factor': 1.3, 'fee_factor': 0.7},
        'same_day': {'name': '当日达', 'speed_factor': 0.3, 'fee_factor': 2.5},
        'next_day': {'name': '次日达', 'speed_factor': 0.5, 'fee_factor': 1.8},
    }
    
    def __init__(self):
        pass
    
    def calculate_courier_hours(self, courier_name, base_hours, features_dict, service_type='standard'):
        courier = self.COURIER_DATA.get(courier_name)
        if not courier:
            return base_hours
        
        service = self.SERVICE_TYPES.get(service_type, self.SERVICE_TYPES['standard'])
        
        hours = base_hours * courier['speed_multiplier'] * service['speed_factor']
        
        holiday_factor = features_dict.get('holiday_delay_factor', 1.0)
        weather_factor = features_dict.get('weather_impact', 1.0)
        congestion_factor = features_dict.get('busy_impact', 1.0)
        
        hours *= (courier['holiday_impact'] * holiday_factor) ** 0.5
        hours *= (courier['weather_impact'] * weather_factor) ** 0.3
        hours *= (courier['congestion_impact'] * congestion_factor) ** 0.3
        
        return max(1, hours)
    
    def calculate_courier_fee(self, courier_name, weight=1, distance=100, service_type='standard'):
        courier = self.COURIER_DATA.get(courier_name)
        if not courier:
            return 0
        
        service = self.SERVICE_TYPES.get(service_type, self.SERVICE_TYPES['standard'])
        
        fee = courier['base_fee'] + max(0, weight - 1) * courier['fee_per_kg']
        
        if distance > 500:
            fee += (distance - 500) * 0.05
        
        fee *= service['fee_factor']
        
        return round(fee, 2)
    
    def compare_couriers(self, base_hours, features_dict, weight=1, distance=100, 
                         couriers=None, service_type='standard'):
        if couriers is None:
            couriers = list(self.COURIER_DATA.keys())
        
        results = []
        for name in couriers:
            courier = self.COURIER_DATA[name]
            
            hours = self.calculate_courier_hours(name, base_hours, features_dict, service_type)
            fee = self.calculate_courier_fee(name, weight, distance, service_type)
            
            speed_score = 100 / max(hours, 1)
            cost_score = 100 / max(fee, 1)
            reliability_score = courier['reliability'] * 100
            
            overall_score = speed_score * 0.4 + cost_score * 0.3 + reliability_score * 0.3
            
            results.append({
                'courier_name': name,
                'estimated_hours': round(hours, 1),
                'estimated_days': round(hours / 24, 1),
                'estimated_fee': fee,
                'reliability': courier['reliability'],
                'speed_score': round(speed_score, 1),
                'cost_score': round(cost_score, 1),
                'reliability_score': round(reliability_score, 1),
                'overall_score': round(overall_score, 1),
                'best_for': courier['best_for'],
                'features': courier['features'],
                'holiday_resistance': round(1 / courier['holiday_impact'], 2),
                'weather_resistance': round(1 / courier['weather_impact'], 2),
                'congestion_resistance': round(1 / courier['congestion_impact'], 2),
            })
        
        results.sort(key=lambda x: x['overall_score'], reverse=True)
        
        for i, r in enumerate(results):
            r['rank'] = i + 1
        
        return results
    
    def recommend_courier(self, comparison_results, priority='balanced'):
        if not comparison_results:
            return None
        
        if priority == 'speed':
            results = sorted(comparison_results, key=lambda x: x['estimated_hours'])
        elif priority == 'cost':
            results = sorted(comparison_results, key=lambda x: x['estimated_fee'])
        elif priority == 'reliability':
            results = sorted(comparison_results, key=lambda x: x['reliability'], reverse=True)
        else:
            results = sorted(comparison_results, key=lambda x: x['overall_score'], reverse=True)
        
        best = results[0]
        
        reasons = []
        if priority == 'speed':
            reasons.append(f"时效最快，预计 {best['estimated_hours']:.1f} 小时送达")
        elif priority == 'cost':
            reasons.append(f"价格最低，预计费用 {best['estimated_fee']} 元")
        elif priority == 'reliability':
            reasons.append(f"可靠性最高，达 {best['reliability']*100:.0f}%")
        else:
            reasons.append(f"综合评分最高 ({best['overall_score']} 分)")
            reasons.append(f"时效 {best['estimated_hours']:.1f} 小时，费用 {best['estimated_fee']} 元")
        
        return {
            'recommended': best['courier_name'],
            'reasons': reasons,
            'details': best
        }
    
    def get_courier_options(self):
        return list(self.COURIER_DATA.keys())
    
    def get_service_options(self):
        return {key: val['name'] for key, val in self.SERVICE_TYPES.items()}
    
    def get_courier_summary(self, courier_name):
        courier = self.COURIER_DATA.get(courier_name)
        if not courier:
            return None
        
        return {
            'name': courier_name,
            'base_fee': courier['base_fee'],
            'fee_per_kg': courier['fee_per_kg'],
            'reliability': courier['reliability'],
            'coverage': courier['coverage'],
            'features': courier['features'],
            'best_for': courier['best_for'],
            'speed_rating': '⭐⭐⭐⭐⭐' if courier['speed_multiplier'] <= 0.8 else
                           '⭐⭐⭐⭐' if courier['speed_multiplier'] <= 1.0 else
                           '⭐⭐⭐' if courier['speed_multiplier'] <= 1.1 else '⭐⭐',
            'cost_rating': '⭐⭐⭐⭐⭐' if courier['base_fee'] <= 12 else
                          '⭐⭐⭐⭐' if courier['base_fee'] <= 18 else
                          '⭐⭐⭐' if courier['base_fee'] <= 23 else '⭐⭐',
        }
