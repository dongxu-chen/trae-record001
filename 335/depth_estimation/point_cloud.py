import numpy as np
import cv2
import os
from typing import Optional, Tuple, Union

from config.config import PointCloudConfig

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    o3d = None


def require_open3d(func):
    def wrapper(*args, **kwargs):
        if not OPEN3D_AVAILABLE:
            raise ImportError(
                "Open3D is required for this functionality. "
                "Please install it with: pip install open3d"
            )
        return func(*args, **kwargs)
    return wrapper


class PointCloudGenerator:
    def __init__(self, config: PointCloudConfig):
        if not OPEN3D_AVAILABLE:
            print("⚠️  Warning: Open3D is not installed. Point cloud generation will be limited.")
            print("   Install Open3D for full functionality: pip install open3d")
        
        self.config = config
        self.point_cloud = None
        self._numpy_points = None
        self._numpy_colors = None

    @require_open3d
    def _get_intrinsics(self, image_shape: Tuple[int, int]) -> 'o3d.camera.PinholeCameraIntrinsic':
        h, w = image_shape
        
        fx = self.config.fx
        fy = self.config.fy
        cx = self.config.cx if self.config.cx is not None else w / 2.0
        cy = self.config.cy if self.config.cy is not None else h / 2.0
        
        intrinsic = o3d.camera.PinholeCameraIntrinsic(
            width=w,
            height=h,
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy
        )
        
        return intrinsic

    def _generate_numpy_pcl(self, rgb_image: np.ndarray, depth_map: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        h, w = depth_map.shape
        
        fx = self.config.fx
        fy = self.config.fy
        cx = self.config.cx if self.config.cx is not None else w / 2.0
        cy = self.config.cy if self.config.cy is not None else h / 2.0
        
        depth_processed = self._process_depth_for_pcl(depth_map)
        
        x, y = np.meshgrid(np.arange(w), np.arange(h))
        
        z = depth_processed / self.config.depth_scale
        x3d = (x - cx) * z / fx
        y3d = (y - cy) * z / fy
        
        valid_mask = z > 0
        
        points = np.stack([x3d[valid_mask], y3d[valid_mask], z[valid_mask]], axis=-1)
        
        rgb_for_pcl = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        colors = rgb_for_pcl[valid_mask]
        
        return points, colors

    def generate(self, rgb_image: np.ndarray, depth_map: np.ndarray) -> Union['o3d.geometry.PointCloud', Tuple[np.ndarray, np.ndarray]]:
        if rgb_image.shape[:2] != depth_map.shape:
            raise ValueError(
                f"RGB image shape {rgb_image.shape[:2]} does not match "
                f"depth map shape {depth_map.shape}"
            )
        
        if OPEN3D_AVAILABLE:
            return self._generate_open3d(rgb_image, depth_map)
        else:
            return self._generate_numpy(rgb_image, depth_map)

    @require_open3d
    def _generate_open3d(self, rgb_image: np.ndarray, depth_map: np.ndarray) -> 'o3d.geometry.PointCloud':
        h, w = depth_map.shape
        
        rgb_for_pcl = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)
        
        depth_processed = self._process_depth_for_pcl(depth_map)
        
        rgb_o3d = o3d.geometry.Image(rgb_for_pcl.astype(np.uint8))
        depth_o3d = o3d.geometry.Image(depth_processed.astype(np.float32))
        
        rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
            rgb_o3d,
            depth_o3d,
            depth_scale=self.config.depth_scale,
            depth_trunc=self.config.max_depth,
            convert_rgb_to_intensity=False
        )
        
        intrinsic = self._get_intrinsics((h, w))
        
        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
            rgbd_image,
            intrinsic
        )
        
        pcd.transform([[1, 0, 0, 0],
                      [0, -1, 0, 0],
                      [0, 0, -1, 0],
                      [0, 0, 0, 1]])
        
        if self.config.downsample:
            pcd = pcd.voxel_down_sample(voxel_size=self.config.downsample_voxel_size)
        
        if self.config.remove_outliers:
            pcd, _ = pcd.remove_statistical_outlier(
                nb_neighbors=self.config.nb_neighbors,
                std_ratio=self.config.std_ratio
            )
        
        self.point_cloud = pcd
        
        if self.config.save_path:
            self.save(self.config.save_path)
        
        if self.config.show:
            self.visualize()
        
        return pcd

    def _generate_numpy(self, rgb_image: np.ndarray, depth_map: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        print("Generating point cloud using NumPy fallback (Open3D not available)...")
        
        points, colors = self._generate_numpy_pcl(rgb_image, depth_map)
        
        if self.config.downsample:
            voxel_size = self.config.downsample_voxel_size
            if voxel_size > 0:
                points, colors = self._voxel_downsample_numpy(points, colors, voxel_size)
        
        if self.config.remove_outliers:
            points, colors = self._remove_outliers_numpy(
                points, colors,
                self.config.nb_neighbors,
                self.config.std_ratio
            )
        
        self._numpy_points = points
        self._numpy_colors = colors
        
        if self.config.save_path:
            self.save_numpy(self.config.save_path, points, colors)
        
        print(f"Generated point cloud with {len(points)} points (NumPy fallback)")
        
        return points, colors

    def _voxel_downsample_numpy(self, points: np.ndarray, colors: np.ndarray, voxel_size: float) -> Tuple[np.ndarray, np.ndarray]:
        voxel_indices = np.floor(points / voxel_size).astype(np.int64)
        
        unique_voxels, inverse_indices = np.unique(voxel_indices, axis=0, return_inverse=True)
        
        downsampled_points = np.zeros((len(unique_voxels), 3), dtype=np.float32)
        downsampled_colors = np.zeros((len(unique_voxels), 3), dtype=np.float32)
        
        for i in range(len(unique_voxels)):
            mask = inverse_indices == i
            downsampled_points[i] = np.mean(points[mask], axis=0)
            downsampled_colors[i] = np.mean(colors[mask], axis=0)
        
        return downsampled_points, downsampled_colors

    def _remove_outliers_numpy(self, points: np.ndarray, colors: np.ndarray, nb_neighbors: int, std_ratio: float) -> Tuple[np.ndarray, np.ndarray]:
        if len(points) < nb_neighbors:
            return points, colors
        
        from scipy.spatial import cKDTree
        
        tree = cKDTree(points)
        distances, _ = tree.query(points, k=nb_neighbors)
        mean_distances = np.mean(distances[:, 1:], axis=1)
        
        threshold = np.mean(mean_distances) + std_ratio * np.std(mean_distances)
        mask = mean_distances < threshold
        
        return points[mask], colors[mask]

    def _process_depth_for_pcl(self, depth_map: np.ndarray) -> np.ndarray:
        depth = depth_map.copy()
        
        depth[np.isnan(depth)] = 0.0
        depth[np.isinf(depth)] = 0.0
        depth[depth < self.config.min_depth] = 0.0
        depth[depth > self.config.max_depth] = 0.0
        
        return depth

    @require_open3d
    def generate_from_rgbd(self, rgbd_image: 'o3d.geometry.RGBDImage',
                          intrinsic: 'o3d.camera.PinholeCameraIntrinsic') -> 'o3d.geometry.PointCloud':
        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
            rgbd_image,
            intrinsic
        )
        
        pcd.transform([[1, 0, 0, 0],
                      [0, -1, 0, 0],
                      [0, 0, -1, 0],
                      [0, 0, 0, 1]])
        
        if self.config.downsample:
            pcd = pcd.voxel_down_sample(voxel_size=self.config.downsample_voxel_size)
        
        if self.config.remove_outliers:
            pcd, _ = pcd.remove_statistical_outlier(
                nb_neighbors=self.config.nb_neighbors,
                std_ratio=self.config.std_ratio
            )
        
        self.point_cloud = pcd
        return pcd

    @require_open3d
    def generate_from_numpy(self, points: np.ndarray, colors: Optional[np.ndarray] = None) -> 'o3d.geometry.PointCloud':
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        if colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(colors)
        
        if self.config.downsample:
            pcd = pcd.voxel_down_sample(voxel_size=self.config.downsample_voxel_size)
        
        if self.config.remove_outliers:
            pcd, _ = pcd.remove_statistical_outlier(
                nb_neighbors=self.config.nb_neighbors,
                std_ratio=self.config.std_ratio
            )
        
        self.point_cloud = pcd
        return pcd

    @require_open3d
    def visualize(self, pcd: Optional['o3d.geometry.PointCloud'] = None) -> None:
        pcd_to_show = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_show is None:
            raise RuntimeError("No point cloud available for visualization")
        
        o3d.visualization.draw_geometries([pcd_to_show])

    def save(self, path: str, pcd: Optional['o3d.geometry.PointCloud'] = None) -> None:
        if not OPEN3D_AVAILABLE:
            if self._numpy_points is not None and self._numpy_colors is not None:
                self.save_numpy(path, self._numpy_points, self._numpy_colors)
                return
            else:
                raise RuntimeError("No point cloud data available for saving")
        
        pcd_to_save = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_save is None:
            raise RuntimeError("No point cloud available for saving")
        
        ext = os.path.splitext(path)[1].lower()
        
        if ext == '.pcd':
            o3d.io.write_point_cloud(path, pcd_to_save, write_ascii=True)
        elif ext == '.ply':
            o3d.io.write_point_cloud(path, pcd_to_save, write_ascii=True)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Use .pcd or .ply")
        
        print(f"Point cloud saved to {path}")

    def save_numpy(self, path: str, points: np.ndarray, colors: Optional[np.ndarray] = None) -> None:
        ext = os.path.splitext(path)[1].lower()
        
        if ext == '.ply':
            self._save_ply_numpy(path, points, colors)
        elif ext == '.pcd':
            self._save_pcd_numpy(path, points, colors)
        elif ext == '.npy':
            data = {'points': points}
            if colors is not None:
                data['colors'] = colors
            np.save(path, data)
        else:
            raise ValueError(f"Unsupported file format for NumPy fallback: {ext}")
        
        print(f"Point cloud saved to {path} (NumPy format)")

    def _save_ply_numpy(self, path: str, points: np.ndarray, colors: Optional[np.ndarray] = None) -> None:
        with open(path, 'w') as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {len(points)}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            if colors is not None:
                f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
            f.write("end_header\n")
            
            for i in range(len(points)):
                line = f"{points[i, 0]:.6f} {points[i, 1]:.6f} {points[i, 2]:.6f}"
                if colors is not None:
                    r, g, b = (colors[i] * 255).astype(np.uint8)
                    line += f" {r} {g} {b}"
                f.write(line + "\n")

    def _save_pcd_numpy(self, path: str, points: np.ndarray, colors: Optional[np.ndarray] = None) -> None:
        with open(path, 'w') as f:
            f.write("# .PCD v.7 - Point Cloud Data file format\n")
            f.write("VERSION .7\n")
            if colors is not None:
                f.write("FIELDS x y z rgb\n")
                f.write("SIZE 4 4 4 4\n")
                f.write("TYPE F F F U\n")
            else:
                f.write("FIELDS x y z\n")
                f.write("SIZE 4 4 4\n")
                f.write("TYPE F F F\n")
            f.write("COUNT 1 1 1 1\n" if colors is not None else "COUNT 1 1 1\n")
            f.write(f"WIDTH {len(points)}\n")
            f.write("HEIGHT 1\n")
            f.write("VIEWPOINT 0 0 0 1 0 0 0\n")
            f.write(f"POINTS {len(points)}\n")
            f.write("DATA ascii\n")
            
            for i in range(len(points)):
                line = f"{points[i, 0]:.6f} {points[i, 1]:.6f} {points[i, 2]:.6f}"
                if colors is not None:
                    r, g, b = (colors[i] * 255).astype(np.uint8)
                    rgb = (int(r) << 16) | (int(g) << 8) | int(b)
                    line += f" {rgb}"
                f.write(line + "\n")

    @require_open3d
    def load(self, path: str) -> 'o3d.geometry.PointCloud':
        if not os.path.exists(path):
            raise FileNotFoundError(f"Point cloud file not found: {path}")
        
        self.point_cloud = o3d.io.read_point_cloud(path)
        print(f"Loaded point cloud with {len(self.point_cloud.points)} points")
        return self.point_cloud

    @require_open3d
    def estimate_normals(self, pcd: Optional['o3d.geometry.PointCloud'] = None,
                       radius: float = 0.1, max_nn: int = 30) -> 'o3d.geometry.PointCloud':
        pcd_to_process = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_process is None:
            raise RuntimeError("No point cloud available")
        
        pcd_to_process.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=radius,
                max_nn=max_nn
            )
        )
        pcd_to_process.orient_normals_consistent_tangent_plane(100)
        
        return pcd_to_process

    @require_open3d
    def reconstruct_mesh(self, pcd: Optional['o3d.geometry.PointCloud'] = None,
                        depth: int = 9, width: float = 0.0) -> 'o3d.geometry.TriangleMesh':
        pcd_to_process = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_process is None:
            raise RuntimeError("No point cloud available")
        
        if not pcd_to_process.has_normals():
            self.estimate_normals(pcd_to_process)
        
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd_to_process,
            depth=depth,
            width=width
        )
        
        vertices_to_remove = densities < np.quantile(densities, 0.01)
        mesh.remove_vertices_by_mask(vertices_to_remove)
        
        return mesh

    def get_point_cloud_stats(self, pcd: Optional[Union['o3d.geometry.PointCloud', np.ndarray]] = None) -> dict:
        if not OPEN3D_AVAILABLE or isinstance(pcd, np.ndarray) or (pcd is None and self._numpy_points is not None):
            if pcd is None:
                points = self._numpy_points
            elif isinstance(pcd, tuple):
                points = pcd[0]
            else:
                points = pcd
            
            if points is None:
                return {}
            
            stats = {
                "num_points": len(points),
                "has_colors": self._numpy_colors is not None,
                "has_normals": False,
                "bbox_min": np.min(points, axis=0).tolist(),
                "bbox_max": np.max(points, axis=0).tolist(),
                "center": np.mean(points, axis=0).tolist(),
                "backend": "NumPy"
            }
            
            if self._numpy_colors is not None:
                stats["mean_color"] = np.mean(self._numpy_colors, axis=0).tolist()
            
            return stats
        
        pcd_to_check = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_check is None:
            return {}
        
        points = np.asarray(pcd_to_check.points)
        
        stats = {
            "num_points": len(points),
            "has_colors": pcd_to_check.has_colors(),
            "has_normals": pcd_to_check.has_normals(),
            "bbox_min": np.min(points, axis=0).tolist(),
            "bbox_max": np.max(points, axis=0).tolist(),
            "center": np.mean(points, axis=0).tolist(),
            "backend": "Open3D"
        }
        
        if pcd_to_check.has_colors():
            colors = np.asarray(pcd_to_check.colors)
            stats["mean_color"] = np.mean(colors, axis=0).tolist()
        
        return stats

    @staticmethod
    @require_open3d
    def apply_transform(pcd: 'o3d.geometry.PointCloud', 
                       transform: np.ndarray) -> 'o3d.geometry.PointCloud':
        if transform.shape != (4, 4):
            raise ValueError("Transform must be a 4x4 matrix")
        
        pcd.transform(transform)
        return pcd

    @staticmethod
    @require_open3d
    def merge_point_clouds(pcd_list: list) -> 'o3d.geometry.PointCloud':
        if not pcd_list:
            raise ValueError("No point clouds to merge")
        
        merged = pcd_list[0]
        for pcd in pcd_list[1:]:
            merged += pcd
        
        return merged

    @require_open3d
    def crop_point_cloud(self, pcd: Optional['o3d.geometry.PointCloud'] = None,
                        min_bound: Optional[np.ndarray] = None,
                        max_bound: Optional[np.ndarray] = None) -> 'o3d.geometry.PointCloud':
        pcd_to_crop = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_crop is None:
            raise RuntimeError("No point cloud available")
        
        if min_bound is None or max_bound is None:
            bbox = pcd_to_crop.get_axis_aligned_bounding_box()
            min_bound = bbox.min_bound
            max_bound = bbox.max_bound
        
        bbox = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
        cropped = pcd_to_crop.crop(bbox)
        
        return cropped

    def filter_by_distance(self, pcd: Optional[Union['o3d.geometry.PointCloud', Tuple[np.ndarray, np.ndarray]]] = None,
                          min_dist: float = 0.0,
                          max_dist: float = 10.0) -> Union['o3d.geometry.PointCloud', Tuple[np.ndarray, np.ndarray]]:
        if not OPEN3D_AVAILABLE or (pcd is None and self._numpy_points is not None) or isinstance(pcd, tuple):
            if pcd is None:
                points = self._numpy_points
                colors = self._numpy_colors
            elif isinstance(pcd, tuple):
                points = pcd[0]
                colors = pcd[1] if len(pcd) > 1 else None
            else:
                points = np.asarray(pcd.points)
                colors = np.asarray(pcd.colors) if pcd.has_colors() else None
            
            if points is None:
                raise RuntimeError("No point cloud available")
            
            distances = np.linalg.norm(points, axis=1)
            mask = (distances >= min_dist) & (distances <= max_dist)
            
            filtered_points = points[mask]
            filtered_colors = colors[mask] if colors is not None else None
            
            return filtered_points, filtered_colors
        
        pcd_to_filter = pcd if pcd is not None else self.point_cloud
        
        if pcd_to_filter is None:
            raise RuntimeError("No point cloud available")
        
        points = np.asarray(pcd_to_filter.points)
        distances = np.linalg.norm(points, axis=1)
        
        mask = (distances >= min_dist) & (distances <= max_dist)
        
        filtered = pcd_to_filter.select_by_index(np.where(mask)[0])
        
        return filtered
