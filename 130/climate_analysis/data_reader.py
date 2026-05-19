import xarray as xr
import dask.array as da
from dask.diagnostics import ProgressBar
from pathlib import Path
from typing import Union, Optional, List, Dict, Tuple
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def optimal_chunks(
    dim_sizes: Dict[str, int],
    target_size_mb: float = 100,
    dtype_size: int = 8,
    time_dim: str = "time"
) -> Dict[str, Union[str, int]]:
    """
    计算最优的chunk大小

    Args:
        dim_sizes: 各维度的大小字典
        target_size_mb: 目标chunk大小(MB)
        dtype_size: 数据类型字节数
        time_dim: 时间维度名

    Returns:
        chunks字典
    """
    target_size_bytes = target_size_mb * 1024 * 1024
    target_elements = target_size_bytes // dtype_size

    spatial_dims = [d for d in dim_sizes.keys() if d != time_dim]
    spatial_size = np.prod([dim_sizes[d] for d in spatial_dims]) if spatial_dims else 1

    if spatial_size <= target_elements:
        time_chunk = min(dim_sizes[time_dim], target_elements // spatial_size)
        chunks = {d: -1 for d in spatial_dims}
        chunks[time_dim] = int(time_chunk)
    else:
        chunks = {time_dim: -1}
        remaining = target_elements
        for d in reversed(spatial_dims):
            size = min(dim_sizes[d], int(np.sqrt(remaining)))
            chunks[d] = size
            remaining = remaining // size

    logger.info(f"推荐chunks: {chunks}")
    return chunks


class ClimateDataReader:
    def __init__(self, chunks: Optional[Dict] = None, target_chunk_mb: float = 100):
        self.default_chunks = chunks
        self.target_chunk_mb = target_chunk_mb
        self.ds = None
        self._chunks_info = None

    def _auto_chunks(self, ds: xr.Dataset, var_name: Optional[str] = None) -> Dict[str, Union[str, int]]:
        """自动计算chunk大小"""
        if var_name and var_name in ds.data_vars:
            dtype = ds[var_name].dtype
            dtype_size = dtype.itemsize
        else:
            dtype_size = 8

        dim_sizes = {d: ds.sizes[d] for d in ds.dims}
        return optimal_chunks(dim_sizes, self.target_chunk_mb, dtype_size)

    def read_netcdf(
        self,
        file_path: Union[str, Path],
        variables: Optional[List[str]] = None,
        chunks: Optional[Dict] = None,
        auto_chunk: bool = True,
        engine: str = "netcdf4",
        **kwargs
    ) -> xr.Dataset:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        logger.info(f"读取NetCDF文件: {file_path}")

        ds_temp = xr.open_dataset(file_path, engine=engine, chunks=None)

        if chunks is None and auto_chunk:
            if variables:
                chunks = self._auto_chunks(ds_temp, variables[0])
            else:
                chunks = self._auto_chunks(ds_temp)

        self.default_chunks = chunks
        self.ds = xr.open_dataset(file_path, chunks=chunks, engine=engine, **kwargs)

        if variables:
            self.ds = self.ds[variables]

        self._chunks_info = {v: dict(self.ds[v].chunksizes) for v in self.ds.data_vars}
        logger.info(f"数据集维度: {dict(self.ds.dims)}")
        logger.info(f"chunks信息: {self._chunks_info}")
        logger.info(f"变量: {list(self.ds.data_vars)}")

        return self.ds

    def read_grib(
        self,
        file_path: Union[str, Path],
        variables: Optional[List[str]] = None,
        chunks: Optional[Dict] = None,
        auto_chunk: bool = True,
        **kwargs
    ) -> xr.Dataset:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        logger.info(f"读取GRIB文件: {file_path}")

        ds_temp = xr.open_dataset(file_path, engine="cfgrib", chunks=None)

        if chunks is None and auto_chunk:
            if variables:
                chunks = self._auto_chunks(ds_temp, variables[0])
            else:
                chunks = self._auto_chunks(ds_temp)

        self.default_chunks = chunks
        self.ds = xr.open_dataset(file_path, engine="cfgrib", chunks=chunks, **kwargs)

        if variables:
            self.ds = self.ds[variables]

        self._chunks_info = {v: dict(self.ds[v].chunksizes) for v in self.ds.data_vars}
        logger.info(f"数据集维度: {dict(self.ds.dims)}")
        logger.info(f"chunks信息: {self._chunks_info}")
        logger.info(f"变量: {list(self.ds.data_vars)}")

        return self.ds

    def read_multiple_files(
        self,
        file_paths: List[Union[str, Path]],
        concat_dim: str = "time",
        combine: str = "by_coords",
        chunks: Optional[Dict] = None,
        auto_chunk: bool = True,
        **kwargs
    ) -> xr.Dataset:
        logger.info(f"读取 {len(file_paths)} 个文件，按 {concat_dim} 拼接")

        first_file = Path(file_paths[0])
        ds_temp = xr.open_dataset(first_file, chunks=None)

        if chunks is None and auto_chunk:
            chunks = self._auto_chunks(ds_temp)

        self.default_chunks = chunks
        self.ds = xr.open_mfdataset(
            file_paths,
            combine=combine,
            concat_dim=concat_dim,
            chunks=chunks,
            **kwargs
        )

        self._chunks_info = {v: dict(self.ds[v].chunksizes) for v in self.ds.data_vars}
        logger.info(f"合并后数据集维度: {dict(self.ds.dims)}")
        logger.info(f"chunks信息: {self._chunks_info}")
        return self.ds

    def rechunk(
        self,
        chunks: Optional[Dict] = None,
        target_size_mb: Optional[float] = None
    ) -> xr.Dataset:
        """重新chunk数据"""
        if self.ds is None:
            raise ValueError("未加载数据集")

        if chunks is None:
            if target_size_mb is not None:
                self.target_chunk_mb = target_size_mb
            chunks = self._auto_chunks(self.ds)

        logger.info(f"重新chunking: {chunks}")
        self.ds = self.ds.chunk(chunks)
        self._chunks_info = {v: dict(self.ds[v].chunksizes) for v in self.ds.data_vars}
        logger.info(f"新chunks信息: {self._chunks_info}")
        return self.ds

    def get_variable(self, var_name: str, load: bool = False) -> xr.DataArray:
        if self.ds is None:
            raise ValueError("未加载数据集，请先调用 read_netcdf 或 read_grib")
        if var_name not in self.ds.data_vars:
            raise ValueError(f"变量 {var_name} 不存在，可用变量: {list(self.ds.data_vars)}")

        da = self.ds[var_name]
        if load:
            da = da.load()
            logger.info(f"已加载变量 {var_name} 到内存")
        return da

    def select_region(
        self,
        var_name: str,
        lat_range: Optional[Tuple[float, float]] = None,
        lon_range: Optional[Tuple[float, float]] = None,
        time_range: Optional[Tuple[str, str]] = None,
        load: bool = False
    ) -> xr.DataArray:
        da_var = self.get_variable(var_name)

        if lat_range:
            da_var = da_var.sel(lat=slice(*lat_range))
        if lon_range:
            da_var = da_var.sel(lon=slice(*lon_range))
        if time_range:
            da_var = da_var.sel(time=slice(*time_range))

        if load:
            da_var = da_var.load()

        return da_var

    def compute(
        self,
        data: Union[xr.DataArray, xr.Dataset],
        show_progress: bool = True
    ) -> Union[xr.DataArray, xr.Dataset]:
        """触发Dask计算"""
        logger.info("开始Dask计算...")
        if show_progress:
            with ProgressBar():
                result = data.compute()
        else:
            result = data.compute()
        logger.info("计算完成")
        return result

    def persist(
        self,
        data: Union[xr.DataArray, xr.Dataset]
    ) -> Union[xr.DataArray, xr.Dataset]:
        """持久化到内存（保持Dask数组）"""
        logger.info("持久化数据到内存...")
        result = data.persist()
        logger.info("持久化完成")
        return result

    def seasonal_mean(self, var_name: str, season: str, lazy: bool = True) -> xr.DataArray:
        da_var = self.get_variable(var_name)
        result = da_var.groupby(f"time.{season}").mean(dim="time")
        if not lazy:
            result = self.compute(result)
        return result

    def annual_mean(self, var_name: str, lazy: bool = True) -> xr.DataArray:
        da_var = self.get_variable(var_name)
        result = da_var.groupby("time.year").mean(dim="time")
        if not lazy:
            result = self.compute(result)
        return result

    def climatology(self, var_name: str, lazy: bool = True) -> xr.DataArray:
        da_var = self.get_variable(var_name)
        result = da_var.mean(dim="time")
        if not lazy:
            result = self.compute(result)
        return result

    def anomaly(self, var_name: str, lazy: bool = True) -> xr.DataArray:
        da_var = self.get_variable(var_name)
        clim = self.climatology(var_name, lazy=True)
        result = da_var - clim
        if not lazy:
            result = self.compute(result)
        return result

    def spatial_mean(
        self,
        var_name: str,
        lat_weights: bool = True,
        lazy: bool = True
    ) -> xr.DataArray:
        """空间平均，可选纬度加权"""
        da_var = self.get_variable(var_name)

        if lat_weights and "lat" in da_var.dims:
            weights = np.cos(np.deg2rad(da_var.lat))
            weights = weights / weights.mean()
            result = (da_var * weights).mean(dim=["lat", "lon"])
        else:
            result = da_var.mean(dim=["lat", "lon"])

        if not lazy:
            result = self.compute(result)
        return result

    def save_to_netcdf(
        self,
        output_path: Union[str, Path],
        data: Optional[xr.Dataset] = None,
        compute: bool = True
    ):
        data = data or self.ds
        if data is None:
            raise ValueError("没有数据可保存")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"保存数据到: {output_path}")

        if compute and data.chunks is not None:
            with ProgressBar():
                data.to_netcdf(output_path)
        else:
            data.to_netcdf(output_path)
        logger.info("保存完成")

    def get_memory_usage(self, var_name: Optional[str] = None) -> Dict[str, float]:
        """获取内存使用情况(MB)"""
        if self.ds is None:
            raise ValueError("未加载数据集")

        if var_name:
            da = self.get_variable(var_name)
            size_mb = da.nbytes / (1024 * 1024)
            return {var_name: size_mb}
        else:
            usage = {}
            for v in self.ds.data_vars:
                size_mb = self.ds[v].nbytes / (1024 * 1024)
                usage[v] = size_mb
            usage["total"] = sum(usage.values())
            logger.info(f"内存使用情况: {usage}")
            return usage
