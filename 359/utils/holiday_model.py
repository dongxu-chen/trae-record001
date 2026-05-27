import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class HolidayModel:
    CHINA_HOLIDAYS_2024 = {
        '元旦': {'start': '2024-01-01', 'end': '2024-01-01', 'volume_factor': 1.3, 'delay_factor': 1.15},
        '春节': {'start': '2024-02-10', 'end': '2024-02-17', 'volume_factor': 0.4, 'delay_factor': 2.0},
        '春节前高峰': {'start': '2024-02-01', 'end': '2024-02-09', 'volume_factor': 2.0, 'delay_factor': 1.5},
        '春节后恢复': {'start': '2024-02-18', 'end': '2024-02-25', 'volume_factor': 1.5, 'delay_factor': 1.3},
        '清明节': {'start': '2024-04-04', 'end': '2024-04-06', 'volume_factor': 1.2, 'delay_factor': 1.2},
        '劳动节': {'start': '2024-05-01', 'end': '2024-05-05', 'volume_factor': 1.4, 'delay_factor': 1.25},
        '端午节': {'start': '2024-06-08', 'end': '2024-06-10', 'volume_factor': 1.2, 'delay_factor': 1.15},
        '中秋节': {'start': '2024-09-15', 'end': '2024-09-17', 'volume_factor': 1.3, 'delay_factor': 1.2},
        '国庆节': {'start': '2024-10-01', 'end': '2024-10-07', 'volume_factor': 1.6, 'delay_factor': 1.4},
        '双十一': {'start': '2024-11-11', 'end': '2024-11-11', 'volume_factor': 3.5, 'delay_factor': 2.0},
        '双十一后': {'start': '2024-11-12', 'end': '2024-11-20', 'volume_factor': 1.8, 'delay_factor': 1.5},
        '双十二': {'start': '2024-12-12', 'end': '2024-12-12', 'volume_factor': 2.5, 'delay_factor': 1.6},
        '年货节': {'start': '2024-12-25', 'end': '2024-12-31', 'volume_factor': 1.8, 'delay_factor': 1.4},
    }
    
    CHINA_HOLIDAYS_2025 = {
        '元旦': {'start': '2025-01-01', 'end': '2025-01-01', 'volume_factor': 1.3, 'delay_factor': 1.15},
        '春节': {'start': '2025-01-28', 'end': '2025-02-04', 'volume_factor': 0.4, 'delay_factor': 2.0},
        '春节前高峰': {'start': '2025-01-18', 'end': '2025-01-27', 'volume_factor': 2.0, 'delay_factor': 1.5},
        '春节后恢复': {'start': '2025-02-05', 'end': '2025-02-12', 'volume_factor': 1.5, 'delay_factor': 1.3},
        '清明节': {'start': '2025-04-04', 'end': '2025-04-06', 'volume_factor': 1.2, 'delay_factor': 1.2},
        '劳动节': {'start': '2025-05-01', 'end': '2025-05-05', 'volume_factor': 1.4, 'delay_factor': 1.25},
        '端午节': {'start': '2025-05-31', 'end': '2025-06-02', 'volume_factor': 1.2, 'delay_factor': 1.15},
        '中秋节': {'start': '2025-10-06', 'end': '2025-10-08', 'volume_factor': 1.3, 'delay_factor': 1.2},
        '国庆节': {'start': '2025-10-01', 'end': '2025-10-08', 'volume_factor': 1.6, 'delay_factor': 1.4},
        '双十一': {'start': '2025-11-11', 'end': '2025-11-11', 'volume_factor': 3.5, 'delay_factor': 2.0},
        '双十一后': {'start': '2025-11-12', 'end': '2025-11-20', 'volume_factor': 1.8, 'delay_factor': 1.5},
        '双十二': {'start': '2025-12-12', 'end': '2025-12-12', 'volume_factor': 2.5, 'delay_factor': 1.6},
        '年货节': {'start': '2025-12-20', 'end': '2025-12-31', 'volume_factor': 1.8, 'delay_factor': 1.4},
    }
    
    HOLIDAY_TYPES = {
        '法定节假日': ['元旦', '春节', '清明节', '劳动节', '端午节', '中秋节', '国庆节'],
        '电商促销节': ['双十一', '双十一后', '双十二', '年货节'],
        '特殊时期': ['春节前高峰', '春节后恢复'],
    }
    
    def __init__(self):
        self.all_holidays = {}
        for name, info in self.CHINA_HOLIDAYS_2024.items():
            self.all_holidays[f"2024_{name}"] = {'name': name, **info}
        for name, info in self.CHINA_HOLIDAYS_2025.items():
            self.all_holidays[f"2025_{name}"] = {'name': name, **info}
    
    def get_holiday_info(self, date):
        if isinstance(date, str):
            date = pd.to_datetime(date)
        elif isinstance(date, datetime):
            date = pd.Timestamp(date)
        
        date_str = date.strftime('%Y-%m-%d')
        
        for holiday_key, info in self.all_holidays.items():
            start = pd.to_datetime(info['start'])
            end = pd.to_datetime(info['end'])
            if start <= date <= end:
                return {
                    'is_holiday': True,
                    'holiday_name': info['name'],
                    'volume_factor': info['volume_factor'],
                    'delay_factor': info['delay_factor'],
                    'holiday_type': self._get_holiday_type(info['name']),
                    'days_until_holiday': 0,
                    'days_since_holiday': 0
                }
        
        nearest_holiday = None
        min_days = 999
        
        for holiday_key, info in self.all_holidays.items():
            holiday_start = pd.to_datetime(info['start'])
            days_until = (holiday_start - date).days
            if 0 < days_until < min_days:
                min_days = days_until
                nearest_holiday = (info['name'], info, days_until)
        
        return {
            'is_holiday': False,
            'holiday_name': nearest_holiday[0] if nearest_holiday else None,
            'volume_factor': 1.0,
            'delay_factor': 1.0,
            'holiday_type': None,
            'days_until_holiday': nearest_holiday[2] if nearest_holiday else -1,
            'nearest_volume_factor': nearest_holiday[1]['volume_factor'] if nearest_holiday else 1.0,
            'nearest_delay_factor': nearest_holiday[1]['delay_factor'] if nearest_holiday else 1.0
        }
    
    def _get_holiday_type(self, holiday_name):
        for htype, names in self.HOLIDAY_TYPES.items():
            if holiday_name in names:
                return htype
        return '其他'
    
    def predict_volume_change(self, date, base_volume=10000):
        info = self.get_holiday_info(date)
        
        if info['is_holiday']:
            predicted_volume = base_volume * info['volume_factor']
            return {
                'predicted_volume': predicted_volume,
                'volume_change_pct': (info['volume_factor'] - 1) * 100,
                'is_holiday': True,
                'holiday_name': info['holiday_name'],
                'confidence': 'high'
            }
        else:
            days_until = info['days_until_holiday']
            if days_until > 0 and days_until <= 7:
                ramp_up = info['nearest_volume_factor'] ** (1 - days_until / 7)
                predicted_volume = base_volume * ramp_up
                return {
                    'predicted_volume': predicted_volume,
                    'volume_change_pct': (ramp_up - 1) * 100,
                    'is_holiday': False,
                    'holiday_name': f"临近{info['holiday_name']}",
                    'confidence': 'medium'
                }
            else:
                return {
                    'predicted_volume': base_volume,
                    'volume_change_pct': 0,
                    'is_holiday': False,
                    'holiday_name': None,
                    'confidence': 'high'
                }
    
    def get_holiday_impact_features(self, date):
        info = self.get_holiday_info(date)
        
        features = {
            'is_holiday': 1 if info['is_holiday'] else 0,
            'holiday_volume_factor': info['volume_factor'],
            'holiday_delay_factor': info['delay_factor'],
            'days_near_holiday': min(info['days_until_holiday'], 14) if info['days_until_holiday'] > 0 else 0,
            'pre_holiday_peak': 1 if (info.get('holiday_name') and '前' in info['holiday_name']) else 0,
            'post_holiday_recovery': 1 if (info.get('holiday_name') and '后' in info['holiday_name']) else 0,
            'is_ecommerce_promo': 1 if (info.get('holiday_type') == '电商促销节') else 0,
            'is_spring_festival': 1 if (info.get('holiday_name') and '春节' in info['holiday_name']) else 0,
        }
        
        if not info['is_holiday'] and info['days_until_holiday'] > 0:
            features['days_until_holiday'] = info['days_until_holiday']
            features['proximal_volume_factor'] = info['nearest_volume_factor']
            features['proximal_delay_factor'] = info['nearest_delay_factor']
        else:
            features['days_until_holiday'] = -1
            features['proximal_volume_factor'] = 1.0
            features['proximal_delay_factor'] = 1.0
        
        return features
    
    def get_holiday_calendar(self, year=None):
        if year is None:
            year = datetime.now().year
        
        holidays = self.CHINA_HOLIDAYS_2024 if year == 2024 else self.CHINA_HOLIDAYS_2025
        if year not in [2024, 2025]:
            holidays = self.CHINA_HOLIDAYS_2024
        
        calendar_data = []
        for name, info in holidays.items():
            start = pd.to_datetime(info['start'])
            end = pd.to_datetime(info['end'])
            duration = (end - start).days + 1
            calendar_data.append({
                '节假日名称': name,
                '类型': self._get_holiday_type(name),
                '开始日期': start.strftime('%Y-%m-%d'),
                '结束日期': end.strftime('%Y-%m-%d'),
                '持续天数': duration,
                '快递量系数': info['volume_factor'],
                '延误系数': info['delay_factor'],
                '影响说明': self._get_impact_description(name, info)
            })
        
        return pd.DataFrame(calendar_data)
    
    def _get_impact_description(self, name, info):
        if info['volume_factor'] > 2:
            return f"快递量暴增至平时的{info['volume_factor']}倍，严重拥堵，延误显著"
        elif info['volume_factor'] > 1.3:
            return f"快递量增至平时的{info['volume_factor']}倍，可能出现延误"
        elif info['volume_factor'] < 0.5:
            return f"春节假期期间，快递量降至平时的{info['volume_factor']}倍，运输中断"
        else:
            return f"快递量变化不大，影响较小"
