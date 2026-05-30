import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from typing import List, Dict, Any
from tqdm import tqdm

from config import Config
from core import (
    AttentionHeatmap, ModelExplainer,
    generate_attention_heatmap, explain_prediction,
    visualize_feature_maps, generate_gradcam
)
from utils.helpers import load_image, save_image


def create_test_data():
    print("Creating test image and saliency map...")
    
    image = np.ones((300, 400, 3), dtype=np.uint8) * 230
    
    cv2.circle(image, (120, 150), 50, (200, 100, 100), -1)
    cv2.rectangle(image, (220, 80), (350, 220), (100, 150, 255), -1)
    cv2.circle(image, (300, 150), 30, (100, 200, 100), -1)
    
    saliency = np.zeros((300, 400), dtype=np.float32)
    for y in range(300):
        for x in range(400):
            d1 = np.sqrt((x - 120) ** 2 + (y - 150) ** 2)
            d2 = np.sqrt((x - 300) ** 2 + (y - 150) ** 2)
            v1 = np.exp(-d1 ** 2 / (2 * 60 ** 2))
            v2 = np.exp(-d2 ** 2 / (2 * 40 ** 2))
            saliency[y, x] = max(v1, v2 * 0.8)
    
    saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min() + 1e-8)
    
    return image, saliency


def example_attention_heatmap():
    print("\n" + "=" * 60)
    print("EXAMPLE: Attention Heatmap Generation")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'heatmap')
    os.makedirs(output_dir, exist_ok=True)
    
    save_image(image, os.path.join(output_dir, 'original.png'))
    save_image((saliency * 255).astype(np.uint8), os.path.join(output_dir, 'saliency.png'))
    
    print("\nTesting different heatmap parameters...")
    
    colormaps = [
        (cv2.COLORMAP_JET, 'jet', (0.3, 0.3)),
        (cv2.COLORMAP_VIRIDIS, 'viridis', (0.3, 0.3)),
        (cv2.COLORMAP_HOT, 'hot', (0.3, 0.3)),
        (cv2.COLORMAP_COOL, 'cool', (0.3, 0.3)),
        (cv2.COLORMAP_PARULA, 'parula', (0.3, 0.3)),
    ]
    
    heatmap_results = []
    
    for cmap, name, (alpha, threshold) in tqdm(colormaps, desc="Generating heatmaps"):
        generator = AttentionHeatmap(colormap=cmap, alpha=alpha)
        result = generator.generate(saliency, image, threshold=threshold, min_region_size=100)
        heatmap_results.append((name, result))
        
        save_image(result.overlay, os.path.join(output_dir, f'overlay_{name}.png'))
        
        annotated = generator.draw_attention_boxes(result, draw_top_k=2)
        save_image(annotated, os.path.join(output_dir, f'annotated_{name}.png'))
    
    print("\nHeatmap statistics:")
    for name, result in heatmap_results:
        print(f"  {name:12s}: {len(result.attention_regions)} regions, "
              f"mean attention={result.attention_regions[0]['mean_attention']:.3f}" 
              if result.attention_regions else "No regions")
    
    print("\nHeatmap features:")
    print("  - JET: High contrast, good for highlighting")
    print("  - VIRIDIS: Perceptually uniform, eye-friendly")
    print("  - HOT: Intensity-based, good for heat detection")
    print("  - COOL: Blue-magenta, good for medical imaging")
    print("  - PARULA: Smooth gradient, modern look")
    
    return heatmap_results


