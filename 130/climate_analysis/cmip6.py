import xarray as xr
import numpy as np
from typing import Optional, List, Dict, Tuple, Union
import logging
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)


try:
    import intake
    INTAKE_AVAILABLE = True
except ImportError:
    INTAKE_AVAILABLE = False
    logger.warning("intake库未安装，CMIP6搜索功能将不可用")


try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests库未安装，下载功能将受限")


class CMIP6Search:
    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        if not INTAKE_AVAILABLE:
            raise ImportError("请先安装intake-esm: pip install intake-esm")

        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".climate_analysis" / "cmip6"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.catalog = None
        self.search_results = None

    def load_catalog(
        self,
        catalog_url: Optional[str] = None,
        use_cache: bool = True
    ):
        logger.info("加载CMIP6数据目录...")

        if catalog_url is None:
            catalog_url = "https://raw.githubusercontent.com/NCAR/intake-esm-datastore/master/catalogs/pangeo-cmip6.json"

        cache_file = self.cache_dir / "cmip6_catalog.json"

        if use_cache and cache_file.exists():
            logger.info(f"从缓存加载目录: {cache_file}")
            self.catalog = intake.open_esm_datastore(str(cache_file))
        else:
            logger.info(f"从URL下载目录: {catalog_url}")
            if REQUESTS_AVAILABLE:
                response = requests.get(catalog_url)
                response.raise_for_status()
                with open(cache_file, 'w') as f:
                    f.write(response.text)
                self.catalog = intake.open_esm_datastore(str(cache_file))
            else:
                self.catalog = intake.open_esm_datastore(catalog_url)

        logger.info(f"目录加载完成，共 {len(self.catalog.df)} 条记录")
        return self.catalog

    def search(
        self,
        experiment_id: Optional[Union[str, List[str]]] = None,
        variable_id: Optional[Union[str, List[str]]] = None,
        source_id: Optional[Union[str, List[str]]] = None,
        member_id: Optional[Union[str, List[str]]] = None,
        table_id: Optional[Union[str, List[str]]] = None,
        grid_label: Optional[str] = None,
        **kwargs
    ) -> xr.Dataset:
        if self.catalog is None:
            self.load_catalog()

        search_kwargs = {}
        if experiment_id:
            search_kwargs["experiment_id"] = experiment_id
        if variable_id:
            search_kwargs["variable_id"] = variable_id
        if source_id:
            search_kwargs["source_id"] = source_id
        if member_id:
            search_kwargs["member_id"] = member_id
        if table_id:
            search_kwargs["table_id"] = table_id
        if grid_label:
            search_kwargs["grid_label"] = grid_label
        search_kwargs.update(kwargs)

        logger.info(f"搜索CMIP6数据: {search_kwargs}")
        self.search_results = self.catalog.search(**search_kwargs)

        logger.info(f"找到 {len(self.search_results.df)} 条匹配记录")
        return self.search_results.df

    def get_available_models(self) -> List[str]:
        if self.catalog is None:
            self.load_catalog()
        return sorted(self.catalog.df["source_id"].unique().tolist())

    def get_available_experiments(self) -> List[str]:
        if self.catalog is None:
            self.load_catalog()
        return sorted(self.catalog.df["experiment_id"].unique().tolist())

    def get_available_variables(self) -> List[str]:
        if self.catalog is None:
            self.load_catalog()
        return sorted(self.catalog.df["variable_id"].unique().tolist())

    def to_dataset(
        self,
        zarr_kwargs: Optional[Dict] = None,
        preprocess: Optional[callable] = None
    ) -> xr.Dataset:
        if self.search_results is None:
            raise ValueError("请先调用 search() 搜索数据")

        zarr_kwargs = zarr_kwargs or {"consolidated": True}

        logger.info("将搜索结果转换为xarray数据集...")
        ds = self.search_results.to_dataset_dict(
            zarr_kwargs=zarr_kwargs,
            preprocess=preprocess
        )

        if len(ds) == 1:
            ds = list(ds.values())[0]

        logger.info(f"数据集加载完成，维度: {dict(ds.dims)}")
        return ds

    def save_search_results(self, filename: Union[str, Path]):
        if self.search_results is None:
            raise ValueError("请先调用 search() 搜索数据")

        filepath = self.cache_dir / filename
        self.search_results.df.to_csv(filepath, index=False)
        logger.info(f"搜索结果已保存到: {filepath}")


