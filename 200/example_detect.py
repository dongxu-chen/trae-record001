#!/usr/bin/env python
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.inference import XRayDefectDetector
from src.image_enhancer import ImageEnhancer
from src.defect_3d_reconstruction import MultiViewDefectDetector
from src.defect_report_generator import DefectReportSystem
from src.online_model_updater import OnlineModelUpdater
import cv2
import numpy as np
from datetime import datetime, timedelta


def example_single_image_detection():
    print("\n" + "=" * 60)
    print("Example 1: Single Image Detection with Dynamic Size")
    print("=" * 60)
    
    model_path = "models/xray_defect/weights/best.pt"
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        print("Please train a model first using src/train.py")
        print("Or download a pretrained model")
        return
    
    detector = XRayDefectDetector(
        model_path=model_path,
        use_enhancement=True,
        conf_threshold=0.25,
        iou_threshold=0.45,
        device='0',
        dynamic_size=True,
        min_size=320,
        max_size=1280,
        enhance_mode='adaptive'
    )
    
    test_image = "data/images/test/sample.jpg"
    if not os.path.exists(test_image):
        print(f"Test image not found at {test_image}")
        print("Please add test images to data/images/test/")
        return
    
    print("\nUsing precision mode: 'balanced'")
    result = detector.detect_single_image(
        image_path=test_image,
        output_dir="outputs",
        save_result=True,
        verbose=True,
        target_precision='balanced'
    )
    
    print(f"\nDetection Summary:")
    print(f"  Total defects found: {result['num_detections']}")
    print(f"  Inference time: {result['inference_time_ms']:.2f} ms")
    print(f"  Inference mode: {result['inference_mode']}")
    print(f"  Dynamic size enabled: {result['dynamic_size_enabled']}")
    for cls_name, stats in result['detection_summary']['by_class'].items():
        print(f"  {cls_name}: {stats['count']} defects, avg confidence: {stats['avg_confidence']:.3f}")


def example_image_enhancement():
    print("\n" + "=" * 60)
    print("Example 2: Adaptive CLAHE Image Enhancement")
    print("=" * 60)
    
    test_image = "data/images/test/sample.jpg"
    if not os.path.exists(test_image):
        print(f"Test image not found at {test_image}")
        return
    
    image = cv2.imread(test_image)
    if image is None:
        print(f"Failed to load image: {test_image}")
        return
    
    print("\nEnhancement modes available:")
    print("  1. Standard CLAHE")
    print("  2. Adaptive CLAHE (auto-tuning based on image content)")
    print("  3. Multi-scale CLAHE (fused multiple scales)")
    
    enhancer_standard = ImageEnhancer(use_adaptive_clahe=False, use_multiscale=False)
    enhancer_adaptive = ImageEnhancer(use_adaptive_clahe=True, use_multiscale=False, auto_tune=True)
    enhancer_multiscale = ImageEnhancer(use_adaptive_clahe=True, use_multiscale=True)
    
    print("\nAnalyzing image content for adaptive enhancement...")
    stats = enhancer_adaptive.get_image_stats(image)
    if stats:
        print("  Image statistics:")
        for k, v in stats.items():
            if isinstance(v, float):
                print(f"    {k}: {v:.4f}")
    
    enhanced_standard = enhancer_standard.enhance_xray(image)
    enhanced_adaptive = enhancer_adaptive.enhance_xray(image)
    enhanced_multiscale = enhancer_multiscale.enhance_xray(image)
    
    os.makedirs("outputs", exist_ok=True)
    
    for name, img in [("standard", enhanced_standard), 
                       ("adaptive", enhanced_adaptive), 
                       ("multiscale", enhanced_multiscale)]:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(f"outputs/enhanced_{name}_clahe.jpg", img)
        print(f"\n{name.capitalize()} CLAHE parameters:")
        if name == "adaptive":
            print(f"  - Auto-tuned clip_limit based on contrast and entropy")
            print(f"  - Auto-tuned tile_grid_size based on brightness and dynamic range")
        elif name == "multiscale":
            print(f"  - Scales: (4,4), (8,8), (16,16)")
            print(f"  - Weights: 0.3, 0.5, 0.2")
    
    print("\nEnhanced images saved to outputs/")


