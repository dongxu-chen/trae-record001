import xarray as xr
import numpy as np
from typing import Optional, Tuple, Dict, List
import logging
from scipy import signal
from datetime import datetime

logger = logging.getLogger(__name__)


class MJOIndex:
    def __init__(self, data: Optional[xr.Dataset] = None):
        self.data = data
        self.rmm1 = None
        self.rmm2 = None
        self.phase = None
        self.amplitude = None
        self.eof_space = None
        self.pcs = None

    def _preprocess_olr(self, olr: xr.DataArray) -> xr.DataArray:
        logger.info("预处理OLR数据...")
        olr_anomaly = olr - olr.mean(dim="time")
        olr_deseasonal = self._remove_seasonal_cycle(olr_anomaly)
        olr_filtered = self._mjo_filter(olr_deseasonal)
        return olr_filtered

    def _preprocess_u850(self, u850: xr.DataArray) -> xr.DataArray:
        logger.info("预处理850hPa风场数据...")
        u850_anomaly = u850 - u850.mean(dim="time")
        u850_deseasonal = self._remove_seasonal_cycle(u850_anomaly)
        u850_filtered = self._mjo_filter(u850_deseasonal)
        return u850_filtered

    def _preprocess_u200(self, u200: xr.DataArray) -> xr.DataArray:
        logger.info("预处理200hPa风场数据...")
        u200_anomaly = u200 - u200.mean(dim="time")
        u200_deseasonal = self._remove_seasonal_cycle(u200_anomaly)
        u200_filtered = self._mjo_filter(u200_deseasonal)
        return u200_filtered

    def _remove_seasonal_cycle(self, data: xr.DataArray) -> xr.DataArray:
        logger.info("去除季节循环...")
        climatology = data.groupby("time.dayofyear").mean(dim="time")
        anomalies = data.groupby("time.dayofyear") - climatology
        return anomalies

    def _mjo_filter(self, data: xr.DataArray, cutoff: Tuple[int, int] = (20, 100)) -> xr.DataArray:
        logger.info(f"应用MJO带通滤波器 ({cutoff[0]}-{cutoff[1]}天)...")
        fs = 1.0
        low = 1.0 / cutoff[1]
        high = 1.0 / cutoff[0]
        b, a = signal.butter(3, [low, high], btype="band")
        filtered = xr.apply_ufunc(
            lambda x: signal.filtfilt(b, a, x) if not np.isnan(x).all() else x,
            data,
            input_core_dims=[["time"]],
            output_core_dims=[["time"]],
            vectorize=True,
            dask="allowed"
        )
        return filtered.transpose("time", ...)

    def _apply_latitude_weights(self, data: xr.DataArray) -> xr.DataArray:
        weights = np.cos(np.deg2rad(data.lat))
        weights = weights / weights.mean()
        return data * np.sqrt(weights)

    def compute_rmm(
        self,
        olr: xr.DataArray,
        u850: xr.DataArray,
        u200: xr.DataArray,
        n_modes: int = 2,
        reference_period: Optional[Tuple[str, str]] = None
    ) -> xr.Dataset:
        logger.info("计算RMM (Real-time Multivariate MJO) 指数...")

        olr_processed = self._preprocess_olr(olr)
        u850_processed = self._preprocess_u850(u850)
        u200_processed = self._preprocess_u200(u200)

        olr_weighted = self._apply_latitude_weights(olr_processed)
        u850_weighted = self._apply_latitude_weights(u850_processed)
        u200_weighted = self._apply_latitude_weights(u200_processed)

        combined = xr.concat(
            [olr_weighted, u850_weighted, u200_weighted],
            dim="variable"
        )

        if reference_period:
            ref_data = combined.sel(time=slice(*reference_period))
        else:
            ref_data = combined

        data_flat = ref_data.stack(spatial=["lat", "lon", "variable"])
        valid_mask = ~np.isnan(data_flat.values).any(axis=0)
        data_valid = data_flat.values[:, valid_mask]

        from sklearn.decomposition import PCA
        pca = PCA(n_components=n_modes, svd_solver="randomized", random_state=42)
        pcs = pca.fit_transform(data_valid)

        eofs_flat = np.full((n_modes, data_flat.shape[1]), np.nan)
        eofs_flat[:, valid_mask] = pca.components_
        eofs_da = xr.DataArray(
            eofs_flat,
            dims=["mode", "spatial"],
            coords={
                "mode": np.arange(1, n_modes + 1),
                "spatial": data_flat.coords["spatial"]
            }
        )
        self.eof_space = eofs_da.unstack("spatial")

        full_data_flat = combined.stack(spatial=["lat", "lon", "variable"])
        full_data_valid = full_data_flat.values[:, valid_mask]
        full_pcs = pca.transform(full_data_valid)

        self.rmm1 = xr.DataArray(
            full_pcs[:, 0],
            dims=["time"],
            coords={"time": combined.time}
        )
        self.rmm2 = xr.DataArray(
            full_pcs[:, 1],
            dims=["time"],
            coords={"time": combined.time}
        )

        self.amplitude = np.sqrt(self.rmm1 ** 2 + self.rmm2 ** 2)
        self.phase = self._compute_phase(self.rmm1, self.rmm2)

        mjo_ds = xr.Dataset({
            "rmm1": self.rmm1,
            "rmm2": self.rmm2,
            "phase": self.phase,
            "amplitude": self.amplitude,
            "explained_variance": ("mode", pca.explained_variance_ratio_)
        })

        logger.info("RMM指数计算完成")
        return mjo_ds

    def _compute_phase(self, rmm1: xr.DataArray, rmm2: xr.DataArray) -> xr.DataArray:
        angle = np.arctan2(rmm2, rmm1)
        phase = np.zeros_like(angle, dtype=int)

        phase[(angle >= 0) & (angle < np.pi / 4)] = 5
        phase[(angle >= np.pi / 4) & (angle < np.pi / 2)] = 6
        phase[(angle >= np.pi / 2) & (angle < 3 * np.pi / 4)] = 7
        phase[(angle >= 3 * np.pi / 4) & (angle < np.pi)] = 8
        phase[(angle >= -np.pi) & (angle < -3 * np.pi / 4)] = 1
        phase[(angle >= -3 * np.pi / 4) & (angle < -np.pi / 2)] = 2
        phase[(angle >= -np.pi / 2) & (angle < -np.pi / 4)] = 3
        phase[(angle >= -np.pi / 4) & (angle < 0)] = 4

        return xr.DataArray(phase, dims=["time"], coords={"time": rmm1.time})

    def get_mjo_events(
        self,
        amplitude_threshold: float = 1.0,
        min_duration: int = 5
    ) -> List[Dict]:
        if self.amplitude is None or self.phase is None:
            raise ValueError("请先调用 compute_rmm() 计算MJO指数")

        active = (self.amplitude > amplitude_threshold).values
        events = []
        current_start = None

        for i in range(len(active)):
            if active[i] and current_start is None:
                current_start = i
            elif not active[i] and current_start is not None:
                duration = i - current_start
                if duration >= min_duration:
                    events.append({
                        "start_time": str(self.amplitude.time[current_start].values),
                        "end_time": str(self.amplitude.time[i - 1].values),
                        "duration": duration,
                        "max_amplitude": float(self.amplitude.isel(time=slice(current_start, i)).max()),
                        "phases": [int(p) for p in self.phase.isel(time=slice(current_start, i)).values]
                    })
                current_start = None

        if current_start is not None:
            duration = len(active) - current_start
            if duration >= min_duration:
                events.append({
                    "start_time": str(self.amplitude.time[current_start].values),
                    "end_time": str(self.amplitude.time[-1].values),
                    "duration": duration,
                    "max_amplitude": float(self.amplitude.isel(time=slice(current_start, None)).max()),
                    "phases": [int(p) for p in self.phase.isel(time=slice(current_start, None)).values]
                })

        logger.info(f"检测到 {len(events)} 个MJO事件")
        return events

    def phase_composite(
        self,
        data: xr.DataArray,
        phase: Optional[int] = None
    ) -> xr.DataArray:
        if self.phase is None:
            raise ValueError("请先调用 compute_rmm() 计算MJO指数")

        if phase is not None:
            mask = self.phase == phase
            composite = data.where(mask).mean(dim="time")
        else:
            composites = []
            for p in range(1, 9):
                mask = self.phase == p
                comp = data.where(mask).mean(dim="time")
                composites.append(comp)
            composite = xr.concat(composites, dim="phase")
            composite["phase"] = np.arange(1, 9)

        return composite

    def save_to_netcdf(self, output_path: str):
        ds = xr.Dataset({
            "rmm1": self.rmm1,
            "rmm2": self.rmm2,
            "phase": self.phase,
            "amplitude": self.amplitude
        })
        ds.to_netcdf(output_path)
        logger.info(f"MJO指数已保存到: {output_path}")
