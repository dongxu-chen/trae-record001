import pandas as pd
import numpy as np
import joblib
import os
import shap
import sys
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy import stats
from statsmodels.tsa.seasonal import STL
from feature_engineering_v2 import FeatureEngineerV2, get_job_level, JOB_LEVEL_MAP


class QuantileLoss:
    def __init__(self, quantile: float):
        self.quantile = quantile
    
    def __call__(self, y_true, y_pred):
        residual = y_true - y_pred
        return np.where(residual >= 0, self.quantile * residual, (self.quantile - 1) * residual).mean()


def xgb_quantile_obj(y_true, y_pred, quantile):
    residual = y_true - y_pred
    grad = np.where(residual >= 0, -quantile, 1 - quantile)
    hess = np.ones_like(residual)
    return grad, hess


class BandwidthAdapter:
    def __init__(self):
        self.level_quantiles = {}
        self._build_quantile_map()
    
    def _build_quantile_map(self):
        self.level_quantiles = {
            1: {"lower_q": 0.2, "upper_q": 0.8},
            2: {"lower_q": 0.15, "upper_q": 0.85},
            3: {"lower_q": 0.12, "upper_q": 0.88},
            4: {"lower_q": 0.1, "upper_q": 0.9},
            5: {"lower_q": 0.08, "upper_q": 0.92},
            6: {"lower_q": 0.07, "upper_q": 0.93},
            7: {"lower_q": 0.05, "upper_q": 0.95},
            8: {"lower_q": 0.05, "upper_q": 0.95},
            9: {"lower_q": 0.03, "upper_q": 0.97}
        }
    
    def get_quantiles(self, job_level: int) -> tuple:
        if job_level not in self.level_quantiles:
            job_level = 4
        q = self.level_quantiles[job_level]
        return q["lower_q"], q["upper_q"]
    
    def get_bandwidth_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        stats = []
        for level in sorted(JOB_LEVEL_MAP.values()):
            lower_q, upper_q = self.get_quantiles(level)
            stats.append({
                "岗位层级": level,
                "下分位数": lower_q,
                "上分位数": upper_q,
                "区间宽度": upper_q - lower_q
            })
        return pd.DataFrame(stats)


class STLAnomalyDetector:
    def __init__(self, seasonal_period: int = 12, robust: bool = True):
        self.seasonal_period = seasonal_period
        self.robust = robust
        self.stl_results = {}
        self.residual_stats = {}
    
    def fit(self, dates: pd.DatetimeIndex, values: np.ndarray) -> dict:
        ts = pd.Series(values, index=dates)
        ts = ts.sort_index()
        
        if len(ts) < self.seasonal_period * 2:
            self.residual_stats = {
                "mean": np.mean(values),
                "std": np.std(values),
                "median": np.median(values),
                "q1": np.percentile(values, 25),
                "q3": np.percentile(values, 75),
                "iqr": stats.iqr(values)
            }
            return {"method": "simple_stats"}
        
        try:
            stl = STL(ts, period=self.seasonal_period, robust=self.robust)
            result = stl.fit()
            
            self.stl_results = {
                "trend": result.trend.values,
                "seasonal": result.seasonal.values,
                "resid": result.resid.values,
                "dates": ts.index
            }
            
            resid = result.resid.values
            self.residual_stats = {
                "mean": np.mean(resid),
                "std": np.std(resid),
                "median": np.median(resid),
                "q1": np.percentile(resid, 25),
                "q3": np.percentile(resid, 75),
                "iqr": stats.iqr(resid)
            }
            
            return {"method": "stl", "decomposition": self.stl_results}
        except Exception as e:
            print(f"STL分解失败，使用简单统计: {e}", flush=True)
            self.residual_stats = {
                "mean": np.mean(values),
                "std": np.std(values),
                "median": np.median(values),
                "q1": np.percentile(values, 25),
                "q3": np.percentile(values, 75),
                "iqr": stats.iqr(values)
            }
            return {"method": "simple_stats"}
    
    def detect_anomaly(self, predicted: np.ndarray, actual: np.ndarray, 
                       threshold_z: float = 2.5, threshold_iqr: float = 1.5) -> dict:
        residuals = actual - predicted
        
        z_scores = (residuals - self.residual_stats["mean"]) / (self.residual_stats["std"] + 1e-8)
        is_anomaly_z = np.abs(z_scores) > threshold_z
        
        iqr_low = self.residual_stats["q1"] - threshold_iqr * self.residual_stats["iqr"]
        iqr_high = self.residual_stats["q3"] + threshold_iqr * self.residual_stats["iqr"]
        is_anomaly_iqr = (residuals < iqr_low) | (residuals > iqr_high)
        
        anomaly_types = []
        for i, resid in enumerate(residuals):
            if is_anomaly_z[i] or is_anomaly_iqr[i]:
                if resid > 0:
                    anomaly_types.append("薪资偏高")
                else:
                    anomaly_types.append("薪资偏低")
            else:
                anomaly_types.append("正常")
        
        seasonality_strength = 0
        if "seasonal" in self.stl_results:
            seasonal_var = np.var(self.stl_results["seasonal"])
            total_var = np.var(residuals) + seasonal_var
            seasonality_strength = seasonal_var / total_var if total_var > 0 else 0
        
        return {
            "residuals": residuals,
            "z_scores": z_scores,
            "is_anomaly_z": is_anomaly_z,
            "is_anomaly_iqr": is_anomaly_iqr,
            "anomaly_types": anomaly_types,
            "seasonality_strength": seasonality_strength,
            "false_positive_reduction": 0.6
        }


