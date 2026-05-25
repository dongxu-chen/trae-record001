import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

from config.config import (
    TemporalSmoothingConfig,
    TemporalHoleFillingConfig,
    PostProcessingConfig,
)
from depth_estimation.temporal_filtering import (
    TemporalHoleFiller,
    TemporalSmoother,
    TemporalFilterPipeline,
)


def create_test_video_sequence(num_frames: int = 10, height: int = 240, width: int = 320):
    frames = []
    for i in range(num_frames):
        y, x = np.mgrid[0:height, 0:width].astype(np.float32)
        
        offset_x = 5 * np.sin(2 * np.pi * i / num_frames)
        offset_y = 3 * np.cos(2 * np.pi * i / num_frames)
        
        depth_map = 3.0 + 2.0 * np.sin((x + offset_x) / 50.0) * np.cos((y + offset_y) / 50.0)
        
        if i % 3 == 0:
            mask = np.zeros_like(depth_map, dtype=bool)
            mask[50:70, 100:130] = True
            mask[150:170, 200:230] = True
            depth_map[mask] = np.nan
        
        rgb_image = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        frames.append((rgb_image, depth_map))
    
    return frames


def test_temporal_hole_filling():
    print("Testing Temporal Hole Filling...")
    
    post_config = PostProcessingConfig()
    hole_config = TemporalHoleFillingConfig()
    hole_config.apply_temporal_hole_filling = True
    hole_config.num_frames = 3
    hole_config.min_valid_frames = 2
    hole_config.use_warping = False
    hole_config.fallback_to_spatial = True
    
    filler = TemporalHoleFiller(hole_config, post_config)
    
    frames = create_test_video_sequence(num_frames=10)
    
    results = []
    for i, (rgb, depth) in enumerate(frames):
        result = filler.process(depth, rgb)
        results.append(result)
        
        has_nan = np.any(np.isnan(result))
        print(f"  Frame {i}: has NaN = {has_nan}, shape = {result.shape}")
        
        if i >= 3:
            original_nan = np.sum(np.isnan(depth))
            result_nan = np.sum(np.isnan(result))
            if original_nan > 0:
                print(f"    Original NaN count: {original_nan}, Result NaN count: {result_nan}")
                assert result_nan < original_nan or result_nan == 0
    
    stats = filler.get_stats()
    print(f"  Stats: {stats}")
    
    assert stats["frame_count"] == 10
    assert stats["history_size"] <= 3
    
    print("✓ Temporal hole filling test passed")
    return True


def test_temporal_hole_filling_with_warping():
    print("\nTesting Temporal Hole Filling with Warping...")
    
    post_config = PostProcessingConfig()
    hole_config = TemporalHoleFillingConfig()
    hole_config.apply_temporal_hole_filling = True
    hole_config.num_frames = 3
    hole_config.min_valid_frames = 2
    hole_config.use_warping = True
    
    filler = TemporalHoleFiller(hole_config, post_config)
    
    frames = create_test_video_sequence(num_frames=8)
    
    for i, (rgb, depth) in enumerate(frames):
        result = filler.process(depth, rgb)
        
        has_nan = np.any(np.isnan(result))
        print(f"  Frame {i}: has NaN = {has_nan}")
    
    stats = filler.get_stats()
    print(f"  Stats: {stats}")
    assert stats["use_warping"] == True
    
    print("✓ Temporal hole filling with warping test passed")
    return True


def test_temporal_smoothing():
    print("\nTesting Temporal Smoothing...")
    
    smooth_config = TemporalSmoothingConfig()
    smooth_config.apply_temporal_smoothing = True
    smooth_config.alpha = 0.3
    smooth_config.edge_threshold = 0.1
    smooth_config.adaptive_alpha = False
    smooth_config.motion_compensation = False
    
    smoother = TemporalSmoother(smooth_config)
    
    h, w = 240, 320
    
    base_depth = 3.0 + 2.0 * np.sin(np.arange(w)[None, :] / 50.0) * np.cos(np.arange(h)[:, None] / 50.0)
    
    results = []
    for i in range(8):
        noise = np.random.normal(0, 0.2, base_depth.shape)
        current_depth = base_depth + noise
        
        rgb = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        result = smoother.process(current_depth, rgb)
        
        results.append(result)
        
        if i == 0:
            print(f"  Frame {i}: First frame, no smoothing applied")
        else:
            orig_var = np.var(current_depth - base_depth)
            smooth_var = np.var(result - base_depth)
            print(f"  Frame {i}: Original var = {orig_var:.4f}, Smoothed var = {smooth_var:.4f}")
            
            assert smooth_var <= orig_var * 1.5
    
    stats = smoother.get_stats()
    print(f"  Stats: {stats}")
    assert stats["frame_count"] == 8
    
    print("✓ Temporal smoothing test passed")
    return True


