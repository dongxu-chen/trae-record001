import numpy as np
import cv2
from typing import Optional, Tuple


class DenseInterpolator:
    """
    稀疏光流稠密化插值器

    将稀疏光流点插值到完整的稠密光流场。
    支持多种插值方法:
        - 'inverse_distance': 反距离加权插值
        - 'linear': 线性插值 (需要三角形剖分)
        - 'gaussian': 高斯核加权
        - 'natural_neighbor': 自然邻域插值
    """

    def __init__(
        self,
        method: str = 'inverse_distance',
        power: float = 2.0,
        smoothing: float = 1.0,
        kernel_radius: int = 15,
        num_iterations: int = 100,
    ):
        self.method = method
        self.power = power
        self.smoothing = smoothing
        self.kernel_radius = kernel_radius
        self.num_iterations = num_iterations

    def interpolate(
        self,
        sparse_points: np.ndarray,
        sparse_vectors: np.ndarray,
        output_size: Tuple[int, int],
        valid_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        将稀疏光流插值到稠密光流场

        参数:
            sparse_points: 稀疏点坐标 (N, 2), 格式为 (x, y)
            sparse_vectors: 稀疏点的光流向量 (N, 2), 格式为 (u, v)
            output_size: 输出光流场大小 (H, W)
            valid_mask: 有效像素掩码 (H, W), 可选

        返回:
            稠密光流场 (H, W, 2)
        """
        h, w = output_size

        if len(sparse_points) == 0:
            return np.zeros((h, w, 2), dtype=np.float32)

        if len(sparse_points) < 3:
            return self._simple_fill(sparse_points, sparse_vectors, output_size)

        if self.method == 'inverse_distance':
            return self._inverse_distance(sparse_points, sparse_vectors, output_size)
        elif self.method == 'gaussian':
            return self._gaussian_kernel(sparse_points, sparse_vectors, output_size)
        elif self.method == 'diffusion':
            return self._diffusion_interpolation(sparse_points, sparse_vectors, output_size)
        elif self.method == 'linear':
            return self._linear_interpolation(sparse_points, sparse_vectors, output_size)
        else:
            return self._inverse_distance(sparse_points, sparse_vectors, output_size)

    def _simple_fill(
        self,
        points: np.ndarray,
        vectors: np.ndarray,
        output_size: Tuple[int, int],
    ) -> np.ndarray:
        """简单填充: 将少量点的向量扩展到最近邻区域"""
        h, w = output_size
        flow = np.zeros((h, w, 2), dtype=np.float32)

        if len(points) == 0:
            return flow

        yy, xx = np.mgrid[0:h, 0:w]
        dists = np.sqrt((xx[..., None] - points[:, 0]) ** 2 + (yy[..., None] - points[:, 1]) ** 2)
        nearest_idx = np.argmin(dists, axis=2)

        flow[..., 0] = vectors[nearest_idx, 0]
        flow[..., 1] = vectors[nearest_idx, 1]

        return flow

    def _inverse_distance(
        self,
        points: np.ndarray,
        vectors: np.ndarray,
        output_size: Tuple[int, int],
    ) -> np.ndarray:
        """
        反距离加权插值 (IDW)

        公式: w_i = 1 / d_i^p, 其中 d_i 是距离, p 是幂次
        """
        h, w = output_size
        flow = np.zeros((h, w, 2), dtype=np.float32)

        if len(points) == 0:
            return flow

        chunk_size = 50
        for y_start in range(0, h, chunk_size):
            y_end = min(y_start + chunk_size, h)
            for x_start in range(0, w, chunk_size):
                x_end = min(x_start + chunk_size, w)

                yy, xx = np.mgrid[y_start:y_end, x_start:x_end]
                coords = np.stack([xx, yy], axis=-1).reshape(-1, 2)

                dists = np.sqrt(
                    (coords[:, None, 0] - points[None, :, 0]) ** 2 +
                    (coords[:, None, 1] - points[None, :, 1]) ** 2
                )
                dists = np.maximum(dists, 1e-8)

                weights = 1.0 / (dists ** self.power)
                weights_sum = weights.sum(axis=1, keepdims=True)
                weights = weights / np.maximum(weights_sum, 1e-8)

                u_chunk = (weights * vectors[None, :, 0]).sum(axis=1)
                v_chunk = (weights * vectors[None, :, 1]).sum(axis=1)

                flow[y_start:y_end, x_start:x_end, 0] = u_chunk.reshape(y_end - y_start, x_end - x_start)
                flow[y_start:y_end, x_start:x_end, 1] = v_chunk.reshape(y_end - y_start, x_end - x_start)

        return flow

    def _gaussian_kernel(
        self,
        points: np.ndarray,
        vectors: np.ndarray,
        output_size: Tuple[int, int],
    ) -> np.ndarray:
        """
        高斯核加权插值

        公式: w_i = exp(-d_i² / (2σ²))
        """
        h, w = output_size
        flow = np.zeros((h, w, 2), dtype=np.float32)

        if len(points) == 0:
            return flow

        sigma = self.smoothing

        chunk_size = 50
        for y_start in range(0, h, chunk_size):
            y_end = min(y_start + chunk_size, h)
            for x_start in range(0, w, chunk_size):
                x_end = min(x_start + chunk_size, w)

                yy, xx = np.mgrid[y_start:y_end, x_start:x_end]
                coords = np.stack([xx, yy], axis=-1).reshape(-1, 2)

                dists_sq = (
                    (coords[:, None, 0] - points[None, :, 0]) ** 2 +
                    (coords[:, None, 1] - points[None, :, 1]) ** 2
                )

                weights = np.exp(-dists_sq / (2 * sigma ** 2))
                weights_sum = weights.sum(axis=1, keepdims=True)
                weights = weights / np.maximum(weights_sum, 1e-8)

                u_chunk = (weights * vectors[None, :, 0]).sum(axis=1)
                v_chunk = (weights * vectors[None, :, 1]).sum(axis=1)

                flow[y_start:y_end, x_start:x_end, 0] = u_chunk.reshape(y_end - y_start, x_end - x_start)
                flow[y_start:y_end, x_start:x_end, 1] = v_chunk.reshape(y_end - y_start, x_end - x_start)

        return flow

    def _diffusion_interpolation(
        self,
        points: np.ndarray,
        vectors: np.ndarray,
        output_size: Tuple[int, int],
    ) -> np.ndarray:
        """
        基于扩散方程的插值

        求解方程: ∇²(u) = 0, 边界条件为稀疏点的光流值
        """
        h, w = output_size
        u = np.zeros((h, w), dtype=np.float32)
        v = np.zeros((h, w), dtype=np.float32)

        mask = np.zeros((h, w), dtype=np.float32)
        for pt, vec in zip(points, vectors):
            x, y = int(pt[0]), int(pt[1])
            if 0 <= x < w and 0 <= y < h:
                u[y, x] = vec[0]
                v[y, x] = vec[1]
                mask[y, x] = 1.0

        kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.float32) / 4.0

        for _ in range(self.num_iterations):
            u_avg = cv2.filter2D(u, -1, kernel)
            v_avg = cv2.filter2D(v, -1, kernel)

            u = np.where(mask > 0, u, u_avg)
            v = np.where(mask > 0, v, v_avg)

        return np.stack([u, v], axis=-1)

    def _linear_interpolation(
        self,
        points: np.ndarray,
        vectors: np.ndarray,
        output_size: Tuple[int, int],
    ) -> np.ndarray:
        """
        线性插值 (Delaunay 三角剖分)

        在三角形内部进行线性插值
        """
        h, w = output_size
        flow = np.zeros((h, w, 2), dtype=np.float32)

        if len(points) < 3:
            return self._inverse_distance(points, vectors, output_size)

        try:
            points_int = points.astype(np.int32)
            rect = (0, 0, w, h)
            subdiv = cv2.Subdiv2D(rect)
            for pt in points_int:
                subdiv.insert((float(pt[0]), float(pt[1])))

            triangles = subdiv.getTriangleList()
            triangles = triangles.reshape(-1, 3, 2)

            valid = np.all(triangles[:, :, 0] >= 0, axis=1) & \
                    np.all(triangles[:, :, 0] < w, axis=1) & \
                    np.all(triangles[:, :, 1] >= 0, axis=1) & \
                    np.all(triangles[:, :, 1] < h, axis=1)

            for tri in triangles[valid]:
                pts_int = tri.astype(np.int32)
                x_min = max(pts_int[:, 0].min(), 0)
                x_max = min(pts_int[:, 0].max(), w - 1)
                y_min = max(pts_int[:, 1].min(), 0)
                y_max = min(pts_int[:, 1].max(), h - 1)

                if x_max < x_min or y_max < y_min:
                    continue

                yy, xx = np.mgrid[y_min:y_max + 1, x_min:x_max + 1]

                v0 = pts_int[2] - pts_int[0]
                v1 = pts_int[1] - pts_int[0]
                v2 = np.stack([xx, yy], axis=-1) - pts_int[0]

                dot00 = np.dot(v0, v0)
                dot01 = np.dot(v0, v1)
                dot02 = (v2[..., 0] * v0[0] + v2[..., 1] * v0[1])
                dot11 = np.dot(v1, v1)
                dot12 = (v2[..., 0] * v1[0] + v2[..., 1] * v1[1])

                denom = dot00 * dot11 - dot01 * dot01
                if abs(denom) < 1e-8:
                    continue

                u = (dot11 * dot02 - dot01 * dot12) / denom
                v = (dot00 * dot12 - dot01 * dot02) / denom

                mask = (u >= 0) & (v >= 0) & (u + v <= 1)

                if mask.any():
                    tri_vectors = np.array([
                        vectors[np.where((points_int == pts_int[i]).all(axis=1))[0][0]]
                        if np.where((points_int == pts_int[i]).all(axis=1))[0].size > 0
                        else [0, 0]
                        for i in range(3)
                    ])

                    flow_u = (1 - u - v) * tri_vectors[0, 0] + u * tri_vectors[1, 0] + v * tri_vectors[2, 0]
                    flow_v = (1 - u - v) * tri_vectors[0, 1] + u * tri_vectors[1, 1] + v * tri_vectors[2, 1]

                    flow[y_min:y_max + 1, x_min:x_max + 1, 0][mask] = flow_u[mask]
                    flow[y_min:y_max + 1, x_min:x_max + 1, 1][mask] = flow_v[mask]

        except Exception:
            return self._inverse_distance(points, vectors, output_size)

        return flow


class SparseToDense:
    """
    稀疏光流到稠密光流的完整转换管线

    支持特征点提取 → 光流跟踪 → 稠密化插值
    """

    def __init__(
        self,
        feature_detector: str = 'shi_tomasi',
        max_corners: int = 1000,
        quality_level: float = 0.01,
        min_distance: int = 10,
        interpolator: Optional[DenseInterpolator] = None,
    ):
        self.feature_detector = feature_detector
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance

        self.interpolator = interpolator or DenseInterpolator(method='inverse_distance', power=2.0)
        self.prev_pts = None
        self.prev_gray = None

    def compute(self, frame: np.ndarray, prev_frame: Optional[np.ndarray] = None) -> np.ndarray:
        """
        从两帧图像计算稠密光流

        参数:
            frame: 当前帧 (BGR 或灰度)
            prev_frame: 上一帧

        返回:
            稠密光流场 (H, W, 2)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        if prev_frame is not None:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY) if len(prev_frame.shape) == 3 else prev_frame
        elif self.prev_gray is not None:
            prev_gray = self.prev_gray
        else:
            self.prev_gray = gray
            h, w = gray.shape
            return np.zeros((h, w, 2), dtype=np.float32)

        pts = self._detect_features(prev_gray)

        if len(pts) < 10:
            self.prev_gray = gray
            return np.zeros(gray.shape + (2,), dtype=np.float32)

        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, gray, pts, None,
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )

        good = status.ravel() == 1
        sparse_pts = pts[good].reshape(-1, 2)
        sparse_vecs = next_pts[good].reshape(-1, 2) - sparse_pts

        dense_flow = self.interpolator.interpolate(sparse_pts, sparse_vecs, gray.shape)

        self.prev_gray = gray
        self.prev_pts = next_pts[good].reshape(-1, 1, 2)

        return dense_flow

    def _detect_features(self, gray: np.ndarray) -> np.ndarray:
        """特征点检测"""
        if self.feature_detector == 'shi_tomasi':
            pts = cv2.goodFeaturesToTrack(
                gray,
                maxCorners=self.max_corners,
                qualityLevel=self.quality_level,
                minDistance=self.min_distance,
                blockSize=7,
            )
        elif self.feature_detector == 'fast':
            fast = cv2.FastFeatureDetector_create(threshold=20, nonmaxSuppression=True)
            kps = fast.detect(gray, None)
            pts = np.array([[kp.pt] for kp in kps], dtype=np.float32)
        elif self.feature_detector == 'sift':
            sift = cv2.SIFT_create(nfeatures=self.max_corners)
            kps = sift.detect(gray, None)
            pts = np.array([[kp.pt] for kp in kps], dtype=np.float32)
        else:
            pts = cv2.goodFeaturesToTrack(
                gray,
                maxCorners=self.max_corners,
                qualityLevel=self.quality_level,
                minDistance=self.min_distance,
                blockSize=7,
            )

        return pts if pts is not None else np.array([])