import numpy as np
import cv2
from dataclasses import dataclass, field
from typing import Optional, Tuple

from dl_stereo import (
    DLConfig, DeepSGMRefiner, RealTimeStereo,
    SREnhancer, WeakTextureEnhancer, FastBilateralSolver,
)


@dataclass
class StereoParams:
    camera_matrix_l: np.ndarray
    dist_coeffs_l: np.ndarray
    camera_matrix_r: np.ndarray
    dist_coeffs_r: np.ndarray
    R: np.ndarray
    T: np.ndarray
    image_size: Tuple[int, int]
    rect_l: Optional[np.ndarray] = None
    rect_r: Optional[np.ndarray] = None
    proj_l: Optional[np.ndarray] = None
    proj_r: Optional[np.ndarray] = None
    Q: Optional[np.ndarray] = None
    roi_l: Optional[Tuple[int, int, int, int]] = None
    roi_r: Optional[Tuple[int, int, int, int]] = None
    map_lx: Optional[np.ndarray] = None
    map_ly: Optional[np.ndarray] = None
    map_rx: Optional[np.ndarray] = None
    map_ry: Optional[np.ndarray] = None


@dataclass
class SGMConfig:
    min_disparity: int = 0
    num_disparities: int = 64
    block_size: int = 5
    p1: int = 8
    p2: int = 32
    disp12_max_diff: int = 1
    pre_filter_cap: int = 63
    uniqueness_ratio: int = 10
    speckle_window_size: int = 100
    speckle_range: int = 32
    mode: int = cv2.STEREO_SGBM_MODE_SGBM_3WAY
    use_mode_hq: bool = False
    wsl_lambda: float = 8000.0
    wsl_sigma: float = 1.5
    median_kernel: int = 5
    bilateral_d: int = 9
    bilateral_sigma_color: int = 75
    bilateral_sigma_space: int = 75
    fill_holes: bool = True
    subpixel_refine: bool = True
    adaptive_p2: bool = True
    adaptive_p1: bool = True
    gradient_scale: float = 1.0
    census_window: int = 5
    multi_peak_detect: bool = True
    peak_ratio: float = 0.85
    peak_min_distance: int = 3
    use_gpu: bool = True
    use_dl_refine: bool = False
    dl_device: str = "auto"
    use_super_res: bool = False
    sr_scale: int = 4
    sr_method: str = "hybrid"
    enhance_weak_texture: bool = False
    weak_texture_grad_thresh: float = 15.0
    use_bilateral_solver: bool = False
    target_fps: int = 30


