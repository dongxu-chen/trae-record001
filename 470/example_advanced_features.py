import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import cv2
from config import Config
from core import SaliencyInferencer, BatchProcessor
from core import guided_edge_refinement, refine_edges
from core import GPUMemoryMonitor, process_with_dynamic_batch
from utils import save_image

Config.ensure_dirs()


def create_test_images(num_images=5):
    print(f"Creating {num_images} test images...")
    images = []
    for i in range(num_images):
        img = np.zeros((300, 400, 3), dtype=np.uint8)
        bg_color = np.random.randint(50, 150, 3)
        img[:] = bg_color
        
        for _ in range(np.random.randint(1, 4)):
            obj_color = np.random.randint(180, 255, 3)
            center = (np.random.randint(80, 320), np.random.randint(80, 220))
            radius = np.random.randint(30, 80)
            cv2.circle(img, center, radius, tuple(int(c) for c in obj_color), -1)
        
        images.append(img)
        print(f"  Created test image {i+1}")
    
    return images


def example_tensorrt_acceleration():
    print("\n" + "=" * 60)
    print("EXAMPLE 1: TensorRT Acceleration")
    print("=" * 60)
    
    test_img = create_test_images(1)[0]
    
    print("\n1. Initialize inferencer with PyTorch...")
    inferencer_pytorch = SaliencyInferencer(
        model_name='basnet',
        pretrained=False,
        use_tensorrt=False
    )
    print(f"   Engine: {inferencer_pytorch.get_model_info()['engine']}")
    
    print("\n2. Run inference with PyTorch...")
    result_pytorch = inferencer_pytorch.predict(
        test_img,
        refine_method='guided',
        measure_time=True
    )
    stats_pytorch = result_pytorch['stats']
    print(f"   Inference time: {stats_pytorch['inference_time_ms']:.1f} ms")
    print(f"   Total time: {stats_pytorch['total_time_ms']:.1f} ms")
    print(f"   Meets target (<=50ms): {stats_pytorch['meets_target']}")
    
    print("\n3. Check for TensorRT engine...")
    trt_path = Config.BASNET_TRT
    if os.path.exists(trt_path):
        print(f"   Found TensorRT engine: {trt_path}")
        
        print("\n4. Initialize inferencer with TensorRT...")
        inferencer_trt = SaliencyInferencer(
            model_name='basnet',
            pretrained=False,
            use_tensorrt=True
        )
        print(f"   Engine: {inferencer_trt.get_model_info()['engine']}")
        
        if inferencer_trt.use_tensorrt:
            print("\n5. Run inference with TensorRT...")
            result_trt = inferencer_trt.predict(
                test_img,
                refine_method='guided',
                measure_time=True
            )
            stats_trt = result_trt['stats']
            print(f"   Inference time: {stats_trt['inference_time_ms']:.1f} ms")
            print(f"   Total time: {stats_trt['total_time_ms']:.1f} ms")
            print(f"   Meets target (<=50ms): {stats_trt['meets_target']}")
            
            speedup = stats_pytorch['inference_time_ms'] / stats_trt['inference_time_ms']
            print(f"\n   Speedup: {speedup:.2f}x")
        else:
            print("   TensorRT not available, using PyTorch")
    else:
        print(f"   TensorRT engine not found at: {trt_path}")
        print("\n   To convert model to TensorRT, run:")
        print("     python convert_to_tensorrt.py --model basnet")
    
    return inferencer_pytorch


