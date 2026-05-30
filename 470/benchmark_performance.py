import os
import sys
import time
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2

from config import Config
from core import SaliencyInferencer
from core import guided_filter_refine, refine_edges
from core import process_with_dynamic_batch

Config.ensure_dirs()


def create_test_image(size=(256, 256)):
    img = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    cv2.circle(img, (size[1]//2, size[0]//2), min(size)//3, (255, 100, 100), -1)
    cv2.rectangle(img, (size[1]//4, size[0]//4), 
                  (size[1]//2, size[0]//2), (100, 255, 100), -1)
    return img


def benchmark_inference_speed(model_name='basnet', num_runs=100, warmup=10):
    print("\n" + "=" * 60)
    print("BENCHMARK: Inference Speed")
    print("=" * 60)
    
    test_img = create_test_image()
    
    print(f"\n[Test 1] PyTorch {model_name.upper()} Inference")
    print("-" * 40)
    inferencer_pytorch = SaliencyInferencer(
        model_name=model_name, 
        pretrained=False, 
        use_tensorrt=False
    )
    stats_pytorch = inferencer_pytorch.benchmark_inference(
        test_img, num_runs=num_runs, warmup_runs=warmup
    )
    
    print(f"\n[Test 2] TensorRT {model_name.upper()} Inference")
    print("-" * 40)
    inferencer_trt = SaliencyInferencer(
        model_name=model_name, 
        pretrained=False, 
        use_tensorrt=True
    )
    
    if inferencer_trt.use_tensorrt:
        stats_trt = inferencer_trt.benchmark_inference(
            test_img, num_runs=num_runs, warmup_runs=warmup
        )
        
        speedup = stats_pytorch['mean_ms'] / stats_trt['mean_ms']
        print(f"\nSpeedup: {speedup:.2f}x")
        print(f"Target time: {Config.TARGET_INFERENCE_TIME}ms")
        print(f"PyTorch meets target: {stats_pytorch['meets_target']}")
        print(f"TensorRT meets target: {stats_trt['meets_target']}")
    else:
        print("TensorRT not available (engine not found or TensorRT not installed)")
        stats_trt = None
    
    return stats_pytorch, stats_trt


def benchmark_edge_refinement(num_runs=50):
    print("\n" + "=" * 60)
    print("BENCHMARK: Edge Refinement Methods")
    print("=" * 60)
    
    test_img = create_test_image((512, 512))
    test_saliency = np.random.rand(512, 512).astype(np.float32)
    test_mask = (test_saliency > 0.5).astype(np.float32)
    
    print(f"\n[Test 1] Morphological Refinement")
    print("-" * 40)
    times_morph = []
    for i in range(num_runs):
        start = time.time()
        sal_morph, mask_morph = refine_edges(test_saliency, test_mask)
        elapsed = (time.time() - start) * 1000
        times_morph.append(elapsed)
    
    times_morph = np.array(times_morph)
    print(f"Mean: {times_morph.mean():.2f} ms")
    print(f"Median: {np.median(times_morph):.2f} ms")
    print(f"Min/Max: {times_morph.min():.2f} / {times_morph.max():.2f} ms")
    
    print(f"\n[Test 2] Guided Filter Refinement (Gray)")
    print("-" * 40)
    times_guided_gray = []
    for i in range(num_runs):
        start = time.time()
        sal_guided = guided_filter_refine(
            test_saliency, test_img, 
            radius=15, eps=1e-3, use_color=False
        )
        elapsed = (time.time() - start) * 1000
        times_guided_gray.append(elapsed)
    
    times_guided_gray = np.array(times_guided_gray)
    print(f"Mean: {times_guided_gray.mean():.2f} ms")
    print(f"Median: {np.median(times_guided_gray):.2f} ms")
    print(f"Min/Max: {times_guided_gray.min():.2f} / {times_guided_gray.max():.2f} ms")
    
    print(f"\n[Test 3] Guided Filter Refinement (Color)")
    print("-" * 40)
    times_guided_color = []
    for i in range(num_runs):
        start = time.time()
        sal_guided_color = guided_filter_refine(
            test_saliency, test_img, 
            radius=15, eps=1e-3, use_color=True
        )
        elapsed = (time.time() - start) * 1000
        times_guided_color.append(elapsed)
    
    times_guided_color = np.array(times_guided_color)
    print(f"Mean: {times_guided_color.mean():.2f} ms")
    print(f"Median: {np.median(times_guided_color):.2f} ms")
    print(f"Min/Max: {times_guided_color.min():.2f} / {times_guided_color.max():.2f} ms")
    
    print(f"\n[Test 4] Fast Guided Filter Refinement")
    print("-" * 40)
    times_guided_fast = []
    for i in range(num_runs):
        start = time.time()
        sal_guided_fast = guided_filter_refine(
            test_saliency, test_img, 
            radius=15, eps=1e-3, use_color=True, fast=True
        )
        elapsed = (time.time() - start) * 1000
        times_guided_fast.append(elapsed)
    
    times_guided_fast = np.array(times_guided_fast)
    print(f"Mean: {times_guided_fast.mean():.2f} ms")
    print(f"Median: {np.median(times_guided_fast):.2f} ms")
    print(f"Min/Max: {times_guided_fast.min():.2f} / {times_guided_fast.max():.2f} ms")
    
    return {
        'morphological': times_morph,
        'guided_gray': times_guided_gray,
        'guided_color': times_guided_color,
        'guided_fast': times_guided_fast
    }


def benchmark_dynamic_batch(num_images=20, initial_batch_size=8):
    print("\n" + "=" * 60)
    print("BENCHMARK: Dynamic Batch Processing")
    print("=" * 60)
    
    test_images = [create_test_image() for _ in range(num_images)]
    
    inferencer = SaliencyInferencer(
        model_name='basnet', 
        pretrained=False, 
        use_tensorrt=False
    )
    
    def process_batch(batch):
        return inferencer.predict_batch(
            batch, 
            dynamic_batch=False,
            refine_method='guided'
        )
    
    print(f"\n[Test] Dynamic Batch Processing ({num_images} images)")
    print("-" * 40)
    print(f"Initial batch size: {initial_batch_size}")
    print(f"Max batch size: {Config.MAX_BATCH_SIZE}")
    
    results, stats = process_with_dynamic_batch(
        test_images,
        process_func=process_batch,
        initial_batch_size=initial_batch_size,
        min_batch_size=1,
        max_batch_size=Config.MAX_BATCH_SIZE,
        show_progress=True
    )
    
    print(f"\nResults:")
    print(f"  Total time: {stats.total_time:.2f} s")
    print(f"  Processed: {stats.processed_items} / {stats.total_items}")
    print(f"  Failed: {stats.failed_items}")
    print(f"  Avg time per image: {stats.avg_time_per_item * 1000:.1f} ms")
    print(f"  Peak memory usage: {stats.memory_peak * 100:.1f}%")
    
    print(f"\n  Batch size history: {stats.batch_size_history}")
    if stats.batch_size_history:
        print(f"  Batch size range: {min(stats.batch_size_history)} - {max(stats.batch_size_history)}")
        print(f"  Average batch size: {sum(stats.batch_size_history)/len(stats.batch_size_history):.1f}")
    
    return stats


def benchmark_full_pipeline(model_name='basnet', num_runs=20):
    print("\n" + "=" * 60)
    print("BENCHMARK: Full Pipeline")
    print("=" * 60)
    
    test_img = create_test_image()
    
    inferencer = SaliencyInferencer(
        model_name=model_name, 
        pretrained=False, 
        use_tensorrt=False
    )
    
    print(f"\n[Test 1] Full Pipeline (Morphological Refinement)")
    print("-" * 40)
    times_morph = []
    for i in range(num_runs):
        start = time.time()
        result = inferencer.predict(
            test_img, 
            edge_refinement=True,
            refine_method='morph',
            measure_time=True
        )
        elapsed = (time.time() - start) * 1000
        times_morph.append(elapsed)
        if i == 0:
            s = result['stats']
            print(f"  Preprocess: {s['preprocess_time_ms']:.1f} ms")
            print(f"  Inference: {s['inference_time_ms']:.1f} ms")
            print(f"  Postprocess: {s['postprocess_time_ms']:.1f} ms")
    
    times_morph = np.array(times_morph)
    print(f"\n  Total mean: {times_morph.mean():.1f} ms")
    print(f"  Total median: {np.median(times_morph):.1f} ms")
    
    print(f"\n[Test 2] Full Pipeline (Guided Filter Refinement)")
    print("-" * 40)
    times_guided = []
    for i in range(num_runs):
        start = time.time()
        result = inferencer.predict(
            test_img, 
            edge_refinement=True,
            refine_method='guided',
            measure_time=True
        )
        elapsed = (time.time() - start) * 1000
        times_guided.append(elapsed)
        if i == 0:
            s = result['stats']
            print(f"  Preprocess: {s['preprocess_time_ms']:.1f} ms")
            print(f"  Inference: {s['inference_time_ms']:.1f} ms")
            print(f"  Postprocess: {s['postprocess_time_ms']:.1f} ms")
    
    times_guided = np.array(times_guided)
    print(f"\n  Total mean: {times_guided.mean():.1f} ms")
    print(f"  Total median: {np.median(times_guided):.1f} ms")
    
    return {
        'morphological': times_morph,
        'guided_filter': times_guided
    }


def main():
    parser = argparse.ArgumentParser(description='Performance benchmark')
    parser.add_argument('--test', '-t', default='all',
                       choices=['all', 'inference', 'edge', 'batch', 'pipeline'],
                       help='Test to run')
    parser.add_argument('--model', '-m', default='basnet',
                       choices=['basnet', 'poolnet'],
                       help='Model to benchmark')
    parser.add_argument('--runs', type=int, default=50,
                       help='Number of runs for benchmarks')
    
    args = parser.parse_args()
    
    results = {}
    
    if args.test in ['all', 'inference']:
        results['inference'] = benchmark_inference_speed(
            model_name=args.model,
            num_runs=args.runs
        )
    
    if args.test in ['all', 'edge']:
        results['edge'] = benchmark_edge_refinement(num_runs=args.runs)
    
    if args.test in ['all', 'batch']:
        results['batch'] = benchmark_dynamic_batch()
    
    if args.test in ['all', 'pipeline']:
        results['pipeline'] = benchmark_full_pipeline(
            model_name=args.model,
            num_runs=min(args.runs, 20)
        )
    
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    try:
        main()
    except ImportError as e:
        if 'torch' in str(e).lower() or 'cuda' in str(e).lower():
            print(f"\nPyTorch/CUDA not available: {e}")
            print("Some benchmarks will be skipped.")
            print("\nTo run full benchmarks, install PyTorch with CUDA:")
            print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        else:
            raise
