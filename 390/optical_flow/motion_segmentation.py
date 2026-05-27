import numpy as np
import cv2
from typing import Optional, Tuple, List
from sklearn.cluster import DBSCAN, KMeans


class MotionSegmentation:
    """
    基于光流的运动分割

    将光流场中的像素根据运动模式聚类，分离出不同运动的物体。
    支持多种聚类方法:
        - 'dbscan': 密度聚类 (自动发现聚类数)
        - 'kmeans': K均值聚类 (需指定聚类数)
        - 'hierarchical': 层次聚类
        - 'spatial': 空间-运动联合聚类
    """

    def __init__(
        self,
        method: str = 'dbscan',
        n_clusters: int = 3,
        eps: float = 0.5,
        min_samples: int = 50,
        spatial_weight: float = 0.3,
        motion_weight: float = 1.0,
    ):
        self.method = method
        self.n_clusters = n_clusters
        self.eps = eps
        self.min_samples = min_samples
        self.spatial_weight = spatial_weight
        self.motion_weight = motion_weight

    def segment(
        self,
        flow: np.ndarray,
        frame: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        对光流场进行运动分割

        参数:
            flow: 光流场 (H, W, 2)
            frame: 原始图像 (可选, 用于边缘感知分割)

        返回:
            分割标签图 (H, W), 每个像素的运动类别编号 (-1 表示噪声)
        """
        h, w = flow.shape[:2]

        magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
        motion_mask = magnitude > 0.5

        if motion_mask.sum() < self.min_samples:
            return np.zeros((h, w), dtype=np.int32)

        features = self._extract_features(flow, frame)

        motion_mask_flat = motion_mask.reshape(-1)
        ys, xs = np.where(motion_mask)
        motion_features = features[motion_mask_flat]

        if len(motion_features) < self.min_samples:
            return np.zeros((h, w), dtype=np.int32)

        motion_features = self._normalize_features(motion_features)

        max_clusters_points = 10000
        if len(motion_features) > max_clusters_points:
            indices = np.random.choice(len(motion_features), max_clusters_points, replace=False)
            sampled_features = motion_features[indices]
            sampled_labels = self._cluster(sampled_features)

            from sklearn.neighbors import KNeighborsClassifier
            knn = KNeighborsClassifier(n_neighbors=3)
            knn.fit(sampled_features, sampled_labels)
            labels_flat = knn.predict(motion_features)
        else:
            labels_flat = self._cluster(motion_features)

        labels = np.full((h, w), -1, dtype=np.int32)
        labels[ys, xs] = labels_flat

        labels = self._refine_labels(labels, flow)

        return labels

    def _extract_features(
        self,
        flow: np.ndarray,
        frame: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        提取聚类特征

        特征向量包含:
        - u, v: 光流分量
        - magnitude: 运动幅度
        - angle: 运动方向
        - x, y: 空间位置 (可选)
        """
        h, w = flow.shape[:2]

        u = flow[..., 0].reshape(-1)
        v = flow[..., 1].reshape(-1)
        magnitude = np.sqrt(u ** 2 + v ** 2)
        angle = np.arctan2(v, u)

        ys, xs = np.mgrid[0:h, 0:w]
        x_norm = xs.reshape(-1).astype(np.float32) / w
        y_norm = ys.reshape(-1).astype(np.float32) / h

        features = np.column_stack([
            self.motion_weight * u,
            self.motion_weight * v,
            self.motion_weight * magnitude,
            angle,
            self.spatial_weight * x_norm,
            self.spatial_weight * y_norm,
        ])

        return features

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """标准化特征"""
        mean = features.mean(axis=0)
        std = features.std(axis=0)
        std = np.where(std < 1e-8, 1.0, std)
        return (features - mean) / std

    def _cluster(self, features: np.ndarray) -> np.ndarray:
        """聚类调度方法"""
        if self.method == 'dbscan':
            return self._dbscan_cluster(features)
        elif self.method == 'kmeans':
            return self._kmeans_cluster(features)
        elif self.method == 'hierarchical':
            return self._hierarchical_cluster(features)
        elif self.method == 'spatial':
            return np.zeros(len(features), dtype=np.int32)
        else:
            return self._dbscan_cluster(features)

    def _dbscan_cluster(self, features: np.ndarray) -> np.ndarray:
        """DBSCAN 密度聚类"""
        eps = self.eps * np.sqrt(features.shape[1])
        min_samples = self.min_samples

        clustering = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric='euclidean',
        )
        labels = clustering.fit_predict(features)
        return labels

    def _kmeans_cluster(self, features: np.ndarray) -> np.ndarray:
        """KMeans 聚类"""
        max_samples = 5000
        if len(features) > max_samples:
            indices = np.random.choice(len(features), max_samples, replace=False)
            subset = features[indices]
        else:
            subset = features
            indices = np.arange(len(features))

        kmeans = KMeans(
            n_clusters=self.n_clusters,
            n_init=3,
            max_iter=100,
            random_state=42,
        )
        labels_subset = kmeans.fit_predict(subset)

        if len(features) > max_samples:
            from sklearn.neighbors import KNeighborsClassifier
            knn = KNeighborsClassifier(n_neighbors=3)
            knn.fit(subset, labels_subset)
            labels = knn.predict(features)
        else:
            labels = labels_subset

        return labels

    def _hierarchical_cluster(self, features: np.ndarray) -> np.ndarray:
        """层次聚类 (使用 Agglomerative)"""
        from sklearn.cluster import AgglomerativeClustering

        max_samples = 5000
        if len(features) > max_samples:
            indices = np.random.choice(len(features), max_samples, replace=False)
            subset = features[indices]
        else:
            subset = features
            indices = np.arange(len(features))

        clustering = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            linkage='ward',
        )
        labels_subset = clustering.fit_predict(subset)

        labels = np.full(len(features), -1, dtype=np.int32)
        labels[indices] = labels_subset
        return labels

    def _spatial_cluster(self, flow: np.ndarray, motion_mask: np.ndarray) -> np.ndarray:
        """
        空间-运动联合聚类

        使用连通区域分析 + 运动方向分组
        """
        h, w = flow.shape[:2]

        mask_uint8 = (motion_mask * 255).astype(np.uint8)
        num_labels, labels_img, stats, _ = cv2.connectedComponentsWithStats(mask_uint8, connectivity=8)

        labels = np.full((h, w), -1, dtype=np.int32)
        cluster_id = 0

        for i in range(1, num_labels):
            component_mask = labels_img == i
            if component_mask.sum() < self.min_samples:
                continue

            component_flow = flow[component_mask]
            component_angle = np.arctan2(component_flow[:, 1], component_flow[:, 0])

            angle_diff = np.abs(np.sin(component_angle[:, None] - component_angle[None, :]))
            avg_diff = angle_diff.mean(axis=1)

            coherent_mask = avg_diff < 0.5
            if coherent_mask.sum() > self.min_samples:
                ys, xs = np.where(component_mask)
                labels[ys[coherent_mask], xs[coherent_mask]] = cluster_id
                cluster_id += 1

        return labels[motion_mask]

    def _refine_labels(self, labels: np.ndarray, flow: np.ndarray) -> np.ndarray:
        """
        细化分割结果

        - 去除小区域
        - 填充空洞
        - 平滑边界
        """
        h, w = labels.shape

        unique_labels = np.unique(labels)
        unique_labels = unique_labels[unique_labels >= 0]

        if len(unique_labels) == 0:
            return labels

        min_size = 100
        for label in unique_labels:
            label_mask = (labels == label).astype(np.uint8)
            num, labels_img, stats, _ = cv2.connectedComponentsWithStats(label_mask, connectivity=8)

            for i in range(1, num):
                if stats[i, cv2.CC_STAT_AREA] < min_size:
                    labels[labels_img == i] = -1

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        for label in unique_labels:
            label_mask = (labels == label).astype(np.uint8)
            label_mask = cv2.morphologyEx(label_mask, cv2.MORPH_CLOSE, kernel)
            labels[label_mask > 0] = label

        return labels

    def visualize_segments(
        self,
        labels: np.ndarray,
        flow: np.ndarray,
        frame: Optional[np.ndarray] = None,
        colormap: str = 'tab10',
    ) -> np.ndarray:
        """
        可视化运动分割结果

        参数:
            labels: 分割标签图 (H, W)
            flow: 光流场 (H, W, 2)
            frame: 原始图像 (可选, 用于叠加显示)
            colormap: 颜色映射名称

        返回:
            可视化图像 (H, W, 3)
        """
        h, w = labels.shape

        if frame is not None:
            result = frame.copy()
        else:
            result = np.zeros((h, w, 3), dtype=np.uint8)

        unique_labels = np.unique(labels)
        unique_labels = unique_labels[unique_labels >= 0]

        colors = self._generate_colors(len(unique_labels))

        for i, label in enumerate(unique_labels):
            mask = labels == label
            if mask.sum() == 0:
                continue

            color = colors[i]
            overlay = np.zeros((h, w, 3), dtype=np.uint8)
            overlay[mask] = color

            if frame is not None:
                alpha = 0.5
                result = cv2.addWeighted(result, 1 - alpha, overlay, alpha, 0)
            else:
                result[mask] = color

            center = self._compute_segment_center(mask)
            if center is not None:
                avg_flow = flow[mask].mean(axis=0)
                end_pt = (int(center[0] + avg_flow[0] * 5), int(center[1] + avg_flow[1] * 5))
                cv2.arrowedLine(result, center, end_pt, color, 2, tipLength=0.3)

        return result

    def _generate_colors(self, n: int) -> List[Tuple[int, int, int]]:
        """生成不同的颜色"""
        colors = []
        for i in range(n):
            hue = int(180 * i / max(n, 1))
            hsv = np.uint8([[[hue, 200, 200]]])
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            colors.append((int(bgr[0, 0, 0]), int(bgr[0, 0, 1]), int(bgr[0, 0, 2])))
        return colors

    def _compute_segment_center(self, mask: np.ndarray) -> Optional[Tuple[int, int]]:
        """计算分割区域的中心"""
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return None
        return (int(xs.mean()), int(ys.mean()))


