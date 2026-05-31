import logging
import numpy as np
import cv2
import open3d as o3d
from collections import deque

logger = logging.getLogger(__name__)


class MotionDetector:
    def __init__(
        self,
        history_length=30,
        bg_ratio=0.3,
        var_threshold=25,
        min_motion_area=100,
        morph_kernel_size=5,
    ):
        self.history_length = history_length
        self.bg_ratio = bg_ratio
        self.var_threshold = var_threshold
        self.min_motion_area = min_motion_area
        self.morph_kernel_size = morph_kernel_size

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history_length,
            varThreshold=var_threshold,
            detectShadows=True,
        )
        self.initialized = False
        self.frame_count = 0
        self.motion_masks = deque(maxlen=10)

    def detect_motion_mask(self, frame):
        if frame.ndim == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        fg_mask = self.bg_subtractor.apply(gray)

        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.morph_kernel_size, self.morph_kernel_size),
        )
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        filtered_mask = np.zeros_like(fg_mask)
        for contour in contours:
            if cv2.contourArea(contour) >= self.min_motion_area:
                cv2.drawContours(filtered_mask, [contour], -1, 255, -1)

        self.motion_masks.append(filtered_mask)
        self.frame_count += 1
        self.initialized = self.frame_count >= 5

        return filtered_mask

    def get_static_mask(self, frame):
        if not self.initialized:
            h, w = frame.shape[:2]
            return np.ones((h, w), dtype=bool)

        motion_mask = self.detect_motion_mask(frame)
        static_mask = motion_mask == 0
        return static_mask

    def get_consistent_static_mask(self):
        if len(self.motion_masks) == 0:
            return None

        h, w = self.motion_masks[0].shape
        consistent_count = np.zeros((h, w), dtype=np.int32)

        for mask in self.motion_masks:
            consistent_count += (mask == 0).astype(np.int32)

        consistency_ratio = consistent_count / len(self.motion_masks)
        consistent_static = consistency_ratio >= self.bg_ratio

        return consistent_static

    def reset(self):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.history_length,
            varThreshold=self.var_threshold,
            detectShadows=True,
        )
        self.initialized = False
        self.frame_count = 0
        self.motion_masks.clear()


