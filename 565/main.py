import numpy as np
import matplotlib.pyplot as plt
import time
import argparse

from hsrx_detector import RXDetector
from sliding_window import SlidingWindowRX, GlobalBackgroundUpdater
from hs_utils import (
    generate_hyperspectral_image,
    generate_complex_hyperspectral,
    HSVisualizer,
    compute_metrics
)
from gpu_module import RXGPU, benchmark_gpu_cpu


def demo_global_rx(use_gpu: bool = False):
    print("=" * 60)
    print("Demo 1: Global RX Anomaly Detection")
    print("=" * 60)

    print("\nGenerating hyperspectral image...")
    image, ground_truth = generate_hyperspectral_image(
        height=150, width=150, n_bands=50, n_anomalies=6, seed=42
    )
    print(f"Image shape: {image.shape}")
    print(f"Number of anomaly pixels: {np.sum(ground_truth)}")

    print("\nRunning RX detection...")
    detector = RXDetector(use_gpu=use_gpu)
    start_time = time.time()
    scores = detector.fit_detect(image)
    elapsed_time = time.time() - start_time
    print(f"Detection completed in {elapsed_time:.4f} seconds")

    metrics = compute_metrics(scores, ground_truth, threshold_percentile=95)
    print(f"\nDetection Metrics:")
    print(f"  AUC: {metrics['auc']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall: {metrics['recall']:.4f}")
    print(f"  F1 Score: {metrics['f1']:.4f}")

    visualizer = HSVisualizer()
    fig, axes = visualizer.plot_detection_results(image, scores, ground_truth)
    plt.savefig('global_rx_results.png', dpi=150, bbox_inches='tight')
    print("\nResults saved to 'global_rx_results.png'")

    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5))
    visualizer.plot_score_histogram(scores, ground_truth, ax=axes2[0])
    visualizer.plot_roc_curve(scores, ground_truth, ax=axes2[1])
    plt.tight_layout()
    plt.savefig('global_rx_analysis.png', dpi=150, bbox_inches='tight')
    print("Analysis saved to 'global_rx_analysis.png'")

    plt.close('all')
    return scores, metrics


def demo_sliding_window():
    print("\n" + "=" * 60)
    print("Demo 2: Sliding Window RX Detection")
    print("=" * 60)

    print("\nGenerating complex hyperspectral image...")
    image, ground_truth = generate_complex_hyperspectral(
        height=120, width=120, n_bands=30, seed=42
    )
    print(f"Image shape: {image.shape}")

    print("\nRunning sliding window RX detection...")
    print("  Window size: 40, Guard size: 8, Update interval: 20")
    detector = SlidingWindowRX(window_size=40, guard_size=8, update_interval=20)
    
    start_time = time.time()
    scores = detector.detect_image(image, step=1)
    elapsed_time = time.time() - start_time
    print(f"Detection completed in {elapsed_time:.4f} seconds")

    metrics = compute_metrics(scores, ground_truth, threshold_percentile=95)
    print(f"\nDetection Metrics:")
    print(f"  AUC: {metrics['auc']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall: {metrics['recall']:.4f}")

    visualizer = HSVisualizer()
    fig, axes = visualizer.plot_detection_results(image, scores, ground_truth)
    plt.savefig('sliding_window_results.png', dpi=150, bbox_inches='tight')
    print("\nResults saved to 'sliding_window_results.png'")
    plt.close('all')

    return scores, metrics