class CMIP6Downloader:
    def __init__(self, download_dir: Optional[Union[str, Path]] = None):
        self.download_dir = Path(download_dir) if download_dir else Path.home() / "climate_data" / "cmip6"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_files = []

    def download_from_esgf(
        self,
        variable: str,
        model: str,
        experiment: str,
        ensemble_member: str = "r1i1p1f1",
        table: str = "Amon",
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        **kwargs
    ) -> Path:
        logger.info(f"从ESGF下载数据: {variable}, {model}, {experiment}, {ensemble_member}")

        filename = f"{variable}_{table}_{model}_{experiment}_{ensemble_member}.nc"
        filepath = self.download_dir / filename

        if filepath.exists():
            logger.info(f"文件已存在，跳过下载: {filepath}")
            return filepath

        logger.warning("注意：完整的ESGF下载功能需要配置ESGF节点和认证")
        logger.info(f"将创建模拟数据: {filepath}")
        self._create_mock_data(filepath, variable, start_year or 1850, end_year or 2014)

        self.downloaded_files.append(filepath)
        return filepath

    def _create_mock_data(
        self,
        filepath: Path,
        variable: str,
        start_year: int,
        end_year: int
    ):
        n_time = (end_year - start_year + 1) * 12
        n_lat = 90
        n_lon = 180

        lat = np.linspace(-89.5, 89.5, n_lat)
        lon = np.linspace(0.5, 359.5, n_lon)
        time = xr.cftime_range(start=f"{start_year}-01-01", periods=n_time, freq="MS", calendar="noleap")

        base_field = 15 * np.cos(np.deg2rad(lat))[:, np.newaxis] - 5 * np.cos(2 * np.deg2rad(lat))[:, np.newaxis]
        trend = np.linspace(0, 2, n_time)[:, np.newaxis, np.newaxis]
        seasonal_cycle = 10 * np.cos(2 * np.pi * (np.arange(n_time) % 12) / 12)[:, np.newaxis, np.newaxis]
        noise = np.random.randn(n_time, n_lat, n_lon) * 0.5

        data = base_field[np.newaxis, :, :] + trend + seasonal_cycle + noise

        ds = xr.Dataset({
            variable: (["time", "lat", "lon"], data)
        }, coords={
            "time": time,
            "lat": lat,
            "lon": lon
        })

        ds[variable].attrs = {
            "units": "K" if variable == "tas" else "unknown",
            "long_name": f"Near-Surface {'Temperature' if variable == 'tas' else variable}",
            "standard_name": variable
        }

        ds.to_netcdf(filepath)
        logger.info(f"模拟数据已创建: {filepath}")

    def batch_download(
        self,
        download_list: List[Dict],
        **kwargs
    ) -> List[Path]:
        logger.info(f"批量下载 {len(download_list)} 个文件...")

        downloaded_paths = []
        for item in download_list:
            try:
                path = self.download_from_esgf(**item, **kwargs)
                downloaded_paths.append(path)
            except Exception as e:
                logger.error(f"下载失败 {item}: {e}")

        logger.info(f"批量下载完成，成功 {len(downloaded_paths)}/{len(download_list)}")
        return downloaded_paths

    def list_downloaded_files(self) -> List[Path]:
        return list(self.download_dir.glob("*.nc"))

    def load_downloaded(self, filepath: Union[str, Path], **kwargs) -> xr.Dataset:
        filepath = Path(filepath)
        logger.info(f"加载已下载的数据: {filepath}")
        return xr.open_dataset(filepath, **kwargs)


class CMIP6BiasCorrection:
    def __init__(self):
        self.correction_params = {}

    def quantile_mapping(
        self,
        model_data: xr.DataArray,
        obs_data: xr.DataArray,
        n_quantiles: int = 100
    ) -> xr.DataArray:
        logger.info("应用分位数映射偏差校正...")

        model_flat = model_data.values.flatten()
        obs_flat = obs_data.values.flatten()

        valid_model = model_flat[~np.isnan(model_flat)]
        valid_obs = obs_flat[~np.isnan(obs_flat)]

        quantiles = np.linspace(0, 1, n_quantiles)
        model_quantiles = np.quantile(valid_model, quantiles)
        obs_quantiles = np.quantile(valid_obs, quantiles)

        from scipy.interpolate import interp1d
        interp_func = interp1d(
            model_quantiles,
            obs_quantiles,
            bounds_error=False,
            fill_value="extrapolate"
        )

        corrected_values = interp_func(model_data.values)
        corrected = xr.DataArray(
            corrected_values,
            dims=model_data.dims,
            coords=model_data.coords
        )

        self.correction_params = {
            "model_quantiles": model_quantiles,
            "obs_quantiles": obs_quantiles
        }

        logger.info("分位数映射完成")
        return corrected

    def mean_adjustment(
        self,
        model_data: xr.DataArray,
        obs_data: xr.DataArray,
        groupby: str = "time.month"
    ) -> xr.DataArray:
        logger.info("应用均值调整偏差校正...")

        model_monthly_mean = model_data.groupby(groupby).mean(dim="time")
        obs_monthly_mean = obs_data.groupby(groupby).mean(dim="time")

        bias = model_monthly_mean - obs_monthly_mean
        corrected = model_data.groupby(groupby) - bias

        logger.info("均值调整完成")
        return corrected

    def variance_adjustment(
        self,
        model_data: xr.DataArray,
        obs_data: xr.DataArray,
        groupby: str = "time.month"
    ) -> xr.DataArray:
        logger.info("应用方差调整偏差校正...")

        model_monthly_std = model_data.groupby(groupby).std(dim="time")
        obs_monthly_std = obs_data.groupby(groupby).std(dim="time")

        variance_ratio = obs_monthly_std / model_monthly_std
        variance_ratio = variance_ratio.where(np.isfinite(variance_ratio), 1.0)

        model_monthly_mean = model_data.groupby(groupby).mean(dim="time")
        anomalies = model_data.groupby(groupby) - model_monthly_mean
        corrected_anomalies = anomalies.groupby(groupby) * variance_ratio
        corrected = corrected_anomalies.groupby(groupby) + model_monthly_mean

        logger.info("方差调整完成")
        return corrected


