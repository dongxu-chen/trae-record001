import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
from matplotlib import cm
import warnings

warnings.filterwarnings('ignore')

class Visualizer:
    def __init__(self, model, units='mg/m³'):
        self.model = model
        self.units = units
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = True
        import warnings
        warnings.filterwarnings('ignore', category=UserWarning)
        import matplotlib
        matplotlib.use('Agg')

    def plot_contour(self, grid_data, ax=None, levels=None, log_scale=True,
                     show_source=True, cmap='viridis', title=None):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))

        X = grid_data['X'] / 1000
        Y = grid_data['Y'] / 1000
        C = grid_data['C'].copy()

        C[C <= 0] = 1e-15

        if levels is None:
            if log_scale:
                C_max = np.nanmax(C)
                C_min = np.nanmax([np.nanmin(C[C > 0]), C_max / 1e6])
                levels = np.logspace(np.log10(C_min), np.log10(C_max), 15)
            else:
                levels = 15

        if log_scale:
            norm = LogNorm(vmin=levels[0], vmax=levels[-1])
            fmt = '%.1e'
        else:
            norm = Normalize(vmin=levels[0], vmax=levels[-1])
            fmt = '%.3f'

        contour = ax.contourf(X, Y, C, levels=levels, cmap=cmap, norm=norm, alpha=0.8)
        cbar = plt.colorbar(contour, ax=ax, label=f'浓度 ({self.units})', format=fmt)

        contour_lines = ax.contour(X, Y, C, levels=levels, colors='k', linewidths=0.5, alpha=0.5)
        ax.clabel(contour_lines, inline=True, fontsize=8, fmt=fmt)

        if show_source:
            ax.plot(0, 0, 'ro', markersize=10, label='排放源')
            ax.annotate('排放源', xy=(0, 0), xytext=(0.5, 0.5),
                       arrowprops=dict(facecolor='black', shrink=0.05))

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel('横风向距离 (km)')

        if title is None:
            title = f'污染物浓度分布 (稳定度: {self.model.stability_class}, 风速: {self.model.u} m/s)'
            if grid_data.get('smoothed', False):
                title += f' (自适应平滑: {grid_data.get("smooth_method", "adaptive_gaussian")})'
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax, cbar

    def plot_isopleth(self, target_concentration, x_range=(100, 10000), y_range=(-2000, 2000),
                      z=0, resolution=200, ax=None, **kwargs):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))

        isopleth_points, grid_data = self.model.calculate_isopleth(
            target_concentration, x_range, y_range, z, resolution, **kwargs
        )

        self.plot_contour(grid_data, ax=ax)

        if isopleth_points:
            x_vals = [p[0] / 1000 for p in isopleth_points]
            y_min_vals = [p[1] / 1000 for p in isopleth_points]
            y_max_vals = [p[2] / 1000 for p in isopleth_points]

            ax.plot(x_vals, y_min_vals, 'r-', linewidth=2, label=f'{target_concentration} {self.units} 等值线')
            ax.plot(x_vals, y_max_vals, 'r-', linewidth=2)
            ax.fill_between(x_vals, y_min_vals, y_max_vals, alpha=0.3, color='red')

        ax.legend()
        return ax, isopleth_points, grid_data

    def plot_smoothing_comparison(self, grid_data_original, grid_data_smoothed,
                                   x_range=(100, 10000), y_range=(-2000, 2000),
                                   ax=None):
        if ax is None:
            fig, ax = plt.subplots(1, 3, figsize=(18, 5))

        smoother = self.model.adaptive_smoother
        if smoother is None:
            from adaptive_smoothing import AdaptiveSmoother
            smoother = AdaptiveSmoother()

        smoother.plot_smoothing_comparison(
            grid_data_original['C_original'] if 'C_original' in grid_data_original else grid_data_original['C'],
            grid_data_smoothed['C'],
            ax=ax
        )

        return ax

    def plot_edge_detection(self, grid_data, ax=None):
        if ax is None:
            fig, ax = plt.subplots(1, 2, figsize=(14, 5))

        smoother = self.model.adaptive_smoother
        if smoother is None:
            from adaptive_smoothing import AdaptiveSmoother
            smoother = AdaptiveSmoother()

        C = grid_data['C_original'] if 'C_original' in grid_data else grid_data['C']
        smoother.plot_edge_detection(C, ax=ax)

        return ax

    def plot_centerline_profile(self, x_range=(100, 10000), z=0, ax=None,
                                Qh=0, v_s=0, d=0, T_s=293, T_a=293):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))

        max_result = self.model.calculate_max_concentration(
            x_range, y=0, z=z, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a
        )

        x = max_result['x_profile'] / 1000
        C = max_result['C_profile']

        ax.semilogy(x, C, 'b-', linewidth=2, label='中心线浓度')
        ax.axvline(max_result['max_x'] / 1000, color='r', linestyle='--',
                   label=f'最大浓度位置: {max_result["max_x"]:.0f} m')
        ax.axhline(max_result['max_C'], color='g', linestyle='--',
                   label=f'最大浓度: {max_result["max_C"]:.2e} {self.units}')

        ax.plot(max_result['max_x'] / 1000, max_result['max_C'], 'ro', markersize=8)

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel(f'浓度 ({self.units})')
        ax.set_title('中心线浓度分布')
        ax.legend()
        ax.grid(True, alpha=0.3, which='both')

        return ax, max_result

    def plot_crosswind_profile(self, x, y_range=(-2000, 2000), z=0, ax=None,
                               Qh=0, v_s=0, d=0, T_s=293, T_a=293, num_points=200):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))

        y = np.linspace(y_range[0], y_range[1], num_points)
        x_arr = np.full_like(y, x)
        z_arr = np.full_like(y, z)

        result = self.model.calculate_concentration(
            x_arr, y, z_arr, Qh, v_s, d, T_s, T_a
        )
        C = result[0]
        sigma_y = result[3]

        sigma_y_val = sigma_y[0] if hasattr(sigma_y, '__len__') else sigma_y

        ax.plot(y / 1000, C, 'b-', linewidth=2, label='横风向浓度')
        ax.axvline(-sigma_y_val / 1000, color='r', linestyle='--', alpha=0.5, label=f'±σ_y = {sigma_y_val:.0f} m')
        ax.axvline(sigma_y_val / 1000, color='r', linestyle='--', alpha=0.5)

        ax.fill_between(y / 1000, 0, C, alpha=0.3)

        ax.set_xlabel('横风向距离 (km)')
        ax.set_ylabel(f'浓度 ({self.units})')
        ax.set_title(f'下风向 {x} m 处横风向浓度分布')
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax, C, sigma_y_val

    def plot_vertical_profile(self, x, z_range=(0, 500), y=0, ax=None,
                              Qh=0, v_s=0, d=0, T_s=293, T_a=293, num_points=200):
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 10))

        z = np.linspace(z_range[0], z_range[1], num_points)
        x_arr = np.full_like(z, x)
        y_arr = np.full_like(z, y)

        result = self.model.calculate_concentration(
            x_arr, y_arr, z, Qh, v_s, d, T_s, T_a
        )
        C = result[0]
        H_e = result[1]
        sigma_z = result[4]

        H_e_val = H_e[0] if hasattr(H_e, '__len__') else H_e
        sigma_z_val = sigma_z[0] if hasattr(sigma_z, '__len__') else sigma_z

        ax.plot(C, z, 'b-', linewidth=2, label='垂直浓度')
        ax.axhline(H_e_val, color='r', linestyle='--', label=f'有效源高 H_e = {H_e_val:.1f} m')
        ax.axhline(H_e_val + sigma_z_val, color='g', linestyle='--', alpha=0.5, label=f'±σ_z = {sigma_z_val:.0f} m')
        ax.axhline(H_e_val - sigma_z_val, color='g', linestyle='--', alpha=0.5)

        ax.fill_betweenx(z, 0, C, alpha=0.3)

        ax.set_xlabel(f'浓度 ({self.units})')
        ax.set_ylabel('高度 (m)')
        ax.set_title(f'下风向 {x} m 处垂直浓度分布')
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax, C, H_e_val, sigma_z_val

    def plot_plume_rise_advanced(self, x_range=(10, 5000), ax=None,
                                  v_s=15, d=3, T_s=400, T_a=293, num_points=200,
                                  compare_with_standard=True):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))

        comparison = self.model.compare_plume_rise_models(
            x_range, v_s, d, T_s, T_a, num_points
        )
        x = comparison['x']

        ax.plot(x / 1000, comparison['delta_h_advanced'], 'b-', linewidth=2,
                label='高级抬升模型 Δh (含热源修正)')
        ax.plot(x / 1000, comparison['H_e_advanced'], 'r-', linewidth=2,
                label='高级模型有效源高 H_e')

        if compare_with_standard:
            ax.plot(x / 1000, comparison['delta_h_standard'], 'b--', linewidth=1.5, alpha=0.6,
                    label='标准抬升模型 Δh')
            ax.plot(x / 1000, comparison['H_e_standard'], 'r--', linewidth=1.5, alpha=0.6,
                    label='标准模型有效源高 H_e')

        ax.axhline(self.model.h_s, color='k', linestyle='--',
                   label=f'烟囱高度 h_s = {self.model.h_s} m')

        heat_source = comparison.get('heat_source')
        if heat_source is not None:
            params_text = f'T_s={T_s}K, T_a={T_a}K, v_s={v_s}m/s, d={d}m\n'
            params_text += f'β={heat_source.beta:.1f}K, F_b={heat_source.F_b:.2f}m⁴/s³, '
            params_text += f'Qh={heat_source.Qh/1000:.1f}kW'
            ax.text(0.02, 0.02, params_text, transform=ax.transAxes,
                   fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel('高度 (m)')
        ax.set_title('烟羽抬升曲线对比 (含热源修正)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        return ax, comparison

    def plot_heat_source_params(self, v_s=15, d=3, T_s=400, T_a=293, ax=None):
        params = self.model.get_heat_source_params(v_s, d, T_s, T_a)

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))

        labels = [
            '出口速度 v_s', '烟囱直径 d', '烟气温度 T_s', '环境温度 T_a',
            '温度差 β', '浮力通量 F_b', '热释放率 Qh',
            '动量通量 M', '弗劳德数 F_r', '理查德森数 R_i',
            '特征长度 l_m'
        ]
        values = [
            params['v_s'], params['d'], params['T_s'], params['T_a'],
            params['beta'], params['F_b'], params['Qh'] / 1000,
            params['M'], params['F_r'], params['R_i'],
            params['l_m'] if np.isfinite(params['l_m']) else 1e6
        ]
        units = ['m/s', 'm', 'K', 'K', 'K', 'm⁴/s³', 'kW', 'kg·m/s²', '-', '-', 'm']

        colors = plt.cm.viridis(np.linspace(0, 1, len(values)))
        bars = ax.bar(range(len(values)), [np.log10(v + 1e-10) if v > 0 else -10 for v in values], color=colors)

        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('log₁₀(参数值)')
        ax.set_title('热源模型参数')
        ax.grid(True, alpha=0.3, axis='y')

        for bar, val, unit in zip(bars, values, units):
            height = bar.get_height()
            if val < 1000:
                val_str = f'{val:.2f} {unit}'
            else:
                val_str = f'{val:.2e} {unit}'
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.05,
                    val_str, ha='center', va='bottom', fontsize=8, rotation=45)

        return ax, params

    def plot_streamline_deflection(self, start_y=0, u=5, stability_class='C',
                                   max_distance=5000, step_size=50, ax=None):
        if self.model.terrain is None:
            print("需要设置地形模型来绘制流线偏转")
            return None

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))

        stream_deflect = self.model.terrain.get_streamline_deflection()

        for y0 in [-1000, -500, 0, 500, 1000]:
            streamline = stream_deflect.trace_streamline(
                0.0, y0, u, stability_class, max_distance, step_size
            )
            ax.plot(streamline['x'] / 1000, streamline['y'] / 1000,
                   label=f'初始 y={y0} m', linewidth=1.5)

        terrain = self.model.terrain
        X, Y = np.meshgrid(terrain.x_grid, terrain.y_grid, indexing='ij')
        contour = ax.contour(X / 1000, Y / 1000, terrain.height_map,
                            levels=10, colors='k', alpha=0.3, linewidths=0.5)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%.0f')

        ax.plot(0, start_y / 1000, 'ro', markersize=10, label='排放源')

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel('横风向距离 (km)')
        ax.set_title(f'地形诱导流线偏转 (稳定度: {stability_class}, 风速: {u} m/s)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axis('equal')

        return ax

    def plot_wind_deflection_field(self, u=5, stability_class='C', ax=None):
        if self.model.terrain is None:
            print("需要设置地形模型来绘制风场偏转")
            return None

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))

        self.model.terrain.plot_wind_deflection(u, stability_class, ax=ax)

        return ax

    def plot_terrain_3d(self, ax=None):
        if self.model.terrain is None:
            print("需要设置地形模型来绘制3D地形")
            return None

        if ax is None:
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')

        self.model.terrain.plot_terrain_profile(ax=ax, use_3d=True)

        return ax

    def plot_plume_rise(self, x_range=(10, 5000), ax=None,
                        Qh=0, v_s=0, d=0, T_s=293, T_a=293, num_points=200):
        from plume_rise import calculate_combined_plume_rise

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))

        x = np.linspace(x_range[0], x_range[1], num_points)
        delta_h = calculate_combined_plume_rise(
            x, Qh, v_s, d, T_s, T_a, self.model.u, self.model.stability_class
        )
        H_e = self.model.h_s + delta_h

        ax.plot(x / 1000, delta_h, 'b-', linewidth=2, label='抬升高度 Δh')
        ax.plot(x / 1000, H_e, 'r-', linewidth=2, label='有效源高 H_e')
        ax.axhline(self.model.h_s, color='k', linestyle='--', label=f'烟囱高度 h_s = {self.model.h_s} m')

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel('高度 (m)')
        ax.set_title('烟羽抬升曲线')
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax, delta_h, H_e

    def plot_stability_comparison(self, x_range=(100, 10000), y=0, z=0,
                                   Qh=0, v_s=0, d=0, T_s=293, T_a=293,
                                   stability_classes=None, ax=None,
                                   use_advanced_plume_rise=True):
        from stability import STABILITY_CLASSES, STABILITY_DESCRIPTIONS

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))

        if stability_classes is None:
            stability_classes = STABILITY_CLASSES

        colors = cm.rainbow(np.linspace(0, 1, len(stability_classes)))

        for i, sc in enumerate(stability_classes):
            model_temp = self.model.__class__(
                Q=self.model.Q, u=self.model.u, stability_class=sc,
                h_s=self.model.h_s, terrain=self.model.terrain,
                use_advanced_plume_rise=use_advanced_plume_rise,
                use_streamline_deflection=self.model.use_streamline_deflection
            )
            result = model_temp.calculate_max_concentration(
                x_range, y=y, z=z, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a
            )
            ax.semilogy(result['x_profile'] / 1000, result['C_profile'],
                       color=colors[i], linewidth=2,
                       label=f'{sc} - {STABILITY_DESCRIPTIONS[sc]}')

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel(f'浓度 ({self.units})')
        ax.set_title('不同稳定度下的中心线浓度对比')
        ax.legend()
        ax.grid(True, alpha=0.3, which='both')

        return ax

    def plot_3d_concentration(self, grid_data, ax=None, log_scale=True):
        from mpl_toolkits.mplot3d import Axes3D

        if ax is None:
            fig = plt.figure(figsize=(12, 8))
            ax = fig.add_subplot(111, projection='3d')

        X = grid_data['X'] / 1000
        Y = grid_data['Y'] / 1000
        C = grid_data['C'].copy()
        C[C <= 0] = 1e-15

        if log_scale:
            C_plot = np.log10(C)
            label = f'log10(浓度) ({self.units})'
        else:
            C_plot = C
            label = f'浓度 ({self.units})'

        surf = ax.plot_surface(X, Y, C_plot, cmap='viridis', alpha=0.8,
                              rcount=50, ccount=50)

        ax.set_xlabel('下风向距离 (km)')
        ax.set_ylabel('横风向距离 (km)')
        ax.set_zlabel(label)
        ax.set_title('污染物浓度分布 3D 视图')

        plt.colorbar(surf, ax=ax, label=label, shrink=0.5)

        return ax

    def plot_geographic(self, grid_data, center_lon=116.4, center_lat=39.9, ax=None):
        try:
            import geopandas as gpd
            from shapely.geometry import Point, Polygon
            import pandas as pd
        except ImportError:
            print("需要安装 geopandas 和 shapely 来绘制地理坐标图")
            return None

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 10))

        X = grid_data['X']
        Y = grid_data['Y']
        C = grid_data['C']

        lon_per_m = 1 / (111320 * np.cos(np.radians(center_lat)))
        lat_per_m = 1 / 111320

        lons = center_lon + X * lon_per_m
        lats = center_lat + Y * lat_per_m

        source_point = Point(center_lon, center_lat)
        gdf_source = gpd.GeoDataFrame({'geometry': [source_point], 'type': ['排放源']}, crs='EPSG:4326')

        points = []
        concentrations = []
        for i in range(lons.shape[0]):
            for j in range(lons.shape[1]):
                points.append(Point(lons[i, j], lats[i, j]))
                concentrations.append(C[i, j])

        gdf_points = gpd.GeoDataFrame({
            'geometry': points,
            'concentration': concentrations
        }, crs='EPSG:4326')

        gdf_points.plot(column='concentration', cmap='viridis', alpha=0.6, ax=ax,
                        legend=True, legend_kwds={'label': f'浓度 ({self.units})'})
        gdf_source.plot(ax=ax, color='red', markersize=100, marker='*', label='排放源')

        ax.set_xlabel('经度 (°)')
        ax.set_ylabel('纬度 (°)')
        ax.set_title('污染物地理分布')
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_advanced_features(self, x_range=(100, 10000), y_range=(-2000, 2000),
                               Qh=0, v_s=15, d=3, T_s=400, T_a=293):
        fig = plt.figure(figsize=(18, 12))

        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        ax1 = fig.add_subplot(gs[0, 0])
        grid_data = self.model.calculate_concentration_grid(
            x_range, y_range, z=0, resolution=100,
            Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a,
            apply_smoothing=True
        )
        self.plot_contour(grid_data, ax=ax1)
        ax1.set_title('自适应平滑后的浓度分布')

        ax2 = fig.add_subplot(gs[0, 1])
        self.plot_edge_detection(grid_data, ax=ax2)
        ax2[0].set_title('边缘强度检测')
        ax2[1].set_title('平滑强度分布')

        ax3 = fig.add_subplot(gs[0, 2])
        self.plot_plume_rise_advanced(x_range=(10, x_range[1]), ax=ax3,
                                      v_s=v_s, d=d, T_s=T_s, T_a=T_a)
        ax3.set_title('高级烟羽抬升 (含热源修正)')

        ax4 = fig.add_subplot(gs[1, 0])
        self.plot_heat_source_params(v_s=v_s, d=d, T_s=T_s, T_a=T_a, ax=ax4)
        ax4.set_title('热源模型参数')

        if self.model.terrain is not None:
            ax5 = fig.add_subplot(gs[1, 1])
            self.plot_streamline_deflection(u=self.model.u,
                                           stability_class=self.model.stability_class,
                                           max_distance=x_range[1], ax=ax5)
            ax5.set_title('流线偏转轨迹')

            ax6 = fig.add_subplot(gs[1, 2])
            self.plot_wind_deflection_field(u=self.model.u,
                                           stability_class=self.model.stability_class,
                                           ax=ax6)
            ax6.set_title('风场偏转矢量图')
        else:
            ax5 = fig.add_subplot(gs[1, 1])
            self.plot_centerline_profile(x_range, ax=ax5,
                                        Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)
            ax6 = fig.add_subplot(gs[1, 2])
            self.plot_stability_comparison(x_range, ax=ax6,
                                          Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)

        ax7 = fig.add_subplot(gs[2, :])
        grid_data_no_smooth = self.model.calculate_concentration_grid(
            x_range, y_range, z=0, resolution=100,
            Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a,
            apply_smoothing=False
        )
        if grid_data.get('smoothing_metrics'):
            metrics = grid_data['smoothing_metrics']
            metrics_text = f'平滑效果评估:\n'
            metrics_text += f'  高梯度像素: {metrics["high_gradient_pixels"]} ({metrics["high_gradient_ratio"]*100:.1f}%)\n'
            metrics_text += f'  高梯度区MAE: {metrics["mae_high_gradient"]:.3e} {self.units}\n'
            metrics_text += f'  高梯度区相关系数: {metrics["correlation_high_gradient"]:.3f}\n'
            metrics_text += f'  总体MAE: {metrics["overall_mae"]:.3e} {self.units}\n'
            metrics_text += f'  总体RMSE: {metrics["overall_rmse"]:.3e} {self.units}'
            ax7.text(0.02, 0.5, metrics_text, transform=ax7.transAxes,
                    fontsize=11, family='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        ax7.set_title('自适应平滑效果评估指标')
        ax7.axis('off')

        return fig

    def plot_all(self, grid_data, x_range=(100, 10000), Qh=0, v_s=0, d=0, T_s=293, T_a=293):
        fig = plt.figure(figsize=(18, 12))

        ax1 = plt.subplot(2, 3, 1)
        self.plot_contour(grid_data, ax=ax1)

        ax2 = plt.subplot(2, 3, 2)
        self.plot_centerline_profile(x_range, ax=ax2, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)

        ax3 = plt.subplot(2, 3, 3)
        self.plot_crosswind_profile(x=1000, ax=ax3, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)

        ax4 = plt.subplot(2, 3, 4)
        self.plot_vertical_profile(x=1000, ax=ax4, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)

        ax5 = plt.subplot(2, 3, 5)
        self.plot_plume_rise(x_range=(10, 5000), ax=ax5, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)

        ax6 = plt.subplot(2, 3, 6)
        self.plot_stability_comparison(x_range, ax=ax6, Qh=Qh, v_s=v_s, d=d, T_s=T_s, T_a=T_a)

        plt.tight_layout()
        return fig
