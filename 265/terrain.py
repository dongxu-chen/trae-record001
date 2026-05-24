import numpy as np
from scipy.interpolate import RegularGridInterpolator, interp1d
from scipy.ndimage import gaussian_filter

class StreamlineDeflection:
    def __init__(self, terrain, base_wind_direction=0.0):
        self.terrain = terrain
        self.base_wind_direction = base_wind_direction
        self._precompute_terrain_gradients()

    def _precompute_terrain_gradients(self):
        h = self.terrain.height_map
        dx = self.terrain.resolution
        dy = self.terrain.resolution

        self.dh_dx, self.dh_dy = np.gradient(h, dx, dy)

        self.slope_magnitude = np.sqrt(self.dh_dx ** 2 + self.dh_dy ** 2)

        self.aspect = np.arctan2(-self.dh_dy, -self.dh_dx)

        self._grad_interpolator_x = RegularGridInterpolator(
            (self.terrain.x_grid, self.terrain.y_grid),
            self.dh_dx,
            bounds_error=False,
            fill_value=0.0
        )
        self._grad_interpolator_y = RegularGridInterpolator(
            (self.terrain.x_grid, self.terrain.y_grid),
            self.dh_dy,
            bounds_error=False,
            fill_value=0.0
        )
        self._slope_interpolator = RegularGridInterpolator(
            (self.terrain.x_grid, self.terrain.y_grid),
            self.slope_magnitude,
            bounds_error=False,
            fill_value=0.0
        )
        self._aspect_interpolator = RegularGridInterpolator(
            (self.terrain.x_grid, self.terrain.y_grid),
            self.aspect,
            bounds_error=False,
            fill_value=0.0
        )

    def get_terrain_gradient(self, x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        points = np.column_stack([x.ravel(), y.ravel()])

        dh_dx = self._grad_interpolator_x(points).reshape(x.shape)
        dh_dy = self._grad_interpolator_y(points).reshape(x.shape)

        return dh_dx, dh_dy

    def get_slope(self, x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        points = np.column_stack([x.ravel(), y.ravel()])
        slope = self._slope_interpolator(points).reshape(x.shape)
        return slope

    def get_aspect(self, x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        points = np.column_stack([x.ravel(), y.ravel()])
        aspect = self._aspect_interpolator(points).reshape(x.shape)
        return aspect

    def calculate_wind_deflection(self, x, y, u, stability_class):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        dh_dx, dh_dy = self.get_terrain_gradient(x, y)
        slope = self.get_slope(x, y)

        wind_dir = self.base_wind_direction
        wind_vec = np.array([np.cos(wind_dir), np.sin(wind_dir)])

        slope_vec = np.array([dh_dx, dh_dy])
        slope_vec = np.where(slope > 0, slope_vec / (slope + 1e-10), 0)

        if stability_class in ['A', 'B', 'C']:
            deflection_strength = 0.8
        elif stability_class == 'D':
            deflection_strength = 0.5
        else:
            deflection_strength = 0.3

        max_deflection = np.pi / 6
        deflection_angle = deflection_strength * max_deflection * np.tanh(slope / 0.3)

        cross_wind_component = wind_vec[0] * slope_vec[1] - wind_vec[1] * slope_vec[0]
        deflection_direction = np.sign(cross_wind_component)

        total_deflection = deflection_direction * deflection_angle

        effective_wind_direction = wind_dir + total_deflection

        speed_factor = 1.0 - 0.3 * np.sin(np.minimum(slope, np.pi/4)) ** 2
        effective_speed = u * speed_factor

        return effective_wind_direction, effective_speed, total_deflection

    def trace_streamline(self, start_x, start_y, u, stability_class,
                          max_distance=10000, step_size=50):
        x = [start_x]
        y = [start_y]
        dist = [0.0]
        wind_dirs = [self.base_wind_direction]
        speeds = [u]
        deflections = [0.0]

        current_x = start_x
        current_y = start_y
        current_dist = 0.0

        while current_dist < max_distance:
            wind_dir, eff_speed, deflection = self.calculate_wind_deflection(
                current_x, current_y, u, stability_class
            )

            dx = eff_speed * np.cos(wind_dir) * step_size / u if u > 0 else np.cos(wind_dir) * step_size
            dy = eff_speed * np.sin(wind_dir) * step_size / u if u > 0 else np.sin(wind_dir) * step_size

            current_x += dx
            current_y += dy
            current_dist += np.sqrt(dx**2 + dy**2)

            x.append(current_x)
            y.append(current_y)
            dist.append(current_dist)
            wind_dirs.append(wind_dir)
            speeds.append(eff_speed)
            deflections.append(deflection)

        return {
            'x': np.array(x),
            'y': np.array(y),
            'distance': np.array(dist),
            'wind_direction': np.array(wind_dirs),
            'wind_speed': np.array(speeds),
            'deflection': np.array(deflections)
        }

    def get_deflected_coordinates(self, x, y, u, stability_class):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        orig_shape = x.shape
        x_flat = x.ravel()
        y_flat = y.ravel()

        x_deflected = np.zeros_like(x_flat)
        y_deflected = np.zeros_like(y_flat)
        wind_deflections = np.zeros_like(x_flat)
        eff_speeds = np.zeros_like(x_flat)

        for i in range(len(x_flat)):
            if x_flat[i] <= 0:
                x_deflected[i] = x_flat[i]
                y_deflected[i] = y_flat[i]
                wind_deflections[i] = 0.0
                eff_speeds[i] = u
                continue

            streamline = self.trace_streamline(
                0.0, y_flat[i], u, stability_class,
                max_distance=x_flat[i] + 100, step_size=20
            )

            if len(streamline['distance']) >= 2:
                f_x = interp1d(streamline['distance'], streamline['x'],
                              bounds_error=False, fill_value='extrapolate')
                f_y = interp1d(streamline['distance'], streamline['y'],
                              bounds_error=False, fill_value='extrapolate')
                f_deflect = interp1d(streamline['distance'], streamline['deflection'],
                                    bounds_error=False, fill_value='extrapolate')
                f_speed = interp1d(streamline['distance'], streamline['wind_speed'],
                                  bounds_error=False, fill_value='extrapolate')

                x_deflected[i] = float(f_x(x_flat[i]))
                y_deflected[i] = float(f_y(x_flat[i]))
                wind_deflections[i] = float(f_deflect(x_flat[i]))
                eff_speeds[i] = float(f_speed(x_flat[i]))
            else:
                x_deflected[i] = x_flat[i]
                y_deflected[i] = y_flat[i]
                wind_deflections[i] = 0.0
                eff_speeds[i] = u

        return {
            'x_deflected': x_deflected.reshape(orig_shape),
            'y_deflected': y_deflected.reshape(orig_shape),
            'wind_deflection': wind_deflections.reshape(orig_shape),
            'effective_speed': eff_speeds.reshape(orig_shape)
        }

    def calculate_streamline_deflection_factor(self, x, y, H_e, stability_class):
        h_t = self.terrain.get_height(x, y)
        h_diff = H_e - h_t

        slope = self.get_slope(x, y)

        if stability_class in ['A', 'B', 'C']:
            base_factor = 1.0
            terrain_effect = np.where(h_diff > 0, 1.0, np.exp(h_diff / 50.0))
        elif stability_class == 'D':
            base_factor = 1.0
            terrain_effect = np.where(h_diff > 0, 1.0, np.exp(h_diff / 30.0))
        else:
            base_factor = 1.0
            terrain_effect = np.where(h_diff > 0, 1.0, np.exp(h_diff / 20.0))

        flow_separation = np.where(slope > 0.5, 0.7 + 0.3 * np.exp(-(slope - 0.5) / 0.2), 1.0)

        total_factor = base_factor * terrain_effect * flow_separation

        return np.clip(total_factor, 0.1, 1.2), h_t, slope

class Terrain:
    def __init__(self, x_min=0, x_max=5000, y_min=-2000, y_max=2000, resolution=50):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.resolution = resolution
        self.x_grid = None
        self.y_grid = None
        self.height_map = None
        self._interpolator = None
        self._streamline_deflection = None
        self._build_flat_terrain()

    def _build_flat_terrain(self):
        nx = int((self.x_max - self.x_min) / self.resolution) + 1
        ny = int((self.y_max - self.y_min) / self.resolution) + 1
        self.x_grid = np.linspace(self.x_min, self.x_max, nx)
        self.y_grid = np.linspace(self.y_min, self.y_max, ny)
        X, Y = np.meshgrid(self.x_grid, self.y_grid, indexing='ij')
        self.height_map = np.zeros_like(X)
        self._update_interpolator()

    def _update_interpolator(self):
        self._interpolator = RegularGridInterpolator(
            (self.x_grid, self.y_grid),
            self.height_map,
            bounds_error=False,
            fill_value=0.0
        )
        self._streamline_deflection = None

    def get_streamline_deflection(self, base_wind_direction=0.0):
        if self._streamline_deflection is None or \
           self._streamline_deflection.base_wind_direction != base_wind_direction:
            self._streamline_deflection = StreamlineDeflection(self, base_wind_direction)
        return self._streamline_deflection

    def get_height(self, x, y):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        points = np.column_stack([x.ravel(), y.ravel()])
        heights = self._interpolator(points)
        return heights.reshape(x.shape)

    def add_hill(self, center_x, center_y, height, radius):
        X, Y = np.meshgrid(self.x_grid, self.y_grid, indexing='ij')
        dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        hill = height * np.exp(-(dist / radius) ** 2)
        self.height_map = np.maximum(self.height_map, hill)
        self._update_interpolator()

    def add_ridge(self, start_x, start_y, end_x, end_y, height, width):
        X, Y = np.meshgrid(self.x_grid, self.y_grid, indexing='ij')
        dx = end_x - start_x
        dy = end_y - start_y
        length = np.sqrt(dx ** 2 + dy ** 2)
        t = ((X - start_x) * dx + (Y - start_y) * dy)
        t = np.clip(t / (length ** 2), 0, 1)
        proj_x = start_x + t * dx
        proj_y = start_y + t * dy
        dist = np.sqrt((X - proj_x) ** 2 + (Y - proj_y) ** 2)
        ridge = height * np.exp(-(dist / width) ** 2)
        self.height_map = np.maximum(self.height_map, ridge)
        self._update_interpolator()

    def add_valley(self, center_x, center_y, depth, radius):
        X, Y = np.meshgrid(self.x_grid, self.y_grid, indexing='ij')
        dist = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
        valley = -depth * np.exp(-(dist / radius) ** 2)
        self.height_map = np.minimum(self.height_map, valley)
        self._update_interpolator()

    def smooth_terrain(self, sigma=1.0):
        self.height_map = gaussian_filter(self.height_map, sigma=sigma)
        self._update_interpolator()

    def apply_terrain_correction(self, x, y, z, stability_class, u=5.0,
                                 use_streamline_deflection=True):
        h_t = self.get_height(x, y)
        z_corrected = np.maximum(z, h_t + 1.0)

        if use_streamline_deflection:
            stream_deflect = self.get_streamline_deflection()
            deflect_result = stream_deflect.get_deflected_coordinates(x, y, u, stability_class)
            return z_corrected, h_t, deflect_result
        else:
            return z_corrected, h_t, None

    def calculate_terrain_factor(self, x, y, H_e, stability_class, u=5.0,
                                 use_streamline_deflection=True):
        if use_streamline_deflection:
            stream_deflect = self.get_streamline_deflection()
            terrain_factor, h_t, slope = stream_deflect.calculate_streamline_deflection_factor(
                x, y, H_e, stability_class
            )
            return terrain_factor, h_t, slope
        else:
            h_t = self.get_height(x, y)
            h_diff = H_e - h_t

            if stability_class in ['A', 'B', 'C']:
                terrain_factor = np.where(h_diff > 0, 1.0, np.exp(h_diff / 50.0))
            elif stability_class == 'D':
                terrain_factor = np.where(h_diff > 0, 1.0, np.exp(h_diff / 30.0))
            else:
                terrain_factor = np.where(h_diff > 0, 1.0, np.exp(h_diff / 20.0))

            return np.clip(terrain_factor, 0.1, 1.0), h_t, None

    def calculate_wind_deflection_field(self, u, stability_class):
        X, Y = np.meshgrid(self.x_grid, self.y_grid, indexing='ij')
        stream_deflect = self.get_streamline_deflection()
        wind_dir, eff_speed, deflection = stream_deflect.calculate_wind_deflection(
            X, Y, u, stability_class
        )
        return X, Y, wind_dir, eff_speed, deflection

    def plot_wind_deflection(self, u, stability_class, ax=None):
        import matplotlib.pyplot as plt

        X, Y, wind_dir, eff_speed, deflection = self.calculate_wind_deflection_field(
            u, stability_class
        )

        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))

        stride = max(1, len(self.x_grid) // 20)
        Q = ax.quiver(X[::stride, ::stride] / 1000, Y[::stride, ::stride] / 1000,
                      np.cos(wind_dir[::stride, ::stride]),
                      np.sin(wind_dir[::stride, ::stride]),
                      eff_speed[::stride, ::stride],
                      cmap='coolwarm', scale=30)
        plt.colorbar(Q, ax=ax, label='有效风速 (m/s)')

        contour = ax.contour(X / 1000, Y / 1000, self.height_map,
                            levels=10, colors='k', alpha=0.3, linewidths=0.5)
        ax.clabel(contour, inline=True, fontsize=8, fmt='%.0f')

        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_title(f'地形诱导风场偏转 (稳定度: {stability_class})')
        ax.grid(True, alpha=0.3)

        return ax

    def plot_terrain_profile(self, ax=None, use_3d=True):
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D

        X, Y = np.meshgrid(self.x_grid, self.y_grid, indexing='ij')

        if use_3d:
            if ax is None:
                fig = plt.figure(figsize=(10, 8))
                ax = fig.add_subplot(111, projection='3d')
            elif not hasattr(ax, 'plot_surface'):
                fig = ax.figure
                pos = ax.get_position()
                ax.remove()
                ax = fig.add_subplot(111, projection='3d')
                ax.set_position(pos)

            surf = ax.plot_surface(X / 1000, Y / 1000, self.height_map,
                                   cmap='terrain', alpha=0.8)
            ax.set_xlabel('X (km)')
            ax.set_ylabel('Y (km)')
            ax.set_zlabel('Height (m)')
            ax.set_title('Terrain Elevation')
            plt.colorbar(surf, ax=ax, label='Elevation (m)')
        else:
            if ax is None:
                fig, ax = plt.subplots(figsize=(10, 8))

            contour = ax.contourf(X / 1000, Y / 1000, self.height_map,
                                  levels=20, cmap='terrain')
            ax.set_xlabel('X (km)')
            ax.set_ylabel('Y (km)')
            ax.set_title('Terrain Elevation (m)')
            plt.colorbar(contour, ax=ax, label='Elevation (m)')
            ax.grid(True, alpha=0.3)

        return ax
