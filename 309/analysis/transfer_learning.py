import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Union
import logging
from datetime import datetime, timedelta
from scipy.spatial.distance import cdist, mahalanobis
from scipy.stats import wasserstein_distance, ks_2samp
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransferLearningAnalyzer:
    def __init__(self, config: Optional[Dict] = None):
        from config import Config
        self.config = config or Config().config
        self.transfer_config = self.config.get('transfer_learning', {})
        self.max_source_products = self.transfer_config.get('max_source_products', 5)
        self.similarity_threshold = self.transfer_config.get('similarity_threshold', 0.3)
        self.tradaboost_iterations = self.transfer_config.get('tradaboost_iterations', 10)
        self.transfer_weight = self.transfer_config.get('transfer_weight', 0.7)

        self.source_products_data: Dict[str, pd.DataFrame] = {}
        self.product_features: Dict[str, pd.DataFrame] = {}
        self.similarity_matrix: pd.DataFrame = pd.DataFrame()
        self.transfer_weights: Dict[str, float] = {}

    def extract_product_features(self, sales_df: pd.DataFrame,
                                  product_df: pd.DataFrame,
                                  inventory_df: pd.DataFrame = None,
                                  promotion_df: pd.DataFrame = None) -> pd.DataFrame:
        logger.info("Extracting product features for similarity analysis...")

        product_ids = product_df['product_id'].unique()
        features_list = []

        for product_id in product_ids:
            product_sales = sales_df[sales_df['product_id'] == product_id].copy()
            product_info = product_df[product_df['product_id'] == product_id].iloc[0]

            if len(product_sales) < 30:
                continue

            features = {
                'product_id': product_id,
                'category': product_info.get('category', 'Unknown'),
                'launch_days': (
                    product_sales['date'].max() - pd.to_datetime(product_info.get('launch_date', product_sales['date'].min()))
                ).days,
                'avg_daily_sales': product_sales['quantity'].mean(),
                'std_daily_sales': product_sales['quantity'].std(),
                'cv_sales': product_sales['quantity'].std() / (product_sales['quantity'].mean() + 1e-6),
                'median_daily_sales': product_sales['quantity'].median(),
                'max_daily_sales': product_sales['quantity'].max(),
                'min_daily_sales': product_sales['quantity'].min(),
                'total_sales': product_sales['quantity'].sum(),
                'sales_trend': self._calculate_trend(product_sales),
                'sales_seasonality_strength': self._calculate_seasonality_strength(product_sales),
                'peak_day_of_week': product_sales.groupby(product_sales['date'].dt.dayofweek)['quantity'].mean().idxmax(),
                'coef_of_var_weekly': self._calculate_weekly_cv(product_sales),
                'growth_rate_30d': self._calculate_growth_rate(product_sales, window=30),
                'growth_rate_90d': self._calculate_growth_rate(product_sales, window=90),
            }

            if inventory_df is not None:
                product_inv = inventory_df[inventory_df['product_id'] == product_id]
                if len(product_inv) > 0:
                    features.update({
                        'avg_inventory': product_inv['stock_quantity'].mean(),
                        'avg_stock_turnover': product_sales['quantity'].mean() / (product_inv['stock_quantity'].mean() + 1e-6),
                    })

            if promotion_df is not None:
                product_promo = promotion_df[promotion_df['product_id'] == product_id]
                if len(product_promo) > 0:
                    promo_dates = []
                    for _, row in product_promo.iterrows():
                        promo_dates.extend(pd.date_range(row['start_date'], row['end_date']))
                    promo_dates = set(promo_dates)
                    product_sales['is_promo'] = product_sales['date'].isin(promo_dates)

                    promo_sales = product_sales[product_sales['is_promo']]['quantity'].mean() if product_sales['is_promo'].any() else 0
                    non_promo_sales = product_sales[~product_sales['is_promo']]['quantity'].mean() if (~product_sales['is_promo']).any() else 1

                    features.update({
                        'promo_elasticity': promo_sales / non_promo_sales if non_promo_sales > 0 else 1,
                        'promo_frequency': len(product_promo) / (len(product_sales) / 30),
                    })

            features_list.append(features)

        features_df = pd.DataFrame(features_list)

        for col in features_df.select_dtypes(include=[np.number]).columns:
            if col != 'product_id':
                features_df[col] = features_df[col].fillna(features_df[col].median())

        logger.info(f"Extracted features for {len(features_df)} products")
        return features_df

    def _calculate_trend(self, sales_df: pd.DataFrame) -> float:
        if len(sales_df) < 60:
            return 0

        monthly = sales_df.groupby(pd.Grouper(key='date', freq='ME'))['quantity'].sum()
        if len(monthly) < 3:
            return 0

        x = np.arange(len(monthly))
        y = monthly.values
        slope = np.polyfit(x, y, 1)[0]
        return slope / (np.mean(y) + 1e-6)

    def _calculate_seasonality_strength(self, sales_df: pd.DataFrame) -> float:
        if len(sales_df) < 60:
            return 0

        daily = sales_df.set_index('date')['quantity']
        weekly_avg = daily.rolling(7, min_periods=1).mean()
        detrended = daily - weekly_avg

        day_of_week_effect = detrended.groupby(detrended.index.dayofweek).mean()
        seasonality_strength = np.var(day_of_week_effect) / (np.var(detrended) + 1e-6)

        return min(1, seasonality_strength)

    def _calculate_weekly_cv(self, sales_df: pd.DataFrame) -> float:
        weekly = sales_df.groupby(pd.Grouper(key='date', freq='W'))['quantity'].sum()
        return weekly.std() / (weekly.mean() + 1e-6)

    def _calculate_growth_rate(self, sales_df: pd.DataFrame, window: int = 30) -> float:
        if len(sales_df) < window * 2:
            return 0

        recent = sales_df.tail(window)['quantity'].mean()
        earlier = sales_df.head(window)['quantity'].mean()

        if earlier > 0:
            return (recent - earlier) / earlier
        return 0

    def calculate_similarity(self, target_product_features: Dict,
                              source_products_features: pd.DataFrame,
                              weight_scheme: str = 'entropy') -> pd.DataFrame:
        logger.info(f"Calculating similarity to target product...")

        feature_cols = source_products_features.select_dtypes(include=[np.number]).columns.tolist()
        if 'product_id' in feature_cols:
            feature_cols.remove('product_id')

        target_vector = np.array([target_product_features.get(col, 0) for col in feature_cols]).reshape(1, -1)
        source_matrix = source_products_features[feature_cols].values

        if weight_scheme == 'entropy':
            weights = self._entropy_weights(source_matrix)
        elif weight_scheme == 'equal':
            weights = np.ones(len(feature_cols)) / len(feature_cols)
        elif weight_scheme == 'variance':
            weights = np.std(source_matrix, axis=0)
            weights = weights / (weights.sum() + 1e-6)
        else:
            weights = np.ones(len(feature_cols)) / len(feature_cols)

        weighted_source = source_matrix * weights
        weighted_target = target_vector * weights

        euclidean_dist = cdist(weighted_target, weighted_source, 'euclidean')[0]
        manhattan_dist = cdist(weighted_target, weighted_source, 'cityblock')[0]
        cosine_dist = cdist(weighted_target, weighted_source, 'cosine')[0]

        euclidean_sim = 1 / (1 + euclidean_dist)
        manhattan_sim = 1 / (1 + manhattan_dist)
        cosine_sim = 1 - cosine_dist

        combined_sim = 0.4 * euclidean_sim + 0.2 * manhattan_sim + 0.4 * cosine_sim

        category_match = source_products_features['category'].apply(
            lambda x: 1 if x == target_product_features.get('category', '') else 0.3
        ).values

        final_sim = combined_sim * 0.7 + category_match * 0.3

        similarity_df = source_products_features.copy()
        similarity_df['similarity_score'] = final_sim
        similarity_df['euclidean_similarity'] = euclidean_sim
        similarity_df['cosine_similarity'] = cosine_sim
        similarity_df['category_match'] = category_match

        similarity_df = similarity_df.sort_values('similarity_score', ascending=False)

        return similarity_df

    def _entropy_weights(self, matrix: np.ndarray) -> np.ndarray:
        n, m = matrix.shape

        norm_matrix = matrix / (matrix.sum(axis=0) + 1e-6)

        epsilon = 1e-12
        log_matrix = np.log(norm_matrix + epsilon)
        entropy = -np.sum(norm_matrix * log_matrix, axis=0) / np.log(n + epsilon)

        weights = (1 - entropy) / (np.sum(1 - entropy) + 1e-6)

        return weights

    def select_source_products(self, target_product_features: Dict,
                                all_products_features: pd.DataFrame,
                                target_product_id: str = None,
                                method: str = 'hybrid') -> List[Tuple[str, float]]:
        logger.info(f"Selecting source products for transfer learning...")

        if target_product_id is not None:
            all_products_features = all_products_features[
                all_products_features['product_id'] != target_product_id
            ]

        similarity_df = self.calculate_similarity(target_product_features, all_products_features)

        similarity_df = similarity_df[similarity_df['similarity_score'] >= self.similarity_threshold]

        if method == 'similarity':
            selected = similarity_df.head(self.max_source_products)
        elif method == 'diversity':
            selected = self._diverse_selection(similarity_df, self.max_source_products)
        elif method == 'hybrid':
            top_sim = similarity_df.head(self.max_source_products * 2)
            selected = self._diverse_selection(top_sim, self.max_source_products)
        else:
            selected = similarity_df.head(self.max_source_products)

        source_products = list(zip(selected['product_id'], selected['similarity_score']))

        logger.info(f"Selected {len(source_products)} source products")
        for product_id, score in source_products:
            logger.info(f"  - {product_id}: similarity = {score:.4f}")

        return source_products

    def _diverse_selection(self, candidates: pd.DataFrame, n: int) -> pd.DataFrame:
        if len(candidates) <= n:
            return candidates

        feature_cols = candidates.select_dtypes(include=[np.number]).columns.tolist()
        if 'product_id' in feature_cols:
            feature_cols.remove('product_id')
        if 'similarity_score' in feature_cols:
            feature_cols.remove('similarity_score')

        selected = [candidates.iloc[0]]
        remaining = candidates.iloc[1:]

        while len(selected) < n and len(remaining) > 0:
            selected_matrix = np.array([s[feature_cols].values for s in selected])
            remaining_matrix = remaining[feature_cols].values

            min_distances = np.min(cdist(remaining_matrix, selected_matrix), axis=1)
            scores = remaining['similarity_score'].values * 0.5 + min_distances * 0.5

            best_idx = np.argmax(scores)
            selected.append(remaining.iloc[best_idx])
            remaining = remaining.drop(remaining.index[best_idx])

        return pd.DataFrame(selected)

    def align_source_data(self, source_product_id: str,
                          source_sales_df: pd.DataFrame,
                          target_launch_date: datetime,
                          time_align_method: str = 'launch_date') -> pd.DataFrame:
        logger.info(f"Aligning source product {source_product_id} data to target...")

        source_launch = source_sales_df['date'].min()

        if time_align_method == 'launch_date':
            source_sales_aligned = source_sales_df.copy()
            source_sales_aligned['date'] = (
                target_launch_date + (source_sales_aligned['date'] - source_launch)
            )
            source_sales_aligned['day_of_ramp'] = (
                source_sales_aligned['date'] - target_launch_date
            ).dt.days

        elif time_align_method == 'growth_stage':
            source_sales_aligned = self._align_by_growth_stage(
                source_sales_df, target_launch_date
            )

        elif time_align_method == 'dynamic_time_warping':
            source_sales_aligned = self._align_by_dtw(
                source_sales_df, target_launch_date
            )

        else:
            source_sales_aligned = source_sales_df.copy()
            source_sales_aligned['date'] = (
                target_launch_date + (source_sales_aligned['date'] - source_launch)
            )
            source_sales_aligned['day_of_ramp'] = (
                source_sales_aligned['date'] - target_launch_date
            ).dt.days

        return source_sales_aligned

    def _align_by_growth_stage(self, source_sales_df: pd.DataFrame,
                                target_launch_date: datetime) -> pd.DataFrame:
        source_sales = source_sales_df.copy()
        source_sales['day_of_ramp'] = (source_sales['date'] - source_sales['date'].min()).dt.days

        source_sales['rolling_mean'] = source_sales['quantity'].rolling(7, min_periods=1).mean()
        source_sales['growth_rate'] = source_sales['rolling_mean'].pct_change().fillna(0)

        stages = []
        current_stage = 0
        for i in range(1, len(source_sales)):
            if source_sales.iloc[i]['growth_rate'] > 0.1:
                current_stage = 1
            elif source_sales.iloc[i]['growth_rate'] < -0.05 and current_stage >= 1:
                current_stage = 2

            stages.append(current_stage)

        stages = [0] + stages
        source_sales['growth_stage'] = stages

        source_sales['date'] = target_launch_date + pd.to_timedelta(source_sales['day_of_ramp'], unit='D')

        return source_sales

    def _align_by_dtw(self, source_sales_df: pd.DataFrame,
                       target_launch_date: datetime) -> pd.DataFrame:
        source_sales = source_sales_df.copy()
        source_sales['day_of_ramp'] = (source_sales['date'] - source_sales['date'].min()).dt.days

        source_sales['smoothed'] = source_sales['quantity'].rolling(7, min_periods=1).mean()

        source_sales['normalized'] = (
            source_sales['smoothed'] - source_sales['smoothed'].min()
        ) / (source_sales['smoothed'].max() - source_sales['smoothed'].min() + 1e-6)

        n = len(source_sales)
        dtw_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                dtw_matrix[i, j] = np.abs(source_sales.iloc[i]['normalized'] - source_sales.iloc[j]['normalized'])

        path = [[0, 0]]
        i, j = 0, 0
        while i < n - 1 and j < n - 1:
            candidates = [(i + 1, j), (i, j + 1), (i + 1, j + 1)]
            costs = [dtw_matrix[c] for c in candidates]
            best = candidates[np.argmin(costs)]
            i, j = best
            path.append([i, j])

        warped_indices = [p[1] for p in path]
        aligned_sales = source_sales.iloc[warped_indices].copy()
        aligned_sales['day_of_ramp'] = np.arange(len(aligned_sales))
        aligned_sales['date'] = target_launch_date + pd.to_timedelta(aligned_sales['day_of_ramp'], unit='D')

        return aligned_sales

    def tradaboost(self, target_initial_data: pd.DataFrame,
                    source_data_list: List[pd.DataFrame],
                    source_weights: List[float],
                    n_iterations: int = None) -> Dict:
        logger.info("Running TrAdaBoost for transfer learning...")
        n_iterations = n_iterations or self.tradaboost_iterations

        target_data = target_initial_data.copy()
        target_data['is_source'] = 0

        all_source_data = []
        for i, source_df in enumerate(source_data_list):
            source_df = source_df.copy()
            source_df['is_source'] = 1
            source_df['source_idx'] = i
            source_df['initial_weight'] = source_weights[i]
            all_source_data.append(source_df)

        if not all_source_data:
            logger.warning("No source data available for TrAdaBoost")
            return {
                'weights': pd.Series([1.0] * len(target_data)),
                'beta': 0.5,
                'predictions': None
            }

        source_combined = pd.concat(all_source_data, ignore_index=True)

        combined_data = pd.concat([target_data, source_combined], ignore_index=True)

        n_target = len(target_data)
        n_source = len(source_combined)
        n_total = n_target + n_source

        weights = np.ones(n_total) / n_total

        if 'source_idx' in source_combined.columns:
            for i in range(n_source):
                weights[n_target + i] = source_combined.iloc[i]['initial_weight']

        weights = weights / weights.sum()

        beta = 1 / (1 + np.sqrt(2 * np.log(n_source) / n_iterations))

        iteration_errors = []

        for iteration in range(n_iterations):
            p = weights / weights.sum()

            target_mask = combined_data['is_source'] == 0

            predictions = self._base_learner_predict(combined_data, p, target_mask)

            if predictions is None:
                break

            errors = np.abs(combined_data['quantity'].values - predictions) / (np.abs(combined_data['quantity'].values) + 1e-6)
            errors = np.minimum(errors, 1)

            target_error = np.sum(errors[target_mask] * p[target_mask]) / np.sum(p[target_mask])

            if target_error >= 0.5 or target_error == 0:
                break

            alpha = target_error / (1 - target_error)

            for i in range(n_total):
                if combined_data.iloc[i]['is_source'] == 1:
                    weights[i] = weights[i] * (beta ** errors[i])
                else:
                    weights[i] = weights[i] * (alpha ** (-errors[i]))

            iteration_errors.append(target_error)

            if target_error < 0.01:
                break

        final_weights = pd.Series(weights, index=combined_data.index)

        return {
            'weights': final_weights,
            'beta': beta,
            'errors': iteration_errors,
            'final_alpha': alpha if 'alpha' in locals() else 0.5,
            'n_iterations': len(iteration_errors)
        }

    def _base_learner_predict(self, data: pd.DataFrame, weights: np.ndarray,
                               target_mask: np.ndarray) -> np.ndarray:
        try:
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.preprocessing import StandardScaler

            features = self._prepare_learning_features(data)

            if len(features.columns) < 2:
                return np.full(len(data), data['quantity'].mean())

            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            target_indices = np.where(target_mask)[0]

            if len(target_indices) < 5:
                train_indices = np.arange(len(data))
            else:
                train_indices = np.concatenate([
                    target_indices,
                    np.where(~target_mask)[0][:50]
                ])

            model = GradientBoostingRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )

            sample_weights = weights[train_indices]
            sample_weights = sample_weights / sample_weights.sum() * len(sample_weights)

            model.fit(
                features_scaled[train_indices],
                data.iloc[train_indices]['quantity'],
                sample_weight=sample_weights
            )

            predictions = model.predict(features_scaled)
            return predictions

        except Exception as e:
            logger.warning(f"Base learner prediction failed: {e}")
            return np.full(len(data), data['quantity'].mean())

    def _prepare_learning_features(self, data: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame()

        if 'day_of_ramp' in data.columns:
            features['day_of_ramp'] = data['day_of_ramp']
            features['day_of_ramp_squared'] = data['day_of_ramp'] ** 2
            features['log_day'] = np.log(data['day_of_ramp'] + 1)

        if 'is_promotion' in data.columns:
            features['is_promotion'] = data['is_promotion'].astype(int)

        if 'promotion_discount' in data.columns:
            features['promotion_discount'] = data['promotion_discount'].fillna(0)

        if 'is_holiday' in data.columns:
            features['is_holiday'] = data['is_holiday'].astype(int)

        if 'day_of_week' not in data.columns and 'date' in data.columns:
            features['day_of_week'] = pd.to_datetime(data['date']).dt.dayofweek
            features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)

        return features

    def transfer_predict(self, target_product_id: str,
                         target_features: Dict,
                         target_launch_date: datetime,
                         all_products_features: pd.DataFrame,
                         sales_df: pd.DataFrame,
                         forecast_days: int = 180,
                         target_initial_sales: pd.DataFrame = None) -> Dict:
        logger.info(f"Running transfer learning prediction for {target_product_id}...")

        source_products = self.select_source_products(
            target_features, all_products_features, target_product_id
        )

        if not source_products:
            logger.warning("No source products found, cannot perform transfer learning")
            return None

        source_data_list = []
        source_weight_list = []

        for source_product_id, similarity_score in source_products:
            source_sales = sales_df[sales_df['product_id'] == source_product_id].copy()

            if len(source_sales) < 30:
                continue

            aligned_source = self.align_source_data(
                source_product_id, source_sales, target_launch_date
            )

            source_data_list.append(aligned_source)
            source_weight_list.append(similarity_score)

        if not source_data_list:
            return None

        if target_initial_sales is not None and len(target_initial_sales) >= 14:
            tradaboost_results = self.tradaboost(
                target_initial_sales, source_data_list, source_weight_list
            )
        else:
            tradaboost_results = None

        forecast = self._generate_transfer_forecast(
            source_data_list, source_weight_list, target_launch_date, forecast_days,
            target_features, tradaboost_results
        )

        return {
            'forecast': forecast,
            'source_products': source_products,
            'source_weights': source_weight_list,
            'tradaboost': tradaboost_results,
            'n_source_products': len(source_data_list)
        }

    def _generate_transfer_forecast(self, source_data_list: List[pd.DataFrame],
                                     source_weights: List[float],
                                     target_launch_date: datetime,
                                     forecast_days: int,
                                     target_features: Dict,
                                     tradaboost_results: Dict = None) -> pd.DataFrame:
        dates = pd.date_range(start=target_launch_date, periods=forecast_days, freq='D')
        forecast_df = pd.DataFrame({'date': dates, 'day_of_ramp': np.arange(forecast_days)})

        all_forecasts = []

        for i, (source_data, weight) in enumerate(zip(source_data_list, source_weights)):
            ramp_data = source_data.groupby('day_of_ramp')['quantity'].mean().reset_index()
            ramp_data = ramp_data[ramp_data['day_of_ramp'] < forecast_days]

            if len(ramp_data) < forecast_days:
                last_value = ramp_data['quantity'].iloc[-1] if len(ramp_data) > 0 else target_features.get('base_demand', 100)
                for day in range(len(ramp_data), forecast_days):
                    ramp_data = pd.concat([
                        ramp_data,
                        pd.DataFrame([{'day_of_ramp': day, 'quantity': last_value}])
                    ], ignore_index=True)

            scale_factor = target_features.get('base_demand', 100) / (ramp_data['quantity'].iloc[7:14].mean() + 1e-6)
            scaled_quantity = ramp_data['quantity'].values * scale_factor

            single_forecast = pd.DataFrame({
                'date': dates,
                'day_of_ramp': np.arange(forecast_days),
                'forecast': scaled_quantity,
                'source_idx': i,
                'weight': weight
            })
            all_forecasts.append(single_forecast)

        combined = pd.concat(all_forecasts, ignore_index=True)

        if tradaboost_results is not None:
            for day in range(forecast_days):
                day_mask = combined['day_of_ramp'] == day
                day_data = combined[day_mask]

                adjusted_weights = day_data['weight'].values
                final_weights = adjusted_weights / adjusted_weights.sum()

                combined.loc[day_mask, 'final_weight'] = final_weights
        else:
            total_weight = combined['weight'].sum()
            combined['final_weight'] = combined['weight'] / total_weight if total_weight > 0 else 1 / len(combined)

        weighted_forecast = combined.groupby(['date', 'day_of_ramp']).apply(
            lambda x: np.average(x['forecast'], weights=x['final_weight'])
        ).reset_index()
        weighted_forecast.columns = ['date', 'day_of_ramp', 'forecast']

        std_forecast = combined.groupby(['date', 'day_of_ramp'])['forecast'].std().reset_index()
        std_forecast.columns = ['date', 'day_of_ramp', 'std']

        final_forecast = weighted_forecast.merge(std_forecast, on=['date', 'day_of_ramp'], how='left')
        final_forecast['std'] = final_forecast['std'].fillna(final_forecast['forecast'] * 0.1)

        final_forecast['forecast_lower'] = np.maximum(0, final_forecast['forecast'] - 1.96 * final_forecast['std'])
        final_forecast['forecast_upper'] = final_forecast['forecast'] + 1.96 * final_forecast['std']
        final_forecast['cumulative_forecast'] = final_forecast['forecast'].cumsum()
        final_forecast['is_transfer_learning'] = True

        return final_forecast

    def calculate_transferability(self, source_product_id: str,
                                   target_product_features: Dict,
                                   sales_df: pd.DataFrame) -> Dict:
        logger.info(f"Calculating transferability for {source_product_id}...")

        source_sales = sales_df[sales_df['product_id'] == source_product_id]

        if len(source_sales) < 30:
            return {'transferable': False, 'reason': 'insufficient_data'}

        source_features = {
            'avg_sales': source_sales['quantity'].mean(),
            'std_sales': source_sales['quantity'].std(),
            'cv': source_sales['quantity'].std() / (source_sales['quantity'].mean() + 1e-6),
            'trend': self._calculate_trend(source_sales),
            'seasonality': self._calculate_seasonality_strength(source_sales),
        }

        feature_cols = ['avg_daily_sales', 'std_daily_sales', 'cv_sales', 'sales_trend', 'sales_seasonality_strength']
        target_vector = np.array([target_product_features.get(col, 0) for col in feature_cols]).reshape(1, -1)
        source_vector = np.array([
            source_features['avg_sales'],
            source_features['std_sales'],
            source_features['cv'],
            source_features['trend'],
            source_features['seasonality']
        ]).reshape(1, -1)

        target_normalized = target_vector / (np.linalg.norm(target_vector) + 1e-6)
        source_normalized = source_vector / (np.linalg.norm(source_vector) + 1e-6)

        feature_similarity = np.dot(target_normalized, source_normalized.T)[0][0]

        ks_stat, ks_pvalue = ks_2samp(
            source_sales['quantity'].values,
            np.random.poisson(
                target_product_features.get('avg_daily_sales', 100),
                len(source_sales)
            )
        )

        distribution_similarity = 1 - ks_stat

        transferability_score = feature_similarity * 0.6 + distribution_similarity * 0.4

        return {
            'product_id': source_product_id,
            'transferable': transferability_score > 0.5,
            'transferability_score': transferability_score,
            'feature_similarity': feature_similarity,
            'distribution_similarity': distribution_similarity,
            'ks_statistic': ks_stat,
            'ks_pvalue': ks_pvalue,
            'source_features': source_features,
            'recommendation': 'highly_recommended' if transferability_score > 0.8
            else 'recommended' if transferability_score > 0.6
            else 'use_caution' if transferability_score > 0.4
            else 'not_recommended'
        }

    def domain_adaptation(self, source_data: pd.DataFrame,
                          target_data: pd.DataFrame,
                          method: str = 'coral') -> pd.DataFrame:
        logger.info(f"Performing domain adaptation using {method}...")

        feature_cols = self._prepare_learning_features(source_data).columns
        source_features = self._prepare_learning_features(source_data)[feature_cols].values
        target_features = self._prepare_learning_features(target_data)[feature_cols].values

        if method == 'coral':
            adapted_source = self._coral_adaptation(source_features, target_features)
        elif method == 'mmd':
            adapted_source = self._mmd_adaptation(source_features, target_features)
        else:
            adapted_source = source_features

        adapted_df = source_data.copy()
        for i, col in enumerate(feature_cols):
            adapted_df[col] = adapted_source[:, i]

        return adapted_df

    def _coral_adaptation(self, source: np.ndarray, target: np.ndarray) -> np.ndarray:
        source_mean = source.mean(axis=0)
        target_mean = target.mean(axis=0)

        source_centered = source - source_mean
        target_centered = target - target_mean

        source_cov = np.cov(source_centered, rowvar=False) + np.eye(source.shape[1]) * 1e-3
        target_cov = np.cov(target_centered, rowvar=False) + np.eye(target.shape[1]) * 1e-3

        source_sqrt = self._matrix_sqrt(source_cov)
        source_sqrt_inv = pinv(source_sqrt)
        target_sqrt = self._matrix_sqrt(target_cov)

        M = source_sqrt_inv @ target_sqrt @ source_sqrt_inv

        adapted = source_centered @ M + target_mean

        return adapted

    def _mmd_adaptation(self, source: np.ndarray, target: np.ndarray) -> np.ndarray:
        lambda_param = 0.1
        n_source = len(source)

        kernel_source = self._rbf_kernel(source, source)
        kernel_target = self._rbf_kernel(source, target)

        K = kernel_source
        L = np.zeros((n_source, n_source))

        for i in range(n_source):
            for j in range(n_source):
                L[i, j] = 1.0 / (n_source ** 2)

        M = np.eye(n_source) + lambda_param * np.linalg.pinv(K @ L @ K)
        alpha = M @ kernel_target.mean(axis=1)

        adapted = source.copy()
        for i in range(n_source):
            adapted[i] = adapted[i] * alpha[i]

        return adapted

    def _rbf_kernel(self, X: np.ndarray, Y: np.ndarray, gamma: float = None) -> np.ndarray:
        if gamma is None:
            gamma = 1.0 / X.shape[1]

        X_norm = np.sum(X ** 2, axis=1)
        Y_norm = np.sum(Y ** 2, axis=1)
        K = X_norm[:, None] + Y_norm[None, :] - 2 * X @ Y.T

        return np.exp(-gamma * K)

    def _matrix_sqrt(self, matrix: np.ndarray) -> np.ndarray:
        eigvals, eigvecs = np.linalg.eigh(matrix)
        eigvals = np.maximum(eigvals, 0)
        return eigvecs @ np.diag(np.sqrt(eigvals)) @ eigvecs.T

    def plot_transfer_comparison(self, source_products: List[str],
                                  target_forecast: pd.DataFrame,
                                  sales_df: pd.DataFrame,
                                  target_launch_date: datetime):
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 1, figsize=(14, 10))

            for product_id in source_products:
                source_data = sales_df[sales_df['product_id'] == product_id].copy()
                if len(source_data) > 0:
                    source_data['day_of_ramp'] = (
                        source_data['date'] - source_data['date'].min()
                    ).dt.days

                    axes[0].plot(
                        source_data['day_of_ramp'],
                        source_data['quantity'].rolling(7, min_periods=1).mean(),
                        label=f'Source: {product_id}',
                        alpha=0.6
                    )

                    axes[1].plot(
                        source_data['day_of_ramp'],
                        source_data['quantity'].cumsum(),
                        label=f'Source: {product_id}',
                        alpha=0.6
                    )

            if target_forecast is not None:
                axes[0].plot(
                    target_forecast['day_of_ramp'],
                    target_forecast['forecast'],
                    label='Target (Transfer)',
                    linewidth=2,
                    color='red'
                )
                axes[0].fill_between(
                    target_forecast['day_of_ramp'],
                    target_forecast['forecast_lower'],
                    target_forecast['forecast_upper'],
                    alpha=0.2,
                    color='red'
                )

                axes[1].plot(
                    target_forecast['day_of_ramp'],
                    target_forecast['cumulative_forecast'],
                    label='Target (Transfer)',
                    linewidth=2,
                    color='red'
                )

            axes[0].set_xlabel('Day of Ramp')
            axes[0].set_ylabel('Daily Sales')
            axes[0].set_title('Transfer Learning - Daily Sales Comparison')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)

            axes[1].set_xlabel('Day of Ramp')
            axes[1].set_ylabel('Cumulative Sales')
            axes[1].set_title('Transfer Learning - Cumulative Sales Comparison')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)

            plt.tight_layout()
            return plt

        except Exception as e:
            logger.warning(f"Could not plot transfer comparison: {e}")
            return None
