import xarray as xr
import numpy as np
from scipy import stats
from typing import Optional, Tuple, Dict
import logging
import dask.array as da

logger = logging.getLogger(__name__)


class TrendAnalysis:
    def __init__(self, data: xr.DataArray):
        self.data = data
        self.trend = None
        self.p_value = None
        self.slope = None
        self.intercept = None
        self.r_value = None
        self.std_err = None
        self.t_stat = None
        self.t_p_value = None

    def linear_trend(
        self,
        dim: str = "time",
        calc_pvalue: bool = True,
        calc_t_test: bool = True,
        lazy: bool = False
    ) -> Tuple[xr.DataArray, xr.DataArray]:
        logger.info("计算线性趋势...")

        if lazy and self.data.chunks is not None:
            return self._linear_trend_dask(dim=dim, calc_pvalue=calc_pvalue, calc_t_test=calc_t_test)
        else:
            return self._linear_trend_numpy(dim=dim, calc_pvalue=calc_pvalue, calc_t_test=calc_t_test)

    def _linear_trend_numpy(
        self,
        dim: str = "time",
        calc_pvalue: bool = True,
        calc_t_test: bool = True
    ) -> Tuple[xr.DataArray, xr.DataArray]:
        def _linear_regress(y):
            if np.isnan(y).all():
                return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
            x = np.arange(len(y))
            mask = ~np.isnan(y)
            if mask.sum() < 3:
                return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

            y_valid = y[mask]
            x_valid = x[mask]

            n = len(y_valid)
            x_mean = x_valid.mean()
            y_mean = y_valid.mean()

            ss_xy = np.sum((x_valid - x_mean) * (y_valid - y_mean))
            ss_xx = np.sum((x_valid - x_mean) ** 2)
            ss_yy = np.sum((y_valid - y_mean) ** 2)

            slope = ss_xy / ss_xx
            intercept = y_mean - slope * x_mean

            y_pred = slope * x_valid + intercept
            residuals = y_valid - y_pred

            r_value = ss_xy / np.sqrt(ss_xx * ss_yy)

            mse = np.sum(residuals ** 2) / (n - 2)
            std_err = np.sqrt(mse / ss_xx)

            t_stat = slope / std_err
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

            return slope, intercept, r_value, p_value, std_err, t_stat

        spatial_dims = [d for d in self.data.dims if d != dim]

        if spatial_dims:
            data_flat = self.data.stack(spatial=spatial_dims)
            results = xr.apply_ufunc(
                _linear_regress,
                data_flat,
                input_core_dims=[[dim]],
                output_core_dims=[[], [], [], [], [], []],
                vectorize=True,
                dask="allowed",
                output_dtypes=[np.float64, np.float64, np.float64, np.float64, np.float64, np.float64]
            )

            self.slope = results[0].unstack("spatial")
            self.intercept = results[1].unstack("spatial")
            self.r_value = results[2].unstack("spatial")
            self.p_value = results[3].unstack("spatial")
            self.std_err = results[4].unstack("spatial")
            self.t_stat = results[5].unstack("spatial")
        else:
            y = self.data.values
            slope, intercept, r_value, p_value, std_err, t_stat = _linear_regress(y)
            self.slope = xr.DataArray(slope)
            self.intercept = xr.DataArray(intercept)
            self.r_value = xr.DataArray(r_value)
            self.p_value = xr.DataArray(p_value)
            self.std_err = xr.DataArray(std_err)
            self.t_stat = xr.DataArray(t_stat)

        self.trend = self.slope * len(self.data[dim])
        self.t_p_value = self.p_value

        logger.info("线性趋势计算完成")
        return self.trend, self.p_value

    def _linear_trend_dask(
        self,
        dim: str = "time",
        calc_pvalue: bool = True,
        calc_t_test: bool = True
    ) -> Tuple[xr.DataArray, xr.DataArray]:
        logger.info("使用Dask延迟计算线性趋势...")

        def _linear_regress_block(block):
            if block.ndim == 1:
                block = block.reshape(-1, 1)

            slope = np.full(block.shape[1], np.nan)
            intercept = np.full(block.shape[1], np.nan)
            r_value = np.full(block.shape[1], np.nan)
            p_value = np.full(block.shape[1], np.nan)
            std_err = np.full(block.shape[1], np.nan)
            t_stat = np.full(block.shape[1], np.nan)

            for i in range(block.shape[1]):
                y = block[:, i]
                mask = ~np.isnan(y)
                if mask.sum() < 3:
                    continue

                y_valid = y[mask]
                x_valid = np.arange(len(y))[mask]
                n = len(y_valid)
                x_mean = x_valid.mean()
                y_mean = y_valid.mean()

                ss_xy = np.sum((x_valid - x_mean) * (y_valid - y_mean))
                ss_xx = np.sum((x_valid - x_mean) ** 2)
                ss_yy = np.sum((y_valid - y_mean) ** 2)

                slope[i] = ss_xy / ss_xx
                intercept[i] = y_mean - slope[i] * x_mean

                y_pred = slope[i] * x_valid + intercept[i]
                residuals = y_valid - y_pred

                r_value[i] = ss_xy / np.sqrt(ss_xx * ss_yy)

                mse = np.sum(residuals ** 2) / (n - 2)
                std_err[i] = np.sqrt(mse / ss_xx)
                t_stat[i] = slope[i] / std_err[i]
                p_value[i] = 2 * (1 - stats.t.cdf(abs(t_stat[i]), n - 2))

            return slope, intercept, r_value, p_value, std_err, t_stat

        spatial_dims = [d for d in self.data.dims if d != dim]

        if spatial_dims:
            data_flat = self.data.stack(spatial=spatial_dims)
            data_da = data_flat.data

            results = da.apply_gufunc(
                _linear_regress_block,
                "(n)->(k),(k),(k),(k),(k),(k)",
                data_da,
                output_dtypes=(np.float64, np.float64, np.float64, np.float64, np.float64, np.float64),
                allow_rechunk=True
            )

            def to_da(result, coords, dims):
                return xr.DataArray(result, coords=coords, dims=dims)

            spatial_coords = {d: data_flat.coords[d] for d in spatial_dims}

            self.slope = to_da(results[0], data_flat.coords, ["spatial"]).unstack("spatial")
            self.intercept = to_da(results[1], data_flat.coords, ["spatial"]).unstack("spatial")
            self.r_value = to_da(results[2], data_flat.coords, ["spatial"]).unstack("spatial")
            self.p_value = to_da(results[3], data_flat.coords, ["spatial"]).unstack("spatial")
            self.std_err = to_da(results[4], data_flat.coords, ["spatial"]).unstack("spatial")
            self.t_stat = to_da(results[5], data_flat.coords, ["spatial"]).unstack("spatial")
        else:
            y = self.data.values
            slope, intercept, r_value, p_value, std_err, t_stat = _linear_regress_block(y)
            self.slope = xr.DataArray(slope[0])
            self.intercept = xr.DataArray(intercept[0])
            self.r_value = xr.DataArray(r_value[0])
            self.p_value = xr.DataArray(p_value[0])
            self.std_err = xr.DataArray(std_err[0])
            self.t_stat = xr.DataArray(t_stat[0])

        self.trend = self.slope * len(self.data[dim])
        self.t_p_value = self.p_value

        logger.info("线性趋势Dask计算完成")
        return self.trend, self.p_value

    def t_test_summary(self, alpha: float = 0.05) -> xr.Dataset:
        if self.t_stat is None or self.t_p_value is None:
            raise ValueError("请先调用 linear_trend() 方法计算趋势和t检验")

        ds = xr.Dataset({
            "slope": self.slope,
            "trend": self.trend,
            "t_statistic": self.t_stat,
            "p_value": self.t_p_value,
            "std_error": self.std_err,
            "significant": self.t_p_value < alpha
        })

        return ds

    def mann_kendall_test(
        self,
        dim: str = "time",
        alpha: float = 0.05,
        lazy: bool = False
    ) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        logger.info("执行Mann-Kendall趋势检验...")

        if lazy and self.data.chunks is not None:
            return self._mann_kendall_dask(dim=dim, alpha=alpha)
        else:
            return self._mann_kendall_numpy(dim=dim, alpha=alpha)

    def _mann_kendall_numpy(
        self,
        dim: str = "time",
        alpha: float = 0.05
    ) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        def _mann_kendall(y):
            if np.isnan(y).all():
                return np.nan, np.nan, np.nan
            y = y[~np.isnan(y)]
            n = len(y)
            if n < 3:
                return np.nan, np.nan, np.nan

            s = 0
            for i in range(n - 1):
                for j in range(i + 1, n):
                    s += np.sign(y[j] - y[i])

            unique_y = np.unique(y)
            if len(unique_y) < n:
                ties = np.array([np.sum(y == t) for t in unique_y if np.sum(y == t) > 1])
                tie_correction = np.sum(ties * (ties - 1) * (2 * ties + 5)) / 18
            else:
                tie_correction = 0

            var_s = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18

            if s > 0:
                z = (s - 1) / np.sqrt(var_s)
            elif s < 0:
                z = (s + 1) / np.sqrt(var_s)
            else:
                z = 0

            p_value = 2 * (1 - stats.norm.cdf(abs(z)))

            slope = np.median([(y[j] - y[i]) / (j - i) for i in range(n) for j in range(i + 1, n)])

            return z, p_value, slope

        spatial_dims = [d for d in self.data.dims if d != dim]

        if spatial_dims:
            data_flat = self.data.stack(spatial=spatial_dims)
            results = xr.apply_ufunc(
                _mann_kendall,
                data_flat,
                input_core_dims=[[dim]],
                output_core_dims=[[], [], []],
                vectorize=True,
                dask="allowed",
                output_dtypes=[np.float64, np.float64, np.float64]
            )

            z_stat = results[0].unstack("spatial")
            p_value = results[1].unstack("spatial")
            theil_sen_slope = results[2].unstack("spatial")
        else:
            y = self.data.values
            z, p, slope = _mann_kendall(y)
            z_stat = xr.DataArray(z)
            p_value = xr.DataArray(p)
            theil_sen_slope = xr.DataArray(slope)

        logger.info("Mann-Kendall检验完成")
        return z_stat, p_value, theil_sen_slope

    def _mann_kendall_dask(
        self,
        dim: str = "time",
        alpha: float = 0.05
    ) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        logger.info("使用Dask延迟执行Mann-Kendall趋势检验...")

        def _mk_block(block):
            if block.ndim == 1:
                block = block.reshape(-1, 1)

            z = np.full(block.shape[1], np.nan)
            p = np.full(block.shape[1], np.nan)
            slope = np.full(block.shape[1], np.nan)

            for i in range(block.shape[1]):
                y = block[:, i]
                y = y[~np.isnan(y)]
                n = len(y)
                if n < 3:
                    continue

                s = 0
                for j in range(n - 1):
                    for k in range(j + 1, n):
                        s += np.sign(y[k] - y[j])

                unique_y = np.unique(y)
                if len(unique_y) < n:
                    ties = np.array([np.sum(y == t) for t in unique_y if np.sum(y == t) > 1])
                    tie_correction = np.sum(ties * (ties - 1) * (2 * ties + 5)) / 18
                else:
                    tie_correction = 0

                var_s = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18

                if s > 0:
                    z[i] = (s - 1) / np.sqrt(var_s)
                elif s < 0:
                    z[i] = (s + 1) / np.sqrt(var_s)
                else:
                    z[i] = 0

                p[i] = 2 * (1 - stats.norm.cdf(abs(z[i])))

                slope[i] = np.median([(y[k] - y[j]) / (k - j) for j in range(n) for k in range(j + 1, n)])

            return z, p, slope

        spatial_dims = [d for d in self.data.dims if d != dim]

        if spatial_dims:
            data_flat = self.data.stack(spatial=spatial_dims)
            data_da = data_flat.data

            results = da.apply_gufunc(
                _mk_block,
                "(n)->(k),(k),(k)",
                data_da,
                output_dtypes=(np.float64, np.float64, np.float64),
                allow_rechunk=True
            )

            def to_da(result, coords, dims):
                return xr.DataArray(result, coords=coords, dims=dims)

            z_stat = to_da(results[0], data_flat.coords, ["spatial"]).unstack("spatial")
            p_value = to_da(results[1], data_flat.coords, ["spatial"]).unstack("spatial")
            theil_sen_slope = to_da(results[2], data_flat.coords, ["spatial"]).unstack("spatial")
        else:
            y = self.data.values
            z, p, slope = _mk_block(y)
            z_stat = xr.DataArray(z[0])
            p_value = xr.DataArray(p[0])
            theil_sen_slope = xr.DataArray(slope[0])

        logger.info("Mann-Kendall Dask检验完成")
        return z_stat, p_value, theil_sen_slope

    def detrend(self, dim: str = "time", order: int = 1, lazy: bool = False) -> xr.DataArray:
        logger.info(f"去除{order}阶多项式趋势...")

        if order == 1:
            if self.slope is None or self.intercept is None:
                self.linear_trend(dim=dim, lazy=lazy)

            trend = self.slope * xr.DataArray(
                np.arange(len(self.data[dim])),
                dims=[dim],
                coords={dim: self.data[dim]}
            ) + self.intercept

            detrended = self.data - trend
        else:
            detrended = self._detrend_poly(dim=dim, order=order, lazy=lazy)

        logger.info("去趋势完成")
        return detrended

    def _detrend_poly(self, dim: str = "time", order: int = 1, lazy: bool = False) -> xr.DataArray:
        def _detrend(y):
            if np.isnan(y).all():
                return y
            x = np.arange(len(y))
            mask = ~np.isnan(y)
            if mask.sum() < order + 1:
                return y
            coeffs = np.polyfit(x[mask], y[mask], order)
            trend = np.polyval(coeffs, x)
            return y - trend

        spatial_dims = [d for d in self.data.dims if d != dim]
        if spatial_dims:
            data_flat = self.data.stack(spatial=spatial_dims)
            detrended_flat = xr.apply_ufunc(
                _detrend,
                data_flat,
                input_core_dims=[[dim]],
                output_core_dims=[[dim]],
                vectorize=True,
                dask="allowed" if lazy else "forbidden",
                output_dtypes=[np.float64]
            )
            detrended = detrended_flat.unstack("spatial")
        else:
            y = self.data.values
            detrended = xr.DataArray(_detrend(y), dims=self.data.dims, coords=self.data.coords)

        return detrended

    def running_mean(self, window_size: int, dim: str = "time", center: bool = True) -> xr.DataArray:
        logger.info(f"计算{window_size}点滑动平均...")
        smoothed = self.data.rolling({dim: window_size}, center=center).mean()
        logger.info("滑动平均完成")
        return smoothed

    def anomaly(self, dim: str = "time") -> xr.DataArray:
        logger.info("计算距平...")
        return self.data - self.data.mean(dim=dim)

    def standardize(self, dim: str = "time") -> xr.DataArray:
        logger.info("标准化数据...")
        mean = self.data.mean(dim=dim)
        std = self.data.std(dim=dim)
        return (self.data - mean) / std

    def get_significant_mask(self, alpha: float = 0.05, method: str = "t_test") -> xr.DataArray:
        if method == "t_test":
            if self.t_p_value is None:
                raise ValueError("请先调用 linear_trend() 方法计算趋势和t检验")
            return self.t_p_value < alpha
        elif method == "mann_kendall":
            if self.p_value is None:
                raise ValueError("请先调用 mann_kendall_test() 方法")
            return self.p_value < alpha
        else:
            raise ValueError(f"不支持的检验方法: {method}")

    def to_dataset(self) -> xr.Dataset:
        ds = xr.Dataset()
        if self.trend is not None:
            ds["trend"] = self.trend
        if self.p_value is not None:
            ds["p_value"] = self.p_value
        if self.slope is not None:
            ds["slope"] = self.slope
        if self.intercept is not None:
            ds["intercept"] = self.intercept
        if self.r_value is not None:
            ds["r_value"] = self.r_value
        if self.std_err is not None:
            ds["std_error"] = self.std_err
        if self.t_stat is not None:
            ds["t_statistic"] = self.t_stat
        return ds

    def save_results(self, output_path: str):
        ds = self.to_dataset()
        ds.to_netcdf(output_path)
        logger.info(f"趋势分析结果已保存到: {output_path}")
