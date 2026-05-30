import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

from dark_channel_dehazer import DarkChannelDehazer
from utils import (load_image, save_image, visualize_results,
                   create_synthetic_hazy_image, batch_dehaze,
                   batch_dehaze_with_report, calculate_psnr, 
                   resize_image, estimate_batch_haze_density)

try:
    from aod_net import AODNetDehazer, create_demo_aod_model
    AOD_NET_AVAILABLE = True
except (ImportError, OSError, Exception):
    AOD_NET_AVAILABLE = False
    AODNetDehazer = None
    create_demo_aod_model = None


def example_1_adaptive_dehaze():
    print("=" * 60)
    print("Example 1: Adaptive Dehazing with Haze Density Estimation")
    print("=" * 60)
    dehazer = DarkChannelDehazer(
        adaptive_params=True,
        auto_brightness=True,
        sky_detection=True
    )
    test_img = create_test_image()
    haze_levels = [0.3, 0.5, 0.7, 0.9]
    results = []
    os.makedirs('output', exist_ok=True)
    for haze_level in haze_levels:
        hazy_img = create_synthetic_hazy_image(test_img, haze_level=haze_level)
        dehazed_img, info = dehazer.dehaze_with_info(hazy_img)
        psnr = calculate_psnr(test_img, dehazed_img)
        results.append((haze_level, hazy_img, dehazed_img, info, psnr))
        save_image(f'output/adaptive_haze{haze_level:.1f}_hazy.jpg', hazy_img)
        save_image(f'output/adaptive_haze{haze_level:.1f}_dehazed.jpg', dehazed_img)
        print(f"\nHaze Level {haze_level}:")
        print(f"  Estimated Density: {info['haze_density']:.3f}")
        print(f"  Adaptive Params: omega={info['omega']:.3f}, "
              f"t_min={info['t_min']:.3f}, strength={info['strength']:.3f}")
        print(f"  PSNR: {psnr:.2f} dB")
    return results


def example_2_sky_enhanced_processing():
    print("\n" + "=" * 60)
    print("Example 2: Enhanced Sky Region Processing")
    print("=" * 60)
    test_img = create_test_image_with_sky()
    hazy_img = create_synthetic_hazy_image(test_img, haze_level=0.6)
    dehazer_no_sky = DarkChannelDehazer(
        sky_detection=False,
        adaptive_params=True,
        auto_brightness=False
    )
    dehazer_basic_sky = DarkChannelDehazer(
        sky_detection=True,
        adaptive_params=True,
        auto_brightness=False
    )
    dehazer_enhanced = DarkChannelDehazer(
        sky_detection=True,
        adaptive_params=True,
        auto_brightness=True
    )
    dehazed_no_sky, _ = dehazer_no_sky.dehaze_with_info(hazy_img)
    dehazed_basic_sky, _ = dehazer_basic_sky.dehaze_with_info(hazy_img)
    dehazed_enhanced, info = dehazer_enhanced.dehaze_with_info(hazy_img)
    sky_mask = dehazer_enhanced.get_sky_mask(hazy_img)
    os.makedirs('output', exist_ok=True)
    save_image('output/sky_hazy.jpg', hazy_img)
    save_image('output/sky_mask.jpg', sky_mask)
    save_image('output/sky_no_detection.jpg', dehazed_no_sky)
    save_image('output/sky_basic.jpg', dehazed_basic_sky)
    save_image('output/sky_enhanced.jpg', dehazed_enhanced)
    psnr_no_sky = calculate_psnr(test_img, dehazed_no_sky)
    psnr_basic = calculate_psnr(test_img, dehazed_basic_sky)
    psnr_enhanced = calculate_psnr(test_img, dehazed_enhanced)
    print(f"\nSky Region Ratio: {info['sky_ratio']:.3f}")
    print(f"PSNR (no sky detection):    {psnr_no_sky:.2f} dB")
    print(f"PSNR (basic sky detection): {psnr_basic:.2f} dB")
    print(f"PSNR (enhanced sky):        {psnr_enhanced:.2f} dB")
    print("\nEnhanced sky processing includes:")
    print("  - Separate sky region processing pipeline")
    print("  - Natural brightness adjustment (0.9-1.25x)")
    print("  - Saturation preservation")
    print("  - Haze compensation for smooth transition")
    return hazy_img, sky_mask, dehazed_no_sky, dehazed_basic_sky, dehazed_enhanced


