import numpy as np
import cv2


class DepthSuperResolution:
    def __init__(self, method="bilinear_guided", scale_factor=2, guided_radius=8, guided_eps=0.01):
        self.method = method
        self.scale_factor = scale_factor
        self.guided_radius = guided_radius
        self.guided_eps = guided_eps

    def upsample(self, depth_low, guidance_rgb=None, target_size=None):
        if depth_low is None or depth_low.size == 0:
            return None

        h_low, w_low = depth_low.shape[:2]

        if target_size is None:
            h_target = int(h_low * self.scale_factor)
            w_target = int(w_low * self.scale_factor)
        else:
            h_target, w_target = target_size

        if self.method == "nearest":
            return self._upsample_nearest(depth_low, (w_target, h_target))
        elif self.method == "bilinear":
            return self._upsample_bilinear(depth_low, (w_target, h_target))
        elif self.method == "bicubic":
            return self._upsample_bicubic(depth_low, (w_target, h_target))
        elif self.method == "bilinear_guided":
            return self._upsample_bilinear_guided(depth_low, guidance_rgb, (w_target, h_target))
        elif self.method == "laplacian_pyramid":
            return self._upsample_laplacian_pyramid(depth_low, guidance_rgb, (w_target, h_target))
        elif self.method == "edge_preserving":
            return self._upsample_edge_preserving(depth_low, guidance_rgb, (w_target, h_target))
        else:
            return self._upsample_bilinear_guided(depth_low, guidance_rgb, (w_target, h_target))

    @staticmethod
    def _upsample_nearest(depth_low, target_size):
        return cv2.resize(depth_low, target_size, interpolation=cv2.INTER_NEAREST)

    @staticmethod
    def _upsample_bilinear(depth_low, target_size):
        return cv2.resize(depth_low, target_size, interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def _upsample_bicubic(depth_low, target_size):
        return cv2.resize(depth_low, target_size, interpolation=cv2.INTER_CUBIC)

    def _guided_filter(self, guidance, target, radius, eps):
        if guidance.ndim == 3:
            guidance_gray = cv2.cvtColor(guidance, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        else:
            guidance_gray = guidance.astype(np.float32) / 255.0 if guidance.max() > 1 else guidance

        target = target.astype(np.float32)

        mean_I = cv2.boxFilter(guidance_gray, cv2.CV_32F, (radius, radius))
        mean_p = cv2.boxFilter(target, cv2.CV_32F, (radius, radius))
        mean_Ip = cv2.boxFilter(guidance_gray * target, cv2.CV_32F, (radius, radius))
        cov_Ip = mean_Ip - mean_I * mean_p

        mean_II = cv2.boxFilter(guidance_gray * guidance_gray, cv2.CV_32F, (radius, radius))
        var_I = mean_II - mean_I * mean_I

        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I

        mean_a = cv2.boxFilter(a, cv2.CV_32F, (radius, radius))
        mean_b = cv2.boxFilter(b, cv2.CV_32F, (radius, radius))

        q = mean_a * guidance_gray + mean_b
        return q.astype(np.float32)

    def _upsample_bilinear_guided(self, depth_low, guidance_rgb, target_size):
        depth_up = cv2.resize(depth_low, target_size, interpolation=cv2.INTER_LINEAR)

        if guidance_rgb is not None:
            guidance_resized = cv2.resize(guidance_rgb, target_size)
            depth_up = self._guided_filter(guidance_resized, depth_up, self.guided_radius, self.guided_eps)

        depth_up = np.clip(depth_up, 0, 1)
        return depth_up.astype(np.float32)

    def _upsample_laplacian_pyramid(self, depth_low, guidance_rgb, target_size):
        h_low, w_low = depth_low.shape[:2]
        h_target, w_target = target_size

        current_depth = depth_low.copy()
        current_guidance = None
        if guidance_rgb is not None:
            current_guidance = cv2.resize(guidance_rgb, (w_low, h_low))

        while current_depth.shape[0] < h_target or current_depth.shape[1] < w_target:
            next_h = min(current_depth.shape[0] * 2, h_target)
            next_w = min(current_depth.shape[1] * 2, w_target)

            depth_up = cv2.resize(current_depth, (next_w, next_h), interpolation=cv2.INTER_LINEAR)

            if current_guidance is not None:
                guidance_up = cv2.resize(current_guidance, (next_w, next_h))
                depth_up = self._guided_filter(guidance_up, depth_up, self.guided_radius // 2, self.guided_eps)
                current_guidance = guidance_up

            current_depth = depth_up

        current_depth = cv2.resize(current_depth, target_size, interpolation=cv2.INTER_LINEAR)

        if guidance_rgb is not None:
            guidance_final = cv2.resize(guidance_rgb, target_size)
            current_depth = self._guided_filter(guidance_final, current_depth, self.guided_radius, self.guided_eps)

        current_depth = np.clip(current_depth, 0, 1)
        return current_depth.astype(np.float32)

    def _upsample_edge_preserving(self, depth_low, guidance_rgb, target_size):
        depth_up = cv2.resize(depth_low, target_size, interpolation=cv2.INTER_LINEAR)

        if guidance_rgb is None:
            return np.clip(depth_up, 0, 1).astype(np.float32)

        guidance_resized = cv2.resize(guidance_rgb, target_size)
        gray = cv2.cvtColor(guidance_resized, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray, 50, 150)
        edge_mask = edges.astype(np.float32) / 255.0

        detail_map = cv2.Laplacian(gray, cv2.CV_64F)
        detail_map = np.abs(detail_map)
        detail_map = (detail_map - detail_map.min()) / (detail_map.max() - detail_map.min() + 1e-10)
        detail_mask = detail_map > 0.3

        depth_guided = self._guided_filter(guidance_resized, depth_up, self.guided_radius, self.guided_eps)

        alpha = 0.5 + 0.3 * edge_mask * (1.0 - detail_mask.astype(np.float32))
        fused = alpha * depth_guided + (1.0 - alpha) * depth_up

        depth_final = np.clip(fused, 0, 1)
        return depth_final.astype(np.float32)


def align_depth_to_rgb(depth_map, rgb_image, intrinsics_depth=None, intrinsics_rgb=None, extrinsics=None):
    if depth_map is None or rgb_image is None:
        return None, depth_map

    h_rgb, w_rgb = rgb_image.shape[:2]
    h_depth, w_depth = depth_map.shape[:2]

    if intrinsics_depth is None and intrinsics_rgb is None and extrinsics is None:
        depth_aligned = cv2.resize(depth_map, (w_rgb, h_rgb), interpolation=cv2.INTER_LINEAR)
        return depth_aligned, depth_aligned

    depth_aligned = np.zeros((h_rgb, w_rgb), dtype=np.float32)

    if intrinsics_depth is not None and intrinsics_rgb is not None:
        fx_d, fy_d, cx_d, cy_d = intrinsics_depth
        fx_r, fy_r, cx_r, cy_r = intrinsics_rgb

        for y_d in range(h_depth):
            for x_d in range(w_depth):
                depth_val = depth_map[y_d, x_d]
                if depth_val <= 0:
                    continue

                z = depth_val
                x_3d = (x_d - cx_d) * z / fx_d
                y_3d = (y_d - cy_d) * z / fy_d

                if extrinsics is not None:
                    R, t = extrinsics
                    p_3d = np.array([x_3d, y_3d, z])
                    p_3d_transformed = R @ p_3d + t
                    x_3d, y_3d, z = p_3d_transformed

                if z <= 0:
                    continue

                x_r = int(fx_r * x_3d / z + cx_r)
                y_r = int(fy_r * y_3d / z + cy_r)

                if 0 <= x_r < w_rgb and 0 <= y_r < h_rgb:
                    if depth_aligned[y_r, x_r] == 0 or z < depth_aligned[y_r, x_r]:
                        depth_aligned[y_r, x_r] = z

    else:
        depth_aligned = cv2.resize(depth_map, (w_rgb, h_rgb), interpolation=cv2.INTER_LINEAR)

    mask = depth_aligned > 0
    if np.any(mask):
        min_d = depth_aligned[mask].min()
        max_d = depth_aligned[mask].max()
        if max_d - min_d > 1e-6:
            depth_aligned[mask] = (depth_aligned[mask] - min_d) / (max_d - min_d)

    return depth_aligned.astype(np.float32), depth_map


def create_aligned_colored_depth(depth_aligned, rgb_image, colormap="turbo", dynamic_mapping=True, alpha_blend=0.0):
    if depth_aligned is None or rgb_image is None:
        return None

    h, w = rgb_image.shape[:2]
    depth_aligned_resized = cv2.resize(depth_aligned, (w, h), interpolation=cv2.INTER_LINEAR)

    if dynamic_mapping:
        from utils import colorize_depth
        depth_colorized = colorize_depth(depth_aligned_resized, colormap=colormap, dynamic_mapping=True)
    else:
        from utils import colorize_depth
        depth_colorized = colorize_depth(depth_aligned_resized, colormap=colormap)

    if alpha_blend > 0:
        rgb_float = rgb_image.astype(np.float32)
        depth_float = depth_colorized.astype(np.float32)
        blended = (1 - alpha_blend) * rgb_float + alpha_blend * depth_float
        aligned_result = np.clip(blended, 0, 255).astype(np.uint8)
    else:
        aligned_result = depth_colorized

    return aligned_result


def compute_depth_metrics(pred_depth, gt_depth, mask=None, max_depth=1.0):
    if pred_depth is None or gt_depth is None:
        return {}

    h_pred, w_pred = pred_depth.shape[:2]
    h_gt, w_gt = gt_depth.shape[:2]

    if h_pred != h_gt or w_pred != w_gt:
        pred_resized = cv2.resize(pred_depth, (w_gt, h_gt), interpolation=cv2.INTER_LINEAR)
    else:
        pred_resized = pred_depth.copy()

    if mask is None:
        mask = (gt_depth > 0) & (gt_depth <= max_depth) & (pred_resized > 0) & (pred_resized <= max_depth)

    if not np.any(mask):
        return {
            "rmse": float("nan"),
            "mae": float("nan"),
            "abs_rel": float("nan"),
            "sq_rel": float("nan"),
            "delta1": float("nan"),
            "delta2": float("nan"),
            "delta3": float("nan"),
            "valid_pixels": 0,
        }

    pred_valid = pred_resized[mask]
    gt_valid = gt_depth[mask]

    pred_valid = np.clip(pred_valid, 1e-6, None)
    gt_valid = np.clip(gt_valid, 1e-6, None)

    rmse = np.sqrt(np.mean((pred_valid - gt_valid) ** 2))
    mae = np.mean(np.abs(pred_valid - gt_valid))
    abs_rel = np.mean(np.abs(pred_valid - gt_valid) / gt_valid)
    sq_rel = np.mean(((pred_valid - gt_valid) ** 2) / gt_valid)

    max_ratio = np.maximum(pred_valid / gt_valid, gt_valid / pred_valid)
    delta1 = np.mean(max_ratio < 1.25)
    delta2 = np.mean(max_ratio < 1.25 ** 2)
    delta3 = np.mean(max_ratio < 1.25 ** 3)

    valid_pixels = int(np.sum(mask))

    return {
        "rmse": float(rmse),
        "mae": float(mae),
        "abs_rel": float(abs_rel),
        "sq_rel": float(sq_rel),
        "delta1": float(delta1),
        "delta2": float(delta2),
        "delta3": float(delta3),
        "valid_pixels": valid_pixels,
    }


def format_metrics_display(metrics):
    lines = []
    if "rmse" in metrics and not np.isnan(metrics["rmse"]):
        lines.append(f"RMSE:    {metrics['rmse']:.4f}")
    if "mae" in metrics and not np.isnan(metrics["mae"]):
        lines.append(f"MAE:     {metrics['mae']:.4f}")
    if "abs_rel" in metrics and not np.isnan(metrics["abs_rel"]):
        lines.append(f"Abs Rel: {metrics['abs_rel']:.4f}")
    if "delta1" in metrics and not np.isnan(metrics["delta1"]):
        lines.append(f"δ < 1.25:  {metrics['delta1']*100:.1f}%")
    if "delta2" in metrics and not np.isnan(metrics["delta2"]):
        lines.append(f"δ < 1.25²: {metrics['delta2']*100:.1f}%")
    if "delta3" in metrics and not np.isnan(metrics["delta3"]):
        lines.append(f"δ < 1.25³: {metrics['delta3']*100:.1f}%")
    if "valid_pixels" in metrics:
        lines.append(f"有效像素: {metrics['valid_pixels']}")
    return "\n".join(lines)


class MetricsAccumulator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.metrics_list = []
        self.frame_count = 0

    def update(self, metrics):
        if metrics and "valid_pixels" in metrics and metrics["valid_pixels"] > 0:
            self.metrics_list.append(metrics)
            self.frame_count += 1

    def get_average(self):
        if not self.metrics_list:
            return {}

        keys = ["rmse", "mae", "abs_rel", "sq_rel", "delta1", "delta2", "delta3"]
        avg = {}

        for key in keys:
            values = [m[key] for m in self.metrics_list if key in m and not np.isnan(m[key])]
            if values:
                avg[key] = float(np.mean(values))
            else:
                avg[key] = float("nan")

        avg["frame_count"] = self.frame_count
        if self.metrics_list and "valid_pixels" in self.metrics_list[0]:
            avg["avg_valid_pixels"] = float(np.mean([m["valid_pixels"] for m in self.metrics_list]))

        return avg
