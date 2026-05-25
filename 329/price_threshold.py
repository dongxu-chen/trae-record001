import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
from scipy import stats
from scipy.signal import find_peaks, argrelextrema


class PriceThresholdDetector:
    
    def __init__(
        self,
        n_clusters: int = 4,
        min_bootstrap_samples: int = 100,
        confidence_level: float = 0.95,
        random_seed: int = 42
    ):
        self.n_clusters = n_clusters
        self.min_bootstrap_samples = min_bootstrap_samples
        self.confidence_level = confidence_level
        self.random_seed = random_seed
        self.thresholds = None
        self.price_segments = None
        self.changepoints = None
        
    def detect_thresholds(
        self,
        df: pd.DataFrame,
        price_col: str = 'effective_price',
        sales_col: str = 'sales_quantity',
        method: str = 'combined'
    ) -> Dict:
        np.random.seed(self.random_seed)
        
        df_clean = df[[price_col, sales_col]].dropna().copy()
        prices = df_clean[price_col].values
        sales = df_clean[sales_col].values
        
        results = {}
        
        if method in ['kmeans', 'combined']:
            kmeans_thresholds = self._detect_kmeans_thresholds(prices, sales)
            results['kmeans'] = kmeans_thresholds
        
        if method in ['changepoint', 'combined']:
            changepoint_thresholds = self._detect_changepoints(prices, sales)
            results['changepoint'] = changepoint_thresholds
        
        if method in ['quantile', 'combined']:
            quantile_thresholds = self._detect_quantile_thresholds(prices, sales)
            results['quantile'] = quantile_thresholds
        
        if method in ['elasticity', 'combined']:
            elasticity_thresholds = self._detect_elasticity_breakpoints(prices, sales)
            results['elasticity'] = elasticity_thresholds
        
        if method == 'combined':
            combined = self._combine_thresholds(results, prices)
            results['combined'] = combined
            self.thresholds = combined
        else:
            self.thresholds = results[method]
        
        self.price_segments = self._build_price_segments(prices, sales, self.thresholds)
        
        return results
    
    def _detect_kmeans_thresholds(self, prices: np.ndarray, sales: np.ndarray) -> Dict:
        price_sales = np.column_stack([prices, sales])
        
        scaler = StandardScaler()
        scaled = scaler.fit_transform(price_sales)
        
        inertias = []
        K = range(2, min(self.n_clusters + 2, 8))
        for k in K:
            km = KMeans(n_clusters=k, random_state=self.random_seed, n_init=10)
            km.fit(scaled)
            inertias.append(km.inertia_)
        
        optimal_k = self.n_clusters
        if len(inertias) > 2:
            diffs = np.diff(inertias)
            elbow_idx = np.argmax(np.abs(diffs[1:] - diffs[:-1]))
            optimal_k = min(optimal_k, elbow_idx + 2)
        
        kmeans = KMeans(n_clusters=optimal_k, random_state=self.random_seed, n_init=10)
        clusters = kmeans.fit_predict(scaled)
        
        cluster_centers = kmeans.cluster_centers_
        cluster_prices = scaler.inverse_transform(cluster_centers)[:, 0]
        
        sorted_indices = np.argsort(cluster_prices)
        sorted_cluster_prices = cluster_prices[sorted_indices]
        
        thresholds = []
        for i in range(len(sorted_cluster_prices) - 1):
            midpoint = (sorted_cluster_prices[i] + sorted_cluster_prices[i + 1]) / 2
            thresholds.append({
                'threshold_price': round(midpoint, 2),
                'lower_center': round(sorted_cluster_prices[i], 2),
                'upper_center': round(sorted_cluster_prices[i + 1], 2),
                'confidence': self._calculate_threshold_confidence(prices, midpoint)
            })
        
        cluster_sales = []
        for cluster_id in sorted_indices:
            mask = clusters == cluster_id
            cluster_sales.append({
                'cluster_id': int(cluster_id),
                'avg_price': np.mean(prices[mask]),
                'avg_sales': np.mean(sales[mask]),
                'std_price': np.std(prices[mask]),
                'std_sales': np.std(sales[mask]),
                'n_points': int(np.sum(mask)),
                'price_range': [np.min(prices[mask]), np.max(prices[mask])]
            })
        
        return {
            'thresholds': sorted(thresholds, key=lambda x: x['threshold_price']),
            'cluster_analysis': cluster_sales,
            'optimal_k': int(optimal_k),
            'method': 'kmeans'
        }
    
    def _detect_changepoints(self, prices: np.ndarray, sales: np.ndarray) -> Dict:
        sorted_indices = np.argsort(prices)
        sorted_prices = prices[sorted_indices]
        sorted_sales = sales[sorted_indices]
        
        window_size = max(5, len(prices) // 10)
        
        rolling_corr = []
        for i in range(window_size, len(sorted_prices) - window_size):
            left_prices = sorted_prices[i-window_size:i]
            left_sales = sorted_sales[i-window_size:i]
            right_prices = sorted_prices[i:i+window_size]
            right_sales = sorted_sales[i:i+window_size]
            
            if len(left_prices) >= 3 and len(right_prices) >= 3:
                left_corr, _ = stats.pearsonr(left_prices, left_sales)
                right_corr, _ = stats.pearsonr(right_prices, right_sales)
                corr_diff = abs(right_corr - left_corr)
                rolling_corr.append((i, sorted_prices[i], corr_diff, left_corr, right_corr))
        
        if len(rolling_corr) == 0:
            return {'thresholds': [], 'changepoints': [], 'method': 'changepoint'}
        
        rc_df = pd.DataFrame(rolling_corr, columns=['idx', 'price', 'corr_diff', 'left_corr', 'right_corr'])
        
        peaks, properties = find_peaks(rc_df['corr_diff'].values, prominence=0.1, distance=window_size)
        
        changepoints = []
        for peak in peaks:
            row = rc_df.iloc[peak]
            changepoints.append({
                'threshold_price': round(row['price'], 2),
                'correlation_change': round(row['corr_diff'], 3),
                'left_correlation': round(row['left_corr'], 3),
                'right_correlation': round(row['right_corr'], 3),
                'confidence': min(0.99, row['corr_diff'] / 0.8)
            })
        
        changepoints = sorted(changepoints, key=lambda x: x['correlation_change'], reverse=True)[:5]
        changepoints = sorted(changepoints, key=lambda x: x['threshold_price'])
        
        return {
            'thresholds': changepoints,
            'method': 'changepoint'
        }
    
    def _detect_quantile_thresholds(self, prices: np.ndarray, sales: np.ndarray) -> Dict:
        sales_percentiles = np.percentile(sales, [25, 50, 75])
        
        thresholds = []
        for i, pct in enumerate([25, 50, 75]):
            mask = sales >= sales_percentiles[i]
            if np.sum(mask) > 5:
                threshold_price = np.percentile(prices[mask], 20)
                thresholds.append({
                    'threshold_price': round(threshold_price, 2),
                    'sales_quantile': pct,
                    'sales_threshold': round(sales_percentiles[i], 1),
                    'confidence': 0.7 + (i * 0.1)
                })
        
        sorted_indices = np.argsort(prices)
        sorted_sales = sales[sorted_indices]
        
        sales_derivative = np.diff(sorted_sales) / np.diff(prices[sorted_indices])
        
        peaks, _ = find_peaks(-sales_derivative, distance=len(prices) // 5)
        
        for peak in peaks:
            threshold_price = prices[sorted_indices][peak + 1]
            thresholds.append({
                'threshold_price': round(threshold_price, 2),
                'sales_quantile': None,
                'sales_threshold': None,
                'confidence': 0.6,
                'from_derivative': True
            })
        
        return {
            'thresholds': sorted(thresholds, key=lambda x: x['threshold_price']),
            'method': 'quantile'
        }
    
    def _detect_elasticity_breakpoints(self, prices: np.ndarray, sales: np.ndarray) -> Dict:
        log_prices = np.log(prices)
        log_sales = np.log(sales)
        
        sorted_indices = np.argsort(log_prices)
        sorted_log_prices = log_prices[sorted_indices]
        sorted_log_sales = log_sales[sorted_indices]
        
        window = max(10, len(prices) // 8)
        step = max(3, window // 3)
        
        elasticities = []
        for i in range(0, len(sorted_log_prices) - window, step):
            window_prices = sorted_log_prices[i:i+window]
            window_sales = sorted_log_sales[i:i+window]
            
            if len(window_prices) >= 5:
                try:
                    X = sm.add_constant(window_prices)
                    model = sm.OLS(window_sales, X).fit()
                    elasticity = model.params[1]
                    mid_price = np.exp(np.mean(window_prices))
                    
                    elasticities.append({
                        'price': mid_price,
                        'elasticity': elasticity,
                        'n_points': len(window_prices),
                        'p_value': model.pvalues[1],
                        'significant': model.pvalues[1] < 0.05
                    })
                except Exception:
                    continue
        
        if len(elasticities) < 2:
            return {'thresholds': [], 'elasticity_profile': elasticities, 'method': 'elasticity'}
        
        elast_df = pd.DataFrame(elasticities)
        
        elast_changes = np.diff(elast_df['elasticity'].values)
        change_threshold = np.std(elast_changes) * 1.5
        
        breakpoints = []
        for i, change in enumerate(elast_changes):
            if abs(change) > change_threshold:
                breakpoints.append({
                    'threshold_price': round(elast_df['price'].iloc[i + 1], 2),
                    'elasticity_change': round(change, 3),
                    'elasticity_before': round(elast_df['elasticity'].iloc[i], 3),
                    'elasticity_after': round(elast_df['elasticity'].iloc[i + 1], 3),
                    'confidence': min(0.95, abs(change) / (change_threshold * 2))
                })
        
        breakpoints = sorted(breakpoints, key=lambda x: abs(x['elasticity_change']), reverse=True)[:4]
        breakpoints = sorted(breakpoints, key=lambda x: x['threshold_price'])
        
        return {
            'thresholds': breakpoints,
            'elasticity_profile': elast_df.to_dict('records'),
            'method': 'elasticity'
        }
    
    def _combine_thresholds(self, results: Dict, prices: np.ndarray) -> Dict:
        all_thresholds = []
        
        for method_name, method_result in results.items():
            if 'thresholds' in method_result:
                for t in method_result['thresholds']:
                    t_copy = t.copy()
                    t_copy['detection_method'] = method_name
                    all_thresholds.append(t_copy)
        
        if len(all_thresholds) == 0:
            return {'thresholds': [], 'combined': True}
        
        price_range = np.max(prices) - np.min(prices)
        merge_threshold = price_range * 0.03
        
        threshold_df = pd.DataFrame(all_thresholds)
        threshold_df = threshold_df.sort_values('threshold_price')
        
        merged = []
        current_group = [threshold_df.iloc[0]]
        
        for _, row in threshold_df.iloc[1:].iterrows():
            if row['threshold_price'] - current_group[-1]['threshold_price'] < merge_threshold:
                current_group.append(row)
            else:
                avg_price = np.mean([t['threshold_price'] for t in current_group])
                max_confidence = np.max([t.get('confidence', 0.5) for t in current_group])
                methods = list(set([t.get('detection_method', '') for t in current_group]))
                
                merged.append({
                    'threshold_price': round(avg_price, 2),
                    'confidence': round(max_confidence, 3),
                    'detection_methods': methods,
                    'n_methods': len(methods),
                    'raw_thresholds': current_group
                })
                current_group = [row]
        
        if current_group:
            avg_price = np.mean([t['threshold_price'] for t in current_group])
            max_confidence = np.max([t.get('confidence', 0.5) for t in current_group])
            methods = list(set([t.get('detection_method', '') for t in current_group]))
            
            merged.append({
                'threshold_price': round(avg_price, 2),
                'confidence': round(max_confidence, 3),
                'detection_methods': methods,
                'n_methods': len(methods),
                'raw_thresholds': current_group
            })
        
        merged = sorted(merged, key=lambda x: x['confidence'], reverse=True)
        
        return {
            'thresholds': merged,
            'all_detected_thresholds': all_thresholds,
            'method': 'combined'
        }
    
    def _calculate_threshold_confidence(self, prices: np.ndarray, threshold: float) -> float:
        below = np.sum(prices < threshold)
        above = np.sum(prices > threshold)
        
        if below == 0 or above == 0:
            return 0.5
        
        proximity_penalty = 0.0
        near_threshold = np.sum(np.abs(prices - threshold) < (np.std(prices) * 0.1))
        if near_threshold / len(prices) > 0.3:
            proximity_penalty = 0.2
        
        balance = min(below, above) / max(below, above)
        
        return min(0.98, max(0.3, balance - proximity_penalty + 0.5))
    
    def _build_price_segments(
        self,
        prices: np.ndarray,
        sales: np.ndarray,
        thresholds_result: Dict
    ) -> pd.DataFrame:
        thresholds = thresholds_result.get('thresholds', [])
        threshold_prices = sorted([t['threshold_price'] for t in thresholds])
        
        segments = []
        
        segment_boundaries = [np.min(prices) * 0.99] + threshold_prices + [np.max(prices) * 1.01]
        
        for i in range(len(segment_boundaries) - 1):
            lower = segment_boundaries[i]
            upper = segment_boundaries[i + 1]
            
            mask = (prices >= lower) & (prices < upper)
            
            if np.sum(mask) >= 3:
                segment_prices = prices[mask]
                segment_sales = sales[mask]
                
                log_p = np.log(segment_prices)
                log_s = np.log(segment_sales)
                
                try:
                    X = sm.add_constant(log_p)
                    model = sm.OLS(log_s, X).fit()
                    elasticity = model.params[1]
                    p_value = model.pvalues[1]
                    r_squared = model.rsquared
                except Exception:
                    elasticity = np.nan
                    p_value = 1.0
                    r_squared = 0.0
                
                segments.append({
                    'segment_id': i + 1,
                    'price_range_lower': round(lower, 2),
                    'price_range_upper': round(upper, 2),
                    'price_range_mid': round((lower + upper) / 2, 2),
                    'avg_price': round(np.mean(segment_prices), 2),
                    'avg_sales': round(np.mean(segment_sales), 1),
                    'std_price': round(np.std(segment_prices), 2),
                    'std_sales': round(np.std(segment_sales), 1),
                    'min_price': round(np.min(segment_prices), 2),
                    'max_price': round(np.max(segment_prices), 2),
                    'n_points': int(np.sum(mask)),
                    'price_elasticity': round(elasticity, 3) if not np.isnan(elasticity) else None,
                    'elasticity_p_value': round(p_value, 4),
                    'elasticity_significant': p_value < 0.05,
                    'r_squared': round(r_squared, 3) if not np.isnan(r_squared) else None,
                    'avg_revenue_per_unit': round(np.mean(segment_prices) * np.mean(segment_sales) / np.mean(segment_sales), 2)
                })
        
        return pd.DataFrame(segments)
    
    def get_threshold_recommendations(self) -> Dict:
        if self.price_segments is None or len(self.price_segments) == 0:
            raise ValueError("No thresholds detected yet")
        
        segments = self.price_segments.copy()
        
        optimal_segment = None
        max_profit_score = -np.inf
        
        for _, seg in segments.iterrows():
            if seg['price_elasticity'] is not None and seg['elasticity_significant']:
                profit_score = seg['avg_price'] * seg['avg_sales'] * (1 + abs(seg['price_elasticity']) * 0.1)
                if profit_score > max_profit_score:
                    max_profit_score = profit_score
                    optimal_segment = seg
        
        critical_points = []
        for _, seg in segments.iterrows():
            if seg['price_elasticity'] is not None and seg['price_elasticity'] < -1:
                critical_points.append({
                    'type': 'elastic_zone_start',
                    'price': seg['price_range_lower'],
                    'description': '价格进入富有弹性区间'
                })
            elif seg['price_elasticity'] is not None and abs(seg['price_elasticity']) < 0.5:
                critical_points.append({
                    'type': 'inelastic_zone_start',
                    'price': seg['price_range_lower'],
                    'description': '价格进入缺乏弹性区间'
                })
        
        psychological_prices = self._detect_psychological_prices()
        
        return {
            'optimal_price_segment': optimal_segment.to_dict() if optimal_segment is not None else None,
            'critical_points': critical_points,
            'psychological_prices': psychological_prices,
            'segments': segments.to_dict('records')
        }
    
    def _detect_psychological_prices(self) -> List[Dict]:
        if self.thresholds is None or 'thresholds' not in self.thresholds:
            return []
        
        psychological = []
        for t in self.thresholds['thresholds']:
            price = t['threshold_price']
            remainder = price % 10
            
            if abs(remainder - 9) < 1:
                psychological.append({
                    'price': price,
                    'type': '尾数9定价',
                    'confidence': t.get('confidence', 0.5)
                })
            elif abs(remainder - 0) < 0.5:
                psychological.append({
                    'price': price,
                    'type': '整数定价',
                    'confidence': t.get('confidence', 0.5)
                })
            elif abs(remainder - 5) < 0.5:
                psychological.append({
                    'price': price,
                    'type': '尾数5定价',
                    'confidence': t.get('confidence', 0.5)
                })
        
        return psychological
    
    def get_segment_comparison_data(self) -> Dict:
        if self.price_segments is None or len(self.price_segments) == 0:
            raise ValueError("No thresholds detected yet")
        
        segments = self.price_segments
        
        x_labels = []
        for _, seg in segments.iterrows():
            x_labels.append(f'{seg["price_range_lower"]:.0f}-{seg["price_range_upper"]:.0f}元')
        
        return {
            'segment_labels': x_labels,
            'avg_sales': segments['avg_sales'].tolist(),
            'avg_price': segments['avg_price'].tolist(),
            'elasticities': segments['price_elasticity'].fillna(0).tolist(),
            'n_points': segments['n_points'].tolist(),
            'segments': segments.to_dict('records')
        }