def example_guided_filter_refinement():
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Guided Filter Edge Refinement")
    print("=" * 60)
    
    test_img = create_test_images(1)[0]
    
    inferencer = SaliencyInferencer(
        model_name='basnet',
        pretrained=False,
        use_tensorrt=False
    )
    
    print("\n1. Run inference with morphological refinement...")
    result_morph = inferencer.predict(
        test_img,
        edge_refinement=True,
        refine_method='morph',
        measure_time=True
    )
    print(f"   Refinement time: {result_morph['stats']['postprocess_time_ms']:.1f} ms")
    
    print("\n2. Run inference with guided filter refinement...")
    result_guided = inferencer.predict(
        test_img,
        edge_refinement=True,
        refine_method='guided',
        measure_time=True
    )
    print(f"   Refinement time: {result_guided['stats']['postprocess_time_ms']:.1f} ms")
    
    print("\n3. Compare edge quality...")
    mask_morph = result_morph['binary_mask']
    mask_guided = result_guided['binary_mask']
    
    contours_morph, _ = cv2.findContours(
        mask_morph.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    contours_guided, _ = cv2.findContours(
        mask_guided.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    print(f"   Morphological - Number of contours: {len(contours_morph)}")
    if contours_morph:
        smoothness_morph = np.mean([cv2.arcLength(c, True) for c in contours_morph])
        print(f"   Morphological - Avg contour length: {smoothness_morph:.1f}")
    
    print(f"   Guided filter - Number of contours: {len(contours_guided)}")
    if contours_guided:
        smoothness_guided = np.mean([cv2.arcLength(c, True) for c in contours_guided])
        print(f"   Guided filter - Avg contour length: {smoothness_guided:.1f}")
    
    print("\n4. Save comparison results...")
    output_dir = os.path.join(Config.OUTPUT_DIR, 'guided_filter_demo')
    os.makedirs(output_dir, exist_ok=True)
    
    save_image(test_img, os.path.join(output_dir, 'original.png'))
    save_image((result_morph['saliency_map'] * 255).astype(np.uint8), 
               os.path.join(output_dir, 'saliency_morph.png'))
    save_image((result_guided['saliency_map'] * 255).astype(np.uint8),
               os.path.join(output_dir, 'saliency_guided.png'))
    save_image((mask_morph * 255).astype(np.uint8),
               os.path.join(output_dir, 'mask_morph.png'))
    save_image((mask_guided * 255).astype(np.uint8),
               os.path.join(output_dir, 'mask_guided.png'))
    
    print(f"   Results saved to: {output_dir}")
    
    return result_guided


def example_dynamic_batch_processing():
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Dynamic Batch Processing")
    print("=" * 60)
    
    num_images = 10
    print(f"\n1. Creating {num_images} test images...")
    test_images = create_test_images(num_images)
    
    inferencer = SaliencyInferencer(
        model_name='basnet',
        pretrained=False,
        use_tensorrt=False
    )
    
    print("\n2. Monitor GPU memory...")
    memory_monitor = GPUMemoryMonitor()
    mem_info = memory_monitor.get_memory_info()
    print(f"   Total memory: {mem_info.total / (1024**3):.1f} GB")
    print(f"   Available: {mem_info.available / (1024**3):.1f} GB")
    print(f"   Memory utilization: {mem_info.utilization * 100:.1f}%")
    
    print("\n3. Processing with dynamic batching...")
    
    def process_batch(batch):
        return inferencer.predict_batch(
            batch,
            edge_refinement=True,
            refine_method='guided',
            dynamic_batch=False
        )
    
    results, stats = process_with_dynamic_batch(
        test_images,
        process_func=process_batch,
        initial_batch_size=Config.BATCH_SIZE,
        min_batch_size=1,
        max_batch_size=Config.MAX_BATCH_SIZE,
        show_progress=True
    )
    
    print(f"\n4. Dynamic batch processing complete!")
    print(f"   Total images: {stats.total_items}")
    print(f"   Successful: {stats.processed_items}")
    print(f"   Failed: {stats.failed_items}")
    print(f"   Total time: {stats.total_time:.2f} s")
    print(f"   Avg time per image: {stats.avg_time_per_item * 1000:.1f} ms")
    print(f"   Peak memory: {stats.memory_peak * 100:.1f}%")
    
    if stats.batch_size_history:
        print(f"\n   Batch size history: {stats.batch_size_history}")
        print(f"   Batch size range: {min(stats.batch_size_history)} - {max(stats.batch_size_history)}")
        print(f"   Average batch size: {sum(stats.batch_size_history)/len(stats.batch_size_history):.1f}")
    
    print("\n5. Processing with fixed batch size (for comparison)...")
    start_time = cv2.getTickCount()
    results_fixed = inferencer.predict_batch(
        test_images,
        edge_refinement=True,
        refine_method='guided',
        dynamic_batch=False
    )
    fixed_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency()
    
    print(f"   Fixed batch ({Config.BATCH_SIZE}) time: {fixed_time:.2f} s")
    print(f"   Dynamic batch time: {stats.total_time:.2f} s")
    
    if stats.total_time < fixed_time:
        speedup = fixed_time / stats.total_time
        print(f"   Dynamic batch is {speedup:.2f}x faster!")
    else:
        slowdown = stats.total_time / fixed_time
        print(f"   Fixed batch is {slowdown:.2f}x faster (small dataset)")
    
    return results


def example_full_pipeline():
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Full Pipeline with All Optimizations")
    print("=" * 60)
    
    num_images = 5
    print(f"\n1. Creating {num_images} test images...")
    test_images = create_test_images(num_images)
    
    print("\n2. Initializing inferencer with all optimizations...")
    inferencer = SaliencyInferencer(
        model_name='basnet',
        pretrained=False,
        use_tensorrt=Config.USE_TENSORRT,
        use_dynamic_batch=True
    )
    
    info = inferencer.get_model_info()
    print(f"   Model: {info['current_model']}")
    print(f"   Engine: {info['engine']}")
    print(f"   Device: {info['device']}")
    print(f"   Target inference time: {info['target_inference_time_ms']} ms")
    
    print("\n3. Running full pipeline with dynamic batch...")
    print(f"   - TensorRT acceleration: {'ON' if inferencer.use_tensorrt else 'OFF'}")
    print(f"   - Guided filter refinement: ON")
    print(f"   - Dynamic batch processing: ON")
    
    batch_processor = BatchProcessor(inferencer)
    
    input_dir = os.path.join(Config.INPUT_DIR, 'pipeline_demo')
    output_dir = os.path.join(Config.OUTPUT_DIR, 'pipeline_demo')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    for i, img in enumerate(test_images):
        save_image(img, os.path.join(input_dir, f'image_{i:02d}.png'))
    
    result = batch_processor.process_directory(
        input_dir=input_dir,
        output_dir=output_dir,
        use_dynamic_batch=True,
        refine_method='guided',
        save_segmented=True,
        save_overlay=True
    )
    
    print(f"\n4. Pipeline complete!")
    print(f"   Total images processed: {result['total_images']}")
    print(f"   Output directory: {result['output_dir']}")
    
    if 'dynamic_stats' in result:
        ds = result['dynamic_stats']
        print(f"   Dynamic batch stats:")
        print(f"     Total time: {ds['total_time']:.2f} s")
        print(f"     Avg per image: {ds['avg_time_per_item'] * 1000:.1f} ms")
    
    print("\n5. Results summary:")
    for i, item in enumerate(result['results']):
        print(f"   Image {i+1}: {item['filename']}")
        print(f"     Mean saliency: {item['stats']['mean_saliency']:.4f}")
        print(f"     Mask area: {item['stats']['mask_area_ratio']:.2%}")
        if 'segmentation' in item:
            print(f"     Objects detected: {item['segmentation']['num_objects']}")
    
    return result


def main():
    print("=" * 60)
    print("Advanced Features Demo")
    print("=" * 60)
    print("\nAvailable examples:")
    print("  1. TensorRT Acceleration (target: <=50ms inference)")
    print("  2. Guided Filter Edge Refinement (sharp edges)")
    print("  3. Dynamic Batch Processing (OOM-safe)")
    print("  4. Full Pipeline (all optimizations)")
    print("  5. Run all examples")
    
    choice = input("\nSelect example to run (1-5): ").strip()
    
    if choice == '1':
        example_tensorrt_acceleration()
    elif choice == '2':
        example_guided_filter_refinement()
    elif choice == '3':
        example_dynamic_batch_processing()
    elif choice == '4':
        example_full_pipeline()
    elif choice == '5':
        example_tensorrt_acceleration()
        example_guided_filter_refinement()
        example_dynamic_batch_processing()
        example_full_pipeline()
    else:
        print("Invalid choice")
        return
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except ImportError as e:
        if 'torch' in str(e).lower():
            print(f"\nPyTorch not available: {e}")
            print("\nPlease install PyTorch to run these examples:")
            print("  pip install torch torchvision")
        else:
            raise
