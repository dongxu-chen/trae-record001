"""
太阳短波辐射参数化方案
支持 GPU 加速、多波段计算、多列向量化
"""

try:
    import backend as bk
    xp = bk.get_backend()
    using_backend = True
except ImportError:
    import numpy as xp
    using_backend = False


class ShortwaveRadiation:
    """
    太阳短波辐射参数化方案
    支持:
    - GPU 加速 (CuPy) 或 CPU (NumPy)
    - 多波段计算
    - 多列向量化
    """

    SOLAR_CONSTANT = 1361.0
    STEFAN_BOLTZMANN = 5.67e-8

    DEFAULT_BANDS = {
        'visible': {'wavelength': [0.4, 0.7], 'solar_fraction': 0.5,
                    'rayleigh_coeff': 1.5, 'water_vapor_coeff': 0.005,
                    'ozone_coeff': 0.08},
        'near_ir': {'wavelength': [0.7, 4.0], 'solar_fraction': 0.45,
                    'rayleigh_coeff': 0.3, 'water_vapor_coeff': 0.02,
                    'ozone_coeff': 0.01},
        'uv': {'wavelength': [0.2, 0.4], 'solar_fraction': 0.05,
               'rayleigh_coeff': 3.0, 'water_vapor_coeff': 0.001,
               'ozone_coeff': 0.2},
    }

    def __init__(self, solar_zenith_angle=0.0, day_of_year=180,
                 n_columns=1, use_bands=False, band_names=None):
        """
        参数:
        - solar_zenith_angle: 太阳天顶角 (度), 可以是标量或数组 (n_columns,)
        - day_of_year: 年中的第几天
        - n_columns: 列数（水平点数）
        - use_bands: 是否使用多波段
        - band_names: 波段名称列表，如 ['visible', 'near_ir', 'uv']
        """
        if using_backend:
            self.xp = bk.get_backend()
            self.device = bk.get_device()
        else:
            self.xp = xp
            self.device = 'cpu'

        self.n_columns = n_columns
        self.use_bands = use_bands

        if isinstance(solar_zenith_angle, (int, float)):
            self.solar_zenith_angle = self.xp.full(n_columns, solar_zenith_angle)
        else:
            self.solar_zenith_angle = self.xp.asarray(solar_zenith_angle)

        self.day_of_year = day_of_year

        if use_bands:
            if band_names is None:
                band_names = list(self.DEFAULT_BANDS.keys())
            self.bands = {name: self.DEFAULT_BANDS[name] for name in band_names}
            self.band_names = band_names
            self.n_bands = len(band_names)
            self.solar_fractions = self.xp.array([self.bands[b]['solar_fraction'] for b in band_names])
        else:
            self.bands = None
            self.band_names = ['broadband']
            self.n_bands = 1
            self.solar_fractions = self.xp.array([1.0])

        self._shape_info = None

    def _get_shape(self, n_levels):
        """获取数据形状"""
        if self.use_bands:
            return (self.n_columns, self.n_bands, n_levels)
        else:
            return (self.n_columns, n_levels)

    def _broadcast_cos_zenith(self, n_levels):
        """广播太阳天顶角余弦到完整形状"""
        cos_z = self.calculate_cos_zenith()

        if self.use_bands:
            cos_z = cos_z[:, self.xp.newaxis, self.xp.newaxis]
            return self.xp.broadcast_to(cos_z, (self.n_columns, self.n_bands, n_levels))
        else:
            cos_z = cos_z[:, self.xp.newaxis]
            return self.xp.broadcast_to(cos_z, (self.n_columns, n_levels))

    def calculate_solar_irradiance(self):
        """计算日地距离校正后的太阳辐照度"""
        eccentricity = 0.0167
        perihelion_day = 3
        day_angle = 2 * self.xp.pi * (self.day_of_year - perihelion_day) / 365.25
        correction_factor = 1 + eccentricity * self.xp.cos(day_angle)
        return self.SOLAR_CONSTANT * correction_factor

    def calculate_cos_zenith(self):
        """计算太阳天顶角余弦，确保物理合理（非负）"""
        cos_zenith = self.xp.cos(self.xp.radians(self.solar_zenith_angle))
        return self.xp.maximum(0.0, cos_zenith)

    def calculate_atmospheric_top_flux(self, per_band=True):
        """
        计算大气顶的太阳短波辐射通量

        参数:
        - per_band: 是否按波段返回
        """
        solar_irradiance = self.calculate_solar_irradiance()
        cos_zenith = self.calculate_cos_zenith()

        if self.use_bands and per_band:
            total_flux = solar_irradiance * cos_zenith[:, self.xp.newaxis]
            band_fluxes = total_flux * self.solar_fractions[self.xp.newaxis, :]
            return band_fluxes
        else:
            return solar_irradiance * cos_zenith

    def calculate_rayleigh_scattering(self, pressure, pressure_surface=101325.0, band_name=None):
        """
        计算瑞利散射光学厚度，支持多波段

        参数:
        - pressure: 气压数组
        - pressure_surface: 地表气压
        - band_name: 波段名称（用于多波段）
        """
        normalized_pressure = pressure / pressure_surface

        if self.use_bands and band_name is not None:
            rayleigh_coeff = self.bands[band_name]['rayleigh_coeff']
        else:
            rayleigh_coeff = 1.0

        optical_depth = 0.008569 * rayleigh_coeff * normalized_pressure * (
            1 + 0.0113 * normalized_pressure + 0.0013 * normalized_pressure ** 2
        )
        return optical_depth

    def calculate_gas_absorption(self, water_vapor, ozone, temperature, band_name=None):
        """
        计算气体吸收（水汽和臭氧），支持多波段
        """
        if self.use_bands and band_name is not None:
            wv_coeff = self.bands[band_name]['water_vapor_coeff']
            oz_coeff = self.bands[band_name]['ozone_coeff']
        else:
            wv_coeff = 0.01
            oz_coeff = 0.05

        water_vapor_absorption = wv_coeff * self.xp.sqrt(self.xp.maximum(water_vapor, 1e-10))
        ozone_absorption = oz_coeff * ozone * (temperature / 273.15)
        return water_vapor_absorption + ozone_absorption

    def calculate_surface_albedo(self, surface_type='land', band_name=None):
        """
        计算地表反照率，支持多波段依赖
        """
        if isinstance(surface_type, str):
            albedo_map = {
                'land': 0.3,
                'ocean': 0.1,
                'snow': 0.8,
                'ice': 0.6,
                'forest': 0.15,
                'desert': 0.35
            }
            base_albedo = albedo_map.get(surface_type, 0.3)
        else:
            base_albedo = self.xp.asarray(surface_type)

        if self.use_bands and band_name is not None:
            if band_name == 'uv':
                spectral_factor = 1.1
            elif band_name == 'visible':
                spectral_factor = 1.0
            elif band_name == 'near_ir':
                spectral_factor = 0.9
            else:
                spectral_factor = 1.0
            base_albedo = base_albedo * spectral_factor

        return base_albedo

    def calculate_transmission(self, optical_depth, cos_zenith):
        """
        计算透射率（指数衰减），支持向量化
        """
        cos_zenith_safe = self.xp.maximum(cos_zenith, 0.01)
        transmission = self.xp.where(
            cos_zenith <= 0,
            0.0,
            self.xp.exp(-optical_depth / cos_zenith_safe)
        )
        return transmission

    def compute_band_optical_depths(self, profile):
        """
        计算所有波段的光学厚度

        返回:
        - total_od: 形状 (n_columns, n_bands, n_levels) 或 (n_columns, n_levels)
        """
        pressure = self.xp.asarray(profile['pressure'])
        temperature = self.xp.asarray(profile['temperature'])
        water_vapor = self.xp.asarray(profile['water_vapor'])
        ozone = self.xp.asarray(profile['ozone'])

        n_levels = pressure.shape[-1]

        if pressure.ndim == 1:
            pressure = self.xp.broadcast_to(pressure, (self.n_columns, n_levels))
            temperature = self.xp.broadcast_to(temperature, (self.n_columns, n_levels))
            water_vapor = self.xp.broadcast_to(water_vapor, (self.n_columns, n_levels))
            ozone = self.xp.broadcast_to(ozone, (self.n_columns, n_levels))

        if self.use_bands:
            total_od = self.xp.zeros((self.n_columns, self.n_bands, n_levels))
            for b, band_name in enumerate(self.band_names):
                rayleigh_od = self.calculate_rayleigh_scattering(pressure, band_name=band_name)
                gas_od = self.calculate_gas_absorption(water_vapor, ozone, temperature, band_name=band_name)
                total_od[:, b, :] = rayleigh_od + gas_od
        else:
            rayleigh_od = self.calculate_rayleigh_scattering(pressure)
            gas_od = self.calculate_gas_absorption(water_vapor, ozone, temperature)
            total_od = rayleigh_od + gas_od

        return total_od

    def compute_shortwave_fluxes(self, profile, surface_type='land', surface_albedo=None):
        """
        计算各层的短波辐射通量

        参数:
        - profile: 大气廓线字典，包含 pressure, temperature, water_vapor, ozone
                   每个变量形状可以是 (n_levels,) 或 (n_columns, n_levels)
        - surface_type: 地表类型或地表反照率数组
        - surface_albedo: 显式指定地表反照率（可选）

        返回:
        - 各层向上、向下短波辐射通量，形状:
          (n_columns, n_bands, n_levels) 或 (n_columns, n_levels)
        """
        pressure = self.xp.asarray(profile['pressure'])
        n_levels = pressure.shape[-1]

        if pressure.ndim == 1:
            n_levels_1d = n_levels
        else:
            n_levels_1d = n_levels

        total_od = self.compute_band_optical_depths(profile)

        cos_zenith_broadcast = self._broadcast_cos_zenith(n_levels_1d)

        if self.use_bands:
            downward_flux = self.xp.zeros((self.n_columns, self.n_bands, n_levels_1d))
            upward_flux = self.xp.zeros((self.n_columns, self.n_bands, n_levels_1d))

            toa_flux = self.calculate_atmospheric_top_flux(per_band=True)
            downward_flux[:, :, 0] = toa_flux

            for i in range(n_levels_1d - 1):
                transmission = self.calculate_transmission(total_od[:, :, i], cos_zenith_broadcast[:, :, i])
                downward_flux[:, :, i + 1] = downward_flux[:, :, i] * transmission

            if surface_albedo is not None:
                albedo = self.xp.asarray(surface_albedo)
            else:
                albedo = self.xp.array([self.calculate_surface_albedo(surface_type, b)
                                     for b in self.band_names])
                albedo = self.xp.broadcast_to(albedo, (self.n_columns, self.n_bands))

            upward_flux[:, :, -1] = downward_flux[:, :, -1] * albedo

            for i in range(n_levels_1d - 2, -1, -1):
                transmission = self.calculate_transmission(total_od[:, :, i], cos_zenith_broadcast[:, :, i])
                upward_flux[:, :, i] = upward_flux[:, :, i + 1] * transmission

        else:
            downward_flux = self.xp.zeros((self.n_columns, n_levels_1d))
            upward_flux = self.xp.zeros((self.n_columns, n_levels_1d))

            toa_flux = self.calculate_atmospheric_top_flux(per_band=False)
            downward_flux[:, 0] = toa_flux

            for i in range(n_levels_1d - 1):
                transmission = self.calculate_transmission(total_od[:, i], cos_zenith_broadcast[:, i])
                downward_flux[:, i + 1] = downward_flux[:, i] * transmission

            if surface_albedo is not None:
                albedo = self.xp.asarray(surface_albedo)
                if albedo.ndim == 0:
                    albedo = self.xp.full(self.n_columns, albedo)
            else:
                albedo_val = self.calculate_surface_albedo(surface_type)
                albedo = self.xp.full(self.n_columns, albedo_val)

            upward_flux[:, -1] = downward_flux[:, -1] * albedo

            for i in range(n_levels_1d - 2, -1, -1):
                transmission = self.calculate_transmission(total_od[:, i], cos_zenith_broadcast[:, i])
                upward_flux[:, i] = upward_flux[:, i + 1] * transmission

        return {
            'downward_flux': downward_flux,
            'upward_flux': upward_flux,
            'net_flux': downward_flux - upward_flux,
            'n_columns': self.n_columns,
            'n_bands': self.n_bands,
            'n_levels': n_levels_1d,
            'band_names': self.band_names if self.use_bands else None
        }

    def integrate_band_fluxes(self, band_results):
        """
        积分多波段通量得到宽带通量
        """
        if not self.use_bands:
            return band_results

        solar_fractions = self.solar_fractions

        broadband_down = self.xp.sum(
            band_results['downward_flux'] * solar_fractions[self.xp.newaxis, :, self.xp.newaxis],
            axis=1
        )
        broadband_up = self.xp.sum(
            band_results['upward_flux'] * solar_fractions[self.xp.newaxis, :, self.xp.newaxis],
            axis=1
        )

        return {
            'downward_flux': broadband_down,
            'upward_flux': broadband_up,
            'net_flux': broadband_down - broadband_up,
            'band_results': band_results
        }

    def to_numpy(self, data):
        """将 GPU 数据转换为 NumPy"""
        if using_backend:
            return bk.to_numpy(data)
        return data

    def synchronize(self):
        """同步 GPU 操作"""
        if using_backend:
            bk.synchronize()
