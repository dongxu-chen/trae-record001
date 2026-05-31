import logging
import numpy as np
import open3d as o3d

logger = logging.getLogger(__name__)


class HoleAnalyzer:
    def __init__(
        self,
        max_hole_area_ratio=0.05,
        max_hole_perimeter_ratio=0.1,
        min_convexity=0.3,
        max_edge_length_ratio=0.2,
    ):
        self.max_hole_area_ratio = max_hole_area_ratio
        self.max_hole_perimeter_ratio = max_hole_perimeter_ratio
        self.min_convexity = min_convexity
        self.max_edge_length_ratio = max_edge_length_ratio

    def detect_holes(self, mesh):
        triangles = np.asarray(mesh.triangles)
        vertices = np.asarray(mesh.vertices)
        num_triangles = len(triangles)

        edge_occurrence = {}

        for tri_idx, tri in enumerate(triangles):
            edges = [
                tuple(sorted((tri[0], tri[1]))),
                tuple(sorted((tri[1], tri[2]))),
                tuple(sorted((tri[2], tri[0]))),
            ]
            for edge in edges:
                if edge not in edge_occurrence:
                    edge_occurrence[edge] = []
                edge_occurrence[edge].append(tri_idx)

        boundary_edges = [edge for edge, tris in edge_occurrence.items() if len(tris) == 1]

        if len(boundary_edges) == 0:
            logger.info("No boundary edges found - mesh is watertight")
            return []

        holes = self._group_edges_into_holes(boundary_edges)

        hole_analysis = []
        total_mesh_area = self._compute_mesh_area(mesh)
        total_edge_length = self._compute_avg_edge_length(mesh)

        for hole_idx, hole in enumerate(holes):
            analysis = self._analyze_hole(
                hole, vertices, total_mesh_area, total_edge_length
            )
            analysis["hole_idx"] = hole_idx
            hole_analysis.append(analysis)

        logger.info(f"Detected {len(holes)} holes in mesh")
        return hole_analysis

    def _group_edges_into_holes(self, boundary_edges):
        if not boundary_edges:
            return []

        edge_map = {}
        for v1, v2 in boundary_edges:
            if v1 not in edge_map:
                edge_map[v1] = []
            if v2 not in edge_map:
                edge_map[v2] = []
            edge_map[v1].append(v2)
            edge_map[v2].append(v1)

        visited = set()
        holes = []

        for start_v in edge_map:
            if start_v in visited:
                continue

            current_loop = []
            current_v = start_v
            prev_v = None

            while current_v not in visited:
                visited.add(current_v)
                current_loop.append(current_v)

                neighbors = edge_map.get(current_v, [])
                next_v = None
                for n in neighbors:
                    if n != prev_v:
                        next_v = n
                        break

                if next_v is None:
                    break

                prev_v = current_v
                current_v = next_v

            if len(current_loop) >= 3:
                holes.append(current_loop)

        return holes

    def _analyze_hole(self, hole_vertices, all_vertices, total_mesh_area, avg_edge_length):
        boundary_vertices = all_vertices[hole_vertices]
        num_boundary_edges = len(hole_vertices)

        centroid = np.mean(boundary_vertices, axis=0)

        vectors = boundary_vertices - centroid
        cross_products = np.cross(vectors[:-1], vectors[1:])
        area_2d = 0.5 * np.sum(np.linalg.norm(cross_products, axis=1))

        perimeter = 0
        for i in range(len(hole_vertices)):
            v1 = boundary_vertices[i]
            v2 = boundary_vertices[(i + 1) % len(hole_vertices)]
            perimeter += np.linalg.norm(v2 - v1)

        if perimeter > 0:
            shape_compactness = (4 * np.pi * area_2d) / (perimeter ** 2)
        else:
            shape_compactness = 0

        avg_hole_edge = perimeter / num_boundary_edges if num_boundary_edges > 0 else 0
        edge_length_ratio = avg_hole_edge / (avg_edge_length + 1e-8)

        area_ratio = area_2d / (total_mesh_area + 1e-8)
        perimeter_ratio = perimeter / (total_mesh_area ** 0.5 + 1e-8)

        distances = np.linalg.norm(vectors, axis=1)
        max_dist = np.max(distances)
        min_dist = np.min(distances)
        convexity = min_dist / (max_dist + 1e-8) if max_dist > 0 else 0

        return {
            "vertices": hole_vertices,
            "centroid": centroid.tolist(),
            "area": float(area_2d),
            "perimeter": float(perimeter),
            "num_boundary_edges": num_boundary_edges,
            "shape_compactness": float(shape_compactness),
            "convexity": float(convexity),
            "area_ratio": float(area_ratio),
            "perimeter_ratio": float(perimeter_ratio),
            "edge_length_ratio": float(edge_length_ratio),
        }

    def _compute_mesh_area(self, mesh):
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)

        if len(triangles) == 0:
            return 0

        v0 = vertices[triangles[:, 0]]
        v1 = vertices[triangles[:, 1]]
        v2 = vertices[triangles[:, 2]]

        cross = np.cross(v1 - v0, v2 - v0)
        areas = 0.5 * np.linalg.norm(cross, axis=1)

        return np.sum(areas)

    def _compute_avg_edge_length(self, mesh):
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)

        if len(triangles) == 0:
            return 0

        edges = np.vstack([
            triangles[:, [0, 1]],
            triangles[:, [1, 2]],
            triangles[:, [2, 0]],
        ])
        edges = np.sort(edges, axis=1)
        edges = np.unique(edges, axis=0)

        v0 = vertices[edges[:, 0]]
        v1 = vertices[edges[:, 1]]
        lengths = np.linalg.norm(v1 - v0, axis=1)

        return np.mean(lengths)

    def is_hole_fillable(self, hole_analysis):
        if hole_analysis["area_ratio"] > self.max_hole_area_ratio:
            return False, "Area too large"

        if hole_analysis["perimeter_ratio"] > self.max_hole_perimeter_ratio:
            return False, "Perimeter too large"

        if hole_analysis["convexity"] < self.min_convexity:
            return False, "Non-convex shape"

        if hole_analysis["edge_length_ratio"] > self.max_edge_length_ratio:
            return False, "Edges too long"

        return True, "Valid"


