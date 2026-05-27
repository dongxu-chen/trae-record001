import numpy as np
import pandas as pd
from typing import Dict, Optional


class PositionValueAnalyzer:
    def __init__(self):
        self.position_metrics = None
        self.position_comparison = None
        self.ad_position_metrics = None

    def analyze_position_values(self, value_results: pd.DataFrame,
                                 df_positions: pd.DataFrame) -> pd.DataFrame:
        merged = value_results.merge(df_positions, on='position_id', how='left')

        position_metrics = merged.groupby(['position_id', 'position_name']).agg(
            total_impressions=('impression_id', 'count'),
            total_clicks=('click', 'sum'),
            total_conversion_value=('conversion_value', 'sum'),
            total_incremental_value=('incremental_value', 'sum'),
            mean_incremental_value=('incremental_value', 'mean'),
            std_incremental_value=('incremental_value', 'std'),
            total_marginal_value=('marginal_value', 'sum')
        ).reset_index()

        position_metrics['ctr'] = position_metrics['total_clicks'] / position_metrics['total_impressions']
        position_metrics['avg_conversion_value'] = np.where(
            position_metrics['total_clicks'] > 0,
            position_metrics['total_conversion_value'] / position_metrics['total_clicks'],
            0
        )
        position_metrics['value_per_impression'] = position_metrics['total_incremental_value'] / position_metrics['total_impressions']
        position_metrics['conversion_rate'] = np.where(
            position_metrics['total_clicks'] > 0,
            (merged.groupby(['position_id', 'position_name'])['conversion'].sum() / position_metrics['total_clicks']).values
            if 'conversion' in merged.columns else 0,
            0
        )

        position_metrics = position_metrics.sort_values('mean_incremental_value', ascending=False)
        self.position_metrics = position_metrics
        return position_metrics

    def compare_positions(self, position_metrics: Optional[pd.DataFrame] = None) -> Dict:
        metrics = position_metrics if position_metrics is not None else self.position_metrics
        if metrics is None:
            raise ValueError("No position metrics available. Run analyze_position_values first.")

        sorted_by_value = metrics.sort_values('mean_incremental_value', ascending=False)
        best_position = sorted_by_value.iloc[0]
        worst_position = sorted_by_value.iloc[-1]

        value_gap = best_position['mean_incremental_value'] - worst_position['mean_incremental_value']
        value_gap_pct = (value_gap / max(abs(worst_position['mean_incremental_value']), 0.001)) * 100

        ctr_gap = best_position['ctr'] - worst_position['ctr']
        conversion_gap = best_position['conversion_rate'] - worst_position['conversion_rate']

        metrics['value_rank'] = metrics['mean_incremental_value'].rank(ascending=False, method='min')
        metrics['ctr_rank'] = metrics['ctr'].rank(ascending=False, method='min')
        metrics['overall_score'] = (
            0.4 * metrics['value_rank'] +
            0.3 * metrics['ctr_rank'] +
            0.3 * (len(metrics) - metrics['conversion_rate'].rank(ascending=False, method='min') + 1)
        )

        comparison = {
            'best_position': {
                'position_id': best_position['position_id'],
                'position_name': best_position['position_name'],
                'mean_incremental_value': best_position['mean_incremental_value'],
                'ctr': best_position['ctr'],
                'conversion_rate': best_position['conversion_rate'],
                'total_impressions': best_position['total_impressions']
            },
            'worst_position': {
                'position_id': worst_position['position_id'],
                'position_name': worst_position['position_name'],
                'mean_incremental_value': worst_position['mean_incremental_value'],
                'ctr': worst_position['ctr'],
                'conversion_rate': worst_position['conversion_rate'],
                'total_impressions': worst_position['total_impressions']
            },
            'gaps': {
                'value_gap_absolute': value_gap,
                'value_gap_percentage': value_gap_pct,
                'ctr_gap': ctr_gap,
                'conversion_rate_gap': conversion_gap
            },
            'ranked_positions': metrics.to_dict('records')
        }

        self.position_comparison = comparison
        return comparison

    def analyze_position_by_ad(self, value_results: pd.DataFrame,
                                df_positions: pd.DataFrame,
                                df_ads: pd.DataFrame) -> pd.DataFrame:
        merged = value_results.merge(df_positions, on='position_id', how='left')
        merged = merged.merge(df_ads[['ad_id', 'category', 'base_bid', 'ad_quality_score']], on='ad_id', how='left')

        ad_position_metrics = merged.groupby(['ad_id', 'position_id', 'position_name', 'category']).agg(
            total_impressions=('impression_id', 'count'),
            total_clicks=('click', 'sum'),
            total_conversion_value=('conversion_value', 'sum'),
            total_incremental_value=('incremental_value', 'sum'),
            mean_incremental_value=('incremental_value', 'mean')
        ).reset_index()

        ad_position_metrics['ctr'] = ad_position_metrics['total_clicks'] / ad_position_metrics['total_impressions']
        ad_position_metrics['value_per_impression'] = ad_position_metrics['total_incremental_value'] / ad_position_metrics['total_impressions']
        ad_position_metrics['conversion_rate'] = np.where(
            ad_position_metrics['total_clicks'] > 0,
            (merged.groupby(['ad_id', 'position_id', 'position_name', 'category'])['conversion'].sum() / ad_position_metrics['total_clicks']).values
            if 'conversion' in merged.columns else 0,
            0
        )

        ad_position_metrics['performance_percentile'] = ad_position_metrics.groupby('ad_id')['mean_incremental_value'].rank(pct=True)
        ad_position_metrics['is_best_for_ad'] = ad_position_metrics.groupby('ad_id')['mean_incremental_value'].transform('max') == ad_position_metrics['mean_incremental_value']
        ad_position_metrics['is_worst_for_ad'] = ad_position_metrics.groupby('ad_id')['mean_incremental_value'].transform('min') == ad_position_metrics['mean_incremental_value']

        ad_position_metrics = ad_position_metrics.sort_values(['ad_id', 'mean_incremental_value'], ascending=[True, False])
        self.ad_position_metrics = ad_position_metrics
        return ad_position_metrics

    def generate_position_report(self) -> Dict:
        if self.position_metrics is None:
            raise ValueError("No analysis data available. Run analyze_position_values first.")

        if self.position_comparison is None:
            self.compare_positions()

        report = {
            'position_metrics_summary': self.position_metrics.to_dict('records'),
            'position_comparison': self.position_comparison,
            'statistics': {
                'total_positions': len(self.position_metrics),
                'total_impressions': self.position_metrics['total_impressions'].sum(),
                'total_clicks': self.position_metrics['total_clicks'].sum(),
                'total_conversion_value': self.position_metrics['total_conversion_value'].sum(),
                'total_incremental_value': self.position_metrics['total_incremental_value'].sum(),
                'mean_ctr': self.position_metrics['ctr'].mean(),
                'mean_incremental_value': self.position_metrics['mean_incremental_value'].mean(),
                'std_incremental_value': self.position_metrics['mean_incremental_value'].std(),
                'best_position_value': self.position_metrics['mean_incremental_value'].max(),
                'worst_position_value': self.position_metrics['mean_incremental_value'].min()
            }
        }

        if self.ad_position_metrics is not None:
            report['ad_position_analysis'] = {
                'total_ad_position_pairs': len(self.ad_position_metrics),
                'best_ad_position_combinations': self.ad_position_metrics[self.ad_position_metrics['is_best_for_ad']].to_dict('records'),
                'worst_ad_position_combinations': self.ad_position_metrics[self.ad_position_metrics['is_worst_for_ad']].to_dict('records'),
                'ad_position_metrics': self.ad_position_metrics.to_dict('records')
            }

        return report
