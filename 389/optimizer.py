import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class BudgetOptimizer:
    def __init__(self, total_budget: float = 500000.0, min_bid_ratio: float = 0.3, max_bid_ratio: float = 3.0,
                 frequency_decay_alpha: float = 0.1, max_budget_change_pct: float = 30.0,
                 min_budget_ratio: float = 0.02, max_budget_ratio: float = 0.25):
        self.total_budget = total_budget
        self.min_bid_ratio = min_bid_ratio
        self.max_bid_ratio = max_bid_ratio
        self.frequency_decay_alpha = frequency_decay_alpha
        self.max_budget_change_pct = max_budget_change_pct
        self.min_budget_ratio = min_budget_ratio
        self.max_budget_ratio = max_budget_ratio

    def rank_exposures_by_value(self, value_results: pd.DataFrame,
                                df_ads: pd.DataFrame, df_users: pd.DataFrame) -> pd.DataFrame:
        ranked = value_results.merge(df_ads[['ad_id', 'category', 'base_bid', 'ad_quality_score']],
                                     on='ad_id', how='left')

        user_exposure_counts = value_results.groupby('user_id').size().reset_index(name='user_exposure_count')
        ranked = ranked.merge(user_exposure_counts, on='user_id', how='left')

        max_exposures = ranked['user_exposure_count'].max()
        ranked['frequency_decay_factor'] = np.exp(
            -self.frequency_decay_alpha * (ranked['user_exposure_count'] - 1) / max(1, max_exposures - 1)
        )
        ranked['frequency_decay_factor'] = ranked['frequency_decay_factor'].fillna(1.0)

        ad_exposure_counts = value_results.groupby('ad_id').size().reset_index(name='ad_exposure_count')
        ranked = ranked.merge(ad_exposure_counts, on='ad_id', how='left')

        ranked['ad_diversity_factor'] = 1.0 / np.log1p(ranked['ad_exposure_count'])
        ranked['ad_diversity_factor'] = ranked['ad_diversity_factor'].fillna(1.0)

        ranked['value_per_impression'] = ranked['incremental_value']
        ranked['adjusted_value'] = (
            ranked['value_per_impression'] *
            ranked['frequency_decay_factor'] *
            ranked['ad_diversity_factor']
        )

        ranked['value_rank'] = ranked['value_per_impression'].rank(ascending=False, method='min')
        ranked['adjusted_value_rank'] = ranked['adjusted_value'].rank(ascending=False, method='min')
        ranked = ranked.sort_values('adjusted_value', ascending=False)

        return ranked

    def compute_ad_value_summary(self, value_results: pd.DataFrame,
                                  df_ads: pd.DataFrame) -> pd.DataFrame:
        ad_summary = value_results.groupby('ad_id').agg(
            total_impressions=('impression_id', 'count'),
            total_clicks=('click', 'sum'),
            total_conversion_value=('conversion_value', 'sum'),
            total_incremental_value=('incremental_value', 'sum'),
            mean_incremental_value=('incremental_value', 'mean'),
            std_incremental_value=('incremental_value', 'std'),
            total_marginal_value=('marginal_value', 'sum')
        ).reset_index()

        ad_summary = ad_summary.merge(df_ads[['ad_id', 'category', 'base_bid', 'current_budget', 'ad_quality_score']],
                                       on='ad_id', how='left')

        ad_summary['ctr'] = ad_summary['total_clicks'] / ad_summary['total_impressions']
        ad_summary['value_roi'] = np.where(
            ad_summary['current_budget'] > 0,
            ad_summary['total_incremental_value'] / ad_summary['current_budget'],
            0
        )
        ad_summary['cvr'] = np.where(
            ad_summary['total_clicks'] > 0,
            (value_results.groupby('ad_id')['conversion'].sum() / ad_summary['total_clicks']).values
            if 'conversion' in value_results.columns else 0,
            0
        )

        ad_summary = ad_summary.sort_values('mean_incremental_value', ascending=False)
        return ad_summary

    def generate_bid_adjustments(self, ad_summary: pd.DataFrame) -> pd.DataFrame:
        adjustments = ad_summary.copy()

        median_roi = adjustments['value_roi'].median()
        median_value = adjustments['mean_incremental_value'].median()

        def calc_bid_ratio(row):
            roi_factor = row['value_roi'] / max(median_roi, 0.001)
            value_factor = row['mean_incremental_value'] / max(median_value, 0.001)

            ratio = 1.0 + 0.3 * (roi_factor - 1.0) + 0.3 * (value_factor - 1.0)
            ratio = np.clip(ratio, self.min_bid_ratio, self.max_bid_ratio)
            return ratio

        adjustments['bid_adjustment_ratio'] = adjustments.apply(calc_bid_ratio, axis=1)
        adjustments['recommended_bid'] = (adjustments['base_bid'] *
                                           adjustments['bid_adjustment_ratio']).round(4)
        adjustments['bid_change_pct'] = ((adjustments['bid_adjustment_ratio'] - 1.0) * 100).round(2)

        def get_recommendation(row):
            if row['bid_adjustment_ratio'] > 1.2:
                return 'increase'
            elif row['bid_adjustment_ratio'] < 0.8:
                return 'decrease'
            else:
                return 'maintain'

        adjustments['recommendation'] = adjustments.apply(get_recommendation, axis=1)
        return adjustments

    def optimize_budget_allocation(self, ad_summary: pd.DataFrame) -> pd.DataFrame:
        allocation = ad_summary.copy()

        total_incremental = allocation['total_incremental_value'].sum()
        if total_incremental > 0:
            allocation['raw_target_ratio'] = (allocation['total_incremental_value'] / total_incremental)
        else:
            allocation['raw_target_ratio'] = 1.0 / len(allocation)

        allocation['target_budget_ratio'] = allocation['raw_target_ratio'].clip(
            self.min_budget_ratio, self.max_budget_ratio
        )

        raw_recommended = self.total_budget * allocation['target_budget_ratio']

        max_allowed_increase = allocation['current_budget'] * (1 + self.max_budget_change_pct / 100)
        max_allowed_decrease = allocation['current_budget'] * max(0, 1 - self.max_budget_change_pct / 100)

        allocation['recommended_budget'] = np.minimum(raw_recommended, max_allowed_increase)
        allocation['recommended_budget'] = np.maximum(allocation['recommended_budget'], max_allowed_decrease)

        total_after_constraints = allocation['recommended_budget'].sum()
        if total_after_constraints > 0:
            allocation['recommended_budget'] = (allocation['recommended_budget'] /
                                                 total_after_constraints * self.total_budget).round(2)

        allocation['budget_difference'] = (allocation['recommended_budget'] -
                                            allocation['current_budget']).round(2)

        def get_budget_action(row):
            change_pct = (row['budget_difference'] / max(row['current_budget'], 0.01)) * 100
            if change_pct > 5:
                return 'increase_budget'
            elif change_pct < -5:
                return 'decrease_budget'
            else:
                return 'maintain_budget'

        allocation['budget_action'] = allocation.apply(get_budget_action, axis=1)
        allocation['budget_change_pct'] = ((allocation['budget_difference'] /
                                            np.maximum(allocation['current_budget'], 0.01)) * 100).round(2)

        return allocation

    def generate_optimization_report(self, value_results: pd.DataFrame,
                                      df_ads: pd.DataFrame,
                                      df_users: pd.DataFrame) -> Dict:
        ranked_exposures = self.rank_exposures_by_value(value_results, df_ads, df_users)
        ad_summary = self.compute_ad_value_summary(value_results, df_ads)
        bid_adjustments = self.generate_bid_adjustments(ad_summary)
        budget_allocation = self.optimize_budget_allocation(ad_summary)

        high_value_exposures = ranked_exposures.head(100).to_dict('records')
        low_value_exposures = ranked_exposures.tail(100).to_dict('records')

        report = {
            'top_100_high_value_exposures': high_value_exposures,
            'top_100_low_value_exposures': low_value_exposures,
            'ad_value_summary': ad_summary.to_dict('records'),
            'bid_adjustments': bid_adjustments.to_dict('records'),
            'budget_allocation': budget_allocation.to_dict('records'),
            'statistics': {
                'total_impressions': len(value_results),
                'total_incremental_value': value_results['incremental_value'].sum(),
                'mean_incremental_value': value_results['incremental_value'].mean(),
                'median_incremental_value': value_results['incremental_value'].median(),
                'std_incremental_value': value_results['incremental_value'].std(),
                'total_budget': self.total_budget,
                'num_ads': len(ad_summary),
                'high_value_exposures_count': len(value_results[value_results['incremental_value'] > value_results['incremental_value'].quantile(0.75)]),
                'low_value_exposures_count': len(value_results[value_results['incremental_value'] < value_results['incremental_value'].quantile(0.25)]),
                'frequency_decay_alpha': self.frequency_decay_alpha,
                'max_budget_change_pct': self.max_budget_change_pct,
                'min_budget_ratio': self.min_budget_ratio,
                'max_budget_ratio': self.max_budget_ratio
            }
        }

        return report

    def get_bid_recommendation_for_ad(self, ad_id: int, ad_summary: pd.DataFrame) -> Optional[Dict]:
        adjustments = self.generate_bid_adjustments(ad_summary)
        ad_row = adjustments[adjustments['ad_id'] == ad_id]

        if len(ad_row) == 0:
            return None

        row = ad_row.iloc[0]
        return {
            'ad_id': ad_id,
            'current_bid': row['base_bid'],
            'recommended_bid': row['recommended_bid'],
            'bid_change_pct': row['bid_change_pct'],
            'recommendation': row['recommendation'],
            'reasoning': {
                'value_roi': row['value_roi'],
                'mean_incremental_value': row['mean_incremental_value'],
                'ctr': row['ctr'],
                'ad_quality_score': row['ad_quality_score']
            }
        }

    def get_budget_recommendation_for_ad(self, ad_id: int, ad_summary: pd.DataFrame) -> Optional[Dict]:
        allocation = self.optimize_budget_allocation(ad_summary)
        ad_row = allocation[allocation['ad_id'] == ad_id]

        if len(ad_row) == 0:
            return None

        row = ad_row.iloc[0]
        return {
            'ad_id': ad_id,
            'current_budget': row['current_budget'],
            'recommended_budget': row['recommended_budget'],
            'budget_difference': row['budget_difference'],
            'budget_change_pct': row['budget_change_pct'],
            'budget_action': row['budget_action'],
            'reasoning': {
                'total_incremental_value': row['total_incremental_value'],
                'value_roi': row['value_roi'],
                'target_budget_ratio': row['target_budget_ratio'],
                'max_budget_change_pct': self.max_budget_change_pct
            }
        }