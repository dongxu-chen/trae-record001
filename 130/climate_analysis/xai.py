import xarray as xr
import numpy as np
from typing import Optional, Tuple, Dict, List, Union
import logging
from pathlib import Path
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("shap库未安装，SHAP功能将不可用")


try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import r2_score, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn未安装，机器学习功能将不可用")


class SHAPExplainer:
    def __init__(self, model=None, model_type: str = "auto"):
        if not SHAP_AVAILABLE:
            raise ImportError("请先安装shap库: pip install shap")
        if not SKLEARN_AVAILABLE:
            raise ImportError("请先安装scikit-learn: pip install scikit-learn")

        self.model = model
        self.model_type = model_type
        self.explainer = None
        self.shap_values = None
        self.feature_names = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None

    def prepare_data(
        self,
        predictors: xr.DataArray,
        predictand: xr.DataArray,
        target_location: Optional[Tuple[float, float]] = None,
        flatten_spatial: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        logger.info("准备SHAP分析数据...")

        if flatten_spatial:
            X_flat = predictors.stack(spatial=["lat", "lon"])
            y_flat = predictand.stack(spatial=["lat", "lon"])

            valid_mask = ~np.isnan(X_flat).any(dim="time") & ~np.isnan(y_flat).any(dim="time")
            X = X_flat.where(valid_mask, drop=True).values.T
            y = y_flat.where(valid_mask, drop=True).values.T

            self.feature_names = [f"loc_{i}" for i in range(X.shape[1])]
        else:
            if target_location is None:
                raise ValueError("需要指定target_location参数 (lat, lon)")

            lat, lon = target_location
            X = predictors.values.reshape(predictors.shape[0], -1)
            y = predictand.sel(lat=lat, lon=lon, method="nearest").values

            valid_mask = ~np.isnan(y)
            X = X[valid_mask]
            y = y[valid_mask]

            self.feature_names = [f"lat_{i}_lon_{j}" for i in range(predictors.shape[1])
                                  for j in range(predictors.shape[2])]

        logger.info(f"数据形状: X={X.shape}, y={y.shape}")
        return X, y

    def train_model(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model_type: str = "random_forest",
        test_size: float = 0.3,
        random_state: int = 42,
        **model_kwargs
    ):
        logger.info(f"训练{model_type}模型...")

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        if model_type == "random_forest":
            default_kwargs = {"n_estimators": 100, "random_state": random_state}
            default_kwargs.update(model_kwargs)
            self.model = RandomForestRegressor(**default_kwargs)
        elif model_type == "gradient_boosting":
            default_kwargs = {"n_estimators": 100, "random_state": random_state}
            default_kwargs.update(model_kwargs)
            self.model = GradientBoostingRegressor(**default_kwargs)
        elif model_type == "linear":
            self.model = LinearRegression(**model_kwargs)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        self.model.fit(self.X_train, self.y_train)

        y_pred = self.model.predict(self.X_test)
        r2 = r2_score(self.y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(self.y_test, y_pred))

        logger.info(f"模型训练完成 - R²: {r2:.4f}, RMSE: {rmse:.4f}")
        return self.model

    def compute_shap_values(
        self,
        X: Optional[np.ndarray] = None,
        explainer_type: str = "auto",
        **kwargs
    ) -> np.ndarray:
        logger.info("计算SHAP值...")

        if self.model is None:
            raise ValueError("请先调用 train_model() 训练模型")

        if X is None:
            X = self.X_test

        if explainer_type == "auto":
            if hasattr(self.model, "tree_") or hasattr(self.model, "estimators_"):
                self.explainer = shap.TreeExplainer(self.model, **kwargs)
            else:
                self.explainer = shap.LinearExplainer(self.model, X, **kwargs)
        elif explainer_type == "tree":
            self.explainer = shap.TreeExplainer(self.model, **kwargs)
        elif explainer_type == "linear":
            self.explainer = shap.LinearExplainer(self.model, X, **kwargs)
        elif explainer_type == "kernel":
            self.explainer = shap.KernelExplainer(self.model.predict, X, **kwargs)
        else:
            raise ValueError(f"不支持的解释器类型: {explainer_type}")

        self.shap_values = self.explainer.shap_values(X)

        if isinstance(self.shap_values, list):
            self.shap_values = self.shap_values[1]

        logger.info(f"SHAP值计算完成，形状: {self.shap_values.shape}")
        return self.shap_values

    def feature_importance(self, top_n: int = 20) -> xr.Dataset:
        if self.shap_values is None:
            raise ValueError("请先调用 compute_shap_values() 计算SHAP值")

        mean_abs_shap = np.mean(np.abs(self.shap_values), axis=0)

        importance_df = xr.Dataset({
            "feature_name": ("feature", self.feature_names),
            "mean_abs_shap": ("feature", mean_abs_shap),
            "std_shap": ("feature", np.std(self.shap_values, axis=0))
        })

        sorted_idx = np.argsort(mean_abs_shap)[::-1]
        importance_df = importance_df.isel(feature=sorted_idx[:top_n])

        return importance_df

    def shap_to_xarray(
        self,
        original_dims: Tuple[int, int],
        lat_coords: np.ndarray,
        lon_coords: np.ndarray
    ) -> xr.DataArray:
        if self.shap_values is None:
            raise ValueError("请先调用 compute_shap_values() 计算SHAP值")

        mean_shap = np.mean(self.shap_values, axis=0)
        mean_shap_2d = mean_shap.reshape(original_dims)

        shap_da = xr.DataArray(
            mean_shap_2d,
            dims=["lat", "lon"],
            coords={"lat": lat_coords, "lon": lon_coords}
        )

        return shap_da

    def summary_plot(
        self,
        output_path: Optional[str] = None,
        max_display: int = 20,
        plot_type: str = "bar"
    ):
        if self.shap_values is None:
            raise ValueError("请先调用 compute_shap_values() 计算SHAP值")

        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            self.shap_values,
            self.X_test if self.X_test is not None else self.X_train,
            feature_names=self.feature_names,
            max_display=max_display,
            plot_type=plot_type,
            show=False
        )
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info(f"SHAP摘要图已保存到: {output_path}")
        plt.close()

    def dependence_plot(
        self,
        feature_index: int,
        output_path: Optional[str] = None,
        interaction_index: Optional[str] = "auto"
    ):
        if self.shap_values is None:
            raise ValueError("请先调用 compute_shap_values() 计算SHAP值")

        plt.figure(figsize=(10, 6))
        shap.dependence_plot(
            feature_index,
            self.shap_values,
            self.X_test if self.X_test is not None else self.X_train,
            feature_names=self.feature_names,
            interaction_index=interaction_index,
            show=False
        )
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info(f"SHAP依赖图已保存到: {output_path}")
        plt.close()

    def force_plot(
        self,
        sample_index: int = 0,
        output_path: Optional[str] = None
    ):
        if self.shap_values is None:
            raise ValueError("请先调用 compute_shap_values() 计算SHAP值")

        plt.figure(figsize=(12, 4))
        shap.force_plot(
            self.explainer.expected_value,
            self.shap_values[sample_index, :],
            self.X_test[sample_index, :] if self.X_test is not None else self.X_train[sample_index, :],
            feature_names=self.feature_names,
            matplotlib=True,
            show=False
        )
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info(f"SHAP力图已保存到: {output_path}")
        plt.close()


