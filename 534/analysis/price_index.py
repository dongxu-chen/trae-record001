import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class PriceIndexAnalyzer:
    def __init__(self, our_price, competitor_prices_df):
        self.our_price = our_price
        self.df = competitor_prices_df.copy()

    def compute_price_index(self):
        if self.df.empty:
            return {}
        avg_price = self.df['current_price'].mean()
        min_price = self.df['current_price'].min()
        max_price = self.df['current_price'].max()
        median_price = self.df['current_price'].median()
        price_index = (self.our_price / avg_price) * 100
        relative_to_min = ((self.our_price - min_price) / min_price) * 100
        relative_to_max = ((max_price - self.our_price) / max_price) * 100
        rank = (self.df['current_price'] < self.our_price).sum() + 1
        total = len(self.df) + 1
        percentile = round((1 - rank / total) * 100, 1)

        return {
            'our_price': self.our_price,
            'avg_price': round(avg_price, 2),
            'min_price': round(min_price, 2),
            'max_price': round(max_price, 2),
            'median_price': round(median_price, 2),
            'price_index': round(price_index, 2),
            'relative_to_avg_pct': round((self.our_price / avg_price - 1) * 100, 2),
            'relative_to_min_pct': round(relative_to_min, 2),
            'relative_to_max_pct': round(relative_to_max, 2),
            'price_rank': rank,
            'total_competitors': total,
            'price_percentile': percentile,
            'competitiveness': self._assess_competitiveness(price_index),
        }

    def _assess_competitiveness(self, price_index):
        if price_index <= 90:
            return {'level': '极强', 'color': 'green', 'desc': '价格远低于市场均价，竞争力极强'}
        elif price_index <= 95:
            return {'level': '强', 'color': 'limegreen', 'desc': '价格低于市场均价，竞争力强'}
        elif price_index <= 102:
            return {'level': '中等', 'color': 'orange', 'desc': '价格接近市场均价，竞争力中等'}
        elif price_index <= 110:
            return {'level': '弱', 'color': 'orangered', 'desc': '价格高于市场均价，竞争力偏弱'}
        else:
            return {'level': '极弱', 'color': 'red', 'desc': '价格远高于市场均价，竞争力极弱'}

    def compute_platform_index(self):
        if self.df.empty or 'platform' not in self.df.columns:
            return pd.DataFrame()
        platform_stats = self.df.groupby('platform').agg(
            avg_price=('current_price', 'mean'),
            min_price=('current_price', 'min'),
            max_price=('current_price', 'max'),
            count=('current_price', 'count'),
        ).round(2)
        platform_stats['our_price'] = self.our_price
        platform_stats['price_index'] = ((self.our_price / platform_stats['avg_price']) * 100).round(2)
        platform_stats['price_diff_pct'] = (((self.our_price - platform_stats['min_price']) / platform_stats['min_price']) * 100).round(2)
        return platform_stats.reset_index()

    def generate_pricing_suggestion(self, target_index=100):
        if self.df.empty:
            return {}
        current = self.compute_price_index()
        avg = current['avg_price']
        suggested_price = round(avg * target_index / 100, 2)
        price_diff = round(suggested_price - self.our_price, 2)
        margin_pct = round((price_diff / self.our_price) * 100, 2)

        if price_diff < 0:
            action = '降价'
            reason = f'当前价格高于目标价格指数{target_index}对应的价位，建议降价以提升竞争力'
        elif price_diff > 0:
            action = '可涨价'
            reason = f'当前价格低于目标价格指数{target_index}对应的价位，存在涨价空间'
        else:
            action = '维持'
            reason = '当前价格与目标价格指数一致，建议维持'

        return {
            'current_price': self.our_price,
            'suggested_price': suggested_price,
            'price_diff': price_diff,
            'margin_pct': margin_pct,
            'action': action,
            'reason': reason,
            'target_index': target_index,
            'current_index': current['price_index'],
        }
