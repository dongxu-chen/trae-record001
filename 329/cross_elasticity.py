import numpy as np
import pandas as pd
import statsmodels.api as sm
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler


class CrossElasticityAnalyzer:
    
    def __init__(
        self,
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95,
        random_seed: int = 42
    ):
        self.n_bootstrap = n_bootstrap
        self.confidence_level = confidence_level
        self.random_seed = random_seed
        self.cross_elasticity_matrix = None
        self.elasticity_ci_matrix = None
        self.product_models = {}
        self.product_info = {}
        
    def fit(self, multi_product_df: pd.DataFrame) -> Dict:
        np.random.seed(self.random_seed)
        
        product_ids = sorted(multi_product_df['product_id'].unique())
        n_products = len(product_ids)
        
        for pid in product_ids:
            self.product_info[pid] = {
                'name': multi_product_df[multi_product_df['product_id'] == pid]['product_name'].iloc[0],
                'category': multi_product_df[multi_product_df['product_id'] == pid]['category'].iloc[0],
                'avg_price': multi_product_df[multi_product_df['product_id'] == pid]['effective_price'].mean(),
                'avg_sales': multi_product_df[multi_product_df['product_id'] == pid]['sales_quantity'].mean()
            }
        
        self.cross_elasticity_matrix = np.zeros((n_products, n_products))
        self.elasticity_ci_matrix = np.zeros((n_products, n_products, 2))
        self.p_value_matrix = np.ones((n_products, n_products))
        
        for target_idx, target_pid in enumerate(product_ids):
            target_df = multi_product_df[multi_product_df['product_id'] == target_pid].copy()
            target_df = target_df.sort_values('date')
            
            feature_data = []
            for date in target_df['date']:
                row = {'target_log_sales': np.log(target_df[target_df['date'] == date]['sales_quantity'].values[0])}
                
                for source_idx, source_pid in enumerate(product_ids):
                    source_data = multi_product_df[
                        (multi_product_df['product_id'] == source_pid) & 
                        (multi_product_df['date'] == date)
                    ]
                    if len(source_data) > 0:
                        row[f'log_price_{source_pid}'] = np.log(source_data['effective_price'].values[0])
                    else:
                        row[f'log_price_{source_pid}'] = np.nan
                
                row['advertising_spend'] = target_df[target_df['date'] == date]['advertising_spend'].values[0]
                row['temperature'] = target_df[target_df['date'] == date]['temperature'].values[0]
                row['is_weekend'] = target_df[target_df['date'] == date]['is_weekend'].values[0]
                row['is_promotion'] = target_df[target_df['date'] == date]['is_promotion'].values[0]
                
                feature_data.append(row)
            
            feature_df = pd.DataFrame(feature_data).dropna()
            
            feature_cols = [f'log_price_{pid}' for pid in product_ids] + \
                          ['advertising_spend', 'temperature', 'is_weekend', 'is_promotion']
            
            X = feature_df[feature_cols]
            y = feature_df['target_log_sales']
            
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            X_sm = sm.add_constant(X_scaled)
            
            try:
                model = sm.OLS(y, X_sm).fit()
                
                self.product_models[target_pid] = {
                    'model': model,
                    'scaler': scaler,
                    'r_squared': model.rsquared,
                    'adj_r_squared': model.rsquared_adj,
                    'feature_cols': feature_cols
                }
                
                for source_idx, source_pid in enumerate(product_ids):
                    param_idx = source_idx + 1
                    if param_idx < len(model.params):
                        coeff = model.params.iloc[param_idx]
                        self.cross_elasticity_matrix[target_idx, source_idx] = coeff
                        self.p_value_matrix[target_idx, source_idx] = model.pvalues.iloc[param_idx]
                        
                        ci = model.conf_int(1 - self.confidence_level).iloc[param_idx]
                        self.elasticity_ci_matrix[target_idx, source_idx, 0] = ci[0]
                        self.elasticity_ci_matrix[target_idx, source_idx, 1] = ci[1]
                        
            except Exception as e:
                print(f"Warning: Failed to fit model for product {target_pid}: {e}")
                self.product_models[target_pid] = None
        
        self._fit_bootstrap(multi_product_df, product_ids)
        
        return self._build_results_summary(product_ids)
    
    def _fit_bootstrap(self, multi_product_df: pd.DataFrame, product_ids: List[int]):
        n_products = len(product_ids)
        bootstrap_coeffs = np.zeros((self.n_bootstrap, n_products, n_products))
        
        dates = sorted(multi_product_df['date'].unique())
        n_dates = len(dates)
        
        for b in range(self.n_bootstrap):
            sample_indices = np.random.choice(n_dates, size=n_dates, replace=True)
            sample_dates = [dates[i] for i in sample_indices]
            
            bootstrap_elasticity = np.zeros((n_products, n_products))
            
            for target_idx, target_pid in enumerate(product_ids):
                feature_data = []
                for date in sample_dates:
                    target_data = multi_product_df[
                        (multi_product_df['product_id'] == target_pid) & 
                        (multi_product_df['date'] == date)
                    ]
                    if len(target_data) == 0:
                        continue
                        
                    row = {'target_log_sales': np.log(target_data['sales_quantity'].values[0])}
                    
                    for source_idx, source_pid in enumerate(product_ids):
                        source_data = multi_product_df[
                            (multi_product_df['product_id'] == source_pid) & 
                            (multi_product_df['date'] == date)
                        ]
                        if len(source_data) > 0:
                            row[f'log_price_{source_pid}'] = np.log(source_data['effective_price'].values[0])
                        else:
                            row[f'log_price_{source_pid}'] = np.nan
                    
                    row['advertising_spend'] = target_data['advertising_spend'].values[0]
                    row['temperature'] = target_data['temperature'].values[0]
                    row['is_weekend'] = target_data['is_weekend'].values[0]
                    row['is_promotion'] = target_data['is_promotion'].values[0]
                    
                    feature_data.append(row)
                
                feature_df = pd.DataFrame(feature_data).dropna()
                if len(feature_df) < n_products + 10:
                    continue
                
                feature_cols = [f'log_price_{pid}' for pid in product_ids] + \
                              ['advertising_spend', 'temperature', 'is_weekend', 'is_promotion']
                
                X = feature_df[feature_cols]
                y = feature_df['target_log_sales']
                
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                X_sm = sm.add_constant(X_scaled)
                
                try:
                    model = sm.OLS(y, X_sm).fit(disp=False)
                    
                    for source_idx in range(n_products):
                        param_idx = source_idx + 1
                        if param_idx < len(model.params):
                            bootstrap_elasticity[target_idx, source_idx] = model.params.iloc[param_idx]
                            
                except Exception:
                    continue
            
            bootstrap_coeffs[b] = bootstrap_elasticity
        
        self.bootstrap_results = {
            'all_coeffs': bootstrap_coeffs,
            'n_valid': np.sum(~np.isnan(bootstrap_coeffs).any(axis=(1, 2)))
        }
    
    def _build_results_summary(self, product_ids: List[int]) -> Dict:
        n_products = len(product_ids)
        summary = {
            'product_ids': product_ids,
            'product_info': self.product_info,
            'cross_elasticity_matrix': pd.DataFrame(
                self.cross_elasticity_matrix,
                index=[f'{self.product_info[pid]["name"]}' for pid in product_ids],
                columns=[f'{self.product_info[pid]["name"]}' for pid in product_ids]
            ),
            'p_value_matrix': pd.DataFrame(
                self.p_value_matrix,
                index=[f'{self.product_info[pid]["name"]}' for pid in product_ids],
                columns=[f'{self.product_info[pid]["name"]}' for pid in product_ids]
            )
        }
        
        own_elasticities = []
        for i in range(n_products):
            own_elasticities.append({
                'product_id': product_ids[i],
                'product_name': self.product_info[product_ids[i]]['name'],
                'category': self.product_info[product_ids[i]]['category'],
                'own_price_elasticity': self.cross_elasticity_matrix[i, i],
                'ci_lower': self.elasticity_ci_matrix[i, i, 0],
                'ci_upper': self.elasticity_ci_matrix[i, i, 1],
                'p_value': self.p_value_matrix[i, i],
                'significant': self.p_value_matrix[i, i] < 0.05
            })
        summary['own_elasticities'] = pd.DataFrame(own_elasticities)
        
        cross_pairs = []
        for i in range(n_products):
            for j in range(n_products):
                if i != j:
                    elasticity = self.cross_elasticity_matrix[i, j]
                    cross_type = '替代品' if elasticity > 0 else ('互补品' if elasticity < 0 else '独立品')
                    
                    if abs(elasticity) >= 0.1 and self.p_value_matrix[i, j] < 0.05:
                        cross_pairs.append({
                            'target_product': self.product_info[product_ids[i]]['name'],
                            'source_product': self.product_info[product_ids[j]]['name'],
                            'target_category': self.product_info[product_ids[i]]['category'],
                            'source_category': self.product_info[product_ids[j]]['category'],
                            'cross_elasticity': elasticity,
                            'ci_lower': self.elasticity_ci_matrix[i, j, 0],
                            'ci_upper': self.elasticity_ci_matrix[i, j, 1],
                            'p_value': self.p_value_matrix[i, j],
                            'relationship_type': cross_type,
                            'significant': True
                        })
        
        if cross_pairs:
            cross_pairs_df = pd.DataFrame(cross_pairs)
            cross_pairs_df = cross_pairs_df.sort_values('cross_elasticity', key=abs, ascending=False)
            summary['significant_cross_pairs'] = cross_pairs_df
        else:
            summary['significant_cross_pairs'] = pd.DataFrame()
        
        return summary
    
    def simulate_price_change_impact(
        self,
        source_product_id: int,
        price_change_pct: float,
        multi_product_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        if self.cross_elasticity_matrix is None:
            raise ValueError("Model not fitted yet")
        
        product_ids = list(self.product_info.keys())
        source_idx = product_ids.index(source_product_id)
        
        results = []
        for target_idx, target_pid in enumerate(product_ids):
            elasticity = self.cross_elasticity_matrix[target_idx, source_idx]
            ci_lower = self.elasticity_ci_matrix[target_idx, source_idx, 0]
            ci_upper = self.elasticity_ci_matrix[target_idx, source_idx, 1]
            p_value = self.p_value_matrix[target_idx, source_idx]
            
            sales_change_pct = elasticity * price_change_pct
            sales_change_pct_lower = ci_lower * price_change_pct
            sales_change_pct_upper = ci_upper * price_change_pct
            
            info = self.product_info[target_pid]
            base_sales = info['avg_sales']
            base_revenue = info['avg_sales'] * info['avg_price']
            
            expected_sales_change = base_sales * sales_change_pct
            expected_revenue_change = base_revenue * sales_change_pct
            
            if target_idx == source_idx:
                impact_type = '自身影响'
            elif elasticity > 0.1:
                impact_type = '替代效应 (+)'
            elif elasticity < -0.1:
                impact_type = '互补效应 (-)'
            else:
                impact_type = '无显著影响'
            
            results.append({
                'product_id': target_pid,
                'product_name': info['name'],
                'category': info['category'],
                'cross_elasticity': elasticity,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'price_change_pct': price_change_pct,
                'sales_change_pct': sales_change_pct,
                'sales_change_pct_lower': sales_change_pct_lower,
                'sales_change_pct_upper': sales_change_pct_upper,
                'base_sales': base_sales,
                'expected_sales_change': expected_sales_change,
                'expected_sales_change_lower': base_sales * sales_change_pct_lower,
                'expected_sales_change_upper': base_sales * sales_change_pct_upper,
                'base_revenue': base_revenue,
                'expected_revenue_change': expected_revenue_change,
                'impact_type': impact_type
            })
        
        results_df = pd.DataFrame(results)
        return results_df
    
    def get_category_level_analysis(self) -> Dict:
        if self.cross_elasticity_matrix is None:
            raise ValueError("Model not fitted yet")
        
        product_ids = list(self.product_info.keys())
        categories = sorted(list(set([info['category'] for info in self.product_info.values()])))
        
        category_elasticity = {}
        for cat in categories:
            cat_product_ids = [pid for pid in product_ids if self.product_info[pid]['category'] == cat]
            other_product_ids = [pid for pid in product_ids if self.product_info[pid]['category'] != cat]
            
            cat_idx = [product_ids.index(pid) for pid in cat_product_ids]
            other_idx = [product_ids.index(pid) for pid in other_product_ids]
            
            if len(cat_idx) > 0:
                within_cat = self.cross_elasticity_matrix[cat_idx][:, cat_idx]
                own_elasticities = np.diag(within_cat)
                cross_elasticities = within_cat[~np.eye(len(cat_idx), dtype=bool)]
                
                category_elasticity[cat] = {
                    'n_products': len(cat_idx),
                    'avg_own_elasticity': np.mean(own_elasticities),
                    'avg_within_category_cross': np.mean(cross_elasticities) if len(cross_elasticities) > 0 else 0,
                    'between_category_cross': np.mean(self.cross_elasticity_matrix[cat_idx][:, other_idx]) if len(other_idx) > 0 else 0
                }
        
        return {
            'categories': categories,
            'category_summary': pd.DataFrame(category_elasticity).T,
            'product_ids': product_ids
        }
    
    def get_elasticity_heatmap_data(self) -> Dict:
        product_ids = list(self.product_info.keys())
        n = len(product_ids)
        
        z_data = self.cross_elasticity_matrix.copy()
        text_data = []
        
        for i in range(n):
            row = []
            for j in range(n):
                elast = z_data[i, j]
                p_val = self.p_value_matrix[i, j]
                sig = '*' if p_val < 0.05 else ''
                row.append(f'{elast:.3f}{sig}')
            text_data.append(row)
        
        return {
            'z': z_data,
            'text': text_data,
            'x_labels': [self.product_info[pid]['name'] for pid in product_ids],
            'y_labels': [self.product_info[pid]['name'] for pid in product_ids],
            'categories': [self.product_info[pid]['category'] for pid in product_ids]
        }
