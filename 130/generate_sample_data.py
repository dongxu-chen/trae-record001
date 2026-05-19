import numpy as np
import xarray as xr
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_climate_data(output_path: str = "sample_data/sample_temperature.nc"):
    logger.info("生成示例气候数据...")

    n_lat = 45
    n_lon = 90
    n_time = 240

    lat = np.linspace(-90, 90, n_lat)
    lon = np.linspace(0, 360, n_lon, endpoint=False)
    time = np.arange("2000-01", "2020-01", dtype="datetime64[M]")

    lons, lats = np.meshgrid(lon, lat)

    base_temp = 15 * np.cos(np.deg2rad(lats)) - 5 * np.cos(2 * np.deg2rad(lats))

    seasonal_cycle = 10 * np.cos(2 * np.pi * (np.arange(n_time) % 12) / 12)
    seasonal_cycle = seasonal_cycle[:, np.newaxis, np.newaxis] * np.cos(np.deg2rad(lats))

    trend = np.linspace(0, 2, n_time)
    trend = trend[:, np.newaxis, np.newaxis] * np.ones_like(base_temp)

    noise = np.random.randn(n_time, n_lat, n_lon) * 2

    eof1_pattern = np.sin(np.deg2rad(lons)) * np.cos(np.deg2rad(lats))
    eof2_pattern = np.cos(2 * np.deg2rad(lons)) * np.sin(np.deg2rad(lats))
    pc1 = np.sin(np.linspace(0, 10 * np.pi, n_time))
    pc2 = np.cos(np.linspace(0, 5 * np.pi, n_time))
    eof_variability = 3 * (pc1[:, np.newaxis, np.newaxis] * eof1_pattern +
                           pc2[:, np.newaxis, np.newaxis] * eof2_pattern)

    temperature = base_temp[np.newaxis, :, :] + seasonal_cycle + trend + noise + eof_variability

    ds = xr.Dataset(
        {
            "temperature": (["time", "lat", "lon"], temperature.astype(np.float32)),
        },
        coords={
            "time": time,
            "lat": lat,
            "lon": lon,
        },
    )

    ds["temperature"].attrs = {
        "units": "degC",
        "long_name": "Surface Air Temperature",
        "standard_name": "air_temperature"
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_path)

    logger.info(f"示例数据已保存到: {output_path}")
    logger.info(f"数据维度: {dict(ds.dims)}")
    logger.info(f"温度范围: {ds.temperature.min().values:.2f} ~ {ds.temperature.max().values:.2f} degC")

    return ds


if __name__ == "__main__":
    generate_sample_climate_data()
