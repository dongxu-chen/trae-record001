import pandas as pd
import numpy as np
from scipy.optimize import minimize_scalar, minimize
import warnings
warnings.filterwarnings('ignore')


def calculate_roi_metrics(touchpoints_df, attribution_df, weight_column='ensemble_weight'):
    channel_metrics = touchpoints_df.groupby('channel').agg({
        'cost': 'sum',
        'user_id': 'nunique'
    }).reset_index()
    channel_metrics.columns = ['channel', 'current_spend', 'users_reached']
    
    total_conversions = touchpoints_df[touchpoints_df['converted'] == 1]['user_id'].nunique()
    total_value = touchpoints_df[touchpoints_df['converted'] == 1]['conversion_value'].sum()
    
    merged = channel_metrics.merge(
        attribution_df[['channel', weight_column]],
        on='channel',
        how='outer'
    )
    
    merged = merged.fillna(0)
    
    merged['attributed_conversions'] = merged[weight_column] * total_conversions
    merged['attributed_value'] = merged[weight_column] * total_value
    
    merged['roi'] = np.where(
        merged['current_spend'] > 0,
        (merged['attributed_value'] - merged['current_spend']) / merged['current_spend'] * 100,
        0
    )
    
    merged['cac'] = np.where(
        merged['attributed_conversions'] > 0,
        merged['current_spend'] / merged['attributed_conversions'],
        0
    )
    
    merged['roas'] = np.where(
        merged['current_spend'] > 0,
        merged['attributed_value'] / merged['current_spend'],
        0
    )
    
    return merged


class ResponseCurve:
    def __init__(self, channel, current_spend, current_value, saturation_multiplier=2.5):
        self.channel = channel
        self.current_spend = current_spend
        self.current_value = current_value
        self.saturation_point = current_spend * saturation_multiplier
        self.base_roas = current_value / current_spend if current_spend > 0 else 1
        self.hill_slope = self._estimate_hill_slope()
        self.half_saturation = current_spend * 1.2
        
    def _estimate_hill_slope(self):
        if self.current_spend <= 0:
            return 2.0
        return max(1.5, min(3.0, 2.0 * self.base_roas / (self.base_roas + 1)))
    
    def value(self, spend):
        if spend <= 0:
            return 0
        if self.current_spend <= 0:
            return self.current_value * (1 - np.exp(-spend / 500))
        
        if spend <= self.current_spend:
            return (spend / self.current_spend) * self.current_value
        
        excess = spend - self.current_spend
        excess_ratio = excess / self.current_spend
        decay = 1 / (1 + excess_ratio * 0.5)
        return self.current_value + excess * self.base_roas * decay
    
    def marginal_return(self, spend, delta=1.0):
        if spend <= delta:
            return self.value(delta) / delta
        return (self.value(spend) - self.value(spend - delta)) / delta
    
    def find_optimal_spend(self, marginal_cost=1.0):
        if self.current_spend <= 0:
            result = minimize_scalar(
                lambda s: -(self.marginal_return(s) - marginal_cost),
                bounds=(10, 5000),
                method='bounded'
            )
            return result.x
        
        search_range = np.linspace(10, self.current_spend * 3, 200)
        marginal_returns = np.array([self.marginal_return(s) for s in search_range])
        
        optimal_idx = None
        for i in range(len(marginal_returns) - 1):
            if marginal_returns[i] >= marginal_cost and marginal_returns[i + 1] < marginal_cost:
                optimal_idx = i
                break
        
        if optimal_idx is None:
            if marginal_returns[-1] >= marginal_cost:
                return search_range[-1]
            else:
                return search_range[0]
        
        from scipy.interpolate import interp1d
        f = interp1d(
            marginal_returns[optimal_idx:optimal_idx + 2] - marginal_cost,
            search_range[optimal_idx:optimal_idx + 2],
            kind='linear',
            fill_value='extrapolate'
        )
        return float(f(0))
    
    def get_curve_data(self, max_spend=None, n_points=100):
        if max_spend is None:
            max_spend = max(self.current_spend * 3, 1000)
        
        spends = np.linspace(10, max_spend, n_points)
        values = np.array([self.value(s) for s in spends])
        marginal = np.array([self.marginal_return(s) for s in spends])
        roas = np.where(spends > 0, values / spends, 0)
        
        return pd.DataFrame({
            'spend': spends,
            'value': values,
            'marginal_return': marginal,
            'roas': roas
        })


