import numpy as np
from scipy.fft import fft2, ifft2, fftshift, ifftshift
from scipy.ndimage import map_coordinates, rotate, zoom, shift


class PhaseCorrelationRegistrator:
    def __init__(self):
        self.xp = np
        self.fft2 = fft2
        self.ifft2 = ifft2
        self.fftshift = fftshift
        self.ifftshift = ifftshift

    def estimate_translation(self, ref_img, target_img):
        ref = ref_img.astype(np.float32)
        target = target_img.astype(np.float32)
        
        rows, cols = ref.shape
        
        F_ref = self.fft2(ref)
        F_target = self.fft2(target)
        
        cross_power = np.conj(F_ref) * F_target
        cross_power /= (np.abs(cross_power) + 1e-12)
        
        correlation = np.abs(self.ifft2(cross_power))
        correlation = self.fftshift(correlation)
        
        peak = np.unravel_index(np.argmax(correlation), correlation.shape)
        y0, x0 = peak
        
        dy_sub, dx_sub = self._subpixel_parabolic_fit(correlation, y0, x0)
        
        dy = dy_sub - rows // 2
        dx = dx_sub - cols // 2
        
        return dx, dy, correlation

    def _subpixel_parabolic_fit(self, correlation, y0, x0):
        rows, cols = correlation.shape
        
        if (y0 <= 1 or y0 >= rows - 2 or x0 <= 1 or x0 >= cols - 2):
            return float(y0), float(x0)
        
        vy = np.array([
            correlation[y0-1, x0],
            correlation[y0, x0],
            correlation[y0+1, x0]
        ])
        vx = np.array([
            correlation[y0, x0-1],
            correlation[y0, x0],
            correlation[y0, x0+1]
        ])
        
        dy_sub = self._parabolic_max_1d(vy)
        dx_sub = self._parabolic_max_1d(vx)
        
        return float(y0 + dy_sub), float(x0 + dx_sub)

    def _parabolic_max_1d(self, v):
        a = v[0]
        b = v[1]
        c = v[2]
        
        denom = a - 2 * b + c
        if abs(denom) < 1e-10:
            return 0.0
        
        return (a - c) / (2 * denom)

    def _create_hanning_window(self, shape):
        rows, cols = shape
        win_y = np.hanning(rows)
        win_x = np.hanning(cols)
        window = np.outer(win_y, win_x)
        return window.astype(np.float32)

    def estimate_rotation_scale(self, ref_img, target_img):
        ref = ref_img.astype(np.float32)
        target = target_img.astype(np.float32)
        
        rows, cols = ref.shape
        window = self._create_hanning_window((rows, cols))
        
        ref_windowed = ref * window
        target_windowed = target * window
        
        F_ref = fft2(ref_windowed)
        F_target = fft2(target_windowed)
        
        magnitude_ref = np.log(np.abs(fftshift(F_ref)) + 1)
        magnitude_target = np.log(np.abs(fftshift(F_target)) + 1)
        
        lp_ref, scale_factor = self.log_polar_transform(magnitude_ref)
        lp_target, _ = self.log_polar_transform(magnitude_target)
        
        F_lp_ref = fft2(lp_ref)
        F_lp_target = fft2(lp_target)
        
        cross_power_lp = F_lp_ref * np.conj(F_lp_target)
        cross_power_lp /= (np.abs(cross_power_lp) + 1e-12)
        
        correlation_lp = np.abs(ifft2(cross_power_lp))
        correlation_lp = fftshift(correlation_lp)
        
        peak = np.unravel_index(np.argmax(correlation_lp), correlation_lp.shape)
        scale_idx, angle_idx = peak
        
        num_angles = lp_ref.shape[1]
        num_radii = lp_ref.shape[0]
        
        rotation_angle = (angle_idx - num_angles // 2) * (360.0 / num_angles)
        
        scale_offset = scale_idx - num_radii // 2
        scale_ratio = np.power(scale_factor, scale_offset)
        scale_ratio = np.clip(scale_ratio, 0.8, 1.25)
        
        candidates = [rotation_angle, rotation_angle + 180, rotation_angle - 180]
        best_angle = rotation_angle
        best_corr = -1
        
        for angle in candidates:
            angle = angle % 360
            if angle > 180:
                angle -= 360
            
            rotated = rotate(target, -angle, reshape=False, order=3, mode='constant', cval=0)
            
            F_r = fft2(ref * window)
            F_t = fft2(rotated * window)
            cross = F_r * np.conj(F_t)
            cross /= (np.abs(cross) + 1e-12)
            corr_val = np.max(np.abs(ifft2(cross)))
            
            if corr_val > best_corr:
                best_corr = corr_val
                best_angle = angle
        
        rotation_angle = self._refine_rotation(ref, target, best_angle, window)
        
        return rotation_angle, scale_ratio, correlation_lp

    def _refine_rotation(self, ref, target, init_angle, window, search_range=5.0, steps=101):
        angles = np.linspace(init_angle - search_range, init_angle + search_range, steps)
        best_angle = init_angle
        best_corr = -1
        
        for angle in angles:
            rotated = rotate(target, -angle, reshape=False, order=3, mode='constant', cval=0)
            
            F_r = fft2(ref * window)
            F_t = fft2(rotated * window)
            cross = F_r * np.conj(F_t)
            cross /= (np.abs(cross) + 1e-12)
            corr_val = np.max(np.abs(ifft2(cross)))
            
            if corr_val > best_corr:
                best_corr = corr_val
                best_angle = angle
        
        corr_vals = []
        fine_angles = np.linspace(best_angle - 0.5, best_angle + 0.5, 11)
        for angle in fine_angles:
            rotated = rotate(target, -angle, reshape=False, order=3, mode='constant', cval=0)
            F_r = fft2(ref * window)
            F_t = fft2(rotated * window)
            cross = F_r * np.conj(F_t)
            cross /= (np.abs(cross) + 1e-12)
            corr_val = np.max(np.abs(ifft2(cross)))
            corr_vals.append(corr_val)
        
        if len(corr_vals) >= 3:
            idx = np.argmax(corr_vals)
            if 0 < idx < len(corr_vals) - 1:
                sub_idx = self._parabolic_max_1d(
                    [corr_vals[idx-1], corr_vals[idx], corr_vals[idx+1]]
                )
                best_angle = fine_angles[idx] + sub_idx * (fine_angles[1] - fine_angles[0])
        
        return best_angle

    def log_polar_transform(self, img):
        rows, cols = img.shape
        center = (rows // 2, cols // 2)
        
        max_radius = min(center[0], center[1], rows - center[0], cols - center[1])
        max_radius = int(max_radius * 0.9)
        
        num_angles = 720
        num_radii = 256
        
        log_min = 0
        log_max = np.log(max_radius + 1)
        log_base = np.exp((log_max - log_min) / num_radii)
        radii = np.exp(np.linspace(log_min, log_max, num_radii)) - 1
        
        angles = np.linspace(0, 2 * np.pi, num_angles, endpoint=False)
        
        angle_grid, radius_grid = np.meshgrid(angles, radii)
        
        y = center[0] + radius_grid * np.sin(angle_grid)
        x = center[1] + radius_grid * np.cos(angle_grid)
        
        coords = np.vstack((y.ravel(), x.ravel()))
        log_polar = map_coordinates(img, coords, order=3, mode='constant', cval=0)
        log_polar = log_polar.reshape(num_radii, num_angles)
        
        return log_polar, log_base

    def register(self, ref_img, target_img):
        if len(ref_img.shape) == 3:
            ref_img = np.mean(ref_img, axis=2)
        if len(target_img.shape) == 3:
            target_img = np.mean(target_img, axis=2)
        
        ref_img = ref_img.astype(np.float32)
        target_img = target_img.astype(np.float32)
        
        rotation, scale, corr_lp = self.estimate_rotation_scale(ref_img, target_img)
        
        rotated_target = rotate(target_img, -rotation, reshape=False, order=3, mode='constant', cval=0)
        
        if scale != 1.0:
            scaled_target = self._rescale_image(rotated_target, 1.0 / scale, ref_img.shape)
        else:
            scaled_target = rotated_target
        
        dx, dy, correlation = self.estimate_translation(ref_img, scaled_target)
        
        transformed = self._apply_full_transform(target_img, dx, dy, rotation, scale, ref_img.shape)
        
        return {
            'translation': (dx, dy),
            'rotation': rotation,
            'scale': scale,
            'transformed': transformed,
            'correlation': correlation,
            'correlation_lp': corr_lp
        }

    def _rescale_image(self, img, scale_factor, target_shape):
        rows, cols = img.shape
        t_rows, t_cols = target_shape
        
        new_rows = int(rows * scale_factor)
        new_cols = int(cols * scale_factor)
        
        scaled = zoom(img, scale_factor, order=3, mode='constant', cval=0)
        
        result = np.zeros(target_shape, dtype=np.float32)
        
        y_start = max(0, (t_rows - new_rows) // 2)
        x_start = max(0, (t_cols - new_cols) // 2)
        y_end = min(t_rows, y_start + new_rows)
        x_end = min(t_cols, x_start + new_cols)
        
        src_y_start = max(0, (new_rows - t_rows) // 2)
        src_x_start = max(0, (new_cols - t_cols) // 2)
        src_y_end = src_y_start + (y_end - y_start)
        src_x_end = src_x_start + (x_end - x_start)
        
        result[y_start:y_end, x_start:x_end] = scaled[src_y_start:src_y_end, src_x_start:src_x_end]
        
        return result

    def _apply_full_transform(self, img, dx, dy, rotation, scale, output_shape):
        rows, cols = output_shape
        src_rows, src_cols = img.shape
        
        angle_rad = np.deg2rad(rotation)
        
        inv_scale = 1.0 / scale
        cos_theta = np.cos(angle_rad)
        sin_theta = np.sin(angle_rad)
        
        center_y = rows // 2
        center_x = cols // 2
        src_center_y = src_rows // 2
        src_center_x = src_cols // 2
        
        y_grid, x_grid = np.mgrid[0:rows, 0:cols]
        
        y_centered = y_grid - center_y - dy
        x_centered = x_grid - center_x - dx
        
        src_y = inv_scale * (cos_theta * y_centered + sin_theta * x_centered) + src_center_y
        src_x = inv_scale * (-sin_theta * y_centered + cos_theta * x_centered) + src_center_x
        
        coords = np.vstack((src_y.ravel(), src_x.ravel()))
        transformed = map_coordinates(img, coords, order=3, mode='constant', cval=0)
        transformed = transformed.reshape(rows, cols)
        
        return transformed