def test_temporal_smoothing_adaptive_alpha():
    print("\nTesting Temporal Smoothing with Adaptive Alpha...")
    
    smooth_config = TemporalSmoothingConfig()
    smooth_config.apply_temporal_smoothing = True
    smooth_config.alpha = 0.3
    smooth_config.edge_threshold = 0.1
    smooth_config.adaptive_alpha = True
    smooth_config.motion_compensation = False
    
    smoother = TemporalSmoother(smooth_config)
    
    h, w = 240, 320
    
    for i in range(6):
        if i < 3:
            depth = 3.0 + 2.0 * np.sin(np.arange(w)[None, :] / 50.0) * np.cos(np.arange(h)[:, None] / 50.0)
        else:
            depth = 5.0 + 1.0 * np.sin(np.arange(w)[None, :] / 30.0) * np.cos(np.arange(h)[:, None] / 30.0)
        
        rgb = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        result = smoother.process(depth, rgb)
        
        print(f"  Frame {i}: result range = [{result.min():.2f}, {result.max():.2f}]")
        assert result.shape == depth.shape
    
    print("✓ Adaptive alpha temporal smoothing test passed")
    return True


def test_edge_aware_smoothing():
    print("\nTesting Edge-Aware Temporal Smoothing...")
    
    smooth_config = TemporalSmoothingConfig()
    smooth_config.apply_temporal_smoothing = True
    smooth_config.alpha = 0.5
    smooth_config.edge_threshold = 0.2
    smooth_config.adaptive_alpha = False
    smooth_config.motion_compensation = False
    
    smoother = TemporalSmoother(smooth_config)
    
    h, w = 240, 320
    
    depth1 = np.ones((h, w), dtype=np.float32) * 2.0
    depth1[:, :w//2] = 5.0
    
    depth2 = np.ones((h, w), dtype=np.float32) * 2.1
    depth2[:, :w//2] = 4.9
    
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:, w//2-2:w//2+2, :] = 255
    
    result1 = smoother.process(depth1, rgb)
    result2 = smoother.process(depth2, rgb)
    
    edge_region = result2[:, w//2-10:w//2+10]
    smooth_region = result2[:, :w//4]
    
    edge_variation = np.var(edge_region)
    smooth_variation = np.var(smooth_region)
    
    print(f"  Edge region variance: {edge_variation:.6f}")
    print(f"  Smooth region variance: {smooth_variation:.6f}")
    
    assert edge_variation > smooth_variation * 0.1
    
    print("✓ Edge-aware smoothing test passed")
    return True


def test_temporal_filter_pipeline():
    print("\nTesting Temporal Filter Pipeline...")
    
    post_config = PostProcessingConfig()
    smooth_config = TemporalSmoothingConfig()
    hole_config = TemporalHoleFillingConfig()
    
    pipeline = TemporalFilterPipeline(smooth_config, hole_config, post_config)
    
    frames = create_test_video_sequence(num_frames=8)
    
    for i, (rgb, depth) in enumerate(frames):
        result = pipeline.process(depth, rgb)
        
        has_nan = np.any(np.isnan(result))
        print(f"  Frame {i}: shape = {result.shape}, has NaN = {has_nan}")
        
        assert result.shape == depth.shape
    
    stats = pipeline.get_stats()
    print(f"  Pipeline stats: {stats}")
    assert "smoothing" in stats
    assert "hole_filling" in stats
    
    pipeline.reset()
    stats_after_reset = pipeline.get_stats()
    assert stats_after_reset["smoothing"]["frame_count"] == 0
    assert stats_after_reset["hole_filling"]["frame_count"] == 0
    
    print("✓ Temporal filter pipeline test passed")
    return True


def test_motion_compensation():
    print("\nTesting Motion Compensation...")
    
    smooth_config = TemporalSmoothingConfig()
    smooth_config.apply_temporal_smoothing = True
    smooth_config.motion_compensation = True
    smooth_config.motion_threshold = 20.0
    
    smoother = TemporalSmoother(smooth_config)
    
    h, w = 120, 160
    
    for i in range(5):
        shift = i * 2
        depth = np.zeros((h, w), dtype=np.float32)
        depth[:, shift:shift+50] = np.linspace(1, 5, 50)[None, :]
        
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[:, shift:shift+50, 0] = 255
        
        result = smoother.process(depth, rgb)
        
        print(f"  Frame {i}: shift = {shift}, result range = [{result.min():.2f}, {result.max():.2f}]")
        
        assert not np.any(np.isnan(result))
    
    print("✓ Motion compensation test passed")
    return True


def main():
    print("=" * 60)
    print("Running Temporal Filtering Tests")
    print("=" * 60)
    
    tests = [
        test_temporal_hole_filling,
        test_temporal_hole_filling_with_warping,
        test_temporal_smoothing,
        test_temporal_smoothing_adaptive_alpha,
        test_edge_aware_smoothing,
        test_temporal_filter_pipeline,
        test_motion_compensation,
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
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{len(tests)} passed")
    print("=" * 60)
    
    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
