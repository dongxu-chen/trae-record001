import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from config.config import (
    Config,
    PostProcessingConfig,
    TemporalSmoothingConfig,
    TemporalHoleFillingConfig,
)
from depth_estimation.temporal_filtering import (
    TemporalHoleFiller,
    TemporalSmoother,
    TemporalFilterPipeline,
)


def create_synthetic_video(num_frames: int = 20):
    """创建带空洞和噪声的合成视频序列"""
    frames = []
    h, w = 240, 320
    
    for i in range(num_frames):
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        
        t = i * 0.1
        offset_x = 20 * np.sin(t)
        offset_y = 10 * np.cos(t)
        
        depth_map = 2.0 + 3.0 * np.sin((x + offset_x) / 40.0) * np.cos((y + offset_y) / 40.0)
        depth_map += 0.15 * np.random.randn(h, w).astype(np.float32)
        
        if i % 4 == 0:
            mask = np.zeros_like(depth_map, dtype=bool)
            mask[30:60, 40:80] = True
            mask[100:130, 150:190] = True
            mask[180:210, 230:270] = True
            depth_map[mask] = np.nan
        
        rgb_base = np.zeros((h, w, 3), dtype=np.uint8)
        rgb_base[..., 0] = (np.sin(x / 30.0) * 50 + 100).astype(np.uint8)
        rgb_base[..., 1] = (np.cos(y / 40.0) * 50 + 100).astype(np.uint8)
        rgb_base[..., 2] = (np.sin(x / 50.0 + y / 50.0) * 50 + 100).astype(np.uint8)
        
        frames.append((rgb_base, depth_map))
    
    return frames


def demo_hole_filling():
    """演示跨帧空洞填充"""
    print("=" * 60)
    print("Demo 1: Temporal Hole Filling")
    print("=" * 60)
    
    post_config = PostProcessingConfig()
    
    hole_config = TemporalHoleFillingConfig()
    hole_config.apply_temporal_hole_filling = True
    hole_config.num_frames = 5
    hole_config.min_valid_frames = 2
    hole_config.use_warping = True
    hole_config.fallback_to_spatial = True
    
    filler = TemporalHoleFiller(hole_config, post_config)
    
    frames = create_synthetic_video(num_frames=15)
    
    print("\nProcessing frames with temporal hole filling...")
    for i, (rgb, depth) in enumerate(frames):
        result = filler.process(depth, rgb)
        
        original_nan = np.sum(np.isnan(depth))
        result_nan = np.sum(np.isnan(result))
        
        print(f"  Frame {i:2d}: NaN count {original_nan:4d} -> {result_nan:4d}", end="")
        if original_nan > 0 and result_nan == 0:
            print("  ✓ All holes filled!")
        elif result_nan < original_nan:
            print(f"  ✓ {100*(1-result_nan/original_nan):.0f}% filled")
        else:
            print()
    
    print(f"\nStats: {filler.get_stats()}")
    print("✓ Temporal hole filling demo complete!\n")


def demo_temporal_smoothing():
    """演示帧间指数平滑滤波"""
    print("=" * 60)
    print("Demo 2: Temporal Exponential Smoothing")
    print("=" * 60)
    
    smooth_config = TemporalSmoothingConfig()
    smooth_config.apply_temporal_smoothing = True
    smooth_config.alpha = 0.3
    smooth_config.edge_threshold = 0.15
    smooth_config.adaptive_alpha = True
    smooth_config.motion_compensation = True
    smooth_config.motion_threshold = 5.0
    
    smoother = TemporalSmoother(smooth_config)
    
    h, w = 240, 320
    base_depth = 3.0 + 2.0 * np.sin(np.arange(w)[None, :] / 50.0) * np.cos(np.arange(h)[:, None] / 50.0)
    
    print("\nProcessing frames with temporal smoothing...")
    for i in range(12):
        if i < 6:
            depth = base_depth + np.random.normal(0, 0.2, base_depth.shape)
        else:
            depth = 1.5 + base_depth * 0.8 + np.random.normal(0, 0.2, base_depth.shape)
        
        rgb = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        result = smoother.process(depth, rgb)
        
        noise_before = np.std(depth - base_depth if i < 6 else depth - (1.5 + base_depth * 0.8))
        noise_after = np.std(result - base_depth if i < 6 else result - (1.5 + base_depth * 0.8))
        
        stats = smoother.get_stats()
        
        print(f"  Frame {i:2d}: noise σ {noise_before:.4f} -> {noise_after:.4f} "
              f"(α ≈ {smooth_config.alpha if not smooth_config.adaptive_alpha else 'adaptive'})")
    
    print(f"\nStats: {smoother.get_stats()}")
    print("✓ Temporal smoothing demo complete!\n")


