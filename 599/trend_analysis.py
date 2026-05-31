import json
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import defaultdict

@dataclass
class TrendPeriod:
    current_period: str
    current_total: float
    previous_period: str
    previous_total: float
    change_amount: float
    change_percent: float
    is_increase: bool
    trend: str

@dataclass
class CategoryTrend:
    category: str
    current_amount: float
    previous_amount: float
    change_amount: float
    change_percent: float
    is_increase: bool
    trend: str
    contribution: float

@dataclass
class ForecastPoint:
    date: str
    forecast: float
    lower: float
    upper: float

class TrendAnalyzer:
    def __init__(self):
        pass
    
    def _prepare_dataframe(self, transactions: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(transactions)
        if df.empty:
            return df
        
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['week'] = df['date'].dt.isocalendar().week
        df['year_month'] = df['date'].dt.to_period('M')
        df['year_quarter'] = df['date'].dt.to_period('Q')
        
        return df
    
    def compare_month_over_month(
        self,
        transactions: List[Dict],
        compare_type: str = "previous_month"
    ) -> TrendPeriod:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return TrendPeriod(
                current_period="", current_total=0.0,
                previous_period="", previous_total=0.0,
                change_amount=0.0, change_percent=0.0,
                is_increase=False, trend="持平"
            )
        
        now = datetime.now()
        
        if compare_type == "previous_month":
            current_start = now.replace(day=1)
            current_end = (now.replace(month=now.month % 12 + 1, day=1) - timedelta(days=1))
            current_data = df[(df['date'] >= current_start) & (df['date'] <= now)]
            
            prev_month_end = current_start - timedelta(days=1)
            prev_month_start = prev_month_end.replace(day=1)
            prev_data = df[(df['date'] >= prev_month_start) & (df['date'] <= prev_month_end)]
            
            current_period = f"{now.year}年{now.month}月（至今）"
            previous_period = f"{prev_month_start.year}年{prev_month_start.month}月"
        
        elif compare_type == "same_month_last_year":
            current_start = now.replace(day=1)
            current_data = df[df['date'] >= current_start]
            
            prev_year = now.year - 1
            prev_start = datetime(prev_year, now.month, 1)
            if now.month == 12:
                prev_end = datetime(prev_year, now.month, 31)
            else:
                prev_end = datetime(prev_year, now.month + 1, 1) - timedelta(days=1)
            prev_data = df[(df['date'] >= prev_start) & (df['date'] <= prev_end)]
            
            current_period = f"{now.year}年{now.month}月（至今）"
            previous_period = f"{prev_year}年{now.month}月"
        
        else:
            return self.compare_month_over_month(transactions, "previous_month")
        
        current_total = current_data['amount'].sum()
        previous_total = prev_data['amount'].sum()
        
        change_amount = current_total - previous_total
        change_percent = (change_amount / previous_total * 100) if previous_total > 0 else 0
        is_increase = change_amount > 0
        
        if abs(change_percent) < 1:
            trend = "持平"
        elif change_percent > 20:
            trend = "大幅上涨"
        elif change_percent > 5:
            trend = "上涨"
        elif change_percent < -20:
            trend = "大幅下降"
        elif change_percent < -5:
            trend = "下降"
        else:
            trend = "小幅波动"
        
        return TrendPeriod(
            current_period=current_period,
            current_total=round(current_total, 2),
            previous_period=previous_period,
            previous_total=round(previous_total, 2),
            change_amount=round(change_amount, 2),
            change_percent=round(change_percent, 2),
            is_increase=is_increase,
            trend=trend
        )
    
    def get_category_trend(
        self,
        transactions: List[Dict],
        compare_type: str = "previous_month"
    ) -> List[CategoryTrend]:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return []
        
        now = datetime.now()
        
        if compare_type == "previous_month":
            current_start = now.replace(day=1)
            prev_month_end = current_start - timedelta(days=1)
            prev_month_start = prev_month_end.replace(day=1)
        else:
            current_start = now.replace(day=1)
            prev_month_start = datetime(now.year - 1, now.month, 1)
            if now.month == 12:
                prev_month_end = datetime(now.year - 1, now.month, 31)
            else:
                prev_month_end = datetime(now.year - 1, now.month + 1, 1) - timedelta(days=1)
        
        current_data = df[df['date'] >= current_start]
        prev_data = df[(df['date'] >= prev_month_start) & (df['date'] <= (prev_month_end if compare_type != "previous_month" else current_start - timedelta(days=1)))]
        
        current_by_cat = current_data.groupby('category')['amount'].sum().to_dict()
        prev_by_cat = prev_data.groupby('category')['amount'].sum().to_dict()
        
        all_categories = set(current_by_cat.keys()) | set(prev_by_cat.keys())
        total_current = sum(current_by_cat.values())
        
        trends = []
        for category in all_categories:
            current = current_by_cat.get(category, 0.0)
            previous = prev_by_cat.get(category, 0.0)
            
            change = current - previous
            change_pct = (change / previous * 100) if previous > 0 else float('inf')
            
            if abs(change_pct) < 1:
                trend = "持平"
            elif change_pct > 30:
                trend = "大幅上涨"
            elif change_pct > 10:
                trend = "上涨"
            elif change_pct < -30:
                trend = "大幅下降"
            elif change_pct < -10:
                trend = "下降"
            else:
                trend = "小幅波动"
            
            contribution = (current / total_current * 100) if total_current > 0 else 0
            
            trends.append(CategoryTrend(
                category=category,
                current_amount=round(current, 2),
                previous_amount=round(previous, 2),
                change_amount=round(change, 2),
                change_percent=round(change_pct, 2) if change_pct != float('inf') else 999.99,
                is_increase=change > 0,
                trend=trend,
                contribution=round(contribution, 2)
            ))
        
        trends.sort(key=lambda x: x.change_percent, reverse=True)
        return trends
    
    def get_monthly_trend(
        self,
        transactions: List[Dict],
        months: int = 12
    ) -> pd.DataFrame:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return pd.DataFrame()
        
        end_date = datetime.now().replace(day=1)
        start_date = end_date - timedelta(days=30 * months)
        
        df_filtered = df[(df['date'] >= start_date) & (df['date'] < end_date)]
        
        monthly_spending = df_filtered.groupby('year_month')['amount'].sum().reset_index()
        monthly_spending.columns = ['月份', '总消费']
        
        monthly_by_cat = df_filtered.groupby(['year_month', 'category'])['amount'].sum().unstack(fill_value=0)
        monthly_by_cat = monthly_by_cat.reset_index()
        monthly_by_cat.columns = ['月份'] + [str(col) for col in monthly_by_cat.columns[1:]]
        
        result = pd.merge(monthly_spending, monthly_by_cat, on='月份', how='left')
        result['月份'] = result['月份'].astype(str)
        
        return result
    
    def get_quarterly_trend(
        self,
        transactions: List[Dict],
        quarters: int = 8
    ) -> pd.DataFrame:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return pd.DataFrame()
        
        end_date = datetime.now().replace(day=1)
        start_date = end_date - timedelta(days=90 * quarters)
        
        df_filtered = df[(df['date'] >= start_date) & (df['date'] < end_date)]
        
        quarterly_spending = df_filtered.groupby('year_quarter')['amount'].sum().reset_index()
        quarterly_spending.columns = ['季度', '总消费']
        
        quarterly_by_cat = df_filtered.groupby(['year_quarter', 'category'])['amount'].sum().unstack(fill_value=0)
        quarterly_by_cat = quarterly_by_cat.reset_index()
        quarterly_by_cat.columns = ['季度'] + [str(col) for col in quarterly_by_cat.columns[1:]]
        
        result = pd.merge(quarterly_spending, quarterly_by_cat, on='季度', how='left')
        result['季度'] = result['季度'].astype(str)
        
        return result
    
    def get_weekday_pattern(
        self,
        transactions: List[Dict],
        weeks: int = 12
    ) -> pd.DataFrame:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return pd.DataFrame()
        
        cutoff = datetime.now() - timedelta(weeks=weeks)
        df_filtered = df[df['date'] >= cutoff].copy()
        
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        df_filtered.loc[:, 'weekday'] = df_filtered['date'].dt.weekday
        df_filtered.loc[:, 'weekday_name'] = df_filtered['weekday'].map(dict(enumerate(weekday_names)))
        
        pattern = df_filtered.groupby('weekday_name').agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        pattern.columns = ['星期', '总消费', '平均每笔', '交易次数']
        pattern['排序'] = pattern['星期'].map(dict(zip(weekday_names, range(7))))
        pattern = pattern.sort_values('排序').drop('排序', axis=1)
        
        pattern['总消费'] = pattern['总消费'].round(2)
        pattern['平均每笔'] = pattern['平均每笔'].round(2)
        
        return pattern
    
    def get_hourly_pattern(
        self,
        transactions: List[Dict],
        weeks: int = 4
    ) -> pd.DataFrame:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return pd.DataFrame()
        
        cutoff = datetime.now() - timedelta(weeks=weeks)
        df_filtered = df[df['date'] >= cutoff].copy()
        
        df_filtered.loc[:, 'hour'] = df_filtered['time'].astype(str).str[:2].astype(int)
        
        pattern = df_filtered.groupby('hour').agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        pattern.columns = ['时段', '总消费', '平均每笔', '交易次数']
        pattern['时段'] = pattern['时段'].apply(lambda x: f"{x:02d}:00-{x:02d}:59")
        
        pattern['总消费'] = pattern['总消费'].round(2)
        pattern['平均每笔'] = pattern['平均每笔'].round(2)
        
        return pattern
    
    def forecast_next_month(
        self,
        transactions: List[Dict],
        method: str = "moving_average"
    ) -> Dict[str, Any]:
        df = self._prepare_dataframe(transactions)
        if df.empty:
            return {}
        
        df_monthly = df.groupby('year_month')['amount'].sum().reset_index()
        df_monthly.columns = ['month', 'amount']
        df_monthly = df_monthly.sort_values('month')
        
        if len(df_monthly) < 2:
            return {
                'forecast': round(df_monthly['amount'].mean() if len(df_monthly) > 0 else 0, 2),
                'lower': 0.0,
                'upper': 0.0,
                'method': method,
                'confidence': 0.5,
                'historical_points': len(df_monthly)
            }
        
        if method == "moving_average":
            window = min(3, len(df_monthly))
            forecast = df_monthly['amount'].tail(window).mean()
            std = df_monthly['amount'].tail(window).std() if window > 1 else forecast * 0.1
        elif method == "weighted_moving_average":
            window = min(3, len(df_monthly))
            weights = list(range(1, window + 1))
            total_weight = sum(weights)
            values = df_monthly['amount'].tail(window).values
            forecast = sum(v * w for v, w in zip(values, weights)) / total_weight
            std = df_monthly['amount'].tail(window).std() if window > 1 else forecast * 0.1
        elif method == "trend":
            x = np.arange(len(df_monthly))
            y = df_monthly['amount'].values
            coeffs = np.polyfit(x, y, 1)
            forecast = coeffs[0] * (len(df_monthly)) + coeffs[1]
            std = df_monthly['amount'].std() * 0.5
        else:
            return self.forecast_next_month(transactions, "moving_average")
        
        lower = max(0, forecast - 1.96 * std)
        upper = forecast + 1.96 * std
        
        confidence = max(0.5, 1 - std / forecast) if forecast > 0 else 0.5
        
        return {
            'forecast': round(forecast, 2),
            'lower': round(lower, 2),
            'upper': round(upper, 2),
            'method': method,
            'confidence': round(confidence, 2),
            'historical_points': len(df_monthly)
        }
    
    def get_top_growing_categories(
        self,
        transactions: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        trends = self.get_category_trend(transactions)
        growing = [t for t in trends if t.is_increase and t.change_percent > 5]
        growing.sort(key=lambda x: x.change_percent, reverse=True)
        
        return [asdict(t) for t in growing[:top_n]]
    
    def get_top_declining_categories(
        self,
        transactions: List[Dict],
        top_n: int = 5
    ) -> List[Dict]:
        trends = self.get_category_trend(transactions)
        declining = [t for t in trends if not t.is_increase and t.change_percent < -5]
        declining.sort(key=lambda x: x.change_percent)
        
        return [asdict(t) for t in declining[:top_n]]
    
    def get_comparison_summary(
        self,
        transactions: List[Dict]
    ) -> Dict[str, Any]:
        mom_prev = self.compare_month_over_month(transactions, "previous_month")
        mom_yoy = self.compare_month_over_month(transactions, "same_month_last_year")
        
        forecast = self.forecast_next_month(transactions)
        
        growing = self.get_top_growing_categories(transactions, top_n=3)
        declining = self.get_top_declining_categories(transactions, top_n=3)
        
        return {
            'mom_comparison': asdict(mom_prev),
            'yoy_comparison': asdict(mom_yoy),
            'forecast': forecast,
            'top_growing': growing,
            'top_declining': declining,
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }
