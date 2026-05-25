import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    o3d = None

from config.config import PointCloudConfig
from depth_estimation import PointCloudGenerator


def create_test_data():
    h, w = 240, 320
    y, x = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    
    depth_map = 2.0 + 1.0 * np.sin(x / 30.0) * np.cos(y / 30.0)
    rgb_image = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    
    return rgb_image, depth_map


def test_point_cloud_generation():
    print("Testing point cloud generation...")
    
    config = PointCloudConfig()
    config.downsample = True
    config.downsample_voxel_size = 0.05
    config.remove_outliers = True
    config.show = False
    config.save_path = None
    
    generator = PointCloudGenerator(config)
    rgb_image, depth_map = create_test_data()
    
    result = generator.generate(rgb_image, depth_map)
    
    assert result is not None
    
    if OPEN3D_AVAILABLE:
        assert len(result.points) > 0
        assert result.has_colors()
        print(f"✓ Point cloud generated with {len(result.points)} points (Open3D)")
    else:
        points, colors = result
        assert len(points) > 0
        assert colors is not None
        print(f"✓ Point cloud generated with {len(points)} points (NumPy fallback)")
    
    return True


def test_intrinsics():
    print("\nTesting camera intrinsics...")
    
    config = PointCloudConfig()
    config.fx = 500.0
    config.fy = 500.0
    config.cx = 160.0
    config.cy = 120.0
    
    generator = PointCloudGenerator(config)
    
    if OPEN3D_AVAILABLE:
        intrinsic = generator._get_intrinsics((240, 320))
        
        assert intrinsic.width == 320
        assert intrinsic.height == 240
        assert intrinsic.intrinsic_matrix[0, 0] == 500.0
        assert intrinsic.intrinsic_matrix[1, 1] == 500.0
        assert intrinsic.intrinsic_matrix[0, 2] == 160.0
        assert intrinsic.intrinsic_matrix[1, 2] == 120.0
        
        print("✓ Camera intrinsics test passed (Open3D)")
    else:
        print("⚠️  Skipping Open3D intrinsics test (Open3D not available)")
    
    return True


def test_point_cloud_stats():
    print("\nTesting point cloud statistics...")
    
    config = PointCloudConfig()
    config.downsample = False
    config.remove_outliers = False
    config.show = False
    
    generator = PointCloudGenerator(config)
    rgb_image, depth_map = create_test_data()
    
    generator.generate(rgb_image, depth_map)
    stats = generator.get_point_cloud_stats()
    
    assert "num_points" in stats
    assert "has_colors" in stats
    assert "bbox_min" in stats
    assert "bbox_max" in stats
    assert "center" in stats
    
    print(f"✓ Point cloud stats: {stats}")
    return True


def test_point_cloud_filters():
    print("\nTesting point cloud filters...")
    
    config = PointCloudConfig()
    config.downsample = False
    config.remove_outliers = False
    config.show = False
    
    generator = PointCloudGenerator(config)
    rgb_image, depth_map = create_test_data()
    
    pcd = generator.generate(rgb_image, depth_map)
    
    if OPEN3D_AVAILABLE:
        original_count = len(pcd.points)
    else:
        original_count = len(pcd[0])
    
    filtered = generator.filter_by_distance(pcd, min_dist=1.5, max_dist=3.5)
    
    if OPEN3D_AVAILABLE:
        filtered_count = len(filtered.points)
    else:
        filtered_count = len(filtered[0])
    
    assert filtered_count <= original_count
    print(f"✓ Distance filter: {original_count} -> {filtered_count} points")
    
    return True


