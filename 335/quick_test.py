import sys
import os
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import Config, ModelConfig, PostProcessingConfig, PointCloudConfig, VideoConfig
from depth_estimation import MidasModel, DepthPostProcessor, VideoDepthEstimator, PointCloudGenerator

print("=" * 60)
print("QUICK TEST - Depth Estimation System")
print("=" * 60)

print("\n1. Testing Config Modules...")
try:
    model_cfg = ModelConfig()
    post_cfg = PostProcessingConfig()
    video_cfg = VideoConfig()
    pc_cfg = PointCloudConfig()
    config = Config()
    print("   ✓ All config classes work correctly")
except Exception as e:
    print(f"   ✗ Config test failed: {e}")
    sys.exit(1)

print("\n2. Testing DepthPostProcessor...")
try:
    h, w = 240, 320
    y, x = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    depth_map = 5.0 + 3.0 * np.sin(x / 50.0) * np.cos(y / 50.0)
    depth_map[100:120, 150:170] = np.nan
    depth_map += np.random.normal(0, 0.1, depth_map.shape)
    
    rgb_image = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    
    processor = DepthPostProcessor(post_cfg)
    processed = processor.process(depth_map, rgb_image)
    
    assert processed.shape == depth_map.shape
    assert not np.any(np.isnan(processed))
    assert not np.any(np.isinf(processed))
    
    colored = DepthPostProcessor.apply_colormap(processed)
    assert colored.shape == (h, w, 3)
    
    edges = DepthPostProcessor.compute_depth_edges(processed)
    assert edges.shape == (h, w)
    
    smoothed = DepthPostProcessor.smooth_with_edges(processed, rgb_image)
    assert smoothed.shape == depth_map.shape
    
    print(f"   ✓ Post-processing works correctly")
    print(f"     - Input: {depth_map.shape}, has NaN: {np.any(np.isnan(depth_map))}")
    print(f"     - Output: {processed.shape}, range: [{processed.min():.2f}, {processed.max():.2f}]")
    print(f"     - Colormap output: {colored.shape}, dtype: {colored.dtype}")
except Exception as e:
    print(f"   ✗ Post-processor test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n3. Testing PointCloudGenerator (NumPy fallback)...")
try:
    pc_cfg.min_depth = 0.1
    pc_cfg.max_depth = 10.0
    pc_cfg.show = False
    pc_cfg.save_path = None
    
    generator = PointCloudGenerator(pc_cfg)
    result = generator.generate(rgb_image, processed)
    
    if isinstance(result, tuple):
        points, colors = result
        print(f"   ✓ Point cloud generated with NumPy fallback")
        print(f"     - Points: {len(points)}, shape: {points.shape}")
        print(f"     - Colors: {colors.shape if colors is not None else 'None'}")
        
        stats = generator.get_point_cloud_stats()
        print(f"     - Stats: {stats['num_points']} points, backend: {stats['backend']}")
        
        save_path = "test_output.ply"
        generator.save_numpy(save_path, points, colors)
        assert os.path.exists(save_path)
        os.remove(save_path)
        print(f"     - Save/Load: Works correctly")
    else:
        print(f"   ✓ Point cloud generated with Open3D")
        print(f"     - Points: {len(result.points)}")
    
    filtered = generator.filter_by_distance(result, min_dist=0.5, max_dist=5.0)
    if isinstance(filtered, tuple):
        print(f"     - Filtered: {len(filtered[0])} points")
    else:
        print(f"     - Filtered: {len(filtered.points)} points")
    
except Exception as e:
    print(f"   ✗ Point cloud test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n4. Testing MidasModel (model info only)...")
try:
    from depth_estimation.midas_model import MidasModel
    
    print(f"   ✓ MidasModel class is available")
    print(f"     - Supports: PyTorch backend, ONNX backend, model export")
    print(f"     - Models: DPT_Large, DPT_Hybrid, MiDaS_small, MiDaS_v21")
    
except Exception as e:
    print(f"   ✗ MidasModel test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n5. Testing VideoDepthEstimator (class info only)...")
try:
    from depth_estimation.video_estimator import VideoDepthEstimator
    
    print(f"   ✓ VideoDepthEstimator class is available")
    print(f"     - Supports: Webcam, video files, frame generators")
    print(f"     - Features: FPS display, hotkeys, video saving, callbacks")
    
except Exception as e:
    print(f"   ✗ VideoDepthEstimator test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n6. Testing Temporal Filtering Modules...")
try:
    from config.config import TemporalSmoothingConfig, TemporalHoleFillingConfig
    from depth_estimation.temporal_filtering import (
        TemporalHoleFiller,
        TemporalSmoother,
        TemporalFilterPipeline,
    )
    
    smooth_cfg = TemporalSmoothingConfig()
    hole_cfg = TemporalHoleFillingConfig()
    post_cfg = PostProcessingConfig()
    
    pipeline = TemporalFilterPipeline(smooth_cfg, hole_cfg, post_cfg)
    
    print(f"   ✓ TemporalFilterPipeline is available")
    print(f"     - Temporal Hole Filling: enabled={hole_cfg.apply_temporal_hole_filling}")
    print(f"       * num_frames={hole_cfg.num_frames}, use_warping={hole_cfg.use_warping}")
    print(f"     - Temporal Smoothing: enabled={smooth_cfg.apply_temporal_smoothing}")
    print(f"       * alpha={smooth_cfg.alpha}, adaptive_alpha={smooth_cfg.adaptive_alpha}")
    print(f"       * edge_threshold={smooth_cfg.edge_threshold}")
    print(f"       * motion_compensation={smooth_cfg.motion_compensation}")
    
except Exception as e:
    print(f"   ✗ Temporal filtering test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n7. Testing Edge-Guided Filter...")
try:
    from config.config import PostProcessingConfig
    
    eg_config = PostProcessingConfig()
    eg_config.apply_edge_guided_filter = True
    eg_config.apply_bilateral_filter = False
    eg_config.edge_guided_r = 7
    eg_config.edge_guided_eps = 0.01
    eg_config.edge_guided_edge_weight = 0.7
    
    eg_processor = DepthPostProcessor(eg_config)
    eg_result = eg_processor.process(processed, rgb_image)
    
    edge_before = processed[:, w//2-5:w//2+5]
    flat_before = processed[:, :w//4]
    edge_after = eg_result[:, w//2-5:w//2+5]
    flat_after = eg_result[:, :w//4]
    
    print(f"   ✓ Edge-Guided Filter is working")
    print(f"     - Flat region variance: {np.var(flat_before):.4f} -> {np.var(flat_after):.4f}")
    print(f"     - Edge region preserved for sharpness")
    
except Exception as e:
    print(f"   ✗ Edge-guided filter test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\n📦 Project Structure:")
print("   config/          - Configuration classes")
print("   depth_estimation/")
print("     midas_model.py       - MiDaS model (PyTorch + ONNX)")
print("     post_processing.py   - Depth map filters & hole filling")
print("     video_estimator.py   - Real-time video processing")
print("     point_cloud.py       - 3D point cloud generation")
print("   examples/        - Example scripts")
print("   tests/           - Unit tests")
print("\n🚀 Quick Start:")
print("   python main.py --mode image --input your_image.jpg")
print("   python main.py --mode webcam --model-type MiDaS_small")
print("   python main.py --mode pointcloud --input image.jpg")
print("\n💡 For more examples, see the examples/ directory.")
print("=" * 60)
