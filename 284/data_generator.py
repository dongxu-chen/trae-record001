import pandas as pd
import numpy as np
from typing import Tuple, Dict

class PromotionDataGenerator:
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.categories = ['电子产品', '服装', '食品', '家居', '美妆']
        self.channels = ['线上商城', '社交媒体', '线下门店', '邮件营销', '直播带货']
        self.price_tiers = ['低价位', '中价位', '高价位']
        self.customer_segments = ['新用户', '活跃用户', '忠诚用户', '流失风险用户']
    
    def generate_synthetic_data(
        self,
        n_products: int = 200,
        n_periods: int = 8
    ) -> pd.DataFrame:
        data = []
        
        for product_id in range(n_products):
            category = np.random.choice(self.categories)
            channel = np.random.choice(self.channels)
            price_tier = np.random.choice(self.price_tiers)
            customer_segment = np.random.choice(self.customer_segments)
            
            base_sales = np.random.uniform(1000, 10000)
            trend = np.random.uniform(0.005, 0.02)
            
            sales_volatility = np.random.uniform(0.05, 0.2)
            historical_growth_rate = np.random.uniform(-0.05, 0.1)
            avg_order_value = np.random.uniform(50, 500)
            review_score = np.random.uniform(3, 5)
            return_rate = np.random.uniform(0.01, 0.15)
            
            customer_age = np.random.randint(18, 65)
            customer_tenure = np.random.randint(1, 36)
            purchase_frequency = np.random.randint(1, 12)
            customer_ltv = np.random.uniform(1000, 10000)
            
            category_effect = {
                '电子产品': 1.2, '服装': 1.0, '食品': 0.8, 
                '家居': 0.9, '美妆': 1.1
            }[category]
            channel_effect = {
                '线上商城': 1.15, '社交媒体': 1.1, '线下门店': 0.95,
                '邮件营销': 0.9, '直播带货': 1.25
            }[channel]
            price_effect = {
                '低价位': 0.9, '中价位': 1.0, '高价位': 1.15
            }[price_tier]
            segment_effect = {
                '新用户': 0.85, '活跃用户': 1.0, 
                '忠诚用户': 1.2, '流失风险用户': 0.75
            }[customer_segment]
            
            is_treated = np.random.binomial(1, 0.5)
            treatment_period = np.random.randint(3, 6) if is_treated else n_periods + 1
            
            if is_treated:
                discount = np.random.uniform(0.1, 0.4)
                duration = np.random.randint(1, 4)
            else:
                discount = 0
                duration = 0
            
            for period in range(n_periods):
                time_factor = 1 + trend * period
                seasonality = 1 + 0.1 * np.sin(2 * np.pi * period / 4)
                
                is_treatment_period = (
                    is_treated and 
                    period >= treatment_period and 
                    period < treatment_period + duration
                )
                
                if is_treatment_period:
                    treatment_effect = 1 + (discount * 0.8 + 0.05 * duration) * category_effect * channel_effect * price_effect * segment_effect
                else:
                    treatment_effect = 1.0
                
                sales = (
                    base_sales * 
                    time_factor * 
                    seasonality * 
                    category_effect * 
                    channel_effect * 
                    price_effect *
                    segment_effect *
                    treatment_effect *
                    np.random.normal(1, sales_volatility)
                )
                
                data.append({
                    'product_id': product_id,
                    'period': period,
                    'category': category,
                    'channel': channel,
                    'price_tier': price_tier,
                    'customer_segment': customer_segment,
                    'base_sales': base_sales,
                    'sales_volatility': sales_volatility,
                    'historical_growth_rate': historical_growth_rate,
                    'avg_order_value': avg_order_value,
                    'review_score': review_score,
                    'return_rate': return_rate,
                    'customer_age': customer_age,
                    'customer_tenure': customer_tenure,
                    'purchase_frequency': purchase_frequency,
                    'customer_ltv': customer_ltv,
                    'discount': discount if is_treatment_period else 0,
                    'duration': duration if is_treatment_period else 0,
                    'is_treated': is_treated,
                    'is_treatment_period': is_treatment_period,
                    'treatment_period': treatment_period if is_treated else -1,
                    'sales': max(0, sales)
                })
        
        df = pd.DataFrame(data)
        df['sales_lift'] = df.groupby('product_id')['sales'].pct_change() * 100
        df['sales_lift'] = df['sales_lift'].fillna(0)
        
        return df
    
    def prepare_did_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df_did = df.copy()
        df_did['post_treatment'] = (
            df_did['period'] >= df_did['treatment_period']
        ) & (df_did['is_treated'])
        df_did['treated_group'] = df_did['is_treated'].astype(int)
        df_did['did_interaction'] = (
            df_did['treated_group'] * df_did['post_treatment'].astype(int)
        )
        return df_did
    
    def prepare_psm_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df_latest = df.sort_values('period').groupby('product_id').last().reset_index()
        
        df_psm = df_latest.copy()
        df_psm['avg_sales_pre'] = df.groupby('product_id').apply(
            lambda x: x[x['period'] < x['treatment_period'].iloc[0]]['sales'].mean()
        ).values
        
        df_psm['sales_trend_pre'] = df.groupby('product_id').apply(
            lambda x: x[x['period'] < x['treatment_period'].iloc[0]]['sales'].pct_change().mean()
        ).fillna(0).values
        
        df_psm['sales_std_pre'] = df.groupby('product_id').apply(
            lambda x: x[x['period'] < x['treatment_period'].iloc[0]]['sales'].std()
        ).fillna(0).values
        
        df_psm['max_sales_pre'] = df.groupby('product_id').apply(
            lambda x: x[x['period'] < x['treatment_period'].iloc[0]]['sales'].max()
        ).values
        
        df_psm['min_sales_pre'] = df.groupby('product_id').apply(
            lambda x: x[x['period'] < x['treatment_period'].iloc[0]]['sales'].min()
        ).values
        
        category_dummies = pd.get_dummies(df_psm['category'], prefix='cat', drop_first=True)
        channel_dummies = pd.get_dummies(df_psm['channel'], prefix='ch', drop_first=True)
        price_dummies = pd.get_dummies(df_psm['price_tier'], prefix='price', drop_first=True)
        segment_dummies = pd.get_dummies(df_psm['customer_segment'], prefix='seg', drop_first=True)
        
        df_psm = pd.concat(
            [df_psm, category_dummies, channel_dummies, price_dummies, segment_dummies], 
            axis=1
        )
        
        return df_psm
    
    def calculate_actual_lift(self, df: pd.DataFrame) -> Dict:
        treated_df = df[df['is_treated'] == True].copy()
        
        def get_product_lift(group):
            treatment_start = group['treatment_period'].iloc[0]
            duration = group[group['is_treatment_period']]['duration'].iloc[0] if any(group['is_treatment_period']) else 0
            
            pre_sales = group[group['period'] < treatment_start]['sales'].mean()
            during_sales = group[
                (group['period'] >= treatment_start) & 
                (group['period'] < treatment_start + duration)
            ]['sales'].mean()
            
            if pre_sales > 0 and duration > 0:
                return (during_sales - pre_sales) / pre_sales * 100
            return 0
        
        actual_lifts = treated_df.groupby('product_id').apply(get_product_lift)
        
        return {
            'mean_lift': actual_lifts.mean(),
            'median_lift': actual_lifts.median(),
            'std_lift': actual_lifts.std(),
            'min_lift': actual_lifts.min(),
            'max_lift': actual_lifts.max()
        }
