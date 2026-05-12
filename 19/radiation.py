"""
气候模型中的辐射传输参数化方案主控模块
支持：
- GPU 加速 (CuPy / NumPy 自动切换)
- 多列向量化计算
- 多波段计算
- HDF5 数据存储
- MPI 列并行
"""

import numpy as np

try:
    import backend as bk
    xp = bk.get_backend()
    using_backend = True
except ImportError:
    xp = np
    using_backend = False

from shortwave import ShortwaveRadiation
from longwave import LongwaveRadiation
from cloud import CloudEffect
from aerosol import AerosolEffect

try:
    from flux_storage import FluxStorage, BatchFluxWriter
    FLUX_STORAGE_AVAILABLE = True
except ImportError:
    FLUX_STORAGE_AVAILABLE = False

try:
    from parallel import ColumnParallel, ParallelRadiationDriver
    PARALLEL_AVAILABLE = True
except ImportError:
    PARALLEL_AVAILABLE = False


class RadiationModel:
    """
    气候模型中的辐射传输参数化方案主控模块
    整合短波、长波、云效应和气溶胶效应

    新特性：
    - GPU 加速 (CuPy)
    - 多列向量化
    - 多波段计算
    """

    def __init__(self, solar_zenith_angle=0.0, day_of_year=180,
                 surface_emissivity=0.95, n_columns=1,
                 use_bands=False, band_names=None,
                 backend='auto'):
        """
        参数:
        - solar_zenith_angle: 太阳天顶角 (度), 标量或 (n_columns,) 数组
        - day_of_year: 年中的第几天
        - surface_emissivity: 地表发射率
        - n_columns: 列数（水平点数）
        - use_bands: 是否使用多波段计算
        - band_names: 波段名称列表
        - backend: 计算后端 ('auto', 'cupy', 'numpy')
        """
        self.n_columns = n_columns
        self.use_bands = use_bands

        if using_backend:
            bk.set_backend(backend)
            self.xp = bk.get_backend()
            self.device = bk.get_device()
        else:
            self.xp = np
            self.device = 'cpu'

        self.shortwave = ShortwaveRadiation(
            solar_zenith_angle, day_of_year,
            n_columns=n_columns,
            use_bands=use_bands,
            band_names=band_names
        )

        self.longwave = LongwaveRadiation(
            surface_emissivity,
            n_columns=n_columns,
            use_bands=use_bands
        )

        self.cloud = CloudEffect(n_columns=n_columns)
        self.aerosol = AerosolEffect(n_columns=n_columns)

    def get_backend_info(self):
        """获取后端信息"""
        return {
            'device': self.device,
            'backend': 'cupy' if self.device == 'gpu' else 'numpy',
            'n_columns': self.n_columns,
            'use_bands': self.use_bands,
            'n_bands': self.shortwave.n_bands
        }

    def create_standard_atmosphere(self, n_levels=10, surface_temperature=298.0,
                                   surface_pressure=101325.0, tropopause_height=12.0):
        """
        创建标准大气廓线（支持多列）

        参数:
        - n_levels: 大气层数
        - surface_temperature: 地表温度 (K)，标量或 (n_columns,) 数组
        - surface_pressure: 地表气压 (Pa)
        - tropopause_height: 对流层顶高度 (km)

        返回:
        - 大气廓线字典，数组形状为 (n_columns, n_levels)
        """
        xp = self.xp

        heights = xp.linspace(0, tropopause_height, n_levels)

        pressure = surface_pressure * xp.exp(-heights / 8.0)

        lapse_rate = 6.5

        if isinstance(surface_temperature, (int, float)):
            Ts = xp.full(self.n_columns, surface_temperature)
        else:
            Ts = xp.asarray(surface_temperature)

        temperature = Ts[:, xp.newaxis] - lapse_rate * heights[xp.newaxis, :]

        water_vapor = 15.0 * xp.exp(-heights / 2.0)
        water_vapor = xp.broadcast_to(water_vapor, (self.n_columns, n_levels))

        ozone_profile = xp.zeros((self.n_columns, n_levels))
        ozone_max_height = 25.0
        for j, h in enumerate(heights):
            if h < ozone_max_height:
                ozone_profile[:, j] = 0.001 + 0.01 * (1 - xp.exp(-h / 5.0))
            else:
                ozone_profile[:, j] = 0.01 * xp.exp(-(h - ozone_max_height) / 10.0)

        return {
            'pressure': pressure[xp.newaxis, :] if pressure.ndim == 1 else pressure,
            'temperature': temperature,
            'water_vapor': water_vapor,
            'ozone': ozone_profile,
            'height': heights
        }

    def create_default_cloud_profile(self, n_levels=10, cloud_layers=None):
        """
        创建默认云廓线（支持多列）

        参数:
        - n_levels: 层数
        - cloud_layers: 云层定义，格式 [(start, end, cloud_type, fraction, water_content), ...]
                       或每列不同的云层

        返回:
        - 云廓线字典，形状 (n_columns, n_levels)
        """
        xp = self.xp

        if cloud_layers is None:
            cloud_layers = []

        cloud_fraction = xp.zeros((self.n_columns, n_levels))
        water_content = xp.zeros((self.n_columns, n_levels))
        cloud_type = [['clear'] * n_levels for _ in range(self.n_columns)]
        temperature = xp.zeros((self.n_columns, n_levels))

        if cloud_layers and len(cloud_layers) > 0:
            if isinstance(cloud_layers[0], list) or isinstance(cloud_layers[0], tuple):
                if len(cloud_layers) == self.n_columns and isinstance(cloud_layers[0], list):
                    for col in range(self.n_columns):
                        for start, end, ct, cf, wc in cloud_layers[col]:
                            for i in range(start, min(end + 1, n_levels)):
                                if 0 <= i < n_levels:
                                    cloud_fraction[col, i] = cf
                                    water_content[col, i] = wc
                                    cloud_type[col][i] = ct
                else:
                    for start, end, ct, cf, wc in cloud_layers:
                        for i in range(start, min(end + 1, n_levels)):
                            if 0 <= i < n_levels:
                                cloud_fraction[:, i] = cf
                                water_content[:, i] = wc
                                for col in range(self.n_columns):
                                    cloud_type[col][i] = ct

        return {
            'cloud_fraction': cloud_fraction,
            'water_content': water_content,
            'cloud_type': cloud_type,
            'temperature': temperature
        }

    def create_default_aerosol_profile(self, n_levels=10, aerosol_layers=None):
        """
        创建默认气溶胶廓线（支持多列）

        参数:
        - n_levels: 层数
        - aerosol_layers: 气溶胶层定义，格式 [(start, end, type, mass_conc, rh), ...]

        返回:
        - 气溶胶廓线字典，形状 (n_columns, n_levels)
        """
        xp = self.xp

        if aerosol_layers is None:
            aerosol_layers = []

        mass_concentration = xp.zeros((self.n_columns, n_levels))
        aerosol_type = [['sulfate'] * n_levels for _ in range(self.n_columns)]
        relative_humidity = xp.full((self.n_columns, n_levels), 50.0)
        temperature = xp.zeros((self.n_columns, n_levels))

        if aerosol_layers and len(aerosol_layers) > 0:
            for start, end, at, mc, rh in aerosol_layers:
                for i in range(start, min(end + 1, n_levels)):
                    if 0 <= i < n_levels:
                        mass_concentration[:, i] = mc
                        relative_humidity[:, i] = rh
                        for col in range(self.n_columns):
                            aerosol_type[col][i] = at

        return {
            'mass_concentration': mass_concentration,
            'aerosol_type': aerosol_type,
            'relative_humidity': relative_humidity,
            'temperature': temperature
        }

    def compute_radiation_budget(self, atmosphere, surface_type='land',
                                surface_temperature=None, cloud_profile=None,
                                aerosol_profile=None, include_clouds=True,
                                include_aerosols=True):
        """
        计算完整的辐射收支（支持多列、多波段）

        参数:
        - atmosphere: 大气廓线字典
        - surface_type: 地表类型
        - surface_temperature: 地表温度
        - cloud_profile: 云廓线
        - aerosol_profile: 气溶胶廓线
        - include_clouds: 是否包含云效应
        - include_aerosols: 是否包含气溶胶效应

        返回:
        - 完整的辐射收支结果
          形状: (n_columns, n_bands, n_levels) 或 (n_columns, n_levels)
        """
        xp = self.xp

        if surface_temperature is None:
            surface_temperature = atmosphere['temperature'][:, 0]

        sw_fluxes = self.shortwave.compute_shortwave_fluxes(atmosphere, surface_type)

        if include_aerosols and aerosol_profile is not None:
            sw_fluxes = self.aerosol.apply_aerosol_effect_to_shortwave(
                sw_fluxes, aerosol_profile, self.shortwave.solar_zenith_angle[0]
            )

        if include_clouds and cloud_profile is not None:
            sw_fluxes = self.cloud.apply_cloud_effect_to_shortwave(
                sw_fluxes, cloud_profile, self.shortwave.solar_zenith_angle[0]
            )

        lw_fluxes = self.longwave.compute_longwave_fluxes(atmosphere, surface_temperature)

        if include_aerosols and aerosol_profile is not None:
            lw_fluxes = self.aerosol.apply_aerosol_effect_to_longwave(
                lw_fluxes, aerosol_profile
            )

        if include_clouds and cloud_profile is not None:
            lw_fluxes = self.cloud.apply_cloud_effect_to_longwave(
                lw_fluxes, cloud_profile
            )

        net_fluxes = {
            'downward_flux': sw_fluxes['downward_flux'] + lw_fluxes['downward_flux'],
            'upward_flux': sw_fluxes['upward_flux'] + lw_fluxes['upward_flux'],
            'net_flux': (sw_fluxes['downward_flux'] + lw_fluxes['downward_flux']) -
                       (sw_fluxes['upward_flux'] + lw_fluxes['upward_flux'])
        }

        cloud_forcing = None
        if include_clouds and cloud_profile is not None:
            cloud_profile_copy = cloud_profile.copy()
            cloud_profile_copy['surface_temperature'] = surface_temperature
            cloud_forcing = self.cloud.calculate_cloud_radiative_forcing(
                cloud_profile_copy, self.shortwave.solar_zenith_angle[0]
            )

        aerosol_forcing = None
        if include_aerosols and aerosol_profile is not None:
            surface_albedo = self.shortwave.calculate_surface_albedo(surface_type)
            aerosol_forcing = self.aerosol.calculate_total_aerosol_forcing(
                aerosol_profile, self.shortwave.solar_zenith_angle[0],
                surface_albedo, cloud_profile
            )

        results = {
            'shortwave': sw_fluxes,
            'longwave': lw_fluxes,
            'net': net_fluxes,
            'cloud_forcing': cloud_forcing,
            'aerosol_forcing': aerosol_forcing,
            'atmosphere': atmosphere,
            'n_columns': self.n_columns,
            'n_bands': self.shortwave.n_bands if self.use_bands else 1,
            'n_levels': len(atmosphere['height']),
            'band_names': self.shortwave.band_names if self.use_bands else None
        }

        return results

    def compute_heating_rate(self, radiation_results):
        """
        计算大气加热率（支持多列）

        参数:
        - radiation_results: 辐射计算结果

        返回:
        - 各层加热率 (K/day)，形状 (n_columns, n_levels-1) 或 (n_columns, n_bands, n_levels-1)
        """
        xp = self.xp

        atmosphere = radiation_results['atmosphere']
        net_flux = radiation_results['net']['net_flux']
        pressure = atmosphere['pressure']

        g = 9.81
        cp = 1004.0

        if net_flux.ndim == 3:
            n_columns, n_bands, n_levels = net_flux.shape
            heating_rate = xp.zeros((n_columns, n_bands, n_levels - 1))

            for col in range(n_columns):
                for b in range(n_bands):
                    for i in range(n_levels - 1):
                        flux_div = net_flux[col, b, i] - net_flux[col, b, i + 1]
                        p_thick = pressure[col, i] - pressure[col, i + 1] if pressure.ndim == 2 else pressure[i] - pressure[i + 1]
                        heating_rate[col, b, i] = (g / cp) * (flux_div / p_thick) * 86400

        else:
            n_columns, n_levels = net_flux.shape
            heating_rate = xp.zeros((n_columns, n_levels - 1))

            for col in range(n_columns):
                for i in range(n_levels - 1):
                    flux_div = net_flux[col, i] - net_flux[col, i + 1]
                    p_thick = pressure[col, i] - pressure[col, i + 1] if pressure.ndim == 2 else pressure[i] - pressure[i + 1]
                    heating_rate[col, i] = (g / cp) * (flux_div / p_thick) * 86400

        return heating_rate

    def to_numpy(self, data):
        """将数据转换为 NumPy 数组（从 GPU 传输）"""
        if using_backend:
            return bk.to_numpy(data)
        elif hasattr(data, 'get'):
            return data.get()
        return data

    def synchronize(self):
        """同步 GPU 操作"""
        if using_backend:
            bk.synchronize()

    def create_batch_runner(self, storage_file, batch_size=10):
        """
        创建批量运行器，集成 HDF5 存储

        参数:
        - storage_file: HDF5 文件路径
        - batch_size: 批量大小

        返回:
        - BatchFluxWriter 实例（如果可用）
        """
        if not FLUX_STORAGE_AVAILABLE:
            return None

        storage = FluxStorage(storage_file, mode='w')
        return BatchFluxWriter(storage, batch_size=batch_size)


