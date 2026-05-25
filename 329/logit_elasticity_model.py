import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import Logit
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.utils import resample
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)
from typing import Dict, Tuple, Optional, List


class PriceElasticityModel:
    def __init__(
        self,
        threshold_quantile: float = 0.5,
        decouple_promotion: bool = True,
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95,
        random_seed: int = 42
    ):
        self.threshold_quantile = threshold_quantile
        self.decouple_promotion = decouple_promotion
        self.n_bootstrap = n_bootstrap
        self.confidence_level = confidence_level
        self.random_seed = random_seed
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.sales_threshold = None
        self.model_results = None
        self.bootstrap_results = None
        self.promo_lag_days = 7
        
    def _create_binary_target(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        self.sales_threshold = df['sales_quantity'].quantile(self.threshold_quantile)
        df['high_sales'] = (df['sales_quantity'] >= self.sales_threshold).astype(int)
        return df
    
    def _add_promotion_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for lag in range(1, self.promo_lag_days + 1):
            df[f'post_promo_{lag}'] = (df['is_promotion'].shift(lag) == 1).astype(int)
            df[f'post_promo_{lag}'] = df[f'post_promo_{lag}'].fillna(0).astype(int)
        df['in_promotion'] = df['is_promotion'].astype(int)
        df['any_promo_effect'] = (
            df['in_promotion'] + 
            sum([df[f'post_promo_{lag}'] for lag in range(1, self.promo_lag_days + 1)])
        ).clip(upper=1)
        return df
    
    def _prepare_features(self, df: pd.DataFrame, feature_set: str = 'full') -> pd.DataFrame:
        df = df.copy()
        
        if self.decouple_promotion:
            df = self._add_promotion_lag_features(df)
            df['log_price_non_promo'] = df['log_price'] * (1 - df['in_promotion'])
            df['log_price_promo'] = df['log_price'] * df['in_promotion']
            
            base_features = [
                'log_price_non_promo',
                'log_price_promo',
                'in_promotion',
                'advertising_spend',
                'relative_price',
                'temperature',
                'is_weekend'
            ]
            
            for lag in range(1, self.promo_lag_days + 1):
                base_features.append(f'post_promo_{lag}')
            
            if feature_set == 'full':
                features = base_features + [
                    'lag_sales_1',
                    'rolling_avg_price_7',
                    'month'
                ]
            elif feature_set == 'price_only':
                features = ['log_price_non_promo', 'log_price_promo', 'in_promotion']
            else:
                features = base_features
        else:
            base_features = [
                'log_price', 
                'is_promotion',
                'advertising_spend',
                'relative_price',
                'temperature',
                'is_weekend'
            ]
            
            if feature_set == 'full':
                features = base_features + [
                    'lag_sales_1',
                    'rolling_avg_price_7',
                    'month'
                ]
            elif feature_set == 'price_only':
                features = ['log_price', 'is_promotion']
            else:
                features = base_features
            
        if self.feature_names is None:
            self.feature_names = features
        else:
            features = self.feature_names
        
        df_features = df[features].copy()
        df_features = df_features.fillna(0)
        
        return df_features
    
    def fit(self, df: pd.DataFrame, feature_set: str = 'full') -> Dict:
        np.random.seed(self.random_seed)
        
        self.feature_names = None
        
        df = self._create_binary_target(df)
        X = self._prepare_features(df, feature_set)
        y = df['high_sales']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=self.random_seed, stratify=y
        )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        X_train_sm = sm.add_constant(X_train_scaled)
        X_test_sm = sm.add_constant(X_test_scaled)
        
        self.model = Logit(y_train, X_train_sm)
        self.model_results = self.model.fit(disp=False, maxiter=1000)
        
        self._fit_bootstrap(X_train_scaled, y_train)
        
        y_pred_proba = self.model_results.predict(X_test_sm)
        y_pred = (y_pred_proba >= 0.5).astype(int)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'confusion_matrix': confusion_matrix(y_test, y_pred)
        }
        
        feature_importance = self._get_feature_importance()
        
        if self.decouple_promotion:
            promotion_effects = self._calculate_promotion_decoupled_effects(df)
        else:
            promotion_effects = None
        
        return {
            'model_summary': self.model_results.summary(),
            'metrics': metrics,
            'sales_threshold': self.sales_threshold,
            'feature_importance': feature_importance,
            'promotion_effects': promotion_effects,
            'bootstrap_results': self.bootstrap_results
        }
    
    def _fit_bootstrap(self, X_train: np.ndarray, y_train: pd.Series) -> None:
        n_samples = len(y_train)
        n_features = X_train.shape[1] + 1
        
        bootstrap_coeffs = np.zeros((self.n_bootstrap, n_features))
        bootstrap_elastics_promo = np.zeros(self.n_bootstrap)
        bootstrap_elastics_non_promo = np.zeros(self.n_bootstrap)
        
        price_idx = None
        price_promo_idx = None
        price_non_promo_idx = None
        
        if self.decouple_promotion:
            if 'log_price_non_promo' in self.feature_names:
                price_non_promo_idx = self.feature_names.index('log_price_non_promo') + 1
            if 'log_price_promo' in self.feature_names:
                price_promo_idx = self.feature_names.index('log_price_promo') + 1
        else:
            if 'log_price' in self.feature_names:
                price_idx = self.feature_names.index('log_price') + 1
        
        for i in range(self.n_bootstrap):
            try:
                X_resample, y_resample = resample(
                    X_train, y_train.values, 
                    n_samples=n_samples, 
                    random_state=self.random_seed + i
                )
                
                X_resample_sm = sm.add_constant(X_resample)
                model = Logit(y_resample, X_resample_sm)
                results = model.fit(disp=False, maxiter=500)
                
                bootstrap_coeffs[i, :] = results.params.values
                
                mean_prob = np.mean(results.predict(X_resample_sm))
                
                if price_idx is not None:
                    bootstrap_elastics_promo[i] = results.params[price_idx] * (1 - mean_prob)
                    bootstrap_elastics_non_promo[i] = bootstrap_elastics_promo[i]
                
                if price_promo_idx is not None:
                    bootstrap_elastics_promo[i] = results.params[price_promo_idx] * (1 - mean_prob)
                if price_non_promo_idx is not None:
                    bootstrap_elastics_non_promo[i] = results.params[price_non_promo_idx] * (1 - mean_prob)
                    
            except Exception as e:
                bootstrap_coeffs[i, :] = np.nan
                bootstrap_elastics_promo[i] = np.nan
                bootstrap_elastics_non_promo[i] = np.nan
        
        alpha = 1 - self.confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        valid_mask = ~np.isnan(bootstrap_coeffs).any(axis=1)
        n_valid = np.sum(valid_mask)
        bootstrap_coeffs_clean = bootstrap_coeffs[valid_mask] if n_valid > 0 else np.zeros((0, n_features))
        bootstrap_elastics_promo_clean = bootstrap_elastics_promo[~np.isnan(bootstrap_elastics_promo)]
        bootstrap_elastics_non_promo_clean = bootstrap_elastics_non_promo[~np.isnan(bootstrap_elastics_non_promo)]
        
        feature_names = ['const'] + self.feature_names
        
        if n_valid > 0:
            coeff_mean = np.nanmean(bootstrap_coeffs, axis=0)
            coeff_median = np.nanmedian(bootstrap_coeffs, axis=0)
            ci_lower = np.nanpercentile(bootstrap_coeffs, lower_percentile, axis=0)
            ci_upper = np.nanpercentile(bootstrap_coeffs, upper_percentile, axis=0)
            std_error = np.nanstd(bootstrap_coeffs, axis=0)
            p_values = np.array([
                2 * min(
                    np.mean(bootstrap_coeffs_clean[:, i] <= 0),
                    np.mean(bootstrap_coeffs_clean[:, i] >= 0)
                ) if len(bootstrap_coeffs_clean) > 0 else 1.0
                for i in range(n_features)
            ])
            
            promo_mean = np.nanmean(bootstrap_elastics_promo) if len(bootstrap_elastics_promo_clean) > 0 else np.nan
            promo_median = np.nanmedian(bootstrap_elastics_promo) if len(bootstrap_elastics_promo_clean) > 0 else np.nan
            promo_ci_lower = np.nanpercentile(bootstrap_elastics_promo, lower_percentile) if len(bootstrap_elastics_promo_clean) > 0 else np.nan
            promo_ci_upper = np.nanpercentile(bootstrap_elastics_promo, upper_percentile) if len(bootstrap_elastics_promo_clean) > 0 else np.nan
            promo_std = np.nanstd(bootstrap_elastics_promo) if len(bootstrap_elastics_promo_clean) > 0 else np.nan
            
            non_promo_mean = np.nanmean(bootstrap_elastics_non_promo) if len(bootstrap_elastics_non_promo_clean) > 0 else np.nan
            non_promo_median = np.nanmedian(bootstrap_elastics_non_promo) if len(bootstrap_elastics_non_promo_clean) > 0 else np.nan
            non_promo_ci_lower = np.nanpercentile(bootstrap_elastics_non_promo, lower_percentile) if len(bootstrap_elastics_non_promo_clean) > 0 else np.nan
            non_promo_ci_upper = np.nanpercentile(bootstrap_elastics_non_promo, upper_percentile) if len(bootstrap_elastics_non_promo_clean) > 0 else np.nan
            non_promo_std = np.nanstd(bootstrap_elastics_non_promo) if len(bootstrap_elastics_non_promo_clean) > 0 else np.nan
        else:
            coeff_mean = np.full(n_features, np.nan)
            coeff_median = np.full(n_features, np.nan)
            ci_lower = np.full(n_features, np.nan)
            ci_upper = np.full(n_features, np.nan)
            std_error = np.full(n_features, np.nan)
            p_values = np.full(n_features, 1.0)
            
            promo_mean = np.nan
            promo_median = np.nan
            promo_ci_lower = np.nan
            promo_ci_upper = np.nan
            promo_std = np.nan
            
            non_promo_mean = np.nan
            non_promo_median = np.nan
            non_promo_ci_lower = np.nan
            non_promo_ci_upper = np.nan
            non_promo_std = np.nan
        
        coeff_ci = pd.DataFrame({
            'feature': feature_names,
            'coeff_mean': coeff_mean,
            'coeff_median': coeff_median,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'std_error_bootstrap': std_error,
            'p_value_bootstrap': p_values
        })
        
        self.bootstrap_results = {
            'n_bootstrap': self.n_bootstrap,
            'n_valid': n_valid,
            'confidence_level': self.confidence_level,
            'coefficient_intervals': coeff_ci,
            'elasticity_promo_ci': {
                'mean': promo_mean,
                'median': promo_median,
                'ci_lower': promo_ci_lower,
                'ci_upper': promo_ci_upper,
                'std_err': promo_std
            },
            'elasticity_non_promo_ci': {
                'mean': non_promo_mean,
                'median': non_promo_median,
                'ci_lower': non_promo_ci_lower,
                'ci_upper': non_promo_ci_upper,
                'std_err': non_promo_std
            },
            'all_coeffs': bootstrap_coeffs,
            'all_elasticities_promo': bootstrap_elastics_promo,
            'all_elasticities_non_promo': bootstrap_elastics_non_promo
        }
    
    def _get_feature_importance(self) -> pd.DataFrame:
        if self.model_results is None:
            raise ValueError("Model not fitted yet")
        
        coeffs = self.model_results.params
        std_errors = self.model_results.bse
        p_values = self.model_results.pvalues
        odds_ratios = np.exp(coeffs)
        
        feature_names = ['const'] + self.feature_names
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'coefficient': coeffs.values,
            'std_error': std_errors.values,
            'z_score': coeffs.values / std_errors.values,
            'p_value': p_values.values,
            'odds_ratio': odds_ratios.values
        })
        
        if self.bootstrap_results is not None:
            bootstrap_ci = self.bootstrap_results['coefficient_intervals']
            importance_df = importance_df.merge(
                bootstrap_ci[['feature', 'ci_lower', 'ci_upper', 'p_value_bootstrap']],
                on='feature',
                how='left'
            )
            importance_df = importance_df.rename(columns={
                'ci_lower': 'bootstrap_ci_lower',
                'ci_upper': 'bootstrap_ci_upper'
            })
        
        importance_df['abs_coeff'] = np.abs(importance_df['coefficient'])
        importance_df = importance_df.sort_values('abs_coeff', ascending=False)
        
        return importance_df.round(4)
    
    def _calculate_promotion_decoupled_effects(self, df: pd.DataFrame) -> Dict:
        if not self.decouple_promotion or self.model_results is None:
            return {}
        
        promo_effects = {}
        
        param_names = self.model_results.params.index.tolist()
        
        in_promo_idx = self.feature_names.index('in_promotion') + 1
        in_promo_param_name = param_names[in_promo_idx] if in_promo_idx < len(param_names) else 'in_promotion'
        promo_coeff = self.model_results.params[in_promo_param_name] if in_promo_param_name in param_names else 0
        promo_odds_ratio = np.exp(promo_coeff)
        
        promo_effects['promotion_boost_coeff'] = promo_coeff
        promo_effects['promotion_odds_ratio'] = promo_odds_ratio
        promo_effects['promotion_p_value'] = self.model_results.pvalues[in_promo_param_name] if in_promo_param_name in self.model_results.pvalues.index else 1.0
        
        post_promo_coeffs = {}
        for lag in range(1, self.promo_lag_days + 1):
            feature_name = f'post_promo_{lag}'
            if feature_name in self.feature_names:
                idx = self.feature_names.index(feature_name) + 1
                param_name = param_names[idx] if idx < len(param_names) else feature_name
                if param_name in param_names:
                    post_promo_coeffs[lag] = {
                        'coefficient': self.model_results.params[param_name],
                        'p_value': self.model_results.pvalues[param_name],
                        'odds_ratio': np.exp(self.model_results.params[param_name]),
                        'significant': self.model_results.pvalues[param_name] < 0.05
                    }
                else:
                    post_promo_coeffs[lag] = {
                        'coefficient': 0,
                        'p_value': 1.0,
                        'odds_ratio': 1.0,
                        'significant': False
                    }
        
        promo_effects['post_promotion_effects'] = post_promo_coeffs
        
        if self.bootstrap_results is not None:
            promo_effects['elasticity_promo'] = self.bootstrap_results['elasticity_promo_ci']
            promo_effects['elasticity_non_promo'] = self.bootstrap_results['elasticity_non_promo_ci']
        
        return promo_effects
    
    def _predict_with_bootstrap_ci(
        self,
        X_scaled: np.ndarray,
        n_samples: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if self.bootstrap_results is None:
            pred = self.model_results.predict(sm.add_constant(X_scaled, has_constant='add'))
            return pred, pred, pred
        
        coeffs = self.bootstrap_results['all_coeffs']
        valid_coeffs = coeffs[~np.isnan(coeffs).any(axis=1)]
        
        if len(valid_coeffs) == 0:
            pred = self.model_results.predict(sm.add_constant(X_scaled, has_constant='add'))
            return pred, pred, pred
        
        n_use = min(n_samples, len(valid_coeffs))
        idx = np.random.choice(len(valid_coeffs), n_use, replace=False)
        selected_coeffs = valid_coeffs[idx]
        
        X_sm = sm.add_constant(X_scaled, has_constant='add')
        
        all_preds = np.zeros((n_use, X_sm.shape[0]))
        for i in range(n_use):
            logits = X_sm @ selected_coeffs[i]
            all_preds[i] = 1 / (1 + np.exp(-logits))
        
        mean_pred = np.mean(all_preds, axis=0)
        alpha = 1 - self.confidence_level
        lower = np.percentile(all_preds, (alpha/2)*100, axis=0)
        upper = np.percentile(all_preds, (1-alpha/2)*100, axis=0)
        
        return mean_pred, lower, upper
    
    def calculate_price_elasticity(
        self, 
        df: pd.DataFrame, 
        price_range: Optional[Tuple[float, float]] = None,
        n_points: int = 100,
        include_bootstrap_ci: bool = True
    ) -> pd.DataFrame:
        if self.model_results is None:
            raise ValueError("Model not fitted yet")
        
        df_features = self._prepare_features(df, feature_set='full')
        mean_values = df_features.mean()
        
        if price_range is None:
            price_min = df['effective_price'].min()
            price_max = df['effective_price'].max()
        else:
            price_min, price_max = price_range
            
        prices = np.linspace(price_min, price_max, n_points)
        log_prices = np.log(prices)
        
        elasticity_results = []
        
        for log_p in log_prices:
            for is_promo in [0, 1]:
                X_eval = mean_values.copy()
                
                if self.decouple_promotion:
                    X_eval['log_price_non_promo'] = log_p * (1 - is_promo)
                    X_eval['log_price_promo'] = log_p * is_promo
                    X_eval['in_promotion'] = is_promo
                    for lag in range(1, self.promo_lag_days + 1):
                        X_eval[f'post_promo_{lag}'] = 0
                else:
                    X_eval['log_price'] = log_p
                    X_eval['is_promotion'] = is_promo
                
                X_scaled = self.scaler.transform(X_eval.values.reshape(1, -1))
                
                if include_bootstrap_ci and self.bootstrap_results is not None:
                    prob, prob_lower, prob_upper = self._predict_with_bootstrap_ci(X_scaled)
                    prob = prob[0]
                    prob_lower = prob_lower[0]
                    prob_upper = prob_upper[0]
                else:
                    X_sm = sm.add_constant(X_scaled, has_constant='add')
                    prob = self.model_results.predict(X_sm)[0]
                    prob_lower = prob
                    prob_upper = prob
                
                if self.decouple_promotion:
                    if is_promo and 'log_price_promo' in self.feature_names:
                        price_idx = self.feature_names.index('log_price_promo') + 1
                    elif not is_promo and 'log_price_non_promo' in self.feature_names:
                        price_idx = self.feature_names.index('log_price_non_promo') + 1
                    else:
                        price_idx = 0
                else:
                    if 'log_price' in self.feature_names:
                        price_idx = self.feature_names.index('log_price') + 1
                    else:
                        price_idx = 0
                
                param_names = self.model_results.params.index.tolist()
                param_name = param_names[price_idx] if price_idx > 0 and price_idx < len(param_names) else None
                price_coeff = self.model_results.params[param_name] if param_name in param_names else 0
                elasticity = price_coeff * (1 - prob)
                
                if include_bootstrap_ci and self.bootstrap_results is not None:
                    if is_promo:
                        elast_ci = self.bootstrap_results['elasticity_promo_ci']
                    else:
                        elast_ci = self.bootstrap_results['elasticity_non_promo_ci']
                    elasticity_lower = elast_ci['ci_lower']
                    elasticity_upper = elast_ci['ci_upper']
                else:
                    elasticity_lower = elasticity
                    elasticity_upper = elasticity
                
                dp = 0.01
                log_p_up = log_p + dp
                
                X_eval_up = mean_values.copy()
                if self.decouple_promotion:
                    X_eval_up['log_price_non_promo'] = log_p_up * (1 - is_promo)
                    X_eval_up['log_price_promo'] = log_p_up * is_promo
                    X_eval_up['in_promotion'] = is_promo
                else:
                    X_eval_up['log_price'] = log_p_up
                    X_eval_up['is_promotion'] = is_promo
                
                X_scaled_up = self.scaler.transform(X_eval_up.values.reshape(1, -1))
                X_sm_up = sm.add_constant(X_scaled_up, has_constant='add')
                prob_up = self.model_results.predict(X_sm_up)[0]
                
                arc_elasticity = ((prob_up - prob) / prob) / (dp) if prob > 0 else 0
                
                elasticity_results.append({
                    'price': np.exp(log_p),
                    'log_price': log_p,
                    'is_promotion': is_promo,
                    'purchase_probability': prob,
                    'prob_ci_lower': prob_lower,
                    'prob_ci_upper': prob_upper,
                    'point_elasticity': elasticity,
                    'elasticity_ci_lower': elasticity_lower,
                    'elasticity_ci_upper': elasticity_upper,
                    'arc_elasticity': arc_elasticity,
                    'marginal_effect': elasticity * prob / np.exp(log_p)
                })
        
        elasticity_df = pd.DataFrame(elasticity_results)
        
        avg_elasticity = elasticity_df['point_elasticity'].mean()
        elasticity_df['elasticity_category'] = pd.cut(
            elasticity_df['point_elasticity'],
            bins=[-np.inf, -2, -1, -0.5, 0, np.inf],
            labels=['极富弹性 (<-2)', '富有弹性 (-2~-1)', '单位弹性 (-1~-0.5)', '缺乏弹性 (-0.5~0)', '无弹性 (>0)']
        )
        
        return elasticity_df
    
    def predict_sales_impact(
        self,
        df: pd.DataFrame,
        base_price: float,
        price_change_pct: float,
        is_promotion: bool = False
    ) -> Dict:
        if self.model_results is None:
            raise ValueError("Model not fitted yet")
        
        new_price = base_price * (1 + price_change_pct)
        
        df_features = self._prepare_features(df, feature_set='full')
        mean_values = df_features.mean()
        
        def predict_for_price(price, promo_flag):
            X_eval = mean_values.copy()
            promo_int = int(promo_flag)
            
            if self.decouple_promotion:
                X_eval['log_price_non_promo'] = np.log(price) * (1 - promo_int)
                X_eval['log_price_promo'] = np.log(price) * promo_int
                X_eval['in_promotion'] = promo_int
                for lag in range(1, self.promo_lag_days + 1):
                    X_eval[f'post_promo_{lag}'] = 0
            else:
                X_eval['log_price'] = np.log(price)
                X_eval['is_promotion'] = promo_int
            
            X_scaled = self.scaler.transform(X_eval.values.reshape(1, -1))
            
            if self.bootstrap_results is not None:
                prob, prob_lower, prob_upper = self._predict_with_bootstrap_ci(X_scaled)
                return prob[0], prob_lower[0], prob_upper[0]
            else:
                X_sm = sm.add_constant(X_scaled, has_constant='add')
                prob = self.model_results.predict(X_sm)[0]
                return prob, prob, prob
        
        prob_base, prob_base_lower, prob_base_upper = predict_for_price(base_price, 0)
        prob_new, prob_new_lower, prob_new_upper = predict_for_price(new_price, is_promotion)
        
        elasticity_df = self.calculate_price_elasticity(
            df, 
            price_range=(base_price * 0.8, base_price * 1.2),
            include_bootstrap_ci=False
        )
        
        if is_promotion:
            avg_elasticity = elasticity_df[elasticity_df['is_promotion'] == 1]['point_elasticity'].mean()
            elast_ci = self.bootstrap_results['elasticity_promo_ci'] if self.bootstrap_results else None
        else:
            avg_elasticity = elasticity_df[elasticity_df['is_promotion'] == 0]['point_elasticity'].mean()
            elast_ci = self.bootstrap_results['elasticity_non_promo_ci'] if self.bootstrap_results else None
        
        expected_sales_change = (prob_new - prob_base) / prob_base
        expected_sales_change_lower = (prob_new_lower - prob_base_upper) / prob_base_upper
        expected_sales_change_upper = (prob_new_upper - prob_base_lower) / prob_base_lower
        
        base_sales = df['sales_quantity'].mean()
        predicted_sales = base_sales * (1 + expected_sales_change)
        predicted_sales_lower = base_sales * (1 + expected_sales_change_lower)
        predicted_sales_upper = base_sales * (1 + expected_sales_change_upper)
        
        base_revenue = base_price * base_sales
        new_revenue = new_price * predicted_sales
        new_revenue_lower = new_price * predicted_sales_lower
        new_revenue_upper = new_price * predicted_sales_upper
        revenue_change = (new_revenue - base_revenue) / base_revenue
        revenue_change_lower = (new_revenue_lower - base_revenue) / base_revenue
        revenue_change_upper = (new_revenue_upper - base_revenue) / base_revenue
        
        result = {
            'base_price': base_price,
            'new_price': new_price,
            'price_change_pct': price_change_pct,
            'is_promotion': is_promotion,
            'base_probability': prob_base,
            'base_prob_ci': (prob_base_lower, prob_base_upper),
            'new_probability': prob_new,
            'new_prob_ci': (prob_new_lower, prob_new_upper),
            'probability_change': prob_new - prob_base,
            'probability_change_pct': expected_sales_change,
            'probability_change_ci': (expected_sales_change_lower, expected_sales_change_upper),
            'average_elasticity': avg_elasticity,
            'base_sales_estimate': base_sales,
            'predicted_sales': predicted_sales,
            'predicted_sales_ci': (predicted_sales_lower, predicted_sales_upper),
            'sales_change': predicted_sales - base_sales,
            'sales_change_pct': expected_sales_change,
            'sales_change_ci': (expected_sales_change_lower, expected_sales_change_upper),
            'base_revenue_estimate': base_revenue,
            'predicted_revenue': new_revenue,
            'predicted_revenue_ci': (new_revenue_lower, new_revenue_upper),
            'revenue_change': new_revenue - base_revenue,
            'revenue_change_pct': revenue_change,
            'revenue_change_ci': (revenue_change_lower, revenue_change_upper)
        }
        
        if elast_ci is not None:
            result['elasticity_ci'] = (elast_ci['ci_lower'], elast_ci['ci_upper'])
        
        return result
    
    def get_elasticity_summary(self, elasticity_df: pd.DataFrame) -> Dict:
        has_promo_split = 'is_promotion' in elasticity_df.columns
        
        if has_promo_split:
            promo_df = elasticity_df[elasticity_df['is_promotion'] == 1]
            non_promo_df = elasticity_df[elasticity_df['is_promotion'] == 0]
            overall_df = elasticity_df
        else:
            promo_df = pd.DataFrame()
            non_promo_df = pd.DataFrame()
            overall_df = elasticity_df
        
        def calc_summary(df):
            if len(df) == 0:
                return {}
            return {
                'avg_point_elasticity': df['point_elasticity'].mean(),
                'avg_arc_elasticity': df['arc_elasticity'].mean(),
                'elastic_range_pct': (df['point_elasticity'] < -1).sum() / len(df) * 100,
                'inelastic_range_pct': (df['point_elasticity'] > -1).sum() / len(df) * 100,
                'unitary_elasticity_price': df.iloc[
                    np.argmin(np.abs(df['point_elasticity'] + 1))
                ]['price'],
                'max_revenue_price': df.iloc[
                    np.argmax(df['purchase_probability'] * df['price'])
                ]['price']
            }
        
        summary = calc_summary(overall_df)
        
        if has_promo_split:
            summary['promo'] = calc_summary(promo_df)
            summary['non_promo'] = calc_summary(non_promo_df)
            
            if self.bootstrap_results is not None:
                summary['promo']['elasticity_ci'] = (
                    self.bootstrap_results['elasticity_promo_ci']['ci_lower'],
                    self.bootstrap_results['elasticity_promo_ci']['ci_upper']
                )
                summary['non_promo']['elasticity_ci'] = (
                    self.bootstrap_results['elasticity_non_promo_ci']['ci_lower'],
                    self.bootstrap_results['elasticity_non_promo_ci']['ci_upper']
                )
        
        return summary