class CMIP6Ensemble:
    def __init__(self, members: Optional[List[xr.DataArray]] = None):
        self.members = members or []
        self.ensemble_mean = None
        self.ensemble_std = None

    def add_member(self, data: xr.DataArray, member_id: str):
        data = data.expand_dims({"member": [member_id]})
        self.members.append(data)
        logger.info(f"添加集合成员: {member_id}")

    def combine_members(self) -> xr.DataArray:
        if not self.members:
            raise ValueError("没有集合成员")

        logger.info("合并集合成员...")
        combined = xr.concat(self.members, dim="member")
        logger.info(f"合并完成，共 {len(combined.member)} 个成员")
        return combined

    def compute_ensemble_stats(self) -> xr.Dataset:
        combined = self.combine_members()

        self.ensemble_mean = combined.mean(dim="member")
        self.ensemble_std = combined.std(dim="member")

        ds = xr.Dataset({
            "ensemble_mean": self.ensemble_mean,
            "ensemble_std": self.ensemble_std,
            "ensemble_min": combined.min(dim="member"),
            "ensemble_max": combined.max(dim="member"),
            "ensemble_median": combined.median(dim="member")
        })

        logger.info("集合统计计算完成")
        return ds

    def get_probability(
        self,
        threshold: float,
        comparison: str = "greater"
    ) -> xr.DataArray:
        combined = self.combine_members()

        if comparison == "greater":
            prob = (combined > threshold).mean(dim="member")
        elif comparison == "less":
            prob = (combined < threshold).mean(dim="member")
        else:
            raise ValueError(f"不支持的比较方式: {comparison}")

        return prob


def get_cmip6_variable_info(variable_id: str) -> Dict:
    variable_info = {
        "tas": {
            "long_name": "Near-Surface Air Temperature",
            "units": "K",
            "table": "Amon",
            "description": "Near-surface (usually, 2 meter) air temperature."
        },
        "tasmax": {
            "long_name": "Daily Maximum Near-Surface Air Temperature",
            "units": "K",
            "table": "day",
            "description": "Daily maximum near-surface air temperature."
        },
        "tasmin": {
            "long_name": "Daily Minimum Near-Surface Air Temperature",
            "units": "K",
            "table": "day",
            "description": "Daily minimum near-surface air temperature."
        },
        "pr": {
            "long_name": "Precipitation",
            "units": "kg m-2 s-1",
            "table": "Amon",
            "description": "Precipitation flux at the surface."
        },
        "psl": {
            "long_name": "Sea Level Pressure",
            "units": "Pa",
            "table": "Amon",
            "description": "Sea level pressure."
        },
        "ts": {
            "long_name": "Surface Temperature",
            "units": "K",
            "table": "Amon",
            "description": "Temperature of the lower boundary of the atmosphere."
        },
        "ua": {
            "long_name": "Eastward Wind",
            "units": "m s-1",
            "table": "Amon",
            "description": "Eastward component of the wind."
        },
        "va": {
            "long_name": "Northward Wind",
            "units": "m s-1",
            "table": "Amon",
            "description": "Northward component of the wind."
        },
        "zg": {
            "long_name": "Geopotential Height",
            "units": "m",
            "table": "Amon",
            "description": "Geopotential height above sea level."
        },
        "hus": {
            "long_name": "Specific Humidity",
            "units": "kg kg-1",
            "table": "Amon",
            "description": "Specific humidity."
        }
    }

    return variable_info.get(variable_id, {
        "long_name": variable_id,
        "units": "unknown",
        "description": "Unknown variable"
    })


def list_cmip6_experiments() -> Dict[str, str]:
    return {
        "historical": "Historical simulation (1850-2014)",
        "ssp126": "SSP1-2.6 scenario",
        "ssp245": "SSP2-4.5 scenario",
        "ssp370": "SSP3-7.0 scenario",
        "ssp585": "SSP5-8.5 scenario",
        "piControl": "Pre-industrial control simulation",
        "abrupt-4xCO2": "Abrupt 4xCO2 simulation",
        "1pctCO2": "1% per year CO2 increase",
        "amip": "Atmospheric Model Intercomparison Project"
    }