def example_attention_regions():
    print("\n" + "=" * 60)
    print("EXAMPLE: Attention Region Analysis")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'regions')
    os.makedirs(output_dir, exist_ok=True)
    
    generator = AttentionHeatmap(alpha=0.4)
    
    thresholds = [0.2, 0.3, 0.5, 0.7]
    
    print("\nTesting different thresholds...")
    results = []
    
    for thresh in thresholds:
        result = generator.generate(saliency, image, threshold=thresh, min_region_size=50)
        results.append((thresh, result))
        
        annotated = generator.draw_attention_boxes(result, draw_top_k=3)
        save_image(annotated, os.path.join(output_dir, f'regions_thresh{thresh}.png'))
        
        print(f"  Threshold {thresh}: {len(result.attention_regions)} regions")
        for i, region in enumerate(result.attention_regions[:3]):
            print(f"    Region #{i+1}: area={region['area']}, "
                  f"mean={region['mean_attention']:.3f}, "
                  f"bbox={region['bbox']}")
    
    print("\nRegion properties:")
    print("  - bbox: Bounding box (x, y, w, h)")
    print("  - center: Centroid coordinates")
    print("  - area: Pixel count")
    print("  - mean_attention: Average saliency in region")
    print("  - max_attention: Peak saliency value")
    print("  - mask: Binary mask of the region")
    
    return results


def example_multi_scale_heatmap():
    print("\n" + "=" * 60)
    print("EXAMPLE: Multi-Scale Attention Heatmap")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'multiscale')
    os.makedirs(output_dir, exist_ok=True)
    
    generator = AttentionHeatmap(alpha=0.5)
    
    print("\nGenerating multi-scale heatmap...")
    result = generator.generate_multi_scale(
        saliency, image,
        scales=[0.5, 1.0, 1.5, 2.0],
        threshold=0.3
    )
    
    save_image(result.overlay, os.path.join(output_dir, 'multiscale_overlay.png'))
    
    print("  Multi-scale combines information across different resolutions")
    print("  - Reduces sensitivity to object scale variations")
    print("  - More robust attention detection")
    
    return result


def example_dynamic_heatmap():
    print("\n" + "=" * 60)
    print("EXAMPLE: Dynamic (Temporal) Heatmap")
    print("=" * 60)
    
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'dynamic')
    os.makedirs(output_dir, exist_ok=True)
    
    generator = AttentionHeatmap(alpha=0.5)
    
    num_frames = 15
    print(f"\nGenerating {num_frames} frame sequence...")
    
    frames = []
    saliency_maps = []
    
    for i in range(num_frames):
        image = np.ones((256, 256, 3), dtype=np.uint8) * 220
        
        cx = int(128 + 60 * np.sin(i * 0.4))
        cy = int(128 + 40 * np.cos(i * 0.3))
        
        cv2.circle(image, (cx, cy), 30, (255, 100, 100), -1)
        frames.append(image)
        
        saliency = np.zeros((256, 256), dtype=np.float32)
        for y in range(256):
            for x in range(256):
                dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                saliency[y, x] = np.exp(-dist ** 2 / (2 * 40 ** 2))
        saliency += np.random.normal(0, 0.03, saliency.shape).astype(np.float32)
        saliency = np.clip(saliency, 0, 1)
        saliency_maps.append(saliency)
    
    print("\nApplying dynamic heatmap with temporal smoothing...")
    
    results = []
    for i in tqdm(range(num_frames), desc="Processing frames"):
        result = generator.generate_dynamic_heatmap(
            saliency_maps[i], frames[i],
            time_window=5,
            decay_rate=0.8
        )
        results.append(result)
        
        comparison = np.hstack([
            frames[i],
            result.overlay
        ])
        save_image(comparison, os.path.join(output_dir, f'frame_{i:03d}.png'))
    
    print("\nDynamic heatmap features:")
    print("  - Accumulates attention over time window")
    print("  - Exponential decay for recent frames")
    print("  - Reduces flickering in video sequences")
    
    print("\nCreating video...")
    output_video = os.path.join(output_dir, 'dynamic_heatmap.mp4')
    h, w = comparison.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_video, fourcc, 5, (w, h))
    
    for i in range(num_frames):
        img_path = os.path.join(output_dir, f'frame_{i:03d}.png')
        img = cv2.imread(img_path)
        if img is not None:
            writer.write(img)
    
    writer.release()
    print(f"Video saved to: {output_video}")
    
    return results


