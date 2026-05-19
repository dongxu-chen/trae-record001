import xarray as xr
import numpy as np
from typing import Optional, Tuple, Dict, List, Union
import logging
from pathlib import Path
from datetime import datetime
from scipy.stats import linregress
import pandas as pd

logger = logging.getLogger(__name__)


class CESMReader:
    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        self.data_dir = Path(data_dir) if data_dir else None
        self.ensemble_members = []
        self.variables = []

    def read_ensemble(
        self,
        variable: str,
        experiment: str = "historical",
        ensemble_members: Optional[List[str]] = None,
        **kwargs
    ) -> xr.DataArray:
        logger.info(f"读取CESM {experiment} 实验的 {variable} 变量...")

        if self.data_dir is None:
            logger.warning("未指定数据目录，使用模拟数据")
            return self._generate_mock_ensemble(variable)

        files = list(self.data_dir.glob(f"*{variable}*{experiment}*.nc"))
        if not files:
            raise FileNotFoundError(f"未找到 {variable} 的 {experiment} 实验数据")

        ds_list = []
        for f in files:
            ds = xr.open_dataset(f, **kwargs)
            ds_list.append(ds)

        ensemble = xr.concat(ds_list, dim="member")
        ensemble["member"] = np.arange(len(ds_list))
        self.ensemble_members = list(ensemble.member.values)
        self.variables.append(variable)

        logger.info(f"读取完成，共 {len(ds_list)} 个集合成员")
        return ensemble[variable]

    def _generate_mock_ensemble(self, variable: str) -> xr.DataArray:
        n_members = 10
        n_time = 240
        n_lat = 45
        n_lon = 90

        lat = np.linspace(-90, 90, n_lat)
        lon = np.linspace(0, 360, n_lon, endpoint=False)
        time = pd.date_range("2000-01", periods=n_time, freq="MS")

        base_field = 15 * np.cos(np.deg2rad(lat))[:, np.newaxis] - 5 * np.cos(2 * np.deg2rad(lat))[:, np.newaxis]
        trend = np.linspace(0, 2, n_time)[:, np.newaxis, np.newaxis]
        noise = np.random.randn(n_members, n_time, n_lat, n_lon) * 1.5

        data = base_field[np.newaxis, np.newaxis, :, :] + trend[np.newaxis, :, :, :] + noise

        da = xr.DataArray(
            data,
            dims=["member", "time", "lat", "lon"],
            coords={
                "member": np.arange(n_members),
                "time": time,
                "lat": lat,
                "lon": lon
            },
            name=variable
        )

        return da

    def read_single_member(
        self,
        variable: str,
        member_id: int,
        experiment: str = "historical",
        **kwargs
    ) -> xr.DataArray:
        ensemble = self.read_ensemble(variable, experiment, **kwargs)
        return ensemble.sel(member=member_id)

    def ensemble_mean(self, data: xr.DataArray) -> xr.DataArray:
        return data.mean(dim="member")

    def ensemble_spread(self, data: xr.DataArray) -> xr.DataArray:
        return data.std(dim="member")


