import cv2
import numpy as np
from scipy.ndimage import convolve, gaussian_filter, sobel
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
from mpl_toolkits.mplot3d import Axes3D
import os


class RegionAnalyzer:
    def __init__(self, img):
        self.img = img.astype(np.float32)
        self.grad_x = None
        self.grad_y = None
        self.grad_mag = None
        self.texture_mask = None
        self.smooth_mask = None
        self.edge_mask = None
        self._compute_regions()

    def _compute_regions(self):
        self.grad_x = cv2.Sobel(self.img, cv2.CV_32F, 1, 0, ksize=3)
        self.grad_y = cv2.Sobel(self.img, cv2.CV_32F, 0, 1, ksize=3)
        self.grad_mag = np.sqrt(self.grad_x ** 2 + self.grad_y ** 2)
        p75 = np.percentile(self.grad_mag, 75)
        p25 = np.percentile(self.grad_mag, 25)
        self.edge_mask = self.grad_mag > p75
        self.smooth_mask = self.grad_mag < p25
        self.texture_mask = ~self.edge_mask & ~self.smooth_mask

    def get_gradient_guidance(self, disp):
        grad_disp_x = cv2.Sobel(disp, cv2.CV_32F, 1, 0, ksize=3)
        grad_disp_y = cv2.Sobel(disp, cv2.CV_32F, 0, 1, ksize=3)
        guidance = np.zeros_like(disp)
        sparse_region = self.smooth_mask
        if np.any(sparse_region):
            img_grad_norm_x = np.where(np.abs(self.grad_x) > 1e-6, self.grad_x, 0)
            img_grad_norm_y = np.where(np.abs(self.grad_y) > 1e-6, self.grad_y, 0)
            alignment_x = img_grad_norm_x * grad_disp_x
            alignment_y = img_grad_norm_y * grad_disp_y
            alignment = alignment_x + alignment_y
            reliability = np.minimum(np.abs(self.grad_x), np.abs(self.grad_y))
            reliability = reliability / (reliability.max() + 1e-6)
            guidance = -alignment * reliability * sparse_region.astype(np.float32)
        return guidance

    def compute_region_errors(self, disp_pred, disp_gt, threshold=3):
        if disp_gt is None:
            return None
        mask = disp_gt > 0
        diff = np.abs(disp_pred - disp_gt)
        results = {}
        for name, region_mask in [('texture', self.texture_mask), ('smooth', self.smooth_mask), ('edge', self.edge_mask)]:
            combined = region_mask & mask
            total = np.sum(combined)
            if total == 0:
                results[name] = {'error_rate': 0.0, 'pixels': 0, 'error_pixels': 0}
                continue
            error_pixels = np.sum((diff > threshold) & combined)
            results[name] = {'error_rate': (error_pixels / total) * 100.0, 'pixels': int(total), 'error_pixels': int(error_pixels)}
        results['overall'] = {'error_rate': (np.sum((diff > threshold) & mask) / np.sum(mask)) * 100.0, 'pixels': int(np.sum(mask)), 'error_pixels': int(np.sum((diff > threshold) & mask))}
        return results


class EdgeRefinementNet:
    def __init__(self, img):
        self.img = img.astype(np.float32)
        self.img_norm = self.img / (self.img.max() + 1e-6)
        self.grad_x = cv2.Sobel(self.img_norm, cv2.CV_32F, 1, 0, ksize=3)
        self.grad_y = cv2.Sobel(self.img_norm, cv2.CV_32F, 0, 1, ksize=3)
        self.grad_mag = np.sqrt(self.grad_x ** 2 + self.grad_y ** 2)
        self.edge_strength = np.clip(self.grad_mag / (self.grad_mag.max() + 1e-6) * 3.0, 0, 1)

    def refine(self, disp, iterations=10, edge_weight=1.0, lr=0.5):
        d = disp.astype(np.float32).copy()
        disp_max = d.max() if d.max() > 0 else 1

        gx = self.grad_x
        gy = self.grad_y
        gm2 = gx ** 2 + gy ** 2 + 1e-8

        for it in range(iterations):
            dx = cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3)
            dy = cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3)

            proj = (dx * gx + dy * gy) / gm2
            misalign_x = dx - proj * gx
            misalign_y = dy - proj * gy
            misalign_mag = np.sqrt(misalign_x ** 2 + misalign_y ** 2)

            proj_x = proj * gx
            proj_y = proj * gy

            sign = np.sign(proj)
            edge_local_scale = np.abs(proj + 1e-6) * disp_max * 0.5
            target_scale = sign * edge_local_scale

            correction = misalign_mag * edge_weight * self.edge_strength * lr * 0.02

            gx_hat = gx / (np.sqrt(gm2) + 1e-6)
            gy_hat = gy / (np.sqrt(gm2) + 1e-6)

            edge_dir_x = -gy_hat
            edge_dir_y = gx_hat

            perp_component = misalign_x * edge_dir_x + misalign_y * edge_dir_y

            shift = np.sign(perp_component) * correction

            d = d + shift

            d = cv2.GaussianBlur(d, (3, 3), 0.5) * self.edge_strength * 0.3 + d * (1 - self.edge_strength * 0.3)

            d = np.clip(d, 0, None)

        return d


