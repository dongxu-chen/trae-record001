import numpy as np
import xarray as xr
from scipy.spatial import cKDTree
from typing import Optional, Tuple, Dict, Union
import logging
import dask.array as da

logger = logging.getLogger(__name__)


class GridInterpolator:
    def __init__(
        self,
        source_lon: np.ndarray,
        source_lat: np.ndarray,
        target_lon: np.ndarray,
        target_lat: np.ndarray,
        method: str = "bilinear"
    ):
        self.source_lon = np.asarray(source_lon)
        self.source_lat = np.asarray(source_lat)
        self.target_lon = np.asarray(target_lon)
        self.target_lat = np.asarray(target_lat)
        self.method = method

        self.source_coords = np.column_stack([
            self.source_lon.flatten(),
            self.source_lat.flatten()
        ])
        self.target_coords = np.column_stack([
            self.target_lon.flatten(),
            self.target_lat.flatten()
        ])

        self.weights = None
        self.indices = None
        self._build_weight_matrix()

    def _build_weight_matrix(self):
        if self.method == "nearest":
            self._build_nearest_weights()
        elif self.method == "bilinear":
            self._build_bilinear_weights()
        else:
            raise ValueError(f"不支持的插值方法: {self.method}")

    def _build_nearest_weights(self):
        logger.info("构建最近邻插值权重矩阵...")
        tree = cKDTree(self.source_coords)
        distances, indices = tree.query(self.target_coords, k=1)

        n_target = len(self.target_coords)
        n_source = len(self.source_coords)

        row_indices = np.arange(n_target)
        col_indices = indices.flatten()
        weights = np.ones(n_target)

        self.weights = weights
        self.indices = col_indices
        self.shape = (n_target, n_source)
        logger.info("最近邻权重矩阵构建完成")

    def _build_bilinear_weights(self):
        logger.info("构建双线性插值权重矩阵...")

        if self.source_lon.ndim == 1 and self.source_lat.ndim == 1:
            source_lon_2d, source_lat_2d = np.meshgrid(self.source_lon, self.source_lat)
        else:
            source_lon_2d = self.source_lon
            source_lat_2d = self.source_lat

        if self.target_lon.ndim == 1 and self.target_lat.ndim == 1:
            target_lon_2d, target_lat_2d = np.meshgrid(self.target_lon, self.target_lat)
        else:
            target_lon_2d = self.target_lon
            target_lat_2d = self.target_lat

        source_lon_1d = source_lon_2d.flatten()
        source_lat_1d = source_lat_2d.flatten()

        unique_lons = np.sort(np.unique(source_lon_1d))
        unique_lats = np.sort(np.unique(source_lat_1d))

        n_target = target_lon_2d.size
        n_source = source_lon_2d.size

        all_indices = []
        all_weights = []
        all_rows = []

        for row_idx, (t_lon, t_lat) in enumerate(zip(target_lon_2d.flatten(), target_lat_2d.flatten())):
            i = np.searchsorted(unique_lons, t_lon) - 1
            j = np.searchsorted(unique_lats, t_lat) - 1

            i = max(0, min(i, len(unique_lons) - 2))
            j = max(0, min(j, len(unique_lats) - 2))

            x0, x1 = unique_lons[i], unique_lons[i + 1]
            y0, y1 = unique_lats[j], unique_lats[j + 1]

            dx = x1 - x0 if x1 != x0 else 1.0
            dy = y1 - y0 if y1 != y0 else 1.0

            wx = (t_lon - x0) / dx
            wy = (t_lat - y0) / dy

            corners = [
                (i, j, (1 - wx) * (1 - wy)),
                (i + 1, j, wx * (1 - wy)),
                (i, j + 1, (1 - wx) * wy),
                (i + 1, j + 1, wx * wy)
            ]

            for ci, cj, w in corners:
                col_idx = cj * len(unique_lons) + ci
                all_indices.append(col_idx)
                all_weights.append(w)
                all_rows.append(row_idx)

        self.weights = np.array(all_weights)
        self.indices = np.array(all_indices)
        self.row_indices = np.array(all_rows)
        self.shape = (n_target, n_source)

        logger.info("双线性权重矩阵构建完成")

    def interpolate(self, data: np.ndarray) -> np.ndarray:
        if data.ndim not in [2, 3]:
            raise ValueError(f"数据维度应为2或3，当前为{data.ndim}")

        if data.ndim == 2:
            data_flat = data.flatten()
            if self.method == "nearest":
                result = data_flat[self.indices]
            else:
                result = np.zeros(self.shape[0], dtype=data.dtype)
                np.add.at(result, self.row_indices, self.weights * data_flat[self.indices])
            result = result.reshape(self.target_lon.shape)
        else:
            n_time = data.shape[0]
            data_flat = data.reshape(n_time, -1)
            if self.method == "nearest":
                result = data_flat[:, self.indices]
            else:
                result = np.zeros((n_time, self.shape[0]), dtype=data.dtype)
                for t in range(n_time):
                    np.add.at(result[t], self.row_indices, self.weights * data_flat[t, self.indices])
            result = result.reshape(n_time, *self.target_lon.shape)

        return result

    def interpolate_xarray(
        self,
        da: xr.DataArray,
        time_dim: str = "time",
        lat_dim: str = "lat",
        lon_dim: str = "lon"
    ) -> xr.DataArray:
        if da.chunks is not None:
            return self._interpolate_dask(da, time_dim, lat_dim, lon_dim)
        else:
            return self._interpolate_numpy(da, time_dim, lat_dim, lon_dim)

    def _interpolate_numpy(
        self,
        da: xr.DataArray,
        time_dim: str,
        lat_dim: str,
        lon_dim: str
    ) -> xr.DataArray:
        data = da.values

        if time_dim in da.dims:
            time_vals = da.coords[time_dim].values
            result_data = self.interpolate(data)
            new_coords = {
                time_dim: time_vals,
                lat_dim: self.target_lat[:, 0] if self.target_lat.ndim == 2 else self.target_lat,
                lon_dim: self.target_lon[0, :] if self.target_lon.ndim == 2 else self.target_lon
            }
        else:
            result_data = self.interpolate(data[np.newaxis, :, :])[0]
            new_coords = {
                lat_dim: self.target_lat[:, 0] if self.target_lat.ndim == 2 else self.target_lat,
                lon_dim: self.target_lon[0, :] if self.target_lon.ndim == 2 else self.target_lon
            }

        result_da = xr.DataArray(
            result_data,
            coords=new_coords,
            dims=da.dims if time_dim in da.dims else (lat_dim, lon_dim),
            attrs=da.attrs
        )

        return result_da

    def _interpolate_dask(
        self,
        da: xr.DataArray,
        time_dim: str,
        lat_dim: str,
        lon_dim: str
    ) -> xr.DataArray:
        logger.info("使用Dask进行插值计算...")

        def _interp_chunk(chunk):
            if chunk.ndim == 2:
                chunk = chunk[np.newaxis, :, :]
            return self.interpolate(chunk)

        if time_dim in da.dims:
            time_vals = da.coords[time_dim].values
            result_data = da.map_blocks(
                _interp_chunk,
                template=xr.DataArray(
                    da.empty_like().data,
                    dims=da.dims
                )
            )
            new_coords = {
                time_dim: time_vals,
                lat_dim: self.target_lat[:, 0] if self.target_lat.ndim == 2 else self.target_lat,
                lon_dim: self.target_lon[0, :] if self.target_lon.ndim == 2 else self.target_lon
            }
        else:
            result_data = da.data.map_blocks(self.interpolate)
            new_coords = {
                lat_dim: self.target_lat[:, 0] if self.target_lat.ndim == 2 else self.target_lat,
                lon_dim: self.target_lon[0, :] if self.target_lon.ndim == 2 else self.target_lon
            }

        result_da = xr.DataArray(
            result_data,
            coords=new_coords,
            dims=da.dims,
            attrs=da.attrs
        )

        return result_da