class SeasonalPredictor:
    def __init__(self, training_data: Optional[xr.DataArray] = None):
        self.training_data = training_data
        self.model = None
        self.predictors = None
        self.predictand = None
        self.coefficients = None
        self.intercept = None

    def prepare_predictors(
        self,
        data: xr.DataArray,
        season: str = "DJF",
        lag_months: int = 1
    ) -> Tuple[xr.DataArray, xr.DataArray]:
        logger.info(f"准备季节预测因子，目标季节: {season}, 滞后: {lag_months}个月")

        seasonal_data = self._seasonal_mean(data, season)

        predictors = seasonal_data.shift(time=lag_months)
        predictand = seasonal_data

        valid_mask = ~np.isnan(predictors).any(dim=["lat", "lon"])
        predictors = predictors.where(valid_mask, drop=True)
        predictand = predictand.where(valid_mask, drop=True)

        self.predictors = predictors
        self.predictand = predictand

        return predictors, predictand

    def _seasonal_mean(self, data: xr.DataArray, season: str) -> xr.DataArray:
        season_months = {
            "DJF": [12, 1, 2],
            "MAM": [3, 4, 5],
            "JJA": [6, 7, 8],
            "SON": [9, 10, 11]
        }

        if season not in season_months:
            raise ValueError(f"不支持的季节: {season}，请使用 DJF, MAM, JJA, SON")

        months = season_months[season]
        seasonal = data.where(data.time.dt.month.isin(months)).groupby("time.year").mean(dim="time")
        seasonal = seasonal.rename({"year": "time"})

        return seasonal

    def fit_linear_regression(
        self,
        predictors: Optional[xr.DataArray] = None,
        predictand: Optional[xr.DataArray] = None
    ):
        logger.info("训练线性回归模型...")

        if predictors is None:
            predictors = self.predictors
        if predictand is None:
            predictand = self.predictand

        if predictors is None or predictand is None:
            raise ValueError("请先调用 prepare_predictors() 或提供预测因子和预测目标")

        X_flat = predictors.stack(spatial=["lat", "lon"])
        y_flat = predictand.stack(spatial=["lat", "lon"])

        valid_mask = ~np.isnan(X_flat).any(dim="time") & ~np.isnan(y_flat).any(dim="time")
        X_valid = X_flat.where(valid_mask, drop=True).values.T
        y_valid = y_flat.where(valid_mask, drop=True).values.T

        n_points = X_valid.shape[0]
        coeffs = np.zeros(n_points)
        intercepts = np.zeros(n_points)

        for i in range(n_points):
            mask = ~np.isnan(X_valid[i]) & ~np.isnan(y_valid[i])
            if mask.sum() > 5:
                slope, intercept, r, p, se = linregress(X_valid[i][mask], y_valid[i][mask])
                coeffs[i] = slope
                intercepts[i] = intercept

        coef_da = xr.DataArray(
            np.full(X_flat.shape[1], np.nan),
            dims=["spatial"],
            coords={"spatial": X_flat.coords["spatial"]}
        )
        coef_da.values[valid_mask.values] = coeffs
        self.coefficients = coef_da.unstack("spatial")

        intercept_da = xr.DataArray(
            np.full(X_flat.shape[1], np.nan),
            dims=["spatial"],
            coords={"spatial": X_flat.coords["spatial"]}
        )
        intercept_da.values[valid_mask.values] = intercepts
        self.intercept = intercept_da.unstack("spatial")

        logger.info("线性回归模型训练完成")
        return self.coefficients, self.intercept

    def predict(
        self,
        new_predictors: xr.DataArray,
        probabilistic: bool = False,
        n_ensemble: int = 10
    ) -> xr.DataArray:
        logger.info("进行季节预测...")

        if self.coefficients is None or self.intercept is None:
            raise ValueError("请先调用 fit_linear_regression() 训练模型")

        prediction = self.coefficients * new_predictors + self.intercept

        if probabilistic:
            residuals = self.predictand - (self.coefficients * self.predictors + self.intercept)
            residual_std = residuals.std(dim="time")

            ensemble_preds = []
            for i in range(n_ensemble):
                noise = xr.DataArray(
                    np.random.randn(*prediction.shape) * residual_std.values,
                    dims=prediction.dims,
                    coords=prediction.coords
                )
                ensemble_preds.append(prediction + noise)

            prediction = xr.concat(ensemble_preds, dim="ensemble")
            prediction["ensemble"] = np.arange(n_ensemble)

        logger.info("预测完成")
        return prediction

    def compute_anomaly_correlation(
        self,
        predicted: xr.DataArray,
        observed: xr.DataArray
    ) -> xr.DataArray:
        logger.info("计算异常相关系数 (ACC)...")

        pred_flat = predicted.stack(spatial=["lat", "lon"])
        obs_flat = observed.stack(spatial=["lat", "lon"])

        valid_mask = ~np.isnan(pred_flat).any(dim="time") & ~np.isnan(obs_flat).any(dim="time")

        acc_values = np.full(pred_flat.shape[1], np.nan)

        for i in range(pred_flat.shape[1]):
            if valid_mask[i]:
                pred_vals = pred_flat[:, i].values
                obs_vals = obs_flat[:, i].values
                mask = ~np.isnan(pred_vals) & ~np.isnan(obs_vals)
                if mask.sum() > 5:
                    acc_values[i] = np.corrcoef(pred_vals[mask], obs_vals[mask])[0, 1]

        acc_da = xr.DataArray(
            acc_values,
            dims=["spatial"],
            coords={"spatial": pred_flat.coords["spatial"]}
        )

        return acc_da.unstack("spatial")

    def compute_rmse(
        self,
        predicted: xr.DataArray,
        observed: xr.DataArray
    ) -> xr.DataArray:
        logger.info("计算均方根误差 (RMSE)...")
        rmse = np.sqrt(((predicted - observed) ** 2).mean(dim="time"))
        return rmse

    def save_model(self, output_path: str):
        ds = xr.Dataset({
            "coefficients": self.coefficients,
            "intercept": self.intercept
        })
        ds.to_netcdf(output_path)
        logger.info(f"预测模型已保存到: {output_path}")

    def load_model(self, model_path: str):
        ds = xr.open_dataset(model_path)
        self.coefficients = ds.coefficients
        self.intercept = ds.intercept
        logger.info(f"预测模型已从 {model_path} 加载")