class SmartHoleFiller:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer or HoleAnalyzer()

    def fill_holes_smart(self, mesh, max_iterations=5, hole_size=0):
        hole_analyses = self.analyzer.detect_holes(mesh)

        if not hole_analyses:
            logger.info("No holes to fill")
            return mesh, []

        fillable_holes = []
        non_fillable_holes = []

        for analysis in hole_analyses:
            fillable, reason = self.analyzer.is_hole_fillable(analysis)
            if fillable:
                fillable_holes.append(analysis)
            else:
                analysis["skip_reason"] = reason
                non_fillable_holes.append(analysis)

        logger.info(
            f"Fillable: {len(fillable_holes)} holes, "
            f"Skipped: {len(non_fillable_holes)} holes"
        )

        if not fillable_holes:
            logger.info("No fillable holes detected")
            return mesh, non_fillable_holes

        for analysis in fillable_holes:
            logger.info(
                f"Filling hole {analysis['hole_idx']}: "
                f"area={analysis['area']:.6f}, edges={analysis['num_boundary_edges']}"
            )

        filled_mesh = mesh.copy()
        for _ in range(max_iterations):
            holes_before = self._count_holes(filled_mesh)
            filled_mesh = filled_mesh.fill_holes(hole_size=hole_size)
            holes_after = self._count_holes(filled_mesh)
            if holes_after == holes_before:
                break

        filled_mesh.remove_degenerate_triangles()
        filled_mesh.remove_duplicated_triangles()
        filled_mesh.remove_unreferenced_vertices()

        fill_stats = {
            "total_holes": len(hole_analyses),
            "filled_holes": len(fillable_holes),
            "skipped_holes": len(non_fillable_holes),
            "skipped_details": non_fillable_holes,
        }

        return filled_mesh, fill_stats

    def _count_holes(self, mesh):
        triangles = np.asarray(mesh.triangles)
        if len(triangles) == 0:
            return 0

        edge_occurrence = {}
        for tri in triangles:
            edges = [
                tuple(sorted((tri[0], tri[1]))),
                tuple(sorted((tri[1], tri[2]))),
                tuple(sorted((tri[2], tri[0]))),
            ]
            for edge in edges:
                edge_occurrence[edge] = edge_occurrence.get(edge, 0) + 1

        boundary_edges = sum(1 for cnt in edge_occurrence.values() if cnt == 1)
        return boundary_edges


class EnhancedSurfaceReconstructor:
    def __init__(self, config=None):
        from modules.surface_recon import SurfaceReconstructor
        self.base_reconstructor = SurfaceReconstructor(config)
        self.hole_analyzer = HoleAnalyzer()
        self.hole_filler = SmartHoleFiller(self.hole_analyzer)

    def reconstruct_with_hole_handling(
        self,
        pcd,
        method="poisson",
        fill_holes=True,
        simplify=True,
        smooth=True,
        **kwargs,
    ):
        mesh = self.base_reconstructor.reconstruct(
            pcd, method=method, simplify=simplify, smooth=smooth, **kwargs
        )

        if mesh is None:
            return None, None

        if fill_holes:
            mesh, fill_stats = self.hole_filler.fill_holes_smart(mesh)
        else:
            hole_analyses = self.hole_analyzer.detect_holes(mesh)
            fill_stats = {
                "total_holes": len(hole_analyses),
                "filled_holes": 0,
                "skipped_holes": len(hole_analyses),
            }

        mesh.compute_vertex_normals()

        return mesh, fill_stats

    def get_hole_report(self, mesh):
        hole_analyses = self.hole_analyzer.detect_holes(mesh)

        report = {
            "num_holes": len(hole_analyses),
            "holes": [],
        }

        for analysis in hole_analyses:
            fillable, reason = self.hole_analyzer.is_hole_fillable(analysis)
            report["holes"].append({
                "hole_idx": analysis["hole_idx"],
                "area": analysis["area"],
                "perimeter": analysis["perimeter"],
                "num_edges": analysis["num_boundary_edges"],
                "convexity": analysis["convexity"],
                "shape_compactness": analysis["shape_compactness"],
                "fillable": fillable,
                "fillable_reason": reason,
            })

        return report
