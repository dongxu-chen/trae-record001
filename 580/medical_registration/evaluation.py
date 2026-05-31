import numpy as np
from scipy.ndimage import label


class RegistrationEvaluator:
    def __init__(self):
        self.results = {}

    def compute_all(self, fixed, moving, moving_warped, transform_matrix=None, fixed_mask=None, moving_mask=None):
        self.results = {}
        self.results["mse_before"] = self.mean_squared_error(fixed, moving)
        self.results["mse_after"] = self.mean_squared_error(fixed, moving_warped)
        self.results["nmi_before"] = self.normalized_mutual_information(fixed, moving)
        self.results["nmi_after"] = self.normalized_mutual_information(fixed, moving_warped)
        self.results["mi_before"] = self.mutual_information(fixed, moving)
        self.results["mi_after"] = self.mutual_information(fixed, moving_warped)
        self.results["ssim_before"] = self.structural_similarity(fixed, moving)
        self.results["ssim_after"] = self.structural_similarity(fixed, moving_warped)
        self.results["correlation_before"] = self.correlation_coefficient(fixed, moving)
        self.results["correlation_after"] = self.correlation_coefficient(fixed, moving_warped)

        if fixed_mask is not None and moving_mask is not None:
            moving_warped_mask = self._warp_mask(moving_mask, transform_matrix, fixed.shape) if transform_matrix is not None else moving_mask
            self.results["dice_before"] = self.dice_coefficient(fixed_mask, moving_mask)
            self.results["dice_after"] = self.dice_coefficient(fixed_mask, moving_warped_mask)
            self.results["jaccard_before"] = self.jaccard_index(fixed_mask, moving_mask)
            self.results["jaccard_after"] = self.jaccard_index(fixed_mask, moving_warped_mask)
            self.results["hausdorff_before"] = self.hausdorff_distance(fixed_mask, moving_mask)
            self.results["hausdorff_after"] = self.hausdorff_distance(fixed_mask, moving_warped_mask)

        if transform_matrix is not None:
            self.results["transform_determinant"] = float(np.linalg.det(transform_matrix[:2, :2] if transform_matrix.shape[0] == 3 else transform_matrix[:3, :3]))

        return self.results

    @staticmethod
    def mean_squared_error(fixed, moving):
        mask = (fixed != 0) & (moving != 0)
        if mask.sum() == 0:
            return float("inf")
        diff = fixed[mask].astype(np.float64) - moving[mask].astype(np.float64)
        return float(np.mean(diff ** 2))

    @staticmethod
    def mutual_information(fixed, moving, num_bins=64):
        fixed = fixed.ravel()
        moving = moving.ravel()
        mask = np.isfinite(fixed) & np.isfinite(moving)
        fixed = fixed[mask]
        moving = moving[mask]

        if len(fixed) == 0:
            return 0.0

        hist_2d, _, _ = np.histogram2d(fixed, moving, bins=num_bins)
        pxy = hist_2d / hist_2d.sum()
        px = pxy.sum(axis=1)
        py = pxy.sum(axis=0)
        px_py = px[:, np.newaxis] * py[np.newaxis, :]

        nonzero = pxy > 0
        return float(np.sum(pxy[nonzero] * np.log(pxy[nonzero] / px_py[nonzero])))

    @staticmethod
    def normalized_mutual_information(fixed, moving, num_bins=64):
        mi = RegistrationEvaluator.mutual_information(fixed, moving, num_bins)

        fixed_flat = fixed.ravel()
        moving_flat = moving.ravel()
        mask = np.isfinite(fixed_flat) & np.isfinite(moving_flat)
        fixed_flat = fixed_flat[mask]
        moving_flat = moving_flat[mask]

        if len(fixed_flat) == 0:
            return 0.0

        hist_f, _ = np.histogram(fixed_flat, bins=num_bins)
        hist_m, _ = np.histogram(moving_flat, bins=num_bins)

        pf = hist_f / hist_f.sum()
        pm = hist_m / hist_m.sum()
        pf = pf[pf > 0]
        pm = pm[pm > 0]

        h_f = -np.sum(pf * np.log(pf))
        h_m = -np.sum(pm * np.log(pm))

        if abs(h_f + h_m) < 1e-10:
            return 0.0

        return float(2.0 * mi / (h_f + h_m))

    @staticmethod
    def correlation_coefficient(fixed, moving):
        mask = (fixed != 0) & (moving != 0)
        if mask.sum() < 10:
            return 0.0
        f = fixed[mask].astype(np.float64)
        m = moving[mask].astype(np.float64)
        f_mean, m_mean = f.mean(), m.mean()
        f_centered = f - f_mean
        m_centered = m - m_mean
        numerator = np.sum(f_centered * m_centered)
        denominator = np.sqrt(np.sum(f_centered ** 2) * np.sum(m_centered ** 2))
        if denominator < 1e-10:
            return 0.0
        return float(numerator / denominator)

    @staticmethod
    def structural_similarity(fixed, moving, win_size=7):
        mask = (fixed != 0) & (moving != 0)
        if mask.sum() < win_size * win_size * 2:
            return 0.0

        f = fixed.astype(np.float64)
        m = moving.astype(np.float64)

        C1 = (0.01 * (f.max() - f.min())) ** 2
        C2 = (0.03 * (f.max() - f.min())) ** 2

        from scipy.ndimage import uniform_filter

        mu_f = uniform_filter(f, size=win_size)
        mu_m = uniform_filter(m, size=win_size)

        mu_f_sq = mu_f ** 2
        mu_m_sq = mu_m ** 2
        mu_fm = mu_f * mu_m

        sigma_f_sq = uniform_filter(f ** 2, size=win_size) - mu_f_sq
        sigma_m_sq = uniform_filter(m ** 2, size=win_size) - mu_m_sq
        sigma_fm = uniform_filter(f * m, size=win_size) - mu_fm

        ssim_map = ((2 * mu_fm + C1) * (2 * sigma_fm + C2)) / (
            (mu_f_sq + mu_m_sq + C1) * (sigma_f_sq + sigma_m_sq + C2)
        )

        valid_mask = mask & np.isfinite(ssim_map)
        if valid_mask.sum() == 0:
            return 0.0
        return float(ssim_map[valid_mask].mean())

    @staticmethod
    def dice_coefficient(mask1, mask2):
        mask1_bool = mask1 > 0
        mask2_bool = mask2 > 0
        intersection = np.sum(mask1_bool & mask2_bool)
        total = np.sum(mask1_bool) + np.sum(mask2_bool)
        if total == 0:
            return 0.0
        return float(2.0 * intersection / total)

    @staticmethod
    def jaccard_index(mask1, mask2):
        mask1_bool = mask1 > 0
        mask2_bool = mask2 > 0
        intersection = np.sum(mask1_bool & mask2_bool)
        union = np.sum(mask1_bool | mask2_bool)
        if union == 0:
            return 0.0
        return float(intersection / union)

    @staticmethod
    def hausdorff_distance(mask1, mask2, percentile=100):
        coords1 = np.argwhere(mask1 > 0)
        coords2 = np.argwhere(mask2 > 0)

        if len(coords1) == 0 or len(coords2) == 0:
            return float("inf")

        from scipy.spatial.distance import cdist

        distances = cdist(coords1, coords2, metric="euclidean")
        min_d1 = distances.min(axis=1)
        min_d2 = distances.min(axis=0)

        all_min_distances = np.concatenate([min_d1, min_d2])
        return float(np.percentile(all_min_distances, percentile))

    @staticmethod
    def target_registration_error(ground_truth_points, transformed_points, spacing=None):
        if len(ground_truth_points) != len(transformed_points):
            raise ValueError("Point sets must have the same length")

        gt = np.asarray(ground_truth_points, dtype=np.float64)
        tp = np.asarray(transformed_points, dtype=np.float64)

        if spacing is not None:
            spacing = np.asarray(spacing, dtype=np.float64)
            gt = gt * spacing
            tp = tp * spacing

        errors = np.sqrt(np.sum((gt - tp) ** 2, axis=1))
        sorted_errors = np.sort(errors)

        return {
            "mean": float(np.mean(errors)),
            "median": float(np.median(errors)),
            "std": float(np.std(errors)),
            "max": float(np.max(errors)),
            "min": float(np.min(errors)),
            "p25": float(np.percentile(errors, 25)),
            "p75": float(np.percentile(errors, 75)),
            "p95": float(np.percentile(errors, 95)),
            "p99": float(np.percentile(errors, 99)),
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "all_errors": errors,
            "sorted_errors": sorted_errors,
            "count": len(errors),
        }

    @staticmethod
    def compute_tre_from_transform(ground_truth_points, transform, params, spacing=None):
        gt = np.asarray(ground_truth_points, dtype=np.float64)
        transformed = np.array([
            transform.transform_point(p, params) for p in gt
        ])
        return RegistrationEvaluator.target_registration_error(gt, transformed, spacing)

    @staticmethod
    def generate_landmark_points(image_shape, num_points=100, seed=None):
        if seed is not None:
            np.random.seed(seed)

        dim = len(image_shape)
        points = np.random.uniform(
            low=np.array([s * 0.2 for s in image_shape]),
            high=np.array([s * 0.8 for s in image_shape]),
            size=(num_points, dim)
        )
        return points

    @staticmethod
    def apply_transform_to_points(points, transform, params, invert=False):
        points = np.asarray(points, dtype=np.float64)
        result = []
        for p in points:
            if invert and hasattr(transform, "get_matrix"):
                try:
                    M = transform.get_matrix(params)
                    M_inv = np.linalg.inv(M)
                    homogeneous = np.append(p, 1.0)
                    transformed = (M_inv @ homogeneous)[: len(p)]
                    result.append(transformed)
                except Exception:
                    result.append(transform.transform_point(p, params))
            else:
                result.append(transform.transform_point(p, params))
        return np.array(result)

    @staticmethod
    def _warp_mask(mask, transform_matrix, output_shape):
        from scipy.ndimage import map_coordinates

        dim = len(output_shape)
        if dim == 2:
            rows, cols = output_shape
            coords = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
            coords = np.stack([coords[0].ravel(), coords[1].ravel()], axis=0)
            ones = np.ones((1, coords.shape[1]))
            homogeneous = np.vstack([coords, ones])
        else:
            slices, rows, cols = output_shape
            coords = np.meshgrid(np.arange(slices), np.arange(rows), np.arange(cols), indexing="ij")
            coords = np.stack([coords[0].ravel(), coords[1].ravel(), coords[2].ravel()], axis=0)
            ones = np.ones((1, coords.shape[1]))
            homogeneous = np.vstack([coords, ones])

        M_inv = np.linalg.inv(transform_matrix)
        src_coords = M_inv @ homogeneous

        result = map_coordinates(
            mask.astype(np.float64),
            src_coords[:dim].tolist(),
            order=0,
            mode="constant",
            cval=0.0,
        )
        return (result.reshape(output_shape) > 0.5).astype(np.uint8)

    def summary(self):
        if not self.results:
            return "No evaluation results available. Run compute_all() first."

        lines = ["=" * 60, "Registration Evaluation Results", "=" * 60]

        sections = {
            "Mean Squared Error": ["mse_before", "mse_after"],
            "Mutual Information": ["mi_before", "mi_after"],
            "Normalized Mutual Information": ["nmi_before", "nmi_after"],
            "SSIM": ["ssim_before", "ssim_after"],
            "Correlation Coefficient": ["correlation_before", "correlation_after"],
            "Dice Coefficient": ["dice_before", "dice_after"],
            "Jaccard Index": ["jaccard_before", "jaccard_after"],
            "Hausdorff Distance": ["hausdorff_before", "hausdorff_after"],
        }

        for section_name, keys in sections.items():
            values = [self.results.get(k) for k in keys]
            if any(v is not None for v in values):
                lines.append(f"\n{section_name}:")
                if values[0] is not None:
                    lines.append(f"  Before: {values[0]:.6f}")
                if values[1] is not None:
                    lines.append(f"  After:  {values[1]:.6f}")
                if values[0] is not None and values[1] is not None:
                    improvement = values[1] - values[0]
                    lines.append(f"  Change: {improvement:+.6f}")

        if "transform_determinant" in self.results:
            lines.append(f"\nTransform Determinant: {self.results['transform_determinant']:.6f}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
