import numpy as np
from typing import Dict, Tuple


class MeshQuality:
    def __init__(self, points: np.ndarray, cells):
        self.points = np.asarray(points, dtype=np.float64)
        self.cells = cells
        self.is_2d = self._detect_2d()
        self.quality_metrics = {}

    def _detect_2d(self) -> bool:
        if self.points.shape[1] < 3:
            return True
        z_coords = self.points[:, 2]
        return np.allclose(z_coords, z_coords[0])

    def compute_all_metrics(self) -> Dict:
        self.quality_metrics = {}

        for cell_block in self.cells:
            cell_type = cell_block.type
            cell_data = np.asarray(cell_block.data, dtype=np.int64)

            if cell_type in ["triangle", "quad"]:
                metrics = self._compute_2d_metrics_vectorized(cell_data, cell_type)
            elif cell_type in ["tetra", "hexahedron", "wedge", "pyramid"]:
                metrics = self._compute_3d_metrics_vectorized(cell_data, cell_type)
            else:
                continue

            self.quality_metrics[cell_type] = metrics

        return self.quality_metrics

    def _compute_2d_metrics_vectorized(self, cell_data: np.ndarray, cell_type: str) -> Dict:
        num_cells = len(cell_data)
        cell_points = self.points[cell_data]

        centers = np.mean(cell_points, axis=1)

        if cell_type == "triangle":
            areas = self._triangle_area_vectorized(cell_points)
            non_orth = self._triangle_non_orthogonality_vectorized(cell_points, centers)
            skewness = self._triangle_skewness_vectorized(cell_points)
            aspect_ratio = self._triangle_aspect_ratio_vectorized(cell_points)
        elif cell_type == "quad":
            areas = self._quad_area_vectorized(cell_points)
            non_orth = self._quad_non_orthogonality_vectorized(cell_points, centers)
            skewness = self._quad_skewness_vectorized(cell_points)
            aspect_ratio = self._quad_aspect_ratio_vectorized(cell_points)
        else:
            areas = np.zeros(num_cells)
            non_orth = np.zeros(num_cells)
            skewness = np.zeros(num_cells)
            aspect_ratio = np.zeros(num_cells)

        return {
            "area": areas,
            "non_orthogonality": non_orth,
            "skewness": skewness,
            "aspect_ratio": aspect_ratio,
            "cell_centers": centers
        }

    def _compute_3d_metrics_vectorized(self, cell_data: np.ndarray, cell_type: str) -> Dict:
        num_cells = len(cell_data)
        cell_points = self.points[cell_data]

        centers = np.mean(cell_points, axis=1)

        if cell_type == "tetra":
            volumes = self._tetra_volume_vectorized(cell_points)
            non_orth = self._tetra_non_orthogonality_vectorized(cell_points, centers)
            skewness = self._tetra_skewness_vectorized(cell_points)
            aspect_ratio = self._tetra_aspect_ratio_vectorized(cell_points)
        elif cell_type == "hexahedron":
            volumes = self._hex_volume_vectorized(cell_points)
            non_orth = self._hex_non_orthogonality_vectorized(cell_points, centers)
            skewness = self._hex_skewness_vectorized(cell_points)
            aspect_ratio = self._hex_aspect_ratio_vectorized(cell_points)
        else:
            volumes = np.zeros(num_cells)
            non_orth = np.zeros(num_cells)
            skewness = np.zeros(num_cells)
            aspect_ratio = np.zeros(num_cells)

        return {
            "volume": volumes,
            "non_orthogonality": non_orth,
            "skewness": skewness,
            "aspect_ratio": aspect_ratio,
            "cell_centers": centers
        }

    @staticmethod
    def _normalize_vectors(v: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(v, axis=-1, keepdims=True)
        norms = np.where(norms < 1e-15, 1.0, norms)
        return v / norms

    @staticmethod
    def _angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
        v1_norm = MeshQuality._normalize_vectors(v1)
        v2_norm = MeshQuality._normalize_vectors(v2)
        dot = np.sum(v1_norm * v2_norm, axis=-1)
        dot = np.clip(dot, -1.0, 1.0)
        return np.degrees(np.arccos(dot))

    @staticmethod
    def _triangle_area_vectorized(points: np.ndarray) -> np.ndarray:
        v1 = points[:, 1] - points[:, 0]
        v2 = points[:, 2] - points[:, 0]
        if points.shape[2] == 3:
            cross = np.cross(v1, v2)
            area = 0.5 * np.linalg.norm(cross, axis=1)
        else:
            area = 0.5 * np.abs(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0])
        return area

    def _triangle_non_orthogonality_vectorized(self, points: np.ndarray, centers: np.ndarray) -> np.ndarray:
        num_cells = len(points)
        max_angles = np.zeros(num_cells)

        for i in range(3):
            p1 = points[:, i]
            p2 = points[:, (i + 1) % 3]
            edge_center = 0.5 * (p1 + p2)

            edge_vec = p2 - p1
            if points.shape[2] == 3:
                normal = np.cross(edge_vec, np.array([0.0, 0.0, 1.0]))
            else:
                normal = np.stack([-edge_vec[:, 1], edge_vec[:, 0], np.zeros(num_cells)], axis=1)

            cell_vec = edge_center - centers

            to_centroid = centers - edge_center
            dot_prod = np.sum(normal * to_centroid, axis=1)
            normal = np.where(dot_prod[:, np.newaxis] < 0, -normal, normal)

            angles = self._angle_between_vectors(normal, cell_vec)
            current_dev = np.abs(90.0 - angles)
            max_angles = np.maximum(max_angles, current_dev)

        return max_angles

    def _triangle_skewness_vectorized(self, points: np.ndarray) -> np.ndarray:
        num_cells = len(points)
        skewness = np.zeros(num_cells)

        for i in range(3):
            edge_center1 = 0.5 * (points[:, i] + points[:, (i + 1) % 3])
            edge_center2 = 0.5 * (points[:, (i + 1) % 3] + points[:, (i + 2) % 3])

            v1 = edge_center1 - points[:, (i + 1) % 3]
            v2 = edge_center2 - points[:, (i + 1) % 3]

            angles = self._angle_between_vectors(v1, v2)
            dev = np.abs(angles - 60.0)
            skewness = np.maximum(skewness, dev / 120.0 * 100.0)

        return skewness

    @staticmethod
    def _triangle_aspect_ratio_vectorized(points: np.ndarray) -> np.ndarray:
        edges = []
        for i in range(3):
            edge_vec = points[:, (i + 1) % 3] - points[:, i]
            edge_len = np.linalg.norm(edge_vec, axis=1)
            edges.append(edge_len)
        edges = np.stack(edges, axis=1)

        max_edge = np.max(edges, axis=1)
        min_edge = np.min(edges, axis=1)
        min_edge = np.where(min_edge < 1e-15, 1e-15, min_edge)
        return max_edge / min_edge

    @staticmethod
    def _quad_area_vectorized(points: np.ndarray) -> np.ndarray:
        area1 = MeshQuality._triangle_area_vectorized(points[:, [0, 1, 2]])
        area2 = MeshQuality._triangle_area_vectorized(points[:, [0, 2, 3]])
        return area1 + area2

    def _quad_non_orthogonality_vectorized(self, points: np.ndarray, centers: np.ndarray) -> np.ndarray:
        num_cells = len(points)
        max_angles = np.zeros(num_cells)

        for i in range(4):
            p1 = points[:, i]
            p2 = points[:, (i + 1) % 4]
            edge_center = 0.5 * (p1 + p2)

            edge_vec = p2 - p1
            if points.shape[2] == 3:
                normal = np.cross(edge_vec, np.array([0.0, 0.0, 1.0]))
            else:
                normal = np.stack([-edge_vec[:, 1], edge_vec[:, 0], np.zeros(num_cells)], axis=1)

            cell_vec = edge_center - centers

            to_centroid = centers - edge_center
            dot_prod = np.sum(normal * to_centroid, axis=1)
            normal = np.where(dot_prod[:, np.newaxis] < 0, -normal, normal)

            angles = self._angle_between_vectors(normal, cell_vec)
            current_dev = np.abs(90.0 - angles)
            max_angles = np.maximum(max_angles, current_dev)

        return max_angles

    def _quad_skewness_vectorized(self, points: np.ndarray) -> np.ndarray:
        num_cells = len(points)
        skewness = np.zeros(num_cells)

        for i in range(4):
            edge_center1 = 0.5 * (points[:, i] + points[:, (i + 1) % 4])
            edge_center2 = 0.5 * (points[:, (i + 1) % 4] + points[:, (i + 2) % 4])

            v1 = edge_center1 - points[:, (i + 1) % 4]
            v2 = edge_center2 - points[:, (i + 1) % 4]

            angles = self._angle_between_vectors(v1, v2)
            dev = np.abs(angles - 90.0)
            skewness = np.maximum(skewness, dev / 90.0 * 100.0)

        return skewness

    @staticmethod
    def _quad_aspect_ratio_vectorized(points: np.ndarray) -> np.ndarray:
        edges = []
        for i in range(4):
            edge_vec = points[:, (i + 1) % 4] - points[:, i]
            edge_len = np.linalg.norm(edge_vec, axis=1)
            edges.append(edge_len)
        edges = np.stack(edges, axis=1)

        max_edge = np.max(edges, axis=1)
        min_edge = np.min(edges, axis=1)
        min_edge = np.where(min_edge < 1e-15, 1e-15, min_edge)
        return max_edge / min_edge

    @staticmethod
    def _tetra_volume_vectorized(points: np.ndarray) -> np.ndarray:
        v1 = points[:, 1] - points[:, 0]
        v2 = points[:, 2] - points[:, 0]
        v3 = points[:, 3] - points[:, 0]
        scalar_triple = np.sum(v1 * np.cross(v2, v3), axis=1)
        return np.abs(scalar_triple) / 6.0

    def _tetra_non_orthogonality_vectorized(self, points: np.ndarray, centers: np.ndarray) -> np.ndarray:
        num_cells = len(points)
        max_angles = np.zeros(num_cells)

        faces = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]

        for face in faces:
            fp = points[:, face]
            face_center = np.mean(fp, axis=1)
            v1 = fp[:, 1] - fp[:, 0]
            v2 = fp[:, 2] - fp[:, 0]
            normal = np.cross(v1, v2)
            cell_vec = face_center - centers

            to_centroid = centers - face_center
            dot_prod = np.sum(normal * to_centroid, axis=1)
            normal = np.where(dot_prod[:, np.newaxis] < 0, -normal, normal)

            angles = self._angle_between_vectors(normal, cell_vec)
            current_dev = np.abs(90.0 - angles)
            max_angles = np.maximum(max_angles, current_dev)

        return max_angles

    def _tetra_skewness_vectorized(self, points: np.ndarray) -> np.ndarray:
        edges = []
        for i in range(4):
            for j in range(i + 1, 4):
                edge_vec = points[:, j] - points[:, i]
                edge_len = np.linalg.norm(edge_vec, axis=1)
                edges.append(edge_len)
        edges = np.stack(edges, axis=1)

        max_edge = np.max(edges, axis=1)
        min_edge = np.min(edges, axis=1)
        min_edge = np.where(min_edge < 1e-15, 1e-15, min_edge)
        ratio = max_edge / min_edge
        ideal_ratio = np.sqrt(2.0)
        return np.minimum(np.abs(ratio - ideal_ratio) / ideal_ratio * 100.0, 100.0)

    @staticmethod
    def _tetra_aspect_ratio_vectorized(points: np.ndarray) -> np.ndarray:
        edges = []
        for i in range(4):
            for j in range(i + 1, 4):
                edge_vec = points[:, j] - points[:, i]
                edge_len = np.linalg.norm(edge_vec, axis=1)
                edges.append(edge_len)
        edges = np.stack(edges, axis=1)

        max_edge = np.max(edges, axis=1)
        min_edge = np.min(edges, axis=1)
        min_edge = np.where(min_edge < 1e-15, 1e-15, min_edge)
        return max_edge / min_edge

    @staticmethod
    def _hex_volume_vectorized(points: np.ndarray) -> np.ndarray:
        v1 = points[:, 1] - points[:, 0]
        v3 = points[:, 3] - points[:, 0]
        v4 = points[:, 4] - points[:, 0]
        scalar_triple = np.sum(v1 * np.cross(v3, v4), axis=1)
        return np.abs(scalar_triple)

    def _hex_non_orthogonality_vectorized(self, points: np.ndarray, centers: np.ndarray) -> np.ndarray:
        num_cells = len(points)
        max_angles = np.zeros(num_cells)

        faces = [
            [0, 1, 2, 3], [4, 5, 6, 7],
            [0, 1, 5, 4], [2, 3, 7, 6],
            [0, 3, 7, 4], [1, 2, 6, 5]
        ]

        for face in faces:
            fp = points[:, face]
            face_center = np.mean(fp, axis=1)
            v1 = fp[:, 1] - fp[:, 0]
            v2 = fp[:, 2] - fp[:, 0]
            normal = np.cross(v1, v2)
            cell_vec = face_center - centers

            to_centroid = centers - face_center
            dot_prod = np.sum(normal * to_centroid, axis=1)
            normal = np.where(dot_prod[:, np.newaxis] < 0, -normal, normal)

            angles = self._angle_between_vectors(normal, cell_vec)
            current_dev = np.abs(90.0 - angles)
            max_angles = np.maximum(max_angles, current_dev)

        return max_angles

    def _hex_skewness_vectorized(self, points: np.ndarray) -> np.ndarray:
        edge_pairs = [(0, 1), (1, 2), (2, 3), (3, 0),
                      (4, 5), (5, 6), (6, 7), (7, 4),
                      (0, 4), (1, 5), (2, 6), (3, 7)]

        edges = []
        for i, j in edge_pairs:
            edge_vec = points[:, j] - points[:, i]
            edge_len = np.linalg.norm(edge_vec, axis=1)
            edges.append(edge_len)
        edges = np.stack(edges, axis=1)

        max_edge = np.max(edges, axis=1)
        min_edge = np.min(edges, axis=1)
        min_edge = np.where(min_edge < 1e-15, 1e-15, min_edge)
        ratio = max_edge / min_edge
        return np.minimum(np.abs(ratio - 1.0) * 100.0, 100.0)

    @staticmethod
    def _hex_aspect_ratio_vectorized(points: np.ndarray) -> np.ndarray:
        edge_pairs = [(0, 1), (1, 2), (2, 3), (3, 0),
                      (4, 5), (5, 6), (6, 7), (7, 4),
                      (0, 4), (1, 5), (2, 6), (3, 7)]

        edges = []
        for i, j in edge_pairs:
            edge_vec = points[:, j] - points[:, i]
            edge_len = np.linalg.norm(edge_vec, axis=1)
            edges.append(edge_len)
        edges = np.stack(edges, axis=1)

        max_edge = np.max(edges, axis=1)
        min_edge = np.min(edges, axis=1)
        min_edge = np.where(min_edge < 1e-15, 1e-15, min_edge)
        return max_edge / min_edge

    def get_statistics(self) -> Dict:
        stats = {}
        for cell_type, metrics in self.quality_metrics.items():
            stats[cell_type] = {}
            for metric_name, values in metrics.items():
                if metric_name == "cell_centers":
                    continue
                valid_values = values[np.isfinite(values)]
                if len(valid_values) > 0:
                    stats[cell_type][metric_name] = {
                        "min": np.min(valid_values),
                        "max": np.max(valid_values),
                        "mean": np.mean(valid_values),
                        "std": np.std(valid_values),
                        "median": np.median(valid_values),
                        "sum": np.sum(valid_values)
                    }
        return stats

    def get_histogram(self, metric_name: str, bins: int = 10) -> Dict:
        all_values = []
        for cell_type, metrics in self.quality_metrics.items():
            if metric_name in metrics:
                values = metrics[metric_name]
                valid_values = values[np.isfinite(values)]
                all_values.extend(valid_values)

        if not all_values:
            return {}

        all_values = np.array(all_values)
        counts, bin_edges = np.histogram(all_values, bins=bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        return {
            "counts": counts,
            "bin_edges": bin_edges,
            "bin_centers": bin_centers,
            "total": len(all_values)
        }

    def get_all_histograms(self, bins: int = 10) -> Dict:
        metrics = ["non_orthogonality", "skewness", "aspect_ratio"]
        if self.is_2d:
            metrics.append("area")
        else:
            metrics.append("volume")

        histograms = {}
        for metric in metrics:
            hist = self.get_histogram(metric, bins)
            if hist:
                histograms[metric] = hist

        return histograms

    def get_bad_cells(self, threshold: Dict[str, float]) -> Dict:
        bad_cells = {}
        for cell_type, metrics in self.quality_metrics.items():
            bad_cells[cell_type] = {}
            for metric_name, limit in threshold.items():
                if metric_name in metrics:
                    values = metrics[metric_name]
                    if metric_name == "non_orthogonality":
                        bad = np.where(values > limit)[0]
                    elif metric_name == "skewness":
                        bad = np.where(values > limit)[0]
                    elif metric_name == "aspect_ratio":
                        bad = np.where(values > limit)[0]
                    else:
                        bad = np.array([])
                    bad_cells[cell_type][metric_name] = bad
        return bad_cells