def example_batch_detection():
    print("\n" + "=" * 60)
    print("Example 3: Batch Image Detection")
    print("=" * 60)
    
    model_path = "models/xray_defect/weights/best.pt"
    input_dir = "data/images/test"
    output_dir = "outputs/batch_results"
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        return
    
    if not os.path.exists(input_dir):
        print(f"Input directory not found at {input_dir}")
        return
    
    detector = XRayDefectDetector(
        model_path=model_path,
        use_enhancement=True,
        conf_threshold=0.3,
        device='0'
    )
    
    results = detector.detect_batch(
        image_dir=input_dir,
        output_dir=output_dir,
        verbose=True
    )
    
    total_defects = sum(r['num_detections'] for r in results)
    total_time = sum(r['inference_time_ms'] for r in results)
    
    print(f"\nBatch Summary:")
    print(f"  Total images processed: {len(results)}")
    print(f"  Total defects found: {total_defects}")
    print(f"  Total processing time: {total_time:.2f} ms")
    print(f"  Average time per image: {total_time / len(results):.2f} ms")


def example_dynamic_size_inference():
    print("\n" + "=" * 60)
    print("Example 4: Dynamic Size Inference")
    print("=" * 60)
    
    model_path = "models/xray_defect/weights/best.engine"
    
    if not os.path.exists(model_path):
        print(f"TensorRT model not found at {model_path}")
        print("Please export the model first with dynamic shape support:")
        print("  python src/export_tensorrt.py --weights models/xray_defect/weights/best.pt --precision fp16 --dynamic")
        return
    
    test_image = "data/images/test/sample.jpg"
    if not os.path.exists(test_image):
        print(f"Test image not found at {test_image}")
        return
    
    image = cv2.imread(test_image)
    h, w = image.shape[:2]
    print(f"\nOriginal image size: {w}x{h}")
    
    print("\nTesting different precision modes:")
    for mode in ['speed', 'balanced', 'accuracy']:
        print(f"\n  Precision mode: {mode}")
        detector = XRayDefectDetector(
            model_path=model_path,
            use_enhancement=True,
            conf_threshold=0.25,
            iou_threshold=0.45,
            device='0',
            dynamic_size=True,
            min_size=320,
            max_size=1280,
            enhance_mode='adaptive'
        )
        
        result = detector.detect_single_image(
            image_path=test_image,
            output_dir=f"outputs/dynamic_{mode}",
            save_result=True,
            verbose=False,
            target_precision=mode
        )
        
        print(f"    Inference time: {result['inference_time_ms']:.2f} ms")
        print(f"    Defects found: {result['num_detections']}")
    
    print("\nDynamic size inference complete!")


def example_multiscale_inference():
    print("\n" + "=" * 60)
    print("Example 5: Multi-scale Inference with Fusion")
    print("=" * 60)
    
    model_path = "models/xray_defect/weights/best.engine"
    
    if not os.path.exists(model_path):
        print(f"TensorRT model not found at {model_path}")
        return
    
    test_image = "data/images/test/sample.jpg"
    if not os.path.exists(test_image):
        print(f"Test image not found at {test_image}")
        return
    
    detector = XRayDefectDetector(
        model_path=model_path,
        use_enhancement=True,
        conf_threshold=0.25,
        iou_threshold=0.45,
        device='0',
        dynamic_size=True,
        multi_scale=True,
        min_size=320,
        max_size=1280,
        enhance_mode='adaptive'
    )
    
    print("\nMulti-scale inference uses scales: 640, 960, 1280")
    print("Results are fused using weighted NMS to improve recall...")
    
    result = detector.detect_single_image(
        image_path=test_image,
        output_dir="outputs/multiscale",
        save_result=True,
        verbose=True
    )
    
    print(f"\nMulti-scale Detection Complete!")
    print(f"  Inference time: {result['inference_time_ms']:.2f} ms")
    print(f"  Defects found: {result['num_detections']}")
    print(f"  Inference mode: {result['inference_mode']}")


