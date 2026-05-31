import logging
import numpy as np
import cv2
import open3d as o3d
from modules.depth_estimation import DepthEstimator
from config import RECONSTRUCTION_CONFIG

logger = logging.getLogger(__name__)


class AdaptivePointCloudFusion:
    def __init__(self, config=None):
        self.config = config or RECONSTRUCTION_CONFIG
        self.prob_threshold = self.config["prob_threshold"]
        self.num_consistent = self.config["num_consistent"]
        self.base_voxel_size = self.config["voxel_size"]
        self.high_texture_scale = 0.5
        self.low_texture_scale = 2.0
        self.texture_threshold = 0.15

    def fuse_depth_maps_adaptive(
        self,
        depth_maps,
        prob_maps,
        cam_dicts,
        image_paths=None,
        use_adaptive=True,
    ):
        num_views = len(depth_maps)
        all_points = []
        all_colors = []
        all_texture_scores = []

        images = {}
        texture_maps = {}
        if image_paths is not None:
            for idx, path in enumerate(image_paths):
                img = cv2.imread(path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    h, w = depth_maps[idx].shape
                    img = cv2.resize(img, (w, h))
                    images[idx] = img
                    if use_adaptive:
                        texture_maps[idx] = self._compute_texture_map(img)

        for ref_idx in range(num_views):
            depth_map = depth_maps[ref_idx]
            prob_map = prob_maps[ref_idx]

            filtered_depth, mask = DepthEstimator.filter_depth(
                depth_map, prob_map, self.prob_threshold
            )

            consistency_mask = self._check_consistency(
                ref_idx, filtered_depth, depth_maps, cam_dicts
            )

            final_mask = mask & consistency_mask
            filtered_depth[~final_mask] = 0

            cam = cam_dicts[ref_idx]
            intrinsic = np.array(cam["intrinsic"])
            extrinsic = np.array(cam["extrinsic"])

            img = images.get(ref_idx)
            texture_map = texture_maps.get(ref_idx)

            pts, colors, texture_scores = self._depth_to_points_with_texture(
                filtered_depth, intrinsic, extrinsic, image=img, texture_map=texture_map
            )

            if len(pts) > 0:
                all_points.append(pts)
                if colors is not None:
                    all_colors.append(colors)
                if texture_scores is not None:
                    all_texture_scores.append(texture_scores)
                logger.info(
                    f"View {ref_idx}: {len(pts)} points after filtering "
                    f"({np.sum(final_mask)} pixels passed)"
                )

        if len(all_points) == 0:
            logger.warning("No valid points found in any view")
            return None, None, None

        fused_points = np.vstack(all_points)
        fused_colors = np.vstack(all_colors) if all_colors else None
        fused_texture = np.concatenate(all_texture_scores) if all_texture_scores else None

        logger.info(
            f"Fused point cloud: {len(fused_points)} points from {num_views} views"
        )
        return fused_points, fused_colors, fused_texture

    def _compute_texture_map(self, image, kernel_size=7):
        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        gray = gray.astype(np.float32)

        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(grad_x ** 2 + grad_y ** 2)

        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)

        texture = gradient_mag + 0.5 * np.abs(laplacian)

        if texture.max() > 0:
            texture = texture / texture.max()

        texture = cv2.GaussianBlur(texture, (kernel_size, kernel_size), 0)

        return texture

    def _depth_to_points_with_texture(self, depth_map, intrinsic, extrinsic, image=None, texture_map=None):
        h, w = depth_map.shape
        fx = intrinsic[0, 0]
        fy = intrinsic[1, 1]
        cx = intrinsic[0, 2]
        cy = intrinsic[1, 2]

        R = extrinsic[:3, :3]
        t = extrinsic[:3, 3]

        mask = depth_map > 0
        ys, xs = np.where(mask)
        ds = depth_map[mask]

        x_cam = (xs - cx) * ds / fx
        y_cam = (ys - cy) * ds / fy
        z_cam = ds

        pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)
        pts_world = (R.T @ (pts_cam - t).T).T

        colors = None
        if image is not None:
            if image.max() > 1.0:
                image = image.astype(np.float32) / 255.0
            colors = image[ys, xs]

        texture_scores = None
        if texture_map is not None:
            texture_scores = texture_map[ys, xs]

        return pts_world, colors, texture_scores

    def adaptive_voxel_downsample(self, points, colors=None, texture_scores=None):
        if texture_scores is None:
            logger.info("No texture scores, using uniform downsampling")
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            if colors is not None:
                pcd.colors = o3d.utility.Vector3dVector(colors)
            pcd = pcd.voxel_down_sample(self.base_voxel_size)
            return pcd

        high_texture_mask = texture_scores > self.texture_threshold
        low_texture_mask = ~high_texture_mask

        logger.info(
            f"High texture points: {np.sum(high_texture_mask)} ({100*np.mean(high_texture_mask):.1f}%), "
            f"Low texture points: {np.sum(low_texture_mask)}"
        )

        high_voxel = self.base_voxel_size * self.high_texture_scale
        low_voxel = self.base_voxel_size * self.low_texture_scale

        pcd_high = self._masked_downsample(
            points, colors, texture_scores, high_texture_mask, high_voxel
        )
        pcd_low = self._masked_downsample(
            points, colors, texture_scores, low_texture_mask, low_voxel
        )

        if pcd_high is not None and pcd_low is not None:
            pcd_combined = pcd_high + pcd_low
        elif pcd_high is not None:
            pcd_combined = pcd_high
        elif pcd_low is not None:
            pcd_combined = pcd_low
        else:
            pcd_combined = o3d.geometry.PointCloud()

        logger.info(
            f"Adaptive downsample: {len(pcd_combined.points)} points "
            f"(high-res voxel: {high_voxel:.4f}, low-res voxel: {low_voxel:.4f})"
        )
        return pcd_combined

    def _masked_downsample(self, points, colors, texture, mask, voxel_size):
        if not np.any(mask):
            return None

        pts_masked = points[mask]
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts_masked)

        if colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(colors[mask])

        pcd = pcd.voxel_down_sample(voxel_size)
        return pcd

    def _check_consistency(self, ref_idx, ref_depth, all_depths, cam_dicts):
        h, w = ref_depth.shape
        consistency_count = np.zeros((h, w), dtype=np.int32)
        num_other = len(all_depths) - 1

        if num_other == 0:
            return ref_depth > 0

        ref_cam = cam_dicts[ref_idx]
        ref_intrinsic = np.array(ref_cam["intrinsic"])
        ref_extrinsic = np.array(ref_cam["extrinsic"])

        for src_idx in range(len(all_depths)):
            if src_idx == ref_idx:
                continue

            src_cam = cam_dicts[src_idx]
            src_intrinsic = np.array(src_cam["intrinsic"])
            src_extrinsic = np.array(src_cam["extrinsic"])
            src_depth = all_depths[src_idx]

            reproj_mask = self._geometric_consistency_check(
                ref_depth, src_depth, ref_intrinsic, ref_extrinsic, src_intrinsic, src_extrinsic
            )
            consistency_count += reproj_mask.astype(np.int32)

        consistency_mask = consistency_count >= min(self.num_consistent, num_other)
        return consistency_mask

    def _geometric_consistency_check(
        self,
        ref_depth,
        src_depth,
        ref_intrinsic,
        ref_extrinsic,
        src_intrinsic,
        src_extrinsic,
        depth_thresh=0.01,
    ):
        h, w = ref_depth.shape
        mask = np.zeros((h, w), dtype=bool)

        ref_R = ref_extrinsic[:3, :3]
        ref_t = ref_extrinsic[:3, 3]
        src_R = src_extrinsic[:3, :3]
        src_t = src_extrinsic[:3, 3]

        fx, fy = ref_intrinsic[0, 0], ref_intrinsic[1, 1]
        cx, cy = ref_intrinsic[0, 2], ref_intrinsic[1, 2]

        ys, xs = np.where(ref_depth > 0)
        if len(ys) == 0:
            return mask

        ds = ref_depth[ys, xs]
        x_cam = (xs - cx) * ds / fx
        y_cam = (ys - cy) * ds / fy
        z_cam = ds

        pts_ref = np.stack([x_cam, y_cam, z_cam], axis=-1)
        pts_world = (ref_R.T @ (pts_ref - ref_t).T).T
        pts_src = (src_R @ pts_world.T).T + src_t

        sfx, sfy = src_intrinsic[0, 0], src_intrinsic[1, 1]
        scx, scy = src_intrinsic[0, 2], src_intrinsic[1, 2]

        src_x = pts_src[:, 0] * sfx / pts_src[:, 2] + scx
        src_y = pts_src[:, 1] * sfy / pts_src[:, 2] + scy

        src_x_int = np.round(src_x).astype(np.int32)
        src_y_int = np.round(src_y).astype(np.int32)

        valid = (
            (src_x_int >= 0) & (src_x_int < w) & (src_y_int >= 0) & (src_y_int < h)
        )

        src_d = np.zeros(len(ys))
        src_d[valid] = src_depth[src_y_int[valid], src_x_int[valid]]

        reproj_depth = pts_src[:, 2]
        depth_diff = np.abs(reproj_depth - src_d)
        depth_rel = depth_diff / (np.abs(src_d) + 1e-6)

        consistent = valid & (src_d > 0) & (depth_rel < depth_thresh)
        mask[ys[consistent], xs[consistent]] = True

        return mask

    def filter_point_cloud_adaptive(
        self,
        pcd,
        nb_neighbors=20,
        std_ratio=2.0,
        radius_multiplier=4,
    ):
        logger.info(f"Before filtering: {len(pcd.points)} points")

        pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
        logger.info(f"After statistical outlier removal: {len(pcd.points)} points")

        radius = self.base_voxel_size * radius_multiplier
        cl, ind = pcd.remove_radius_outlier(nb_points=4, radius=radius)
        pcd = pcd.select_by_index(ind)
        logger.info(f"After radius outlier removal: {len(pcd.points)} points")

        return pcd

    def estimate_normals(self, pcd, voxel_size=None):
        if voxel_size is None:
            voxel_size = self.base_voxel_size

        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=30)
        )
        pcd.orient_normals_consistent_tangent_plane(k=15)

        return pcd

    def save_point_cloud(self, pcd, output_path, save_ply=True, save_pcd=True):
        base_path = output_path.rsplit(".", 1)[0]

        if save_ply:
            ply_path = base_path + ".ply"
            o3d.io.write_point_cloud(ply_path, pcd)
            logger.info(f"Saved PLY: {ply_path}")

        if save_pcd:
            pcd_path = base_path + ".pcd"
            o3d.io.write_point_cloud(pcd_path, pcd)
            logger.info(f"Saved PCD: {pcd_path}")

        return pcd
