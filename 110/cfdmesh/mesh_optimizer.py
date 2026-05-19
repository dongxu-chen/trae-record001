import numpy as np
import meshio
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

from .mesh_quality import MeshQuality


class MeshOptimizer:
    def __init__(self, mesh: meshio.Mesh):
        self.original_mesh = mesh
        self.mesh = meshio.Mesh(mesh.points.copy(), mesh.cells)
        self.points = self.mesh.points
        self.cells = self.mesh.cells
        self.vertex_neighbors = self._build_vertex_connectivity()

    def _build_vertex_connectivity(self) -> Dict[int, List[int]]:
        neighbors = defaultdict(set)
        for cell_block in self.cells:
            for cell in cell_block.data:
                for i, v in enumerate(cell):
                    for j, w in enumerate(cell):
                        if i != j:
                            neighbors[v].add(w)
        return {k: list(v) for k, v in neighbors.items()}

    def laplacian_smooth(self, iterations: int = 10, relaxation: float = 0.5,
                          fixed_boundary: bool = True) -> meshio.Mesh:
        num_vertices = len(self.points)
        is_boundary = self._find_boundary_vertices()

        for _ in range(iterations):
            new_points = self.points.copy()
            for v in range(num_vertices):
                if fixed_boundary and is_boundary[v]:
                    continue
                if v in self.vertex_neighbors and len(self.vertex_neighbors[v]) > 0:
                    neighbor_points = self.points[self.vertex_neighbors[v]]
                    centroid = np.mean(neighbor_points, axis=0)
                    new_points[v] = (1 - relaxation) * self.points[v] + relaxation * centroid
            self.points[:] = new_points

        self.mesh.points = self.points
        return self.mesh

    def _find_boundary_vertices(self) -> np.ndarray:
        edge_count = defaultdict(int)

        for cell_block in self.cells:
            cell_type = cell_block.type
            for cell in cell_block.data:
                if cell_type in ['triangle', 'quad']:
                    n = len(cell)
                    for i in range(n):
                        edge = tuple(sorted([cell[i], cell[(i + 1) % n]]))
                        edge_count[edge] += 1
                elif cell_type in ['tetra', 'hexahedron']:
                    faces = self._get_cell_faces(cell, cell_type)
                    for face in faces:
                        face_key = tuple(sorted(face))
                        edge_count[face_key] += 1

        boundary_vertices = set()
        for edge, count in edge_count.items():
            if count == 1:
                boundary_vertices.update(edge)

        is_boundary = np.zeros(len(self.points), dtype=bool)
        for v in boundary_vertices:
            is_boundary[v] = True
        return is_boundary

    def _get_cell_faces(self, cell: np.ndarray, cell_type: str) -> List[Tuple]:
        if cell_type == 'triangle':
            return [(cell[0], cell[1]), (cell[1], cell[2]), (cell[2], cell[0])]
        elif cell_type == 'quad':
            return [(cell[0], cell[1]), (cell[1], cell[2]),
                    (cell[2], cell[3]), (cell[3], cell[0])]
        elif cell_type == 'tetra':
            return [
                (cell[0], cell[1], cell[2]),
                (cell[0], cell[1], cell[3]),
                (cell[0], cell[2], cell[3]),
                (cell[1], cell[2], cell[3])
            ]
        elif cell_type == 'hexahedron':
            return [
                (cell[0], cell[1], cell[2], cell[3]),
                (cell[4], cell[5], cell[6], cell[7]),
                (cell[0], cell[1], cell[5], cell[4]),
                (cell[2], cell[3], cell[7], cell[6]),
                (cell[0], cell[3], cell[7], cell[4]),
                (cell[1], cell[2], cell[6], cell[5])
            ]
        return []

    def compute_curvature(self) -> np.ndarray:
        num_vertices = len(self.points)
        curvature = np.zeros(num_vertices)

        for v in range(num_vertices):
            if v not in self.vertex_neighbors:
                continue
            neighbors = self.vertex_neighbors[v]
            if len(neighbors) < 2:
                continue
            neighbor_points = self.points[neighbors]
            vectors = neighbor_points - self.points[v]
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms = np.where(norms < 1e-15, 1.0, norms)
            unit_vectors = vectors / norms

            dot_products = np.dot(unit_vectors, unit_vectors.T)
            angles = np.arccos(np.clip(dot_products, -1.0, 1.0))
            curvature[v] = np.std(angles) if len(angles) > 1 else 0

        return curvature

    def compute_quality_metrics(self) -> Dict[str, np.ndarray]:
        quality = MeshQuality(self.points, self.cells)
        metrics = quality.compute_all_metrics()

        cell_quality = defaultdict(list)

        for cell_type, cell_metrics in metrics.items():
            for metric_name, values in cell_metrics.items():
                if metric_name != 'cell_centers':
                    cell_quality[metric_name].extend(values)

        return {k: np.array(v) for k, v in cell_quality.items()}

    def adaptive_refine(self, method: str = 'quality', threshold: Optional[float] = None,
                         max_level: int = 2, quality_metric: str = 'non_orthogonality') -> meshio.Mesh:
        for level in range(max_level):
            if method == 'curvature':
                refinement_mask = self._get_curvature_refinement_mask(threshold)
            elif method == 'quality':
                refinement_mask = self._get_quality_refinement_mask(quality_metric, threshold)
            else:
                raise ValueError(f"Unknown refinement method: {method}")

            if np.any(refinement_mask):
                self._refine_cells(refinement_mask)
                self.vertex_neighbors = self._build_vertex_connectivity()
            else:
                break

        return self.mesh

    def _get_curvature_refinement_mask(self, threshold: Optional[float]) -> np.ndarray:
        curvature = self.compute_curvature()
        if threshold is None:
            threshold = np.percentile(curvature, 80)

        cell_curvatures = []
        for cell_block in self.cells:
            for cell in cell_block.data:
                avg_curvature = np.mean(curvature[cell])
                cell_curvatures.append(avg_curvature)

        cell_curvatures = np.array(cell_curvatures)
        return cell_curvatures > threshold

    def _get_quality_refinement_mask(self, quality_metric: str, threshold: Optional[float]) -> np.ndarray:
        quality = MeshQuality(self.points, self.cells)
        metrics = quality.compute_all_metrics()

        cell_qualities = []
        for cell_type, cell_metrics in metrics.items():
            if quality_metric in cell_metrics:
                cell_qualities.extend(cell_metrics[quality_metric])

        cell_qualities = np.array(cell_qualities)

        if threshold is None:
            if quality_metric in ['non_orthogonality', 'skewness']:
                threshold = np.percentile(cell_qualities, 70)
            else:
                threshold = np.percentile(cell_qualities, 70)

        return cell_qualities > threshold

    def _refine_cells(self, refinement_mask: np.ndarray):
        new_points_list = [self.points.copy()]
        new_cells_list = []

        cell_idx = 0
        for cell_block in self.cells:
            cell_type = cell_block.type
            refined_cells = []

            for i, cell in enumerate(cell_block.data):
                if refinement_mask[cell_idx]:
                    split_cells, extra_points = self._split_cell(cell, cell_type)
                    new_points_list.append(extra_points)
                    refined_cells.extend(split_cells)
                else:
                    refined_cells.append(cell)
                cell_idx += 1

            new_cells_list.append(meshio.CellBlock(cell_type, np.array(refined_cells)))

        all_points = np.vstack(new_points_list)
        self.points = all_points
        self.cells = new_cells_list
        self.mesh.points = all_points
        self.mesh.cells = new_cells_list

    def _split_cell(self, cell: np.ndarray, cell_type: str) -> Tuple[List[np.ndarray], np.ndarray]:
        if cell_type == 'triangle':
            return self._split_triangle(cell)
        elif cell_type == 'quad':
            return self._split_quad(cell)
        elif cell_type == 'tetra':
            return self._split_tetra(cell)
        elif cell_type == 'hexahedron':
            return self._split_hexahedron(cell)
        else:
            return [cell], np.array([])

    def _split_triangle(self, cell: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
        v0, v1, v2 = cell
        p0, p1, p2 = self.points[[v0, v1, v2]]

        m01 = len(self.points)
        m12 = len(self.points) + 1
        m20 = len(self.points) + 2

        new_points = np.array([
            (p0 + p1) / 2,
            (p1 + p2) / 2,
            (p2 + p0) / 2
        ])

        new_cells = [
            np.array([v0, m01, m20]),
            np.array([v1, m12, m01]),
            np.array([v2, m20, m12]),
            np.array([m01, m12, m20])
        ]

        return new_cells, new_points

    def _split_quad(self, cell: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
        v0, v1, v2, v3 = cell
        p0, p1, p2, p3 = self.points[[v0, v1, v2, v3]]

        m01 = len(self.points)
        m12 = len(self.points) + 1
        m23 = len(self.points) + 2
        m30 = len(self.points) + 3
        center = len(self.points) + 4

        new_points = np.array([
            (p0 + p1) / 2,
            (p1 + p2) / 2,
            (p2 + p3) / 2,
            (p3 + p0) / 2,
            (p0 + p1 + p2 + p3) / 4
        ])

        new_cells = [
            np.array([v0, m01, center, m30]),
            np.array([v1, m12, center, m01]),
            np.array([v2, m23, center, m12]),
            np.array([v3, m30, center, m23])
        ]

        return new_cells, new_points

    def _split_tetra(self, cell: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
        v0, v1, v2, v3 = cell
        p0, p1, p2, p3 = self.points[[v0, v1, v2, v3]]

        m01 = len(self.points)
        m02 = len(self.points) + 1
        m03 = len(self.points) + 2
        m12 = len(self.points) + 3
        m13 = len(self.points) + 4
        m23 = len(self.points) + 5
        center = len(self.points) + 6

        new_points = np.array([
            (p0 + p1) / 2,
            (p0 + p2) / 2,
            (p0 + p3) / 2,
            (p1 + p2) / 2,
            (p1 + p3) / 2,
            (p2 + p3) / 2,
            (p0 + p1 + p2 + p3) / 4
        ])

        new_cells = [
            np.array([v0, m01, m02, m03]),
            np.array([v1, m12, m13, m01]),
            np.array([v2, m23, m02, m12]),
            np.array([v3, m03, m13, m23]),
            np.array([m01, m02, m03, center]),
            np.array([m01, m12, m13, center]),
            np.array([m02, m12, m23, center]),
            np.array([m03, m13, m23, center])
        ]

        return new_cells, new_points

    def _split_hexahedron(self, cell: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
        v0, v1, v2, v3, v4, v5, v6, v7 = cell
        p = self.points[cell]

        mid_indices = {}
        new_points_list = []

        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]

        for i, j in edges:
            mid_idx = len(self.points) + len(new_points_list)
            mid_indices[(i, j)] = mid_idx
            mid_indices[(j, i)] = mid_idx
            new_points_list.append((p[i] + p[j]) / 2)

        face_centers = {}
        faces = [
            (0, 1, 2, 3), (4, 5, 6, 7),
            (0, 1, 5, 4), (2, 3, 7, 6),
            (0, 3, 7, 4), (1, 2, 6, 5)
        ]

        for face in faces:
            fc_idx = len(self.points) + len(new_points_list)
            face_centers[face] = fc_idx
            face_centers[tuple(reversed(face))] = fc_idx
            new_points_list.append(np.mean(p[list(face)], axis=0))

        center_idx = len(self.points) + len(new_points_list)
        new_points_list.append(np.mean(p, axis=0))

        new_points = np.array(new_points_list)

        new_cells = [
            np.array([v0, mid_indices[(0,1)], face_centers[(0,1,5,4)], mid_indices[(0,4)],
                      mid_indices[(0,3)], face_centers[(0,3,7,4)], face_centers[(0,1,2,3)]],
            np.array([v1, mid_indices[(1,2)], face_centers[(1,2,6,5)], mid_indices[(0,1)],
                      mid_indices[(1,5)], face_centers[(0,1,5,4)], face_centers[(0,1,2,3)]])
        ]

        return new_cells, new_points

    def smooth_transition(self, iterations: int = 3) -> meshio.Mesh:
        return self.laplacian_smooth(iterations=iterations, relaxation=0.3, fixed_boundary=True)

    def optimize_mesh(self, smooth_iterations: int = 10, refinement_method: str = 'quality',
                       refinement_threshold: Optional[float] = None, max_refinement_level: int = 2) -> Dict:
        quality_before = self._compute_quality_summary()

        self.laplacian_smooth(iterations=smooth_iterations)

        if max_refinement_level > 0:
            self.adaptive_refine(method=refinement_method, threshold=refinement_threshold,
                                 max_level=max_refinement_level)
            self.smooth_transition()

        quality_after = self._compute_quality_summary()

        return {
            'before': quality_before,
            'after': quality_after,
            'mesh': self.mesh
        }

    def _compute_quality_summary(self) -> Dict:
        quality = MeshQuality(self.points, self.cells)
        metrics = quality.compute_all_metrics()
        stats = quality.get_statistics()

        summary = {
            'num_points': len(self.points),
            'num_cells': sum(len(cb.data) for cb in self.cells),
            'statistics': stats
        }

        return summary

    def get_current_mesh(self) -> meshio.Mesh:
        return self.mesh

    def reset(self):
        self.points = self.original_mesh.points.copy()
        self.cells = self.original_mesh.cells
        self.mesh = meshio.Mesh(self.points, self.cells)
        self.vertex_neighbors = self._build_vertex_connectivity()
