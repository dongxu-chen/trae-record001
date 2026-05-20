import xarray as xr
import numpy as np
from typing import Optional, Tuple, Dict
import logging
from sklearn.decomposition import PCA, IncrementalPCA
import dask.array as da

logger = logging.getLogger(__name__)


class EOFAnalysis:
    def __init__(self, data: xr.DataArray):
        self.data = data
        self.eofs = None
        self.pcs = None
        self.eigenvalues = None
        self.explained_variance_ratio = None
        self.n_modes = None
        self._pca_model = None
        self._data_mean = None
        self._valid_mask = None
        self._spatial_dims = None
        self._dim = None

    def _apply_weights(self, data: xr.DataArray) -> xr.DataArray:
        if "lat" in data.dims:
            weights = np.cos(np.deg2rad(data.lat))
            weights = weights.where(weights > 0, 0)
            weights = weights / weights.mean()
            data = data * np.sqrt(weights)
        return data

    def fit(
        self,
        n_modes: int = 10,
        apply_weights: bool = True,
        dim: str = "time",
        use_incremental: bool = False,
        batch_size: Optional[int] = None,
        lazy: bool = False
    ) -> Tuple[xr.DataArray, xr.DataArray, np.ndarray]:
        logger.info(f"开始EOF分析，计算前 {n_modes} 个模态")
        logger.info(f"使用方法: {'增量SVD' if use_incremental else 'sklearn PCA'}")

        self.n_modes = n_modes
        self._dim = dim
        data = self.data.copy()

        if apply_weights:
            data = self._apply_weights(data)

        self._data_mean = data.mean(dim=dim)
        data_centered = data - self._data_mean

        self._spatial_dims = [d for d in data_centered.dims if d != dim]
        data_flat = data_centered.stack(spatial=self._spatial_dims)

        if lazy and data.chunks is not None:
            return self._fit_dask(data_flat, n_modes, use_incremental, batch_size)
        else:
            return self._fit_numpy(data_flat, n_modes, use_incremental, batch_size)

    def _fit_numpy(
        self,
        data_flat: xr.DataArray,
        n_modes: int,
        use_incremental: bool,
        batch_size: Optional[int]
    ) -> Tuple[xr.DataArray, xr.DataArray, np.ndarray]:
        logger.info("使用NumPy/sklearn进行EOF分析")

        data_np = data_flat.values
        if data_np.ndim > 2:
            data_np = data_np.reshape(data_np.shape[0], -1)

        self._valid_mask = ~np.isnan(data_np).any(axis=0)
        data_valid = data_np[:, self._valid_mask]

        n_samples, n_features = data_valid.shape

        if use_incremental:
            if batch_size is None:
                batch_size = min(n_samples // 10, 1000)
                batch_size = max(batch_size, 100)
            logger.info(f"使用增量PCA，batch_size={batch_size}")

            pca = IncrementalPCA(n_components=n_modes, batch_size=batch_size)
            for i in range(0, n_samples, batch_size):
                batch = data_valid[i:i + batch_size]
                pca.partial_fit(batch)
        else:
            logger.info("使用标准PCA (Randomized SVD)")
            pca = PCA(n_components=n_modes, svd_solver="randomized", random_state=42)
            pca.fit(data_valid)

        self._pca_model = pca
        self.eigenvalues = pca.explained_variance_
        self.explained_variance_ratio = pca.explained_variance_ratio_

        eofs_flat = pca.components_
        n_features_full = data_np.shape[1]
        eofs_full = np.full((n_modes, n_features_full), np.nan)
        eofs_full[:, self._valid_mask] = eofs_flat

        eofs_da = xr.DataArray(
            eofs_full,
            dims=["mode", "spatial"],
            coords={"mode": np.arange(1, n_modes + 1), "spatial": data_flat.coords["spatial"]}
        )
        eofs_da = eofs_da.unstack("spatial")

        for d in self._spatial_dims:
            if d in self.data.coords:
                eofs_da[d] = self.data.coords[d]

        self.eofs = eofs_da

        pcs_np = pca.transform(data_valid)
        self.pcs = xr.DataArray(
            pcs_np,
            dims=[self._dim, "mode"],
            coords={
                self._dim: self.data.coords[self._dim],
                "mode": np.arange(1, n_modes + 1)
            }
        )

        logger.info(f"EOF分析完成，前{n_modes}个模态解释方差: {[f'{r:.2%}' for r in self.explained_variance_ratio]}")

        return self.eofs, self.pcs, self.eigenvalues

    def _fit_dask(
        self,
        data_flat: xr.DataArray,
        n_modes: int,
        use_incremental: bool,
        batch_size: Optional[int]
    ) -> Tuple[xr.DataArray, xr.DataArray, np.ndarray]:
        logger.info("使用Dask进行延迟EOF分析")

        data_da = data_flat.data
        n_samples = data_da.shape[0]

        self._valid_mask = ~np.isnan(data_da.compute()).any(axis=0)
        valid_idx = np.where(self._valid_mask)[0]
        data_valid = data_da[:, valid_idx]

        if use_incremental:
            if batch_size is None:
                batch_size = min(n_samples // 10, 1000)
                batch_size = max(batch_size, 100)
            logger.info(f"使用增量PCA，batch_size={batch_size}")

            pca = IncrementalPCA(n_components=n_modes, batch_size=batch_size)

            def _fit_batch(block):
                pca.partial_fit(block)
                return block

            da.map_blocks(_fit_batch, data_valid).compute()
        else:
            logger.info("使用标准PCA")
            data_np = data_valid.compute()
            pca = PCA(n_components=n_modes, svd_solver="randomized", random_state=42)
            pca.fit(data_np)

        self._pca_model = pca
        self.eigenvalues = pca.explained_variance_
        self.explained_variance_ratio = pca.explained_variance_ratio_

        eofs_flat = pca.components_
        n_features_full = data_da.shape[1]
        eofs_full = np.full((n_modes, n_features_full), np.nan)
        eofs_full[:, self._valid_mask] = eofs_flat

        eofs_da = xr.DataArray(
            eofs_full,
            dims=["mode", "spatial"],
            coords={"mode": np.arange(1, n_modes + 1), "spatial": data_flat.coords["spatial"]}
        )
        eofs_da = eofs_da.unstack("spatial")

        for d in self._spatial_dims:
            if d in self.data.coords:
                eofs_da[d] = self.data.coords[d]

        self.eofs = eofs_da

        def _transform_block(block):
            return self._pca_model.transform(block)

        pcs_da = da.map_blocks(_transform_block, data_valid, dtype=np.float64)
        self.pcs = xr.DataArray(
            pcs_da,
            dims=[self._dim, "mode"],
            coords={
                self._dim: self.data.coords[self._dim],
                "mode": np.arange(1, n_modes + 1)
            }
        )

        logger.info(f"EOF分析完成，前{n_modes}个模态解释方差: {[f'{r:.2%}' for r in self.explained_variance_ratio]}")

        return self.eofs, self.pcs, self.eigenvalues

    def transform(self, new_data: xr.DataArray, lazy: bool = False) -> xr.DataArray:
        if self._pca_model is None:
            raise ValueError("请先调用 fit() 方法进行EOF分析")

        data_centered = new_data - self._data_mean
        data_flat = data_centered.stack(spatial=self._spatial_dims)

        if lazy and data_flat.chunks is not None:
            data_valid = data_flat.data[:, self._valid_mask]

            def _transform_block(block):
                return self._pca_model.transform(block)

            pcs_da = da.map_blocks(_transform_block, data_valid, dtype=np.float64)
            pcs = xr.DataArray(
                pcs_da,
                dims=[self._dim, "mode"],
                coords={
                    self._dim: new_data.coords[self._dim],
                    "mode": np.arange(1, self.n_modes + 1)
                }
            )
        else:
            data_np = data_flat.values
            data_valid = data_np[:, self._valid_mask]
            pcs_np = self._pca_model.transform(data_valid)
            pcs = xr.DataArray(
                pcs_np,
                dims=[self._dim, "mode"],
                coords={
                    self._dim: new_data.coords[self._dim],
                    "mode": np.arange(1, self.n_modes + 1)
                }
            )

        return pcs

    def get_eofs(self, modes: Optional[list] = None) -> xr.DataArray:
        if self.eofs is None:
            raise ValueError("请先调用 fit() 方法进行EOF分析")
        if modes is None:
            return self.eofs
        return self.eofs.sel(mode=modes)

    def get_pcs(self, modes: Optional[list] = None) -> xr.DataArray:
        if self.pcs is None:
            raise ValueError("请先调用 fit() 方法进行EOF分析")
        if modes is None:
            return self.pcs
        return self.pcs.sel(mode=modes)

    def get_explained_variance_ratio(self) -> np.ndarray:
        if self.explained_variance_ratio is None:
            raise ValueError("请先调用 fit() 方法进行EOF分析")
        return self.explained_variance_ratio

    def reconstruct(self, modes: Optional[list] = None, lazy: bool = False) -> xr.DataArray:
        if self.eofs is None or self.pcs is None:
            raise ValueError("请先调用 fit() 方法进行EOF分析")

        if modes is None:
            modes = list(range(1, self.n_modes + 1))

        eofs_subset = self.eofs.sel(mode=modes)
        pcs_subset = self.pcs.sel(mode=modes)

        if lazy and pcs_subset.chunks is not None:
            reconstructed = xr.dot(pcs_subset, eofs_subset, dims=["mode"])
        else:
            reconstructed = xr.dot(pcs_subset, eofs_subset, dims=["mode"])

        reconstructed = reconstructed + self._data_mean

        return reconstructed

    def to_dataset(self) -> xr.Dataset:
        if self.eofs is None or self.pcs is None:
            raise ValueError("请先调用 fit() 方法进行EOF分析")

        ds = xr.Dataset({
            "eofs": self.eofs,
            "pcs": self.pcs,
            "eigenvalues": ("mode", self.eigenvalues),
            "explained_variance_ratio": ("mode", self.explained_variance_ratio)
        })
        return ds

    def save_results(self, output_path: str):
        ds = self.to_dataset()
        ds.to_netcdf(output_path)
        logger.info(f"EOF结果已保存到: {output_path}")
