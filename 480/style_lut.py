import numpy as np
import cv2
from typing import List, Optional, Tuple
from sklearn.mixture import GaussianMixture
from color_transfer import (
    ColorSpace,
    convert_to_color_space,
    convert_from_color_space,
    _channel_stats,
    reinhard_transfer,
    GMMColorTransfer,
)


class StylePalette:
    def __init__(
        self,
        n_colors: int = 8,
        color_space: ColorSpace = ColorSpace.LAB,
    ):
        self.n_colors = n_colors
        self.color_space = color_space
        self.palette_means: Optional[np.ndarray] = None
        self.palette_stds: Optional[np.ndarray] = None
        self.palette_weights: Optional[np.ndarray] = None
        self.gmm: Optional[GaussianMixture] = None

    def fit(
        self,
        references: List[np.ndarray],
        weights: Optional[List[float]] = None,
        sample_ratio: float = 0.3,
    ) -> "StylePalette":
        if weights is None:
            weights = [1.0] * len(references)
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        all_pixels = []
        rng = np.random.RandomState(42)

        for ref_img, w in zip(references, weights):
            ref_cs = convert_to_color_space(ref_img, self.color_space)
            pixels = ref_cs.reshape(-1, 3)
            n_pixels = pixels.shape[0]
            n_sample = max(1, int(n_pixels * sample_ratio * w * len(references)))
            n_sample = min(n_sample, n_pixels)
            indices = rng.choice(n_pixels, size=n_sample, replace=False)
            all_pixels.append(pixels[indices])

        all_pixels = np.vstack(all_pixels)

        n_comp = min(self.n_colors, all_pixels.shape[0])
        self.gmm = GaussianMixture(
            n_components=n_comp,
            max_iter=200,
            covariance_type="full",
            random_state=42,
        )
        self.gmm.fit(all_pixels)

        labels = self.gmm.predict(all_pixels)
        self.palette_means = self.gmm.means_.copy()
        self.palette_stds = np.zeros((n_comp, 3), dtype=np.float64)
        self.palette_weights = np.zeros(n_comp, dtype=np.float64)

        for k in range(n_comp):
            mask = labels == k
            count = np.sum(mask)
            self.palette_weights[k] = count / len(labels)
            if count > 1:
                cluster_pixels = all_pixels[mask]
                self.palette_stds[k] = np.std(cluster_pixels, axis=0)
            else:
                self.palette_stds[k] = np.sqrt(np.diag(self.gmm.covariances_[k]))
            self.palette_stds[k][self.palette_stds[k] < 1e-6] = 1e-6

        return self

    def transfer(
        self,
        source: np.ndarray,
        blend: float = 1.0,
        preserve_details: bool = True,
    ) -> np.ndarray:
        if self.palette_means is None or self.gmm is None:
            raise RuntimeError("Call fit() before transfer()")

        src_cs = convert_to_color_space(source, self.color_space)
        h, w = source.shape[:2]
        src_pixels = src_cs.reshape(-1, 3)

        src_gmm = GaussianMixture(
            n_components=self.gmm.n_components,
            max_iter=200,
            covariance_type="full",
            random_state=42,
        )
        src_gmm.fit(src_pixels)

        src_labels = src_gmm.predict(src_pixels)

        transferred = src_pixels.copy().astype(np.float64)
        for k in range(self.gmm.n_components):
            mask = src_labels == k
            src_k = src_pixels[mask]
            if len(src_k) == 0:
                continue

            src_mean_k = np.mean(src_k, axis=0)
            src_std_k = np.std(src_k, axis=0)
            src_std_k[src_std_k < 1e-6] = 1e-6

            distances = np.linalg.norm(src_gmm.means_[k] - self.palette_means, axis=1)
            closest = np.argmin(distances)

            ref_mean_k = self.palette_means[closest]
            ref_std_k = self.palette_stds[closest]

            transferred[mask] = (
                (src_k - src_mean_k) * (ref_std_k / src_std_k) + ref_mean_k
            )

        result = transferred.reshape(h, w, 3)

        if 0.0 < blend < 1.0:
            result = src_cs * (1 - blend) + result * blend

        if self.color_space == ColorSpace.HSV:
            result[:, :, 0] = result[:, :, 0] % 180

        return convert_from_color_space(result, self.color_space, preserve_details=preserve_details)

    def get_palette_rgb(self) -> np.ndarray:
        if self.palette_means is None:
            raise RuntimeError("Call fit() before get_palette_rgb()")

        lab_means = self.palette_means.copy()
        if self.color_space == ColorSpace.LAB:
            lab_uint8 = np.round(lab_means).astype(np.uint8)
            lab_pixels = lab_uint8.reshape(1, -1, 3)
            bgr = cv2.cvtColor(lab_pixels, cv2.COLOR_Lab2BGR)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return rgb.reshape(-1, 3)
        elif self.color_space == ColorSpace.RGB:
            return np.round(lab_means).astype(np.uint8)
        else:
            dummy = np.zeros((1, lab_means.shape[0], 3), dtype=np.uint8)
            for i, mean in enumerate(lab_means):
                pixel = np.round(mean).astype(np.uint8).reshape(1, 1, 3)
                if self.color_space == ColorSpace.HSV:
                    bgr = cv2.cvtColor(pixel, cv2.COLOR_HSV2BGR)
                elif self.color_space == ColorSpace.YCRCB:
                    bgr = cv2.cvtColor(pixel, cv2.COLOR_YCrCb2BGR)
                else:
                    bgr = pixel
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                dummy[0, i] = rgb[0, 0]
            return dummy.reshape(-1, 3)

    def visualize_palette(self, swatch_size: int = 60) -> np.ndarray:
        rgb_colors = self.get_palette_rgb()
        n = rgb_colors.shape[0]
        canvas = np.zeros((swatch_size, n * swatch_size, 3), dtype=np.uint8)
        for i in range(n):
            canvas[:, i * swatch_size:(i + 1) * swatch_size] = rgb_colors[i]
        return canvas


