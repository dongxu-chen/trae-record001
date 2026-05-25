import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    print("Testing imports...")
    
    try:
        from config.config import Config, ModelConfig, PostProcessingConfig
        print("✓ Config module imported successfully")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from depth_estimation import MidasModel
        print("✓ MidasModel imported successfully")
    except Exception as e:
        print(f"✗ MidasModel import failed: {e}")
        return False
    
    try:
        from depth_estimation import DepthPostProcessor
        print("✓ DepthPostProcessor imported successfully")
    except Exception as e:
        print(f"✗ DepthPostProcessor import failed: {e}")
        return False
    
    try:
        from depth_estimation import VideoDepthEstimator
        print("✓ VideoDepthEstimator imported successfully")
    except Exception as e:
        print(f"✗ VideoDepthEstimator import failed: {e}")
        return False
    
    try:
        from depth_estimation import PointCloudGenerator
        print("✓ PointCloudGenerator imported successfully")
    except Exception as e:
        print(f"✗ PointCloudGenerator import failed: {e}")
        return False
    
    try:
        import numpy as np
        import cv2
        print("✓ OpenCV and NumPy imported successfully")
    except Exception as e:
        print(f"✗ OpenCV/NumPy import failed: {e}")
        return False
    
    try:
        import torch
        print(f"✓ PyTorch imported successfully (version: {torch.__version__})")
    except Exception as e:
        print(f"✗ PyTorch import failed: {e}")
        return False
    
    try:
        import open3d as o3d
        print(f"✓ Open3D imported successfully (version: {o3d.__version__})")
    except Exception as e:
        print(f"⚠️  Open3D not available: {e}")
        print("   Point cloud functions will use NumPy fallback.")
    
    try:
        import onnxruntime as ort
        print(f"✓ ONNX Runtime imported successfully (version: {ort.__version__})")
    except Exception as e:
        print(f"⚠️  ONNX Runtime not available: {e}")
        print("   ONNX inference mode will not be available.")
    
    print("\nCore imports successful! (Optional features may be limited)")
    return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
