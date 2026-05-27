import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import os
from scipy.stats import gaussian_kde
from scipy.interpolate import interp1d
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from config import Config
from utils.features import FeatureEngineer


class DeliveryTimeModel:
    def __init__(self, confidence_levels=None):
        self.models = {}
        self.feature_names = None
        self.confidence_levels = confidence_levels or [0.80, 0.90, 0.95, 0.99]
        self._build_quantiles()
        self._residual_kde = None
        self._mean_absolute_error = None
    
    def _build_quantiles(self):
        self.quantiles = [0.5]
        for cl in self.confidence_levels:
            lower = (1 - cl) / 2
            upper = 1 - lower
            self.quantiles.append(lower)
            self.quantiles.append(upper)
        self.quantiles = sorted(set(self.quantiles))
    
    def prepare_features(self, df):
        features_list = []
        
        for _, row in df.iterrows():
            order_time = pd.to_datetime(row['order_time'])
            weather = {
                'weather': row['weather'],
                'temperature': row['temperature'],
                'humidity': row['humidity'],
                'windpower': str(row['windpower']),
                'precipitation_rate': row.get('precipitation_rate', 0),
                'precipitation_max': row.get('precipitation_max', 0),
                'precipitation_coverage': row.get('precipitation_coverage', 0)
            }
            route_info = {
                'distance': row['distance'],
                'duration': row['distance'] / 60,
                'tolls': row['distance'] * 0.5 if row['distance'] > 100 else 0
            }
            
            features, _ = FeatureEngineer.build_features(
                row['from_address'],
                row['to_address'],
                order_time,
                weather,
                row['busy_level'],
                route_info
            )
            features_list.append(features)
        
        features_df = pd.DataFrame(features_list)
        return features_df
    
    @staticmethod
    def _enforce_monotonicity(predictions_dict, quantiles):
        sorted_quantiles = sorted(quantiles)
        predictions = np.array([predictions_dict[q] for q in sorted_quantiles])
        
        for i in range(1, len(predictions)):
            if predictions[i] < predictions[i-1]:
                predictions[i] = predictions[i-1] + 1e-6
        
        return {q: predictions[i] for i, q in enumerate(sorted_quantiles)}
    
    def _train_kde_residual_model(self, X_train, y_train, y_pred_median):
        residuals = y_train.values - y_pred_median
        if len(residuals) > 10 and np.std(residuals) > 0:
            try:
                self._residual_kde = gaussian_kde(residuals, bw_method='scott')
            except:
                self._residual_kde = None
        self._mean_absolute_error = np.mean(np.abs(residuals))
    
    def _kde_bandwidth_correction(self, predictions, features_dict):
        if self._residual_kde is None or self._mean_absolute_error is None:
            return predictions
        
        distance = features_dict.get('distance', 100)
        busy_impact = features_dict.get('busy_impact', 1.0)
        weather_impact = features_dict.get('weather_impact', 1.0)
        
        uncertainty_factor = 1.0 + (distance / 1000) * 0.3 + (busy_impact - 1.0) + (1 - weather_impact)
        uncertainty_factor = max(0.8, min(1.5, uncertainty_factor))
        
        bandwidth = self._mean_absolute_error * uncertainty_factor
        
        return predictions, bandwidth
    
    def _narrow_confidence_interval(self, predictions_dict, features_dict, target_confidence=0.95):
        predictions, bandwidth = self._kde_bandwidth_correction(predictions_dict, features_dict)
        
        median_pred = predictions.get(0.5, np.mean(list(predictions.values())))
        
        if self._residual_kde is not None:
            try:
                lower_quantile = (1 - target_confidence) / 2
                upper_quantile = 1 - lower_quantile
                
                residual_range = np.linspace(-3 * bandwidth, 3 * bandwidth, 1000)
                pdf = self._residual_kde(residual_range)
                cdf = np.cumsum(pdf) / np.sum(pdf)
                
                lower_residual = np.interp(lower_quantile, cdf, residual_range)
                upper_residual = np.interp(upper_quantile, cdf, residual_range)
                
                k_lower = 0.85 + 0.1 * (features_dict.get('weather_impact', 1.0))
                k_upper = 0.85 + 0.1 * (2 - features_dict.get('busy_impact', 1.0))
                
                lower_bound = median_pred + lower_residual * k_lower
                upper_bound = median_pred + upper_residual * k_upper
                
                raw_lower = predictions.get(lower_quantile, median_pred - bandwidth)
                raw_upper = predictions.get(upper_quantile, median_pred + bandwidth)
                
                w = 0.6
                final_lower = w * lower_bound + (1 - w) * raw_lower
                final_upper = w * upper_bound + (1 - w) * raw_upper
                
                if final_upper - final_lower < 0.5:
                    final_lower = median_pred - 0.25
                    final_upper = median_pred + 0.25
                
                predictions[lower_quantile] = max(0, final_lower)
                predictions[upper_quantile] = final_upper
                predictions[0.5] = median_pred
            except:
                pass
        
        return predictions
    
    def train(self, df, use_cross_validation=False):
        print("正在准备特征...")
        X = self.prepare_features(df)
        y = df['delivery_hours']
        self.feature_names = X.columns.tolist()
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        print(f"训练集大小: {len(X_train)}, 测试集大小: {len(X_test)}")
        
        if use_cross_validation:
            print("\n使用交叉验证训练分位数模型...")
            self._train_with_cv(X_train, y_train, X_test, y_test)
        else:
            for quantile in self.quantiles:
                print(f"\n正在训练分位数 {quantile} 的模型...")
                self._train_single_quantile(quantile, X_train, y_train, X_test, y_test)
        
        print("\n训练残差KDE模型用于区间收窄...")
        y_pred_median = self.models[0.5].predict(X_train)
        self._train_kde_residual_model(X_train, y_train, y_pred_median)
        
        print("\n模型评估 (中位数模型):")
        y_pred = self.models[0.5].predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        print(f"MAE: {mae:.2f} 小时")
        print(f"RMSE: {rmse:.2f} 小时")
        print(f"R²: {r2:.4f}")
        
        metrics = {'mae': mae, 'rmse': rmse, 'r2': r2}
        
        for cl in sorted(self.confidence_levels, reverse=True):
            coverage = self._calculate_coverage(X_test, y_test, cl)
            interval_width = self._calculate_interval_width(X_test, cl)
            print(f"{int(cl*100)}%置信区间 覆盖率: {coverage:.2%}, 平均宽度: {interval_width:.2f} 小时")
            metrics[f'coverage_{int(cl*100)}'] = coverage
            metrics[f'interval_width_{int(cl*100)}'] = interval_width
        
        return metrics
    
    def _train_single_quantile(self, quantile, X_train, y_train, X_val, y_val):
        params = {
            'objective': 'quantile',
            'alpha': quantile,
            'metric': 'quantile',
            'boosting_type': 'gbdt',
            'num_leaves': 47,
            'learning_rate': 0.03,
            'feature_fraction': 0.85,
            'bagging_fraction': 0.75,
            'bagging_freq': 5,
            'verbose': -1,
            'min_data_in_leaf': 15,
            'max_depth': 10,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'min_gain_to_split': 0.01
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=800,
            valid_sets=[valid_data],
            callbacks=[
                lgb.early_stopping(stopping_rounds=60),
                lgb.log_evaluation(period=150)
            ]
        )
        
        self.models[quantile] = model
    
    def _train_with_cv(self, X_train, y_train, X_test, y_test):
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        
        for quantile in self.quantiles:
            print(f"\n正在交叉验证训练分位数 {quantile} 的模型...")
            
            params = {
                'objective': 'quantile',
                'alpha': quantile,
                'metric': 'quantile',
                'boosting_type': 'gbdt',
                'num_leaves': 47,
                'learning_rate': 0.03,
                'feature_fraction': 0.85,
                'bagging_fraction': 0.75,
                'bagging_freq': 5,
                'verbose': -1,
                'min_data_in_leaf': 15,
                'max_depth': 10,
                'lambda_l1': 0.1,
                'lambda_l2': 0.1
            }
            
            best_iterations = []
            
            for train_idx, val_idx in kf.split(X_train):
                X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
                y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
                
                train_data = lgb.Dataset(X_tr, label=y_tr)
                valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
                
                model = lgb.train(
                    params,
                    train_data,
                    num_boost_round=800,
                    valid_sets=[valid_data],
                    callbacks=[lgb.early_stopping(stopping_rounds=60)]
                )
                best_iterations.append(model.best_iteration)
            
            best_iter = int(np.mean(best_iterations))
            print(f"  最佳迭代次数: {best_iter}")
            
            full_train_data = lgb.Dataset(X_train, label=y_train)
            model = lgb.train(params, full_train_data, num_boost_round=best_iter)
            self.models[quantile] = model
    
    def _calculate_coverage(self, X, y, confidence_level=0.95):
        lower_q = (1 - confidence_level) / 2
        upper_q = 1 - lower_q
        
        lower = self.models[lower_q].predict(X)
        upper = self.models[upper_q].predict(X)
        
        features = X.iloc[0].to_dict() if hasattr(X, 'iloc') else X
        lower, upper = self._apply_narrowing_batch(lower, upper, X, confidence_level)
        
        covered = np.sum((y >= lower) & (y <= upper))
        return covered / len(y)
    
    def _calculate_interval_width(self, X, confidence_level=0.95):
        lower_q = (1 - confidence_level) / 2
        upper_q = 1 - lower_q
        
        lower = self.models[lower_q].predict(X)
        upper = self.models[upper_q].predict(X)
        
        lower, upper = self._apply_narrowing_batch(lower, upper, X, confidence_level)
        
        return np.mean(upper - lower)
    
    def _apply_narrowing_batch(self, lower, upper, X, confidence_level):
        if self._residual_kde is None:
            return lower, upper
        
        try:
            distance = X['distance'].values if 'distance' in X.columns else np.ones(len(lower)) * 100
            busy_impact = X['busy_impact'].values if 'busy_impact' in X.columns else np.ones(len(lower))
            weather_impact = X['weather_impact'].values if 'weather_impact' in X.columns else np.ones(len(lower))
            
            uncertainty_factor = 1.0 + (distance / 1000) * 0.3 + (busy_impact - 1.0) + (1 - weather_impact)
            uncertainty_factor = np.clip(uncertainty_factor, 0.8, 1.5)
            
            bandwidth = self._mean_absolute_error * uncertainty_factor
            
            lower_q = (1 - confidence_level) / 2
            upper_q = 1 - lower_q
            
            median_pred = self.models[0.5].predict(X)
            
            residual_range = np.linspace(-3 * np.max(bandwidth), 3 * np.max(bandwidth), 1000)
            pdf = self._residual_kde(residual_range)
            cdf = np.cumsum(pdf) / np.sum(pdf)
            
            for i in range(len(lower)):
                bw = bandwidth[i]
                scaled_range = residual_range * bw / np.max(bandwidth)
                lower_residual = np.interp(lower_q, cdf, scaled_range)
                upper_residual = np.interp(upper_q, cdf, scaled_range)
                
                k_lower = 0.85 + 0.1 * weather_impact[i]
                k_upper = 0.85 + 0.1 * (2 - busy_impact[i])
                
                w = 0.6
                lower[i] = w * (median_pred[i] + lower_residual * k_lower) + (1 - w) * lower[i]
                upper[i] = w * (median_pred[i] + upper_residual * k_upper) + (1 - w) * upper[i]
                
                if upper[i] - lower[i] < 0.5:
                    lower[i] = median_pred[i] - 0.25
                    upper[i] = median_pred[i] + 0.25
                
                lower[i] = max(0, lower[i])
        except:
            pass
        
        return lower, upper
    
    def predict(self, features_dict, confidence_level=0.95):
        if not self.models:
            raise ValueError("模型未训练，请先调用 train() 方法")
        
        X = pd.DataFrame([features_dict])
        X = X[self.feature_names]
        
        predictions = {}
        for quantile in self.quantiles:
            pred = self.models[quantile].predict(X)[0]
            predictions[quantile] = max(0, pred)
        
        predictions = self._enforce_monotonicity(predictions, self.quantiles)
        predictions = self._narrow_confidence_interval(predictions, features_dict, confidence_level)
        predictions = self._enforce_monotonicity(predictions, self.quantiles)
        
        lower_q = (1 - confidence_level) / 2
        upper_q = 1 - lower_q
        
        all_intervals = {}
        for cl in self.confidence_levels:
            lq = (1 - cl) / 2
            uq = 1 - lq
            if lq in predictions and uq in predictions:
                all_intervals[f'{int(cl*100)}%'] = {
                    'lower': predictions[lq],
                    'upper': predictions[uq]
                }
        
        return {
            'predicted_hours': predictions[0.5],
            'lower_bound': predictions.get(lower_q, predictions[0.5] - 1),
            'upper_bound': predictions.get(upper_q, predictions[0.5] + 1),
            'confidence_level': f'{int(confidence_level*100)}%',
            'all_intervals': all_intervals,
            'interval_width': predictions.get(upper_q, predictions[0.5] + 1) - predictions.get(lower_q, predictions[0.5] - 1),
            'narrowed': self._residual_kde is not None
        }
    
    def save(self, path=None):
        if path is None:
            path = Config.MODEL_PATH
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        model_data = {
            'models': self.models,
            'feature_names': self.feature_names,
            'quantiles': self.quantiles,
            'confidence_levels': self.confidence_levels,
            'residual_kde': self._residual_kde,
            'mean_absolute_error': self._mean_absolute_error
        }
        joblib.dump(model_data, path)
        print(f"模型已保存到 {path}")
    
    def load(self, path=None):
        if path is None:
            path = Config.MODEL_PATH
        
        model_data = joblib.load(path)
        self.models = model_data['models']
        self.feature_names = model_data['feature_names']
        self.quantiles = model_data['quantiles']
        self.confidence_levels = model_data.get('confidence_levels', [0.95])
        self._residual_kde = model_data.get('residual_kde', None)
        self._mean_absolute_error = model_data.get('mean_absolute_error', None)
        print(f"模型已从 {path} 加载")
        
        return self
    
    def get_feature_importance(self, top_n=None):
        if 0.5 not in self.models:
            return None
        
        importance = self.models[0.5].feature_importance()
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance,
            'importance_pct': importance / importance.sum() * 100
        }).sort_values('importance', ascending=False)
        
        if top_n:
            importance_df = importance_df.head(top_n)
        
        return importance_df


def train_model(use_cv=False, confidence_levels=None):
    print("加载训练数据...")
    df = pd.read_csv(Config.DATA_PATH)
    print(f"加载了 {len(df)} 条数据")
    
    model = DeliveryTimeModel(confidence_levels=confidence_levels)
    metrics = model.train(df, use_cross_validation=use_cv)
    model.save()
    
    print("\n特征重要性:")
    importance = model.get_feature_importance(10)
    print(importance)
    
    return model, metrics


if __name__ == '__main__':
    train_model()
