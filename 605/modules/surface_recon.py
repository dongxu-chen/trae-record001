import logging
import numpy as np
import open3d as o3d
from config import RECONSTRUCTION_CONFIG

logger = logging.getLogger(__name__)


class SurfaceReconstructor:
    def __init__(self, config=None):
        self.config = config or RECONSTRUCTION_CONFIG
        self.poisson_depth = self.config["poisson_depth"]
        self.simplify_factor = self.config["simplify_factor"]
        self.smooth_iter = self.config["smooth_iter"]

    def poisson_reconstruction(self, pcd, depth=None, scale=1.1, linear_fit=False):
        if depth is None:
            depth = self.poisson_depth

        if not pcd.has_normals():
            logger.info("Estimating normals for Poisson reconstruction")
            pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
            )
            pcd.orient_normals_consistent_tangent_plane(k=15)

        logger.info(f"Running Poisson reconstruction (depth={depth})")
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd, depth=depth, scale=scale, linear_fit=linear_fit
        )

        vertices_to_remove = densities < np.quantile(densities, 0.1)
        mesh.remove_vertices_by_mask(vertices_to_remove)
        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_duplicated_vertices()
        mesh.remove_unreferenced_vertices()

        logger.info(
            f"Poisson mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles"
        )
        return mesh

    def ball_pivoting_reconstruction(self, pcd, radii=None):
        if radii is None:
            bbox = pcd.get_axis_aligned_bounding_box()
            extent = bbox.get_extent()
            avg_extent = np.mean(extent)
            radii = [
                avg_extent * 0.005,
                avg_extent * 0.01,
                avg_extent * 0.02,
                avg_extent * 0.04,
            ]

        radii_o3d = o3d.utility.DoubleVector(radii)

        if not pcd.has_normals():
            logger.info("Estimating normals for Ball Pivoting reconstruction")
            pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
            )
            pcd.orient_normals_consistent_tangent_plane(k=15)

        logger.info(f"Running Ball Pivoting reconstruction (radii={radii})")
        mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(pcd, radii_o3d)

        if mesh is None or len(mesh.triangles) == 0:
            logger.warning("Ball Pivoting reconstruction produced empty mesh")
            return None

        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_duplicated_vertices()
        mesh.remove_unreferenced_vertices()

        logger.info(
            f"Ball Pivoting mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles"
        )
        return mesh

    def simplify_mesh(self, mesh, target_factor=None):
        if target_factor is None:
            target_factor = self.simplify_factor

        target_triangles = int(len(mesh.triangles) * target_factor)
        if target_triangles < 100:
            target_triangles = 100

        simplified = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangles)
        simplified.remove_degenerate_triangles()
        simplified.remove_duplicated_triangles()

        logger.info(
            f"Simplified mesh: {len(simplified.vertices)} vertices, "
            f"{len(simplified.triangles)} triangles (factor={target_factor})"
        )
        return simplified

    def smooth_mesh(self, mesh, iterations=None):
        if iterations is None:
            iterations = self.smooth_iter

        smoothed = mesh.filter_smooth_taubin(number_of_iterations=iterations)
        smoothed.remove_degenerate_triangles()
        smoothed.remove_duplicated_triangles()

        logger.info(f"Smoothed mesh with {iterations} iterations")
        return smoothed

    def subdivide_mesh(self, mesh, iterations=1):
        subdivided = mesh.subdivide_midpoint(number_of_iterations=iterations)
        logger.info(
            f"Subdivided mesh: {len(subdivided.vertices)} vertices, "
            f"{len(subdivided.triangles)} triangles"
        )
        return subdivided

    def compute_mesh_quality(self, mesh):
        stats = {
            "num_vertices": len(mesh.vertices),
            "num_triangles": len(mesh.triangles),
            "is_watertight": mesh.is_watertight(),
        }

        if mesh.has_vertex_normals():
            stats["has_vertex_normals"] = True
        if mesh.has_vertex_colors():
            stats["has_vertex_colors"] = True

        triangle_normals = np.asarray(mesh.triangle_normals)
        if len(triangle_normals) > 0:
            areas = np.linalg.norm(np.asarray(mesh.triangles), axis=1) * 0.5
            stats["total_area"] = float(np.sum(areas))
            stats["avg_triangle_area"] = float(np.mean(areas))

        return stats

    def reconstruct(
        self,
        pcd,
        method="poisson",
        simplify=True,
        smooth=True,
        **kwargs,
    ):
        if method == "poisson":
            mesh = self.poisson_reconstruction(pcd, **kwargs)
        elif method == "ball_pivoting":
            mesh = self.ball_pivoting_reconstruction(pcd, **kwargs)
        else:
            raise ValueError(f"Unknown reconstruction method: {method}")

        if mesh is None:
            return None

        if smooth:
            mesh = self.smooth_mesh(mesh)

        if simplify:
            mesh = self.simplify_mesh(mesh)

        mesh.compute_vertex_normals()

        return mesh

    @staticmethod
    def save_mesh(mesh, output_path):
        base_path = output_path.rsplit(".", 1)[0]

        ply_path = base_path + ".ply"
        o3d.io.write_triangle_mesh(ply_path, mesh)
        logger.info(f"Saved mesh (PLY): {ply_path}")

        obj_path = base_path + ".obj"
        o3d.io.write_triangle_mesh(obj_path, mesh)
        logger.info(f"Saved mesh (OBJ): {obj_path}")

        return ply_path, obj_path

    @staticmethod
    def export_to_dict(mesh):
        vertices = np.asarray(mesh.vertices).tolist()
        triangles = np.asarray(mesh.triangles).tolist()
        result = {"vertices": vertices, "triangles": triangles}

        if mesh.has_vertex_normals():
            result["vertex_normals"] = np.asarray(mesh.vertex_normals).tolist()
        if mesh.has_vertex_colors():
            result["vertex_colors"] = np.asarray(mesh.vertex_colors).tolist()

        return result
