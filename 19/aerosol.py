"""
气溶胶效应的参数化方案
支持 GPU 加速、多列向量化
"""

try:
    import backend as bk
    xp = bk.get_backend()
    using_backend = True
except ImportError:
    import numpy as xp
    using_backend = False


class AerosolEffect:
    """
    气溶胶效应的参数化方案
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

        self.aerosol_types = {
            'sulfate': {
                'extinction_efficiency': 3.0,
                'single_scattering_albedo': 0.95,
                'asymmetry_parameter': 0.6,
                'absorption_coefficient': 0.05,
                'color_index': 1.0
            },
            'black_carbon': {
                'extinction_efficiency': 2.0,
                'single_scattering_albedo': 0.2,
                'asymmetry_parameter': 0.5,
                'absorption_coefficient': 0.8,
                'color_index': 1.5
            },
            'organic_carbon': {
                'extinction_efficiency': 2.5,
                'single_scattering_albedo': 0.8,
                'asymmetry_parameter': 0.55,
                'absorption_coefficient': 0.2,
                'color_index': 1.2
            },
            'dust': {
                'extinction_efficiency': 1.5,
                'single_scattering_albedo': 0.7,
                'asymmetry_parameter': 0.7,
                'absorption_coefficient': 0.3,
                'color_index': 2.0
            },
            'sea_salt': {
                'extinction_efficiency': 2.2,
                'single_scattering_albedo': 0.98,
                'asymmetry_parameter': 0.65,
                'absorption_coefficient': 0.02,
                'color_index': 0.8
            }
        }

    def _aerosol_type_to_indices(self, aerosol_type_list, n_layers):
        """将气溶胶类型列表转换为属性数组"""
        ssa = self.xp.zeros((self.n_columns, n_layers))
        g = self.xp.zeros((self.n_columns, n_layers))
        ext_eff = self.xp.zeros((self.n_columns, n_layers))

        for col in range(self.n_columns):
            for layer in range(n_layers):
                if isinstance(aerosol_type_list, list) and len(aerosol_type_list) > 0:
                    if isinstance(aerosol_type_list[0], list):
                        at = aerosol_type_list[col][layer] if layer < len(aerosol_type_list[col]) else 'sulfate'
                    else:
                        at = aerosol_type_list[layer] if layer < len(aerosol_type_list) else 'sulfate'
                else:
                    at = aerosol_type_list

                props = self.aerosol_types.get(at, self.aerosol_types['sulfate'])
                ssa[col, layer] = props['single_scattering_albedo']
                g[col, layer] = props['asymmetry_parameter']
                ext_eff[col, layer] = props['extinction_efficiency']

        return ssa, g, ext_eff

    def calculate_aerosol_optical_depth(self, aerosol_mass_concentration, aerosol_type='sulfate',
                                     relative_humidity=50.0, scale_height=2.0):
        """
        计算气溶胶光学厚度 (AOD)，支持向量化
        输入可以是:
        - 标量: 所有列所有层相同
        - (n_columns,): 每列一个值（所有层相同）
        - (n_columns, n_layers): 完整的向量化数据
        """
        aerosol_mass_concentration = self.xp.asarray(aerosol_mass_concentration)

        if aerosol_mass_concentration.ndim == 0:
            n_layers = 1
            mc = self.xp.full((self.n_columns, n_layers), float(aerosol_mass_concentration))
        elif aerosol_mass_concentration.ndim == 1:
            if aerosol_mass_concentration.shape[0] == self.n_columns:
                n_layers = 1
                mc = aerosol_mass_concentration.reshape(-1, 1)
            else:
                n_layers = aerosol_mass_concentration.shape[0]
                mc = self.xp.broadcast_to(aerosol_mass_concentration, (self.n_columns, n_layers))
        else:
            n_layers = aerosol_mass_concentration.shape[1]
            mc = aerosol_mass_concentration

        if isinstance(aerosol_type, list) and len(aerosol_type) == self.n_columns and not isinstance(aerosol_type[0], list):
            aerosol_type_for_indices = [[at] for at in aerosol_type]
        else:
            aerosol_type_for_indices = aerosol_type

        ssa, g, ext_eff = self._aerosol_type_to_indices(aerosol_type_for_indices, n_layers)

        relative_humidity = self.xp.asarray(relative_humidity)
        if relative_humidity.ndim == 1:
            relative_humidity = relative_humidity.reshape(-1, 1)

        rh_factor = 1.0 + 0.01 * (relative_humidity / 100.0) ** 3
        mass_extinction = ext_eff * rh_factor

        aod = mass_extinction * mc * scale_height * 1e-3
        aod = self.xp.where(mc > 0, self.xp.maximum(0.0, aod), 0.0)

        if aod.shape[1] == 1:
            return aod[:, 0]
        return aod

    def calculate_single_scattering_albedo(self, aerosol_type='sulfate', n_layers=1):
        """
        计算单散射反照率 (SSA)，支持向量化
        """
        if isinstance(aerosol_type, list) and len(aerosol_type) == self.n_columns and not isinstance(aerosol_type[0], list):
            aerosol_type_for_indices = [[at] for at in aerosol_type]
        else:
            aerosol_type_for_indices = aerosol_type

        ssa, _, _ = self._aerosol_type_to_indices(aerosol_type_for_indices, n_layers)
        if ssa.shape[1] == 1:
            return ssa[:, 0]
        return ssa

    def calculate_asymmetry_parameter(self, aerosol_type='sulfate', n_layers=1):
        """
        计算不对称参数 (g)，支持向量化
        """
        if isinstance(aerosol_type, list) and len(aerosol_type) == self.n_columns and not isinstance(aerosol_type[0], list):
            aerosol_type_for_indices = [[at] for at in aerosol_type]
        else:
            aerosol_type_for_indices = aerosol_type

        _, g, _ = self._aerosol_type_to_indices(aerosol_type_for_indices, n_layers)
        if g.shape[1] == 1:
            return g[:, 0]
        return g

    def hg_phase_function_normalization(self, g, mu=None):
        """
        计算 Henyey-Greenstein 相函数的归一化因子
        """
        g = self.xp.asarray(g)

        if mu is None:
            normalization = self.xp.where(
                g == 0,
                1.0,
                (1 - g ** 2) / (2 * g) * self.xp.log((1 + g) / self.xp.maximum(0.001, 1 - g))
            )
            return normalization
        else:
            mu = self.xp.asarray(mu)
            phase_function = (1 - g ** 2) / (1 + g ** 2 - 2 * g * mu) ** (1.5)
            return phase_function

    def calculate_backscattering_ratio(self, g):
        """
        计算后向散射比率，支持向量化
        """
        g = self.xp.asarray(g)
        backscatter_fraction = 0.5 - 0.375 * g
        backscatter_fraction = self.xp.maximum(0.0, self.xp.minimum(0.5, backscatter_fraction))
        backscatter_fraction = self.xp.where(g >= 0.99, 0.0, backscatter_fraction)
        return backscatter_fraction

    def calculate_aerosol_forcing_efficiency(self, aerosol_type='sulfate', solar_zenith_angle=0.0, n_layers=1):
        """
        计算气溶胶辐射强迫效率
        """
        ssa, g, _ = self._aerosol_type_to_indices(aerosol_type, n_layers)

        cos_zenith = self.xp.maximum(0.01, self.xp.cos(self.xp.radians(solar_zenith_angle)))

        backscatter_ratio = self.calculate_backscattering_ratio(g)
        scattering_efficiency = ssa * backscatter_ratio
        absorption_efficiency = (1 - ssa)

        forcing_efficiency = self.xp.where(
            absorption_efficiency > scattering_efficiency,
            30.0 * absorption_efficiency / cos_zenith,
            -50.0 * scattering_efficiency / cos_zenith
        )

        return forcing_efficiency

    def calculate_direct_radiative_forcing(self, aod, aerosol_type='sulfate',
                                        solar_zenith_angle=0.0, surface_albedo=0.3):
        """
        计算气溶胶直接辐射强迫，支持向量化
        """
        aod = self.xp.asarray(aod)

        if aod.ndim <= 1:
            n_layers = 1
            if aod.ndim == 0:
                aod_2d = self.xp.full((self.n_columns, n_layers), float(aod))
            else:
                aod_2d = aod.reshape(-1, 1)
        else:
            n_layers = aod.shape[1]
            aod_2d = aod

        if isinstance(aerosol_type, list) and len(aerosol_type) == self.n_columns and not isinstance(aerosol_type[0], list):
            aerosol_type_for_indices = [[at] for at in aerosol_type]
        else:
            aerosol_type_for_indices = aerosol_type

        ssa, g, _ = self._aerosol_type_to_indices(aerosol_type_for_indices, n_layers)

        if ssa.shape[1] == 1 and ssa.shape[0] == self.n_columns:
            ssa = ssa[:, 0].reshape(-1, 1)
        if g.shape[1] == 1 and g.shape[0] == self.n_columns:
            g = g[:, 0].reshape(-1, 1)

        cos_zenith = self.xp.maximum(0.01, self.xp.cos(self.xp.radians(solar_zenith_angle)))

        transmission_factor = 1 - self.xp.exp(-aod_2d / cos_zenith)

        scattering_optical_depth = ssa * aod_2d
        absorption_optical_depth = (1 - ssa) * aod_2d

        backscatter_ratio = self.calculate_backscattering_ratio(g)
        if backscatter_ratio.ndim == 1:
            backscatter_ratio = backscatter_ratio.reshape(-1, 1)
        upscatter_fraction = backscatter_ratio

        normalized_scattering = 2 * upscatter_fraction * (1 - surface_albedo)
        normalized_absorption = 1 + surface_albedo

        scattering_effect = scattering_optical_depth * normalized_scattering / self.xp.maximum(aod_2d, 1e-10)
        absorption_effect = absorption_optical_depth * normalized_absorption / self.xp.maximum(aod_2d, 1e-10)

        total_effect = absorption_effect - scattering_effect

        SOLAR_CONSTANT = 1361.0
        forcing = -0.5 * SOLAR_CONSTANT * cos_zenith * transmission_factor * total_effect

        result = self.xp.where(aod_2d <= 0, 0.0, forcing)

        if result.shape[1] == 1:
            return result[:, 0]
        return result

    def calculate_indirect_radiative_forcing(self, aod, cloud_liquid_water=0.1,
                                         cloud_fraction=0.5, relative_humidity=60.0):
        """
        计算气溶胶间接辐射强迫，支持向量化
        """
        aod = self.xp.asarray(aod)
        cloud_liquid_water = self.xp.asarray(cloud_liquid_water)
        cloud_fraction = self.xp.asarray(cloud_fraction)
        relative_humidity = self.xp.asarray(relative_humidity)

        if aod.ndim <= 1:
            n_layers = 1
            if aod.ndim == 0:
                aod_2d = self.xp.full((self.n_columns, n_layers), float(aod))
            else:
                aod_2d = aod.reshape(-1, 1)
        else:
            n_layers = aod.shape[1]
            aod_2d = aod

        if cloud_liquid_water.ndim == 0:
            clw_2d = self.xp.full((self.n_columns, n_layers), float(cloud_liquid_water))
        elif cloud_liquid_water.ndim == 1:
            clw_2d = cloud_liquid_water.reshape(-1, 1)
        else:
            clw_2d = cloud_liquid_water

        if cloud_fraction.ndim == 0:
            cf_2d = self.xp.full((self.n_columns, n_layers), float(cloud_fraction))
        elif cloud_fraction.ndim == 1:
            cf_2d = cloud_fraction.reshape(-1, 1)
        else:
            cf_2d = cloud_fraction

        if relative_humidity.ndim == 0:
            rh_2d = self.xp.full((self.n_columns, n_layers), float(relative_humidity))
        elif relative_humidity.ndim == 1:
            rh_2d = relative_humidity.reshape(-1, 1)
        else:
            rh_2d = relative_humidity

        effective_radius_effect = self.xp.log(1 + 0.1 * aod_2d)
        lwp_effect = 1 + 0.05 * (rh_2d / 100.0) * aod_2d

        cloud_albedo_change = 0.1 * effective_radius_effect * lwp_effect

        base_cloud_albedo = 0.5
        new_cloud_albedo = self.xp.minimum(0.9, base_cloud_albedo + cloud_albedo_change * cf_2d)

        albedo_difference = new_cloud_albedo - base_cloud_albedo

        SOLAR_CONSTANT = 1361.0
        forcing = -0.5 * SOLAR_CONSTANT * albedo_difference * cf_2d

        result = self.xp.where(aod_2d <= 0, 0.0, forcing)

        if result.shape[1] == 1:
            return result[:, 0]
        return result

    def calculate_total_aerosol_forcing(self, aerosol_profile, solar_zenith_angle=0.0,
                                   surface_albedo=0.3, cloud_profile=None):
        """
        计算气溶胶总辐射强迫
        """
        mc = self.xp.asarray(aerosol_profile['mass_concentration'])

        if mc.ndim == 2:
            n_layers = mc.shape[1]
        elif mc.ndim == 1:
            n_layers = mc.shape[0]
        else:
            n_layers = 1

        direct_forcing = self.xp.zeros((self.n_columns, n_layers))
        indirect_forcing = self.xp.zeros((self.n_columns, n_layers))

        at = aerosol_profile['aerosol_type']
        rh = self.xp.asarray(aerosol_profile['relative_humidity'])

        if cloud_profile is not None:
            cf_profile = self.xp.asarray(cloud_profile['cloud_fraction'])
            clw_profile = self.xp.asarray(cloud_profile['water_content'])

        for i in range(n_layers):
            if mc.ndim == 2:
                concentration = mc[:, i]
            elif mc.ndim == 1:
                concentration = mc[i]
            else:
                concentration = mc

            if isinstance(at, list) and len(at) > 0:
                if isinstance(at[0], list) and i < len(at[0]):
                    aerosol_type = [col[i] for col in at]
                elif i < len(at):
                    aerosol_type = at[i]
                else:
                    aerosol_type = 'sulfate'
            else:
                aerosol_type = at

            if rh.ndim == 2:
                rel_hum = rh[:, i]
            elif rh.ndim == 1:
                rel_hum = rh[i]
            else:
                rel_hum = rh

            aod = self.calculate_aerosol_optical_depth(
                concentration, aerosol_type, rel_hum
            )

            direct = self.calculate_direct_radiative_forcing(
                aod, aerosol_type, solar_zenith_angle, surface_albedo
            )

            if direct.ndim == 2:
                direct_forcing[:, i] = direct[:, 0] if direct.shape[1] == 1 else direct[:, i]
            else:
                direct_forcing[:, i] = direct

            if cloud_profile is not None:
                if cf_profile.ndim == 2:
                    cf = cf_profile[:, i] if i < cf_profile.shape[1] else 0.0
                elif cf_profile.ndim == 1:
                    cf = cf_profile[i] if i < cf_profile.shape[0] else 0.0
                else:
                    cf = cf_profile

                if clw_profile.ndim == 2:
                    clw = clw_profile[:, i] if i < clw_profile.shape[1] else 0.0
                elif clw_profile.ndim == 1:
                    clw = clw_profile[i] if i < clw_profile.shape[0] else 0.0
                else:
                    clw = clw_profile

                indirect = self.calculate_indirect_radiative_forcing(
                    aod, clw, cf, rel_hum
                )
                if indirect.ndim == 2:
                    indirect_forcing[:, i] = indirect[:, 0] if indirect.shape[1] == 1 else indirect[:, i]
                else:
                    indirect_forcing[:, i] = indirect

        return {
            'direct_forcing': direct_forcing,
            'indirect_forcing': indirect_forcing,
            'total_forcing': direct_forcing + indirect_forcing
        }

    def apply_aerosol_effect_to_shortwave(self, sw_fluxes, aerosol_profile, solar_zenith_angle=0.0):
        """
        将气溶胶效应应用到短波辐射通量
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

        mc = self.xp.asarray(aerosol_profile['mass_concentration'])
        at = aerosol_profile['aerosol_type']
        rh = self.xp.asarray(aerosol_profile['relative_humidity'])

        if mc.ndim == 2:
            n_aero_levels = mc.shape[1]
        elif mc.ndim == 1:
            n_aero_levels = mc.shape[0]
        else:
            n_aero_levels = 1

        for i in range(n_levels - 1):
            if i < n_aero_levels:
                if mc.ndim == 2:
                    concentration = mc[:, i]
                elif mc.ndim == 1:
                    concentration = mc[i]
                else:
                    concentration = mc

                if isinstance(at, list) and len(at) > 0:
                    if isinstance(at[0], list) and i < len(at[0]):
                        aerosol_type = [col[i] for col in at]
                    elif i < len(at):
                        aerosol_type = at[i]
                    else:
                        aerosol_type = 'sulfate'
                else:
                    aerosol_type = at

                if rh.ndim == 2:
                    rel_hum = rh[:, i]
                elif rh.ndim == 1:
                    rel_hum = rh[i]
                else:
                    rel_hum = rh

                mask = concentration > 0

                if self.xp.any(mask):
                    aod = self.calculate_aerosol_optical_depth(
                        concentration, aerosol_type, rel_hum
                    )

                    ssa = self.calculate_single_scattering_albedo(aerosol_type, 1)
                    g = self.calculate_asymmetry_parameter(aerosol_type, 1)

                    if ssa.ndim == 2:
                        ssa = ssa[:, 0]
                    if g.ndim == 2:
                        g = g[:, 0]

                    cos_zenith = self.xp.maximum(0.01, self.xp.cos(self.xp.radians(solar_zenith_angle)))

                    backscatter_ratio = self.calculate_backscattering_ratio(g)

                    scattering_optical_depth = ssa * aod
                    absorption_optical_depth = (1 - ssa) * aod
                    extinction_optical_depth = scattering_optical_depth + absorption_optical_depth

                    transmission = self.xp.exp(-extinction_optical_depth / cos_zenith)

                    forward_scatter_fraction = 1 - backscatter_ratio
                    backward_scatter_fraction = backscatter_ratio

                    normalized_backward = backward_scatter_fraction * ssa

                    if use_bands:
                        n_bands = modified_fluxes['downward_flux'].shape[1]
                        for b in range(n_bands):
                            modified_fluxes['downward_flux'][:, b, i + 1] *= transmission

                            reflection_factor = normalized_backward * (1 - transmission) / self.xp.maximum(cos_zenith, 0.1)
                            reflection_factor = self.xp.minimum(reflection_factor, 0.5)
                            modified_fluxes['upward_flux'][:, b, i] *= (1 + reflection_factor)
                    else:
                        modified_fluxes['downward_flux'][:, i + 1] *= transmission

                        reflection_factor = normalized_backward * (1 - transmission) / self.xp.maximum(cos_zenith, 0.1)
                        reflection_factor = self.xp.minimum(reflection_factor, 0.5)
                        modified_fluxes['upward_flux'][:, i] *= (1 + reflection_factor)

        modified_fluxes['net_flux'] = modified_fluxes['downward_flux'] - modified_fluxes['upward_flux']

        return modified_fluxes

    def apply_aerosol_effect_to_longwave(self, lw_fluxes, aerosol_profile):
        """
        将气溶胶效应应用到长波辐射通量
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

        mc = self.xp.asarray(aerosol_profile['mass_concentration'])
        at = aerosol_profile['aerosol_type']
        temp = self.xp.asarray(aerosol_profile['temperature'])

        for i in range(n_levels):
            if i < len(aerosol_profile['mass_concentration']):
                concentration = mc[i] if mc.ndim == 1 else mc[:, i]
                aerosol_type = at[i] if isinstance(at, list) and i < len(at) else 'sulfate'

                mask = concentration > 0

                if self.xp.any(mask):
                    aod = self.calculate_aerosol_optical_depth(
                        concentration, aerosol_type
                    )

                    ssa = self.calculate_single_scattering_albedo(aerosol_type, 1)
                    if ssa.ndim == 2:
                        ssa = ssa[:, 0]

                    absorption_coefficient = aod * (1 - ssa)
                    emissivity = 1 - self.xp.exp(-absorption_coefficient)

                    temp_i = temp[i] if temp.ndim == 1 else temp[:, i]

                    aerosol_emission = emissivity * STEFAN_BOLTZMANN * temp_i ** 4

                    if use_bands:
                        n_bands = modified_fluxes['downward_flux'].shape[1]
                        for b in range(n_bands):
                            modified_fluxes['downward_flux'][:, b, i] += aerosol_emission * 0.1
                    else:
                        modified_fluxes['downward_flux'][:, i] += aerosol_emission * 0.1

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
