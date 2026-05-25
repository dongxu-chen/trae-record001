import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Union
import logging
from datetime import datetime, timedelta
from scipy.stats import norm, gamma, lognorm, poisson, beta
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupplierRiskAssessor:
    def __init__(self, config: Optional[Dict] = None):
        from config import Config
        self.config = config or Config().config
        self.risk_config = self.config.get('supplier_risk', {})
        self.confidence_level = self.config.get('forecasting.confidence_level', 0.95)
        self.z_score = norm.ppf((1 + self.confidence_level) / 2)

        self.supplier_history: Dict[str, pd.DataFrame] = {}
        self.supplier_risk_scores: Dict[str, Dict] = {}
        self.lead_time_distributions: Dict[str, Dict] = {}

    def analyze_lead_time_history(self, supplier_df: pd.DataFrame,
                                   purchase_history_df: pd.DataFrame = None) -> pd.DataFrame:
        logger.info("Analyzing supplier lead time history...")

        if purchase_history_df is not None and 'actual_lead_time' in purchase_history_df.columns:
            lead_time_data = purchase_history_df.copy()
        else:
            lead_time_data = supplier_df.copy()

        analysis_results = []

        for supplier in lead_time_data['supplier_name'].unique():
            supplier_data = lead_time_data[lead_time_data['supplier_name'] == supplier].copy()

            if 'actual_lead_time' in supplier_data.columns:
                actual_lead_times = supplier_data['actual_lead_time'].dropna().values
            elif 'lead_time_days' in supplier_data.columns:
                actual_lead_times = supplier_data['lead_time_days'].dropna().values
            else:
                continue

            if len(actual_lead_times) < 5:
                logger.warning(f"Insufficient lead time data for {supplier}")
                continue

            product_id = supplier_data['product_id'].iloc[0] if 'product_id' in supplier_data.columns else 'ALL'

            stats = self._calculate_lead_time_statistics(actual_lead_times)
            distribution = self._fit_lead_time_distribution(actual_lead_times)
            risk_score = self._calculate_supplier_risk_score(stats, distribution, supplier_data)

            self.supplier_history[supplier] = supplier_data
            self.supplier_risk_scores[supplier] = {
                'product_id': product_id,
                **stats,
                **risk_score,
                'distribution': distribution['type']
            }
            self.lead_time_distributions[supplier] = distribution

            analysis_results.append({
                'supplier_name': supplier,
                'product_id': product_id,
                **stats,
                **risk_score,
                'best_fit_distribution': distribution['type'],
                'distribution_params': str(distribution.get('params', {}))
            })

        results_df = pd.DataFrame(analysis_results)

        if not results_df.empty:
            results_df = results_df.sort_values('overall_risk_score', ascending=False)

        logger.info(f"Analyzed lead time for {len(analysis_results)} suppliers")
        return results_df

    def _calculate_lead_time_statistics(self, lead_times: np.ndarray) -> Dict:
        clean_lead_times = lead_times[lead_times > 0]

        if len(clean_lead_times) == 0:
            return {}

        stats = {
            'mean_lead_time': np.mean(clean_lead_times),
            'median_lead_time': np.median(clean_lead_times),
            'std_lead_time': np.std(clean_lead_times, ddof=1),
            'min_lead_time': np.min(clean_lead_times),
            'max_lead_time': np.max(clean_lead_times),
            'range_lead_time': np.max(clean_lead_times) - np.min(clean_lead_times),
            'cv_lead_time': np.std(clean_lead_times, ddof=1) / np.mean(clean_lead_times) if np.mean(clean_lead_times) > 0 else 0,
            'q10_lead_time': np.percentile(clean_lead_times, 10),
            'q25_lead_time': np.percentile(clean_lead_times, 25),
            'q75_lead_time': np.percentile(clean_lead_times, 75),
            'q90_lead_time': np.percentile(clean_lead_times, 90),
            'q95_lead_time': np.percentile(clean_lead_times, 95),
            'q99_lead_time': np.percentile(clean_lead_times, 99),
            'skewness': pd.Series(clean_lead_times).skew(),
            'kurtosis': pd.Series(clean_lead_times).kurtosis(),
            'sample_size': len(clean_lead_times)
        }

        return stats

    def _fit_lead_time_distribution(self, lead_times: np.ndarray) -> Dict:
        clean_lead_times = lead_times[lead_times > 0]

        if len(clean_lead_times) < 10:
            return {'type': 'normal', 'params': {'loc': np.mean(clean_lead_times), 'scale': np.std(clean_lead_times)}}

        results = []

        try:
            mu, std = norm.fit(clean_lead_times)
            kstest_stat, kstest_pvalue = norm.fit(clean_lead_times)
            results.append({'type': 'normal', 'params': {'loc': mu, 'scale': std}, 'ks_stat': kstest_stat})
        except:
            pass

        try:
            a, loc, scale = gamma.fit(clean_lead_times, floc=0)
            kstest_stat, kstest_pvalue = gamma.fit(clean_lead_times, floc=0)
            results.append({'type': 'gamma', 'params': {'a': a, 'loc': loc, 'scale': scale}, 'ks_stat': kstest_stat})
        except:
            pass

        try:
            shape, loc, scale = lognorm.fit(clean_lead_times, floc=0)
            kstest_stat, kstest_pvalue = lognorm.fit(clean_lead_times, floc=0)
            results.append({'type': 'lognormal', 'params': {'shape': shape, 'loc': loc, 'scale': scale}, 'ks_stat': kstest_stat})
        except:
            pass

        try:
            lambda_poisson = np.mean(clean_lead_times)
            kstest_stat, kstest_pvalue = poisson.fit(clean_lead_times)
            results.append({'type': 'poisson', 'params': {'mu': lambda_poisson}, 'ks_stat': kstest_stat})
        except:
            pass

        if results:
            best_fit = min(results, key=lambda x: x['ks_stat'])
            return best_fit

        return {'type': 'normal', 'params': {'loc': np.mean(clean_lead_times), 'scale': np.std(clean_lead_times)}}

    def _calculate_supplier_risk_score(self, stats: Dict, distribution: Dict, supplier_data: pd.DataFrame) -> Dict:
        if not stats:
            return {'overall_risk_score': 0.5, 'risk_level': 'Medium'}

        cv_score = min(1.0, stats.get('cv_lead_time', 0) / 0.5)

        range_score = min(1.0, stats.get('range_lead_time', 0) / 30)

        on_time_rate = 0.8
        if 'on_time' in supplier_data.columns:
            on_time_rate = supplier_data['on_time'].mean()
        elif 'promised_lead_time' in supplier_data.columns and 'actual_lead_time' in supplier_data.columns:
            on_time_rate = (supplier_data['actual_lead_time'] <= supplier_data['promised_lead_time']).mean()
        delivery_score = 1 - on_time_rate

        quality_score = 0.0
        if 'defect_rate' in supplier_data.columns:
            quality_score = min(1.0, supplier_data['defect_rate'].mean() / 0.1)
        elif 'quality_score' in supplier_data.columns:
            quality_score = 1 - (supplier_data['quality_score'].mean() / 100)

        risk_scores = {
            'lead_time_variability_score': cv_score * 0.35,
            'lead_time_range_score': range_score * 0.15,
            'delivery_reliability_score': delivery_score * 0.30,
            'quality_score': quality_score * 0.20
        }

        overall_risk = sum(risk_scores.values())

        risk_level = 'Low' if overall_risk < 0.3 else 'Medium' if overall_risk < 0.6 else 'High'

        risk_scores.update({
            'overall_risk_score': overall_risk,
            'risk_level': risk_level,
            'on_time_delivery_rate': on_time_rate,
            'quality_score': 1 - quality_score
        })

        return risk_scores

    def adjust_forecast_confidence_interval(self, forecast_df: pd.DataFrame,
                                             supplier_risk_df: pd.DataFrame,
                                             supplier_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Adjusting forecast confidence intervals based on supplier risk...")

        adjusted_forecast = forecast_df.copy()

        if 'supplier_name' not in adjusted_forecast.columns and 'product_id' in adjusted_forecast.columns:
            product_supplier = supplier_df.groupby('product_id')['supplier_name'].first().reset_index()
            adjusted_forecast = adjusted_forecast.merge(product_supplier, on='product_id', how='left')

        if 'supplier_name' not in adjusted_forecast.columns:
            logger.warning("No supplier information available for confidence adjustment")
            return adjusted_forecast

        risk_multipliers = {}
        for supplier in supplier_risk_df['supplier_name'].unique():
            risk_data = supplier_risk_df[supplier_risk_df['supplier_name'] == supplier].iloc[0]
            risk_score = risk_data['overall_risk_score']
            cv = risk_data.get('cv_lead_time', 0.1)

            multiplier = 1 + risk_score * 0.5 + cv * 0.3
            risk_multipliers[supplier] = multiplier

        adjusted_forecast['supplier_risk_multiplier'] = adjusted_forecast['supplier_name'].map(risk_multipliers).fillna(1.0)

        if 'forecast_lower' in adjusted_forecast.columns and 'forecast_upper' in adjusted_forecast.columns:
            original_width = adjusted_forecast['forecast_upper'] - adjusted_forecast['forecast']
            adjusted_width = original_width * adjusted_forecast['supplier_risk_multiplier']

            adjusted_forecast['forecast_lower'] = np.maximum(0, adjusted_forecast['forecast'] - adjusted_width)
            adjusted_forecast['forecast_upper'] = adjusted_forecast['forecast'] + adjusted_width
            adjusted_forecast['confidence_interval_adjusted'] = True

        adjusted_forecast['lead_time_std'] = adjusted_forecast['supplier_name'].map(
            supplier_risk_df.set_index('supplier_name')['std_lead_time']
        ).fillna(7)

        return adjusted_forecast

    def adjust_safety_stock_for_risk(self, safety_stock_df: pd.DataFrame,
                                      supplier_risk_df: pd.DataFrame,
                                      supplier_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Adjusting safety stock levels based on supplier risk...")

        adjusted_ss = safety_stock_df.copy()

        if 'supplier_name' not in adjusted_ss.columns and 'product_id' in adjusted_ss.columns:
            product_supplier = supplier_df.groupby('product_id')['supplier_name'].first().reset_index()
            adjusted_ss = adjusted_ss.merge(product_supplier, on='product_id', how='left')

        if 'supplier_name' not in adjusted_ss.columns:
            logger.warning("No supplier information available for safety stock adjustment")
            return adjusted_ss

        risk_adjustments = {}
        for supplier in supplier_risk_df['supplier_name'].unique():
            risk_data = supplier_risk_df[supplier_risk_df['supplier_name'] == supplier].iloc[0]
            risk_level = risk_data['risk_level']
            cv = risk_data.get('cv_lead_time', 0.1)
            p95_lead_time = risk_data.get('q95_lead_time', risk_data.get('mean_lead_time', 7) * 1.5)

            if risk_level == 'High':
                adjustment_factor = 1.5
                lead_time_buffer = p95_lead_time - risk_data.get('mean_lead_time', 7)
            elif risk_level == 'Medium':
                adjustment_factor = 1.2
                lead_time_buffer = p95_lead_time - risk_data.get('mean_lead_time', 7)
            else:
                adjustment_factor = 1.0
                lead_time_buffer = 0

            risk_adjustments[supplier] = {
                'adjustment_factor': adjustment_factor,
                'lead_time_buffer': lead_time_buffer,
                'cv_lead_time': cv
            }

        def adjust_row(row):
            supplier = row.get('supplier_name', None)
            if supplier not in risk_adjustments:
                return row

            adj = risk_adjustments[supplier]
            original_ss = row.get('safety_stock_recommended', 0)
            daily_demand = row.get('avg_daily_demand', 0)

            adjusted_ss = original_ss * adj['adjustment_factor']
            additional_buffer = daily_demand * adj['lead_time_buffer']
            final_ss = adjusted_ss + additional_buffer

            row['safety_stock_recommended'] = final_ss
            row['safety_stock_original'] = original_ss
            row['safety_stock_adjustment_factor'] = adj['adjustment_factor']
            row['lead_time_buffer_days'] = adj['lead_time_buffer']
            row['supplier_risk_level'] = supplier_risk_df[
                supplier_risk_df['supplier_name'] == supplier
            ]['risk_level'].iloc[0]

            return row

        adjusted_ss = adjusted_ss.apply(adjust_row, axis=1)

        if 'reorder_point' in adjusted_ss.columns and 'avg_daily_demand' in adjusted_ss.columns and 'avg_lead_time' in adjusted_ss.columns:
            adjusted_ss['reorder_point'] = (
                adjusted_ss['avg_daily_demand'] *
                (adjusted_ss['avg_lead_time'] + adjusted_ss.get('lead_time_buffer_days', 0))
            ) + adjusted_ss['safety_stock_recommended']

        return adjusted_ss

    def simulate_lead_time(self, supplier_name: str, num_samples: int = 1000) -> np.ndarray:
        if supplier_name not in self.lead_time_distributions:
            logger.warning(f"No distribution found for {supplier_name}, using normal approximation")
            mean_lt = self.supplier_risk_scores.get(supplier_name, {}).get('mean_lead_time', 7)
            std_lt = self.supplier_risk_scores.get(supplier_name, {}).get('std_lead_time', 2)
            return np.maximum(1, np.random.normal(mean_lt, std_lt, num_samples).astype(int))

        dist = self.lead_time_distributions[supplier_name]
        params = dist['params']

        if dist['type'] == 'normal':
            samples = norm.rvs(loc=params['loc'], scale=params['scale'], size=num_samples)
        elif dist['type'] == 'gamma':
            samples = gamma.rvs(a=params['a'], loc=params['loc'], scale=params['scale'], size=num_samples)
        elif dist['type'] == 'lognormal':
            samples = lognorm.rvs(s=params['shape'], loc=params['loc'], scale=params['scale'], size=num_samples)
        elif dist['type'] == 'poisson':
            samples = poisson.rvs(mu=params['mu'], size=num_samples)
        else:
            mean_lt = self.supplier_risk_scores.get(supplier_name, {}).get('mean_lead_time', 7)
            std_lt = self.supplier_risk_scores.get(supplier_name, {}).get('std_lead_time', 2)
            samples = norm.rvs(loc=mean_lt, scale=std_lt, size=num_samples)

        return np.maximum(1, samples.astype(int))

    def get_supplier_risk_report(self) -> pd.DataFrame:
        if not self.supplier_risk_scores:
            return pd.DataFrame()

        report = pd.DataFrame.from_dict(self.supplier_risk_scores, orient='index').reset_index()
        report = report.rename(columns={'index': 'supplier_name'})

        return report.sort_values('overall_risk_score', ascending=False)

    def identify_high_risk_suppliers(self, threshold: float = 0.6) -> pd.DataFrame:
        report = self.get_supplier_risk_report()
        if report.empty:
            return report

        high_risk = report[report['overall_risk_score'] >= threshold].copy()
        return high_risk.sort_values('overall_risk_score', ascending=False)

    def recommend_supplier_actions(self) -> pd.DataFrame:
        report = self.get_supplier_risk_report()
        if report.empty:
            return report

        recommendations = []

        for _, row in report.iterrows():
            risk_level = row['risk_level']
            cv = row.get('cv_lead_time', 0)
            on_time_rate = row.get('on_time_delivery_rate', 0)

            if risk_level == 'High':
                if cv > 0.3:
                    action = 'Consider dual sourcing or find alternative suppliers'
                elif on_time_rate < 0.7:
                    action = 'Implement stricter delivery penalties and monitoring'
                else:
                    action = 'Increase safety stock and reorder point'
                priority = 'Critical'
            elif risk_level == 'Medium':
                if cv > 0.2:
                    action = 'Work with supplier to reduce lead time variability'
                else:
                    action = 'Monitor supplier performance quarterly'
                priority = 'Medium'
            else:
                action = 'Maintain current relationship, consider volume discounts'
                priority = 'Low'

            recommendations.append({
                'supplier_name': row['supplier_name'],
                'product_id': row.get('product_id', 'ALL'),
                'overall_risk_score': row['overall_risk_score'],
                'risk_level': risk_level,
                'recommended_action': action,
                'priority': priority,
                'estimated_cost_impact': row.get('mean_lead_time', 7) * row.get('overall_risk_score', 0) * 100
            })

        return pd.DataFrame(recommendations).sort_values('overall_risk_score', ascending=False)

    def plot_lead_time_distribution(self, supplier_name: str, num_samples: int = 1000):
        try:
            import matplotlib.pyplot as plt

            if supplier_name not in self.lead_time_distributions:
                logger.warning(f"No distribution found for {supplier_name}")
                return None

            samples = self.simulate_lead_time(supplier_name, num_samples)
            actual_data = self.supplier_history.get(supplier_name, None)

            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            axes[0, 0].hist(samples, bins=30, alpha=0.7, density=True, label='Simulated')
            axes[0, 0].set_title(f'Lead Time Distribution - {supplier_name}')
            axes[0, 0].set_xlabel('Lead Time (days)')
            axes[0, 0].set_ylabel('Density')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

            if actual_data is not None and 'actual_lead_time' in actual_data.columns:
                actual_lt = actual_data['actual_lead_time'].dropna().values
                axes[0, 1].hist(actual_lt, bins=20, alpha=0.7, density=True, label='Actual', color='orange')
                axes[0, 1].set_title('Actual Lead Time Distribution')
                axes[0, 1].set_xlabel('Lead Time (days)')
                axes[0, 1].legend()
                axes[0, 1].grid(True, alpha=0.3)

            sorted_samples = np.sort(samples)
            cdf = np.arange(1, len(sorted_samples) + 1) / len(sorted_samples)
            axes[1, 0].plot(sorted_samples, cdf)
            axes[1, 0].fill_between(sorted_samples, cdf, alpha=0.3)
            axes[1, 0].set_title('Cumulative Distribution Function')
            axes[1, 0].set_xlabel('Lead Time (days)')
            axes[1, 0].set_ylabel('Cumulative Probability')
            axes[1, 0].grid(True, alpha=0.3)

            risk_scores = self.supplier_risk_scores.get(supplier_name, {})
            metrics = ['overall_risk_score', 'lead_time_variability_score',
                       'delivery_reliability_score', 'quality_score']
            values = [risk_scores.get(m, 0) for m in metrics]
            axes[1, 1].barh(metrics, values, color=['red', 'orange', 'blue', 'green'])
            axes[1, 1].set_title('Risk Component Breakdown')
            axes[1, 1].set_xlim(0, 1)
            axes[1, 1].grid(True, alpha=0.3, axis='x')

            plt.tight_layout()
            return plt

        except Exception as e:
            logger.warning(f"Could not plot lead time distribution: {e}")
            return None