def example_int8_calibration():
    print("\n" + "=" * 60)
    print("Example 6: INT8 Quantization with Calibration")
    print("=" * 60)
    
    print("\nINT8 quantization requires representative calibration samples.")
    print("\nSteps to export INT8 model with calibration:")
    print("\n1. Prepare calibration dataset (representative samples):")
    print("   - Place 300-500 representative X-ray images in data/calib/")
    print("   - Include various brightness, contrast, and defect types")
    
    print("\n2. Run export with INT8 precision:")
    print("   python src/export_tensorrt.py \\"
          "\n     --weights models/xray_defect/weights/best.pt \\"
          "\n     --precision int8 \\"
          "\n     --calib_data data/calib/ \\"
          "\n     --calib_samples 500 \\"
          "\n     --validate \\"
          "\n     --val_data data/images/val/ \\"
          "\n     --dynamic")
    
    print("\n3. Key features:")
    print("   - Automatic dataset analysis (brightness, contrast, aspect ratio)")
    print("   - Multi-scale calibration (320, 640, 1280)")
    print("   - Optional image enhancement during calibration")
    print("   - Post-quantization accuracy validation (FP32 vs INT8)")
    print("   - Precision/recall/mAP drop metrics")
    print("   - Dynamic shape optimization")
    
    print("\n4. After export, run INT8 inference:")
    print("   python src/inference.py --model models/xray_defect/weights/best.engine --input data/images/test/")
    
    print("\nExpected performance:")
    print("   - Speedup: 2-4x over FP32")
    print("   - Model size: ~4x smaller")
    print("   - Accuracy drop: <2% with proper calibration")


def example_tensorrt_inference():
    print("\n" + "=" * 60)
    print("Example 7: TensorRT Inference with Dynamic Shapes")
    print("=" * 60)
    
    model_path = "models/xray_defect/weights/best.engine"
    
    if not os.path.exists(model_path):
        print(f"TensorRT model not found at {model_path}")
        print("Please export the model first using src/export_tensorrt.py")
        print("Example with dynamic shapes and INT8:")
        print("  python src/export_tensorrt.py --weights models/xray_defect/weights/best.pt "
              "--precision int8 --calib_data data/calib/ --dynamic")
        return
    
    detector = XRayDefectDetector(
        model_path=model_path,
        use_enhancement=True,
        conf_threshold=0.25,
        iou_threshold=0.45,
        device='0',
        dynamic_size=True,
        min_size=320,
        max_size=1280,
        enhance_mode='adaptive',
        metadata_path="models/xray_defect_trt_int8_metadata.json"
    )
    
    test_image = "data/images/test/sample.jpg"
    if not os.path.exists(test_image):
        print(f"Test image not found at {test_image}")
        return
    
    result = detector.detect_single_image(
        image_path=test_image,
        output_dir="outputs/tensorrt_results",
        save_result=True,
        verbose=True
    )
    
    print(f"\nTensorRT Detection Complete!")
    print(f"  Inference time: {result['inference_time_ms']:.2f} ms")
    print(f"  Defects found: {result['num_detections']}")
    print(f"  Dynamic size enabled: {result['dynamic_size_enabled']}")


def example_3d_reconstruction():
    print("\n" + "=" * 60)
    print("Example 8: Multi-View 3D Defect Reconstruction")
    print("=" * 60)

    model_path = "models/xray_defect/weights/best.pt"
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        return

    multi_view_dir = "data/images/multi_view"
    if not os.path.exists(multi_view_dir):
        print(f"Multi-view directory not found at {multi_view_dir}")
        print("\nTo use 3D reconstruction:")
        print("1. Create directory: data/images/multi_view")
        print("2. Place 3+ X-ray images of the same object, taken from different angles")
        print("3. Image naming: view_001.jpg, view_002.jpg, view_003.jpg, etc.")
        print("4. Recommended angular range: -15° to +15° for best results")
        print("\n3D reconstruction features:")
        print("  - ORB feature matching for image registration")
        print("  - Parallax-based depth estimation")
        print("  - Defect 3D coordinate reconstruction")
        print("  - Defect size and volume calculation")
        print("  - Multi-view detection result fusion")
        return

    base_detector = XRayDefectDetector(
        model_path=model_path,
        use_enhancement=True,
        conf_threshold=0.25,
        iou_threshold=0.45,
        device='0',
        dynamic_size=True,
        min_size=320,
        max_size=1280,
        enhance_mode='adaptive'
    )

    multi_view_detector = MultiViewDefectDetector(
        detector=base_detector,
        num_views=3,
        angular_range=30.0,
        camera_distance=1000.0
    )

    image_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = []
    for ext in image_ext:
        image_files.extend(sorted(Path(multi_view_dir).glob(f'*{ext}')))

    image_paths = [str(p) for p in image_files[:3]]

    print(f"\nFound {len(image_files)} multi-view images")
    for i, p in enumerate(image_paths):
        print(f"  View {i}: {os.path.basename(p)}")

    print(f"\nCamera parameters:")
    print(f"  Angular range: ±15°")
    print(f"  Camera distance: 1000 mm")
    print(f"  Pixel size: 0.2 mm")

    print("\nRunning 3D reconstruction...")
    result = multi_view_detector.detect_multi_view(
        image_paths=image_paths,
        output_dir="outputs/3d_reconstruction",
        visualize=True
    )

    print(f"\n3D Reconstruction Results:")
    print(f"  Total defects: {result['num_defects_3d']}")
    print(f"  Defects matched across views: {len(result['defects_3d'])}")

    for defect in result['defects_3d']:
        if len(defect.views_detected) >= 2:
            print(f"\n  Defect {defect.id} ({defect.class_name}):")
            print(f"    3D Center: ({defect.center_3d[0]:.1f}, {defect.center_3d[1]:.1f}, {defect.center_3d[2]:.1f}) mm")
            print(f"    Size: {defect.size_3d[0]:.1f} x {defect.size_3d[1]:.1f} x {defect.size_3d[2]:.1f} mm")
            print(f"    Volume: {defect.volume:.1f} mm³")
            print(f"    Depth: {defect.depth:.1f} mm")
            print(f"    Views detected: {defect.views_detected}")

    print("\nOutput files:")
    print(f"  - {result.get('json_path', 'N/A')}")
    print(f"  - {result.get('visualization_path', 'N/A')}")


