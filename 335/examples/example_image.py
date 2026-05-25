import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from config.config import Config, ModelConfig, PostProcessingConfig, PointCloudConfig
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
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    
    print("Initializing model...")
    model = MidasModel(config.model)
    
    print("Predicting depth...")
    raw_depth = model.predict(image)
    print(f"Raw depth shape: {raw_depth.shape}, range: [{raw_depth.min():.3f}, {raw_depth.max():.3f}]")
    
    print("Post-processing...")
    post_processor = DepthPostProcessor(config.post_processing)
    processed_depth = post_processor.process(raw_depth, image)
    print(f"Processed depth shape: {processed_depth.shape}, range: [{processed_depth.min():.3f}, {processed_depth.max():.3f}]")
    
    print("Applying colormap...")
    depth_colored = DepthPostProcessor.apply_colormap(processed_depth)
    
    output_path = "depth_output.png"
    cv2.imwrite(output_path, depth_colored)
    print(f"Depth map saved to: {output_path}")
    
    combined = np.hstack((image, depth_colored))
    combined_path = "combined_output.png"
    cv2.imwrite(combined_path, combined)
    print(f"Combined output saved to: {combined_path}")
    
    print("Generating point cloud...")
    pc_config = PointCloudConfig()
    pc_config.save_path = "pointcloud.ply"
    pc_config.show = False
    
    pc_generator = PointCloudGenerator(pc_config)
    pcd = pc_generator.generate(image, processed_depth)
    
    stats = pc_generator.get_point_cloud_stats()
    print(f"Point cloud stats: {stats}")
    
    print("Saving raw depth data...")
    np.save("depth_raw.npy", processed_depth)
    
    print("\n=== Model Info ===")
    print(model.get_model_info())
    
    print("\n=== Post-Processing Pipeline ===")
    print(post_processor.get_pipeline_info())
    
    print("\nDone!")


if __name__ == "__main__":
    main()