def test_point_cloud_io(tmp_path=None):
    print("\nTesting point cloud I/O...")
    
    config = PointCloudConfig()
    config.downsample = True
    config.downsample_voxel_size = 0.1
    config.remove_outliers = False
    config.show = False
    
    generator = PointCloudGenerator(config)
    rgb_image, depth_map = create_test_data()
    
    generator.generate(rgb_image, depth_map)
    
    if tmp_path is None:
        tmp_path = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(tmp_path, exist_ok=True)
    
    ply_path = os.path.join(tmp_path, "test.ply")
    generator.save(ply_path)
    assert os.path.exists(ply_path)
    
    if OPEN3D_AVAILABLE:
        loaded_pcd = generator.load(ply_path)
        if isinstance(generator.point_cloud, np.ndarray):
            original_count = len(generator.point_cloud)
        else:
            original_count = len(generator.point_cloud.points)
        assert len(loaded_pcd.points) == original_count or abs(len(loaded_pcd.points) - original_count) < 10
        print(f"✓ Point cloud I/O test passed ({len(loaded_pcd.points)} points)")
    else:
        print(f"✓ Point cloud saved to {ply_path} (NumPy format)")
    
    for f in os.listdir(tmp_path):
        os.remove(os.path.join(tmp_path, f))
    os.rmdir(tmp_path)
    
    return True


def test_numpy_fallback():
    print("\nTesting NumPy fallback functionality...")
    
    if OPEN3D_AVAILABLE:
        print("⚠️  Open3D is available, skipping NumPy fallback specific tests")
        return True
    
    config = PointCloudConfig()
    config.downsample = True
    config.downsample_voxel_size = 0.1
    config.remove_outliers = True
    config.show = False
    
    generator = PointCloudGenerator(config)
    rgb_image, depth_map = create_test_data()
    
    points, colors = generator.generate(rgb_image, depth_map)
    
    assert points.shape[1] == 3
    assert colors.shape[1] == 3
    assert len(points) == len(colors)
    
    print(f"✓ NumPy fallback: generated {len(points)} points")
    
    tmp_path = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(tmp_path, exist_ok=True)
    
    for ext in ['.ply', '.pcd', '.npy']:
        path = os.path.join(tmp_path, f"test{ext}")
        generator.save_numpy(path, points, colors)
        assert os.path.exists(path)
        print(f"  ✓ Saved {ext} format")
    
    for f in os.listdir(tmp_path):
        os.remove(os.path.join(tmp_path, f))
    os.rmdir(tmp_path)
    
    return True


def test_normal_estimation():
    print("\nTesting normal estimation...")
    
    if not OPEN3D_AVAILABLE:
        print("⚠️  Skipping normal estimation test (Open3D not available)")
        return True
    
    config = PointCloudConfig()
    config.downsample = True
    config.downsample_voxel_size = 0.05
    config.remove_outliers = False
    config.show = False
    
    generator = PointCloudGenerator(config)
    rgb_image, depth_map = create_test_data()
    
    pcd = generator.generate(rgb_image, depth_map)
    
    assert not pcd.has_normals()
    
    pcd_with_normals = generator.estimate_normals(pcd, radius=0.2, max_nn=20)
    
    assert pcd_with_normals.has_normals()
    normals = np.asarray(pcd_with_normals.normals)
    assert normals.shape[1] == 3
    
    print("✓ Normal estimation test passed")
    return True


def test_merge_point_clouds():
    print("\nTesting point cloud merging...")
    
    if not OPEN3D_AVAILABLE:
        print("⚠️  Skipping merge test (Open3D not available)")
        return True
    
    config = PointCloudConfig()
    config.downsample = False
    config.remove_outliers = False
    config.show = False
    
    generator = PointCloudGenerator(config)
    
    points1 = np.random.rand(100, 3)
    colors1 = np.random.rand(100, 3)
    pcd1 = generator.generate_from_numpy(points1, colors1)
    
    points2 = np.random.rand(150, 3) + 1.0
    colors2 = np.random.rand(150, 3)
    pcd2 = generator.generate_from_numpy(points2, colors2)
    
    merged = PointCloudGenerator.merge_point_clouds([pcd1, pcd2])
    
    assert len(merged.points) == 250
    
    print("✓ Point cloud merging test passed")
    return True


def main():
    print("=" * 50)
    print(f"Running Point Cloud Tests (Open3D available: {OPEN3D_AVAILABLE})")
    print("=" * 50)
    
    tests = [
        test_point_cloud_generation,
        test_intrinsics,
        test_point_cloud_stats,
        test_point_cloud_filters,
        test_point_cloud_io,
        test_numpy_fallback,
        test_normal_estimation,
        test_merge_point_clouds,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{len(tests)} passed")
    print("=" * 50)
    
    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
