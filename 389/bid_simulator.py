import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


class DynamicBidSimulator:
    def __init__(self, total_budget: float, time_horizon: int = 30, learning_rate: float = 0.1,
                 roi_threshold: float = 1.0, min_bid: float = 0.01, max_bid: float = 1000.0):
        self.total_budget = total_budget
        self.time_horizon = time_horizon
        self.learning_rate = learning_rate
        self.roi_threshold = roi_threshold
        self.min_bid = min_bid
        self.max_bid = max_bid
        self.daily_budget = total_budget / time_horizon
        self.bid_history = []
        self.spending_history = []

    def calculate_ctr_prediction(self, features: pd.DataFrame, model: Optional[object] = None) -> pd.Series:
        if model is not None and hasattr(model, 'predict'):
            predictions = model.predict(features)
            return pd.Series(np.clip(predictions, 0, 1), index=features.index)
        
        feature_cols = [c for c in features.columns if c in ['ad_quality_score', 'position_rank', 'user_engagement_score', 'category_match_score']]
        if len(feature_cols) == 0:
            base_ctr = 0.02
            return pd.Series(base_ctr, index=features.index)
        
        weights = {
            'ad_quality_score': 0.3,
            'position_rank': -0.4,
            'user_engagement_score': 0.2,
            'category_match_score': 0.1
        }
        
        ctr_pred = pd.Series(0.02, index=features.index)
        for col, weight in weights.items():
            if col in features.columns:
                if col == 'position_rank':
                    normalized = 1.0 / (features[col] + 1)
                else:
                    normalized = (features[col] - features[col].min()) / (features[col].max() - features[col].min() + 1e-10)
                ctr_pred += weight * normalized * 0.05
        
        return np.clip(ctr_pred, 0.001, 0.5)

    def calculate_expected_value(self, ctr_pred: pd.Series, conversion_value_pred: pd.Series) -> pd.Series:
        return ctr_pred * conversion_value_pred

    def optimize_bid_strategy(self, value_results: pd.DataFrame, ad_summary: pd.DataFrame,
                              total_budget: Optional[float] = None) -> pd.DataFrame:
        budget = total_budget if total_budget is not None else self.total_budget
        
        merged = value_results.merge(ad_summary[['ad_id', 'base_bid', 'ad_quality_score', 'value_roi']],
                                     on='ad_id', how='left')
        
        merged['incremental_roi'] = np.where(
            merged['base_bid'] > 0,
            merged['incremental_value'] / merged['base_bid'],
            0
        )
        
        median_roi = merged['incremental_roi'].median()
        median_value = merged['incremental_value'].median()
        
        def calc_optimal_bid(row):
            roi_factor = row['incremental_roi'] / max(median_roi, 0.001)
            value_factor = row['incremental_value'] / max(median_value, 0.001)
            quality_factor = row['ad_quality_score'] / 5.0
            
            bid_multiplier = 0.5 + 0.4 * roi_factor + 0.3 * value_factor + 0.2 * quality_factor
            optimal_bid = row['base_bid'] * bid_multiplier
            
            expected_roi = row['incremental_value'] / max(optimal_bid, 0.001)
            if expected_roi < self.roi_threshold:
                optimal_bid = row['incremental_value'] / max(self.roi_threshold, 0.001)
            
            return np.clip(optimal_bid, self.min_bid, self.max_bid)
        
        merged['optimal_bid'] = merged.apply(calc_optimal_bid, axis=1)
        merged['bid_roi'] = merged['incremental_value'] / merged['optimal_bid']
        merged['bid_approved'] = merged['bid_roi'] >= self.roi_threshold
        
        result = merged[['impression_id', 'ad_id', 'user_id', 'incremental_value', 'base_bid',
                         'optimal_bid', 'bid_roi', 'bid_approved', 'ad_quality_score']].copy()
        
        return result

    def simulate_bidding_with_budget(self, ad_summary: pd.DataFrame, position_metrics: pd.DataFrame,
                                     total_budget: Optional[float] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        budget = total_budget if total_budget is not None else self.total_budget
        daily_budget = budget / self.time_horizon
        
        ad_position_pairs = []
        for _, ad_row in ad_summary.iterrows():
            for _, pos_row in position_metrics.iterrows():
                ad_position_pairs.append({
                    'ad_id': ad_row['ad_id'],
                    'position_id': pos_row['position_id'],
                    'position_name': pos_row['position_name'],
                    'base_bid': ad_row['base_bid'],
                    'ad_quality_score': ad_row['ad_quality_score'],
                    'position_ctr': pos_row['ctr'],
                    'position_value': pos_row['mean_incremental_value'],
                    'position_rank': pos_row['position_id']
                })
        
        ap_df = pd.DataFrame(ad_position_pairs)
        
        position_adj = {1: 1.5, 2: 1.3, 3: 1.15, 4: 1.0, 5: 0.85}
        ap_df['position_adjustment'] = ap_df['position_rank'].map(lambda x: position_adj.get(x, 1.0))
        
        ap_df['base_position_bid'] = ap_df['base_bid'] * ap_df['position_adjustment']
        ap_df['expected_value'] = ap_df['position_ctr'] * ap_df['position_value']
        ap_df['expected_roi'] = np.where(
            ap_df['base_position_bid'] > 0,
            ap_df['expected_value'] / ap_df['base_position_bid'],
            0
        )
        
        ap_df = ap_df.sort_values('expected_roi', ascending=False)
        
        total_roi_above = ap_df[ap_df['expected_roi'] >= self.roi_threshold]['expected_roi'].sum()
        if total_roi_above > 0:
            ap_df['budget_weight'] = np.where(
                ap_df['expected_roi'] >= self.roi_threshold,
                ap_df['expected_roi'] / total_roi_above,
                0
            )
        else:
            ap_df['budget_weight'] = 1.0 / len(ap_df)
        
        ap_df['allocated_budget'] = budget * ap_df['budget_weight']
        ap_df['daily_spend_target'] = ap_df['allocated_budget'] / self.time_horizon
        
        time_steps = []
        remaining_budget = budget
        current_day = 1
        
        while current_day <= self.time_horizon and remaining_budget > 0:
            day_spend = 0
            for _, row in ap_df.iterrows():
                if remaining_budget <= 0:
                    break
                
                target_spend = min(row['daily_spend_target'], remaining_budget)
                pacing_factor = 1.0 + (np.random.random() - 0.5) * 0.2
                actual_spend = target_spend * pacing_factor
                actual_spend = min(actual_spend, remaining_budget)
                
                impressions = int(actual_spend / max(row['base_position_bid'], 0.001))
                expected_clicks = impressions * row['position_ctr']
                expected_val = expected_clicks * row['position_value']
                
                time_steps.append({
                    'day': current_day,
                    'ad_id': row['ad_id'],
                    'position_id': row['position_id'],
                    'daily_budget': daily_budget,
                    'target_spend': target_spend,
                    'actual_spend': actual_spend,
                    'impressions': impressions,
                    'expected_clicks': expected_clicks,
                    'expected_value': expected_val,
                    'cumulative_spend': budget - remaining_budget + actual_spend
                })
                
                day_spend += actual_spend
                remaining_budget -= actual_spend
            
            self.spending_history.append({
                'day': current_day,
                'total_spend': day_spend,
                'remaining_budget': remaining_budget
            })
            current_day += 1
        
        simulation_df = pd.DataFrame(time_steps)
        allocation_df = ap_df[['ad_id', 'position_id', 'position_name', 'base_position_bid',
                               'expected_value', 'expected_roi', 'budget_weight', 'allocated_budget',
                               'daily_spend_target']].copy()
        allocation_df = allocation_df.sort_values(['ad_id', 'position_id'])
        
        return allocation_df, simulation_df

    def generate_bid_recommendations(self, ad_value_summary: pd.DataFrame, position_metrics: pd.DataFrame,
                                     total_budget: Optional[float] = None) -> pd.DataFrame:
        budget = total_budget if total_budget is not None else self.total_budget
        
        allocation_df, _ = self.simulate_bidding_with_budget(ad_value_summary, position_metrics, budget)
        
        recommendations = allocation_df.merge(
            ad_value_summary[['ad_id', 'base_bid', 'value_roi', 'mean_incremental_value', 'ad_quality_score']],
            on='ad_id', how='left'
        )
        
        position_adj = {1: 1.5, 2: 1.3, 3: 1.15, 4: 1.0, 5: 0.85}
        recommendations['position_adjustment'] = recommendations['position_id'].map(lambda x: position_adj.get(x, 1.0))
        
        median_roi = ad_value_summary['value_roi'].median()
        median_value = ad_value_summary['mean_incremental_value'].median()
        
        def calc_rec_bid(row):
            roi_factor = row['value_roi'] / max(median_roi, 0.001)
            value_factor = row['mean_incremental_value'] / max(median_value, 0.001)
            position_factor = row['position_adjustment']
            
            bid = row['base_bid'] * (0.7 + 0.3 * roi_factor + 0.2 * value_factor) * position_factor
            
            expected_roi = row['expected_value'] / max(bid, 0.001)
            if expected_roi < self.roi_threshold:
                bid = max(self.min_bid, row['expected_value'] / self.roi_threshold)
            
            return np.clip(bid, self.min_bid, self.max_bid)
        
        recommendations['recommended_bid'] = recommendations.apply(calc_rec_bid, axis=1)
        recommendations['bid_change_pct'] = ((recommendations['recommended_bid'] - recommendations['base_bid']) / 
                                             recommendations['base_bid'] * 100).round(2)
        recommendations['expected_roi'] = recommendations['expected_value'] / recommendations['recommended_bid']
        recommendations['meets_roi_threshold'] = recommendations['expected_roi'] >= self.roi_threshold
        
        def get_action(row):
            if not row['meets_roi_threshold']:
                return 'pause'
            elif row['bid_change_pct'] > 20:
                return 'increase_significantly'
            elif row['bid_change_pct'] > 5:
                return 'increase_moderately'
            elif row['bid_change_pct'] < -20:
                return 'decrease_significantly'
            elif row['bid_change_pct'] < -5:
                return 'decrease_moderately'
            else:
                return 'maintain'
        
        recommendations['action'] = recommendations.apply(get_action, axis=1)
        recommendations['priority_score'] = (
            0.5 * recommendations['expected_roi'].rank(pct=True) +
            0.3 * recommendations['mean_incremental_value'].rank(pct=True) +
            0.2 * (1 / recommendations['position_id']).rank(pct=True)
        ).round(4)
        
        recommendations = recommendations.sort_values('priority_score', ascending=False)
        
        result = recommendations[['ad_id', 'position_id', 'position_name', 'base_bid', 'recommended_bid',
                                   'bid_change_pct', 'expected_roi', 'meets_roi_threshold', 'action',
                                   'allocated_budget', 'priority_score']].copy()
        
        return result
        ).round(4)
        
        recommendations = recommendations.sort_values('priority_score', ascending=False)
        
        result = recommendations[['ad_id', 'position_id', 'position_name', 'base_bid', 'recommended_bid',
                                   'bid_change_pct', 'expected_roi', 'meets_roi_threshold', 'action',
                                   'allocated_budget', 'priority_score']].copy()
        
        return result