def build_response_curves(roi_metrics):
    curves = {}
    for _, row in roi_metrics.iterrows():
        channel = row['channel']
        current_spend = row['current_spend']
        current_value = row['attributed_value']
        
        curves[channel] = ResponseCurve(channel, current_spend, current_value)
    
    return curves


def calculate_marginal_return_analysis(response_curves, roi_metrics):
    results = []
    
    for channel, curve in response_curves.items():
        row = roi_metrics[roi_metrics['channel'] == channel]
        current_spend = row['current_spend'].values[0] if len(row) > 0 else 0
        
        marginal_at_current = curve.marginal_return(current_spend) if current_spend > 0 else 0
        optimal_spend = curve.find_optimal_spend(marginal_cost=1.0)
        optimal_value = curve.value(optimal_spend)
        
        curve_data = curve.get_curve_data()
        optimal_marginal = curve.marginal_return(optimal_spend)
        
        results.append({
            'channel': channel,
            'current_spend': current_spend,
            'optimal_spend': round(optimal_spend, 2),
            'marginal_return_at_current': round(marginal_at_current, 4),
            'marginal_return_at_optimal': round(optimal_marginal, 4),
            'optimal_projected_value': round(optimal_value, 2),
            'spend_efficiency': round(optimal_spend / current_spend, 2) if current_spend > 0 else float('inf'),
            'curve_data': curve_data
        })
    
    return pd.DataFrame(results)


def optimize_budget(roi_metrics, total_budget, response_curves=None):
    if response_curves is None:
        response_curves = build_response_curves(roi_metrics)
    
    channels = roi_metrics['channel'].tolist()
    n_channels = len(channels)
    
    current_spends = roi_metrics.set_index('channel')['current_spend'].to_dict()
    
    def objective(spend_array):
        total_value = 0
        for i, channel in enumerate(channels):
            spend = spend_array[i]
            if channel in response_curves:
                total_value += response_curves[channel].value(spend)
        return -total_value
    
    def budget_constraint(spend_array):
        return total_budget - np.sum(spend_array)
    
    x0 = np.array([current_spends.get(c, total_budget / n_channels) for c in channels])
    
    bounds = []
    for channel in channels:
        current = current_spends.get(channel, 0)
        min_spend = max(0, current * 0.3)
        max_spend = total_budget * 0.6
        bounds.append((min_spend, max_spend))
    
    constraints = [{'type': 'ineq', 'fun': budget_constraint}]
    
    result = minimize(
        objective,
        x0,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000}
    )
    
    optimized_spends = result.x
    
    recommendations = []
    for i, channel in enumerate(channels):
        current = current_spends.get(channel, 0)
        optimized = optimized_spends[i]
        
        if channel in response_curves:
            projected_value = response_curves[channel].value(optimized)
        else:
            projected_value = optimized * roi_metrics[roi_metrics['channel'] == channel]['roas'].values[0]
        
        recommendations.append({
            'channel': channel,
            'current_spend': current,
            'recommended_spend': optimized,
            'change_amount': optimized - current,
            'change_percent': ((optimized - current) / current * 100) if current > 0 else float('inf'),
            'projected_value': projected_value
        })
    
    rec_df = pd.DataFrame(recommendations)
    rec_df['change_percent'] = rec_df['change_percent'].replace([float('inf')], 999)
    
    return rec_df