class FeatureAttribution:
    def __init__(self):
        self.attributions = None

    def linear_attribution(
        self,
        predictors: xr.DataArray,
        predictand: xr.DataArray
    ) -> xr.DataArray:
        logger.info("计算线性回归特征归因...")

        from scipy.stats import linregress

        X_flat = predictors.stack(spatial=["lat", "lon"])
        y_flat = predictand.stack(spatial=["lat", "lon"])

        valid_mask = ~np.isnan(X_flat).any(dim="time") & ~np.isnan(y_flat).any(dim="time")
        X_valid = X_flat.where(valid_mask, drop=True).values
        y_valid = y_flat.where(valid_mask, drop=True).values

        coeffs = np.zeros(X_flat.shape[1])

        for i in range(X_flat.shape[1]):
            mask = ~np.isnan(X_valid[:, i]) & ~np.isnan(y_valid[:, i])
            if mask.sum() > 5:
                slope, intercept, r, p, se = linregress(X_valid[mask, i], y_valid[mask, i])
                coeffs[i] = slope

        coef_da = xr.DataArray(
            coeffs,
            dims=["spatial"],
            coords={"spatial": X_flat.coords["spatial"]}
        )

        return coef_da.unstack("spatial")

    def correlation_attribution(
        self,
        predictors: xr.DataArray,
        predictand: xr.DataArray
    ) -> xr.DataArray:
        logger.info("计算相关系数特征归因...")

        X_flat = predictors.stack(spatial=["lat", "lon"])
        y_flat = predictand.stack(spatial=["lat", "lon"])

        valid_mask = ~np.isnan(X_flat).any(dim="time") & ~np.isnan(y_flat).any(dim="time")
        X_valid = X_flat.where(valid_mask, drop=True).values
        y_valid = y_flat.where(valid_mask, drop=True).values

        correlations = np.zeros(X_flat.shape[1])

        for i in range(X_flat.shape[1]):
            mask = ~np.isnan(X_valid[:, i]) & ~np.isnan(y_valid[:, i])
            if mask.sum() > 5:
                correlations[i] = np.corrcoef(X_valid[mask, i], y_valid[mask, i])[0, 1]

        corr_da = xr.DataArray(
            correlations,
            dims=["spatial"],
            coords={"spatial": X_flat.coords["spatial"]}
        )

        return corr_da.unstack("spatial")

    def composite_analysis(
        self,
        data: xr.DataArray,
        index: xr.DataArray,
        n_quantiles: int = 3
    ) -> xr.Dataset:
        logger.info(f"进行合成分析，分为 {n_quantiles} 个分位数...")

        quantiles = np.quantile(index, np.linspace(0, 1, n_quantiles + 1))
        composites = []

        for i in range(n_quantiles):
            mask = (index >= quantiles[i]) & (index < quantiles[i + 1])
            composite = data.where(mask).mean(dim="time")
            composites.append(composite)

        ds = xr.concat(composites, dim="quantile")
        ds["quantile"] = np.arange(n_quantiles)
        ds["quantile_bounds"] = ("quantile", [f"{quantiles[i]:.2f}-{quantiles[i+1]:.2f}"
                                               for i in range(n_quantiles)])

        return ds.to_dataset(name="composite")