class MotionAnalyzer:
    """
    运动分析器

    提供运动物体的统计信息:
        - 运动物体数量
        - 每个物体的运动参数 (平移、旋转、缩放)
        - 运动一致性度量
    """

    def __init__(self, min_object_size: int = 500):
        self.min_object_size = min_object_size

    def analyze(
        self,
        labels: np.ndarray,
        flow: np.ndarray,
        frame: Optional[np.ndarray] = None,
    ) -> dict:
        """
        分析运动分割结果

        参数:
            labels: 分割标签图 (H, W)
            flow: 光流场 (H, W, 2)
            frame: 原始图像 (可选)

        返回:
            分析结果字典
        """
        result = {
            'num_objects': 0,
            'objects': [],
            'total_moving_pixels': 0,
            'background_motion': None,
        }

        h, w = labels.shape
        unique_labels = np.unique(labels)
        unique_labels = unique_labels[unique_labels >= 0]

        result['num_objects'] = len(unique_labels)

        for label in unique_labels:
            mask = labels == label
            if mask.sum() < self.min_object_size:
                continue

            obj_flow = flow[mask]
            obj_center = np.where(mask)

            obj_info = {
                'label': int(label),
                'num_pixels': int(mask.sum()),
                'center': (float(obj_center[1].mean()), float(obj_center[0].mean())),
                'avg_flow': (float(obj_flow[:, 0].mean()), float(obj_flow[:, 1].mean())),
                'flow_std': (float(obj_flow[:, 0].std()), float(obj_flow[:, 1].std())),
                'bbox': self._compute_bbox(mask),
            }

            obj_info['motion_consistency'] = self._compute_motion_consistency(obj_flow)
            obj_info['motion_type'] = self._classify_motion(obj_flow)

            result['objects'].append(obj_info)
            result['total_moving_pixels'] += obj_info['num_pixels']

        return result

    def _compute_bbox(self, mask: np.ndarray) -> Tuple[int, int, int, int]:
        """计算边界框"""
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return (0, 0, 0, 0)
        return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

    def _compute_motion_consistency(self, flow: np.ndarray) -> float:
        """
        计算运动一致性

        基于光流方向的方差
        """
        if len(flow) < 2:
            return 0.0

        angles = np.arctan2(flow[:, 1], flow[:, 0])
        angle_circular_mean = np.arctan2(
            np.sin(angles).mean(),
            np.cos(angles).mean()
        )
        angle_diff = np.abs(np.sin(angles - angle_circular_mean))
        consistency = 1.0 - angle_diff.mean() / np.pi

        return float(max(0, min(1, consistency)))

    def _classify_motion(self, flow: np.ndarray) -> str:
        """
        分类运动类型

        - 'static': 几乎静止
        - 'translational': 平移运动
        - 'rotational': 旋转运动
        - 'complex': 复杂运动
        """
        if len(flow) < 3:
            return 'static'

        magnitude = np.sqrt(flow[:, 0] ** 2 + flow[:, 1] ** 2)
        mean_mag = magnitude.mean()

        if mean_mag < 0.5:
            return 'static'

        angles = np.arctan2(flow[:, 1], flow[:, 0])
        angle_std = np.std(angles)

        if angle_std < 0.3:
            return 'translational'
        elif angle_std < 1.0:
            return 'complex'
        else:
            return 'rotational'