def example_3_haze_density_estimation():
    print("\n" + "=" * 60)
    print("Example 3: Haze Density Estimation")
    print("=" * 60)
    dehazer = DarkChannelDehazer()
    test_img = create_test_image()
    haze_levels = [0.2, 0.4, 0.6, 0.8]
    print("\nHaze Level vs Estimated Density:")
    print("-" * 40)
    for haze_level in haze_levels:
        hazy_img = create_synthetic_hazy_image(test_img, haze_level=haze_level)
        estimated_density = dehazer.estimate_haze_density(hazy_img)
        omega, t_min, strength = dehazer._adaptive_parameters(estimated_density)
        print(f"  {haze_level:.1f} -> {estimated_density:.3f} | "
              f"params: ω={omega:.2f}, t_min={t_min:.2f}, S={strength:.2f}")
    print("\nAdaptive Parameter Rules:")
    print("  - Light haze (<0.3):    mild dehazing, higher t_min")
    print("  - Medium haze (0.3-0.6): standard dehazing")
    print("  - Heavy haze (>0.6):    strong dehazing, lower t_min")
    return haze_levels


def example_4_batch_with_pre_estimation():
    print("\n" + "=" * 60)
    print("Example 4: Batch Processing with Haze Pre-Estimation")
    print("=" * 60)
    input_dir = 'test_images'
    output_dir = 'output/batch_adaptive'
    report_path = 'output/batch_report.json'
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    haze_levels = [0.3, 0.5, 0.7, 0.6, 0.4, 0.8]
    for i, haze_level in enumerate(haze_levels):
        test_img = create_test_image(seed=i)
        hazy_img = create_synthetic_hazy_image(test_img, haze_level=haze_level)
        save_image(os.path.join(input_dir, f'image_{i}_haze{haze_level:.1f}.jpg'), hazy_img)
    print(f"\nCreated {len(haze_levels)} test images with varying haze levels")
    dehazer = DarkChannelDehazer(
        adaptive_params=True,
        auto_brightness=True,
        sky_detection=True
    )
    print("\nStep 1: Pre-estimate haze densities...")
    haze_densities = estimate_batch_haze_density(dehazer, input_dir)
    print("\nStep 2: Process images with adaptive parameters...")
    report = batch_dehaze_with_report(dehazer, input_dir, output_dir)
    import json
    def convert_to_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        return obj
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=convert_to_serializable)
    print(f"\nReport saved to {report_path}")
    print(f"\nSummary:")
    print(f"  Total images: {report['total_images']}")
    print(f"  Processed: {report['processed_count']}")
    for img_info in report['images']:
        filename = os.path.basename(img_info['input_path'])
        print(f"  {filename}: haze={img_info['haze_density']:.2f}, "
              f"str={img_info['strength']:.2f}, sky={img_info['sky_ratio']:.2f}")
    return report


def example_5_manual_vs_adaptive():
    print("\n" + "=" * 60)
    print("Example 5: Manual vs Adaptive Parameter Comparison")
    print("=" * 60)
    test_img = create_test_image()
    hazy_img = create_synthetic_hazy_image(test_img, haze_level=0.7)
    dehazer_manual = DarkChannelDehazer(
        adaptive_params=False,
        omega=0.95,
        t_min=0.1,
        dehaze_strength=1.0,
        sky_detection=False
    )
    dehazer_adaptive = DarkChannelDehazer(
        adaptive_params=True,
        auto_brightness=True,
        sky_detection=True
    )
    dehazed_manual = dehazer_manual.dehaze(hazy_img)
    dehazed_adaptive, info = dehazer_adaptive.dehaze_with_info(hazy_img)
    psnr_manual = calculate_psnr(test_img, dehazed_manual)
    psnr_adaptive = calculate_psnr(test_img, dehazed_adaptive)
    os.makedirs('output', exist_ok=True)
    save_image('output/compare_hazy.jpg', hazy_img)
    save_image('output/compare_manual.jpg', dehazed_manual)
    save_image('output/compare_adaptive.jpg', dehazed_adaptive)
    print(f"\nManual Parameters (fixed):")
    print(f"  omega=0.95, t_min=0.1, strength=1.0")
    print(f"  PSNR: {psnr_manual:.2f} dB")
    print(f"\nAdaptive Parameters:")
    print(f"  haze_density={info['haze_density']:.3f}")
    print(f"  omega={info['omega']:.3f}, t_min={info['t_min']:.3f}, "
          f"strength={info['strength']:.3f}")
    print(f"  sky_ratio={info['sky_ratio']:.3f}")
    print(f"  PSNR: {psnr_adaptive:.2f} dB")
    improvement = psnr_adaptive - psnr_manual
    print(f"\nPSNR Improvement: {improvement:+.2f} dB")
    return hazy_img, dehazed_manual, dehazed_adaptive, info


