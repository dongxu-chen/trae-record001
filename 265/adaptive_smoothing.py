import numpy as np
from scipy.ndimage import gaussian_filter, convolve
from scipy.interpolate import RectBivariateSpline, RegularGridInterpolator
from scipy.signal import savgol_filter

class AdaptiveSmoother:
    def __init__(self, gradient_threshold=0.1, min_sigma=0.5, max_sigma=3.0,
                 edge_detection_method='gradient'):
        self.gradient_threshold = gradient_threshold
        self.min_sigma = min_sigma
        self.max_sigma = max_sigma
        self.edge_detection_method = edge_detection_method

    def calculate_gradient_magnitude(self, data):
        data = np.asarray(data, dtype=float)
        grad_y, grad_x = np.gradient(data)
        gradient_magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)

        data_max = np.nanmax(np.abs(data))
        if data_max > 0:
            gradient_magnitude_normalized = gradient_magnitude / data_max
        else:
            gradient_magnitude_normalized = np.zeros_like(gradient_magnitude)

        return gradient_magnitude_normalized, grad_x, grad_y

    def calculate_curvature(self, data):
        data = np.asarray(data, dtype=float)
        grad_y, grad_x = np.gradient(data)
        grad_yy, grad_yx = np.gradient(grad_y)
        grad_xy, grad_xx = np.gradient(grad_x)

        curvature = np.abs(grad_xx) + np.abs(grad_yy) + np.abs(grad_xy) + np.abs(grad_yx)

        data_max = np.nanmax(np.abs(data))
        if data_max > 0:
            curvature_normalized = curvature / (data_max + 1e-10)
        else:
            curvature_normalized = np.zeros_like(curvature)

        return curvature_normalized

    def detect_edges(self, data, method=None):
        if method is None:
            method = self.edge_detection_method

        if method == 'gradient':
            edge_strength, _, _ = self.calculate_gradient_magnitude(data)
        elif method == 'curvature':
            edge_strength = self.calculate_curvature(data)
        elif method == 'combined':
            grad, _, _ = self.calculate_gradient_magnitude(data)
            curv = self.calculate_curvature(data)
            edge_strength = 0.5 * grad + 0.5 * curv
        elif method == 'sobel':
            edge_strength = self._sobel_edge_detection(data)
        else:
            raise ValueError(f"Unknown edge detection method: {method}")

        return edge_strength

    def _sobel_edge_detection(self, data):
        data = np.asarray(data, dtype=float)

        sobel_x = np.array([[-1, 0, 1],
                           [-2, 0, 2],
                           [-1, 0, 1]])
        sobel_y = np.array([[-1, -2, -1],
                           [0, 0, 0],
                           [1, 2, 1]])

        grad_x = convolve(data, sobel_x, mode='reflect')
        grad_y = convolve(data, sobel_y, mode='reflect')

        edge_strength = np.sqrt(grad_x ** 2 + grad_y ** 2)

        data_max = np.nanmax(np.abs(data))
        if data_max > 0:
            edge_strength = edge_strength / (data_max * 8 + 1e-10)

        return np.clip(edge_strength, 0, 1)

    def calculate_sigma_field(self, data, edge_strength=None):
        if edge_strength is None:
            edge_strength = self.detect_edges(data)

        sigma_field = self.max_sigma - (self.max_sigma - self.min_sigma) * \
                      np.tanh(edge_strength / self.gradient_threshold)

        return sigma_field

    def adaptive_gaussian_smooth(self, data, log_transform=False):
        data = np.asarray(data, dtype=float)
        original_data = data.copy()

        if log_transform:
            data_log = np.log10(np.maximum(data, 1e-15))
            data_smoothed = self._adaptive_smooth_2d(data_log)
            data_smoothed = 10 ** data_smoothed
        else:
            data_smoothed = self._adaptive_smooth_2d(data)

        data_smoothed = np.maximum(data_smoothed, 0)

        return data_smoothed

    def _adaptive_smooth_2d(self, data):
        data = np.asarray(data, dtype=float)
        smoothed = np.zeros_like(data)

        edge_strength = self.detect_edges(data)
        sigma_field = self.calculate_sigma_field(data, edge_strength)

        sigma_levels = np.linspace(self.min_sigma, self.max_sigma, 5)

        smoothed_versions = []
        for sigma in sigma_levels:
            smoothed_versions.append(gaussian_filter(data, sigma=sigma, mode='reflect'))

        for i, sigma in enumerate(sigma_levels[:-1]):
            sigma_low = sigma
            sigma_high = sigma_levels[i + 1]

            mask = (sigma_field >= sigma_low) & (sigma_field < sigma_high)

            if np.any(mask):
                alpha = (sigma_field[mask] - sigma_low) / (sigma_high - sigma_low)
                smoothed[mask] = (1 - alpha) * smoothed_versions[i][mask] + \
                                alpha * smoothed_versions[i + 1][mask]

        mask_high = sigma_field >= sigma_levels[-1]
        if np.any(mask_high):
            smoothed[mask_high] = smoothed_versions[-1][mask_high]

        mask_low = sigma_field < sigma_levels[0]
        if np.any(mask_low):
            smoothed[mask_low] = smoothed_versions[0][mask_low]

        return smoothed

    def adaptive_savgol_smooth(self, data, window_size_range=(3, 11), poly_order=2):
        data = np.asarray(data, dtype=float)
        smoothed = np.zeros_like(data)

        edge_strength = self.detect_edges(data)

        min_window, max_window = window_size_range
        window_sizes = np.arange(min_window, max_window + 2, 2)

        window_field = min_window + (max_window - min_window) * \
                       (1 - np.tanh(edge_strength / self.gradient_threshold))
        window_field = np.round(window_field).astype(int)
        window_field = np.where(window_field % 2 == 0, window_field + 1, window_field)
        window_field = np.clip(window_field, min_window, max_window)

        for w in window_sizes:
            mask = window_field == w
            if np.any(mask):
                for i in range(data.shape[0]):
                    row_mask = mask[i, :]
                    if np.any(row_mask):
                        try:
                            smoothed_row = savgol_filter(data[i, :], window_length=w,
                                                        polyorder=poly_order, mode='mirror')
                            smoothed[i, row_mask] = smoothed_row[row_mask]
                        except:
                            smoothed[i, row_mask] = data[i, row_mask]

                for j in range(data.shape[1]):
                    col_mask = mask[:, j]
                    if np.any(col_mask):
                        try:
                            smoothed_col = savgol_filter(data[:, j], window_length=w,
                                                        polyorder=poly_order, mode='mirror')
                            smoothed[col_mask, j] = 0.5 * smoothed[col_mask, j] + \
                                                    0.5 * smoothed_col[col_mask]
                        except:
                            pass

        return smoothed

    def bicubic_interpolate(self, X, Y, C, new_resolution_factor=2):
        x = X[:, 0]
        y = Y[0, :]

        nx_new = len(x) * new_resolution_factor
        ny_new = len(y) * new_resolution_factor

        x_new = np.linspace(x[0], x[-1], nx_new)
        y_new = np.linspace(y[0], y[-1], ny_new)
        X_new, Y_new = np.meshgrid(x_new, y_new, indexing='ij')

        spline = RectBivariateSpline(x, y, C, kx=3, ky=3)
        C_new = spline(x_new, y_new)

        return X_new, Y_new, C_new

    def smooth_isopleth_points(self, isopleth_points, smoothing_method='savgol',
                               window_length=5, poly_order=2):
        if len(isopleth_points) < 3:
            return isopleth_points

        x = np.array([p[0] for p in isopleth_points])
        y_min = np.array([p[1] for p in isopleth_points])
        y_max = np.array([p[2] for p in isopleth_points])

        if smoothing_method == 'savgol':
            y_min_smoothed = savgol_filter(y_min, window_length=window_length,
                                          polyorder=poly_order, mode='interp')
            y_max_smoothed = savgol_filter(y_max, window_length=window_length,
                                          polyorder=poly_order, mode='interp')
        elif smoothing_method == 'gaussian':
            sigma = window_length / 4.0
            y_min_smoothed = gaussian_filter(y_min, sigma=sigma)
            y_max_smoothed = gaussian_filter(y_max, sigma=sigma)
        elif smoothing_method == 'moving_average':
            kernel = np.ones(window_length) / window_length
            y_min_smoothed = np.convolve(y_min, kernel, mode='same')
            y_max_smoothed = np.convolve(y_max, kernel, mode='same')
        else:
            raise ValueError(f"Unknown smoothing method: {smoothing_method}")

        smoothed_points = []
        for i in range(len(x)):
            smoothed_points.append((x[i], y_min_smoothed[i], y_max_smoothed[i]))

        return smoothed_points

    def calculate_detail_preservation_metric(self, original_data, smoothed_data):
        original_edges = self.detect_edges(original_data)
        smoothed_edges = self.detect_edges(smoothed_data)

        high_gradient_mask = original_edges > self.gradient_threshold

        if np.any(high_gradient_mask):
            mae_high_gradient = np.mean(np.abs(
                original_data[high_gradient_mask] - smoothed_data[high_gradient_mask]
            ))
            correlation_high_gradient = np.corrcoef(
                original_data[high_gradient_mask].ravel(),
                smoothed_data[high_gradient_mask].ravel()
            )[0, 1]
        else:
            mae_high_gradient = 0.0
            correlation_high_gradient = 1.0

        overall_mae = np.mean(np.abs(original_data - smoothed_data))
        overall_rmse = np.sqrt(np.mean((original_data - smoothed_data) ** 2))

        return {
            'mae_high_gradient': mae_high_gradient,
            'correlation_high_gradient': correlation_high_gradient,
            'overall_mae': overall_mae,
            'overall_rmse': overall_rmse,
            'high_gradient_pixels': np.sum(high_gradient_mask),
            'high_gradient_ratio': np.mean(high_gradient_mask)
        }

    def process_concentration_grid(self, grid_data, use_log=True,
                                  interpolation_factor=1, smooth_method='adaptive_gaussian'):
        X = grid_data['X']
        Y = grid_data['Y']
        C = grid_data['C'].copy()

        if interpolation_factor > 1:
            X, Y, C = self.bicubic_interpolate(X, Y, C, interpolation_factor)

        if smooth_method == 'adaptive_gaussian':
            C_smoothed = self.adaptive_gaussian_smooth(C, log_transform=use_log)
        elif smooth_method == 'adaptive_savgol':
            C_smoothed = self.adaptive_savgol_smooth(C)
        elif smooth_method == 'gaussian':
            sigma = (self.min_sigma + self.max_sigma) / 2
            if use_log:
                C_log = np.log10(np.maximum(C, 1e-15))
                C_smoothed = 10 ** gaussian_filter(C_log, sigma=sigma)
            else:
                C_smoothed = gaussian_filter(C, sigma=sigma)
        elif smooth_method == 'none':
            C_smoothed = C
        else:
            raise ValueError(f"Unknown smoothing method: {smooth_method}")

        metrics = self.calculate_detail_preservation_metric(C, C_smoothed)

        result = grid_data.copy()
        result['X'] = X
        result['Y'] = Y
        result['C'] = C_smoothed
        result['C_original'] = C
        result['smoothing_metrics'] = metrics

        if interpolation_factor > 1:
            result['x'] = X[:, 0]
            result['y'] = Y[0, :]

        if smooth_method != 'none':
            result['smoothed'] = True
            result['smooth_method'] = smooth_method
        else:
            result['smoothed'] = False
            result['smooth_method'] = 'none'

        return result

    def plot_edge_detection(self, data, ax=None):
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(1, 2, figsize=(14, 5))

        edge_strength = self.detect_edges(data)
        sigma_field = self.calculate_sigma_field(data, edge_strength)

        im1 = ax[0].imshow(edge_strength.T, origin='lower', cmap='hot', aspect='auto')
        ax[0].set_title('Edge Strength')
        plt.colorbar(im1, ax=ax[0], label='Normalized Gradient')

        im2 = ax[1].imshow(sigma_field.T, origin='lower', cmap='coolwarm', aspect='auto')
        ax[1].set_title('Smoothing Sigma Field')
        plt.colorbar(im2, ax=ax[1], label='Sigma')

        return ax

    def plot_smoothing_comparison(self, original, smoothed, ax=None):
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(1, 3, figsize=(18, 5))

        edge_strength = self.detect_edges(original)

        vmin = np.nanmin(original[original > 0])
        vmax = np.nanmax(original)

        im1 = ax[0].imshow(original.T, origin='lower', cmap='viridis',
                          aspect='auto', norm=LogNorm(vmin=vmin, vmax=vmax))
        ax[0].set_title('Original Data')
        plt.colorbar(im1, ax=ax[0], label='Concentration')

        im2 = ax[1].imshow(smoothed.T, origin='lower', cmap='viridis',
                          aspect='auto', norm=LogNorm(vmin=vmin, vmax=vmax))
        ax[1].set_title('Smoothed Data')
        plt.colorbar(im2, ax=ax[1], label='Concentration')

        diff = np.abs(original - smoothed) / (original + 1e-10) * 100
        im3 = ax[2].imshow(diff.T, origin='lower', cmap='RdYlBu_r',
                          aspect='auto', vmin=0, vmax=20)
        ax[2].set_title('Relative Difference (%)')
        plt.colorbar(im3, ax=ax[2], label='Difference (%)')

        high_grad_mask = edge_strength > self.gradient_threshold
        if np.any(high_grad_mask):
            y_idx, x_idx = np.where(high_grad_mask.T)
            ax[2].plot(x_idx, y_idx, 'k.', markersize=1, alpha=0.5, label='High Gradient')
            ax[2].legend()

        return ax