class HoleFiller:
    def __init__(self, img):
        self.img = img.astype(np.float32)
        self.prev_disp = None
        self.next_disp = None

    def set_temporal_frames(self, prev_disp=None, next_disp=None):
        self.prev_disp = prev_disp
        self.next_disp = next_disp

    def fill_holes(self, disp, hole_threshold=0.5, spatial_weight=1.0, temporal_weight=0.3):
        valid = disp > hole_threshold
        filled = disp.copy()
        holes = ~valid

        if not np.any(holes):
            return filled

        filled = self._multi_direction_interpolation(filled, valid)

        if temporal_weight > 0 and (self.prev_disp is not None or self.next_disp is not None):
            filled = self._temporal_filling(filled, disp, valid, temporal_weight)

        if spatial_weight > 0 and np.any(holes):
            mask = holes.astype(np.uint8)
            filled_8u = np.clip(filled, 0, 255).astype(np.uint8)
            radius = 5
            filled_8u = cv2.inpaint(filled_8u, mask * 255, radius, cv2.INPAINT_NS)
            inpainted = filled_8u.astype(np.float32)
            blend = holes.astype(np.float32) * spatial_weight
            filled = filled * (1 - blend) + inpainted * blend

        return filled

    def _multi_direction_interpolation(self, disp, valid):
        filled = disp.copy()
        h, w = disp.shape
        valid_map = valid.copy()

        for direction in ['left', 'right', 'up', 'down']:
            scan = filled.copy()
            if direction == 'left':
                for x in range(1, w):
                    hole_pixels = ~valid_map[:, x] & valid_map[:, x - 1]
                    scan[hole_pixels, x] = scan[hole_pixels, x - 1]
                    valid_map[hole_pixels, x] = True
            elif direction == 'right':
                for x in range(w - 2, -1, -1):
                    hole_pixels = ~valid_map[:, x] & valid_map[:, x + 1]
                    scan[hole_pixels, x] = scan[hole_pixels, x + 1]
                    valid_map[hole_pixels, x] = True
            elif direction == 'up':
                for y in range(1, h):
                    hole_pixels = ~valid_map[y, :] & valid_map[y - 1, :]
                    scan[y, hole_pixels] = scan[y - 1, hole_pixels]
                    valid_map[y, hole_pixels] = True
            elif direction == 'down':
                for y in range(h - 2, -1, -1):
                    hole_pixels = ~valid_map[y, :] & valid_map[y + 1, :]
                    scan[y, hole_pixels] = scan[y + 1, hole_pixels]
                    valid_map[y, hole_pixels] = True
            filled = scan

        return filled

    def _temporal_filling(self, filled, disp, valid, temporal_weight):
        result = filled.copy()
        holes = ~valid

        for frame in [self.prev_disp, self.next_disp]:
            if frame is not None:
                f_h, f_w = frame.shape[:2]
                d_h, d_w = disp.shape[:2]
                min_h, min_w = min(f_h, d_h), min(f_w, d_w)
                frame_crop = frame[:min_h, :min_w]
                holes_crop = holes[:min_h, :min_w]
                if np.any(holes_crop):
                    temporal_vals = frame_crop[holes_crop]
                    blend = holes_crop.astype(np.float32) * temporal_weight
                    result[:min_h, :min_w] = result[:min_h, :min_w] * (1 - blend) + frame_crop * blend

        return result

    def generate_temporal_frames(self, gt_disp, motion_strength=2.0):
        h, w = gt_disp.shape
        y, x = np.ogrid[:h, :w]
        flow_x = motion_strength * np.sin(y / 30.0) * np.cos(x / 40.0)
        flow_y = motion_strength * np.cos(y / 25.0) * np.sin(x / 35.0)

        map_x = x.astype(np.float32) + flow_x
        map_y = y.astype(np.float32) + flow_y
        map_x = np.clip(map_x, 0, w - 1).astype(np.float32)
        map_y = np.clip(map_y, 0, h - 1).astype(np.float32)

        prev_disp = cv2.remap(gt_disp, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        map_x2 = x.astype(np.float32) - flow_x
        map_y2 = y.astype(np.float32) - flow_y
        map_x2 = np.clip(map_x2, 0, w - 1).astype(np.float32)
        map_y2 = np.clip(map_y2, 0, h - 1).astype(np.float32)

        next_disp = cv2.remap(gt_disp, map_x2, map_y2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        self.set_temporal_frames(prev_disp, next_disp)
        return prev_disp, next_disp


class PointCloudGenerator:
    def __init__(self, fx=500, fy=500, cx=None, cy=None, baseline=0.1):
        self.fx = fx
        self.fy = fy
        self.baseline = baseline
        self.cx = cx
        self.cy = cy
        self.points_3d = None
        self.colors = None

    def generate(self, disp, img, valid_threshold=0.5):
        h, w = disp.shape
        if self.cx is None:
            self.cx = w / 2.0
        if self.cy is None:
            self.cy = h / 2.0

        valid = disp > valid_threshold
        ys, xs = np.where(valid)
        disps = disp[valid]

        Z = (self.fx * self.baseline) / (disps + 1e-6)
        Z = np.clip(Z, 0.01, 100.0)
        X = (xs - self.cx) * Z / self.fx
        Y = (ys - self.cy) * Z / self.fy

        self.points_3d = np.stack([X, Y, Z], axis=1)

        if img.ndim == 2:
            self.colors = np.stack([img[valid]] * 3, axis=1).astype(np.float32) / 255.0
        else:
            self.colors = img[valid].astype(np.float32) / 255.0

        return self.points_3d, self.colors

    def measure_distance(self, pt1_idx, pt2_idx):
        if self.points_3d is None:
            return None
        p1 = self.points_3d[pt1_idx]
        p2 = self.points_3d[pt2_idx]
        return float(np.linalg.norm(p1 - p2))

    def measure_area(self, indices):
        if self.points_3d is None or len(indices) < 3:
            return None
        pts = self.points_3d[indices]
        center = pts.mean(axis=0)
        total_area = 0.0
        for i in range(1, len(pts) - 1):
            v1 = pts[i] - center
            v2 = pts[i + 1] - center
            cross = np.cross(v1, v2)
            total_area += np.linalg.norm(cross) / 2.0
        return float(total_area)

    def measure_volume(self, indices, reference_z=None):
        if self.points_3d is None or len(indices) < 3:
            return None
        pts = self.points_3d[indices]
        if reference_z is None:
            reference_z = pts[:, 2].max()
        total_volume = 0.0
        center_xy = pts[:, :2].mean(axis=0)
        for i in range(1, len(pts) - 1):
            tri = pts[[0, i, i + 1]]
            area_2d = 0.5 * abs((tri[1, 0] - tri[0, 0]) * (tri[2, 1] - tri[0, 1]) - (tri[2, 0] - tri[0, 0]) * (tri[1, 1] - tri[0, 1]))
            height = reference_z - tri[:, 2].mean()
            total_volume += area_2d * abs(height) / 3.0
        return float(total_volume)

    def get_statistics(self):
        if self.points_3d is None:
            return None
        stats = {
            'num_points': len(self.points_3d),
            'x_range': (float(self.points_3d[:, 0].min()), float(self.points_3d[:, 0].max())),
            'y_range': (float(self.points_3d[:, 1].min()), float(self.points_3d[:, 1].max())),
            'z_range': (float(self.points_3d[:, 2].min()), float(self.points_3d[:, 2].max())),
            'z_mean': float(self.points_3d[:, 2].mean()),
            'z_std': float(self.points_3d[:, 2].std()),
        }
        corner_indices = self._get_corner_indices()
        if corner_indices is not None:
            stats['scene_width'] = self.measure_distance(corner_indices[0], corner_indices[1])
            stats['scene_height'] = self.measure_distance(corner_indices[0], corner_indices[2])
        return stats

    def _get_corner_indices(self):
        if self.points_3d is None:
            return None
        n = len(self.points_3d)
        if n < 4:
            return None
        step = max(1, n // 20)
        candidates = list(range(0, n, step))[:20]
        return candidates[:4]


class DisparityOptimizer:
    def __init__(self, left_img_path=None, right_img_path=None, gt_path=None):
        self.left_img = None
        self.right_img = None
        self.gt_disp = None
        self.initial_disp = None
        self.optimized_disp = None
        self.region_analyzer = None
        self.energy_history = []
        self.edge_refiner = None
        self.hole_filler = None
        self.point_cloud_gen = None

        self.load_images(left_img_path, right_img_path, gt_path)

        self.bf_params = {'d': 9, 'sigma_color': 75, 'sigma_space': 75, 'gradient_weight': 0.3}
        self.gf_params = {'r': 8, 'eps': 0.1, 'gradient_weight': 0.3}
        self.bp_params = {'iterations': 10, 'data_weight': 0.15, 'smooth_weight': 0.8, 'disp_levels': 16, 'convergence_threshold': 0.005, 'gradient_weight': 0.3}
        self.dl_params = {'iterations': 10, 'lr': 0.5, 'edge_weight': 1.0, 'gradient_weight': 0.3}
        self.hf_params = {'hole_threshold': 0.5, 'spatial_weight': 1.0, 'temporal_weight': 0.3}

    def load_images(self, left_path, right_path, gt_path=None):
        if gt_path and os.path.exists(gt_path):
            self.gt_disp = cv2.imread(gt_path, cv2.IMREAD_GRAYSCALE).astype(np.float32)
            self.gt_disp = self.gt_disp / 16.0 if self.gt_disp.max() > 100 else self.gt_disp
        else:
            self.gt_disp = self.generate_ground_truth()
        if left_path and os.path.exists(left_path) and right_path and os.path.exists(right_path):
            self.left_img = cv2.imread(left_path, cv2.IMREAD_GRAYSCALE)
            self.right_img = cv2.imread(right_path, cv2.IMREAD_GRAYSCALE)
        else:
            self.left_img, self.right_img = self.generate_stereo_images()
        if self.left_img.shape != self.right_img.shape:
            h, w = min(self.left_img.shape[0], self.right_img.shape[0]), min(self.left_img.shape[1], self.right_img.shape[1])
            self.left_img = self.left_img[:h, :w]
            self.right_img = self.right_img[:h, :w]
            if self.gt_disp is not None:
                self.gt_disp = self.gt_disp[:h, :w]
        self.region_analyzer = RegionAnalyzer(self.left_img)
        self.edge_refiner = EdgeRefinementNet(self.left_img)
        self.hole_filler = HoleFiller(self.left_img)
        self.hole_filler.generate_temporal_frames(self.gt_disp)
        self.point_cloud_gen = PointCloudGenerator()

    def generate_ground_truth(self):
        h, w = 200, 300
        gt = np.ones((h, w), dtype=np.float32) * 5
        gt[30:80, 40:90] = 35
        gt[40:130, 150:230] = 25
        y, x = np.ogrid[:h, :w]
        dist = np.sqrt((x - 150) ** 2 + (y - 100) ** 2)
        gt[dist < 40] = 18
        for i in range(5):
            x_pos = 50 + i * 50
            gt[150:180, x_pos:x_pos + 30] = 10 + i * 3
        gt = gaussian_filter(gt, sigma=1.5)
        return gt

    def generate_stereo_images(self):
        h, w = self.gt_disp.shape
        y, x = np.ogrid[:h, :w]
        left_img = (128 + 40 * np.sin(y / 20.0) * np.cos(x / 25.0)).astype(np.uint8)
        cv2.rectangle(left_img, (40, 30), (90, 80), 220, -1)
        cv2.rectangle(left_img, (150, 40), (230, 130), 100, -1)
        cv2.circle(left_img, (150, 100), 40, 160, -1)
        for i in range(5):
            x_pos = 50 + i * 50
            cv2.rectangle(left_img, (x_pos, 150), (x_pos + 30, 180), 80 + i * 20, -1)
        left_img = gaussian_filter(left_img, sigma=0.8).astype(np.uint8)
        right_img = np.zeros_like(left_img, dtype=np.uint8)
        for row in range(h):
            for col in range(w):
                d = int(self.gt_disp[row, col])
                src_col = col - d
                if 0 <= src_col < w:
                    right_img[row, col] = left_img[row, src_col]
                else:
                    right_img[row, col] = 128
        return left_img, right_img

    def compute_initial_disparity(self, noise_level=5.0):
        self.initial_disp = self.gt_disp.copy()
        noise = np.random.normal(0, noise_level, self.gt_disp.shape)
        self.initial_disp += noise
        self.initial_disp = np.clip(self.initial_disp, 0, None)
        outlier_mask = np.random.random(self.initial_disp.shape) < 0.1
        self.initial_disp[outlier_mask] = 0
        return self.initial_disp

    def bilateral_filter(self, disp, d=9, sigma_color=75, sigma_space=75, gradient_weight=0.3):
        disp_norm = cv2.normalize(disp, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        result = cv2.bilateralFilter(disp_norm, d, sigma_color, sigma_space)
        result = result.astype(np.float32)
        if disp.max() > 0:
            result = result * (disp.max() / 255.0)
        if gradient_weight > 0 and self.region_analyzer is not None:
            guidance = self.region_analyzer.get_gradient_guidance(disp)
            smooth_region = self.region_analyzer.smooth_mask.astype(np.float32)
            result = result + gradient_weight * guidance * (disp.max() / 255.0)
            result = np.clip(result, 0, None)
            reliable_grad_mask = (self.region_analyzer.grad_mag > np.percentile(self.region_analyzer.grad_mag, 50)).astype(np.float32)
            blend = smooth_region * gradient_weight
            result = result * (1 - blend) + disp * blend * reliable_grad_mask + result * blend * (1 - reliable_grad_mask)
            result = np.clip(result, 0, None)
        return result

    def guided_filter(self, disp, r=8, eps=0.1, gradient_weight=0.3):
        I = self.left_img.astype(np.float32) / 255.0
        p = disp.astype(np.float32)
        max_p = p.max() if p.max() > 0 else 1
        p = p / max_p
        if gradient_weight > 0 and self.region_analyzer is not None:
            grad_mag_norm = self.region_analyzer.grad_mag / (self.region_analyzer.grad_mag.max() + 1e-6)
            texture_confidence = np.clip(grad_mag_norm * 3.0, 0, 1)
            p_confident = p * (1 - gradient_weight * (1 - texture_confidence) * self.region_analyzer.smooth_mask.astype(np.float32))
            p = p_confident
        mean_I = cv2.boxFilter(I, cv2.CV_32F, (r, r))
        mean_p = cv2.boxFilter(p, cv2.CV_32F, (r, r))
        mean_Ip = cv2.boxFilter(I * p, cv2.CV_32F, (r, r))
        cov_Ip = mean_Ip - mean_I * mean_p
        mean_II = cv2.boxFilter(I * I, cv2.CV_32F, (r, r))
        var_I = mean_II - mean_I * mean_I
        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I
        mean_a = cv2.boxFilter(a, cv2.CV_32F, (r, r))
        mean_b = cv2.boxFilter(b, cv2.CV_32F, (r, r))
        q = mean_a * I + mean_b
        q = q * max_p
        return q

    def belief_propagation(self, disp, iterations=10, data_weight=0.15, smooth_weight=0.8, disp_levels=16, convergence_threshold=0.005, gradient_weight=0.3):
        h, w = disp.shape
        L = disp_levels
        scale = L / (disp.max() + 1e-6)
        disp_norm = disp * scale
        d_labels = np.arange(L, dtype=np.float32)
        data_cost = np.abs(disp_norm[:, :, None] - d_labels[None, None, :]) * data_weight
        if gradient_weight > 0 and self.region_analyzer is not None:
            grad_mag_norm = self.region_analyzer.grad_mag / (self.region_analyzer.grad_mag.max() + 1e-6)
            texture_confidence = np.clip(grad_mag_norm * 5.0, 0, 1)
            smooth_confidence = 1.0 - texture_confidence
            smooth_penalties = np.abs(d_labels[None, None, :] - disp_norm[:, :, None]) * gradient_weight * smooth_confidence[:, :, None]
            data_cost += smooth_penalties * 0.1
            gradient_guidance = self.region_analyzer.get_gradient_guidance(disp)
            guidance_cost = np.abs(gradient_guidance[:, :, None] - d_labels[None, None, :] * 0.01) * gradient_weight * smooth_confidence[:, :, None]
            data_cost += guidance_cost * 0.05
        msg = np.zeros((4, h, w, L), dtype=np.float32)
        self.energy_history = []
        prev_energy = None
        for it in range(iterations):
            new_msg = np.zeros_like(msg)
            for d_send in range(4):
                d_exclude = (d_send + 2) % 4
                belief_no_exclude = data_cost.copy()
                for d_in in range(4):
                    if d_in != d_exclude:
                        belief_no_exclude += msg[d_in]
                if d_send == 0:
                    shifted = np.roll(belief_no_exclude, -1, axis=1); shifted[:, -1, :] = 1e6
                elif d_send == 1:
                    shifted = np.roll(belief_no_exclude, -1, axis=0); shifted[-1, :, :] = 1e6
                elif d_send == 2:
                    shifted = np.roll(belief_no_exclude, 1, axis=1); shifted[:, 0, :] = 1e6
                else:
                    shifted = np.roll(belief_no_exclude, 1, axis=0); shifted[0, :, :] = 1e6
                shifted_min = np.min(shifted, axis=2, keepdims=True)
                shifted_norm = shifted - shifted_min
                forward = np.empty_like(shifted_norm)
                forward[:, :, 0] = shifted_norm[:, :, 0]
                for d in range(1, L):
                    forward[:, :, d] = np.minimum(forward[:, :, d - 1] + smooth_weight, shifted_norm[:, :, d])
                backward = np.empty_like(shifted_norm)
                backward[:, :, -1] = shifted_norm[:, :, -1]
                for d in range(L - 2, -1, -1):
                    backward[:, :, d] = np.minimum(backward[:, :, d + 1] + smooth_weight, shifted_norm[:, :, d])
                new_msg[d_send] = np.minimum(forward, backward)
            msg = 0.5 * msg + 0.5 * new_msg
            belief = data_cost.copy()
            for d_in in range(4):
                belief += msg[d_in]
            current_energy = float(np.sum(np.min(belief, axis=2)))
            self.energy_history.append(current_energy)
            if prev_energy is not None and convergence_threshold > 0:
                energy_change = abs(prev_energy - current_energy) / (abs(prev_energy) + 1e-10)
                if energy_change < convergence_threshold:
                    break
            prev_energy = current_energy
        belief = data_cost.copy()
        for d_in in range(4):
            belief += msg[d_in]
        optimized = np.argmin(belief, axis=2).astype(np.float32)
        if disp.max() > 0:
            optimized = optimized / scale
        return optimized

    def dl_edge_refine(self, disp, iterations=10, lr=0.5, edge_weight=1.0, gradient_weight=0.3):
        if self.edge_refiner is None:
            self.edge_refiner = EdgeRefinementNet(self.left_img)

        refined = self.edge_refiner.refine(disp, iterations=iterations, edge_weight=edge_weight, lr=lr)

        disp_input = disp.astype(np.float32)
        disp_max = disp_input.max() if disp_input.max() > 0 else 1

        diff = np.abs(refined - disp_input)
        threshold = disp_max * 0.02
        large_change = diff > threshold

        safe_refined = refined.copy()
        safe_refined[large_change] = disp_input[large_change]

        alpha = self.edge_refiner.edge_strength
        alpha = alpha / (alpha.max() + 1e-6) * 0.5
        result = disp_input * (1 - alpha) + safe_refined * alpha

        if gradient_weight > 0 and self.region_analyzer is not None:
            edge_att = self.edge_refiner.edge_strength
            non_edge = 1.0 - edge_att
            smooth_region = self.region_analyzer.smooth_mask.astype(np.float32)
            bf_temp = self.bilateral_filter(disp_input, d=9, sigma_color=75, sigma_space=75, gradient_weight=0)
            smooth_blend = smooth_region * non_edge * gradient_weight
            result = result * (1 - smooth_blend) + bf_temp * smooth_blend

        return np.clip(result, 0, None)

    def fill_disparity_holes(self, disp, hole_threshold=0.5, spatial_weight=1.0, temporal_weight=0.3):
        if self.hole_filler is None:
            self.hole_filler = HoleFiller(self.left_img)
            self.hole_filler.generate_temporal_frames(self.gt_disp)
        return self.hole_filler.fill_holes(disp, hole_threshold, spatial_weight, temporal_weight)

    def generate_point_cloud(self, disp, valid_threshold=0.5):
        if self.point_cloud_gen is None:
            self.point_cloud_gen = PointCloudGenerator()
        return self.point_cloud_gen.generate(disp, self.left_img, valid_threshold)

    def compute_error_rate(self, disp_pred, disp_gt, threshold=3):
        if disp_gt is None:
            return None
        mask = disp_gt > 0
        diff = np.abs(disp_pred - disp_gt)
        error_pixels = np.sum((diff > threshold) & mask)
        total_pixels = np.sum(mask)
        if total_pixels == 0:
            return 0.0
        return (error_pixels / total_pixels) * 100.0

    def compute_region_error_rates(self, disp_pred, disp_gt, threshold=3):
        if self.region_analyzer is None or disp_gt is None:
            return None
        return self.region_analyzer.compute_region_errors(disp_pred, disp_gt, threshold)

    def optimize(self, method='bilateral', **kwargs):
        if self.initial_disp is None:
            self.compute_initial_disparity()
        self.energy_history = []
        if method == 'bilateral':
            params = {**self.bf_params, **kwargs}
            self.optimized_disp = self.bilateral_filter(self.initial_disp, **params)
        elif method == 'guided':
            params = {**self.gf_params, **kwargs}
            self.optimized_disp = self.guided_filter(self.initial_disp, **params)
        elif method == 'bp':
            params = {**self.bp_params, **kwargs}
            self.optimized_disp = self.belief_propagation(self.initial_disp, **params)
        elif method == 'dl_edge':
            params = {**self.dl_params, **kwargs}
            self.optimized_disp = self.dl_edge_refine(self.initial_disp, **params)
        else:
            raise ValueError(f"Unknown method: {method}")
        return self.optimized_disp


class InteractiveTuner:
    def __init__(self, optimizer):
        self.optimizer = optimizer
        self.current_method = 'bilateral'
        self.show_pointcloud = False
        self.updating = False
        if self.optimizer.initial_disp is None:
            self.optimizer.compute_initial_disparity()
        self.fig = plt.figure(figsize=(20, 13))
        self.setup_ui()
        self.update_display()

    def setup_ui(self):
        gs = self.fig.add_gridspec(3, 5, hspace=0.35, wspace=0.25, left=0.04, right=0.97, top=0.95, bottom=0.30)
        self.ax_left = self.fig.add_subplot(gs[0, 0])
        self.ax_right = self.fig.add_subplot(gs[0, 1])
        self.ax_initial = self.fig.add_subplot(gs[0, 2])
        self.ax_optimized = self.fig.add_subplot(gs[0, 3])
        self.ax_filled = self.fig.add_subplot(gs[0, 4])
        self.ax_gt = self.fig.add_subplot(gs[1, 0])
        self.ax_error = self.fig.add_subplot(gs[1, 1])
        self.ax_region = self.fig.add_subplot(gs[1, 2])
        self.ax_energy = self.fig.add_subplot(gs[1, 3])
        self.ax_cloud = self.fig.add_subplot(gs[1, 4], projection='3d')
        self.ax_method = plt.axes([0.04, 0.07, 0.12, 0.17])
        self.method_radio = RadioButtons(self.ax_method, ('Bilateral', 'Guided', 'BP', 'DL Edge'), active=0)
        self.method_radio.on_clicked(self.on_method_change)
        self.slider_ax1 = plt.axes([0.22, 0.19, 0.42, 0.022])
        self.slider_ax2 = plt.axes([0.22, 0.15, 0.42, 0.022])
        self.slider_ax3 = plt.axes([0.22, 0.11, 0.42, 0.022])
        self.slider_ax4 = plt.axes([0.22, 0.07, 0.42, 0.022])
        self.slider_ax5 = plt.axes([0.22, 0.03, 0.42, 0.022])
        self.slider1 = Slider(self.slider_ax1, 'Param 1', 1, 20, valinit=9, valstep=1)
        self.slider2 = Slider(self.slider_ax2, 'Param 2', 10, 200, valinit=75, valstep=5)
        self.slider3 = Slider(self.slider_ax3, 'Param 3', 10, 200, valinit=75, valstep=5)
        self.slider4 = Slider(self.slider_ax4, 'Grad Weight', 0.0, 1.0, valinit=0.3, valstep=0.05)
        self.slider5 = Slider(self.slider_ax5, 'Temporal Wt', 0.0, 1.0, valinit=0.3, valstep=0.05)
        for s in [self.slider1, self.slider2, self.slider3, self.slider4, self.slider5]:
            s.on_changed(self.on_slider_change)
        self.reset_ax = plt.axes([0.75, 0.03, 0.07, 0.04])
        self.reset_btn = Button(self.reset_ax, 'Reset')
        self.reset_btn.on_clicked(self.reset_params)
        self.cloud_ax = plt.axes([0.85, 0.03, 0.10, 0.04])
        self.cloud_btn = Button(self.cloud_ax, '3D Cloud')
        self.cloud_btn.on_clicked(self.toggle_cloud)
        self.update_slider_labels()

    def update_slider_labels(self):
        self.updating = True
        if self.current_method == 'bilateral':
            self.slider1.label.set_text('d (Kernel)'); self.slider1.set_val(9)
            self.slider2.label.set_text('sigma_color'); self.slider2.set_val(75)
            self.slider3.label.set_text('sigma_space'); self.slider3.set_val(75)
        elif self.current_method == 'guided':
            self.slider1.label.set_text('r (Radius)'); self.slider1.set_val(8)
            self.slider2.label.set_text('eps'); self.slider2.set_val(0.1)
            self.slider3.label.set_text('N/A'); self.slider3.set_val(0)
        elif self.current_method == 'bp':
            self.slider1.label.set_text('Max Iters'); self.slider1.set_val(10)
            self.slider2.label.set_text('Data Wt'); self.slider2.set_val(0.15)
            self.slider3.label.set_text('Smooth Wt'); self.slider3.set_val(0.8)
        elif self.current_method == 'dl_edge':
            self.slider1.label.set_text('DL Iters'); self.slider1.set_val(10)
            self.slider2.label.set_text('LR'); self.slider2.set_val(0.5)
            self.slider3.label.set_text('Edge Wt'); self.slider3.set_val(1.0)
            self.slider4.set_val(0.3)
        self.slider5.set_val(0.3)
        self.updating = False

    def on_method_change(self, label):
        method_map = {'Bilateral': 'bilateral', 'Guided': 'guided', 'BP': 'bp', 'DL Edge': 'dl_edge'}
        self.current_method = method_map[label]
        self.update_slider_labels()
        self.update_display()

    def reset_params(self, event):
        self.optimizer.compute_initial_disparity()
        self.update_slider_labels()
        self.update_display()

    def toggle_cloud(self, event):
        self.show_pointcloud = not self.show_pointcloud
        self.update_display()

    def on_slider_change(self, val):
        if not self.updating:
            self.update_display()

    def update_display(self):
        p1, p2, p3, gw, tw = self.slider1.val, self.slider2.val, self.slider3.val, self.slider4.val, self.slider5.val
        if self.current_method == 'bilateral':
            optimized = self.optimizer.optimize('bilateral', d=int(p1), sigma_color=p2, sigma_space=p3, gradient_weight=gw)
        elif self.current_method == 'guided':
            optimized = self.optimizer.optimize('guided', r=int(p1), eps=p2, gradient_weight=gw)
        elif self.current_method == 'bp':
            optimized = self.optimizer.optimize('bp', iterations=int(p1), data_weight=p2, smooth_weight=p3, gradient_weight=gw)
        elif self.current_method == 'dl_edge':
            optimized = self.optimizer.optimize('dl_edge', iterations=int(p1), lr=p2, edge_weight=p3, gradient_weight=gw)
        filled = self.optimizer.fill_disparity_holes(optimized, temporal_weight=tw)
        disp_max = max(self.optimizer.initial_disp.max(), filled.max(), self.optimizer.gt_disp.max())

        self.ax_left.clear(); self.ax_left.imshow(self.optimizer.left_img, cmap='gray'); self.ax_left.set_title('Left'); self.ax_left.axis('off')
        self.ax_right.clear(); self.ax_right.imshow(self.optimizer.right_img, cmap='gray'); self.ax_right.set_title('Right'); self.ax_right.axis('off')
        self.ax_initial.clear(); self.ax_initial.imshow(self.optimizer.initial_disp, cmap='jet', vmin=0, vmax=disp_max); self.ax_initial.set_title('Initial'); self.ax_initial.axis('off')
        self.ax_optimized.clear(); self.ax_optimized.imshow(optimized, cmap='jet', vmin=0, vmax=disp_max); self.ax_optimized.set_title(f'Optimized ({self.current_method})'); self.ax_optimized.axis('off')
        self.ax_filled.clear(); self.ax_filled.imshow(filled, cmap='jet', vmin=0, vmax=disp_max); self.ax_filled.set_title('Hole-Filled'); self.ax_filled.axis('off')
        self.ax_gt.clear(); self.ax_gt.imshow(self.optimizer.gt_disp, cmap='jet', vmin=0, vmax=disp_max); self.ax_gt.set_title('Ground Truth'); self.ax_gt.axis('off')

        error_map = np.abs(filled - self.optimizer.gt_disp)
        self.ax_error.clear(); im = self.ax_error.imshow(error_map, cmap='hot', vmin=0, vmax=10); self.ax_error.set_title('Error'); self.ax_error.axis('off')
        plt.colorbar(im, ax=self.ax_error, shrink=0.7)

        ra = self.optimizer.region_analyzer
        self.ax_region.clear()
        region_vis = np.zeros((*ra.grad_mag.shape, 3), dtype=np.uint8)
        region_vis[ra.texture_mask] = [0, 200, 0]; region_vis[ra.smooth_mask] = [0, 0, 200]; region_vis[ra.edge_mask] = [200, 0, 0]
        self.ax_region.imshow(region_vis); self.ax_region.set_title('Regions'); self.ax_region.axis('off')

        self.ax_energy.clear()
        if self.optimizer.energy_history:
            e = self.optimizer.energy_history
            self.ax_energy.plot(range(1, len(e) + 1), e, 'b-o', markersize=3)
            self.ax_energy.set_xlabel('Iter'); self.ax_energy.set_ylabel('Energy'); self.ax_energy.set_title(f'Convergence ({len(e)})'); self.ax_energy.grid(True, alpha=0.3)
        else:
            self.ax_energy.text(0.5, 0.5, 'N/A', transform=self.ax_energy.transAxes, ha='center', fontsize=10); self.ax_energy.set_title('Energy'); self.ax_energy.axis('off')

        self.ax_cloud.clear()
        if self.show_pointcloud:
            pts, colors = self.optimizer.generate_point_cloud(filled)
            if pts is not None and len(pts) > 0:
                step = max(1, len(pts) // 2000)
                pts_s, cols_s = pts[::step], colors[::step]
                self.ax_cloud.scatter(pts_s[:, 0], pts_s[:, 1], pts_s[:, 2], c=cols_s, s=1, alpha=0.6)
                self.ax_cloud.set_xlabel('X'); self.ax_cloud.set_ylabel('Y'); self.ax_cloud.set_zlabel('Z')
                stats = self.optimizer.point_cloud_gen.get_statistics()
                title = '3D Point Cloud'
                if stats:
                    title += f'\nZ: {stats["z_mean"]:.2f}+/-{stats["z_std"]:.2f}m'
                self.ax_cloud.set_title(title, fontsize=9)
        else:
            self.ax_cloud.text(0.5, 0.5, 'Click\n"3D Cloud"\nto view', transform=self.ax_cloud.transAxes, ha='center', va='center', fontsize=10)
            self.ax_cloud.set_title('3D Point Cloud')

        init_err = self.optimizer.compute_error_rate(self.optimizer.initial_disp, self.optimizer.gt_disp)
        opt_err = self.optimizer.compute_error_rate(optimized, self.optimizer.gt_disp)
        fill_err = self.optimizer.compute_error_rate(filled, self.optimizer.gt_disp)
        region_errors = self.optimizer.compute_region_error_rates(filled, self.optimizer.gt_disp)

        for txt in self.fig.texts:
            txt.remove()

        self.fig.text(0.5, 0.27, f"Init: {init_err:.1f}% | Optimized: {opt_err:.1f}% | Filled: {fill_err:.1f}% | Improve: {init_err - fill_err:.1f}%", ha='center', fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        if region_errors:
            rt = ""
            for rn, dn in [('texture', 'Tex'), ('smooth', 'Smo'), ('edge', 'Edg')]:
                rt += f"{dn}: {region_errors[rn]['error_rate']:.1f}%  "
            self.fig.text(0.5, 0.24, rt, ha='center', fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        if self.show_pointcloud and self.optimizer.point_cloud_gen is not None:
            stats = self.optimizer.point_cloud_gen.get_statistics()
            if stats:
                mt = f"Points: {stats['num_points']} | Z range: [{stats['z_range'][0]:.2f}, {stats['z_range'][1]:.2f}]m"
                if 'scene_width' in stats:
                    mt += f" | W: {stats['scene_width']:.2f}m H: {stats['scene_height']:.2f}m"
                self.fig.text(0.5, 0.01, mt, ha='center', fontsize=8, bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.8))

        self.fig.canvas.draw_idle()

    def show(self):
        plt.show()


def main():
    print("=" * 60)
    print("Disparity Map Optimization System (v3.0)")
    print("=" * 60)
    optimizer = DisparityOptimizer()
    print("\nGenerating initial disparity...")
    optimizer.compute_initial_disparity()
    init_err = optimizer.compute_error_rate(optimizer.initial_disp, optimizer.gt_disp)
    print(f"Initial Error: {init_err:.2f}%")

    for method_name, method_key, extra_kw in [
        ('Bilateral', 'bilateral', {}),
        ('Guided Filter', 'guided', {}),
        ('Belief Propagation', 'bp', {'iterations': 8}),
        ('DL Edge Refine', 'dl_edge', {'iterations': 3}),
    ]:
        optimizer.compute_initial_disparity()
        result = optimizer.optimize(method_key, **extra_kw)
        filled = optimizer.fill_disparity_holes(result)
        err = optimizer.compute_error_rate(filled, optimizer.gt_disp)
        print(f"{method_name}: {err:.2f}% (improvement: {init_err - err:.2f}%)")

    print("\nLaunching interactive tuner...")
    tuner = InteractiveTuner(optimizer)
    tuner.show()


if __name__ == '__main__':
    main()