class PermutationImportance:
    def __init__(self, model=None):
        self.model = model
        self.importances = None

    def compute(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_permutations: int = 100,
        random_state: int = 42,
        scoring: str = "r2"
    ) -> xr.Dataset:
        logger.info(f"计算排列重要性，{n_permutations}次排列...")

        if self.model is None:
            raise ValueError("请先训练模型")

        np.random.seed(random_state)

        baseline_score = self._score(X, y, scoring)
        importances = np.zeros((X.shape[1], n_permutations))

        for i in range(X.shape[1]):
            for j in range(n_permutations):
                X_permuted = X.copy()
                X_permuted[:, i] = np.random.permutation(X_permuted[:, i])
                permuted_score = self._score(X_permuted, y, scoring)
                importances[i, j] = baseline_score - permuted_score

        self.importances = xr.Dataset({
            "importance_mean": ("feature", np.mean(importances, axis=1)),
            "importance_std": ("feature", np.std(importances, axis=1)),
            "baseline_score": baseline_score
        })

        logger.info("排列重要性计算完成")
        return self.importances

    def _score(self, X: np.ndarray, y: np.ndarray, scoring: str) -> float:
        y_pred = self.model.predict(X)

        if scoring == "r2":
            return r2_score(y, y_pred)
        elif scoring == "mse":
            return -mean_squared_error(y, y_pred)
        elif scoring == "rmse":
            return -np.sqrt(mean_squared_error(y, y_pred))
        else:
            raise ValueError(f"不支持的评分方法: {scoring}")

    def plot_importance(
        self,
        output_path: Optional[str] = None,
        top_n: int = 20,
        feature_names: Optional[List[str]] = None
    ):
        if self.importances is None:
            raise ValueError("请先调用 compute() 计算排列重要性")

        importances = self.importances.importance_mean.values
        std = self.importances.importance_std.values

        sorted_idx = np.argsort(importances)[::-1]
        top_idx = sorted_idx[:top_n]

        plt.figure(figsize=(10, 8))
        y_pos = np.arange(len(top_idx))

        plt.barh(y_pos, importances[top_idx], xerr=std[top_idx], align="center")
        plt.yticks(y_pos, feature_names[top_idx] if feature_names else top_idx)
        plt.xlabel("Permutation Importance")
        plt.title("Feature Permutation Importance")
        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info(f"排列重要性图已保存到: {output_path}")
        plt.close()