def example_defect_report():
    print("\n" + "=" * 60)
    print("Example 9: Defect Report Generation")
    print("=" * 60)

    report_system = DefectReportSystem(
        db_path="data/defect_database.json"
    )

    print("\nGenerating some sample data for demonstration...")
    print("(In production, data would come from actual detections)")

    sample_image = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
    sample_detections = [
        {
            'class_id': 0,
            'class_name': 'Porosity',
            'confidence': 0.85,
            'bbox': {'x1': 100, 'y1': 100, 'x2': 120, 'y2': 120,
                     'center_x': 110, 'center_y': 110, 'width': 20, 'height': 20},
            'size_mm': (2.0, 2.0)
        },
        {
            'class_id': 1,
            'class_name': 'Crack',
            'confidence': 0.92,
            'bbox': {'x1': 200, 'y1': 200, 'x2': 280, 'y2': 210,
                     'center_x': 240, 'center_y': 205, 'width': 80, 'height': 10},
            'size_mm': (8.0, 1.0)
        },
        {
            'class_id': 2,
            'class_name': 'Slag Inclusion',
            'confidence': 0.78,
            'bbox': {'x1': 350, 'y1': 150, 'x2': 380, 'y2': 170,
                     'center_x': 365, 'center_y': 160, 'width': 30, 'height': 20},
            'size_mm': (3.0, 2.0)
        }
    ]

    print("\nSample detection data:")
    for det in sample_detections:
        print(f"  {det['class_name']}: confidence={det['confidence']:.2f}")

    report_system.add_detection_results(
        image_path="data/images/test/sample.jpg",
        detections=sample_detections,
        inspection_line='line_1'
    )

    print("\n" + "-" * 60)
    report_system.print_summary(days=30)

    print("\nGenerating HTML report...")
    report_path = report_system.generate_report(
        output_dir="reports",
        time_period_days=30,
        report_format='html'
    )

    if report_path:
        print(f"\nReport generated: {report_path}")
        print("\nReport contents:")
        print("  - Summary cards with key metrics")
        print("  - Defect type distribution (bar chart + pie chart)")
        print("  - Severity distribution analysis")
        print("  - Daily and weekly trend analysis")
        print("  - Detection confidence distribution")
        print("  - Defect size statistics")
        print("  - Recent defects table")
        print("\nTo view the report, open in a web browser.")

    print("\nAlso available: CSV export")
    csv_path = report_system.generate_report(
        output_dir="reports",
        time_period_days=30,
        report_format='csv'
    )
    if csv_path:
        print(f"CSV report: {csv_path}")


