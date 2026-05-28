import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple
import json
import os

class HolidayManager:
    def __init__(self, custom_holidays: List[str] = None):
        self.holidays = self._load_default_holidays()
        if custom_holidays:
            self.add_holidays(custom_holidays)
        
    def _load_default_holidays(self) -> Set[datetime]:
        default_holidays = set()
        
        for year in range(2020, 2030):
            default_holidays.add(datetime(year, 1, 1))
            default_holidays.add(datetime(year, 5, 1))
            default_holidays.add(datetime(year, 10, 1))
            default_holidays.add(datetime(year, 12, 25))
            
            easter_date = self._calculate_easter(year)
            default_holidays.add(easter_date)
            
            spring_festival = self._calculate_spring_festival(year)
            for i in range(7):
                default_holidays.add(spring_festival + timedelta(days=i))
        
        return default_holidays
    
    def _calculate_easter(self, year: int) -> datetime:
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return datetime(year, month, day)
    
    def _calculate_spring_festival(self, year: int) -> datetime:
        spring_festival_dates = {
            2020: (1, 25),
            2021: (2, 12),
            2022: (2, 1),
            2023: (1, 22),
            2024: (2, 10),
            2025: (1, 29),
            2026: (2, 17),
            2027: (2, 6),
            2028: (1, 26),
            2029: (2, 13),
        }
        if year in spring_festival_dates:
            month, day = spring_festival_dates[year]
            return datetime(year, month, day)
        return datetime(year, 2, 1)
    
    def add_holidays(self, dates: List[str]):
        for date_str in dates:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                self.holidays.add(dt)
            except ValueError:
                print(f"Invalid date format: {date_str}")
    
    def is_holiday(self, date: datetime) -> bool:
        date_only = datetime(date.year, date.month, date.day)
        return date_only in self.holidays
    
    def is_weekend(self, date: datetime) -> bool:
        return date.weekday() >= 5
    
    def is_special_day(self, date: datetime) -> Tuple[bool, str]:
        if self.is_holiday(date):
            return True, 'holiday'
        if self.is_weekend(date):
            return True, 'weekend'
        return False, 'normal'
    
    def mark_holidays_in_dataframe(self, df: pd.DataFrame, 
                                   timestamp_col: str = 'timestamp') -> pd.DataFrame:
        df = df.copy()
        
        df['is_holiday'] = df[timestamp_col].apply(self.is_holiday)
        df['is_weekend'] = df[timestamp_col].apply(self.is_weekend)
        df['day_type'] = df[timestamp_col].apply(
            lambda x: 'holiday' if self.is_holiday(x) 
            else ('weekend' if self.is_weekend(x) else 'workday')
        )
        
        return df
    
    def remove_holiday_effect(self, df: pd.DataFrame, metrics: List[str],
                               timestamp_col: str = 'timestamp') -> pd.DataFrame:
        df = self.mark_holidays_in_dataframe(df, timestamp_col)
        df_normalized = df.copy()
        
        workday_mask = df['day_type'] == 'workday'
        
        for metric in metrics:
            workday_mean = df.loc[workday_mask, metric].mean()
            workday_std = df.loc[workday_mask, metric].std()
            
            for day_type in ['holiday', 'weekend']:
                mask = df['day_type'] == day_type
                if mask.sum() > 0:
                    day_mean = df.loc[mask, metric].mean()
                    day_std = df.loc[mask, metric].std()
                    
                    if day_std > 0:
                        normalized_values = (
                            (df.loc[mask, metric] - day_mean) / day_std * workday_std 
                            + workday_mean
                        )
                        df_normalized.loc[mask, metric] = normalized_values
        
        return df_normalized
    
    def get_holiday_adjustment_factor(self, df: pd.DataFrame, metric: str,
                                       timestamp_col: str = 'timestamp') -> Dict[str, float]:
        df = self.mark_holidays_in_dataframe(df, timestamp_col)
        
        factors = {}
        workday_mean = df.loc[df['day_type'] == 'workday', metric].mean()
        
        for day_type in ['workday', 'weekend', 'holiday']:
            mask = df['day_type'] == day_type
            if mask.sum() > 0:
                day_mean = df.loc[mask, metric].mean()
                factors[day_type] = day_mean / workday_mean if workday_mean > 0 else 1.0
        
        return factors
    
    def filter_holiday_anomalies(self, anomalies: List[Dict], 
                                  df: pd.DataFrame) -> List[Dict]:
        filtered_anomalies = []
        holiday_anomalies = []
        
        for anomaly in anomalies:
            ts = anomaly['timestamp']
            is_special, day_type = self.is_special_day(ts)
            
            if is_special:
                adjustment_factor = self._calculate_holiday_adjustment_score(
                    df, anomaly, day_type
                )
                if adjustment_factor > 0.7:
                    holiday_anomalies.append({
                        **anomaly,
                        'is_holiday_effect': True,
                        'day_type': day_type,
                        'adjustment_factor': adjustment_factor
                    })
                else:
                    filtered_anomalies.append({
                        **anomaly,
                        'is_holiday_effect': False,
                        'day_type': day_type
                    })
            else:
                filtered_anomalies.append({
                    **anomaly,
                    'is_holiday_effect': False,
                    'day_type': 'workday'
                })
        
        return filtered_anomalies, holiday_anomalies
    
    def _calculate_holiday_adjustment_score(self, df: pd.DataFrame, 
                                             anomaly: Dict, day_type: str) -> float:
        ts = anomaly['timestamp']
        hour = ts.hour
        
        window_start = ts - timedelta(hours=2)
        window_end = ts + timedelta(hours=2)
        
        same_type_mask = (
            (df['timestamp'].dt.hour >= hour - 1) &
            (df['timestamp'].dt.hour <= hour + 1) &
            (df['timestamp'].apply(lambda x: self.is_special_day(x)[0]))
        )
        
        if same_type_mask.sum() < 5:
            return 0.0
        
        metrics = list(anomaly['metrics'].keys())
        total_score = 0.0
        
        for metric in metrics:
            same_type_values = df.loc[same_type_mask, metric]
            if len(same_type_values) > 0:
                same_type_mean = same_type_values.mean()
                workday_mask = df['timestamp'].apply(lambda x: not self.is_special_day(x)[0])
                workday_values = df.loc[workday_mask & (df['timestamp'].dt.hour == hour), metric]
                
                if len(workday_values) > 0:
                    workday_mean = workday_values.mean()
                    ratio = same_type_mean / workday_mean if workday_mean > 0 else 1.0
                    
                    if abs(1 - ratio) > 0.2:
                        total_score += 0.5
        
        return min(1.0, total_score / len(metrics) if metrics else 0)
    
    def get_holiday_list(self, year: int = None) -> List[str]:
        if year:
            return sorted([
                h.strftime('%Y-%m-%d') 
                for h in self.holidays 
                if h.year == year
            ])
        return sorted([h.strftime('%Y-%m-%d') for h in self.holidays])