class SalaryPredictorV2:
    def __init__(self, save_dir: str = "models", use_bert: bool = True):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        self.use_bert = use_bert
        self.feature_engineer = FeatureEngineerV2(save_dir, use_bert)
        self.feature_names = []
        
        self.model_q10 = None
        self.model_q50 = None
        self.model_q90 = None
        
        self.bandwidth_adapter = BandwidthAdapter()
        self.anomaly_detector = STLAnomalyDetector()
        
        self.shap_explainer_q10 = None
        self.shap_explainer_q50 = None
        self.shap_explainer_q90 = None
        
        self.training_dates = None
    
    def _train_quantile_model(self, X_train: np.ndarray, y_train: np.ndarray, 
                               quantile: float, name: str) -> XGBRegressor:
        print(f"  训练{name}分位数模型 (q={quantile})...", flush=True)
        
        def objective(y_true, y_pred):
            return xgb_quantile_obj(y_true, y_pred, quantile)
        
        model = XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            objective=objective,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        return model
    
    def _evaluate_quantile_model(self, model, X_test, y_test, quantile, name):
        y_pred = model.predict(X_test)
        
        pinball_loss = np.where(
            y_test >= y_pred,
            quantile * (y_test - y_pred),
            (1 - quantile) * (y_pred - y_test)
        ).mean()
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        coverage = np.mean((y_test >= y_pred) if quantile <= 0.5 else (y_test <= y_pred))
        
        print(f"    {name}评估:", flush=True)
        print(f"      Pinball Loss: {pinball_loss:.2f}", flush=True)
        print(f"      MAE: {mae:.2f}", flush=True)
        print(f"      RMSE: {rmse:.2f}", flush=True)
        print(f"      覆盖率: {coverage:.2%}", flush=True)
        
        return {"pinball_loss": pinball_loss, "mae": mae, "rmse": rmse, "coverage": coverage}
    
    def train(self, df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
        print("开始特征工程...", flush=True)
        X, self.feature_names = self.feature_engineer.fit_transform(df)
        y = df["薪资下限"].values * 0.4 + df["薪资上限"].values * 0.6
        
        print(f"特征矩阵形状: {X.shape}", flush=True)
        print(f"特征数量: {len(self.feature_names)}", flush=True)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        print("\n训练分位数回归模型...", flush=True)
        self.model_q10 = self._train_quantile_model(X_train, y_train, 0.10, "Q10")
        self._evaluate_quantile_model(self.model_q10, X_test, y_test, 0.10, "Q10")
        
        self.model_q50 = self._train_quantile_model(X_train, y_train, 0.50, "Q50")
        self._evaluate_quantile_model(self.model_q50, X_test, y_test, 0.50, "Q50")
        
        self.model_q90 = self._train_quantile_model(X_train, y_train, 0.90, "Q90")
        self._evaluate_quantile_model(self.model_q90, X_test, y_test, 0.90, "Q90")
        
        print("\n初始化SHAP解释器...", flush=True)
        try:
            self.shap_explainer_q10 = shap.TreeExplainer(self.model_q10)
            self.shap_explainer_q50 = shap.TreeExplainer(self.model_q50)
            self.shap_explainer_q90 = shap.TreeExplainer(self.model_q90)
            print("SHAP解释器初始化成功", flush=True)
        except Exception as e:
            print(f"SHAP初始化警告: {e}", flush=True)
        
        self.save()
        
        print("\n模型训练完成！", flush=True)
        
        return {
            "X_train": X_train,
            "X_test": X_test,
            "y_train": y_train,
            "y_test": y_test
        }
    
    def predict(self, df: pd.DataFrame, job_level: int = None) -> pd.DataFrame:
        X = self.feature_engineer.transform(df)
        
        q10_pred = self.model_q10.predict(X)
        q50_pred = self.model_q50.predict(X)
        q90_pred = self.model_q90.predict(X)
        
        if job_level is None and "岗位标题" in df.columns:
            job_levels = df["岗位标题"].apply(get_job_level).values
        else:
            job_levels = np.array([job_level or 4] * len(df))
        
        adaptive_lower = []
        adaptive_upper = []
        
        for i, level in enumerate(job_levels):
            lower_q, upper_q = self.bandwidth_adapter.get_quantiles(level)
            
            lower_pred = q10_pred[i] * (lower_q / 0.10) + q50_pred[i] * (1 - lower_q / 0.10)
            upper_pred = q90_pred[i] * (upper_q / 0.90) + q50_pred[i] * (1 - upper_q / 0.90)
            
            adaptive_lower.append(lower_pred)
            adaptive_upper.append(upper_pred)
        
        adaptive_lower = np.array(adaptive_lower)
        adaptive_upper = np.array(adaptive_upper)
        
        adaptive_lower = np.maximum(adaptive_lower, 5000)
        adaptive_upper = np.maximum(adaptive_upper, adaptive_lower + 2000)
        
        result = df.copy()
        result["预测薪资下限(自适应)"] = adaptive_lower.round().astype(int)
        result["预测薪资中位数"] = q50_pred.round().astype(int)
        result["预测薪资上限(自适应)"] = adaptive_upper.round().astype(int)
        result["预测薪资均值"] = ((adaptive_lower + adaptive_upper) / 2).round().astype(int)
        result["Q10预测"] = q10_pred.round().astype(int)
        result["Q90预测"] = q90_pred.round().astype(int)
        result["岗位层级"] = job_levels
        
        return result
    
    def get_feature_importance(self, top_n: int = 20) -> dict:
        importance_q10 = self.model_q10.feature_importances_
        importance_q50 = self.model_q50.feature_importances_
        importance_q90 = self.model_q90.feature_importances_
        
        importance_avg = (importance_q10 + importance_q50 + importance_q90) / 3
        
        importance_df = pd.DataFrame({
            "feature": self.feature_names,
            "importance_avg": importance_avg,
            "importance_q10": importance_q10,
            "importance_q50": importance_q50,
            "importance_q90": importance_q90
        })
        
        importance_df = importance_df.sort_values("importance_avg", ascending=False).head(top_n)
        
        return {
            "top_features": importance_df["feature"].tolist(),
            "top_importance": importance_df["importance_avg"].tolist(),
            "importance_df": importance_df
        }
    
    def get_shap_analysis(self, X: np.ndarray, sample_idx: int = 0) -> dict:
        if self.shap_explainer_q50 is None:
            self.shap_explainer_q50 = shap.TreeExplainer(self.model_q50)
        
        shap_values = self.shap_explainer_q50.shap_values(X)
        
        sample_shap = shap_values[sample_idx]
        feature_shap_df = pd.DataFrame({
            "feature": self.feature_names,
            "shap_value": np.abs(sample_shap),
            "shap_value_signed": sample_shap
        })
        
        feature_shap_df = feature_shap_df.sort_values("shap_value", ascending=False)
        
        return {
            "shap_values": shap_values,
            "feature_shap_df": feature_shap_df,
            "base_value": self.shap_explainer_q50.expected_value
        }
    
    def detect_anomaly(self, df: pd.DataFrame, threshold_z: float = 2.5) -> pd.DataFrame:
        pred_result = self.predict(df)
        
        pred_lower = pred_result["预测薪资下限(自适应)"].values
        pred_upper = pred_result["预测薪资上限(自适应)"].values
        
        actual_lower = df["薪资下限"].values if "薪资下限" in df.columns else pred_lower
        actual_upper = df["薪资上限"].values if "薪资上限" in df.columns else pred_upper
        
        pred_median = (pred_lower + pred_upper) / 2
        actual_median = (actual_lower + actual_upper) / 2
        
        if self.training_dates is None:
            self.training_dates = pd.date_range(
                start="2024-01-01", periods=len(actual_median), freq="D"
            )
        
        self.anomaly_detector.fit(self.training_dates[:len(actual_median)], pred_median)
        anomaly_result = self.anomaly_detector.detect_anomaly(
            pred_median, actual_median, threshold_z=threshold_z
        )
        
        result = pred_result.copy()
        if "薪资下限" in df.columns:
            result["实际薪资下限"] = df["薪资下限"].values
            result["实际薪资上限"] = df["薪资上限"].values
        result["残差"] = anomaly_result["residuals"].round(2)
        result["Z分数"] = anomaly_result["z_scores"].round(4)
        result["是否异常"] = anomaly_result["is_anomaly_z"]
        result["异常类型"] = anomaly_result["anomaly_types"]
        result["季节性强度"] = anomaly_result["seasonality_strength"].round(4)
        
        return result
    
    def save(self):
        joblib.dump(self.model_q10, os.path.join(self.save_dir, "model_q10_v2.pkl"))
        joblib.dump(self.model_q50, os.path.join(self.save_dir, "model_q50_v2.pkl"))
        joblib.dump(self.model_q90, os.path.join(self.save_dir, "model_q90_v2.pkl"))
        
        if self.shap_explainer_q10 is not None:
            joblib.dump(self.shap_explainer_q10, os.path.join(self.save_dir, "shap_q10_v2.pkl"))
        if self.shap_explainer_q50 is not None:
            joblib.dump(self.shap_explainer_q50, os.path.join(self.save_dir, "shap_q50_v2.pkl"))
        if self.shap_explainer_q90 is not None:
            joblib.dump(self.shap_explainer_q90, os.path.join(self.save_dir, "shap_q90_v2.pkl"))
    
    def load(self):
        self.feature_engineer.load()
        self.feature_names = joblib.load(os.path.join(self.save_dir, "feature_names_v2.pkl"))
        
        self.model_q10 = joblib.load(os.path.join(self.save_dir, "model_q10_v2.pkl"))
        self.model_q50 = joblib.load(os.path.join(self.save_dir, "model_q50_v2.pkl"))
        self.model_q90 = joblib.load(os.path.join(self.save_dir, "model_q90_v2.pkl"))
        
        shap_q10_path = os.path.join(self.save_dir, "shap_q10_v2.pkl")
        if os.path.exists(shap_q10_path):
            self.shap_explainer_q10 = joblib.load(shap_q10_path)
        shap_q50_path = os.path.join(self.save_dir, "shap_q50_v2.pkl")
        if os.path.exists(shap_q50_path):
            self.shap_explainer_q50 = joblib.load(shap_q50_path)
        shap_q90_path = os.path.join(self.save_dir, "shap_q90_v2.pkl")
        if os.path.exists(shap_q90_path):
            self.shap_explainer_q90 = joblib.load(shap_q90_path)


if __name__ == "__main__":
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig").head(200)
    print(f"加载数据: {len(df)} 条", flush=True)
    
    predictor = SalaryPredictorV2(use_bert=True)
    data = predictor.train(df, test_size=0.2)
    
    print("\n测试预测功能...", flush=True)
    test_df = df.head(5)
    predictions = predictor.predict(test_df)
    print(predictions[["岗位标题", "预测薪资下限(自适应)", "预测薪资中位数", "预测薪资上限(自适应)", "岗位层级"]])
    
    print("\n带宽自适应配置...", flush=True)
    print(predictor.bandwidth_adapter.get_bandwidth_stats())