def example_stats_analysis():
    print("\n" + "=" * 60)
    print("EXAMPLE: Attention Statistics Analysis")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'stats')
    os.makedirs(output_dir, exist_ok=True)
    
    explainer = ModelExplainer()
    
    print("\nComputing attention statistics...")
    heatmap_result = generate_attention_heatmap(saliency, image, threshold=0.3)
    
    stats = explainer._compute_attention_stats(saliency, heatmap_result)
    
    print("\nAttention Statistics:")
    print(f"  Mean attention:    {stats['mean_attention']:.4f}")
    print(f"  Max attention:     {stats['max_attention']:.4f}")
    print(f"  Std deviation:     {stats['std_attention']:.4f}")
    print(f"  Num regions:       {stats['num_regions']}")
    print(f"  Total area:        {stats['total_attention_area']:.2%}")
    print(f"  Coverage (>50%):   {stats['attention_above_50']:.2%}")
    print(f"  Attention entropy: {stats['attention_entropy']:.2f}")
    
    print("\nTop regions:")
    for i, region in enumerate(stats['top_regions'][:3]):
        print(f"  Region #{i+1}: area={region['area_ratio']:.2%}, "
              f"mean={region['mean_attention']:.3f}")
    
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    axes[0, 0].set_title('Original Image')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(saliency, cmap='jet')
    axes[0, 1].set_title('Saliency Map')
    axes[0, 1].axis('off')
    
    hist, bins = np.histogram(saliency.flatten(), bins=50, range=(0, 1))
    axes[1, 0].bar(bins[:-1], hist, width=0.02)
    axes[1, 0].set_title('Saliency Distribution')
    axes[1, 0].set_xlabel('Saliency Value')
    axes[1, 0].set_ylabel('Pixel Count')
    axes[1, 0].axvline(stats['mean_attention'], color='r', linestyle='--', label=f'Mean: {stats["mean_attention"]:.3f}')
    axes[1, 0].legend()
    
    region_names = [f'#{i+1}' for i in range(len(stats['top_regions']))]
    region_means = [r['mean_attention'] for r in stats['top_regions']]
    region_areas = [r['area_ratio'] * 100 for r in stats['top_regions']]
    
    x = np.arange(len(region_names))
    width = 0.35
    
    axes[1, 1].bar(x - width/2, region_means, width, label='Mean Attention')
    axes[1, 1].bar(x + width/2, region_areas, width, label='Area (%)')
    axes[1, 1].set_title('Top Regions Analysis')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(region_names)
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    stats_plot_path = os.path.join(output_dir, 'attention_stats.png')
    plt.savefig(stats_plot_path)
    plt.close()
    
    print(f"\nStatistics plot saved to: {stats_plot_path}")
    
    return stats


