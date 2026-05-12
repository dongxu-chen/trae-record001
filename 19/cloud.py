"""
云效应对辐射传输的参数化方案
支持 GPU 加速、多列向量化
"""

try:
    import backend as bk
    xp = bk.get_backend()
    using_backend = True
except ImportError:
    import numpy as xp
    using_backend = False


class CloudEffect:
    """
    云效应的参数化方案
    支持:
    - GPU 加速 (CuPy) 或 CPU (NumPy)
    - 多列向量化
    """

    def __init__(self, n_columns=1):
        """
        参数:
        - n_columns: 列数（水平点数）
        """
        if using_backend:
            self.xp = bk.get_backend()
            self.device = bk.get_device()
        else:
            self.xp = xp
            self.device = 'cpu'

        self.n_columns = n_columns

        self.cloud_types = {
            'cirrus': {'albedo': 0.3, 'emissivity': 0.1, 'optical_depth_range': (0.1, 3.0)},
            'stratus': {'albedo': 0.6, 'emissivity': 0.95, 'optical_depth_range': (5.0, 20.0)},
            'cumulus': {'albedo': 0.5, 'emissivity': 0.9, 'optical_depth_range': (3.0, 15.0)},
            'cumulonimbus': {'albedo': 0.7, 'emissivity': 0.99, 'optical_depth_range': (10.0, 50.0)},
            'nimbostratus': {'albedo': 0.65, 'emissivity': 0.98, 'optical_depth_range': (10.0, 30.0)},
        }

    def _cloud_type_to_indices(self, cloud_type_list, n_layers):
        """将云类型列表转换为属性数组"""
        cloud_props = self.cloud_types

        albedo = self.xp.zeros((self.n_columns, n_layers))
        emissivity = self.xp.zeros((self.n_columns, n_layers))
        od_min = self.xp.zeros((self.n_columns, n_layers))
        od_max = self.xp.zeros((self.n_columns, n_layers))

        for col in range(self.n_columns):
            for layer in range(n_layers):
                if isinstance(cloud_type_list, list) and len(cloud_type_list) > 0:
                    if isinstance(cloud_type_list[0], list):
                        ct = cloud_type_list[col][layer] if layer < len(cloud_type_list[col]) else 'stratus'
                    else:
                        ct = cloud_type_list[layer] if layer < len(cloud_type_list) else 'stratus'
                else:
                    ct = cloud_type_list

                props = cloud_props.get(ct, cloud_props['stratus'])
                albedo[col, layer] = props['albedo']
                emissivity[col, layer] = props['emissivity']
                od_min[col, layer] = props['optical_depth_range'][0]
                od_max[col, layer] = props['optical_depth_range'][1]

        return albedo, emissivity, od_min, od_max

    def calculate_cloud_optical_depth(self, water_content, cloud_type='stratus', particle_size=10.0):
        """
        计算云的光学厚度，支持向量化

        参数:
        - water_content: 云水含量, 形状可以是标量、(n_columns,) 或 (n_columns, n_layers)
        - cloud_type: 云类型字符串或列表
        - particle_size: 云滴/冰晶大小

        返回:
        - 光学厚度数组
        """
        water_content = self.xp.asarray(water_content)

        if water_content.ndim == 0:
            n_layers = 1
            wc = self.xp.full((self.n_columns, n_layers), float(water_content))
        elif water_content.ndim == 1:
            if water_content.shape[0] == self.n_columns:
                n_layers = 1
                wc = water_content.reshape(-1, 1)
            else:
                n_layers = water_content.shape[0]
                wc = self.xp.broadcast_to(water_content, (self.n_columns, n_layers))
        else:
            n_layers = water_content.shape[1]
            wc = water_content

        particle_size = max(1.0, particle_size)

        wc_clamped = self.xp.maximum(0.01, self.xp.minimum(wc, 10.0))
        wc_clamped = self.xp.where(wc > 0, wc_clamped, 0.0)

        extinction_coefficient = 100 * wc_clamped / particle_size
        cloud_depth = 1000
        optical_depth = extinction_coefficient * cloud_depth / 1000

        if isinstance(cloud_type, list) and len(cloud_type) == self.n_columns and not isinstance(cloud_type[0], list):
            cloud_type_for_indices = [[ct] for ct in cloud_type]
        else:
            cloud_type_for_indices = cloud_type

        _, _, od_min, od_max = self._cloud_type_to_indices(cloud_type_for_indices, n_layers)

        optical_depth = self.xp.where(
            wc > 0,
            self.xp.maximum(od_min, self.xp.minimum(od_max, optical_depth)),
            0.0
        )

        if optical_depth.shape[1] == 1:
            optical_depth = optical_depth[:, 0]

        return optical_depth

    def calculate_cloud_albedo(self, optical_depth, cloud_type='stratus'):
        """
        计算云的短波反照率
        """
        optical_depth = self.xp.asarray(optical_depth)

        if optical_depth.ndim == 0:
            n_layers = 1
            od = self.xp.full((self.n_columns, n_layers), float(optical_depth))
        elif optical_depth.ndim == 1:
            if optical_depth.shape[0] == self.n_columns:
                n_layers = 1
                od = optical_depth.reshape(-1, 1)
            else:
                n_layers = optical_depth.shape[0]
                od = self.xp.broadcast_to(optical_depth, (self.n_columns, n_layers))
        else:
            n_layers = optical_depth.shape[1]
            od = optical_depth

        if isinstance(cloud_type, list) and len(cloud_type) == self.n_columns and not isinstance(cloud_type[0], list):
            cloud_type_for_indices = [[ct] for ct in cloud_type]
        else:
            cloud_type_for_indices = cloud_type

        base_albedo, _, _, _ = self._cloud_type_to_indices(cloud_type_for_indices, n_layers)

        albedo = 1 - self.xp.exp(-od / 2)
        albedo = albedo * base_albedo
        albedo = self.xp.maximum(0.1, self.xp.minimum(0.9, albedo))

        if albedo.shape[1] == 1:
            return albedo[:, 0]
        return albedo

    def calculate_cloud_emissivity(self, optical_depth, cloud_type='stratus'):
        """
        计算云的长波发射率
        """
        optical_depth = self.xp.asarray(optical_depth)

        if optical_depth.ndim == 0:
            n_layers = 1
            od = self.xp.full((self.n_columns, n_layers), float(optical_depth))
        elif optical_depth.ndim == 1:
            if optical_depth.shape[0] == self.n_columns:
                n_layers = 1
                od = optical_depth.reshape(-1, 1)
            else:
                n_layers = optical_depth.shape[0]
                od = self.xp.broadcast_to(optical_depth, (self.n_columns, n_layers))
        else:
            n_layers = optical_depth.shape[1]
            od = optical_depth

        if isinstance(cloud_type, list) and len(cloud_type) == self.n_columns and not isinstance(cloud_type[0], list):
            cloud_type_for_indices = [[ct] for ct in cloud_type]
        else:
            cloud_type_for_indices = cloud_type

        _, base_emissivity, _, _ = self._cloud_type_to_indices(cloud_type_for_indices, n_layers)

        emissivity = 1 - self.xp.exp(-od)
        emissivity = emissivity * base_emissivity
        emissivity = self.xp.maximum(0.05, self.xp.minimum(1.0, emissivity))

        if emissivity.shape[1] == 1:
            return emissivity[:, 0]
        return emissivity

    def calculate_shortwave_cloud_effect(self, cloud_fraction, optical_depth, solar_zenith_angle=0.0):
        """
        计算云对短波辐射的影响，支持向量化
        """
        cloud_fraction = self.xp.asarray(cloud_fraction)
        optical_depth = self.xp.asarray(optical_depth)

        if optical_depth.ndim <= 1:
            n_layers = 1
        else:
            n_layers = optical_depth.shape[1]

        if cloud_fraction.ndim == 0:
            cf = self.xp.full((self.n_columns, n_layers), float(cloud_fraction))
        elif cloud_fraction.ndim == 1:
            if cloud_fraction.shape[0] == self.n_columns:
                cf = cloud_fraction.reshape(-1, 1)
            else:
                cf = self.xp.broadcast_to(cloud_fraction, (self.n_columns, n_layers))
        else:
            cf = cloud_fraction

        if optical_depth.ndim == 0:
            od = self.xp.full((self.n_columns, n_layers), float(optical_depth))
        elif optical_depth.ndim == 1:
            if optical_depth.shape[0] == self.n_columns:
                od = optical_depth.reshape(-1, 1)
            else:
                od = self.xp.broadcast_to(optical_depth, (self.n_columns, n_layers))
        else:
            od = optical_depth

        cos_zenith = self.xp.maximum(0.01, self.xp.cos(self.xp.radians(solar_zenith_angle)))

        cloud_albedo = self.calculate_cloud_albedo(od)
        if cloud_albedo.ndim == 1:
            cloud_albedo = cloud_albedo.reshape(-1, 1)

        cloud_transmission = self.xp.exp(-od / cos_zenith)

        effective_albedo_change = cf * cloud_albedo
        effective_transmission = 1 - cf + cf * cloud_transmission

        if effective_albedo_change.shape[1] == 1:
            effective_albedo_change = effective_albedo_change[:, 0]
            effective_transmission = effective_transmission[:, 0]

        return effective_albedo_change, effective_transmission

    def calculate_longwave_cloud_effect(self, cloud_fraction, optical_depth, cloud_temperature,
                                        surface_temperature):
        """
        计算云对长波辐射的影响，支持向量化
        """
        STEFAN_BOLTZMANN = 5.67e-8

        cloud_fraction = self.xp.asarray(cloud_fraction)
        optical_depth = self.xp.asarray(optical_depth)
        cloud_temperature = self.xp.asarray(cloud_temperature)
        surface_temperature = self.xp.asarray(surface_temperature)

        if optical_depth.ndim <= 1:
            n_layers = 1
        else:
            n_layers = optical_depth.shape[1]

        if cloud_fraction.ndim == 0:
            cf = self.xp.full((self.n_columns, n_layers), float(cloud_fraction))
        elif cloud_fraction.ndim == 1:
            if cloud_fraction.shape[0] == self.n_columns:
                cf = cloud_fraction.reshape(-1, 1)
            else:
                cf = self.xp.broadcast_to(cloud_fraction, (self.n_columns, n_layers))
        else:
            cf = cloud_fraction

        if optical_depth.ndim == 0:
            od = self.xp.full((self.n_columns, n_layers), float(optical_depth))
        elif optical_depth.ndim == 1:
            if optical_depth.shape[0] == self.n_columns:
                od = optical_depth.reshape(-1, 1)
            else:
                od = self.xp.broadcast_to(optical_depth, (self.n_columns, n_layers))
        else:
            od = optical_depth

        if cloud_temperature.ndim == 0:
            ct = self.xp.full((self.n_columns, n_layers), float(cloud_temperature))
        elif cloud_temperature.ndim == 1:
            if cloud_temperature.shape[0] == self.n_columns:
                ct = cloud_temperature.reshape(-1, 1)
            else:
                ct = self.xp.broadcast_to(cloud_temperature, (self.n_columns, n_layers))
        else:
            ct = cloud_temperature

        cloud_emissivity = self.calculate_cloud_emissivity(od)
        if cloud_emissivity.ndim == 1:
            cloud_emissivity = cloud_emissivity.reshape(-1, 1)

        surface_emission = STEFAN_BOLTZMANN * surface_temperature ** 4
        cloud_emission = cloud_emissivity * STEFAN_BOLTZMANN * ct ** 4

        if surface_emission.ndim == 0:
            surface_emission = self.xp.full((self.n_columns, n_layers), float(surface_emission))
        elif surface_emission.ndim == 1:
            surface_emission = surface_emission.reshape(-1, 1)

        cloud_forcing = cf * (cloud_emission - surface_emission)

        if cloud_forcing.shape[1] == 1:
            cloud_forcing = cloud_forcing[:, 0]

        return cloud_forcing

    def calculate_cloud_radiative_forcing(self, cloud_profile, solar_zenith_angle=0.0):
        """
        计算各层云的辐射强迫
        """
        n_layers = len(cloud_profile['cloud_fraction'])

        sw_forcing = self.xp.zeros((self.n_columns, n_layers))
        lw_forcing = self.xp.zeros((self.n_columns, n_layers))

        cf = self.xp.asarray(cloud_profile['cloud_fraction'])
        wc = self.xp.asarray(cloud_profile['water_content'])
        temp = self.xp.asarray(cloud_profile['temperature'])
        surface_temp = cloud_profile.get('surface_temperature', 298.0)

        optical_depth = self.calculate_cloud_optical_depth(wc, cloud_profile.get('cloud_type', 'stratus'))

        sw_albedo_change, _ = self.calculate_shortwave_cloud_effect(
            cf, optical_depth, solar_zenith_angle
        )
        sw_forcing = -sw_albedo_change * 100

        lw_forcing = self.calculate_longwave_cloud_effect(
            cf, optical_depth, temp, surface_temp
        )

        return {
            'shortwave_forcing': sw_forcing,
            'longwave_forcing': lw_forcing,
            'net_forcing': sw_forcing + lw_forcing
        }

    def apply_cloud_effect_to_shortwave(self, sw_fluxes, cloud_profile, solar_zenith_angle=0.0):
        """
        将云效应应用到短波辐射通量
        """
        modified_fluxes = {}
        for k, v in sw_fluxes.items():
            if hasattr(v, 'copy'):
                modified_fluxes[k] = v.copy()
            else:
                modified_fluxes[k] = v

        n_columns = modified_fluxes['downward_flux'].shape[0]
        n_levels = modified_fluxes['downward_flux'].shape[-1]

        use_bands = modified_fluxes['downward_flux'].ndim == 3

        cf = self.xp.asarray(cloud_profile['cloud_fraction'])
        wc = self.xp.asarray(cloud_profile['water_content'])

        if cf.ndim == 1:
            cf = self.xp.broadcast_to(cf, (n_columns, n_levels))
        if wc.ndim == 1:
            wc = self.xp.broadcast_to(wc, (n_columns, n_levels))

        ct = cloud_profile.get('cloud_type', 'stratus')

        for i in range(n_levels - 1):
            cf_i = cf[:, i] if cf.ndim == 2 else cf
            wc_i = wc[:, i] if wc.ndim == 2 else wc

            mask = (cf_i > 0) & (wc_i > 0)

            if self.xp.any(mask):
                od_i = self.calculate_cloud_optical_depth(wc_i, ct)
                _, transmission = self.calculate_shortwave_cloud_effect(cf_i, od_i, solar_zenith_angle)
                albedo_change = self.calculate_cloud_albedo(od_i, ct) * cf_i

                if use_bands:
                    n_bands = modified_fluxes['downward_flux'].shape[1]
                    for b in range(n_bands):
                        modified_fluxes['downward_flux'][:, b, i + 1] *= transmission
                        modified_fluxes['upward_flux'][:, b, i] *= (1 + albedo_change * 0.5)
                else:
                    modified_fluxes['downward_flux'][:, i + 1] *= transmission
                    modified_fluxes['upward_flux'][:, i] *= (1 + albedo_change * 0.5)

        modified_fluxes['net_flux'] = modified_fluxes['downward_flux'] - modified_fluxes['upward_flux']

        return modified_fluxes

    def apply_cloud_effect_to_longwave(self, lw_fluxes, cloud_profile):
        """
        将云效应应用到长波辐射通量
        """
        modified_fluxes = {}
        for k, v in lw_fluxes.items():
            if hasattr(v, 'copy'):
                modified_fluxes[k] = v.copy()
            else:
                modified_fluxes[k] = v
        STEFAN_BOLTZMANN = 5.67e-8

        n_columns = modified_fluxes['downward_flux'].shape[0]
        n_levels = modified_fluxes['downward_flux'].shape[-1]

        use_bands = modified_fluxes['downward_flux'].ndim == 3

        cf = self.xp.asarray(cloud_profile['cloud_fraction'])
        wc = self.xp.asarray(cloud_profile['water_content'])
        temp = self.xp.asarray(cloud_profile['temperature'])

        if cf.ndim == 1:
            cf = self.xp.broadcast_to(cf, (n_columns, n_levels))
        if wc.ndim == 1:
            wc = self.xp.broadcast_to(wc, (n_columns, n_levels))
        if temp.ndim == 1:
            temp = self.xp.broadcast_to(temp, (n_columns, n_levels))

        ct = cloud_profile.get('cloud_type', 'stratus')

        for i in range(n_levels):
            cf_i = cf[:, i] if cf.ndim == 2 else cf
            wc_i = wc[:, i] if wc.ndim == 2 else wc
            temp_i = temp[:, i] if temp.ndim == 2 else temp

            mask = (cf_i > 0) & (wc_i > 0)

            if self.xp.any(mask):
                od_i = self.calculate_cloud_optical_depth(wc_i, ct)
                emissivity = self.calculate_cloud_emissivity(od_i, ct)

                cloud_emission = emissivity * STEFAN_BOLTZMANN * temp_i ** 4
                cloud_forcing = cf_i * cloud_emission

                if use_bands:
                    n_bands = modified_fluxes['downward_flux'].shape[1]
                    for b in range(n_bands):
                        modified_fluxes['downward_flux'][:, b, i] += cloud_forcing * 0.3
                        modified_fluxes['upward_flux'][:, b, i] *= (1 - cf_i * emissivity * 0.5)
                else:
                    modified_fluxes['downward_flux'][:, i] += cloud_forcing * 0.3
                    modified_fluxes['upward_flux'][:, i] *= (1 - cf_i * emissivity * 0.5)

        modified_fluxes['net_flux'] = modified_fluxes['downward_flux'] - modified_fluxes['upward_flux']

        return modified_fluxes

    def to_numpy(self, data):
        """将 GPU 数据转换为 NumPy"""
        if using_backend:
            return bk.to_numpy(data)
        return data

    def synchronize(self):
        """同步 GPU 操作"""
        if using_backend:
            bk.synchronize()