class StereoRectifier:
    def __init__(self, params: StereoParams):
        self.params = params
        self._computed = False

    def compute_rectification(self, alpha: float = 0.0) -> None:
        p = self.params
        (self.params.rect_l, self.params.rect_r,
         self.params.proj_l, self.params.proj_r,
         self.params.Q, self.params.roi_l, self.params.roi_r) = cv2.stereoRectify(
            p.camera_matrix_l, p.dist_coeffs_l,
            p.camera_matrix_r, p.dist_coeffs_r,
            p.image_size, p.R, p.T,
            alpha=alpha,
            flags=cv2.CALIB_ZERO_DISPARITY,
        )
        self.params.map_lx, self.params.map_ly = cv2.initUndistortRectifyMap(
            p.camera_matrix_l, p.dist_coeffs_l,
            p.rect_l, p.proj_l, p.image_size, cv2.CV_32FC1,
        )
        self.params.map_rx, self.params.map_ry = cv2.initUndistortRectifyMap(
            p.camera_matrix_r, p.dist_coeffs_r,
            p.rect_r, p.proj_r, p.image_size, cv2.CV_32FC1,
        )
        self._computed = True

    def rectify(self, img_l: np.ndarray, img_r: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self._computed:
            self.compute_rectification()
        p = self.params
        rect_l = cv2.remap(img_l, p.map_lx, p.map_ly, cv2.INTER_LINEAR)
        rect_r = cv2.remap(img_r, p.map_rx, p.map_ry, cv2.INTER_LINEAR)
        return rect_l, rect_r

    def get_valid_roi(self) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
        return self.params.roi_l, self.params.roi_r


class SGMDisparity:
    def __init__(self, config: SGMConfig):
        self.config = config
        self._build_matcher()

    def _build_matcher(self) -> None:
        c = self.config
        mode = cv2.STEREO_SGBM_MODE_HQ if c.use_mode_hq else c.mode
        self.matcher = cv2.StereoSGBM_create(
            minDisparity=c.min_disparity,
            numDisparities=c.num_disparities,
            blockSize=c.block_size,
            P1=c.p1 * c.block_size * c.block_size,
            P2=c.p2 * c.block_size * c.block_size,
            disp12MaxDiff=c.disp12_max_diff,
            preFilterCap=c.pre_filter_cap,
            uniquenessRatio=c.uniqueness_ratio,
            speckleWindowSize=c.speckle_window_size,
            speckleRange=c.speckle_range,
            mode=mode,
        )
        self.right_matcher = cv2.ximgproc.createRightMatcher(self.matcher)

    def compute(self, img_l: np.ndarray, img_r: np.ndarray) -> np.ndarray:
        gray_l = cv2.cvtColor(img_l, cv2.COLOR_BGR2GRAY) if len(img_l.shape) == 3 else img_l
        gray_r = cv2.cvtColor(img_r, cv2.COLOR_BGR2GRAY) if len(img_r.shape) == 3 else img_r
        disp_l = self.matcher.compute(gray_l, gray_r).astype(np.float32) / 16.0
        return disp_l

    def compute_lr(self, img_l: np.ndarray, img_r: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        gray_l = cv2.cvtColor(img_l, cv2.COLOR_BGR2GRAY) if len(img_l.shape) == 3 else img_l
        gray_r = cv2.cvtColor(img_r, cv2.COLOR_BGR2GRAY) if len(img_r.shape) == 3 else img_r
        disp_l = self.matcher.compute(gray_l, gray_r).astype(np.float32) / 16.0
        disp_r = self.right_matcher.compute(gray_r, gray_l).astype(np.float32) / 16.0
        return disp_l, disp_r


class AdaptiveSGMDisparity:
    def __init__(self, config: SGMConfig):
        self.config = config
        self._base_matcher = SGMDisparity(config)
        self.matcher = self._base_matcher.matcher
        self.right_matcher = self._base_matcher.right_matcher
        self._cost_volume = None
        self._confidence = None
        self._grad_mag = None

    @staticmethod
    def _to_gray(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def compute_gradient(self, img: np.ndarray) -> np.ndarray:
        gray = self._to_gray(img).astype(np.float32)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        return np.sqrt(gx * gx + gy * gy)

    def compute_adaptive_p_maps(self, img_l: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        c = self.config
        grad = self.compute_gradient(img_l)
        self._grad_mag = grad
        grad_norm = cv2.normalize(grad, None, 0, 1, cv2.NORM_MINMAX)
        h, w = grad_norm.shape
        p1_base = c.p1 * c.block_size * c.block_size
        p2_base = c.p2 * c.block_size * c.block_size
        if c.adaptive_p1:
            p1_map = (p1_base * (1.0 + c.gradient_scale * (1.0 - grad_norm))).astype(np.float32)
        else:
            p1_map = np.full((h, w), p1_base, dtype=np.float32)
        if c.adaptive_p2:
            p2_map = (p2_base / (1.0 + c.gradient_scale * grad_norm)).astype(np.float32)
            p2_map = np.clip(p2_map, p2_base * 0.1, p2_base * 2.0)
        else:
            p2_map = np.full((h, w), p2_base, dtype=np.float32)
        return p1_map, p2_map

    def _census_transform(self, img: np.ndarray, window: int = 5) -> np.ndarray:
        gray = self._to_gray(img)
        h, w = gray.shape
        half = window // 2
        census = np.zeros((h, w), dtype=np.uint64)
        bit = 0
        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                if dy == 0 and dx == 0:
                    continue
                shifted = np.roll(np.roll(gray, -dy, axis=0), -dx, axis=1)
                census |= ((gray > shifted).astype(np.uint64) << bit)
                bit += 1
        return census

    @staticmethod
    def _popcount(arr: np.ndarray) -> np.ndarray:
        count = np.zeros(arr.shape, dtype=np.float32)
        tmp = arr.copy()
        while np.any(tmp > 0):
            count += (tmp & 1).astype(np.float32)
            tmp >>= 1
        return count

    def compute_census_cost(self, img_l: np.ndarray, img_r: np.ndarray) -> np.ndarray:
        c = self.config
        census_l = self._census_transform(img_l, c.census_window)
        census_r = self._census_transform(img_r, c.census_window)
        h, w = census_l.shape
        nd = c.num_disparities
        cost = np.zeros((h, w, nd), dtype=np.float32)
        for d in range(nd):
            shifted_r = np.roll(census_r, -d, axis=1)
            xor = np.bitwise_xor(census_l, shifted_r)
            cost[:, :, d] = self._popcount(xor)
            if d > 0:
                cost[:, :d, d] = cost[:, :d, 0]
        return cost

    def _aggregate_direction(self, cost_vol: np.ndarray, p1_map: np.ndarray,
                             p2_map: np.ndarray, axis: int, forward: bool) -> np.ndarray:
        h, w, nd = cost_vol.shape
        agg = np.zeros_like(cost_vol)
        n_iter = w if axis == 1 else h

        for i in range(n_iter):
            if forward:
                idx = i
                prev_idx = i - 1
            else:
                idx = n_iter - 1 - i
                prev_idx = idx + 1

            if (forward and i == 0) or (not forward and i == 0):
                if axis == 1:
                    agg[:, idx, :] = cost_vol[:, idx, :]
                else:
                    agg[idx, :, :] = cost_vol[idx, :, :]
                continue

            if axis == 1:
                prev = agg[:, prev_idx, :]
                cur_p1 = p1_map[:, idx]
                cur_p2 = p2_map[:, idx]
            else:
                prev = agg[prev_idx, :, :]
                cur_p1 = p1_map[idx, :]
                cur_p2 = p2_map[idx, :]

            min_prev = np.min(prev, axis=1, keepdims=True)

            term_same = prev

            term_d_minus1 = np.full_like(prev, np.inf)
            term_d_minus1[:, 1:] = prev[:, :-1] + cur_p1[:, np.newaxis]

            term_d_plus1 = np.full_like(prev, np.inf)
            term_d_plus1[:, :-1] = prev[:, 1:] + cur_p1[:, np.newaxis]

            term_min = min_prev + cur_p2[:, np.newaxis]

            best = np.minimum(
                np.minimum(term_same, term_d_minus1),
                np.minimum(term_d_plus1, term_min),
            )

            if axis == 1:
                agg[:, idx, :] = cost_vol[:, idx, :] + best - min_prev
            else:
                agg[idx, :, :] = cost_vol[idx, :, :] + best - min_prev

        return agg

    def aggregate_cost(self, cost_vol: np.ndarray, p1_map: np.ndarray,
                       p2_map: np.ndarray) -> np.ndarray:
        paths = [
            (1, True),
            (1, False),
            (0, True),
            (0, False),
        ]
        total = np.zeros_like(cost_vol)
        for axis, forward in paths:
            total += self._aggregate_direction(cost_vol, p1_map, p2_map, axis, forward)
        return total

    def multi_peak_detect(self, agg_cost: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        c = self.config
        h, w, nd = agg_cost.shape
        sorted_idx = np.argsort(agg_cost, axis=2)
        best_d = sorted_idx[:, :, 0].astype(np.float32) + c.min_disparity
        best_cost = np.take_along_axis(agg_cost, sorted_idx[:, :, 0:1], axis=2).squeeze(axis=2)
        second_d = sorted_idx[:, :, 1].astype(np.float32) + c.min_disparity
        second_cost = np.take_along_axis(agg_cost, sorted_idx[:, :, 1:2], axis=2).squeeze(axis=2)

        disparity_dist = np.abs(best_d - second_d)
        far_peak = disparity_dist >= c.peak_min_distance

        ambiguous = np.ones((h, w), dtype=bool)
        valid = best_cost < np.inf
        ratio = np.ones((h, w), dtype=np.float32)
        ratio[valid] = best_cost[valid] / (second_cost[valid] + 1e-10)
        clear_peak = ratio < c.peak_ratio
        ambiguous = ~(clear_peak & far_peak)

        confidence = np.zeros((h, w), dtype=np.float32)
        confidence[valid & ~ambiguous] = 1.0 - ratio[valid & ~ambiguous]
        confidence[ambiguous] = 0.0

        best_d[ambiguous] = -1.0
        return best_d, confidence

    def compute(self, img_l: np.ndarray, img_r: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        c = self.config
        disp_base = self._base_matcher.compute(img_l, img_r)
        if not c.adaptive_p2 and not c.adaptive_p1 and not c.multi_peak_detect:
            return disp_base, np.ones_like(disp_base)

        p1_map, p2_map = self.compute_adaptive_p_maps(img_l)
        cost_vol = self.compute_census_cost(img_l, img_r)

        nd = c.num_disparities
        disp_idx = np.clip(
            (disp_base - c.min_disparity).astype(np.int32), 0, nd - 1,
        )
        h, w = disp_base.shape
        y_grid, x_grid = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        base_cost = cost_vol[y_grid, x_grid, disp_idx]
        cost_boost = base_cost * 0.3
        for d in range(nd):
            cost_vol[:, :, d] += cost_boost

        agg_cost = self.aggregate_cost(cost_vol, p1_map, p2_map)
        self._cost_volume = agg_cost

        if c.multi_peak_detect:
            disp_adaptive, confidence = self.multi_peak_detect(agg_cost)
        else:
            disp_adaptive = np.argmin(agg_cost, axis=2).astype(np.float32) + c.min_disparity
            confidence = np.ones((h, w), dtype=np.float32)

        mask = disp_adaptive < 0
        disp_adaptive[mask] = disp_base[mask]
        confidence[mask] = 0.0

        self._confidence = confidence
        return disp_adaptive, confidence

    def compute_lr(self, img_l: np.ndarray, img_r: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        disp_l, confidence = self.compute(img_l, img_r)
        disp_r = self._base_matcher.right_matcher.compute(
            self._to_gray(img_r), self._to_gray(img_l),
        ).astype(np.float32) / 16.0
        return disp_l, disp_r, confidence


class DisparityPostProcessor:
    def __init__(self, config: SGMConfig, matcher_left=None):
        self.config = config
        self.matcher_left = matcher_left

    def wls_filter(self, img_l: np.ndarray, disp_l: np.ndarray, disp_r: np.ndarray) -> np.ndarray:
        if self.matcher_left is not None:
            wls = cv2.ximgproc.createDisparityWLSFilter(self.matcher_left)
        else:
            wls = cv2.ximgproc.createDisparityWLSFilter(np.bool_(True))
        wls.setLambda(self.config.wsl_lambda)
        wls.setSigmaColor(self.config.wsl_sigma)
        filtered = wls.filter(disp_l, img_l, disparity_map_right=disp_r)
        return filtered

    def median_filter(self, disp: np.ndarray) -> np.ndarray:
        valid = disp >= self.config.min_disparity
        result = cv2.medianBlur(disp, self.config.median_kernel)
        result[~valid] = disp[~valid]
        return result

    def bilateral_filter(self, disp: np.ndarray) -> np.ndarray:
        valid = disp >= self.config.min_disparity
        result = cv2.bilateralFilter(
            disp, self.config.bilateral_d,
            self.config.bilateral_sigma_color,
            self.config.bilateral_sigma_space,
        )
        result[~valid] = disp[~valid]
        return result

    def fill_invalid(self, disp: np.ndarray) -> np.ndarray:
        if not self.config.fill_holes:
            return disp
        invalid = disp < self.config.min_disparity
        if not np.any(invalid):
            return disp
        result = disp.copy()
        filled = cv2.inpaint(
            result.astype(np.float32),
            invalid.astype(np.uint8),
            inpaintRadius=3,
            flags=cv2.INPAINT_TELEA,
        )
        return filled

    def subpixel_refinement(self, disp: np.ndarray, img_l: np.ndarray) -> np.ndarray:
        if not self.config.subpixel_refine:
            return disp
        result = disp.copy()
        valid = disp >= self.config.min_disparity
        d_left = np.roll(disp, 1, axis=1)
        d_right = np.roll(disp, -1, axis=1)
        denom = 2.0 * (d_left + d_right - 2.0 * disp)
        has_peak = np.abs(denom) > 1e-6
        offset = np.zeros_like(disp)
        offset[has_peak] = (d_left[has_peak] - d_right[has_peak]) / denom[has_peak]
        offset = np.clip(offset, -0.5, 0.5)
        result[valid] = disp[valid] + offset[valid]
        return result

    def process(self, img_l: np.ndarray, disp_l: np.ndarray,
                disp_r: Optional[np.ndarray] = None,
                confidence: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        result = disp_l.copy()
        conf = confidence.copy() if confidence is not None else np.ones_like(disp_l)

        low_conf = conf < 0.3
        result[low_conf] = -1.0

        if disp_r is not None:
            try:
                result = self.wls_filter(img_l, result, disp_r)
            except Exception:
                result = self.median_filter(result)
        else:
            result = self.median_filter(result)
        result = self.bilateral_filter(result)
        result = self.fill_invalid(result)
        result = self.subpixel_refinement(result, img_l)

        if confidence is not None:
            restored = low_conf & (result >= self.config.min_disparity)
            conf[restored] = 0.2

        return result, conf


class DepthEstimator:
    def __init__(self, Q: np.ndarray, baseline: Optional[float] = None, focal_length: Optional[float] = None):
        self.Q = Q
        self.baseline = baseline
        self.focal_length = focal_length
        self._extract_params()

    def _extract_params(self) -> None:
        if self.Q is not None and self.Q.size > 0:
            self.Q_baseline = abs(1.0 / self.Q[3, 2]) if abs(self.Q[3, 2]) > 1e-10 else 0.0
            self.Q_focal = abs(self.Q[2, 3]) if abs(self.Q[2, 3]) > 1e-10 else 0.0
        else:
            self.Q_baseline = self.baseline if self.baseline else 0.0
            self.Q_focal = self.focal_length if self.focal_length else 0.0

    def disparity_to_depth(self, disparity: np.ndarray, max_depth: float = 0.0) -> np.ndarray:
        if self.Q is not None and self.Q.size > 0:
            points = cv2.reprojectImageTo3D(disparity, self.Q, handleMissingValues=True)
            depth = np.abs(points[:, :, 2])
            depth[disparity <= 0] = 0
            depth[depth < 0] = 0
            if max_depth > 0:
                depth[depth > max_depth] = 0
            return depth
        if self.Q_baseline > 0 and self.Q_focal > 0:
            depth = np.zeros_like(disparity, dtype=np.float32)
            valid = disparity > 0
            depth[valid] = (self.Q_focal * self.Q_baseline) / disparity[valid]
            return depth
        raise ValueError("No valid Q matrix or baseline/focal parameters for depth computation")

    def reproject_to_3d(self, disparity: np.ndarray) -> np.ndarray:
        if self.Q is None or self.Q.size == 0:
            raise ValueError("Q matrix is required for 3D reprojection")
        return cv2.reprojectImageTo3D(disparity, self.Q, handleMissingValues=True)


class PointCloudGenerator:
    def __init__(self):
        try:
            import open3d as o3d
            self.o3d = o3d
            self.available = True
        except ImportError:
            self.available = False

    @staticmethod
    def _extract_colors(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            colors_bgr = image[mask]
            colors_rgb = colors_bgr[:, ::-1].astype(np.float64) / 255.0
        else:
            gray = image[mask].astype(np.float64) / 255.0
            colors_rgb = np.stack([gray, gray, gray], axis=1)
        return colors_rgb

    def create_from_disparity(self, image: np.ndarray, disparity: np.ndarray,
                               Q: np.ndarray, max_depth: float = 10.0,
                               confidence: Optional[np.ndarray] = None,
                               min_confidence: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        points_3d = cv2.reprojectImageTo3D(disparity, Q, handleMissingValues=True)
        abs_z = np.abs(points_3d[:, :, 2])
        valid_disp = disparity > 0
        valid_depth = (abs_z > 0) & (abs_z < max_depth)
        mask = valid_disp & valid_depth
        if confidence is not None:
            mask &= confidence >= min_confidence
        points_3d[:, :, 2] = abs_z
        points = points_3d[mask]
        colors_rgb = self._extract_colors(image, mask)
        return points, colors_rgb

    def create_from_depth(self, image: np.ndarray, depth: np.ndarray,
                          Q: np.ndarray, max_depth: float = 10.0,
                          confidence: Optional[np.ndarray] = None,
                          min_confidence: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        points_3d = cv2.reprojectImageTo3D(depth, Q, handleMissingValues=True)
        abs_z = np.abs(points_3d[:, :, 2])
        mask = (depth > 0) & (abs_z > 0) & (abs_z < max_depth)
        if confidence is not None:
            mask &= confidence >= min_confidence
        points_3d[:, :, 2] = np.abs(points_3d[:, :, 2])
        points = points_3d[mask]
        colors_rgb = self._extract_colors(image, mask)
        return points, colors_rgb

    def create_with_original_colors(self, rectified_image: np.ndarray,
                                     original_image: np.ndarray,
                                     disparity: np.ndarray,
                                     Q: np.ndarray,
                                     map_lx: np.ndarray, map_ly: np.ndarray,
                                     max_depth: float = 10.0,
                                     confidence: Optional[np.ndarray] = None,
                                     min_confidence: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        points_3d = cv2.reprojectImageTo3D(disparity, Q, handleMissingValues=True)
        abs_z = np.abs(points_3d[:, :, 2])
        valid_disp = disparity > 0
        valid_depth = (abs_z > 0) & (abs_z < max_depth)
        mask = valid_disp & valid_depth
        if confidence is not None:
            mask &= confidence >= min_confidence
        points_3d[:, :, 2] = abs_z
        points = points_3d[mask]

        h, w = disparity.shape
        yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        src_x = map_lx[mask]
        src_y = map_ly[mask]
        src_x = np.clip(src_x.astype(np.int32), 0, original_image.shape[1] - 1)
        src_y = np.clip(src_y.astype(np.int32), 0, original_image.shape[0] - 1)
        orig_colors_bgr = original_image[src_y, src_x]
        if len(original_image.shape) == 3:
            colors_rgb = orig_colors_bgr[:, ::-1].astype(np.float64) / 255.0
        else:
            gray = orig_colors_bgr.astype(np.float64) / 255.0
            colors_rgb = np.stack([gray, gray, gray], axis=1)

        return points, colors_rgb

    def to_open3d(self, points: np.ndarray, colors: np.ndarray):
        if not self.available:
            raise ImportError("Open3D is not installed. Install with: pip install open3d")
        pcd = self.o3d.geometry.PointCloud()
        pcd.points = self.o3d.utility.Vector3dVector(points)
        pcd.colors = self.o3d.utility.Vector3dVector(colors)
        return pcd

    def visualize(self, pcd) -> None:
        if not self.available:
            raise ImportError("Open3D is not installed")
        self.o3d.visualization.draw_geometries([pcd], window_name="Point Cloud")

    def save(self, pcd, filepath: str) -> None:
        if not self.available:
            raise ImportError("Open3D is not installed")
        self.o3d.io.write_point_cloud(filepath, pcd)

    def save_ply(self, points: np.ndarray, colors: np.ndarray, filepath: str) -> None:
        pcd = self.to_open3d(points, colors)
        self.save(pcd, filepath)


class StereoDepthPipeline:
    def __init__(self, params: StereoParams, sgm_config: Optional[SGMConfig] = None):
        self.params = params
        self.sgm_config = sgm_config or SGMConfig()
        self.rectifier = StereoRectifier(params)
        self.disparity_estimator = AdaptiveSGMDisparity(self.sgm_config)
        self.post_processor = DisparityPostProcessor(self.sgm_config, self.disparity_estimator.matcher)
        self.depth_estimator = DepthEstimator(params.Q)
        self.point_cloud_gen = PointCloudGenerator()
        self._rect_l = None
        self._rect_r = None
        self._original_l = None
        self._confidence = None
        self._dl_refiner = None
        self._sr_enhancer = None
        self._weak_enhancer = None
        self._bilateral_solver = None
        self._rt_stereo = None
        self._init_optional_modules()

    def _init_optional_modules(self):
        c = self.sgm_config
        if c.use_dl_refine:
            dl_config = DLConfig(use_gpu=c.use_gpu, sr_scale=c.sr_scale)
            self._dl_refiner = DeepSGMRefiner(dl_config, device=c.dl_device)
        if c.use_super_res:
            self._sr_enhancer = SREnhancer(scale=c.sr_scale, method=c.sr_method)
        if c.enhance_weak_texture:
            self._weak_enhancer = WeakTextureEnhancer(
                gradient_threshold=c.weak_texture_grad_thresh,
            )
        if c.use_bilateral_solver:
            self._bilateral_solver = FastBilateralSolver()
        if c.use_gpu:
            self._rt_stereo = RealTimeStereo(
                min_disparity=c.min_disparity,
                num_disparities=c.num_disparities,
                block_size=c.block_size,
                target_fps=c.target_fps,
            )

    def rectify(self, img_l: np.ndarray, img_r: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        self._original_l = img_l.copy()
        self._rect_l, self._rect_r = self.rectifier.rectify(img_l, img_r)
        if self.params.Q is not None:
            self.depth_estimator = DepthEstimator(self.params.Q)
        return self._rect_l, self._rect_r

    def estimate_disparity_fast(self, img_l: np.ndarray, img_r: np.ndarray) -> dict:
        if self._rt_stereo is not None:
            return self._rt_stereo.process_frame(img_l, img_r)
        disparity = self.disparity_estimator._base_matcher.compute(img_l, img_r)
        return {"disparity": disparity, "time_ms": 0, "fps": 0, "avg_fps": 0}

    def estimate_disparity(self, img_l: np.ndarray, img_r: np.ndarray,
                           use_lr: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        if use_lr:
            disp_l, disp_r, confidence = self.disparity_estimator.compute_lr(img_l, img_r)
            return disp_l, disp_r, confidence
        disp_l, confidence = self.disparity_estimator.compute(img_l, img_r)
        return disp_l, None, confidence

    def dl_refine_disparity(self, img_l: np.ndarray, img_r: np.ndarray,
                             disp_init: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if self._dl_refiner is None:
            return disp_init, np.ones_like(disp_init)
        return self._dl_refiner.refine_disparity(img_l, img_r, disp_init)

    def enhance_weak_texture(self, img_l: np.ndarray, img_r: np.ndarray,
                              disparity: np.ndarray,
                              confidence: Optional[np.ndarray] = None) -> np.ndarray:
        if self._weak_enhancer is None:
            return disparity
        return self._weak_enhancer.enhance(img_l, img_r, disparity, confidence)

    def post_process(self, img_l: np.ndarray, disp_l: np.ndarray,
                     disp_r: Optional[np.ndarray] = None,
                     confidence: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        return self.post_processor.process(img_l, disp_l, disp_r, confidence)

    def bilateral_solve(self, disparity: np.ndarray, guidance: np.ndarray,
                         confidence: Optional[np.ndarray] = None) -> np.ndarray:
        if self._bilateral_solver is None:
            return disparity
        return self._bilateral_solver.solve(disparity, guidance, confidence)

    def super_resolve_depth(self, depth: np.ndarray,
                             guidance: Optional[np.ndarray] = None) -> np.ndarray:
        if self._sr_enhancer is None:
            return depth
        return self._sr_enhancer.enhance(depth, guidance)

    def compute_depth(self, disparity: np.ndarray, max_depth: float = 0.0) -> np.ndarray:
        return self.depth_estimator.disparity_to_depth(disparity, max_depth)

    def generate_point_cloud(self, image: np.ndarray, disparity: np.ndarray,
                             max_depth: float = 10.0,
                             confidence: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
        if self.params.Q is None:
            raise ValueError("Q matrix not available. Run rectification first.")
        using_sr = (self._original_l is not None and
                    disparity.shape[:2] != self._original_l.shape[:2])
        if (not using_sr and self._original_l is not None
                and self.params.map_lx is not None):
            return self.point_cloud_gen.create_with_original_colors(
                image, self._original_l, disparity, self.params.Q,
                self.params.map_lx, self.params.map_ly,
                max_depth, confidence,
            )
        return self.point_cloud_gen.create_from_disparity(
            image, disparity, self.params.Q, max_depth, confidence,
        )

    def benchmark_gpu(self, img_l: np.ndarray, img_r: np.ndarray,
                       seconds: float = 3.0) -> dict:
        if self._rt_stereo is None:
            return {"fps": 0, "use_cuda": False}
        return self._rt_stereo.benchmark(img_l, img_r, seconds)

    def run(self, img_l: np.ndarray, img_r: np.ndarray,
            use_lr: bool = True, max_depth: float = 10.0) -> dict:
        rect_l, rect_r = self.rectify(img_l, img_r)

        if self.sgm_config.use_gpu and self._rt_stereo is not None:
            fast_result = self.estimate_disparity_fast(rect_l, rect_r)
            disp_l = fast_result["disparity"]
            disp_r = None
            confidence = np.ones_like(disp_l)
            perf = {"fast_ms": fast_result["time_ms"], "fast_fps": fast_result["fps"]}
        else:
            disp_l, disp_r, confidence = self.estimate_disparity(rect_l, rect_r, use_lr=use_lr)
            perf = {}

        disp_filtered, confidence_out = self.post_process(rect_l, disp_l, disp_r, confidence)

        if self.sgm_config.use_dl_refine:
            disp_filtered, dl_conf = self.dl_refine_disparity(rect_l, rect_r, disp_filtered)
            confidence_out = np.minimum(confidence_out, dl_conf)

        if self.sgm_config.enhance_weak_texture:
            disp_filtered = self.enhance_weak_texture(rect_l, rect_r, disp_filtered, confidence_out)

        if self.sgm_config.use_bilateral_solver:
            disp_filtered = self.bilateral_solve(disp_filtered, rect_l, confidence_out)

        self._confidence = confidence_out

        depth = self.compute_depth(disp_filtered, max_depth)

        if self.sgm_config.use_super_res and self._sr_enhancer is not None:
            depth = self.super_resolve_depth(depth, rect_l)
            disp_filtered = cv2.resize(
                disp_filtered, (depth.shape[1], depth.shape[0]),
                interpolation=cv2.INTER_CUBIC,
            )
            confidence_out = cv2.resize(
                confidence_out, (depth.shape[1], depth.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
            rect_l_sr = cv2.resize(
                rect_l, (depth.shape[1], depth.shape[0]),
                interpolation=cv2.INTER_CUBIC,
            )
        else:
            rect_l_sr = rect_l

        points, colors = self.generate_point_cloud(rect_l_sr, disp_filtered, max_depth, confidence_out)

        result = {
            "rectified_left": rect_l,
            "rectified_right": rect_r,
            "disparity_raw": disp_l,
            "disparity_right": disp_r,
            "disparity_filtered": disp_filtered,
            "depth": depth,
            "points_3d": points,
            "colors": colors,
            "confidence": confidence_out,
            "gradient": self.disparity_estimator._grad_mag,
            "performance": perf,
        }
        return result

    def run_with_calibration(self, img_l: np.ndarray, img_r: np.ndarray,
                              camera_matrix_l: np.ndarray, dist_coeffs_l: np.ndarray,
                              camera_matrix_r: np.ndarray, dist_coeffs_r: np.ndarray,
                              R: np.ndarray, T: np.ndarray,
                              image_size: Tuple[int, int],
                              use_lr: bool = True, max_depth: float = 10.0) -> dict:
        self.params = StereoParams(
            camera_matrix_l=camera_matrix_l,
            dist_coeffs_l=dist_coeffs_l,
            camera_matrix_r=camera_matrix_r,
            dist_coeffs_r=dist_coeffs_r,
            R=R, T=T, image_size=image_size,
        )
        self.rectifier = StereoRectifier(self.params)
        self.depth_estimator = DepthEstimator(self.params.Q)
        return self.run(img_l, img_r, use_lr=use_lr, max_depth=max_depth)
