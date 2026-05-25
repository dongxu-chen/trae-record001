import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2

from config.config import PostProcessingConfig
from depth_estimation import DepthPostProcessor


def create_test_depth_map():
    h, w = 240, 320
    y, x = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    
    depth_map = 5.0 + 3.0 * np.sin(x / 50.0) * np.cos(y / 50.0)
    
    mask = np.zeros_like(depth_map, dtype=bool)
    mask[100:120, 150:170] = True
    mask[50:60, 200:220] = True
    depth_map[mask] = np.nan
    
    noise = np.random.normal(0, 0.1, depth_map.shape)
    depth_map += noise
    
    return depth_map


def test_normalization():
    print("Testing normalization...")
    
    config = PostProcessingConfig()
    config.normalize = True
    config.min_depth = 0.1
    config.max_depth = 10.0
    config.apply_bilateral_filter = False
    config.apply_median_filter = False
    config.apply_gaussian_filter = False
    config.fill_holes = False
    
    processor = DepthPostProcessor(config)
    depth_map = create_test_depth_map()
    
    processed = processor.process(depth_map)
    
    valid_mask = ~np.isnan(depth_map)
    assert np.min(processed[valid_mask]) >= config.min_depth
    assert np.max(processed[valid_mask]) <= config.max_depth
    
    print("✓ Normalization test passed")
    return True


def test_filters():
    print("\nTesting filters...")
    
    depth_map = create_test_depth_map()
    rgb_image = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    config = PostProcessingConfig()
    config.normalize = True
    config.apply_bilateral_filter = True
    config.apply_median_filter = True
    config.apply_gaussian_filter = True
    config.fill_holes = False
    
    processor = DepthPostProcessor(config)
    processed = processor.process(depth_map, rgb_image)
    
    assert processed.shape == depth_map.shape
    print("✓ Filters test passed")
    return True


def test_hole_filling():
    print("\nTesting hole filling...")
    
    config = PostProcessingConfig()
    config.normalize = True
    config.apply_bilateral_filter = False
    config.apply_median_filter = False
    config.apply_gaussian_filter = False
    config.fill_holes = True
    config.hole_fill_kernel = 5
    
    processor = DepthPostProcessor(config)
    depth_map = create_test_depth_map()
    
    processed = processor.process(depth_map)
    
    assert not np.any(np.isnan(processed))
    assert not np.any(np.isinf(processed))
    assert np.all(processed > 0)
    
    print("✓ Hole filling test passed")
    return True


def test_colormap():
    print("\nTesting colormap...")
    
    depth_map = create_test_depth_map()
    depth_map[np.isnan(depth_map)] = 5.0
    
    colored = DepthPostProcessor.apply_colormap(depth_map)
    
    assert colored.shape == (240, 320, 3)
    assert colored.dtype == np.uint8
    
    print("✓ Colormap test passed")
    return True


def test_edge_aware_smoothing():
    print("\nTesting edge-aware smoothing...")
    
    depth_map = create_test_depth_map()
    depth_map[np.isnan(depth_map)] = 5.0
    rgb_image = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    smoothed = DepthPostProcessor.smooth_with_edges(depth_map, rgb_image)
    
    assert smoothed.shape == depth_map.shape
    print("✓ Edge-aware smoothing test passed")
    return True


def test_full_pipeline():
    print("\nTesting full post-processing pipeline...")
    
    config = PostProcessingConfig()
    processor = DepthPostProcessor(config)
    
    depth_map = create_test_depth_map()
    rgb_image = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    processed = processor.process(depth_map, rgb_image)
    
    assert processed.shape == depth_map.shape
    assert not np.any(np.isnan(processed))
    assert not np.any(np.isinf(processed))
    
    print("✓ Full pipeline test passed")
    return True


def test_edge_guided_filter():
    print("\nTesting edge-guided filter...")
    
    h, w = 240, 320
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    
    depth_map = np.ones((h, w), dtype=np.float32) * 3.0
    depth_map[:, :w//2] = 6.0
    
    noise = np.random.normal(0, 0.1, depth_map.shape)
    depth_map += noise
    
    rgb_image = np.zeros((h, w, 3), dtype=np.uint8)
    rgb_image[:, :w//2] = 200
    rgb_image[:, w//2:] = 50
    rgb_image = rgb_image + np.random.randint(-10, 10, rgb_image.shape).astype(np.uint8)
    
    config = PostProcessingConfig()
    config.apply_edge_guided_filter = True
    config.edge_guided_r = 7
    config.edge_guided_eps = 0.01
    config.edge_guided_edge_weight = 0.7
    config.apply_bilateral_filter = False
    config.apply_median_filter = False
    config.apply_gaussian_filter = False
    config.fill_holes = False
    config.normalize = False
    
    processor = DepthPostProcessor(config)
    processed = processor.process(depth_map, rgb_image)
    
    edge_region_before = depth_map[:, w//2-10:w//2+10]
    flat_region_before = depth_map[:, :w//4]
    
    edge_region_after = processed[:, w//2-10:w//2+10]
    flat_region_after = processed[:, :w//4]
    
    edge_var_before = np.var(edge_region_before)
    edge_var_after = np.var(edge_region_after)
    flat_var_before = np.var(flat_region_before)
    flat_var_after = np.var(flat_region_after)
    
    print(f"  Flat region - variance before: {flat_var_before:.6f}, after: {flat_var_after:.6f}")
    print(f"  Edge region - variance before: {edge_var_before:.6f}, after: {edge_var_after:.6f}")
    print(f"  Flat noise reduction: {(1 - flat_var_after/flat_var_before)*100:.1f}%")
    
    assert flat_var_after < flat_var_before * 0.5, "Flat region should be smoothed"
    assert edge_var_after > flat_var_after * 0.5, "Edge region should retain variation"
    
    print("✓ Edge-guided filter test passed")
    return True


def main():
    print("=" * 50)
    print("Running Post-Processing Tests")
    print("=" * 50)
    
    tests = [
        test_normalization,
        test_filters,
        test_hole_filling,
        test_colormap,
        test_edge_aware_smoothing,
        test_edge_guided_filter,
        test_full_pipeline,
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
