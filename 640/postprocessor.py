import SimpleITK as sitk
import numpy as np
from scipy import ndimage
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PostProcessor:
    def __init__(self):
        self.default_params = {
            "cca_min_volume": 100,
            "cca_keep_largest": False,
            "cca_adaptive": True,
            "cca_volume_ratio": 0.05,
            "hole_fill_2d": True,
            "hole_fill_3d": False,
            "hole_fill_multiseed": True,
            "hole_fill_seed_spacing": 8,
            "hole_fill_enclosure_thresh": 0.5,
            "smooth_method": "gaussian",
            "smooth_sigma": 0.5,
            "smooth_iterations": 1,
            "smooth_adaptive": True,
            "smooth_ref_surface": 1000.0,
            "morph_operation": None,
            "morph_radius": 1,
        }

    def _compute_adaptive_min_volume(
        self,
        mask: np.ndarray,
        base_min_volume: int,
        adaptive: bool,
        volume_ratio: float,
    ) -> int:
        if not adaptive:
            return base_min_volume
        total_volume = int(np.sum(mask > 0))
        if total_volume == 0:
            return base_min_volume
        adaptive_min = max(1, int(total_volume * volume_ratio))
        return adaptive_min

    def connected_component_analysis(
        self,
        mask: np.ndarray,
        min_volume: int = 100,
        keep_largest: bool = False,
        adaptive: bool = True,
        volume_ratio: float = 0.05,
    ) -> np.ndarray:
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        effective_min = self._compute_adaptive_min_volume(
            mask, min_volume, adaptive, volume_ratio
        )
        labeled, num_features = ndimage.label(mask)
        if num_features == 0:
            return mask
        if keep_largest:
            component_sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
            largest_label = np.argmax(component_sizes) + 1
            return (labeled == largest_label).astype(np.uint8)
        component_sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
        valid_labels = [
            i + 1 for i, s in enumerate(component_sizes) if s >= effective_min
        ]
        if not valid_labels:
            return np.zeros_like(mask, dtype=np.uint8)
        result = np.isin(labeled, valid_labels).astype(np.uint8)
        return result

    def _compute_surface_area(
        self,
        mask: np.ndarray,
        spacing: Optional[Tuple[float, ...]] = None,
    ) -> float:
        if spacing is None:
            spacing = tuple([1.0] * mask.ndim)
        struct = ndimage.generate_binary_structure(mask.ndim, 1)
        dilated = ndimage.binary_dilation(mask, structure=struct)
        boundary = dilated.astype(np.float32) - mask.astype(np.float32)
        voxel_surface_area = boundary * np.prod(spacing)
        return float(np.sum(voxel_surface_area))

    def _compute_adaptive_iterations(
        self,
        mask: np.ndarray,
        base_iterations: int,
        adaptive: bool,
        ref_surface: float,
        spacing: Optional[Tuple[float, ...]] = None,
    ) -> int:
        if not adaptive:
            return base_iterations
        surface_area = self._compute_surface_area(mask, spacing)
        if surface_area <= 0 or ref_surface <= 0:
            return base_iterations
        scale = surface_area / ref_surface
        adaptive_iters = max(1, round(base_iterations * scale))
        return min(adaptive_iters, 20)

    def _fill_holes_multiseed_2d(
        self,
        mask_2d: np.ndarray,
        seed_spacing: int = 8,
        enclosure_thresh: float = 0.5,
    ) -> np.ndarray:
        bg = (mask_2d == 0)
        if not np.any(bg):
            return mask_2d
        struct_8conn = ndimage.generate_binary_structure(2, 2)
        labeled_bg, num_bg = ndimage.label(bg, structure=struct_8conn)
        if num_bg == 0:
            return mask_2d
        border = np.zeros_like(mask_2d, dtype=bool)
        border[0, :] = True
        border[-1, :] = True
        border[:, 0] = True
        border[:, -1] = True
        border_labels = set(np.unique(labeled_bg[border])) - {0}
        result = mask_2d.copy()
        for comp_id in range(1, num_bg + 1):
            comp_mask = labeled_bg == comp_id
            if comp_id not in border_labels:
                result[comp_mask] = 1
                continue
            dilated = ndimage.binary_dilation(comp_mask, structure=struct_8conn)
            boundary_voxels = dilated & ~comp_mask
            fg_boundary = boundary_voxels & (mask_2d > 0)
            total_boundary = np.sum(boundary_voxels)
            if total_boundary > 0:
                enclosure = float(np.sum(fg_boundary)) / float(total_boundary)
                if enclosure >= enclosure_thresh:
                    result[comp_mask] = 1
        h, w = result.shape
        for y in range(seed_spacing // 2, h, seed_spacing):
            for x in range(seed_spacing // 2, w, seed_spacing):
                if result[y, x] == 0:
                    seed_bg = (result == 0).astype(np.uint8)
                    seed_mask = np.zeros_like(result, dtype=np.uint8)
                    seed_mask[y, x] = 1
                    propagated = ndimage.binary_propagation(
                        seed_mask, structure=struct_8conn, mask=seed_bg
                    )
                    if not np.any(propagated[border]):
                        result[propagated] = 1
        return result

    def _fill_holes_multiseed_3d(
        self,
        mask: np.ndarray,
        seed_spacing: int = 8,
        enclosure_thresh: float = 0.5,
    ) -> np.ndarray:
        bg = (mask == 0)
        if not np.any(bg):
            return mask
        struct_26conn = ndimage.generate_binary_structure(3, 3)
        labeled_bg, num_bg = ndimage.label(bg, structure=struct_26conn)
        if num_bg == 0:
            return mask
        border = np.zeros_like(mask, dtype=bool)
        border[0, :, :] = True
        border[-1, :, :] = True
        border[:, 0, :] = True
        border[:, -1, :] = True
        border[:, :, 0] = True
        border[:, :, -1] = True
        border_labels = set(np.unique(labeled_bg[border])) - {0}
        result = mask.copy()
        for comp_id in range(1, num_bg + 1):
            comp_mask = labeled_bg == comp_id
            if comp_id not in border_labels:
                result[comp_mask] = 1
                continue
            dilated = ndimage.binary_dilation(comp_mask, structure=struct_26conn)
            boundary_voxels = dilated & ~comp_mask
            fg_boundary = boundary_voxels & (mask > 0)
            total_boundary = np.sum(boundary_voxels)
            if total_boundary > 0:
                enclosure = float(np.sum(fg_boundary)) / float(total_boundary)
                if enclosure >= enclosure_thresh:
                    result[comp_mask] = 1
        d, h, w = result.shape
        for z in range(seed_spacing // 2, d, seed_spacing):
            for y in range(seed_spacing // 2, h, seed_spacing):
                for x in range(seed_spacing // 2, w, seed_spacing):
                    if result[z, y, x] == 0:
                        seed_bg = (result == 0).astype(np.uint8)
                        seed_mask = np.zeros_like(result, dtype=np.uint8)
                        seed_mask[z, y, x] = 1
                        propagated = ndimage.binary_propagation(
                            seed_mask, structure=struct_26conn, mask=seed_bg
                        )
                        if not np.any(propagated[border]):
                            result[propagated] = 1
        return result

    def fill_holes(
        self,
        mask: np.ndarray,
        fill_2d: bool = True,
        fill_3d: bool = False,
        multiseed: bool = True,
        seed_spacing: int = 8,
        enclosure_thresh: float = 0.5,
    ) -> np.ndarray:
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        result = mask.copy()
        if not multiseed:
            if fill_3d:
                result = ndimage.binary_fill_holes(result).astype(np.uint8)
            if fill_2d:
                if result.ndim == 3:
                    for i in range(result.shape[0]):
                        result[i] = ndimage.binary_fill_holes(result[i]).astype(
                            np.uint8
                        )
                    for j in range(result.shape[1]):
                        result[:, j, :] = ndimage.binary_fill_holes(
                            result[:, j, :]
                        ).astype(np.uint8)
                    for k in range(result.shape[2]):
                        result[:, :, k] = ndimage.binary_fill_holes(
                            result[:, :, k]
                        ).astype(np.uint8)
                else:
                    result = ndimage.binary_fill_holes(result).astype(np.uint8)
        else:
            if fill_3d:
                result = self._fill_holes_multiseed_3d(
                    result, seed_spacing, enclosure_thresh
                )
            if fill_2d:
                if result.ndim == 3:
                    for i in range(result.shape[0]):
                        result[i] = self._fill_holes_multiseed_2d(
                            result[i], seed_spacing, enclosure_thresh
                        )
                    for j in range(result.shape[1]):
                        result[:, j, :] = self._fill_holes_multiseed_2d(
                            result[:, j, :], seed_spacing, enclosure_thresh
                        )
                    for k in range(result.shape[2]):
                        result[:, :, k] = self._fill_holes_multiseed_2d(
                            result[:, :, k], seed_spacing, enclosure_thresh
                        )
                else:
                    result = self._fill_holes_multiseed_2d(
                        result, seed_spacing, enclosure_thresh
                    )
        return result

    def smooth_edge(
        self,
        mask: np.ndarray,
        method: str = "gaussian",
        sigma: float = 0.5,
        iterations: int = 1,
        spacing: Optional[Tuple[float, ...]] = None,
        adaptive: bool = True,
        ref_surface: float = 1000.0,
    ) -> np.ndarray:
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        if spacing is None:
            spacing = tuple([1.0] * mask.ndim)
        effective_iters = self._compute_adaptive_iterations(
            mask, iterations, adaptive, ref_surface, spacing
        )
        original_label = 1
        result = mask.copy()
        for _ in range(effective_iters):
            if method == "gaussian":
                result = self._smooth_gaussian(result, sigma, spacing)
            elif method == "median":
                result = self._smooth_median(result, spacing)
            elif method == "sitk_curvature":
                result = self._smooth_sitk_curvature(result, spacing)
            else:
                logger.warning(f"Unknown smooth method: {method}, using gaussian")
                result = self._smooth_gaussian(result, sigma, spacing)
        return (result > 0).astype(np.uint8) * original_label

    def _smooth_gaussian(
        self,
        mask: np.ndarray,
        sigma: float,
        spacing: Tuple[float, ...],
    ) -> np.ndarray:
        sigmas = [sigma / s for s in spacing]
        smoothed = ndimage.gaussian_filter(mask.astype(np.float32), sigma=sigmas)
        threshold = 0.5
        return (smoothed > threshold).astype(np.uint8)

    def _smooth_median(
        self,
        mask: np.ndarray,
        spacing: Tuple[float, ...],
    ) -> np.ndarray:
        size = 3
        return ndimage.median_filter(mask.astype(np.float32), size=size).astype(
            np.uint8
        )

    def _smooth_sitk_curvature(
        self,
        mask: np.ndarray,
        spacing: Tuple[float, ...],
    ) -> np.ndarray:
        sitk_mask = sitk.GetImageFromArray(mask)
        sitk_mask.SetSpacing(spacing)
        dilated = sitk.BinaryDilate(sitk_mask, 1)
        eroded = sitk.BinaryErode(sitk_mask, 1)
        combo = sitk.Or(dilated, eroded)
        result = sitk.GetArrayFromImage(combo)
        return result.astype(np.uint8)

    def morphological_operation(
        self,
        mask: np.ndarray,
        operation: str = "close",
        radius: int = 1,
    ) -> np.ndarray:
        if mask.dtype != np.uint8:
            mask = mask.astype(np.uint8)
        struct = ndimage.generate_binary_structure(mask.ndim, radius)
        if operation == "close":
            result = ndimage.binary_closing(mask, structure=struct).astype(np.uint8)
        elif operation == "open":
            result = ndimage.binary_opening(mask, structure=struct).astype(np.uint8)
        elif operation == "dilate":
            result = ndimage.binary_dilation(mask, structure=struct).astype(np.uint8)
        elif operation == "erode":
            result = ndimage.binary_erosion(mask, structure=struct).astype(np.uint8)
        else:
            logger.warning(f"Unknown morph operation: {operation}")
            return mask
        return result

    def process_label(
        self,
        mask: np.ndarray,
        params: Dict,
        spacing: Optional[Tuple[float, ...]] = None,
    ) -> np.ndarray:
        result = mask.copy()
        if params.get("cca_enabled", True):
            result = self.connected_component_analysis(
                result,
                min_volume=params.get("cca_min_volume", 100),
                keep_largest=params.get("cca_keep_largest", False),
                adaptive=params.get("cca_adaptive", True),
                volume_ratio=params.get("cca_volume_ratio", 0.05),
            )
        if params.get("hole_fill_enabled", True):
            result = self.fill_holes(
                result,
                fill_2d=params.get("hole_fill_2d", True),
                fill_3d=params.get("hole_fill_3d", False),
                multiseed=params.get("hole_fill_multiseed", True),
                seed_spacing=params.get("hole_fill_seed_spacing", 8),
                enclosure_thresh=params.get("hole_fill_enclosure_thresh", 0.5),
            )
        morph_op = params.get("morph_operation", None)
        if morph_op:
            result = self.morphological_operation(
                result,
                operation=morph_op,
                radius=params.get("morph_radius", 1),
            )
        if params.get("smooth_enabled", True):
            result = self.smooth_edge(
                result,
                method=params.get("smooth_method", "gaussian"),
                sigma=params.get("smooth_sigma", 0.5),
                iterations=params.get("smooth_iterations", 1),
                spacing=spacing,
                adaptive=params.get("smooth_adaptive", True),
                ref_surface=params.get("smooth_ref_surface", 1000.0),
            )
        return result

    def process_multi_label(
        self,
        mask: np.ndarray,
        params_per_label: Dict[int, Dict],
        spacing: Optional[Tuple[float, ...]] = None,
    ) -> np.ndarray:
        unique_labels = np.unique(mask)
        unique_labels = unique_labels[unique_labels != 0]
        result = np.zeros_like(mask, dtype=np.uint8)
        for label_val in unique_labels:
            label_val = int(label_val)
            binary_mask = (mask == label_val).astype(np.uint8)
            label_params = params_per_label.get(label_val, self.default_params)
            processed = self.process_label(binary_mask, label_params, spacing)
            result[processed > 0] = label_val
        return result

    def compute_dice(
        self,
        a: np.ndarray,
        b: np.ndarray,
        label: int = 1,
    ) -> float:
        a_bin = (a == label).astype(np.float32)
        b_bin = (b == label).astype(np.float32)
        intersection = np.sum(a_bin * b_bin)
        total = np.sum(a_bin) + np.sum(b_bin)
        if total == 0:
            return 1.0
        return float(2.0 * intersection / total)

    def compute_hausdorff(
        self,
        a: np.ndarray,
        b: np.ndarray,
        label: int = 1,
        spacing: Optional[Tuple[float, ...]] = None,
        percentile: float = 100.0,
    ) -> float:
        if spacing is None:
            spacing = tuple([1.0] * a.ndim)
        a_bin = (a == label).astype(np.uint8)
        b_bin = (b == label).astype(np.uint8)
        if np.sum(a_bin) == 0 or np.sum(b_bin) == 0:
            return float("inf")
        if a.ndim == 2:
            struct = ndimage.generate_binary_structure(2, 1)
            a_contour = a_bin & ~ndimage.binary_erosion(a_bin, structure=struct)
            b_contour = b_bin & ~ndimage.binary_erosion(b_bin, structure=struct)
            a_coords = np.column_stack(np.where(a_contour)).astype(np.float32)
            b_coords = np.column_stack(np.where(b_contour)).astype(np.float32)
            for i in range(a.ndim):
                a_coords[:, i] *= spacing[i]
                b_coords[:, i] *= spacing[i]
        else:
            struct = ndimage.generate_binary_structure(3, 1)
            a_contour = a_bin & ~ndimage.binary_erosion(a_bin, structure=struct)
            b_contour = b_bin & ~ndimage.binary_erosion(b_bin, structure=struct)
            a_coords = np.column_stack(np.where(a_contour)).astype(np.float32)
            b_coords = np.column_stack(np.where(b_contour)).astype(np.float32)
            for i in range(a.ndim):
                a_coords[:, i] *= spacing[i]
                b_coords[:, i] *= spacing[i]
        if len(a_coords) == 0 or len(b_coords) == 0:
            return float("inf")
        distances_ab = self._pairwise_distances(a_coords, b_coords)
        distances_ba = self._pairwise_distances(b_coords, a_coords)
        if percentile < 100.0:
            k1 = max(1, int(len(distances_ab) * (100.0 - percentile) / 100.0))
            k2 = max(1, int(len(distances_ba) * (100.0 - percentile) / 100.0))
            hd_ab = np.partition(distances_ab, k1)[k1]
            hd_ba = np.partition(distances_ba, k2)[k2]
        else:
            hd_ab = np.max(distances_ab)
            hd_ba = np.max(distances_ba)
        return float(max(hd_ab, hd_ba))

    @staticmethod
    def _pairwise_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        max_points = 20000
        if len(a) > max_points:
            indices = np.random.choice(len(a), max_points, replace=False)
            a = a[indices]
        if len(b) > max_points:
            indices = np.random.choice(len(b), max_points, replace=False)
            b = b[indices]
        dists = []
        batch_size = 1000
        for i in range(0, len(a), batch_size):
            a_batch = a[i:i + batch_size]
            diff = a_batch[:, np.newaxis, :] - b[np.newaxis, :, :]
            batch_dists = np.sqrt(np.sum(diff ** 2, axis=2))
            dists.append(np.min(batch_dists, axis=1))
        return np.concatenate(dists)

    def compute_metrics(
        self,
        pred: np.ndarray,
        gt: np.ndarray,
        spacing: Optional[Tuple[float, ...]] = None,
    ) -> Dict[int, Dict[str, float]]:
        labels = np.unique(pred)
        labels = labels[labels != 0]
        metrics = {}
        for label in labels:
            label_int = int(label)
            dice = self.compute_dice(pred, gt, label_int)
            hd95 = self.compute_hausdorff(pred, gt, label_int, spacing, percentile=95.0)
            hd100 = self.compute_hausdorff(pred, gt, label_int, spacing, percentile=100.0)
            pred_vol = int(np.sum(pred == label_int))
            gt_vol = int(np.sum(gt == label_int))
            metrics[label_int] = {
                "dice": round(dice, 4),
                "hd95": round(hd95, 2),
                "hd100": round(hd100, 2),
                "pred_volume": pred_vol,
                "gt_volume": gt_vol,
                "volume_diff": pred_vol - gt_vol,
            }
        return metrics

    def region_grow_2d(
        self,
        image: np.ndarray,
        seed: Tuple[int, int],
        lower_thresh: float,
        upper_thresh: float,
        connectivity: int = 4,
        max_size: int = 100000,
    ) -> np.ndarray:
        if connectivity == 4:
            struct = ndimage.generate_binary_structure(2, 1)
        else:
            struct = ndimage.generate_binary_structure(2, 2)
        seed_mask = np.zeros_like(image, dtype=np.uint8)
        y, x = seed
        if 0 <= y < image.shape[0] and 0 <= x < image.shape[1]:
            seed_mask[y, x] = 1
        in_range = ((image >= lower_thresh) & (image <= upper_thresh)).astype(np.uint8)
        grown = ndimage.binary_propagation(seed_mask, structure=struct, mask=in_range)
        if np.sum(grown) > max_size:
            grown = np.zeros_like(image, dtype=np.uint8)
        return grown.astype(np.uint8)

    def region_grow_3d(
        self,
        image: np.ndarray,
        seeds: List[Tuple[int, int, int]],
        lower_thresh: float,
        upper_thresh: float,
        connectivity: int = 6,
        max_size: int = 1000000,
    ) -> np.ndarray:
        if connectivity == 6:
            struct = ndimage.generate_binary_structure(3, 1)
        else:
            struct = ndimage.generate_binary_structure(3, 2)
        seed_mask = np.zeros_like(image, dtype=np.uint8)
        for seed in seeds:
            z, y, x = seed
            if 0 <= z < image.shape[0] and 0 <= y < image.shape[1] and 0 <= x < image.shape[2]:
                seed_mask[z, y, x] = 1
        in_range = ((image >= lower_thresh) & (image <= upper_thresh)).astype(np.uint8)
        grown = ndimage.binary_propagation(seed_mask, structure=struct, mask=in_range)
        if np.sum(grown) > max_size:
            grown = np.zeros_like(image, dtype=np.uint8)
        return grown.astype(np.uint8)

    def interactive_brush_2d(
        self,
        mask: np.ndarray,
        brush_positions: List[Tuple[int, int]],
        brush_radius: int = 3,
        mode: str = "draw",
    ) -> np.ndarray:
        result = mask.copy()
        for (y, x) in brush_positions:
            for dy in range(-brush_radius, brush_radius + 1):
                for dx in range(-brush_radius, brush_radius + 1):
                    if dy * dy + dx * dx <= brush_radius * brush_radius:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < result.shape[0] and 0 <= nx < result.shape[1]:
                            if mode == "draw":
                                result[ny, nx] = 1
                            elif mode == "erase":
                                result[ny, nx] = 0
        return result