class RegularGridInterpolator:
    def __init__(
        self,
        source_lon: np.ndarray,
        source_lat: np.ndarray,
        target_lon: np.ndarray,
        target_lat: np.ndarray,
        method: str = "linear"
    ):
        self.source_lon = np.asarray(source_lon)
        self.source_lat = np.asarray(source_lat)
        self.target_lon = np.asarray(target_lon)
        self.target_lat = np.asarray(target_lat)
        self.method = method

        self._i_indices = None
        self._j_indices = None
        self._weights = None
        self._precompute_weights()

    def _precompute_weights(self):
        logger.info("预计算规则网格插值权重...")

        i_indices = np.searchsorted(self.source_lon, self.target_lon) - 1
        j_indices = np.searchsorted(self.source_lat, self.target_lat) - 1

        i_indices = np.clip(i_indices, 0, len(self.source_lon) - 2)
        j_indices = np.clip(j_indices, 0, len(self.source_lat) - 2)

        self._i_indices = i_indices
        self._j_indices = j_indices

        x0 = self.source_lon[i_indices]
        x1 = self.source_lon[i_indices + 1]
        y0 = self.source_lat[j_indices]
        y1 = self.source_lat[j_indices + 1]

        dx = x1 - x0
        dy = y1 - y0

        self._wx = (self.target_lon - x0) / dx
        self._wy = (self.target_lat - y0) / dy

        logger.info("权重预计算完成")

    def interpolate(self, data: np.ndarray, use_dask: bool = False) -> np.ndarray:
        if data.ndim == 2:
            return self._interpolate_2d(data)
        elif data.ndim == 3:
            if use_dask:
                return self._interpolate_3d_dask(data)
            else:
                return self._interpolate_3d_numpy(data)
        else:
            raise ValueError(f"不支持的数据维度: {data.ndim}")

    def _interpolate_2d(self, data: np.ndarray) -> np.ndarray:
        i, j = np.meshgrid(self._i_indices, self._j_indices)
        wx, wy = np.meshgrid(self._wx, self._wy)

        v00 = data[j, i]
        v10 = data[j, i + 1]
        v01 = data[j + 1, i]
        v11 = data[j + 1, i + 1]

        result = (
            v00 * (1 - wx) * (1 - wy) +
            v10 * wx * (1 - wy) +
            v01 * (1 - wx) * wy +
            v11 * wx * wy
        )

        return result

    def _interpolate_3d_numpy(self, data: np.ndarray) -> np.ndarray:
        n_time = data.shape[0]
        result = np.empty((n_time, len(self.target_lat), len(self.target_lon)), dtype=data.dtype)

        for t in range(n_time):
            result[t] = self._interpolate_2d(data[t])

        return result

    def _interpolate_3d_dask(self, data: da.Array) -> da.Array:
        logger.info("使用Dask进行3D插值...")

        def interp_block(block):
            if block.ndim == 2:
                return self._interpolate_2d(block)
            else:
                return self._interpolate_3d_numpy(block)

        result = da.map_blocks(
            interp_block,
            data,
            chunks=(data.chunks[0], len(self.target_lat), len(self.target_lon)),
            dtype=data.dtype
        )

        return result

    def interpolate_xarray(self, da: xr.DataArray, lazy: bool = True) -> xr.DataArray:
        has_time = "time" in da.dims

        if lazy and da.chunks is not None:
            data = da.data
            interpolated = self.interpolate(data, use_dask=True)
        else:
            data = da.values
            interpolated = self.interpolate(data, use_dask=False)

        coords = {"lat": self.target_lat, "lon": self.target_lon}
        if has_time:
            coords["time"] = da.coords["time"].values

        dims = ("time", "lat", "lon") if has_time else ("lat", "lon")

        return xr.DataArray(
            interpolated,
            coords=coords,
            dims=dims,
            attrs=da.attrs
        )