def example_online_model_update():
    print("\n" + "=" * 60)
    print("Example 10: Online Model Update")
    print("=" * 60)

    base_model = "models/xray_defect/weights/best.pt"
    
    if not os.path.exists(base_model):
        print(f"Base model not found at {base_model}")
        print("\nTo use online updates:")
        print("1. Train initial model with src/train.py")
        print("2. Configure update policy (min_samples, auto_update, etc.)")
        print("3. Add labeled samples as they become available")
        print("4. System automatically triggers updates when conditions met")
        return

    updater = OnlineModelUpdater(
        base_model_path=base_model,
        buffer_dir="data/sample_buffer",
        model_dir="models/versions",
        device='0'
    )

    print("\nCurrent update status:")
    updater.print_status()

    print("\n" + "-" * 60)
    print("Simulating sample accumulation...")
    print("(In production, samples would come from manual labeling)")

    sample_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    sample_bboxes = [
        {'x1': 100, 'y1': 100, 'x2': 130, 'y2': 130},
        {'x1': 250, 'y1': 200, 'x2': 290, 'y2': 220},
        {'x1': 400, 'y1': 300, 'x2': 440, 'y2': 330}
    ]
    class_ids = [0, 1, 2]
    class_names = ['Porosity', 'Crack', 'Slag Inclusion']

    for i, (bbox, cls, name) in enumerate(zip(sample_bboxes, class_ids, class_names)):
        sample = updater.add_manual_label(
            image=sample_image,
            bbox=bbox,
            class_id=cls,
            class_name=name
        )
        if sample:
            print(f"  Added sample {i+1}: {name}")

    print("\n" + "-" * 60)
    print("Update policy configuration:")
    print("  min_samples_for_update: 50")
    print("  max_samples_per_update: 500")
    print("  min_days_between_updates: 7")
    print("  min_improvement_threshold: 0.02")
    print("  class_balancing: True")
    print("  hard_negative_mining: True")

    print("\n" + "-" * 60)
    print("Update process:")
    print("1. Collect labeled samples until threshold reached")
    print("2. Balance classes and select hard samples")
    print("3. Export to YOLO dataset format (80/20 train/val split)")
    print("4. Incremental fine-tuning (freeze first 10 layers)")
    print("5. Validate mAP improvement against threshold")
    print("6. If improvement > 2%, save new model version")
    print("7. Mark samples as used in training")

    print("\n" + "-" * 60)
    print("Model version management:")
    print("  - Auto-versioning with timestamps")
    print("  - Keep last 10 active versions")
    print("  - Support rollback to previous versions")
    print("  - Track training metrics and sample counts")

    print("\nChecking update status again...")
    updater.print_status()

    print("\n" + "-" * 60)
    print("To trigger update manually:")
    print("  python src/main.py --mode update_model --base_model models/xray_defect/weights/best.pt --force_update")
    print("\nTo check update status:")
    print("  python src/main.py --mode update_status")
    print("\nTo rollback to previous version:")
    print("  python src/main.py --mode update_model --rollback_version v20240501_120000")


def main():
    print("\n" + "#" * 60)
    print("# X-ray Defect Detection - Usage Examples (Complete)")
    print("#" * 60)
    
    print("\nAvailable examples:")
    print("  1. Single Image Detection with Dynamic Size")
    print("  2. Adaptive CLAHE Image Enhancement")
    print("  3. Batch Detection")
    print("  4. Dynamic Size Inference (speed/balanced/accuracy)")
    print("  5. Multi-scale Inference with Fusion")
    print("  6. INT8 Quantization with Calibration Guide")
    print("  7. TensorRT Inference with Dynamic Shapes")
    print("  8. Multi-View 3D Defect Reconstruction")
    print("  9. Defect Report Generation")
    print(" 10. Online Model Update")
    print(" 11. Run All Examples")
    
    choice = input("\nEnter example number (1-11): ").strip()
    
    if choice == '1':
        example_single_image_detection()
    elif choice == '2':
        example_image_enhancement()
    elif choice == '3':
        example_batch_detection()
    elif choice == '4':
        example_dynamic_size_inference()
    elif choice == '5':
        example_multiscale_inference()
    elif choice == '6':
        example_int8_calibration()
    elif choice == '7':
        example_tensorrt_inference()
    elif choice == '8':
        example_3d_reconstruction()
    elif choice == '9':
        example_defect_report()
    elif choice == '10':
        example_online_model_update()
    elif choice == '11':
        example_image_enhancement()
        example_single_image_detection()
        example_batch_detection()
        example_dynamic_size_inference()
        example_multiscale_inference()
        example_int8_calibration()
        example_tensorrt_inference()
        example_3d_reconstruction()
        example_defect_report()
        example_online_model_update()
    else:
        print("Invalid choice. Running adaptive CLAHE demo...")
        example_image_enhancement()
    
    print("\n" + "#" * 60)
    print("# Example Complete!")
    print("#" * 60 + "\n")


if __name__ == '__main__':
    main()
