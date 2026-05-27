import numpy as np
import cv2
import argparse
import sys
from pathlib import Path
import time

from color_constancy import (
    gray_world,
    perfect_reflection,
    shades_of_gray,
    gray_world_block,
    gray_world_multiscale,
    local_white_balance,
    neural_network_estimation,
    correct_white_balance,
    evaluate_illuminant_estimation,
    evaluate_white_balance,
    evaluate_stability,
    evaluate_color_difference_stability,
    SFUGreyBallDataset,
    generate_synthetic_dataset,
    TENSORRT_AVAILABLE
)
from color_constancy.nn_method import IlluminantEstimationNN
from color_constancy.visualization import generate_summary_report, plot_stability_comparison


def parse_args():
    parser = argparse.ArgumentParser(description='Color Constancy Evaluation')
    parser.add_argument('--dataset', type=str, default='synthetic',
                       help='Dataset to use: "synthetic" or path to SFU GreyBall dataset')
    parser.add_argument('--num_samples', type=int, default=30,
                       help='Number of samples for synthetic dataset')
    parser.add_argument('--image_size', type=int, nargs=2, default=(128, 128),
                       help='Image size (height width) for synthetic dataset')
    parser.add_argument('--output_dir', type=str, default='results',
                       help='Output directory for results')
    parser.add_argument('--train_nn', action='store_true',
                       help='Train neural network before evaluation')
    parser.add_argument('--use_tensorrt', action='store_true',
                       help='Use TensorRT acceleration for neural network')
    parser.add_argument('--eval_stability', action='store_true',
                       help='Evaluate algorithm stability')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed')
    return parser.parse_args()


def get_evaluation_methods():
    """
    Get dictionary of color constancy methods to evaluate.
    
    Returns:
        methods: Dictionary of method_name -> (function, kwargs)
    """
    def gw_block_32(img, mask=None):
        est, _ = gray_world_block(img, block_size=32, overlap=8, mask=mask)
        return est
    
    def gw_block_64(img, mask=None):
        est, _ = gray_world_block(img, block_size=64, overlap=16, mask=mask)
        return est
    
    methods = {
        'Gray World': (gray_world, {}),
        'Gray World Block (32x32)': (gw_block_32, {}),
        'Gray World Block (64x64)': (gw_block_64, {}),
        'Gray World Multi-scale': (gray_world_multiscale, {}),
        'Perfect Reflection (99%)': (perfect_reflection, {'percentile': 99}),
        'Perfect Reflection (95%)': (perfect_reflection, {'percentile': 95}),
        'Shades of Gray (p=1)': (shades_of_gray, {'p': 1.0}),
        'Shades of Gray (p=3)': (shades_of_gray, {'p': 3.0}),
        'Shades of Gray (p=6)': (shades_of_gray, {'p': 6.0}),
        'Shades of Gray (p=10)': (shades_of_gray, {'p': 10.0}),
    }
    return methods


def run_illuminant_estimation(images, masks, methods, nn_model=None):
    """
    Run illuminant estimation for all methods.
    
    Args:
        images: List of input images
        masks: List of optional masks
        methods: Dictionary of methods to evaluate
        nn_model: Optional trained neural network model
    
    Returns:
        estimates: Dictionary of method_name -> (N, 3) estimates
        times: Dictionary of method_name -> average time per image
    """
    estimates = {}
    times = {}
    
    all_methods = dict(methods)
    if nn_model is not None:
        all_methods['Neural Network'] = (nn_model.predict, {})
    
    for method_name, (func, kwargs) in all_methods.items():
        print(f"\nRunning {method_name}...")
        method_estimates = []
        total_time = 0
        
        for i, (img, mask) in enumerate(zip(images, masks)):
            start = time.time()
            
            if mask is not None:
                est = func(img, mask=mask, **kwargs)
            else:
                est = func(img, **kwargs)
            
            total_time += time.time() - start
            method_estimates.append(est)
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(images)} images")
        
        estimates[method_name] = np.array(method_estimates)
        times[method_name] = total_time / len(images)
        print(f"  Average time: {times[method_name]:.4f}s per image")
    
    return estimates, times


def run_white_balance_correction(images, estimates, ground_truth_illums):
    """
    Apply white balance correction using estimated illuminants.
    
    Args:
        images: List of original images
        estimates: Dictionary of method_name -> illuminant estimates
        ground_truth_illums: Ground truth illuminants
    
    Returns:
        corrected: Dictionary of method_name -> corrected images
        reference: Reference images corrected with ground truth
    """
    corrected = {}
    reference = []
    
    print("\nApplying white balance correction...")
    
    for i, img in enumerate(images):
        ref = correct_white_balance(img, ground_truth_illums[i])
        reference.append(ref)
    
    for method_name, method_estimates in estimates.items():
        method_corrected = []
        for i, (img, est) in enumerate(zip(images, method_estimates)):
            corr = correct_white_balance(img, est)
            method_corrected.append(corr)
        corrected[method_name] = method_corrected
    
    return corrected, reference


