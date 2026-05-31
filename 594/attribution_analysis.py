import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class ROICalculator:
    def __init__(self):
        pass
    
    def calculate_basic_roi(self, campaign_df: pd.DataFrame) -> pd.DataFrame:
        df = campaign_df.copy()
        
        df['roi'] = ((df['revenue'] - df['actual_cost']) / df['actual_cost'] * 100).round(2)
        df['profit'] = df['revenue'] - df['actual_cost']
        df['cpa'] = (df['actual_cost'] / df['conversions'].replace(0, 1)).round(2)
        df['cpc'] = (df['actual_cost'] / df['clicks'].replace(0, 1)).round(2)
        df['cpm'] = (df['actual_cost'] / df['impressions'].replace(0, 1) * 1000).round(2)
        df['conversion_rate'] = (df['conversions'] / df['clicks'].replace(0, 1) * 100).round(2)
        df['ctr'] = (df['clicks'] / df['impressions'].replace(0, 1) * 100).round(2)
        df['roas'] = (df['revenue'] / df['actual_cost'].replace(0, 1)).round(2)
        
        return df
    
    def calculate_influencer_roi(self, campaign_df: pd.DataFrame) -> pd.DataFrame:
        df = self.calculate_basic_roi(campaign_df)
        
        influencer_roi = df.groupby(['influencer_id', 'influencer_name']).agg({
            'campaign_id': 'count',
            'actual_cost': 'sum',
            'revenue': 'sum',
            'profit': 'sum',
            'conversions': 'sum',
            'clicks': 'sum',
            'impressions': 'sum',
            'roi': 'mean'
        }).rename(columns={'campaign_id': 'campaign_count'})
        
        influencer_roi['avg_roi'] = influencer_roi['roi'].round(2)
        influencer_roi['overall_roi'] = ((influencer_roi['revenue'] - influencer_roi['actual_cost']) / 
                                        influencer_roi['actual_cost'] * 100).round(2)
        influencer_roi['roas'] = (influencer_roi['revenue'] / influencer_roi['actual_cost']).round(2)
        
        return influencer_roi.reset_index()
    
    def get_roi_benchmarks(self, campaign_df: pd.DataFrame, platform: str = None,
                           category: str = None) -> Dict:
        df = self.calculate_basic_roi(campaign_df)
        
        if platform:
            df = df[df['platform'] == platform]
        if category:
            df = df[df['category'] == category]
        
        if len(df) == 0:
            return {'error': 'No data for the specified filters'}
        
        return {
            'avg_roi': df['roi'].mean(),
            'median_roi': df['roi'].median(),
            'roi_std': df['roi'].std(),
            'positive_roi_ratio': (df['roi'] > 0).mean() * 100,
            'avg_roas': df['roas'].mean(),
            'avg_cpa': df['cpa'].mean(),
            'avg_conversion_rate': df['conversion_rate'].mean(),
            'top_25_roi_threshold': df['roi'].quantile(0.75),
            'bottom_25_roi_threshold': df['roi'].quantile(0.25),
            'sample_size': len(df)
        }


class AttributionModel:
    def __init__(self):
        self.models = ['first_touch', 'last_touch', 'linear', 'time_decay', 'u_shaped']
    
    def first_touch_attribution(self, touchpoints: List[Dict]) -> Dict:
        if not touchpoints:
            return {}
        
        sorted_touchpoints = sorted(touchpoints, key=lambda x: x['timestamp'])
        first_touch = sorted_touchpoints[0]
        
        attribution = defaultdict(float)
        attribution[first_touch['influencer_id']] = 1.0
        
        return dict(attribution)
    
    def last_touch_attribution(self, touchpoints: List[Dict]) -> Dict:
        if not touchpoints:
            return {}
        
        sorted_touchpoints = sorted(touchpoints, key=lambda x: x['timestamp'])
        last_touch = sorted_touchpoints[-1]
        
        attribution = defaultdict(float)
        attribution[last_touch['influencer_id']] = 1.0
        
        return dict(attribution)
    
    def linear_attribution(self, touchpoints: List[Dict]) -> Dict:
        if not touchpoints:
            return {}
        
        attribution = defaultdict(float)
        weight = 1.0 / len(touchpoints)
        
        for touchpoint in touchpoints:
            attribution[touchpoint['influencer_id']] += weight
        
        return dict(attribution)
    
    def time_decay_attribution(self, touchpoints: List[Dict], 
                                decay_factor: float = 0.5) -> Dict:
        if not touchpoints:
            return {}
        
        sorted_touchpoints = sorted(touchpoints, key=lambda x: x['timestamp'])
        n = len(sorted_touchpoints)
        
        attribution = defaultdict(float)
        total_weight = 0
        
        for i, touchpoint in enumerate(sorted_touchpoints):
            weight = decay_factor ** (n - i - 1)
            attribution[touchpoint['influencer_id']] += weight
            total_weight += weight
        
        for influencer_id in attribution:
            attribution[influencer_id] /= total_weight
        
        return dict(attribution)
    
    def u_shaped_attribution(self, touchpoints: List[Dict]) -> Dict:
        if not touchpoints:
            return {}
        if len(touchpoints) == 1:
            return {touchpoints[0]['influencer_id']: 1.0}
        
        sorted_touchpoints = sorted(touchpoints, key=lambda x: x['timestamp'])
        n = len(sorted_touchpoints)
        
        attribution = defaultdict(float)
        
        if n == 2:
            attribution[sorted_touchpoints[0]['influencer_id']] = 0.5
            attribution[sorted_touchpoints[1]['influencer_id']] = 0.5
        else:
            attribution[sorted_touchpoints[0]['influencer_id']] = 0.3
            attribution[sorted_touchpoints[-1]['influencer_id']] = 0.3
            
            middle_weight = 0.4 / (n - 2)
            for i in range(1, n - 1):
                attribution[sorted_touchpoints[i]['influencer_id']] += middle_weight
        
        return dict(attribution)
    
    def multi_touch_attribution(self, touchpoints: List[Dict], 
                                 model: str = 'linear') -> Dict:
        if model == 'first_touch':
            return self.first_touch_attribution(touchpoints)
        elif model == 'last_touch':
            return self.last_touch_attribution(touchpoints)
        elif model == 'linear':
            return self.linear_attribution(touchpoints)
        elif model == 'time_decay':
            return self.time_decay_attribution(touchpoints)
        elif model == 'u_shaped':
            return self.u_shaped_attribution(touchpoints)
        else:
            raise ValueError(f"Unknown attribution model: {model}")
    
    def compare_attribution_models(self, touchpoints: List[Dict]) -> pd.DataFrame:
        results = []
        
        for model in self.models:
            attribution = self.multi_touch_attribution(touchpoints, model)
            for influencer_id, weight in attribution.items():
                results.append({
                    'model': model,
                    'influencer_id': influencer_id,
                    'attribution_weight': weight
                })
        
        return pd.DataFrame(results)


