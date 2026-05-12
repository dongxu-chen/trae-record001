"""
地面长波辐射参数化方案
支持 GPU 加速、多列向量化
"""

try:
    import backend as bk
    xp = bk.get_backend()
    using_backend = True
except ImportError:
    import numpy as xp
    using_backend = False


class LongwaveRadiation:
    """
    地面长波辐射参数化方案
    支持:
    - GPU 加速 (CuPy) 或 CPU (NumPy)
    - 多列向量化
    """

    STEFAN_BOLTZMANN = 5.67e-8
    EARTH_EMISSIVITY = 0.95

    LW_BANDS = {
        'window': {'wavelength': [8.0, 14.0], 'co2_weight': 0.3, 'wv_weight': 0.6},
        'strong_co2': {'wavelength': [13.0, 17.0], 'co2_weight': 0.9, 'wv_weight': 0.2},
        'rotational_wv': {'wavelength': [0.0, 8.0], 'co2_weight': 0.1, 'wv_weight': 0.95},
    }

    def __init__(self, surface_emissivity=0.95, n_columns=1, use_bands=False):
        """
        参数:
        - surface_emissivity: 地表发射率
        - n_columns: 列数（水平点数）
        - use_bands: 是否使用多波段
        """
        if using_backend:
            self.xp = bk.get_backend()
            self.device = bk.get_device()
        else:
            self.xp = xp
            self.device = 'cpu'

        self.n_columns = n_columns
        self.use_bands = use_bands

        if isinstance(surface_emissivity, (int, float)):
            self.surface_emissivity = self.xp.full(n_columns, surface_emissivity)
        else:
            self.surface_emissivity = self.xp.asarray(surface_emissivity)

        if use_bands:
            self.band_names = list(self.LW_BANDS.keys())
            self.n_bands = len(self.band_names)
        else:
            self.band_names = ['broadband']
            self.n_bands = 1

    def blackbody_radiation(self, temperature):
        """
        计算黑体辐射通量，支持向量化
        """
        return self.STEFAN_BOLTZMANN * temperature ** 4

    def graybody_radiation(self, temperature, emissivity):
        """
        计算灰体辐射通量
        """
        return emissivity * self.blackbody_radiation(temperature)

    def planck_function(self, temperature, wavelength_micron=10.0):
        """
        计算普朗克函数（简化版本，用于多波段）
        """
        h = 6.626e-34
        c = 3.0e8
        k = 1.38e-23

        wavelength = wavelength_micron * 1e-6
        exponent = h * c / (wavelength * k * temperature)

        with self.xp.errstate(over='ignore'):
            exp_term = self.xp.exp(self.xp.minimum(exponent, 100.0))
            radiance = 2 * h * c ** 2 / (wavelength ** 5 * (exp_term - 1))

        return radiance

    def calculate_water_vapor_optical_depth(self, water_vapor_path, band_name=None):
        """
        计算水汽的光学厚度，支持多波段
        """
        water_vapor_path = self.xp.maximum(water_vapor_path, 1e-6)

        if self.use_bands and band_name is not None:
            wv_weight = self.LW_BANDS[band_name]['wv_weight']
        else:
            wv_weight = 0.5

        optical_depth = 0.1 * wv_weight * water_vapor_path ** 0.8
        return optical_depth

    def calculate_carbon_dioxide_optical_depth(self, co2_mixing_ratio=400e-6, band_name=None):
        """
        计算CO2的光学厚度，支持多波段
        """
        if self.use_bands and band_name is not None:
            co2_weight = self.LW_BANDS[band_name]['co2_weight']
        else:
            co2_weight = 0.5

        return 0.02 * co2_weight * self.xp.log(1 + 1000 * co2_mixing_ratio)

    def calculate_ozone_optical_depth(self, ozone_path):
        """
        计算臭氧的光学厚度
        """
        return 0.01 * ozone_path

    def calculate_all_optical_depths(self, profile):
        """
        计算所有层的光学厚度

        返回:
        - total_od: 形状 (n_columns, n_levels) 或 (n_columns, n_bands, n_levels)
        """
        water_vapor = self.xp.asarray(profile['water_vapor'])
        ozone = self.xp.asarray(profile['ozone'])
        co2 = profile.get('co2', 400e-6)

        n_levels = water_vapor.shape[-1]

        if water_vapor.ndim == 1:
            water_vapor = self.xp.broadcast_to(water_vapor, (self.n_columns, n_levels))
            ozone = self.xp.broadcast_to(ozone, (self.n_columns, n_levels))

        if self.use_bands:
            total_od = self.xp.zeros((self.n_columns, self.n_bands, n_levels))
            for b, band_name in enumerate(self.band_names):
                wv_od = self.calculate_water_vapor_optical_depth(water_vapor, band_name)
                co2_od = self.calculate_carbon_dioxide_optical_depth(co2, band_name)
                oz_od = self.calculate_ozone_optical_depth(ozone)
                total_od[:, b, :] = wv_od + co2_od + oz_od
        else:
            wv_od = self.calculate_water_vapor_optical_depth(water_vapor)
            co2_od = self.calculate_carbon_dioxide_optical_depth(co2)
            oz_od = self.calculate_ozone_optical_depth(ozone)
            total_od = wv_od + co2_od + oz_od

        return total_od

    def calculate_transmittance(self, optical_depth):
        """
        计算透射率，支持向量化
        """
        return self.xp.exp(-optical_depth)

    def calculate_emissivity(self, optical_depth):
        """
        计算发射率，支持向量化
        """
        return 1 - self.xp.exp(-optical_depth)

    def _broadcast_2d(self, arr, target_shape):
        """广播数组到目标形状"""
        arr = self.xp.asarray(arr)
        if arr.ndim == 0:
            return self.xp.broadcast_to(arr, target_shape)
        elif arr.ndim == 1:
            if arr.shape[0] == self.n_columns:
                return arr[:, self.xp.newaxis]
            else:
                return arr[self.xp.newaxis, :]
        return arr

    def compute_longwave_fluxes(self, profile, surface_temperature):
        """
        计算各层的长波辐射通量

        参数:
        - profile: 大气廓线字典
        - surface_temperature: 地表温度 (K), 可以是标量或 (n_columns,) 数组

        返回:
        - 各层向上、向下长波辐射通量，形状:
          (n_columns, n_bands, n_levels) 或 (n_columns, n_levels)
        """
        pressure = self.xp.asarray(profile['pressure'])
        temperature = self.xp.asarray(profile['temperature'])
        n_levels = pressure.shape[-1]

        if temperature.ndim == 1:
            temperature = self.xp.broadcast_to(temperature, (self.n_columns, n_levels))

        total_od = self.calculate_all_optical_depths(profile)

        if isinstance(surface_temperature, (int, float)):
            Ts = self.xp.full(self.n_columns, surface_temperature)
        else:
            Ts = self.xp.asarray(surface_temperature)

        if self.use_bands:
            downward_flux = self.xp.zeros((self.n_columns, self.n_bands, n_levels))
            upward_flux = self.xp.zeros((self.n_columns, self.n_bands, n_levels))

            for b in range(self.n_bands):
                surface_emission = self.graybody_radiation(
                    Ts, self.surface_emissivity
                )
                upward_flux[:, b, -1] = surface_emission

                for i in range(n_levels - 2, -1, -1):
                    layer_od = total_od[:, b, i + 1]
                    layer_temp = temperature[:, i + 1]

                    layer_emissivity = self.calculate_emissivity(layer_od)
                    layer_transmittance = self.calculate_transmittance(layer_od)

                    layer_emission = self.graybody_radiation(layer_temp, layer_emissivity)

                    upward_flux[:, b, i] = layer_emission + layer_transmittance * upward_flux[:, b, i + 1]

                for i in range(1, n_levels):
                    layer_od = total_od[:, b, i - 1]
                    layer_temp = temperature[:, i - 1]

                    layer_emissivity = self.calculate_emissivity(layer_od)
                    layer_transmittance = self.calculate_transmittance(layer_od)

                    layer_emission = self.graybody_radiation(layer_temp, layer_emissivity)

                    downward_flux[:, b, i] = layer_emission + layer_transmittance * downward_flux[:, b, i - 1]

        else:
            downward_flux = self.xp.zeros((self.n_columns, n_levels))
            upward_flux = self.xp.zeros((self.n_columns, n_levels))

            surface_emission = self.graybody_radiation(Ts, self.surface_emissivity)
            upward_flux[:, -1] = surface_emission

            for i in range(n_levels - 2, -1, -1):
                layer_od = total_od[:, i + 1]
                layer_temp = temperature[:, i + 1]

                layer_emissivity = self.calculate_emissivity(layer_od)
                layer_transmittance = self.calculate_transmittance(layer_od)

                layer_emission = self.graybody_radiation(layer_temp, layer_emissivity)

                upward_flux[:, i] = layer_emission + layer_transmittance * upward_flux[:, i + 1]

            for i in range(1, n_levels):
                layer_od = total_od[:, i - 1]
                layer_temp = temperature[:, i - 1]

                layer_emissivity = self.calculate_emissivity(layer_od)
                layer_transmittance = self.calculate_transmittance(layer_od)

                layer_emission = self.graybody_radiation(layer_temp, layer_emissivity)

                downward_flux[:, i] = layer_emission + layer_transmittance * downward_flux[:, i - 1]

        return {
            'downward_flux': downward_flux,
            'upward_flux': upward_flux,
            'net_flux': downward_flux - upward_flux,
            'n_columns': self.n_columns,
            'n_bands': self.n_bands,
            'n_levels': n_levels,
            'band_names': self.band_names if self.use_bands else None
        }

    def compute_surface_longwave_flux(self, surface_temperature, air_temperature, water_vapor):
        """
        计算地表净长波辐射通量（简化版本，支持向量化）
        """
        surface_temperature = self.xp.asarray(surface_temperature)
        air_temperature = self.xp.asarray(air_temperature)
        water_vapor = self.xp.asarray(water_vapor)

        surface_emission = self.graybody_radiation(surface_temperature, self.surface_emissivity)

        water_vapor_depth = self.calculate_water_vapor_optical_depth(water_vapor)
        atmospheric_emissivity = self.calculate_emissivity(water_vapor_depth)
        downward_atmospheric = self.graybody_radiation(air_temperature, atmospheric_emissivity)

        return downward_atmospheric - surface_emission

    def to_numpy(self, data):
        """将 GPU 数据转换为 NumPy"""
        if using_backend:
            return bk.to_numpy(data)
        return data

    def synchronize(self):
        """同步 GPU 操作"""
        if using_backend:
            bk.synchronize()
