import numpy as np
from numba import jit, prange, njit
from typing import Dict, Tuple


@njit(fastmath=True)
def _normalize_vector(v: np.ndarray) -> np.ndarray:
    norm = np.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if norm < 1e-15:
        return np.zeros(3)
    return v / norm


@njit(fastmath=True)
def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    n1 = _normalize_vector(v1)
    n2 = _normalize_vector(v2)
    dot = n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]
    dot = max(min(dot, 1.0), -1.0)
    return np.degrees(np.arccos(dot))


@njit(fastmath=True, parallel=True)
def compute_quad_quality(points: np.ndarray, cells: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_cells = len(cells)
    areas = np.zeros(n_cells)
    non_orth = np.zeros(n_cells)
    aspect = np.zeros(n_cells)

    for idx in prange(n_cells):
        cell = cells[idx]
        p0 = points[cell[0]]
        p1 = points[cell[1]]
        p2 = points[cell[2]]
        p3 = points[cell[3]]

        v1 = p1 - p0
        v2 = p2 - p0
        cross = np.cross(v1, v2)
        area1 = 0.5 * np.sqrt(cross[0]**2 + cross[1]**2 + cross[2]**2)

        v3 = p3 - p0
        cross2 = np.cross(v2, v3)
        area2 = 0.5 * np.sqrt(cross2[0]**2 + cross2[1]**2 + cross2[2]**2)
        areas[idx] = area1 + area2

        centroid = (p0 + p1 + p2 + p3) / 4.0

        max_dev = 0.0
        edges = [(p0, p1), (p1, p2), (p2, p3), (p3, p0)]
        for e_start, e_end in edges:
            edge_center = (e_start + e_end) / 2.0
            edge_vec = e_end - e_start
            normal = np.array([-edge_vec[1], edge_vec[0], 0.0])
            cell_vec = edge_center - centroid

            to_centroid = centroid - edge_center
            dot_prod = normal[0]*to_centroid[0] + normal[1]*to_centroid[1] + normal[2]*to_centroid[2]
            if dot_prod < 0:
                normal = -normal

            angle = _angle_between(normal, cell_vec)
            dev = np.abs(90.0 - angle)
            if dev > max_dev:
                max_dev = dev

        non_orth[idx] = max_dev

        edge_lens = np.zeros(4)
        for i in range(4):
            pi = points[cell[i]]
            pj = points[cell[(i+1) % 4]]
            edge_lens[i] = np.sqrt(np.sum((pj - pi)**2))

        aspect[idx] = np.max(edge_lens) / (np.min(edge_lens) + 1e-15)

    return areas, non_orth, aspect


@njit(fastmath=True, parallel=True)
def compute_hex_quality(points: np.ndarray, cells: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_cells = len(cells)
    volumes = np.zeros(n_cells)
    non_orth = np.zeros(n_cells)
    aspect = np.zeros(n_cells)

    for idx in prange(n_cells):
        cell = cells[idx]
        p0, p1, p2, p3, p4, p5, p6, p7 = points[cell]

        v1 = p1 - p0
        v3 = p3 - p0
        v4 = p4 - p0
        scalar = v1[0] * np.cross(v3, v4)[0] + v1[1] * np.cross(v3, v4)[1] + v1[2] * np.cross(v3, v4)[2]
        volumes[idx] = np.abs(scalar)

        centroid = (p0 + p1 + p2 + p3 + p4 + p5 + p6 + p7) / 8.0

        faces = [
            (p0, p1, p2, p3), (p4, p5, p6, p7),
            (p0, p1, p5, p4), (p2, p3, p7, p6),
            (p0, p3, p7, p4), (p1, p2, p6, p5)
        ]

        max_dev = 0.0
        for face in faces:
            fp0, fp1, fp2, fp3 = face
            face_center = (fp0 + fp1 + fp2 + fp3) / 4.0
            fv1 = fp1 - fp0
            fv2 = fp2 - fp0
            normal = np.cross(fv1, fv2)
            cell_vec = face_center - centroid

            to_centroid = centroid - face_center
            dot_prod = normal[0]*to_centroid[0] + normal[1]*to_centroid[1] + normal[2]*to_centroid[2]
            if dot_prod < 0:
                normal = -normal

            angle = _angle_between(normal, cell_vec)
            dev = np.abs(90.0 - angle)
            if dev > max_dev:
                max_dev = dev

        non_orth[idx] = max_dev

        edge_pairs = [(0,1), (1,2), (2,3), (3,0),
                      (4,5), (5,6), (6,7), (7,4),
                      (0,4), (1,5), (2,6), (3,7)]
        edge_lens = np.zeros(12)
        for i, (ei, ej) in enumerate(edge_pairs):
            pi = points[cell[ei]]
            pj = points[cell[ej]]
            edge_lens[i] = np.sqrt(np.sum((pj - pi)**2))

        aspect[idx] = np.max(edge_lens) / (np.min(edge_lens) + 1e-15)

    return volumes, non_orth, aspect


@njit(fastmath=True, parallel=True)
def laplacian_smooth_step(points: np.ndarray, adjacency: list,
                           fixed_mask: np.ndarray, relaxation: float = 0.5) -> np.ndarray:
    n_points = len(points)
    new_points = points.copy()

    for i in prange(n_points):
        if fixed_mask[i]:
            continue

        neighbors = adjacency[i]
        if len(neighbors) == 0:
            continue

        avg_pos = np.zeros(3)
        for j in neighbors:
            avg_pos += points[j]
        avg_pos /= len(neighbors)

        new_points[i] = (1 - relaxation) * points[i] + relaxation * avg_pos

    return new_points


@njit(fastmath=True)
def compute_vertex_curvature(points: np.ndarray, adjacency: list) -> np.ndarray:
    n_points = len(points)
    curvature = np.zeros(n_points)

    for i in range(n_points):
        neighbors = adjacency[i]
        if len(neighbors) < 2:
            continue

        angles = []
        pos_i = points[i]
        for j in range(len(neighbors)):
            for k in range(j+1, len(neighbors)):
                v1 = points[neighbors[j]] - pos_i
                v2 = points[neighbors[k]] - pos_i
                angle = _angle_between(v1, v2)
                angles.append(angle)

        if len(angles) > 0:
            curvature[i] = np.std(np.array(angles))

    return curvature


class FastMeshQuality:
    def __init__(self, points: np.ndarray, cells_dict: dict):
        self.points = np.asarray(points, dtype=np.float64)
        if self.points.shape[1] == 2:
            self.points = np.hstack([self.points, np.zeros((len(self.points), 1))])
        self.cells_dict = cells_dict
        self._build_adjacency()

    def _build_adjacency(self):
        n_points = len(self.points)
        adjacency = [set() for _ in range(n_points)]

        for cell_type, cell_data in self.cells_dict.items():
            for cell in cell_data:
                for i in range(len(cell)):
                    for j in range(len(cell)):
                        if i != j:
                            adjacency[cell[i]].add(cell[j])

        self.adjacency = [list(neighbors) for neighbors in adjacency]

    def compute_all(self) -> Dict[str, Dict[str, np.ndarray]]:
        results = {}

        for cell_type, cell_data in self.cells_dict.items():
            if cell_type == 'quad' and len(cell_data) > 0:
                areas, non_orth, aspect = compute_quad_quality(self.points, np.array(cell_data))
                results[cell_type] = {
                    'area': areas,
                    'non_orthogonality': non_orth,
                    'aspect_ratio': aspect
                }
            elif cell_type == 'hexahedron' and len(cell_data) > 0:
                volumes, non_orth, aspect = compute_hex_quality(self.points, np.array(cell_data))
                results[cell_type] = {
                    'volume': volumes,
                    'non_orthogonality': non_orth,
                    'aspect_ratio': aspect
                }

        return results

    def laplacian_smooth(self, iterations: int = 20, relaxation: float = 0.5,
                         fixed_boundary: bool = True) -> np.ndarray:
        current_points = self.points.copy()
        fixed_mask = np.zeros(len(current_points), dtype=bool)

        if fixed_boundary:
            boundary_vertices = self._find_boundary_vertices()
            fixed_mask[boundary_vertices] = True

        for _ in range(iterations):
            current_points = laplacian_smooth_step(
                current_points, self.adjacency, fixed_mask, relaxation
            )

        return current_points

    def _find_boundary_vertices(self) -> list:
        edge_count = {}

        for cell_type, cell_data in self.cells_dict.items():
            for cell in cell_data:
                n = len(cell)
                for i in range(n):
                    edge = tuple(sorted([cell[i], cell[(i+1) % n]]))
                    edge_count[edge] = edge_count.get(edge, 0) + 1

        boundary_vertices = set()
        for edge, count in edge_count.items():
            if count == 1:
                boundary_vertices.update(edge)

        return list(boundary_vertices)

    def get_curvature(self) -> np.ndarray:
        return compute_vertex_curvature(self.points, self.adjacency)
