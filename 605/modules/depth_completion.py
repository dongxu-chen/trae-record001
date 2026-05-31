import logging
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class DepthHoleFiller:
    def __init__(
        self,
        max_iterations=3,
        min_consensus=2,
        depth_rel_thresh=0.02,
        spatial_sigma=1.5,
        range_sigma=0.1,
    ):
        self.max_iterations = max_iterations
        self.min_consensus = min_consensus
        self.depth_rel_thresh = depth_rel_thresh
        self.spatial_sigma = spatial_sigma
        self.range_sigma = range_sigma

    def fill_holes_cross_view(
        self,
        ref_depth,
        src_depths,
        ref_cam,
        src_cams,
        ref_image=None,
    ):
        h, w = ref_depth.shape
        filled = ref_depth.copy()
        hole_mask = ref_depth <= 0

        if not np.any(hole_mask):
            logger.info("No holes to fill in reference depth map")
            return filled, hole_mask

        logger.info(f"Filling {np.sum(hole_mask)} holes using {len(src_depths)} source views")

        for iteration in range(self.max_iterations):
            new_holes = filled <= 0
            if not np.any(new_holes):
                break

            fill_candidates = self._gather_fill_candidates(
                filled, src_depths, ref_cam, src_cams, new_holes
            )

            filled = self._apply_consensus_filling(
                filled, fill_candidates, new_holes, ref_image
            )

            logger.info(
                f"Iteration {iteration + 1}: {np.sum(filled <= 0)} holes remaining"
            )

        final_holes = filled <= 0
        filled_holes = hole_mask & ~final_holes
        logger.info(f"Filled {np.sum(filled_holes)} / {np.sum(hole_mask)} holes")

        return filled, final_holes

    def _gather_fill_candidates(
        self, ref_depth, src_depths, ref_cam, src_cams, hole_mask
    ):
        h, w = ref_depth.shape
        candidates = {}

        ref_intrinsic = np.array(ref_cam["intrinsic"])
        ref_extrinsic = np.array(ref_cam["extrinsic"])

        hole_y, hole_x = np.where(hole_mask)

        for src_idx, (src_depth, src_cam) in enumerate(zip(src_depths, src_cams)):
            src_intrinsic = np.array(src_cam["intrinsic"])
            src_extrinsic = np.array(src_cam["extrinsic"])

            reproj_x, reproj_y, reproj_depth = self._project_holes_to_source(
                hole_x, hole_y, ref_intrinsic, ref_extrinsic,
                src_intrinsic, src_extrinsic, src_depth
            )

            valid = (
                (reproj_x >= 0) & (reproj_x < w) &
                (reproj_y >= 0) & (reproj_y < h) &
                (reproj_depth > 0)
            )

            for i in np.where(valid)[0]:
                px, py = hole_x[i], hole_y[i]
                depth_val = reproj_depth[i]

                if (py, px) not in candidates:
                    candidates[(py, px)] = []
                candidates[(py, px)].append((depth_val, src_idx))

        return candidates

    def _project_holes_to_source(
        self,
        hole_x, hole_y,
        ref_intrinsic, ref_extrinsic,
        src_intrinsic, src_extrinsic,
        src_depth,
        num_samples=5,
        depth_range=None,
    ):
        if depth_range is None:
            valid_depths = src_depth[src_depth > 0]
            if len(valid_depths) == 0:
                return np.zeros_like(hole_x), np.zeros_like(hole_y), np.zeros_like(hole_x)
            depth_range = (np.percentile(valid_depths, 10), np.percentile(valid_depths, 90))

        n_holes = len(hole_x)
        reproj_x_all = np.zeros((n_holes, num_samples))
        reproj_y_all = np.zeros((n_holes, num_samples))
        reproj_depth_all = np.zeros((n_holes, num_samples))

        for d_idx, depth_sample in enumerate(np.linspace(depth_range[0], depth_range[1], num_samples)):
            depths = np.full(n_holes, depth_sample)

            pts_world = self._pixel_to_world(
                hole_x, hole_y, depths, ref_intrinsic, ref_extrinsic
            )
            src_pts_x, src_pts_y, src_pts_z = self._world_to_pixel(
                pts_world, src_intrinsic, src_extrinsic
            )

            reproj_x_all[:, d_idx] = src_pts_x
            reproj_y_all[:, d_idx] = src_pts_y
            reproj_depth_all[:, d_idx] = src_pts_z

        h, w = src_depth.shape
        valid_mask = (
            (reproj_x_all >= 0) & (reproj_x_all < w - 1) &
            (reproj_y_all >= 0) & (reproj_y_all < h - 1)
        )

        final_depth = np.zeros(n_holes)
        final_x = np.zeros(n_holes)
        final_y = np.zeros(n_holes)

        for i in range(n_holes):
            for d_idx in range(num_samples):
                if not valid_mask[i, d_idx]:
                    continue
                sx = int(reproj_x_all[i, d_idx])
                sy = int(reproj_y_all[i, d_idx])
                src_d = src_depth[sy, sx]

                if src_d > 0:
                    sampled_d = reproj_depth_all[i, d_idx]
                    if abs(src_d - sampled_d) / src_d < self.depth_rel_thresh:
                        final_depth[i] = src_d
                        final_x[i] = sx
                        final_y[i] = sy
                        break

        return final_x, final_y, final_depth

    def _pixel_to_world(self, x, y, depths, intrinsic, extrinsic):
        fx, fy = intrinsic[0, 0], intrinsic[1, 1]
        cx, cy = intrinsic[0, 2], intrinsic[1, 2]
        R = extrinsic[:3, :3]
        t = extrinsic[:3, 3]

        x_cam = (x - cx) * depths / fx
        y_cam = (y - cy) * depths / fy
        z_cam = depths

        pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)
        pts_world = (R.T @ (pts_cam - t).T).T
        return pts_world

    def _world_to_pixel(self, pts_world, intrinsic, extrinsic):
        R = extrinsic[:3, :3]
        t = extrinsic[:3, 3]
        pts_cam = (R @ pts_world.T).T + t

        fx, fy = intrinsic[0, 0], intrinsic[1, 1]
        cx, cy = intrinsic[0, 2], intrinsic[1, 2]

        x = pts_cam[:, 0] * fx / pts_cam[:, 2] + cx
        y = pts_cam[:, 1] * fy / pts_cam[:, 2] + cy
        z = pts_cam[:, 2]

        return x, y, z

    def _apply_consensus_filling(self, depth, candidates, hole_mask, image=None):
        filled = depth.copy()

        if image is not None:
            edge_map = self._compute_edge_strength(image)
        else:
            edge_map = None

        for (y, x), depth_list in candidates.items():
            if not hole_mask[y, x]:
                continue

            if len(depth_list) < self.min_consensus:
                continue

            depths = np.array([d for d, _ in depth_list])

            median_depth = np.median(depths)
            deviations = np.abs(depths - median_depth) / (median_depth + 1e-8)
            consistent = deviations < self.depth_rel_thresh

            if np.sum(consistent) < self.min_consensus:
                continue

            final_depth = np.median(depths[consistent])

            if edge_map is not None:
                edge_weight = edge_map[y, x]
                if edge_weight > 0.5:
                    filled[y, x] = final_depth
                else:
                    filled[y, x] = final_depth
            else:
                filled[y, x] = final_depth

        return filled

    def _compute_edge_strength(self, image):
        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)

        magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
        if magnitude.max() > 0:
            magnitude = magnitude / magnitude.max()

        return magnitude


class MultiViewDepthCompletion:
    def __init__(self):
        self.filler = DepthHoleFiller()

    def complete_all_views(self, depth_maps, cam_dicts, images=None):
        num_views = len(depth_maps)
        completed_depths = []
        hole_masks = []

        for ref_idx in range(num_views):
            ref_depth = depth_maps[ref_idx]
            src_indices = [i for i in range(num_views) if i != ref_idx]
            src_depths = [depth_maps[i] for i in src_indices]
            src_cams = [cam_dicts[i] for i in src_indices]

            ref_img = None
            if images is not None and ref_idx < len(images):
                ref_img = images[ref_idx]

            completed, remaining_holes = self.filler.fill_holes_cross_view(
                ref_depth, src_depths, cam_dicts[ref_idx], src_cams, ref_img
            )

            completed_depths.append(completed)
            hole_masks.append(remaining_holes)

        return completed_depths, hole_masks