def example_6_dehaze_enhance_linkage():
    print("\n" + "=" * 60)
    print("Example 6: Dehaze + Enhancement Linkage")
    print("=" * 60)
    test_img = create_test_image()
    hazy_img = create_synthetic_hazy_image(test_img, haze_level=0.6)
    dehazer_basic = DarkChannelDehazer(
        adaptive_params=True,
        enhance_enabled=False
    )
    dehazer_enhanced = DarkChannelDehazer(
        adaptive_params=True,
        enhance_enabled=True,
        enhance_strength=0.5
    )
    dehazed_basic = dehazer_basic.dehaze(hazy_img)
    final_enhanced, dehazed_only, info = dehazer_enhanced.dehaze_with_info_and_enhance(hazy_img)
    os.makedirs('output', exist_ok=True)
    save_image('output/enhance_hazy.jpg', hazy_img)
    save_image('output/enhance_dehaze_only.jpg', dehazed_basic)
    save_image('output/enhance_dehaze_enhanced.jpg', final_enhanced)
    from utils import evaluate_dehazing, print_evaluation_report
    metrics_basic = evaluate_dehazing(hazy_img, dehazed_basic, test_img)
    metrics_enhanced = evaluate_dehazing(hazy_img, final_enhanced, test_img)
    print("\nBasic Dehazing vs Enhanced Dehazing:")
    print(f"  {'Metric':<25} {'Basic':>10} {'Enhanced':>10} {'Improvement':>12}")
    print(f"  {'-'*60}")
    for key in ['psnr', 'edge_improvement_ratio', 'contrast_improvement_ratio', 'overall_quality_score']:
        if key in metrics_basic and key in metrics_enhanced:
            basic = metrics_basic[key]
            enhanced = metrics_enhanced[key]
            improvement = enhanced - basic
            print(f"  {key:<25} {basic:>10.2f} {enhanced:>10.2f} {improvement:>+12.2f}")
    print("\nEnhancement includes:")
    print("  - Adaptive CLAHE based on haze density")
    print("  - LAB color space for luminance enhancement")
    print("  - Preserves color information")
    return hazy_img, dehazed_basic, final_enhanced


def example_7_quality_evaluation():
    print("\n" + "=" * 60)
    print("Example 7: Dehazing Quality Evaluation")
    print("=" * 60)
    from utils import evaluate_dehazing, print_evaluation_report
    test_img = create_test_image()
    hazy_img = create_synthetic_hazy_image(test_img, haze_level=0.6)
    dehazer = DarkChannelDehazer(adaptive_params=True, enhance_enabled=True)
    dehazed_img, _ = dehazer.dehaze_with_info(hazy_img)
    metrics = evaluate_dehazing(hazy_img, dehazed_img, test_img)
    print_evaluation_report(metrics, "Comprehensive Quality Evaluation")
    print("\nMetric Explanations:")
    print("  - Edge Density: Measures visible details (higher = better)")
    print("  - Edge Improvement Ratio: How many more edges are visible")
    print("  - Contrast: Image contrast level (higher = better)")
    print("  - Entropy: Information content in image (higher = better)")
    print("  - PSNR: Peak Signal-to-Noise Ratio (with reference, higher = better)")
    print("  - SSIM: Structural Similarity (with reference, 0-1, higher = better)")
    print("  - Overall Quality Score: Weighted combination of metrics")
    return metrics