class DynamicObjectRemover:
    def __init__(
        self,
        num_frames=5,
        depth_variance_thresh=0.05,
        motion_thresh=5.0,
        min_consistent_views=3,
    ):
        self.num_frames = num_frames
        self.depth_variance_thresh = depth_variance_thresh
        self.motion_thresh = motion_thresh
        self.min_consistent_views = min_consistent_views

        self.depth_history = deque(maxlen=num_frames)
        self.frame_history = deque(maxlen=num_frames)
        self.motion_detector = MotionDetector()

    def filter_dynamic_from_depth(
        self,
        depth_maps,
        cam_dicts,
        images=None,
    ):
        num_views = len(depth_maps)
        static_depths = []

        for ref_idx in range(num_views):
            ref_depth = depth_maps[ref_idx].copy()
            ref_cam = cam_dicts[ref_idx]
            ref_intrinsic = np.array(ref_cam["intrinsic"])
            ref_extrinsic = np.array(ref_cam["extrinsic"])

            consistency_count = np.zeros(ref_depth.shape, dtype=np.int32)
            depth_sum = np.zeros(ref_depth.shape, dtype=np.float64)
            depth_sq_sum = np.zeros(ref_depth.shape, dtype=np.float64)
            valid_count = np.zeros(ref_depth.shape, dtype=np.int32)

            ref_mask = ref_depth > 0
            consistency_count += ref_mask.astype(np.int32)
            depth_sum += ref_depth * ref_mask
            depth_sq_sum += (ref_depth ** 2) * ref_mask
            valid_count += ref_mask.astype(np.int32)

            for src_idx in range(num_views):
                if src_idx == ref_idx:
                    continue

                src_depth = depth_maps[src_idx]
                src_cam = cam_dicts[src_idx]
                src_intrinsic = np.array(src_cam["intrinsic"])
                src_extrinsic = np.array(src_cam["extrinsic"])

                reproj_mask, reproj_depth = self._reproject_and_compare(
                    ref_depth, src_depth,
                    ref_intrinsic, ref_extrinsic,
                    src_intrinsic, src_extrinsic,
                )

                consistency_count += reproj_mask.astype(np.int32)

                valid_reproj = reproj_mask & (reproj_depth > 0)
                depth_sum += reproj_depth * valid_reproj
                depth_sq_sum += (reproj_depth ** 2) * valid_reproj
                valid_count += valid_reproj.astype(np.int32)

            consistent_mask = consistency_count >= self.min_consistent_views

            depth_variance = np.zeros(ref_depth.shape)
            has_variance = valid_count >= 2
            depth_variance[has_variance] = (
                depth_sq_sum[has_variance] / valid_count[has_variance]
                - (depth_sum[has_variance] / valid_count[has_variance]) ** 2
            )
            low_variance = depth_variance < self.depth_variance_thresh

            static_depth = ref_depth.copy()
            dynamic_mask = ~(consistent_mask & low_variance)
            static_depth[dynamic_mask] = 0

            if images is not None and ref_idx < len(images):
                motion_mask = self.motion_detector.detect_motion_mask(images[ref_idx])
                motion_depth_mask = motion_mask > 0
                static_depth[motion_depth_mask & (ref_depth > 0)] = 0

            removed = np.sum(ref_depth > 0) - np.sum(static_depth > 0)
            logger.info(
                f"View {ref_idx}: removed {removed} dynamic points "
                f"({100 * removed / max(np.sum(ref_depth > 0), 1):.1f}%)"
            )

            static_depths.append(static_depth)

        return static_depths

    def _reproject_and_compare(
        self,
        ref_depth,
        src_depth,
        ref_intrinsic,
        ref_extrinsic,
        src_intrinsic,
        src_extrinsic,
        depth_thresh=0.02,
    ):
        h, w = ref_depth.shape
        mask = np.zeros((h, w), dtype=bool)
        reproj_depth = np.zeros((h, w), dtype=np.float64)

        ref_R = ref_extrinsic[:3, :3]
        ref_t = ref_extrinsic[:3, 3]
        src_R = src_extrinsic[:3, :3]
        src_t = src_extrinsic[:3, 3]

        fx, fy = ref_intrinsic[0, 0], ref_intrinsic[1, 1]
        cx, cy = ref_intrinsic[0, 2], ref_intrinsic[1, 2]

        ys, xs = np.where(ref_depth > 0)
        if len(ys) == 0:
            return mask, reproj_depth

        ds = ref_depth[ys, xs]
        x_cam = (xs - cx) * ds / fx
        y_cam = (ys - cy) * ds / fy
        z_cam = ds

        pts_ref = np.stack([x_cam, y_cam, z_cam], axis=-1)
        pts_world = (ref_R.T @ (pts_ref - ref_t).T).T
        pts_src = (src_R @ pts_world.T).T + src_t

        sfx, sfy = src_intrinsic[0, 0], src_intrinsic[1, 1]
        scx, scy = src_intrinsic[0, 2], src_intrinsic[1, 2]

        src_px = pts_src[:, 0] * sfx / pts_src[:, 2] + scx
        src_py = pts_src[:, 1] * sfy / pts_src[:, 2] + scy

        src_px_int = np.round(src_px).astype(np.int32)
        src_py_int = np.round(src_py).astype(np.int32)

        valid = (
            (src_px_int >= 0) & (src_px_int < w) &
            (src_py_int >= 0) & (src_py_int < h)
        )

        src_d = np.zeros(len(ys))
        src_d[valid] = src_depth[src_py_int[valid], src_px_int[valid]]

        reproj_d = pts_src[:, 2]
        depth_rel = np.abs(reproj_d - src_d) / (np.abs(src_d) + 1e-6)

        consistent = valid & (src_d > 0) & (depth_rel < depth_thresh)
        mask[ys[consistent], xs[consistent]] = True
        reproj_depth[ys, xs] = src_d

        return mask, reproj_depth

    def filter_dynamic_point_cloud(
        self,
        pcd,
        depth_maps,
        cam_dicts,
        images=None,
        voxel_size=0.01,
    ):
        static_depths = self.filter_dynamic_from_depth(
            depth_maps, cam_dicts, images
        )

        all_points = []
        all_colors = []

        for idx, (depth, cam) in enumerate(zip(static_depths, cam_dicts)):
            intrinsic = np.array(cam["intrinsic"])
            extrinsic = np.array(cam["extrinsic"])
            R = extrinsic[:3, :3]
            t = extrinsic[:3, 3]

            fx, fy = intrinsic[0, 0], intrinsic[1, 1]
            cx, cy = intrinsic[0, 2], intrinsic[1, 2]

            valid = depth > 0
            ys, xs = np.where(valid)
            ds = depth[valid]

            x_cam = (xs - cx) * ds / fx
            y_cam = (ys - cy) * ds / fy
            z_cam = ds

            pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)
            pts_world = (R.T @ (pts_cam - t).T).T
            all_points.append(pts_world)

            if images is not None and idx < len(images):
                img = images[idx]
                if img.max() > 1.0:
                    img = img.astype(np.float64) / 255.0
                all_colors.append(img[ys, xs])

        if not all_points:
            logger.warning("No static points found")
            return None

        fused = np.vstack(all_points)
        colors_fused = np.vstack(all_colors) if all_colors else None

        static_pcd = o3d.geometry.PointCloud()
        static_pcd.points = o3d.utility.Vector3dVector(fused)
        if colors_fused is not None:
            static_pcd.colors = o3d.utility.Vector3dVector(colors_fused)

        static_pcd = static_pcd.voxel_down_sample(voxel_size)
        static_pcd, _ = static_pcd.remove_statistical_outlier(
            nb_neighbors=20, std_ratio=2.0
        )

        logger.info(f"Static point cloud: {len(static_pcd.points)} points")
        return static_pcd