def generate_budget_insights(recommendations_df, roi_metrics, marginal_analysis=None):
    insights = []
    
    high_roi_channels = roi_metrics[roi_metrics['roi'] > 50]
    if len(high_roi_channels) > 0:
        channels_str = ', '.join(high_roi_channels['channel'].tolist())
        insights.append({
            'type': 'opportunity',
            'title': '高ROI渠道',
            'content': f'{channels_str} 等渠道ROI超过50%，建议增加预算投入'
        })
    
    low_roi_channels = roi_metrics[(roi_metrics['roi'] < 0) & (roi_metrics['current_spend'] > 0)]
    if len(low_roi_channels) > 0:
        channels_str = ', '.join(low_roi_channels['channel'].tolist())
        insights.append({
            'type': 'warning',
            'title': '低效率渠道',
            'content': f'{channels_str} 等渠道ROI为负，建议优化或减少预算'
        })
    
    increased_budget = recommendations_df[recommendations_df['change_percent'] > 20]
    if len(increased_budget) > 0:
        channels_str = ', '.join(increased_budget['channel'].tolist())
        insights.append({
            'type': 'recommendation',
            'title': '预算增加建议',
            'content': f'建议增加 {channels_str} 的预算投入，预期带来更高回报'
        })
    
    decreased_budget = recommendations_df[recommendations_df['change_percent'] < -20]
    if len(decreased_budget) > 0:
        channels_str = ', '.join(decreased_budget['channel'].tolist())
        insights.append({
            'type': 'recommendation',
            'title': '预算优化建议',
            'content': f'建议减少 {channels_str} 的预算，将资金转移到更高效率渠道'
        })
    
    high_cac_channels = roi_metrics[roi_metrics['cac'] > roi_metrics['cac'].quantile(0.75)]
    if len(high_cac_channels) > 0 and len(high_cac_channels) < len(roi_metrics) * 0.5:
        channels_str = ', '.join(high_cac_channels['channel'].tolist())
        avg_cac = high_cac_channels['cac'].mean()
        insights.append({
            'type': 'warning',
            'title': '高获客成本',
            'content': f'{channels_str} 的获客成本较高(平均¥{avg_cac:.1f})，建议优化投放策略'
        })
    
    if marginal_analysis is not None:
        over_saturated = marginal_analysis[marginal_analysis['marginal_return_at_current'] < 0.5]
        if len(over_saturated) > 0:
            channels_str = ', '.join(over_saturated['channel'].tolist())
            insights.append({
                'type': 'warning',
                'title': '边际收益递减',
                'content': f'{channels_str} 当前预算已超过边际收益递减点，继续投入的回报率较低'
            })
        
        under_invested = marginal_analysis[
            (marginal_analysis['marginal_return_at_current'] > 1.5) & 
            (marginal_analysis['current_spend'] > 0)
        ]
        if len(under_invested) > 0:
            channels_str = ', '.join(under_invested['channel'].tolist())
            insights.append({
                'type': 'opportunity',
                'title': '边际收益充裕',
                'content': f'{channels_str} 仍有较高边际收益，每增加1元投入预期可获得>1.5元回报'
            })
    
    return insights


def run_budget_analysis(touchpoints_df, attribution_df, total_budget=None, weight_column='ensemble_weight'):
    roi_metrics = calculate_roi_metrics(touchpoints_df, attribution_df, weight_column)
    
    if total_budget is None:
        total_budget = roi_metrics['current_spend'].sum()
    
    response_curves = build_response_curves(roi_metrics)
    
    optimized = optimize_budget(roi_metrics, total_budget, response_curves)
    
    marginal_analysis = calculate_marginal_return_analysis(response_curves, roi_metrics)
    
    insights = generate_budget_insights(optimized, roi_metrics, marginal_analysis)
    
    return {
        'roi_metrics': roi_metrics,
        'recommendations': optimized,
        'insights': insights,
        'response_curves': response_curves,
        'total_budget': total_budget,
        'marginal_analysis': marginal_analysis
    }


if __name__ == '__main__':
    from data_generator import generate_attribution_data
    from attribution_models import run_all_attribution_models
    from shap_attribution import shap_based_attribution, combine_all_attributions
    
    users_df, touchpoints_df = generate_attribution_data(n_users=2000)
    
    rule_attributions = run_all_attribution_models(touchpoints_df)
    shap_attr, _ = shap_based_attribution(touchpoints_df)
    combined = combine_all_attributions(rule_attributions, shap_attr)
    
    print("运行预算优化...")
    budget_results = run_budget_analysis(
        touchpoints_df, 
        combined, 
        total_budget=10000
    )
    
    print("\n边际收益分析:")
    ma = budget_results['marginal_analysis']
    print(ma[['channel', 'current_spend', 'optimal_spend', 'marginal_return_at_current', 'marginal_return_at_optimal']])