def example_8_video_dehazing_concept():
    print("\n" + "=" * 60)
    print("Example 8: Video Dehazing (Temporal Smoothing Demo)")
    print("=" * 60)
    print("Video dehazing features:")
    print("  - Temporal smoothing of haze density estimates")
    print("  - Frame-to-frame parameter consistency")
    print("  - Avoids flickering from abrupt parameter changes")
    print("\nTemporal Smoothing Logic:")
    print("  smoothed_haze(t) = 0.7 * smoothed_haze(t-1) + 0.3 * haze(t)")
    print("\nAvailable video modes:")
    print("  1. Full processing: python dehaze.py video -i input.mp4 -o output.mp4")
    print("  2. Preview mode: python dehaze.py video -i input.mp4 --preview")
    print("  3. With enhancement: python dehaze.py video -i input.mp4 -o output.mp4 --enhance")
    print("\nTo test with synthetic hazy video:")
    print("  1. Use create_synthetic_hazy_video() function")
    print("  2. Process with VideoDehazer class")
    test_img = create_test_image()
    hazy_frames = []
    dehazed_frames = []
    from video_dehazer import VideoDehazer
    dehazer = VideoDehazer(temporal_smooth=True, smooth_window=5)
    print("\nSimulating 10 frames with varying haze:")
    for i in range(10):
        haze_variation = 0.5 + 0.2 * np.sin(i / 2)
        frame = create_synthetic_hazy_image(test_img, haze_level=haze_variation)
        dehazed, info = dehazer.dehaze_frame(frame)
        print(f"  Frame {i}: haze_input={haze_variation:.3f}, haze_smoothed={info['smoothed_haze_density']:.3f}")
    print("\nNotice: Smoothed haze changes more gradually!")
    return dehazer


def example_9_aod_net():
    print("\n" + "=" * 60)
    print("Example 9: AOD-Net Dehazing")
    print("=" * 60)
    if not AOD_NET_AVAILABLE:
        print("Skipping AOD-Net example: PyTorch is not available")
        print("Please install PyTorch to use AOD-Net")
        return None, None
    model_path = 'aod_net_demo.pth'
    create_demo_aod_model(model_path)
    dehazer = AODNetDehazer(model_path=model_path, dehaze_strength=1.0)
    test_img = create_test_image()
    hazy_img = create_synthetic_hazy_image(test_img, haze_level=0.6)
    dehazed_img = dehazer.dehaze(hazy_img)
    os.makedirs('output', exist_ok=True)
    save_image('output/aod_hazy.jpg', hazy_img)
    save_image('output/aod_dehazed.jpg', dehazed_img)
    print("AOD-Net results saved to output/ directory")
    return hazy_img, dehazed_img


def create_test_image(seed=42):
    np.random.seed(seed)
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    img[:200, :, 0] = np.random.randint(100, 150, (200, 600))
    img[:200, :, 1] = np.random.randint(150, 200, (200, 600))
    img[:200, :, 2] = np.random.randint(180, 230, (200, 600))
    img[200:, :, 0] = np.random.randint(30, 80, (200, 600))
    img[200:, :, 1] = np.random.randint(80, 130, (200, 600))
    img[200:, :, 2] = np.random.randint(40, 90, (200, 600))
    for _ in range(10):
        x1 = np.random.randint(50, 550)
        y1 = np.random.randint(220, 380)
        x2 = x1 + np.random.randint(30, 80)
        y2 = y1 + np.random.randint(20, 60)
        color = np.random.randint(20, 100, 3)
        cv2.rectangle(img, (x1, y1), (x2, y2), color.tolist(), -1)
    return img


def create_test_image_with_sky():
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    sky_gradient = np.linspace(180, 230, 200).reshape(-1, 1)
    img[:200, :, 0] = sky_gradient * 0.5
    img[:200, :, 1] = sky_gradient * 0.8
    img[:200, :, 2] = sky_gradient
    img[200:, :, 0] = np.random.randint(30, 70, (200, 600))
    img[200:, :, 1] = np.random.randint(70, 110, (200, 600))
    img[200:, :, 2] = np.random.randint(40, 80, (200, 600))
    return img


def run_all_examples():
    print("\n" + "#" * 60)
    print("# Running All Examples")
    print("#" * 60)
    example_1_adaptive_dehaze()
    example_2_sky_enhanced_processing()
    example_3_haze_density_estimation()
    example_4_batch_with_pre_estimation()
    example_5_manual_vs_adaptive()
    example_6_dehaze_enhance_linkage()
    example_7_quality_evaluation()
    example_8_video_dehazing_concept()
    example_9_aod_net()
    print("\n" + "=" * 60)
    print("All examples completed! Check output/ directory for results.")
    print("=" * 60)


if __name__ == '__main__':
    run_all_examples()
