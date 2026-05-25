import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from config.config import Config, ModelConfig
from depth_estimation import MidasModel, DepthPostProcessor


def main():
    pytorch_config = ModelConfig()
    pytorch_config.model_type = "MiDaS_small"
    pytorch_config.device = "cuda"
    pytorch_config.use_onnx = False
    
    print("Loading PyTorch model...")
    pytorch_model = MidasModel(pytorch_config)
    
    onnx_path = "midas_small.onnx"
    print(f"\nExporting to ONNX: {onnx_path}")
    pytorch_model.export_to_onnx(onnx_path)
    
    del pytorch_model
    
    print("\nLoading ONNX model...")
    onnx_config = ModelConfig()
    onnx_config.use_onnx = True
    onnx_config.onnx_path = onnx_path
    onnx_config.device = "cuda"
    
    onnx_model = MidasModel(onnx_config)
    
    print("\nCreating test image...")
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    print("Running ONNX inference...")
    depth_map = onnx_model.predict(test_image)
    
    print(f"Depth map shape: {depth_map.shape}")
    print(f"Depth range: [{depth_map.min():.3f}, {depth_map.max():.3f}]")
    
    post_processor = DepthPostProcessor(Config().post_processing)
    processed_depth = post_processor.process(depth_map, test_image)
    
    depth_colored = DepthPostProcessor.apply_colormap(processed_depth)
    cv2.imwrite("onnx_depth_output.png", depth_colored)
    
    print("\n=== Model Info ===")
    print(onnx_model.get_model_info())
    
    print("\nDone! ONNX inference test passed.")


if __name__ == "__main__":
    main()