def demo_gpu_vectorized():
    """演示 GPU/向量化功能"""
    print("=" * 70)
    print("Radiation Model with GPU/Vectorization Demo")
    print("=" * 70)
    print()

    n_columns = 5
    n_levels = 10

    print(f"Configuration:")
    print(f"  - Columns (horizontal points): {n_columns}")
    print(f"  - Vertical levels: {n_levels}")
    print()

    zenith_angles = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    surface_temps = np.array([298.0, 295.0, 290.0, 285.0, 280.0])

    model = RadiationModel(
        solar_zenith_angle=zenith_angles,
        day_of_year=180,
        n_columns=n_columns,
        use_bands=True,
        band_names=['visible', 'near_ir', 'uv'],
        backend='auto'
    )

    info = model.get_backend_info()
    print(f"Backend info: {info}")
    print()

    print("1. Creating vectorized atmosphere...")
    atmosphere = model.create_standard_atmosphere(
        n_levels=n_levels,
        surface_temperature=surface_temps
    )
    print(f"   Pressure shape: {atmosphere['pressure'].shape}")
    print(f"   Temperature shape: {atmosphere['temperature'].shape}")
    print()

    print("2. Creating cloud/aerosol profiles...")
    cloud_profile = model.create_default_cloud_profile(
        n_levels=n_levels,
        cloud_layers=[(2, 4, 'stratus', 0.7, 0.3)]
    )

    aerosol_profile = model.create_default_aerosol_profile(
        n_levels=n_levels,
        aerosol_layers=[(0, 2, 'sulfate', 15.0, 70.0)]
    )
    print()

    print("3. Computing radiation budget (vectorized)...")
    results = model.compute_radiation_budget(
        atmosphere,
        surface_type='land',
        cloud_profile=cloud_profile,
        aerosol_profile=aerosol_profile
    )

    sw = results['shortwave']
    lw = results['longwave']
    net = results['net']
    print()

    print("4. Results summary (vectorized):")
    print("-" * 70)

    for col in range(n_columns):
        print(f"\nColumn {col + 1} (zenith={zenith_angles[col]} deg, Ts={surface_temps[col]} K):")

        for b, band in enumerate(results['band_names']):
            print(f"  Band: {band}")
            print(f"    TOA - SW down: {sw['downward_flux'][col, b, 0]:.1f}, up: {sw['upward_flux'][col, b, 0]:.1f}")
            print(f"    TOA - LW up: {lw['upward_flux'][col, b, 0]:.1f}")
            print(f"    TOA - Net: {net['net_flux'][col, b, 0]:.1f}")

    print()
    print("=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    demo_gpu_vectorized()