def example_heatmap_legend():
    print("\n" + "=" * 60)
    print("EXAMPLE: Heatmap Legend and Colormap Guide")
    print("=" * 60)
    
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'legend')
    os.makedirs(output_dir, exist_ok=True)
    
    colormaps = [
        (cv2.COLORMAP_JET, 'JET'),
        (cv2.COLORMAP_VIRIDIS, 'VIRIDIS'),
        (cv2.COLORMAP_HOT, 'HOT'),
        (cv2.COLORMAP_COOL, 'COOL'),
        (cv2.COLORMAP_PARULA, 'PARULA'),
        (cv2.COLORMAP_BONE, 'BONE'),
        (cv2.COLORMAP_RAINBOW, 'RAINBOW'),
        (cv2.COLORMAP_OCEAN, 'OCEAN'),
    ]
    
    print("\nGenerating colormap legends...")
    
    legend_width = 400
    legend_height = 50
    total_height = len(colormaps) * (legend_height + 30)
    
    legend_image = np.ones((total_height, legend_width + 100, 3), dtype=np.uint8) * 255
    
    for i, (cmap, name) in enumerate(colormaps):
        generator = AttentionHeatmap(colormap=cmap)
        legend = generator.create_heatmap_legend(width=legend_width, height=legend_height)
        
        y_offset = i * (legend_height + 30)
        legend_image[y_offset:y_offset+legend_height, 10:10+legend_width] = legend
        
        cv2.putText(legend_image, name, (legend_width + 25, y_offset + 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        cv2.putText(legend_image, '0.0', (10, y_offset + legend_height + 18),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
        cv2.putText(legend_image, '1.0', (legend_width - 20, y_offset + legend_height + 18),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    
    legend_path = os.path.join(output_dir, 'colormap_guide.png')
    save_image(legend_image, legend_path)
    
    print(f"Colormap guide saved to: {legend_path}")
    
    print("\nColormap recommendations:")
    print("  - VIRIDIS: Best for scientific visualization (perceptually uniform)")
    print("  - JET: Good for highlighting attention (high contrast)")
    print("  - HOT: Good for thermal/heat interpretation")
    print("  - PARULA: Smooth gradient, pleasing to eye")
    
    return legend_image


def example_convenience_functions():
    print("\n" + "=" * 60)
    print("EXAMPLE: Convenience Functions")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo', 'quick')
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nUsing convenience functions...")
    
    heatmap_result = generate_attention_heatmap(
        saliency, image,
        colormap=cv2.COLORMAP_JET,
        alpha=0.5,
        threshold=0.3,
        min_region_size=100
    )
    save_image(heatmap_result.overlay, os.path.join(output_dir, 'quick_heatmap.png'))
    print(f"  Heatmap: {len(heatmap_result.attention_regions)} regions detected")
    
    print("\n  All convenience functions executed successfully!")
    
    return heatmap_result


def create_explanation_composite():
    print("\n" + "=" * 60)
    print("CREATING COMPREHENSIVE EXPLANATION VISUALIZATION")
    print("=" * 60)
    
    image, saliency = create_test_data()
    output_dir = os.path.join(Config.OUTPUT_DIR, 'explain_demo')
    os.makedirs(output_dir, exist_ok=True)
    
    explainer = ModelExplainer()
    
    print("\nGenerating heatmap result...")
    heatmap_result = generate_attention_heatmap(saliency, image, threshold=0.3)
    
    print("\nComputing statistics...")
    stats = explainer._compute_attention_stats(saliency, heatmap_result)
    
    print("\nCreating visualization...")
    
    class MockExplainerResult:
        def __init__(self):
            self.heatmap_result = heatmap_result
            self.feature_maps = []
            self.attention_stats = stats
    
    mock_result = MockExplainerResult()
    
    visualization = explainer.create_explanation_visualization(
        mock_result,
        figsize=(1000, 600)
    )
    
    viz_path = os.path.join(output_dir, 'explanation_visualization.png')
    save_image(visualization, viz_path)
    
    print(f"Visualization saved to: {viz_path}")
    
    print("\nSaving all outputs...")
    explainer.save_explanation(
        mock_result,
        output_dir=os.path.join(output_dir, 'saved'),
        base_filename='test_explanation'
    )
    
    print("  All outputs saved successfully!")
    
    return visualization


def main():
    print("\n" + "=" * 60)
    print("ATTENTION HEATMAP & EXPLAINABILITY - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    try:
        example_attention_heatmap()
        example_attention_regions()
        example_multi_scale_heatmap()
        example_dynamic_heatmap()
        example_stats_analysis()
        example_heatmap_legend()
        example_convenience_functions()
        create_explanation_composite()
        
        print("\n" + "=" * 60)
        print("ALL EXPLAINABILITY EXAMPLES COMPLETE")
        print("=" * 60)
        
        print(f"\nAll outputs saved to: {os.path.join(Config.OUTPUT_DIR, 'explain_demo')}")
        
    except Exception as e:
        print(f"\nError during examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
