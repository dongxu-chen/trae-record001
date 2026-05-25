import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from config.config import Config, PointCloudConfig
from depth_estimation import MidasModel, DepthPostProcessor, PointCloudGenerator


def main():
    config = Config()
    config.model.model_type = "DPT_Large"
    config.model.device = "cuda"
    
    image_path = "input.jpg"
    
    if not os.path.exists(image_path):
        print(f"Creating test image: {image_path}")
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        cv2.imwrite(image_path, test_image)
    
    print("Loading image...")
    image = cv2.imread(image_path)
    
    print("Estimating depth...")
    model = MidasModel(config.model)
    post_processor = DepthPostProcessor(config.post_processing)
    
    raw_depth = model.predict(image)
    processed_depth = post_processor.process(raw_depth, image)
    
    print("Generating point cloud with default settings...")
    pc_config = PointCloudConfig()
    pc_config.fx = 525.0
    pc_config.fy = 525.0
    pc_config.depth_scale = 1000.0
    pc_config.downsample = True
    pc_config.downsample_voxel_size = 0.02
    pc_config.remove_outliers = True
    pc_config.save_path = "output/pointcloud.ply"
    pc_config.show = False
    
    os.makedirs("output", exist_ok=True)
    
    pc_generator = PointCloudGenerator(pc_config)
    pcd = pc_generator.generate(image, processed_depth)
    
    print(f"\n=== Point Cloud Stats ===")
    print(pc_generator.get_point_cloud_stats())
    
    print("\nEstimating normals...")
    pcd_with_normals = pc_generator.estimate_normals(pcd)
    
    print("Reconstructing mesh (Poisson)...")
    mesh = pc_generator.reconstruct_mesh(pcd_with_normals, depth=8)
    
    import open3d as o3d
    o3d.io.write_triangle_mesh("output/mesh.ply", mesh)
    print("Mesh saved to: output/mesh.ply")
    
    print("\nFiltering point cloud by distance...")
    filtered_pcd = pc_generator.filter_by_distance(pcd, min_dist=0.5, max_dist=5.0)
    pc_generator.save("output/pointcloud_filtered.ply", filtered_pcd)
    
    print("\n=== All operations completed ===")
    print("Output files:")
    print("  - output/pointcloud.ply (original)")
    print("  - output/pointcloud_filtered.ply (distance filtered)")
    print("  - output/mesh.ply (reconstructed mesh)")


if __name__ == "__main__":
    main()