def demo_full_pipeline():
    """演示完整的时间滤波管线"""
    print("=" * 60)
    print("Demo 3: Full Temporal Filter Pipeline")
    print("=" * 60)
    
    post_config = PostProcessingConfig()
    post_config.apply_edge_guided_filter = True
    
    smooth_config = TemporalSmoothingConfig()
    smooth_config.apply_temporal_smoothing = True
    smooth_config.alpha = 0.35
    smooth_config.edge_threshold = 0.2
    smooth_config.adaptive_alpha = True
    smooth_config.motion_compensation = True
    
    hole_config = TemporalHoleFillingConfig()
    hole_config.apply_temporal_hole_filling = True
    hole_config.num_frames = 4
    hole_config.min_valid_frames = 2
    hole_config.use_warping = True
    hole_config.fallback_to_spatial = True
    
    pipeline = TemporalFilterPipeline(smooth_config, hole_config, post_config)
    
    frames = create_synthetic_video(num_frames=12)
    
    print("\nProcessing frames with full pipeline...")
    for i, (rgb, depth) in enumerate(frames):
        result = pipeline.process(depth, rgb)
        
        has_nan = np.any(np.isnan(result))
        noise_level = np.nanstd(result)
        
        print(f"  Frame {i:2d}: has NaN = {str(has_nan):5s}, depth std = {noise_level:.4f}")
        
        output_dir = "output_temporal"
        os.makedirs(output_dir, exist_ok=True)
        
        depth_colored = cv2.applyColorMap(
            cv2.normalize(result, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U),
            cv2.COLORMAP_MAGMA
        )
        cv2.imwrite(f"{output_dir}/frame_{i:03d}_depth.png", depth_colored)
        cv2.imwrite(f"{output_dir}/frame_{i:03d}_rgb.png", rgb)
    
    print(f"\nPipeline stats: {pipeline.get_stats()}")
    print(f"\nOutput saved to {output_dir}/ directory")
    print("✓ Full pipeline demo complete!\n")


def demo_edge_guided_filter():
    """演示边缘引导滤波"""
    print("=" * 60)
    print("Demo 4: Edge-Guided Filter (Spatial)")
    print("=" * 60)
    
    from depth_estimation import DepthPostProcessor
    
    h, w = 300, 400
    depth = np.ones((h, w), dtype=np.float32) * 2.0
    depth[:, :w//2] = 5.0
    depth += np.random.normal(0, 0.1, depth.shape)
    
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:, :w//2] = 180
    rgb[:, w//2:] = 60
    rgb = rgb + np.random.randint(-5, 5, rgb.shape).astype(np.uint8)
    
    config = PostProcessingConfig()
    config.apply_edge_guided_filter = True
    config.apply_bilateral_filter = False
    config.apply_median_filter = False
    config.apply_gaussian_filter = False
    config.fill_holes = False
    config.normalize = False
    config.edge_guided_r = 9
    config.edge_guided_eps = 0.02
    config.edge_guided_edge_weight = 0.8
    
    processor = DepthPostProcessor(config)
    filtered = processor.process(depth, rgb)
    
    edge_before = depth[:, w//2-5:w//2+5]
    flat_before = depth[:, :w//4]
    edge_after = filtered[:, w//2-5:w//2+5]
    flat_after = filtered[:, :w//4]
    
    print(f"\nDepth variance analysis:")
    print(f"  Flat region: {np.var(flat_before):.4f} -> {np.var(flat_after):.4f} "
          f"({(1-np.var(flat_after)/np.var(flat_before))*100:.1f}% noise reduction)")
    print(f"  Edge region: {np.var(edge_before):.4f} -> {np.var(edge_after):.4f} "
          f"(preserved for sharpness)")
    
    print(f"\nPipeline info: {processor.get_pipeline_info()}")
    print("✓ Edge-guided filter demo complete!\n")


def main():
    print("\n" + "#" * 60)
    print("#" + " " * 12 + "TEMPORAL FILTERING DEMO" + " " * 19 + "#")
    print("#" * 60 + "\n")
    
    try:
        demo_edge_guided_filter()
        demo_hole_filling()
        demo_temporal_smoothing()
        demo_full_pipeline()
        
        print("=" * 60)
        print("🎉 All demos completed successfully!")
        print("=" * 60)
        print("\nKey features demonstrated:")
        print("  • Edge-Guided Filter: preserves depth discontinuities while smoothing")
        print("  • Temporal Hole Filling: uses previous frames + warping to fill holes")
        print("  • Temporal Smoothing: adaptive exponential smoothing with edge protection")
        print("  • Motion Compensation: uses optical flow for better frame alignment")
        print("\nConfiguration options available in config.config:")
        print("  - PostProcessingConfig.apply_edge_guided_filter")
        print("  - TemporalSmoothingConfig (alpha, edge_threshold, adaptive_alpha, etc.)")
        print("  - TemporalHoleFillingConfig (num_frames, use_warping, etc.)")
        print("\nThese are automatically integrated into VideoDepthEstimator")
        print("for real-time video depth estimation.")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