class LUT3D:
    def __init__(self, size: int = 33):
        self.size = size
        self.lut: Optional[np.ndarray] = None

    @staticmethod
    def from_transfer_function(
        transfer_fn,
        size: int = 33,
    ) -> "LUT3D":
        lut_obj = LUT3D(size)
        n = size ** 3
        side = size ** 2

        rgb_values = np.zeros((n, 3), dtype=np.uint8)
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    idx = b * size * size + g * size + r
                    rgb_values[idx, 0] = int(round(r / (size - 1) * 255))
                    rgb_values[idx, 1] = int(round(g / (size - 1) * 255))
                    rgb_values[idx, 2] = int(round(b / (size - 1) * 255))

        img_h = side
        img_w = size
        bgr_values = rgb_values[:, ::-1].copy()
        big_img = bgr_values.reshape(img_h, img_w, 3)

        result_img = transfer_fn(big_img)

        result_rgb = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
        result_float = result_rgb.reshape(n, 3).astype(np.float64) / 255.0
        lut_obj.lut = result_float.reshape(size, size, size, 3)

        return lut_obj

    def apply(self, image: np.ndarray) -> np.ndarray:
        if self.lut is None:
            raise RuntimeError("LUT not initialized")

        h, w = image.shape[:2]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float64) / 255.0
        s = self.size - 1

        r = rgb[:, :, 0] * s
        g = rgb[:, :, 1] * s
        b = rgb[:, :, 2] * s

        r0 = np.floor(r).astype(np.int32)
        g0 = np.floor(g).astype(np.int32)
        b0 = np.floor(b).astype(np.int32)

        r1 = np.minimum(r0 + 1, s)
        g1 = np.minimum(g0 + 1, s)
        b1 = np.minimum(b0 + 1, s)

        r0 = np.clip(r0, 0, s)
        g0 = np.clip(g0, 0, s)
        b0 = np.clip(b0, 0, s)

        rd = (r - r0).astype(np.float64)
        gd = (g - g0).astype(np.float64)
        bd = (b - b0).astype(np.float64)

        def _lookup(bi, gi, ri):
            return self.lut[bi, gi, ri]

        c000 = _lookup(b0, g0, r0)
        c001 = _lookup(b0, g0, r1)
        c010 = _lookup(b0, g1, r0)
        c011 = _lookup(b0, g1, r1)
        c100 = _lookup(b1, g0, r0)
        c101 = _lookup(b1, g0, r1)
        c110 = _lookup(b1, g1, r0)
        c111 = _lookup(b1, g1, r1)

        rd = rd[:, :, np.newaxis]
        gd = gd[:, :, np.newaxis]
        bd = bd[:, :, np.newaxis]

        c00 = c000 * (1 - rd) + c001 * rd
        c01 = c010 * (1 - rd) + c011 * rd
        c10 = c100 * (1 - rd) + c101 * rd
        c11 = c110 * (1 - rd) + c111 * rd

        c0 = c00 * (1 - gd) + c01 * gd
        c1 = c10 * (1 - gd) + c11 * gd

        result = c0 * (1 - bd) + c1 * bd
        result = np.clip(result, 0.0, 1.0)

        result_uint8 = np.round(result * 255.0).astype(np.uint8)
        result_bgr = cv2.cvtColor(result_uint8, cv2.COLOR_RGB2BGR)

        return result_bgr

    def save_cube(self, filepath: str, name: str = "ColorTransferLUT") -> None:
        if self.lut is None:
            raise RuntimeError("LUT not initialized")

        with open(filepath, "w") as f:
            f.write(f"# Created by style_lut\n")
            f.write(f'TITLE "{name}"\n')
            f.write(f"LUT_3D_SIZE {self.size}\n")
            f.write("\n")

            for b in range(self.size):
                for g in range(self.size):
                    for r in range(self.size):
                        rgb = self.lut[b, g, r]
                        f.write(f"{rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n")

    @staticmethod
    def load_cube(filepath: str) -> "LUT3D":
        with open(filepath, "r") as f:
            lines = f.readlines()

        size = None
        data_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("TITLE"):
                continue
            if stripped.startswith("LUT_3D_SIZE"):
                size = int(stripped.split()[-1])
                continue
            data_lines.append(stripped)

        if size is None:
            raise ValueError("LUT_3D_SIZE not found in .cube file")

        lut_obj = LUT3D(size)
        lut_obj.lut = np.zeros((size, size, size, 3), dtype=np.float64)

        idx = 0
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    parts = data_lines[idx].split()
                    lut_obj.lut[b, g, r, 0] = float(parts[0])
                    lut_obj.lut[b, g, r, 1] = float(parts[1])
                    lut_obj.lut[b, g, r, 2] = float(parts[2])
                    idx += 1

        return lut_obj

    def save_png(self, filepath: str, hald_size: int = 16) -> None:
        if self.lut is None:
            raise RuntimeError("LUT not initialized")

        s = self.size
        img_size = s * s
        clut = np.zeros((img_size, img_size, 3), dtype=np.uint8)

        cols = np.arange(img_size)
        rows = np.arange(img_size)
        col_grid, row_grid = np.meshgrid(cols, rows)

        r_idx = col_grid % s
        g_idx = row_grid % s
        b_idx = col_grid // s

        r_idx = np.clip(r_idx, 0, s - 1)
        g_idx = np.clip(g_idx, 0, s - 1)
        b_idx = np.clip(b_idx, 0, s - 1)

        rgb = self.lut[b_idx, g_idx, r_idx]
        rgb_uint8 = np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
        clut = rgb_uint8

        bgr = cv2.cvtColor(clut, cv2.COLOR_RGB2BGR)
        cv2.imwrite(filepath, bgr)
