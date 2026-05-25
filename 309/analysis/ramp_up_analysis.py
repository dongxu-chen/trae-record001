import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from datetime import datetime, timedelta
from scipy.optimize import curve_fit
from scipy.stats import norm

from config import Config
from .transfer_learning import TransferLearningAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RampUpAnalyzer:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().config
        self.ramp_period = self.config.get('ramp_up.ramp_period_days', 90)
        self.growth_curve_type = self.config.get('ramp_up.growth_curve', 'logistic')
        self.saturation_multiplier = self.config.get('ramp_up.saturation_multiplier', 1.5)

        self.historical_ramps: Dict[str, pd.DataFrame] = {}
        self.fitted_curves: Dict[str, Dict] = {}
        self.transfer_analyzer = TransferLearningAnalyzer(config)
        self.product_features: pd.DataFrame = pd.DataFrame()

    @staticmethod
    def logistic_curve(t: np.ndarray, L: float, k: float, t0: float) -> np.ndarray:
        return L / (1 + np.exp(-k * (t - t0)))

    @staticmethod
    def gompertz_curve(t: np.ndarray, L: float, k: float, t0: float) -> np.ndarray:
        return L * np.exp(-np.exp(-k * (t - t0)))

    @staticmethod
    def richards_curve(t: np.ndarray, L: float, k: float, t0: float, m: float) -> np.ndarray:
        return L * (1 + m * np.exp(-k * (t - t0))) ** (-1 / m)

    @staticmethod
    def exponential_curve(t: np.ndarray, L: float, k: float, t0: float) -> np.ndarray:
        return L * (1 - np.exp(-k * (t - t0)))

    def _get_growth_curve(self, curve_type: str):
        curves = {
            'logistic': self.logistic_curve,
            'gompertz': self.gompertz_curve,
            'richards': self.richards_curve,
            'exponential': self.exponential_curve
        }
        return curves.get(curve_type, self.logistic_curve)

    def identify_new_products(self, sales_df: pd.DataFrame,
                               product_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Identifying new products for ramp-up analysis...")

        if 'launch_date' not in product_df.columns:
            product_df['launch_date'] = sales_df.groupby('product_id')['date'].min().reset_index()['date']

        today = sales_df['date'].max()
        six_months_ago = today - timedelta(days=180)

        new_products = product_df[
            (pd.to_datetime(product_df['launch_date']) >= six_months_ago) |
            (pd.to_datetime(product_df['launch_date']) <= today)
        ].copy()

        new_products['days_since_launch'] = (today - pd.to_datetime(new_products['launch_date'])).dt.days
        new_products['is_new'] = new_products['days_since_launch'] <= 180

        logger.info(f"Identified {len(new_products[new_products['is_new']])} new products")

        return new_products

    def analyze_historical_ramps(self, sales_df: pd.DataFrame,
                                  product_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        logger.info("Analyzing historical ramp-up patterns...")

        products_with_launch = product_df[product_df['launch_date'].notna()].copy()
        products_with_launch['launch_date'] = pd.to_datetime(products_with_launch['launch_date'])

        for _, product in products_with_launch.iterrows():
            product_id = product['product_id']
            launch_date = product['launch_date']

            product_sales = sales_df[
                (sales_df['product_id'] == product_id) &
                (sales_df['date'] >= launch_date) &
                (sales_df['date'] <= launch_date + timedelta(days=self.ramp_period * 2))
            ].copy()

            if len(product_sales) < 30:
                continue

            product_sales = product_sales.sort_values('date')
            product_sales['day_of_ramp'] = (product_sales['date'] - launch_date).dt.days

            weekly_sales = product_sales.groupby(
                pd.Grouper(key='date', freq='W')
            )['quantity'].sum().reset_index()
            weekly_sales['week_of_ramp'] = (weekly_sales['date'] - launch_date).dt.days // 7 + 1

            daily_sales = product_sales.groupby('day_of_ramp')['quantity'].sum().reset_index()
            daily_sales['cumulative'] = daily_sales['quantity'].cumsum()
            daily_sales['rolling_mean_7'] = daily_sales['quantity'].rolling(7, min_periods=1).mean()
            daily_sales['growth_rate'] = daily_sales['quantity'].pct_change().fillna(0)

            self.historical_ramps[product_id] = {
                'daily': daily_sales,
                'weekly': weekly_sales,
                'launch_date': launch_date,
                'category': product.get('category', 'Unknown')
            }

        logger.info(f"Analyzed {len(self.historical_ramps)} historical product ramps")
        return self.historical_ramps

    def fit_ramp_curve(self, product_id: str, days: np.ndarray,
                       sales: np.ndarray, curve_type: str = None) -> Dict:
        curve_type = curve_type or self.growth_curve_type
        curve_func = self._get_growth_curve(curve_type)

        sales_cumulative = np.cumsum(sales)
        saturation_level = sales_cumulative[-1] * self.saturation_multiplier

        try:
            if curve_type == 'richards':
                p0 = [saturation_level, 0.1, len(days) / 2, 1.0]
                bounds = ([0, 0, 0, 0.1], [np.inf, 1, len(days), 10])
            else:
                p0 = [saturation_level, 0.1, len(days) / 2]
                bounds = ([0, 0, 0], [np.inf, 1, len(days)])

            popt, pcov = curve_fit(
                curve_func, days, sales_cumulative,
                p0=p0, bounds=bounds, maxfev=10000
            )

            perr = np.sqrt(np.diag(pcov)) if pcov is not None else np.zeros(len(popt))

            fitted_values = curve_func(days, *popt)
            residuals = sales_cumulative - fitted_values
            r_squared = 1 - (np.sum(residuals ** 2) / np.sum((sales_cumulative - np.mean(sales_cumulative)) ** 2))

            curve_params = {
                'curve_type': curve_type,
                'params': popt,
                'param_errors': perr,
                'r_squared': r_squared,
                'saturation': popt[0],
                'growth_rate': popt[1],
                'midpoint': popt[2]
            }

            if curve_type == 'richards':
                curve_params['shape'] = popt[3]

            self.fitted_curves[product_id] = curve_params
            logger.info(f"Fitted {curve_type} curve for {product_id} (R² = {r_squared:.4f})")

            return curve_params

        except Exception as e:
            logger.warning(f"Could not fit curve for {product_id}: {e}")
            return {
                'curve_type': curve_type,
                'params': None,
                'r_squared': 0,
                'error': str(e)
            }

    def prepare_transfer_features(self, sales_df: pd.DataFrame,
                                   product_df: pd.DataFrame,
                                   inventory_df: pd.DataFrame = None,
                                   promotion_df: pd.DataFrame = None):
        logger.info("Preparing product features for transfer learning...")

        self.product_features = self.transfer_analyzer.extract_product_features(
            sales_df, product_df, inventory_df, promotion_df
        )

        return self.product_features

    def predict_new_product_ramp_transfer(self, new_product: Dict,
                                           sales_df: pd.DataFrame,
                                           forecast_days: int = 180,
                                           target_initial_sales: pd.DataFrame = None,
                                           use_transfer_learning: bool = True) -> Dict:
        logger.info(f"Predicting ramp-up for new product with transfer learning: {new_product.get('product_id', 'Unknown')}")

        if self.product_features.empty:
            logger.warning("Product features not prepared. Call prepare_transfer_features() first.")
            return {
                'forecast': self._generate_generic_ramp(new_product, forecast_days),
                'method': 'generic',
                'source_products': []
            }

        target_product_id = new_product.get('product_id', 'NEW')
        target_features = {
            'category': new_product.get('category', 'Unknown'),
            'base_demand': new_product.get('base_demand', 100),
            'avg_daily_sales': new_product.get('base_demand', 100),
            'std_daily_sales': new_product.get('base_demand', 100) * 0.2,
            'cv_sales': 0.2,
            'sales_trend': 0,
            'sales_seasonality_strength': 0.3,
        }

        if use_transfer_learning:
            transfer_results = self.transfer_analyzer.transfer_predict(
                target_product_id=target_product_id,
                target_features=target_features,
                target_launch_date=pd.to_datetime(new_product.get('launch_date', datetime.now())),
                all_products_features=self.product_features,
                sales_df=sales_df,
                forecast_days=forecast_days,
                target_initial_sales=target_initial_sales
            )

            if transfer_results is not None:
                forecast_df = transfer_results['forecast']
                forecast_df['phase'] = forecast_df['day_of_ramp'].apply(self._classify_ramp_phase)
                forecast_df['curve_type'] = 'transfer_learning'

                return {
                    'forecast': forecast_df,
                    'method': 'transfer_learning',
                    'source_products': transfer_results['source_products'],
                    'tradaboost_results': transfer_results['tradaboost'],
                    'n_source_products': transfer_results['n_source_products']
                }

        logger.info("Falling back to traditional ramp curve fitting")
        forecast = self.predict_new_product_ramp(new_product, None, forecast_days)

        return {
            'forecast': forecast,
            'method': 'curve_fitting',
            'source_products': []
        }

    def get_transferability_report(self, target_product_features: Dict,
                                    sales_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Generating transferability report for target product...")

        if self.product_features.empty:
            logger.warning("Product features not prepared.")
            return pd.DataFrame()

        report = []
        for source_product_id in self.product_features['product_id']:
            result = self.transfer_analyzer.calculate_transferability(
                source_product_id, target_product_features, sales_df
            )
            report.append(result)

        report_df = pd.DataFrame(report)
        return report_df.sort_values('transferability_score', ascending=False)

    def predict_new_product_ramp(self, new_product: Dict,
                                  similar_products: List[str] = None,
                                  forecast_days: int = 180) -> pd.DataFrame:
        logger.info(f"Predicting ramp-up for new product: {new_product.get('product_id', 'Unknown')}")

        if similar_products is None and 'similar_product_id' in new_product:
            similar_products = [new_product['similar_product_id']]

        if not similar_products or not self.historical_ramps:
            logger.warning("No similar products or historical ramps available. Using generic curve.")
            return self._generate_generic_ramp(new_product, forecast_days)

        ramp_params_list = []
        for sim_product in similar_products:
            if sim_product in self.historical_ramps:
                daily_data = self.historical_ramps[sim_product]['daily']

                days = daily_data['day_of_ramp'].values
                sales = daily_data['quantity'].values

                curve_params = self.fit_ramp_curve(sim_product, days, sales)
                if curve_params.get('params') is not None:
                    ramp_params_list.append(curve_params)

        if not ramp_params_list:
            return self._generate_generic_ramp(new_product, forecast_days)

        avg_params = self._average_curve_params(ramp_params_list)
        base_demand = new_product.get('base_demand', 100)

        return self._generate_ramp_forecast(
            new_product, avg_params, base_demand, forecast_days
        )

    def _average_curve_params(self, params_list: List[Dict]) -> Dict:
        if not params_list:
            return {}

        saturation = np.mean([p['saturation'] for p in params_list])
        growth_rate = np.mean([p['growth_rate'] for p in params_list])
        midpoint = np.mean([p['midpoint'] for p in params_list])
        r_squared = np.mean([p.get('r_squared', 0) for p in params_list])

        return {
            'curve_type': params_list[0]['curve_type'],
            'saturation': saturation,
            'growth_rate': growth_rate,
            'midpoint': midpoint,
            'r_squared': r_squared
        }

    def _generate_generic_ramp(self, new_product: Dict, forecast_days: int) -> pd.DataFrame:
        logger.info("Generating generic ramp-up forecast...")

        launch_date = pd.to_datetime(new_product.get('launch_date', datetime.now()))
        base_demand = new_product.get('base_demand', 100)

        dates = pd.date_range(start=launch_date, periods=forecast_days, freq='D')
        days = np.arange(forecast_days)

        saturation = base_demand * 30 * self.saturation_multiplier
        growth_rate = 0.05
        midpoint = self.ramp_period / 2

        cumulative_forecast = self.logistic_curve(days, saturation, growth_rate, midpoint)
        daily_forecast = np.diff(cumulative_forecast, prepend=0)

        std_dev = daily_forecast * 0.2
        lower = np.maximum(0, daily_forecast - 1.96 * std_dev)
        upper = daily_forecast + 1.96 * std_dev

        return self._create_ramp_dataframe(
            dates, daily_forecast, lower, upper, cumulative_forecast,
            {'curve_type': 'logistic', 'saturation': saturation,
             'growth_rate': growth_rate, 'midpoint': midpoint,
             'is_generic': True}
        )

    def _generate_ramp_forecast(self, new_product: Dict, params: Dict,
                                 base_demand: float, forecast_days: int) -> pd.DataFrame:
        launch_date = pd.to_datetime(new_product.get('launch_date', datetime.now()))
        dates = pd.date_range(start=launch_date, periods=forecast_days, freq='D')
        days = np.arange(forecast_days)

        curve_func = self._get_growth_curve(params['curve_type'])

        scale_factor = (base_demand * 30) / (params['saturation'] / self.saturation_multiplier)
        adjusted_saturation = params['saturation'] * scale_factor

        if params['curve_type'] == 'richards':
            cumulative_forecast = curve_func(
                days, adjusted_saturation, params['growth_rate'],
                params['midpoint'], params.get('shape', 1.0)
            )
        else:
            cumulative_forecast = curve_func(
                days, adjusted_saturation, params['growth_rate'], params['midpoint']
            )

        daily_forecast = np.diff(cumulative_forecast, prepend=0)

        std_dev = daily_forecast * 0.15
        lower = np.maximum(0, daily_forecast - 1.96 * std_dev)
        upper = daily_forecast + 1.96 * std_dev

        return self._create_ramp_dataframe(
            dates, daily_forecast, lower, upper, cumulative_forecast, params
        )

    def _create_ramp_dataframe(self, dates: pd.DatetimeIndex, forecast: np.ndarray,
                                lower: np.ndarray, upper: np.ndarray,
                                cumulative: np.ndarray, params: Dict) -> pd.DataFrame:
        df = pd.DataFrame({
            'date': dates,
            'day_of_ramp': np.arange(len(dates)),
            'forecast': forecast,
            'forecast_lower': lower,
            'forecast_upper': upper,
            'cumulative_forecast': cumulative,
            'curve_type': params['curve_type'],
            'saturation_level': params['saturation'],
            'growth_rate': params['growth_rate'],
            'midpoint_day': params['midpoint'],
            'r_squared': params.get('r_squared', np.nan),
            'is_generic': params.get('is_generic', False)
        })

        df['phase'] = df['day_of_ramp'].apply(self._classify_ramp_phase)

        return df

    def _classify_ramp_phase(self, day: int) -> str:
        if day < 14:
            return 'launch'
        elif day < 30:
            return 'early_growth'
        elif day < 60:
            return 'rapid_growth'
        elif day < 90:
            return 'late_growth'
        else:
            return 'mature'

    def get_ramp_metrics(self, ramp_df: pd.DataFrame) -> Dict:
        if ramp_df.empty:
            return {}

        launch_phase = ramp_df[ramp_df['phase'] == 'launch']
        early_phase = ramp_df[ramp_df['phase'] == 'early_growth']
        rapid_phase = ramp_df[ramp_df['phase'] == 'rapid_growth']

        metrics = {
            'total_forecast_90d': ramp_df[ramp_df['day_of_ramp'] < 90]['forecast'].sum(),
            'total_forecast_180d': ramp_df['forecast'].sum(),
            'peak_daily_demand': ramp_df['forecast'].max(),
            'peak_day': ramp_df.loc[ramp_df['forecast'].idxmax(), 'day_of_ramp'],
            'avg_launch_phase': launch_phase['forecast'].mean() if not launch_phase.empty else 0,
            'avg_early_growth': early_phase['forecast'].mean() if not early_phase.empty else 0,
            'avg_rapid_growth': rapid_phase['forecast'].mean() if not rapid_phase.empty else 0,
            'growth_rate_launch_to_early': 0,
            'days_to_80_penetration': self._find_days_to_penetration(ramp_df, 0.8)
        }

        if metrics['avg_launch_phase'] > 0:
            metrics['growth_rate_launch_to_early'] = (
                (metrics['avg_early_growth'] - metrics['avg_launch_phase']) /
                metrics['avg_launch_phase'] * 100
            )

        return metrics

    def _find_days_to_penetration(self, ramp_df: pd.DataFrame, penetration: float) -> int:
        total = ramp_df['cumulative_forecast'].iloc[-1]
        target = total * penetration

        mask = ramp_df['cumulative_forecast'] >= target
        if mask.any():
            return ramp_df[mask].iloc[0]['day_of_ramp']
        return len(ramp_df)

    def compare_ramps(self, product_ids: List[str]) -> pd.DataFrame:
        comparison_data = []

        for product_id in product_ids:
            if product_id in self.historical_ramps:
                ramp_data = self.historical_ramps[product_id]['daily']
                metrics = self.get_ramp_metrics(ramp_data)
                metrics['product_id'] = product_id
                metrics['category'] = self.historical_ramps[product_id]['category']
                comparison_data.append(metrics)

        return pd.DataFrame(comparison_data)

    def plot_ramp_curves(self, product_ids: List[str], new_product_forecast: pd.DataFrame = None):
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 1, figsize=(12, 10))

            for product_id in product_ids:
                if product_id in self.historical_ramps:
                    ramp_data = self.historical_ramps[product_id]['daily']
                    axes[0].plot(ramp_data['day_of_ramp'], ramp_data['quantity'],
                                 label=f'{product_id} (Actual)', alpha=0.7)
                    axes[1].plot(ramp_data['day_of_ramp'], ramp_data['cumulative'],
                                 label=f'{product_id} (Actual)', alpha=0.7)

            if new_product_forecast is not None:
                axes[0].plot(new_product_forecast['day_of_ramp'],
                             new_product_forecast['forecast'],
                             label='New Product (Forecast)', linewidth=2, color='red')
                axes[0].fill_between(new_product_forecast['day_of_ramp'],
                                     new_product_forecast['forecast_lower'],
                                     new_product_forecast['forecast_upper'],
                                     alpha=0.2, color='red')

                axes[1].plot(new_product_forecast['day_of_ramp'],
                             new_product_forecast['cumulative_forecast'],
                             label='New Product (Forecast)', linewidth=2, color='red')

            axes[0].set_xlabel('Day of Ramp')
            axes[0].set_ylabel('Daily Sales')
            axes[0].set_title('Ramp-Up Comparison - Daily Sales')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)

            axes[1].set_xlabel('Day of Ramp')
            axes[1].set_ylabel('Cumulative Sales')
            axes[1].set_title('Ramp-Up Comparison - Cumulative Sales')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)

            plt.tight_layout()
            return plt
        except Exception as e:
            logger.warning(f"Could not plot ramp curves: {e}")
            return None