class HybridForecast:
    def __init__(self):
        self.dynamical_model = None
        self.statistical_correction = None

    def bias_correction(
        self,
        model_output: xr.DataArray,
        observations: xr.DataArray,
        method: str = "quantile_mapping"
    ) -> xr.DataArray:
        logger.info(f"应用偏差校正方法: {method}")

        if method == "quantile_mapping":
            corrected = self._quantile_mapping(model_output, observations)
        elif method == "mean_adjustment":
            corrected = self._mean_adjustment(model_output, observations)
        else:
            raise ValueError(f"不支持的偏差校正方法: {method}")

        logger.info("偏差校正完成")
        return corrected

    def _quantile_mapping(
        self,
        model_output: xr.DataArray,
        observations: xr.DataArray
    ) -> xr.DataArray:
        model_flat = model_output.stack(spatial=["lat", "lon"])
        obs_flat = observations.stack(spatial=["lat", "lon"])

        corrected_values = np.zeros_like(model_flat.values)

        for i in range(model_flat.shape[1]):
            model_vals = model_flat[:, i].values
            obs_vals = obs_flat[:, i].values

            model_valid = model_vals[~np.isnan(model_vals)]
            obs_valid = obs_vals[~np.isnan(obs_vals)]

            if len(model_valid) > 10 and len(obs_valid) > 10:
                from scipy.interpolate import interp1d

                n_quantiles = 100
                quantiles = np.linspace(0, 1, n_quantiles)

                model_quantiles = np.quantile(model_valid, quantiles)
                obs_quantiles = np.quantile(obs_valid, quantiles)

                interp_func = interp1d(
                    model_quantiles,
                    obs_quantiles,
                    bounds_error=False,
                    fill_value="extrapolate"
                )

                corrected_values[:, i] = interp_func(model_vals)
            else:
                corrected_values[:, i] = model_vals

        corrected = xr.DataArray(
            corrected_values,
            dims=["time", "spatial"],
            coords={"time": model_flat.time, "spatial": model_flat.spatial}
        )

        return corrected.unstack("spatial")

    def _mean_adjustment(
        self,
        model_output: xr.DataArray,
        observations: xr.DataArray
    ) -> xr.DataArray:
        model_mean = model_output.mean(dim="time")
        obs_mean = observations.mean(dim="time")
        bias = model_mean - obs_mean
        corrected = model_output - bias
        return corrected

    def weighted_ensemble(
        self,
        dynamical_forecast: xr.DataArray,
        statistical_forecast: xr.DataArray,
        dynamical_weight: float = 0.6
    ) -> xr.DataArray:
        logger.info("创建加权集合预报...")
        hybrid_forecast = dynamical_weight * dynamical_forecast + (1 - dynamical_weight) * statistical_forecast
        return hybrid_forecast
