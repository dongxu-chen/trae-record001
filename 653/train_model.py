import pandas as pd
import numpy as np
import joblib
import os
import shap
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy import stats
from feature_engineering import FeatureEngineer


class SalaryPredictor:
    def __init__(self, save_dir: str = "models"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        self.model_lower = None
        self.model_upper = None
        self.feature_engineer = FeatureEngineer(save_dir)
        self.feature_names = []
        
        self.residual_stats = None
        self.shap_explainer_lower = None
        self.shap_explainer_upper = None
        
    def train(self, df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42):
        import sys
        print("开始特征工程...", flush=True)
        X, self.feature_names = self.feature_engineer.fit_transform(df)
        y_lower = df["薪资下限"].values
        y_upper = df["薪资上限"].values
        
        print(f"特征矩阵形状: {X.shape}", flush=True)
        print(f"特征数量: {len(self.feature_names)}", flush=True)
        
        X_train, X_test, y_lower_train, y_lower_test, y_upper_train, y_upper_test = train_test_split(
            X, y_lower, y_upper, test_size=test_size, random_state=random_state
        )
        
        print("\n训练薪资下限预测模型...", flush=True)
        self.model_lower = self._train_xgb_model(X_train, y_lower_train, "lower")
        self._evaluate_model(self.model_lower, X_test, y_lower_test, "薪资下限")
        
        print("\n训练薪资上限预测模型...", flush=True)
        self.model_upper = self._train_xgb_model(X_train, y_upper_train, "upper")
        self._evaluate_model(self.model_upper, X_test, y_upper_test, "薪资上限")
        
        print("\n计算残差统计用于异常检测...", flush=True)
        pred_lower_train = self.model_lower.predict(X_train)
        pred_upper_train = self.model_upper.predict(X_train)
        
        residuals_lower = y_lower_train - pred_lower_train
        residuals_upper = y_upper_train - pred_upper_train
        
        self.residual_stats = {
            "lower_mean": np.mean(residuals_lower),
            "lower_std": np.std(residuals_lower),
            "upper_mean": np.mean(residuals_upper),
            "upper_std": np.std(residuals_upper),
            "lower_iqr": stats.iqr(residuals_lower),
            "upper_iqr": stats.iqr(residuals_upper),
            "lower_q1": np.percentile(residuals_lower, 25),
            "lower_q3": np.percentile(residuals_lower, 75),
            "upper_q1": np.percentile(residuals_upper, 25),
            "upper_q3": np.percentile(residuals_upper, 75)
        }
        
        print("\n保存模型...", flush=True)
        self.save()
        
        print("\n初始化SHAP解释器...", flush=True)
        try:
            self.shap_explainer_lower = shap.TreeExplainer(self.model_lower)
            self.shap_explainer_upper = shap.TreeExplainer(self.model_upper)
            print("SHAP解释器初始化成功", flush=True)
        except Exception as e:
            print(f"SHAP初始化警告: {e}", flush=True)
            print("将在需要时动态初始化SHAP解释器", flush=True)
        
        self.save()
        
        print("\n模型训练完成！", flush=True)
        
        return {
            "X_train": X_train,
            "X_test": X_test,
            "y_lower_train": y_lower_train,
            "y_lower_test": y_lower_test,
            "y_upper_train": y_upper_train,
            "y_upper_test": y_upper_test
        }
    
    def _train_xgb_model(self, X_train: np.ndarray, y_train: np.ndarray, name: str) -> XGBRegressor:
        params = {
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42
        }
        
        model = XGBRegressor(**params)
        model.fit(X_train, y_train)
        
        return model
    
    def _evaluate_model(self, model: XGBRegressor, X_test: np.ndarray, y_test: np.ndarray, name: str):
        y_pred = model.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print(f"  {name}模型评估:", flush=True)
        print(f"    MAE: {mae:.2f}", flush=True)
        print(f"    RMSE: {rmse:.2f}", flush=True)
        print(f"    R2: {r2:.4f}", flush=True)
        
        return mae, rmse, r2
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X = self.feature_engineer.transform(df)
        
        pred_lower = self.model_lower.predict(X)
        pred_upper = self.model_upper.predict(X)
        
        pred_lower = np.maximum(pred_lower, 5000)
        pred_upper = np.maximum(pred_upper, pred_lower + 2000)
        
        result = df.copy()
        result["预测薪资下限"] = pred_lower.round().astype(int)
        result["预测薪资上限"] = pred_upper.round().astype(int)
        result["预测薪资均值"] = ((pred_lower + pred_upper) / 2).round().astype(int)
        
        return result
    
    def get_feature_importance(self, top_n: int = 20) -> dict:
        importance_lower = self.model_lower.feature_importances_
        importance_upper = self.model_upper.feature_importances_
        
        importance_avg = (importance_lower + importance_upper) / 2
        
        importance_df = pd.DataFrame({
            "feature": self.feature_names,
            "importance": importance_avg,
            "importance_lower": importance_lower,
            "importance_upper": importance_upper
        })
        
        importance_df = importance_df.sort_values("importance", ascending=False).head(top_n)
        
        return {
            "top_features": importance_df["feature"].tolist(),
            "top_importance": importance_df["importance"].tolist(),
            "importance_df": importance_df
        }
    
    def get_shap_analysis(self, X: np.ndarray, sample_idx: int = 0) -> dict:
        if self.shap_explainer_lower is None:
            self.shap_explainer_lower = shap.TreeExplainer(self.model_lower)
        if self.shap_explainer_upper is None:
            self.shap_explainer_upper = shap.TreeExplainer(self.model_upper)
        
        shap_values_lower = self.shap_explainer_lower.shap_values(X)
        shap_values_upper = self.shap_explainer_upper.shap_values(X)
        
        shap_values_avg = (shap_values_lower + shap_values_upper) / 2
        
        sample_shap = shap_values_avg[sample_idx]
        feature_shap_df = pd.DataFrame({
            "feature": self.feature_names,
            "shap_value": np.abs(sample_shap),
            "shap_value_signed": sample_shap
        })
        
        feature_shap_df = feature_shap_df.sort_values("shap_value", ascending=False)
        
        return {
            "shap_values_lower": shap_values_lower,
            "shap_values_upper": shap_values_upper,
            "shap_values_avg": shap_values_avg,
            "feature_shap_df": feature_shap_df,
            "base_value_lower": self.shap_explainer_lower.expected_value,
            "base_value_upper": self.shap_explainer_upper.expected_value
        }
    
    def detect_anomaly(self, df: pd.DataFrame, threshold: float = 2.5) -> pd.DataFrame:
        X = self.feature_engineer.transform(df)
        
        pred_lower = self.model_lower.predict(X)
        pred_upper = self.model_upper.predict(X)
        
        actual_lower = df["薪资下限"].values if "薪资下限" in df.columns else pred_lower
        actual_upper = df["薪资上限"].values if "薪资上限" in df.columns else pred_upper
        
        residuals_lower = actual_lower - pred_lower
        residuals_upper = actual_upper - pred_upper
        
        z_score_lower = (residuals_lower - self.residual_stats["lower_mean"]) / self.residual_stats["lower_std"]
        z_score_upper = (residuals_upper - self.residual_stats["upper_mean"]) / self.residual_stats["upper_std"]
        
        is_outlier_z = (np.abs(z_score_lower) > threshold) | (np.abs(z_score_upper) > threshold)
        
        lower_threshold_low = self.residual_stats["lower_q1"] - 1.5 * self.residual_stats["lower_iqr"]
        lower_threshold_high = self.residual_stats["lower_q3"] + 1.5 * self.residual_stats["lower_iqr"]
        upper_threshold_low = self.residual_stats["upper_q1"] - 1.5 * self.residual_stats["upper_iqr"]
        upper_threshold_high = self.residual_stats["upper_q3"] + 1.5 * self.residual_stats["upper_iqr"]
        
        is_outlier_iqr = (
            (residuals_lower < lower_threshold_low) | (residuals_lower > lower_threshold_high) |
            (residuals_upper < upper_threshold_low) | (residuals_upper > upper_threshold_high)
        )
        
        result = df.copy()
        result["预测薪资下限"] = pred_lower.round().astype(int)
        result["预测薪资上限"] = pred_upper.round().astype(int)
        result["残差_下限"] = residuals_lower.round(2)
        result["残差_上限"] = residuals_upper.round(2)
        result["Z分数_下限"] = z_score_lower.round(4)
        result["Z分数_上限"] = z_score_upper.round(4)
        result["是否异常(Z分数)"] = is_outlier_z
        result["是否异常(IQR)"] = is_outlier_iqr
        result["异常类型"] = "正常"
        
        for i in range(len(result)):
            if is_outlier_z[i] or is_outlier_iqr[i]:
                if residuals_lower[i] > 0 or residuals_upper[i] > 0:
                    result.loc[i, "异常类型"] = "薪资偏高"
                else:
                    result.loc[i, "异常类型"] = "薪资偏低"
        
        return result
    
    def save(self):
        joblib.dump(self.model_lower, os.path.join(self.save_dir, "model_lower.pkl"))
        joblib.dump(self.model_upper, os.path.join(self.save_dir, "model_upper.pkl"))
        joblib.dump(self.residual_stats, os.path.join(self.save_dir, "residual_stats.pkl"))
        joblib.dump(self.shap_explainer_lower, os.path.join(self.save_dir, "shap_explainer_lower.pkl"))
        joblib.dump(self.shap_explainer_upper, os.path.join(self.save_dir, "shap_explainer_upper.pkl"))
    
    def load(self):
        self.feature_engineer.load()
        self.feature_names = joblib.load(os.path.join(self.save_dir, "feature_names.pkl"))
        self.model_lower = joblib.load(os.path.join(self.save_dir, "model_lower.pkl"))
        self.model_upper = joblib.load(os.path.join(self.save_dir, "model_upper.pkl"))
        self.residual_stats = joblib.load(os.path.join(self.save_dir, "residual_stats.pkl"))
        self.shap_explainer_lower = joblib.load(os.path.join(self.save_dir, "shap_explainer_lower.pkl"))
        self.shap_explainer_upper = joblib.load(os.path.join(self.save_dir, "shap_explainer_upper.pkl"))


if __name__ == "__main__":
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    print(f"加载数据: {len(df)} 条")
    
    predictor = SalaryPredictor()
    data = predictor.train(df)
    
    print("\n" + "="*50)
    print("测试预测功能...")
    test_df = df.sample(5, random_state=42)
    predictions = predictor.predict(test_df)
    print(predictions[["岗位标题", "地区", "公司规模", "学历要求", "薪资下限", "薪资上限", "预测薪资下限", "预测薪资上限"]])
    
    print("\n" + "="*50)
    print("测试异常检测...")
    anomaly_df = predictor.detect_anomaly(df.head(20))
    print(anomaly_df[["岗位标题", "薪资下限", "薪资上限", "预测薪资下限", "预测薪资上限", "是否异常(Z分数)", "异常类型"]])
    
    print("\n" + "="*50)
    print("特征重要性Top 10...")
    importance = predictor.get_feature_importance(top_n=10)
    for feat, imp in zip(importance["top_features"], importance["top_importance"]):
        print(f"  {feat}: {imp:.4f}")
