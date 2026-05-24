import numpy as np
from stability import calculate_sigma_y, calculate_sigma_z, get_mixing_layer_height
from plume_rise import (
    calculate_effective_stack_height,
    calculate_effective_stack_height_advanced,
    HeatSourceModel
)
from adaptive_smoothing import AdaptiveSmoother

class GaussianPlumeModel:
    def __init__(self, Q, u, stability_class, h_s, terrain=None,
                 use_advanced_plume_rise=True,
                 use_streamline_deflection=True,
                 adaptive_smoother=None):
        self.Q = Q
        self.u = u
        self.stability_class = stability_class
        self.h_s = h_s
        self.terrain = terrain
        self.mixing_height = get_mixing_layer_height(stability_class)
        self.use_advanced_plume_rise = use_advanced_plume_rise
        self.use_streamline_deflection = use_streamline_deflection

        if adaptive_smoother is None:
            self.adaptive_smoother = AdaptiveSmoother(
                gradient_threshold=0.05,
                min_sigma=0.3,
                max_sigma=2.0,
                edge_detection_method='combined'
            )
        else:
            self.adaptive_smoother = adaptive_smoother

        self.heat_source = None

    def calculate_concentration(self, x, y, z, Qh=0, v_s=0, d=0, T_s=293, T_a=293):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        z = np.asarray(z, dtype=float)

        x_orig = x.copy()
        y_orig = y.copy()
        x = np.maximum(x, 1.0)

        if y_orig.ndim == 0 or y_orig.shape != x_orig.shape:
            y_orig = np.broadcast_to(y_orig, x_orig.shape).copy()
        if z.ndim == 0 or z.shape != x.shape:
            z = np.broadcast_to(z, x.shape).copy()

        if self.use_advanced_plume_rise and v_s > 0 and d > 0 and T_s > 0:
            H_e, delta_h, heat_source = calculate_effective_stack_height_advanced(
                x, self.h_s, v_s, d, T_s, T_a, self.u, self.stability_class
            )
            self.heat_source = heat_source
        else:
            H_e, delta_h = calculate_effective_stack_height(
                x, self.h_s, Qh, v_s, d, T_s, T_a, self.u, self.stability_class
            )

        if self.terrain is not None and self.use_streamline_deflection:
            stream_deflect = self.terrain.get_streamline_deflection()
            deflect_result = stream_deflect.get_deflected_coordinates(
                x_orig, y_orig, self.u, self.stability_class
            )
            x_deflected = deflect_result['x_deflected']
            y_deflected = deflect_result['y_deflected']
            effective_speed = deflect_result['effective_speed']
            wind_deflection = deflect_result['wind_deflection']

            x_for_calc = np.maximum(x_deflected, 1.0)
            y_for_calc = y_deflected
            u_for_calc = effective_speed
        else:
            x_for_calc = x
            y_for_calc = y if y.shape == x.shape else np.broadcast_to(y, x.shape).copy()
            u_for_calc = self.u
            wind_deflection = np.zeros_like(x)
            effective_speed = np.full_like(x, self.u)

        sigma_y = calculate_sigma_y(x_for_calc, self.stability_class)
        sigma_z = calculate_sigma_z(x_for_calc, self.stability_class)

        if self.terrain is not None:
            z_corrected, h_t, _ = self.terrain.apply_terrain_correction(
                x_for_calc, y_for_calc, z, self.stability_class, u=self.u,
                use_streamline_deflection=self.use_streamline_deflection
            )
            terrain_factor, h_t, slope = self.terrain.calculate_terrain_factor(
                x_for_calc, y_for_calc, H_e, self.stability_class, u=self.u,
                use_streamline_deflection=self.use_streamline_deflection
            )
            H_e_corrected = np.maximum(H_e, h_t + 2.0)
        else:
            z_corrected = z
            H_e_corrected = H_e
            terrain_factor = 1.0
            h_t = np.zeros_like(x)
            slope = np.zeros_like(x)

        sigma_y_corrected = sigma_y
        sigma_z_corrected = sigma_z
        if self.terrain is not None and self.use_streamline_deflection:
            slope_correction = 1.0 + 0.5 * np.tanh(slope / 0.3)
            sigma_y_corrected = sigma_y * slope_correction
            sigma_z_corrected = sigma_z * slope_correction

        term1 = 1 / (2 * np.pi * u_for_calc * sigma_y_corrected * sigma_z_corrected)

        exp1 = np.exp(-(y_for_calc ** 2) / (2 * sigma_y_corrected ** 2))

        exp2 = np.exp(-(z_corrected - H_e_corrected) ** 2 / (2 * sigma_z_corrected ** 2))
        exp3 = np.exp(-(z_corrected + H_e_corrected) ** 2 / (2 * sigma_z_corrected ** 2))

        n_reflections = 3
        for n in range(1, n_reflections + 1):
            exp2 += np.exp(-(z_corrected - H_e_corrected - 2 * n * self.mixing_height) ** 2 / (2 * sigma_z_corrected ** 2))
            exp2 += np.exp(-(z_corrected - H_e_corrected + 2 * n * self.mixing_height) ** 2 / (2 * sigma_z_corrected ** 2))
            exp3 += np.exp(-(z_corrected + H_e_corrected - 2 * n * self.mixing_height) ** 2 / (2 * sigma_z_corrected ** 2))
            exp3 += np.exp(-(z_corrected + H_e_corrected + 2 * n * self.mixing_height) ** 2 / (2 * sigma_z_corrected ** 2))

        C = self.Q * term1 * exp1 * (exp2 + exp3) * terrain_factor

        C = C * 1000.0

        C = np.where(x_orig < 1.0, 0.0, C)
        C = np.nan_to_num(C, nan=0.0, posinf=0.0, neginf=0.0)

        result = {
            'C': C,
            'H_e': H_e,
            'delta_h': delta_h,
            'sigma_y': sigma_y_corrected,
            'sigma_z': sigma_z_corrected,
            'sigma_y_original': sigma_y,
            'sigma_z_original': sigma_z,
            'terrain_factor': terrain_factor,
            'h_t': h_t,
            'slope': slope,
            'wind_deflection': wind_deflection,
            'effective_speed': effective_speed,
            'x_deflected': x_for_calc if self.terrain is not None and self.use_streamline_deflection else x_orig,
            'y_deflected': y_for_calc if self.terrain is not None and self.use_streamline_deflection else y_orig,
            'heat_source': self.heat_source
        }

        return C, H_e, delta_h, sigma_y_corrected, sigma_z_corrected, result

    def calculate_ground_level_concentration(self, x, y, Qh=0, v_s=0, d=0, T_s=293, T_a=293):
        result = self.calculate_concentration(x, y, 0, Qh, v_s, d, T_s, T_a)
        return result[0], result[1], result[2], result[3], result[4], result[5]

    def calculate_centerline_concentration(self, x, z=0, Qh=0, v_s=0, d=0, T_s=293, T_a=293):
        return self.calculate_concentration(x, 0, z, Qh, v_s, d, T_s, T_a)

    def calculate_concentration_grid(self, x_range, y_range, z=0, resolution=50,
                                      Qh=0, v_s=0, d=0, T_s=293, T_a=293,
                                      apply_smoothing=True, smooth_method='adaptive_gaussian',
                                      interpolation_factor=1, use_log_for_smooth=True):
        x_min, x_max = x_range
        y_min, y_max = y_range

        x = np.linspace(x_min, x_max, resolution)
        y = np.linspace(y_min, y_max, resolution)
        X, Y = np.meshgrid(x, y, indexing='ij')

        C, H_e, delta_h, sigma_y, sigma_z, extra = self.calculate_ground_level_concentration(
            X, Y, Qh, v_s, d, T_s, T_a
        )

        grid_data = {
            'X': X,
            'Y': Y,
            'C': C,
            'H_e': H_e,
            'delta_h': delta_h,
            'sigma_y': sigma_y,
            'sigma_z': sigma_z,
            'x': x,
            'y': y,
            'extra': extra,
            'smoothed': False
        }

        if apply_smoothing and self.adaptive_smoother is not None:
            grid_data = self.adaptive_smoother.process_concentration_grid(
                grid_data, use_log=use_log_for_smooth,
                interpolation_factor=interpolation_factor,
                smooth_method=smooth_method
            )
            grid_data['smoothed'] = True
            grid_data['smooth_method'] = smooth_method

        return grid_data

    def calculate_max_concentration(self, x_range=(100, 10000), y=0, z=0,
                                    Qh=0, v_s=0, d=0, T_s=293, T_a=293, num_points=1000):
        x = np.linspace(x_range[0], x_range[1], num_points)
        C, H_e, delta_h, sigma_y, sigma_z, extra = self.calculate_concentration(
            x, y, z, Qh, v_s, d, T_s, T_a
        )

        max_idx = np.argmax(C)
        return {
            'max_C': C[max_idx],
            'max_x': x[max_idx],
            'max_y': y,
            'max_z': z,
            'C_profile': C,
            'x_profile': x,
            'H_e_at_max': H_e[max_idx] if hasattr(H_e, '__len__') else H_e,
            'sigma_y_at_max': sigma_y[max_idx] if hasattr(sigma_y, '__len__') else sigma_y,
            'sigma_z_at_max': sigma_z[max_idx] if hasattr(sigma_z, '__len__') else sigma_z,
            'extra_at_max': {k: v[max_idx] if hasattr(v, '__len__') else v
                            for k, v in extra.items() if v is not None and isinstance(v, np.ndarray)}
        }

    def calculate_isopleth(self, target_concentration, x_range=(100, 10000), y_range=(-2000, 2000),
                           z=0, resolution=200, Qh=0, v_s=0, d=0, T_s=293, T_a=293,
                           smooth_isopleth=True, smooth_method='savgol',
                           smooth_window=5, smooth_polyorder=2,
                           apply_grid_smoothing=True):
        grid_data = self.calculate_concentration_grid(
            x_range, y_range, z, resolution, Qh, v_s, d, T_s, T_a,
            apply_smoothing=apply_grid_smoothing
        )

        from scipy.interpolate import interp1d

        X, Y = grid_data['X'], grid_data['Y']
        C = grid_data['C']

        isopleth_points = []
        for i, xi in enumerate(grid_data['x']):
            if xi < 10:
                continue
            c_row = C[i, :]
            y_vals = grid_data['y']

            above = c_row >= target_concentration
            if np.any(above):
                y_above = y_vals[above]
                if len(y_above) >= 2:
                    y_min = y_above[0]
                    y_max = y_above[-1]
                    isopleth_points.append((xi, y_min, y_max))

        if smooth_isopleth and len(isopleth_points) >= 3 and self.adaptive_smoother is not None:
            isopleth_points = self.adaptive_smoother.smooth_isopleth_points(
                isopleth_points, smoothing_method=smooth_method,
                window_length=smooth_window, poly_order=smooth_polyorder
            )

        return isopleth_points, grid_data

    def calculate_footprint_area(self, target_concentration, x_range=(100, 10000),
                                 y_range=(-2000, 2000), z=0, resolution=200,
                                 Qh=0, v_s=0, d=0, T_s=293, T_a=293,
                                 apply_smoothing=True):
        grid_data = self.calculate_concentration_grid(
            x_range, y_range, z, resolution, Qh, v_s, d, T_s, T_a,
            apply_smoothing=apply_smoothing
        )

        C = grid_data['C']
        dx = (x_range[1] - x_range[0]) / (len(grid_data['x']) - 1)
        dy = (y_range[1] - y_range[0]) / (len(grid_data['y']) - 1)

        area = np.sum(C >= target_concentration) * dx * dy
        return area, grid_data

    def compare_plume_rise_models(self, x_range=(10, 5000), v_s=15, d=3, T_s=400, T_a=293, num_points=100):
        x = np.linspace(x_range[0], x_range[1], num_points)

        H_e_adv, delta_h_adv, heat_source = calculate_effective_stack_height_advanced(
            x, self.h_s, v_s, d, T_s, T_a, self.u, self.stability_class
        )

        Qh = heat_source.Qh if heat_source is not None else 0
        H_e_std, delta_h_std = calculate_effective_stack_height(
            x, self.h_s, Qh, v_s, d, T_s, T_a, self.u, self.stability_class
        )

        return {
            'x': x,
            'H_e_advanced': H_e_adv,
            'delta_h_advanced': delta_h_adv,
            'H_e_standard': H_e_std,
            'delta_h_standard': delta_h_std,
            'heat_source': heat_source
        }

    def get_heat_source_params(self, v_s=15, d=3, T_s=400, T_a=293):
        if self.heat_source is None or \
           self.heat_source.v_s != v_s or \
           self.heat_source.d != d or \
           self.heat_source.T_s != T_s or \
           self.heat_source.T_a != T_a:
            self.heat_source = HeatSourceModel(v_s, d, T_s, T_a)

        params = {
            'v_s': self.heat_source.v_s,
            'd': self.heat_source.d,
            'T_s': self.heat_source.T_s,
            'T_a': self.heat_source.T_a,
            'rho_s': self.heat_source.rho_s,
            'rho_a': self.heat_source.rho_a,
            'beta': self.heat_source.beta,
            'w_star': self.heat_source.w_star,
            'F_b': self.heat_source.F_b,
            'Qh': self.heat_source.Qh,
            'M': self.heat_source.M,
            'F_r': self.heat_source.F_r,
            'R_i': self.heat_source.R_i,
            'l_m': self.heat_source.l_m
        }
        return params