def main():
    args = parse_args()
    np.random.seed(args.seed)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("COLOR CONSTANCY EVALUATION")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Dataset: {args.dataset}")
    print(f"  Output directory: {output_dir}")
    print(f"  Train NN: {args.train_nn}")
    print(f"  Use TensorRT: {args.use_tensorrt}")
    print(f"  Evaluate Stability: {args.eval_stability}")
    print(f"  TensorRT Available: {TENSORRT_AVAILABLE}")
    
    print("\n" + "-" * 60)
    print("Loading dataset...")
    print("-" * 60)
    
    if args.dataset.lower() == 'synthetic':
        print(f"Generating synthetic dataset with {args.num_samples} samples...")
        images, ground_truths, masks = generate_synthetic_dataset(
            num_samples=args.num_samples,
            image_size=tuple(args.image_size),
            seed=args.seed
        )
        print(f"Generated {len(images)} synthetic images")
    else:
        print(f"Loading SFU GreyBall dataset from {args.dataset}...")
        dataset = SFUGreyBallDataset(args.dataset, target_size=tuple(args.image_size))
        images, ground_truths, masks = dataset.get_all()
        print(f"Loaded {len(images)} images")
    
    ground_truths = np.array(ground_truths)
    
    nn_model = None
    if args.train_nn:
        print("\n" + "-" * 60)
        print("Training neural network...")
        print("-" * 60)
        
        use_tensorrt = args.use_tensorrt and TENSORRT_AVAILABLE
        
        if len(images) > 10:
            train_images = images[:int(len(images) * 0.8)]
            train_gt = ground_truths[:int(len(images) * 0.8)]
            train_masks = masks[:int(len(images) * 0.8)]
            
            nn_model = IlluminantEstimationNN(
                input_dim=96, hidden_dims=[128, 64], 
                use_tensorrt=use_tensorrt
            )
            nn_model.train(train_images, train_gt, train_masks, 
                          epochs=50, lr=0.05, batch_size=8)
            
            if use_tensorrt:
                print("TensorRT engine built. Running speed comparison...")
                dummy_img = np.random.randint(0, 255, (args.image_size[0], args.image_size[1], 3), dtype=np.uint8)
                
                nn_model.use_tensorrt = False
                times_cpu = []
                for _ in range(20):
                    start = time.perf_counter()
                    _ = nn_model.predict(dummy_img)
                    times_cpu.append(time.perf_counter() - start)
                
                nn_model.use_tensorrt = True
                times_trt = []
                for _ in range(20):
                    start = time.perf_counter()
                    _ = nn_model.predict(dummy_img)
                    times_trt.append(time.perf_counter() - start)
                
                speedup = np.mean(times_cpu) / np.mean(times_trt)
                print(f"CPU: {np.mean(times_cpu)*1000:.2f}ms, TensorRT: {np.mean(times_trt)*1000:.2f}ms")
                print(f"Speedup: {speedup:.2f}x")
        else:
            print("Warning: Not enough samples for training, using default NN model")
            nn_model = IlluminantEstimationNN(
                input_dim=96, hidden_dims=[128, 64],
                use_tensorrt=(args.use_tensorrt and TENSORRT_AVAILABLE)
            )
    elif args.use_tensorrt and TENSORRT_AVAILABLE:
        nn_model = IlluminantEstimationNN(
            input_dim=96, hidden_dims=[128, 64], use_tensorrt=True
        )
    
    methods = get_evaluation_methods()
    print(f"\nMethods to evaluate: {list(methods.keys())}")
    if nn_model is not None:
        nn_label = "Neural Network"
        if args.use_tensorrt and TENSORRT_AVAILABLE:
            nn_label += " (TensorRT)"
        print(f"  + {nn_label}")
    
    print("\n" + "-" * 60)
    print("Running illuminant estimation...")
    print("-" * 60)
    
    estimates, times = run_illuminant_estimation(images, masks, methods, nn_model)
    
    print("\n" + "-" * 60)
    print("Evaluating illuminant estimation...")
    print("-" * 60)
    
    metrics = {}
    for method_name in estimates.keys():
        method_metrics = evaluate_illuminant_estimation(
            estimates[method_name], ground_truths
        )
        metrics[method_name] = method_metrics
        
        print(f"\n{method_name}:")
        print(f"  Mean Angular Error: {method_metrics['mean']:.2f}°")
        print(f"  Median Angular Error: {method_metrics['median']:.2f}°")
        print(f"  Trimean: {method_metrics['trimean']:.2f}°")
        print(f"  Best 25%: {method_metrics['best25']:.2f}°")
        print(f"  Worst 25%: {method_metrics['worst25']:.2f}°")
        print(f"  Min: {method_metrics['min']:.2f}°, Max: {method_metrics['max']:.2f}°")
        print(f"  Std Angular Error: {method_metrics['std']:.2f}°")
    
    print("\n" + "-" * 60)
    print("Applying white balance correction...")
    print("-" * 60)
    
    corrected, reference = run_white_balance_correction(images, estimates, ground_truths)
    
    print("\n" + "-" * 60)
    print("Evaluating white balance correction...")
    print("-" * 60)
    
    quality_metrics = {}
    color_diff_stability = {}
    for method_name in estimates.keys():
        qm = evaluate_white_balance(corrected[method_name], reference, masks)
        quality_metrics[method_name] = qm
        
        cds = evaluate_color_difference_stability(
            corrected[method_name], reference, masks
        )
        color_diff_stability[method_name] = cds
        
        print(f"\n{method_name}:")
        print(f"  Mean ΔE: {qm['delta_e']['mean']:.2f}")
        print(f"  ΔE Std (per image): {cds['delta_e_std_per_image']['mean']:.2f}")
        print(f"  ΔE Std (overall): {cds['overall_delta_e_distribution']['std']:.2f}")
        print(f"  Mean PSNR: {qm['psnr']['mean']:.2f} dB")
        print(f"  Mean SSIM: {qm['ssim']['mean']:.4f}")
    
    stability_metrics = {}
    if args.eval_stability:
        print("\n" + "-" * 60)
        print("Evaluating algorithm stability...")
        print("-" * 60)
        
        all_methods = dict(methods)
        if nn_model is not None:
            all_methods['Neural Network'] = (nn_model.predict, {})
        
        for method_name, (func, kwargs) in all_methods.items():
            print(f"\nEvaluating stability for {method_name}...")
            
            def wrapped_method(img, mask=None):
                return func(img, mask=mask, **kwargs)
            
            sm = evaluate_stability(
                wrapped_method, images[:10], masks[:10] if masks else None,
                num_runs=5, perturbation_intensity=0.03
            )
            stability_metrics[method_name] = sm
            
            print(f"  Mean Angular Variation: {sm['mean_angular_variation_deg']:.4f}°")
            print(f"  Overall Mean Std: {sm['overall_mean_std']:.6f}")
            print(f"  Coefficient of Variation: {sm['coefficient_of_variation']:.6f}")
    
    print("\n" + "-" * 60)
    print("Generating summary report...")
    print("-" * 60)
    
    sample_idx = min(5, len(images) - 1)
    sample_results = {
        'original': images[sample_idx],
        'corrected': {m: corrected[m][sample_idx] for m in estimates.keys()},
        'ground_truth': reference[sample_idx]
    }
    
    results = {
        'num_samples': len(images),
        'estimates': estimates,
        'ground_truths': ground_truths,
        'metrics': metrics,
        'quality_metrics': quality_metrics,
        'color_diff_stability': color_diff_stability,
        'stability_metrics': stability_metrics,
        'times': times,
        'sample_results': sample_results
    }
    
    generate_summary_report(results, output_dir)
    
    if args.eval_stability:
        try:
            plot_stability_comparison(stability_metrics, output_dir / 'stability_comparison.png')
        except Exception as e:
            print(f"Warning: Could not generate stability plot: {e}")
    
    results_path = output_dir / 'results.npz'
    np.savez(results_path,
             estimates=np.array([estimates[m] for m in estimates.keys()]),
             ground_truths=ground_truths,
             method_names=np.array(list(estimates.keys())))
    print(f"\nRaw results saved to {results_path}")
    
    txt_report = output_dir / 'evaluation_summary.txt'
    with open(txt_report, 'a') as f:
        f.write('\n' + '=' * 60 + '\n')
        f.write('COLOR DIFFERENCE STANDARD DEVIATION (ΔE Std)\n')
        f.write('=' * 60 + '\n\n')
        f.write(f"{'Method':<25} {'ΔE Mean':>8} {'ΔE Std':>8} {'Overall ΔE Std':>12}\n")
        f.write('-' * 60 + '\n')
        for method_name in estimates.keys():
            qm = quality_metrics[method_name]
            cds = color_diff_stability[method_name]
            f.write(f"{method_name:<25} {qm['delta_e']['mean']:>8.2f} "
                   f"{cds['delta_e_std_per_image']['mean']:>8.2f} "
                   f"{cds['overall_delta_e_distribution']['std']:>12.2f}\n")
        
        if stability_metrics:
            f.write('\n' + '=' * 60 + '\n')
            f.write('ALGORITHM STABILITY METRICS\n')
            f.write('=' * 60 + '\n\n')
            f.write(f"{'Method':<25} {'Angular Var':>12} {'Mean Std':>10} {'CoV':>10}\n")
            f.write('-' * 60 + '\n')
            for method_name, sm in stability_metrics.items():
                f.write(f"{method_name:<25} {sm['mean_angular_variation_deg']:>12.4f}° "
                       f"{sm['overall_mean_std']:>10.6f} "
                       f"{sm['coefficient_of_variation']:>10.6f}\n")
    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    print(f"\nResults saved to: {output_dir}")
    print("\nSummary of angular errors (mean):")
    for method_name in estimates.keys():
        print(f"  {method_name:<25}: {metrics[method_name]['mean']:.2f}°")
    
    best_method = min(metrics.keys(), key=lambda m: metrics[m]['mean'])
    print(f"\nBest method: {best_method} (mean: {metrics[best_method]['mean']:.2f}°)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
