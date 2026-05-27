import numpy as np
import cv2
from typing import Optional, Tuple, Dict, Any


class SceneFlowEstimator:
    """
    场景流估计器

    结合2D光流和深度图计算3D场景流。

    场景流是光流在3D空间的扩展, 描述每个3D点的运动向量 (X, Y, Z)。

    核心公式:
        给定:
            (x1, y1) = 上一帧像素坐标
            (x2, y2) = 当前帧像素坐标 = (x1 + u, y1 + v)
            Z1 = 上一帧深度
            Z2 = 当前帧深度
            fx, fy = 相机焦距
            cx, cy = 相机光心

        3D点:
            X1 = (x1 - cx) * Z1 / fx
            Y1 = (y1 - cy) * Z1 / fy
            Z1 = Z1

            X2 = (x2 - cx) * Z2 / fx
            Y2 = (y2 - cy) * Z2 / fy
            Z2 = Z2

        场景流:
            (ΔX, ΔY, ΔZ) = (X2 - X1, Y2 - Y1, Z2 - Z1)
    """

    def __init__(
        self,
        fx: float = 500.0,
        fy: float = 500.0,
        cx: Optional[float] = None,
        cy: Optional[float] = None,
    ):
        self.fx = fx
        self.fy = fy
        self._cx = cx
        self._cy = cy

    def compute(
        self,
        flow_2d: np.ndarray,
        depth_prev: np.ndarray,
        depth_curr: Optional[np.ndarray] = None,
        depth_prev_frame: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        计算场景流

        参数:
            flow_2d: 2D光流场 (H, W, 2)
            depth_prev: 上一帧深度图 (H, W)
            depth_curr: 当前帧深度图 (H, W), 如果为 None 则使用 depth_prev
            depth_prev_frame: 上一帧图像 (可选, 用于深度图)

        返回:
            场景流场 (H, W, 3), 通道为 (ΔX, ΔY, ΔZ)
        """
        h, w = flow_2d.shape[:2]

        if self._cx is None:
            self._cx = w / 2.0
        if self._cy is None:
            self._cy = h / 2.0

        if depth_curr is None:
            depth_curr = depth_prev

        u = flow_2d[..., 0]
        v = flow_2d[..., 1]

        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)

        X1 = (xs - self._cx) * depth_prev / self.fx
        Y1 = (ys - self._cy) * depth_prev / self.fy
        Z1 = depth_prev

        xs_curr = xs + u
        ys_curr = ys + v

        xs_curr_int = np.clip(xs_curr.astype(np.int32), 0, w - 1)
        ys_curr_int = np.clip(ys_curr.astype(np.int32), 0, h - 1)

        Z2 = depth_curr[ys_curr_int, xs_curr_int]

        X2 = (xs_curr - self._cx) * Z2 / self.fx
        Y2 = (ys_curr - self._cy) * Z2 / self.fy

        dX = X2 - X1
        dY = Y2 - Y1
        dZ = Z2 - Z1

        scene_flow = np.stack([dX, dY, dZ], axis=-1)

        valid = (depth_prev > 0) & (Z2 > 0)
        scene_flow[~valid] = 0

        return scene_flow.astype(np.float32)

    def compute_from_disparity(
        self,
        flow_2d: np.ndarray,
        disparity: np.ndarray,
        baseline: float = 0.1,
    ) -> np.ndarray:
        """
        从视差图计算场景流

        参数:
            flow_2d: 2D光流场 (H, W, 2)
            disparity: 视差图 (H, W)
            baseline: 相机基线距离 (米)

        返回:
            场景流场 (H, W, 3)
        """
        depth = self.fx * baseline / (disparity + 1e-8)
        return self.compute(flow_2d, depth)

    def visualize_scene_flow(
        self,
        scene_flow: np.ndarray,
        max_depth: float = 10.0,
    ) -> np.ndarray:
        """
        可视化场景流

        将3D运动向量投影到2D图像平面进行可视化

        参数:
            scene_flow: 场景流场 (H, W, 3)
            max_depth: 最大深度 (用于归一化)

        返回:
            可视化图像 (H, W, 3)
        """
        h, w = scene_flow.shape[:2]

        dX = scene_flow[..., 0]
        dY = scene_flow[..., 1]
        dZ = scene_flow[..., 2]

        magnitude_3d = np.sqrt(dX ** 2 + dY ** 2 + dZ ** 2)

        angle_xy = np.arctan2(dY, dX)
        angle_z = np.arctan2(np.sqrt(dX ** 2 + dY ** 2), dZ)

        hsv = np.zeros((h, w, 3), dtype=np.uint8)

        hsv[..., 0] = (angle_xy * 180 / np.pi / 2 + 90).astype(np.uint8)
        hsv[..., 1] = np.clip(angle_z / np.pi * 255, 0, 255).astype(np.uint8)
        hsv[..., 2] = np.clip(magnitude_3d / max_depth * 255, 0, 255).astype(np.uint8)

        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        return bgr

    def compute_point_cloud(
        self,
        depth: np.ndarray,
        frame: Optional[np.ndarray] = None,
        scene_flow: Optional[np.ndarray] = None,
        stride: int = 4,
    ) -> Dict[str, np.ndarray]:
        """
        计算点云和可选的运动点云

        参数:
            depth: 深度图 (H, W)
            frame: 图像 (H, W, 3)
            scene_flow: 场景流场 (H, W, 3)
            stride: 点云采样步长

        返回:
            包含点云数据的字典
        """
        h, w = depth.shape[:2]

        ys, xs = np.mgrid[0:h:stride, 0:w:stride].astype(np.float32)
        depth_sampled = depth[ys.astype(np.int32), xs.astype(np.int32)]

        valid = depth_sampled > 0

        X = (xs - self._cx) * depth_sampled / self.fx
        Y = (ys - self._cy) * self.fy
        Z = depth_sampled

        points = np.stack([X, Y, Z], axis=-1)

        result = {
            'points': points[valid],
        }

        if frame is not None:
            colors = frame[ys.astype(np.int32), xs.astype(np.int32)]
            result['colors'] = colors[valid]

        if scene_flow is not None:
            flow_sampled = scene_flow[ys.astype(np.int32), xs.astype(np.int32)]
            result['motion_prev'] = result['points']
            result['motion_curr'] = result['points'] + flow_sampled[valid]

        return result


class DepthFlowFusion:
    """
    光流-深度融合

    结合光流和深度信息进行更精确的运动估计
    """

    def __init__(
        self,
        fx: float = 500.0,
        fy: float = 500.0,
        cx: Optional[float] = None,
        cy: Optional[float] = None,
    ):
        self.fx = fx
        self.fy = fy
        self._cx = cx
        self._cy = cy

    def estimate_3d_motion(
        self,
        flow: np.ndarray,
        depth_prev: np.ndarray,
        depth_curr: np.ndarray,
    ) -> Dict[str, Any]:
        """
        估计3D运动参数

        参数:
            flow: 2D光流场 (H, W, 2)
            depth_prev: 上一帧深度图 (H, W)
            depth_curr: 当前帧深度图 (H, W)

        返回:
            包含3D运动参数的字典
        """
        h, w = flow.shape[:2]

        if self._cx is None:
            self._cx = w / 2.0
        if self._cy is None:
            self._cy = h / 2.0

        u = flow[..., 0]
        v = flow[..., 1]

        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)

        valid = (depth_prev > 0) & (depth_curr > 0)

        X1 = (xs - self._cx) * depth_prev / self.fx
        Y1 = (ys - self._cy) * depth_prev / self.fy
        Z1 = depth_prev

        xs_curr = xs + u
        ys_curr = ys + v
        xs_curr_clipped = np.clip(xs_curr.astype(np.int32), 0, w - 1)
        ys_curr_clipped = np.clip(ys_curr.astype(np.int32), 0, h - 1)

        Z2 = depth_curr[ys_curr_clipped, xs_curr_clipped]

        X2 = (xs_curr - self._cx) * Z2 / self.fx
        Y2 = (ys_curr - self._cy) * Z2 / self.fy

        X1_valid = X1[valid]
        Y1_valid = Y1[valid]
        Z1_valid = Z1[valid]

        X2_valid = X2[valid]
        Y2_valid = Y2[valid]
        Z2_valid = Z2[valid]

        result = {
            'translation': np.array([
                float(np.mean(X2_valid - X1_valid)),
                float(np.mean(Y2_valid - Y1_valid)),
                float(np.mean(Z2_valid - Z1_valid)),
            ]),
            'rotation': self._estimate_rotation(
                X1_valid, Y1_valid, Z1_valid, X2_valid, Y2_valid, Z2_valid),
            'scale': float(
                np.mean(np.sqrt(X2_valid**2 + Y2_valid**2 + Z2_valid**2)) /
                (np.mean(np.sqrt(X1_valid**2 + Y1_valid**2 + Z1_valid**2)) + 1e-8)
            ),
        }

        return result

    def _estimate_rotation(
        self,
        X1: np.ndarray,
        Y1: np.ndarray,
        Z1: np.ndarray,
        X2: np.ndarray,
        Y2: np.ndarray,
        Z2: np.ndarray,
    ) -> np.ndarray:
        """
        估计旋转参数 (简化版)

        使用点云配准估计旋转矩阵
        """
        if len(X1) < 10:
            return np.eye(3)

        centroid1 = np.array([X1.mean(), Y1.mean(), Z1.mean()])
        centroid2 = np.array([X2.mean(), Y2.mean(), Z2.mean()])

        X1_centered = np.stack([X1, Y1, Z1], axis=1) - centroid1
        X2_centered = np.stack([X2, Y2, Z2], axis=1) - centroid2

        H = X1_centered.T @ X2_centered

        U, S, Vt = np.linalg.svd(H)

        R = Vt.T @ U.T

        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        return R

    def project_3d_to_2d(
        self,
        points_3d: np.ndarray,
        depth: np.ndarray,
    ) -> np.ndarray:
        """
        将3D点投影回2D图像

        参数:
            points_3d: 3D点 (N, 3)
            depth: 深度图 (H, W)

        返回:
            2D像素坐标 (N, 2)
        """
        X = points_3d[:, 0]
        Y = points_3d[:, 1]
        Z = points_3d[:, 2]

        x = X * self.fx / (Z + 1e-8) + self._cx
        y = Y * self.fy / (Z + 1e-8) + self._cy

        return np.stack([x, y], axis=-1)

    def compute_depth_from_stereo(
        self,
        img_left: np.ndarray,
        img_right: np.ndarray,
        num_disparities: int = 128,
        block_size: int = 9,
    ) -> np.ndarray:
        """
        从立体图像对计算深度图

        参数:
            img_left: 左图像 (H, W)
            img_right: 右图像 (H, W)
            num_disparities: 最大视差
            block_size: 匹配块大小

        返回:
            深度图 (H, W)
        """
        if len(img_left.shape) == 3:
            gray_left = cv2.cvtColor(img_left, cv2.COLOR_BGR2GRAY)
            gray_right = cv2.cvtColor(img_right, cv2.COLOR_BGR2GRAY)
        else:
            gray_left = img_left
            gray_right = img_right

        stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=num_disparities,
            blockSize=block_size,
            P1=8 * 3 * block_size ** 2,
            P2=32 * 3 * block_size ** 2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=32,
        )

        disparity = stereo.compute(gray_left, gray_right).astype(np.float32) / 16.0

        return disparity