def demo_background_update():
    print("\n" + "=" * 60)
    print("Demo 3: Adaptive Background Update")
    print("=" * 60)

    print("\nGenerating sequential hyperspectral data...")
    n_frames = 5
    frames = []
    ground_truths = []

    for i in range(n_frames):
        image, gt = generate_hyperspectral_image(
            height=80, width=80, n_bands=40, n_anomalies=4, seed=100 + i
        )
        frames.append(image)
        ground_truths.append(gt)

    print(f"Generated {n_frames} frames")

    updater = GlobalBackgroundUpdater(alpha=0.1)
    updater.initialize(frames[0])

    all_scores = []
    all_metrics = []

    print("\nProcessing frames with adaptive background update...")
    for i, (frame, gt) in enumerate(zip(frames, ground_truths)):
        scores = updater.detect(frame)
        all_scores.append(scores)

        metrics = compute_metrics(scores, gt, threshold_percentile=95)
        all_metrics.append(metrics)

        print(f"  Frame {i+1}: AUC = {metrics['auc']:.4f}")

        if i < n_frames - 1:
            updater.update(frame)

    fig, axes = plt.subplots(2, n_frames, figsize=(4 * n_frames, 8))
    visualizer = HSVisualizer()

    for i in range(n_frames):
        visualizer.plot_rgb_composite(frames[i], ax=axes[0, i], title=f"Frame {i+1}")
        im = axes[1, i].imshow(all_scores[i], cmap='hot')
        axes[1, i].set_title(f"Scores - AUC: {all_metrics[i]['auc']:.3f}")
        axes[1, i].axis('off')

    plt.tight_layout()
    plt.savefig('adaptive_background_results.png', dpi=150, bbox_inches='tight')
    print("\nResults saved to 'adaptive_background_results.png'")
    plt.close('all')

    return all_scores, all_metrics


def demo_gpu_benchmark():
    print("\n" + "=" * 60)
    print("Demo 4: GPU vs CPU Benchmark")
    print("=" * 60)

    print("\nGenerating benchmark data...")
    n_samples_list = [1000, 5000, 10000, 25000, 50000]
    n_bands = 50

    results = []

    for n_samples in n_samples_list:
        print(f"\nBenchmarking {n_samples} samples...")
        data = np.random.randn(n_samples, n_bands)
        mean = np.random.randn(n_bands)
        cov = np.random.randn(n_bands, n_bands)
        cov = cov.T @ cov + 0.1 * np.eye(n_bands)
        cov_inv = np.linalg.inv(cov)

        benchmark = benchmark_gpu_cpu(data, mean, cov_inv)
        benchmark['n_samples'] = n_samples
        results.append(benchmark)

        print(f"  CPU time: {benchmark['cpu_time']:.4f}s")
        print(f"  GPU time: {benchmark['gpu_time']:.4f}s")
        print(f"  Speedup: {benchmark['speedup']:.2f}x")
        print(f"  GPU available: {benchmark['gpu_available']}")

    fig, ax = plt.subplots(figsize=(10, 6))
    
    samples = [r['n_samples'] for r in results]
    cpu_times = [r['cpu_time'] for r in results]
    gpu_times = [r['gpu_time'] for r in results]
    speedups = [r['speedup'] for r in results]

    ax.plot(samples, cpu_times, 'o-', label='CPU', linewidth=2)
    ax.plot(samples, gpu_times, 's-', label='GPU', linewidth=2)
    ax.set_xlabel('Number of Samples')
    ax.set_ylabel('Time (seconds)')
    ax.set_title('CPU vs GPU Performance Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xscale('log')
    ax.set_yscale('log')

    plt.tight_layout()
    plt.savefig('gpu_benchmark.png', dpi=150, bbox_inches='tight')
    print("\nBenchmark plot saved to 'gpu_benchmark.png'")
    plt.close('all')

    return results


def run_all_demos(use_gpu: bool = False):
    print("\n" + "=" * 60)
    print("HYPERSPECTRAL ANOMALY DETECTION DEMO")
    print("RX Algorithm with Sliding Window and GPU Acceleration")
    print("=" * 60)

    demo_global_rx(use_gpu=use_gpu)
    demo_sliding_window()
    demo_background_update()
    demo_gpu_benchmark()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Hyperspectral Anomaly Detection using RX Algorithm'
    )
    parser.add_argument(
        '--demo',
        type=str,
        default='all',
        choices=['all', 'global', 'sliding', 'adaptive', 'benchmark'],
        help='Which demo to run'
    )
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Use GPU acceleration if available'
    )
    parser.add_argument(
        '--no-show',
        action='store_true',
        help='Do not display plots, only save to files'
    )

    args = parser.parse_args()

    if args.demo == 'all':
        run_all_demos(use_gpu=args.gpu)
    elif args.demo == 'global':
        demo_global_rx(use_gpu=args.gpu)
    elif args.demo == 'sliding':
        demo_sliding_window()
    elif args.demo == 'adaptive':
        demo_background_update()
    elif args.demo == 'benchmark':
        demo_gpu_benchmark()

    if not args.no_show:
        plt.show()


if __name__ == '__main__':
    main()
