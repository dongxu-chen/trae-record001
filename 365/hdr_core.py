import numpy as np
import cv2
from typing import List, Tuple, Optional, Dict
from collections import deque


class ImageAligner:
    def __init__(self, max_features: int = 5000, good_match_ratio: float = 0.75,
                 ransac_threshold: float = 5.0):
        self.max_features = max_features
        self.good_match_ratio = good_match_ratio
        self.ransac_threshold = ransac_threshold
        self.sift = cv2.SIFT_create(nfeatures=max_features)
        self.flann = cv2.FlannBasedMatcher(
            dict(algorithm=1, trees=5),
            dict(checks=50)
        )

    def align_images(self, images: List[np.ndarray],
                     reference_idx: int = 0) -> List[np.ndarray]:
        if len(images) <= 1:
            return images

        ref_img = images[reference_idx]
        ref_gray = self._to_gray(ref_img)
        ref_kp, ref_des = self.sift.detectAndCompute(ref_gray, None)

        aligned = [None] * len(images)
        aligned[reference_idx] = ref_img.copy()

        h, w = ref_img.shape[:2]

        for i, img in enumerate(images):
            if i == reference_idx:
                continue

            img_gray = self._to_gray(img)
            kp, des = self.sift.detectAndCompute(img_gray, None)

            if des is None or len(kp) < 4:
                aligned[i] = img.copy()
                continue

            raw_matches = self.flann.knnMatch(des, ref_des, k=2)

            good_matches = []
            for m, n in raw_matches:
                if m.distance < self.good_match_ratio * n.distance:
                    good_matches.append(m)

            if len(good_matches) < 4:
                aligned[i] = img.copy()
                continue

            src_pts = np.float32([kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([ref_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,
                                          self.ransac_threshold)

            if H is None:
                aligned[i] = img.copy()
                continue

            inlier_ratio = np.sum(mask) / len(mask) if mask is not None else 0
            if inlier_ratio < 0.3:
                aligned[i] = img.copy()
                continue

            aligned[i] = cv2.warpPerspective(img, H, (w, h),
                                             flags=cv2.INTER_LINEAR,
                                             borderMode=cv2.BORDER_REPLICATE)

        return aligned

    def _to_gray(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img


class CameraResponseCalculator:
    def __init__(self, num_samples: int = 100, smoothness: float = 100.0,
                 regularization: float = 1.0, max_iter: int = 10,
                 convergence_tol: float = 1e-4):
        self.num_samples = num_samples
        self.smoothness = smoothness
        self.regularization = regularization
        self.max_iter = max_iter
        self.convergence_tol = convergence_tol

    def sample_pixels(self, images: List[np.ndarray]) -> np.ndarray:
        h, w = images[0].shape[:2]
        num_pixels = h * w
        indices = np.linspace(0, num_pixels - 1, self.num_samples, dtype=np.int64)

        samples = []
        for img in images:
            if len(img.shape) == 3:
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                img_gray = img
            flat = img_gray.flatten()
            samples.append(flat[indices])

        return np.array(samples, dtype=np.float64)

    def solve_response_curve(self, images: List[np.ndarray],
                            exposure_times: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        Z = self.sample_pixels(images)
        B = np.log(np.clip(exposure_times, 1e-10, None))

        n = 256
        m = Z.shape[0]
        p = Z.shape[1]

        z_min, z_max = 5, 250

        g_prev = np.linspace(0, 5, n)
        lE_prev = np.zeros(p)

        for iteration in range(self.max_iter):
            W_diag = np.zeros(m * p, dtype=np.float64)
            A_rows = []
            b_rows = []

            k = 0
            for i in range(m):
                for j in range(p):
                    z = int(Z[i, j])
                    if z < z_min or z > z_max:
                        k += 1
                        continue
                    w = self._weight_function(z, g_prev[z])
                    W_diag[k] = w

                    row = np.zeros(n + p, dtype=np.float64)
                    row[z] = w
                    row[n + j] = -w
                    A_rows.append(row)
                    b_rows.append(w * B[i])
                    k += 1

            A_data = np.array(A_rows, dtype=np.float64) if A_rows else np.zeros((0, n + p))
            b_data = np.array(b_rows, dtype=np.float64) if b_rows else np.zeros(0)

            constraint_row = np.zeros(n + p, dtype=np.float64)
            constraint_row[128] = 1.0
            A_data = np.vstack([A_data, constraint_row])
            b_data = np.append(b_data, 0.0)

            reg_weight = self.smoothness * self.regularization
            for i in range(1, n - 1):
                w_smooth = self._weight_function(i, g_prev[i])
                reg_row = np.zeros(n + p, dtype=np.float64)
                reg_row[i - 1] = reg_weight * w_smooth
                reg_row[i] = -2.0 * reg_weight * w_smooth
                reg_row[i + 1] = reg_weight * w_smooth
                A_data = np.vstack([A_data, reg_row])
                b_data = np.append(b_data, 0.0)

            tikhonov_lambda = self.regularization * 0.1
            ATA = A_data.T @ A_data
            ATb = A_data.T @ b_data
            ATA[np.arange(n), np.arange(n)] += tikhonov_lambda

            try:
                x = np.linalg.solve(ATA, ATb)
            except np.linalg.LinAlgError:
                x = np.linalg.lstsq(A_data, b_data, rcond=None)[0]

            g = x[:n]
            lE = x[n:]

            g = g - g[0]

            g = np.sort(g)

            diff = np.max(np.abs(g - g_prev))
            if diff < self.convergence_tol:
                break

            g_prev = g.copy()
            lE_prev = lE.copy()

        return g, lE

    def _weight_function(self, z: int, g_z: float) -> float:
        z_f = float(z)
        if z_f <= 127:
            base_w = z_f + 1
        else:
            base_w = 256 - z_f

        w = base_w / 128.0

        g_range = np.max(g_z) - np.min(g_z) if hasattr(g_z, '__len__') else 5.0
        g_abs = abs(g_z) if g_z > 0 else 1.0
        w *= np.exp(-0.5 * (g_abs / (g_range + 1e-8)) ** 2)

        return w

    def _weight(self, z: int) -> float:
        if z <= 127:
            return z + 1
        return 256 - z


class HDRComposer:
    def __init__(self, response_curve: Optional[np.ndarray] = None):
        self.response_curve = response_curve

    def _weight(self, z: np.ndarray) -> np.ndarray:
        w = np.zeros_like(z, dtype=np.float64)
        mask = z <= 127
        w[mask] = z[mask] + 1
        w[~mask] = 256 - z[~mask]

        w = w / 128.0
        return w

    def compose(self, images: List[np.ndarray], exposure_times: np.ndarray,
                response_curves: Optional[List[np.ndarray]] = None) -> np.ndarray:
        h, w = images[0].shape[:2]
        num_channels = images[0].shape[2] if len(images[0].shape) == 3 else 1

        if response_curves is None:
            if self.response_curve is None:
                calc = CameraResponseCalculator()
                response_curves = []
                for c in range(num_channels):
                    channel_images = [img[:, :, c] for img in images]
                    g, _ = calc.solve_response_curve(channel_images, exposure_times)
                    response_curves.append(g)
            else:
                response_curves = [self.response_curve] * num_channels

        hdr = np.zeros((h, w, num_channels), dtype=np.float64)
        weight_sum = np.zeros((h, w, num_channels), dtype=np.float64)

        log_dt = np.log(np.clip(exposure_times, 1e-10, None))

        for i, img in enumerate(images):
            img_float = img.astype(np.float64)
            for c in range(num_channels):
                channel = img_float[:, :, c]
                z = np.clip(channel.astype(np.int32), 0, 255)
                w = self._weight(z)
                g = response_curves[c]
                g_z = g[z]
                hdr[:, :, c] += w * (g_z - log_dt[i])
                weight_sum[:, :, c] += w

        weight_sum[weight_sum == 0] = 1e-8
        hdr = np.exp(hdr / weight_sum)

        if num_channels == 1:
            hdr = hdr[:, :, 0]

        return hdr.astype(np.float32)


class ToneMapper:
    @staticmethod
    def _compute_luminance(hdr: np.ndarray) -> np.ndarray:
        if len(hdr.shape) == 3:
            return 0.2126 * hdr[:, :, 0] + 0.7152 * hdr[:, :, 1] + 0.0722 * hdr[:, :, 2]
        return hdr.copy()

    @staticmethod
    def _shoulder_compress(luminance: np.ndarray, threshold: float = 0.8,
                           strength: float = 0.5) -> np.ndarray:
        if strength <= 0:
            return luminance

        l_max = np.max(luminance)
        if l_max <= threshold:
            return luminance

        t = threshold * l_max

        below = luminance < t
        above = ~below

        result = luminance.copy()

        over = luminance[above] - t
        normalized_over = over / (l_max - t + 1e-8)

        compressed = t + (l_max - t) * np.power(normalized_over, 1.0 / (1.0 + strength))

        result[above] = compressed

        return result

    @staticmethod
    def reinhard(hdr: np.ndarray, key: float = 0.18,
                 white: Optional[float] = None,
                 highlight_compression: float = 0.3,
                 highlight_threshold: float = 0.8) -> np.ndarray:
        hdr_copy = hdr.copy()

        lum = ToneMapper._compute_luminance(hdr_copy)

        log_lum = np.log(lum + 1e-8)
        avg_lum = np.exp(np.mean(log_lum))

        scaled_lum = (key / avg_lum) * lum
        l_white = white if white is not None else np.max(scaled_lum)

        mapped_lum = (scaled_lum * (1 + scaled_lum / (l_white ** 2))) / (1 + scaled_lum)

        mapped_lum = ToneMapper._shoulder_compress(mapped_lum, highlight_threshold,
                                                    highlight_compression)

        if len(hdr_copy.shape) == 3:
            ratio = mapped_lum / (lum + 1e-8)
            result = hdr_copy * ratio[:, :, np.newaxis]
        else:
            result = mapped_lum

        result = np.clip(result, 0, 1)
        return (result * 255).astype(np.uint8)

    @staticmethod
    def filmic(hdr: np.ndarray, exposure: float = 1.0,
               contrast: float = 1.0, saturation: float = 1.0,
               highlight_compression: float = 0.4,
               highlight_threshold: float = 0.85) -> np.ndarray:
        hdr_copy = hdr.copy() * exposure

        def _aces_filmic(x: np.ndarray) -> np.ndarray:
            a = 2.51
            b = 0.03
            c = 2.43
            d = 0.59
            e = 0.14
            return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)

        result = _aces_filmic(hdr_copy)

        if highlight_compression > 0:
            lum = ToneMapper._compute_luminance(result)
            compressed_lum = ToneMapper._shoulder_compress(
                lum, highlight_threshold, highlight_compression
            )
            if len(result.shape) == 3:
                ratio = compressed_lum / (lum + 1e-8)
                result = result * ratio[:, :, np.newaxis]
            else:
                result = compressed_lum

        if len(result.shape) == 3 and saturation != 1.0:
            gray = np.mean(result, axis=2, keepdims=True)
            result = gray + saturation * (result - gray)

        if contrast != 1.0:
            result = 0.5 + contrast * (result - 0.5)

        result = np.clip(result, 0, 1)
        return (result * 255).astype(np.uint8)

    @staticmethod
    def gamma_correction(hdr: np.ndarray, gamma: float = 2.2,
                         highlight_compression: float = 0.2,
                         highlight_threshold: float = 0.8) -> np.ndarray:
        result = np.clip(hdr, 0, None)
        result = result / (result + 1.0)

        if highlight_compression > 0:
            lum = ToneMapper._compute_luminance(result)
            compressed_lum = ToneMapper._shoulder_compress(
                lum, highlight_threshold, highlight_compression
            )
            if len(result.shape) == 3:
                ratio = compressed_lum / (lum + 1e-8)
                result = result * ratio[:, :, np.newaxis]
            else:
                result = compressed_lum

        result = np.power(result, 1.0 / gamma)
        return (result * 255).astype(np.uint8)


class GhostRemoval:
    def __init__(self, threshold: float = 30.0, morph_kernel_size: int = 5,
                 dilation_iterations: int = 2, min_ghost_size: int = 100):
        self.threshold = threshold
        self.morph_kernel_size = morph_kernel_size
        self.dilation_iterations = dilation_iterations
        self.min_ghost_size = min_ghost_size

    def detect_ghosts(self, images: List[np.ndarray],
                      reference_idx: int = 0) -> List[np.ndarray]:
        if len(images) <= 1:
            return [np.zeros(img.shape[:2], dtype=np.uint8) for img in images]

        ref_img = images[reference_idx]
        ref_gray = self._to_gray(ref_img).astype(np.float32)

        ghost_masks = []
        for i, img in enumerate(images):
            if i == reference_idx:
                ghost_masks.append(np.zeros(img.shape[:2], dtype=np.uint8))
                continue

            img_gray = self._to_gray(img).astype(np.float32)
            diff = np.abs(ref_gray - img_gray)

            binary_mask = (diff > self.threshold).astype(np.uint8)

            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (self.morph_kernel_size, self.morph_kernel_size)
            )
            binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
            binary_mask = cv2.morphologyEx(
                binary_mask, cv2.MORPH_DILATE, kernel,
                iterations=self.dilation_iterations
            )

            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
                binary_mask, connectivity=8
            )
            for label in range(1, num_labels):
                if stats[label, cv2.CC_STAT_AREA] < self.min_ghost_size:
                    binary_mask[labels == label] = 0

            ghost_masks.append(binary_mask)

        return ghost_masks

    def remove_ghosts(self, images: List[np.ndarray],
                      exposure_times: np.ndarray,
                      ghost_masks: Optional[List[np.ndarray]] = None,
                      reference_idx: int = 0) -> List[np.ndarray]:
        if ghost_masks is None:
            ghost_masks = self.detect_ghosts(images, reference_idx)

        cleaned = [img.copy() for img in images]

        for i, (img, mask) in enumerate(zip(images, ghost_masks)):
            if i == reference_idx or np.sum(mask) == 0:
                continue

            ref_img = images[reference_idx]
            for c in range(img.shape[2] if len(img.shape) == 3 else 1):
                if len(img.shape) == 3:
                    src = img[:, :, c]
                    dst = ref_img[:, :, c]
                else:
                    src = img
                    dst = ref_img

                exposure_ratio = exposure_times[reference_idx] / exposure_times[i]
                adjusted_dst = np.clip(dst * exposure_ratio, 0, 255).astype(np.uint8)

                mask_3ch = mask if len(img.shape) == 2 else mask

                src[mask_3ch > 0] = adjusted_dst[mask_3ch > 0]

                if len(img.shape) == 3:
                    cleaned[i][:, :, c] = src
                else:
                    cleaned[i] = src

        return cleaned

    def detect_and_remove(self, images: List[np.ndarray],
                          exposure_times: np.ndarray,
                          reference_idx: int = 0) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        ghost_masks = self.detect_ghosts(images, reference_idx)
        cleaned = self.remove_ghosts(images, exposure_times, ghost_masks, reference_idx)
        return cleaned, ghost_masks

    def _to_gray(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img


class AdaptiveHDRComposer:
    def __init__(self, block_size: int = 32, overlap: int = 16,
                 contrast_weight: float = 1.0, saturation_weight: float = 1.0,
                 well_exposedness_weight: float = 1.0):
        self.block_size = block_size
        self.overlap = overlap
        self.contrast_weight = contrast_weight
        self.saturation_weight = saturation_weight
        self.well_exposedness_weight = well_exposedness_weight

    def _compute_block_quality(self, img_block: np.ndarray) -> float:
        if len(img_block.shape) == 3:
            block_gray = cv2.cvtColor(img_block, cv2.COLOR_BGR2GRAY)
        else:
            block_gray = img_block

        contrast = np.std(block_gray) / 128.0

        if len(img_block.shape) == 3:
            hsv = cv2.cvtColor(img_block, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1]) / 255.0
        else:
            saturation = 0.0

        mean_val = np.mean(block_gray)
        well_exposed = np.exp(-0.5 * ((mean_val - 128.0) / 64.0) ** 2)

        quality = (
            self.contrast_weight * contrast +
            self.saturation_weight * saturation +
            self.well_exposedness_weight * well_exposed
        )

        return quality

    def compute_weight_map(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        weight_map = np.zeros((h, w), dtype=np.float32)

        step = self.block_size - self.overlap
        y_starts = list(range(0, h - self.block_size + 1, step))
        x_starts = list(range(0, w - self.block_size + 1, step))

        if y_starts[-1] != h - self.block_size:
            y_starts.append(h - self.block_size)
        if x_starts[-1] != w - self.block_size:
            x_starts.append(w - self.block_size)

        block_weights = np.zeros((h, w), dtype=np.float32)

        for y in y_starts:
            for x in x_starts:
                block = image[y:y + self.block_size, x:x + self.block_size]
                quality = self._compute_block_quality(block)

                gaussian = cv2.getGaussianKernel(self.block_size, self.block_size / 4.0)
                gaussian_2d = gaussian @ gaussian.T

                weight_map[y:y + self.block_size, x:x + self.block_size] += (
                    quality * gaussian_2d
                )
                block_weights[y:y + self.block_size, x:x + self.block_size] += gaussian_2d

        block_weights[block_weights == 0] = 1e-8
        weight_map /= block_weights

        return weight_map

    def compose(self, images: List[np.ndarray], exposure_times: np.ndarray,
                response_curves: Optional[List[np.ndarray]] = None) -> np.ndarray:
        h, w = images[0].shape[:2]
        num_channels = images[0].shape[2] if len(images[0].shape) == 3 else 1

        if response_curves is None:
            calc = CameraResponseCalculator()
            response_curves = []
            for c in range(num_channels):
                channel_images = [img[:, :, c] for img in images]
                g, _ = calc.solve_response_curve(channel_images, exposure_times)
                response_curves.append(g)

        weight_maps = []
        for img in images:
            wm = self.compute_weight_map(img)
            weight_maps.append(wm)

        weight_sum = np.sum(weight_maps, axis=0)
        weight_sum[weight_sum == 0] = 1e-8

        log_dt = np.log(np.clip(exposure_times, 1e-10, None))

        hdr = np.zeros((h, w, num_channels), dtype=np.float64)

        for i, img in enumerate(images):
            img_float = img.astype(np.float64)
            for c in range(num_channels):
                channel = img_float[:, :, c]
                z = np.clip(channel.astype(np.int32), 0, 255)
                g = response_curves[c]
                g_z = g[z]
                hdr[:, :, c] += weight_maps[i] * (g_z - log_dt[i])

        hdr /= weight_sum[:, :, np.newaxis] if num_channels > 1 else weight_sum
        hdr = np.exp(hdr)

        if num_channels == 1:
            hdr = hdr[:, :, 0]

        return hdr.astype(np.float32)


class ResponseCurveLibrary:
    def __init__(self):
        self.curves: Dict[str, np.ndarray] = {}
        self._init_standard_curves()

    def _init_standard_curves(self):
        z = np.arange(256, dtype=np.float64)

        self.curves['linear'] = z / 255.0 * 5.0
        self.curves['sRGB'] = self._srgb_response_curve(z)
        self.curves['gamma_1_8'] = self._gamma_curve(z, 1.8)
        self.curves['gamma_2_2'] = self._gamma_curve(z, 2.2)
        self.curves['gamma_2_4'] = self._gamma_curve(z, 2.4)
        self.curves['canon'] = self._canon_style_curve(z)
        self.curves['nikon'] = self._nikon_style_curve(z)
        self.curves['sony'] = self._sony_style_curve(z)
        self.curves['log'] = np.log(z / 255.0 * 100.0 + 0.01)
        self.curves['cinematic'] = self._cinematic_curve(z)

    def _srgb_response_curve(self, z: np.ndarray) -> np.ndarray:
        linear = np.where(
            z <= 10,
            z / 3294.6,
            ((z / 255.0 + 0.055) / 1.055) ** 2.4
        )
        return np.log(linear * 100.0 + 0.01)

    def _gamma_curve(self, z: np.ndarray, gamma: float) -> np.ndarray:
        linear = (z / 255.0) ** gamma
        return np.log(linear * 100.0 + 0.01)

    def _canon_style_curve(self, z: np.ndarray) -> np.ndarray:
        t = z / 255.0
        linear = np.piecewise(t, [
            t < 0.1,
            (t >= 0.1) & (t < 0.9),
            t >= 0.9
        ], [
            lambda x: x * 2.5,
            lambda x: np.power(x, 2.2) * 0.9 + 0.1,
            lambda x: (x - 0.9) * 3.0 + 0.9
        ])
        return np.log(linear * 100.0 + 0.01)

    def _nikon_style_curve(self, z: np.ndarray) -> np.ndarray:
        t = z / 255.0
        linear = np.piecewise(t, [
            t < 0.05,
            (t >= 0.05) & (t < 0.95),
            t >= 0.95
        ], [
            lambda x: x * 3.0,
            lambda x: np.power(x, 2.0) * 0.85 + 0.15,
            lambda x: (x - 0.95) * 4.0 + 0.95
        ])
        return np.log(linear * 100.0 + 0.01)

    def _sony_style_curve(self, z: np.ndarray) -> np.ndarray:
        t = z / 255.0
        linear = np.piecewise(t, [
            t < 0.08,
            (t >= 0.08) & (t < 0.85),
            t >= 0.85
        ], [
            lambda x: x * 2.8,
            lambda x: np.power(x, 2.3) * 0.88 + 0.12,
            lambda x: (x - 0.85) * 3.5 + 0.88
        ])
        return np.log(linear * 100.0 + 0.01)

    def _cinematic_curve(self, z: np.ndarray) -> np.ndarray:
        t = z / 255.0
        linear = np.piecewise(t, [
            t < 0.15,
            (t >= 0.15) & (t < 0.8),
            t >= 0.8
        ], [
            lambda x: np.power(x, 1.2) * 2.0,
            lambda x: np.power(x, 2.0) * 0.8 + 0.2,
            lambda x: np.power(x, 0.8) * 1.2 - 0.1
        ])
        return np.log(np.clip(linear, 0.001, None) * 100.0)

    def get_curve(self, name: str) -> np.ndarray:
        if name not in self.curves:
            raise ValueError(f"未知的响应曲线: {name}. 可用: {list(self.curves.keys())}")
        return self.curves[name].copy()

    def get_curves_for_rgb(self, name: str) -> List[np.ndarray]:
        curve = self.get_curve(name)
        return [curve.copy() for _ in range(3)]

    def list_curves(self) -> List[str]:
        return list(self.curves.keys())

    def match_curve(self, measured_curve: np.ndarray,
                    candidates: Optional[List[str]] = None) -> Tuple[str, float]:
        if candidates is None:
            candidates = self.list_curves()

        best_name = None
        best_distance = float('inf')

        measured_norm = (measured_curve - measured_curve[0])
        measured_norm = measured_norm / (measured_norm[-1] + 1e-8)

        for name in candidates:
            candidate = self.curves[name]
            candidate_norm = (candidate - candidate[0])
            candidate_norm = candidate_norm / (candidate_norm[-1] + 1e-8)

            distance = np.mean((measured_norm - candidate_norm) ** 2)

            if distance < best_distance:
                best_distance = distance
                best_name = name

        return best_name, best_distance

    def add_custom_curve(self, name: str, curve: np.ndarray):
        if curve.shape[0] != 256:
            raise ValueError("响应曲线必须是256个采样点")
        self.curves[name] = curve.copy()


def align_images(images: List[np.ndarray], reference_idx: int = 0,
                 **kwargs) -> List[np.ndarray]:
    aligner = ImageAligner(**kwargs)
    return aligner.align_images(images, reference_idx)


def compute_response_curve(images: List[np.ndarray],
                           exposure_times: np.ndarray,
                           **kwargs) -> List[np.ndarray]:
    num_channels = images[0].shape[2] if len(images[0].shape) == 3 else 1
    calc = CameraResponseCalculator(**kwargs)
    response_curves = []

    for c in range(num_channels):
        if num_channels > 1:
            channel_images = [img[:, :, c] for img in images]
        else:
            channel_images = images
        g, _ = calc.solve_response_curve(channel_images, exposure_times)
        response_curves.append(g)

    return response_curves


def create_hdr(images: List[np.ndarray], exposure_times: np.ndarray,
               response_curves: Optional[List[np.ndarray]] = None,
               align: bool = False,
               remove_ghosts: bool = False,
               adaptive: bool = False) -> np.ndarray:
    if align:
        images = align_images(images)

    if remove_ghosts:
        ghost_remover = GhostRemoval()
        images, _ = ghost_remover.detect_and_remove(images, exposure_times)

    if adaptive:
        composer = AdaptiveHDRComposer()
    else:
        composer = HDRComposer()

    return composer.compose(images, exposure_times, response_curves)


def tone_map(hdr: np.ndarray, method: str = 'reinhard', **kwargs) -> np.ndarray:
    mapper = ToneMapper()

    if method == 'reinhard':
        return mapper.reinhard(hdr, **kwargs)
    elif method == 'filmic':
        return mapper.filmic(hdr, **kwargs)
    elif method == 'gamma':
        return mapper.gamma_correction(hdr, **kwargs)
    else:
        raise ValueError(f"Unknown tone mapping method: {method}")


def get_response_curve_library() -> ResponseCurveLibrary:
    return ResponseCurveLibrary()