class ConversionAnalyzer:
    def __init__(self):
        self.roi_calculator = ROICalculator()
    
    def analyze_conversion_funnel(self, campaign_df: pd.DataFrame) -> Dict:
        df = self.roi_calculator.calculate_basic_roi(campaign_df)
        
        total_impressions = df['impressions'].sum()
        total_clicks = df['clicks'].sum()
        total_conversions = df['conversions'].sum()
        
        funnel = {
            'impressions': total_impressions,
            'clicks': total_clicks,
            'conversions': total_conversions,
            'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
            'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
            'click_to_conversion': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
            'impression_to_conversion': (total_conversions / total_impressions * 100) if total_impressions > 0 else 0
        }
        
        return funnel
    
    def cohort_analysis(self, campaign_df: pd.DataFrame, period: str = 'month') -> pd.DataFrame:
        df = self.roi_calculator.calculate_basic_roi(campaign_df)
        df['start_date'] = pd.to_datetime(df['start_date'])
        
        if period == 'month':
            df['cohort'] = df['start_date'].dt.to_period('M')
        elif period == 'quarter':
            df['cohort'] = df['start_date'].dt.to_period('Q')
        else:
            df['cohort'] = df['start_date'].dt.to_period('W')
        
        cohort_metrics = df.groupby('cohort').agg({
            'campaign_id': 'count',
            'actual_cost': 'sum',
            'revenue': 'sum',
            'conversions': 'sum',
            'roi': 'mean'
        }).rename(columns={'campaign_id': 'campaign_count'})
        
        cohort_metrics['avg_revenue_per_campaign'] = cohort_metrics['revenue'] / cohort_metrics['campaign_count']
        cohort_metrics['avg_roi'] = cohort_metrics['roi'].round(2)
        
        return cohort_metrics.reset_index()
    
    def predict_conversion(self, influencer_metrics: Dict, historical_data: pd.DataFrame) -> Dict:
        avg_conversion_rate = historical_data['conversion_rate'].mean()
        avg_clicks_per_campaign = historical_data['clicks'].mean()
        
        engagement_factor = influencer_metrics.get('engagement_rate', 5) / 5
        follower_factor = min(influencer_metrics.get('followers', 10000) / 100000, 2)
        
        predicted_clicks = avg_clicks_per_campaign * engagement_factor * follower_factor
        predicted_conversions = predicted_clicks * avg_conversion_rate / 100
        
        return {
            'predicted_clicks': int(predicted_clicks),
            'predicted_conversions': int(predicted_conversions),
            'predicted_conversion_rate': avg_conversion_rate,
            'confidence': 'medium'
        }
    
    def calculate_ltv(self, customer_data: Dict) -> float:
        avg_purchase_value = customer_data.get('avg_purchase_value', 100)
        purchase_frequency = customer_data.get('purchase_frequency', 2)
        customer_lifespan = customer_data.get('customer_lifespan', 12)
        profit_margin = customer_data.get('profit_margin', 0.3)
        
        ltv = avg_purchase_value * purchase_frequency * customer_lifespan * profit_margin
        return round(ltv, 2)
