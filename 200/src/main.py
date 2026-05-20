import os
import sys
import argparse
from pathlib import Path
import json
import time
import numpy as np
import cv2
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from src.image_enhancer import ImageEnhancer
from src.inference import XRayDefectDetector
from src.defect_3d_reconstruction import MultiViewDefectDetector
from src.defect_report_generator import DefectReportSystem
from src.online_model_updater import OnlineModelUpdater


def parse_args():
    parser = argparse.ArgumentParser(description='X-ray Defect Detection - Complete Pipeline')
    parser.add_argument('--mode', type=str, default='detect',
                        choices=['detect', 'enhance', 'benchmark', 'info',
                                 'detect_3d', 'report', 'update_model', 'update_status'],
                        help='operation mode')
    parser.add_argument('--model', type=str, default=None, help='model path')
    parser.add_argument('--input', type=str, default=None, help='input image or directory')
    parser.add_argument('--output', type=str, default='../outputs', help='output directory')
    parser.add_argument('--conf', type=float, default=0.25, help='confidence threshold')
    parser.add_argument('--iou', type=float, default=0.45, help='NMS IOU threshold')
    parser.add_argument('--device', type=str, default='0', help='cuda device')
    parser.add_argument('--no_enhance', action='store_true', help='disable image enhancement')
    parser.add_argument('--enhance_mode', type=str, default='adaptive',
                        choices=['standard', 'adaptive', 'multiscale'], help='enhancement mode')
    parser.add_argument('--imgsz', type=int, default=None, help='fixed inference size')
    parser.add_argument('--min_imgsz', type=int, default=320, help='minimum image size for dynamic')
    parser.add_argument('--max_imgsz', type=int, default=1280, help='maximum image size for dynamic')
    parser.add_argument('--no_dynamic', action='store_true', help='disable dynamic size adjustment')
    parser.add_argument('--multi_scale', action='store_true', help='enable multi-scale inference')
    parser.add_argument('--precision_mode', type=str, default='balanced',
                        choices=['speed', 'balanced', 'accuracy'], help='target precision mode')
    parser.add_argument('--metadata', type=str, default=None, help='model metadata path')
    parser.add_argument('--iterations', type=int, default=100, help='benchmark iterations')
    parser.add_argument('--verbose', action='store_true', help='verbose output')
    parser.add_argument('--num_views', type=int, default=3, help='number of views for 3D reconstruction')
    parser.add_argument('--angular_range', type=float, default=30.0, help='angular range for 3D (degrees)')
    parser.add_argument('--camera_distance', type=float, default=1000.0, help='camera distance for 3D (mm)')
    parser.add_argument('--report_format', type=str, default='html',
                        choices=['html', 'csv'], help='report format')
    parser.add_argument('--report_days', type=int, default=30, help='report time period (days)')
    parser.add_argument('--db_path', type=str, default=None, help='database path for reports')
    parser.add_argument('--force_update', action='store_true', help='force model update')
    parser.add_argument('--base_model', type=str, default=None, help='base model for online update')
    parser.add_argument('--rollback_version', type=str, default=None, help='version to rollback to')
    parser.add_argument('--inspection_line', type=str, default='line_1', help='inspection line ID')
    return parser.parse_args()


def print_info():
    print("\n" + "=" * 60)
    print("X射线图像缺陷检测系统")
    print("X-ray Image Defect Detection System")
    print("=" * 60)
    print("\n功能模块:")
    print("  1. 图像增强 (Image Enhancement)")
    print("     - 自适应CLAHE (Adaptive CLAHE) - 默认")
    print("     - 多尺度CLAHE (Multi-scale CLAHE)")
    print("     - 标准CLAHE (Standard CLAHE)")
    print("     - 对比度拉伸 (Contrast Stretching)")
    print("     - 非锐化掩膜 (Unsharp Mask)")
    print("     - 自适应Gamma校正")
    print("\n  2. 数据增强 (Data Augmentation)")
    print("     - 几何变换 (翻转、旋转、缩放)")
    print("     - 光度变换 (亮度、对比度、噪声)")
    print("     - Mosaic & CutMix")
    print("\n  3. 缺陷检测 (Defect Detection)")
    print("     - 气孔 (Porosity)")
    print("     - 裂纹 (Crack)")
    print("     - 夹渣 (Slag Inclusion)")
    print("\n  4. 动态尺寸推理 (Dynamic Size Inference)")
    print("     - 自适应尺寸选择 (320-1280px)")
    print("     - 多尺度推理融合")
    print("     - 精度模式选择 (speed/balanced/accuracy)")
    print("\n  5. 模型量化与校准 (Model Quantization)")
    print("     - INT8量化校准 (使用代表样本)")
    print("     - 精度验证 (FP32 vs INT8对比)")
    print("     - 动态尺寸优化配置")
    print("\n  6. 缺陷三维定位 (3D Defect Reconstruction)")
    print("     - 多角度图像配准 (ORB特征匹配)")
    print("     - 视差深度估计 (Parallax Depth Estimation)")
    print("     - 3D坐标重建 (3D Coordinate Reconstruction)")
    print("     - 缺陷尺寸与体积计算")
    print("     - 多视图检测结果融合")
    print("\n  7. 缺陷分类报告 (Defect Report Generation)")
    print("     - 缺陷类型频率统计")
    print("     - 严重程度分布分析")
    print("     - 时间趋势分析 (日/周趋势)")
    print("     - HTML可视化报告 (图表+表格)")
    print("     - CSV数据导出")
    print("\n  8. 模型在线更新 (Online Model Update)")
    print("     - 标注样本累积管理")
    print("     - 类别平衡与困难样本挖掘")
    print("     - 增量微调训练 (冻结前10层)")
    print("     - 模型版本管理与回滚")
    print("     - 自动更新触发机制")
    print("\n  9. 模型部署 (Model Deployment)")
    print("     - PyTorch (.pt)")
    print("     - ONNX (.onnx)")
    print("     - TensorRT (.engine) - FP32/FP16/INT8")
    print("     - 动态形状支持 (Dynamic Shapes)")
    print("\n支持的模型架构:")
    print("  - YOLOv8n (nano)")
    print("  - YOLOv8s (small)")
    print("  - YOLOv8m (medium)")
    print("  - YOLOv8l (large)")
    print("  - YOLOv8x (xlarge)")
    print("\n技术栈:")
    print("  - Ultralytics YOLOv8")
    print("  - OpenCV")
    print("  - CUDA / TensorRT")
    print("  - Albumentations")
    print("\n运行模式:")
    print("  detect       - 标准缺陷检测")
    print("  detect_3d    - 多角度3D缺陷检测")
    print("  enhance      - 图像增强")
    print("  report       - 生成检测报告")
    print("  update_model - 模型增量更新")
    print("  update_status - 查看更新状态")
    print("  benchmark    - 模型性能基准")
    print("  info         - 显示系统信息")
    print("\n" + "=" * 60 + "\n")


def enhance_images(input_path: str, output_dir: str, enhance_mode: str = 'adaptive', verbose: bool = True):
    use_adaptive = (enhance_mode in ['adaptive', 'multiscale'])
    use_multiscale = (enhance_mode == 'multiscale')
    
    enhancer = ImageEnhancer(
        use_adaptive_clahe=use_adaptive,
        use_multiscale=use_multiscale,
        auto_tune=True
    )
    
    print(f"\nEnhancement mode: {enhance_mode}")
    print(f"  Adaptive CLAHE: {'Enabled' if use_adaptive else 'Disabled'}")
    print(f"  Multi-scale CLAHE: {'Enabled' if use_multiscale else 'Disabled'}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    if os.path.isfile(input_path):
        image = cv2.imread(input_path)
        if image is None:
            print(f"Error: Could not load image {input_path}")
            return
        
        if verbose:
            stats = enhancer.get_image_stats(image)
            if stats:
                print(f"\nImage statistics:")
                for k, v in stats.items():
                    if isinstance(v, float):
                        print(f"  {k}: {v:.4f}")
        
        enhanced = enhancer.enhance_xray(image)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_dir, f'{base_name}_enhanced_{enhance_mode}.jpg')
        
        if len(enhanced.shape) == 2:
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            cv2.imwrite(output_path, enhanced_bgr)
        else:
            cv2.imwrite(output_path, enhanced)
        
        if verbose:
            print(f"\nEnhanced image saved to: {output_path}")
    
    elif os.path.isdir(input_path):
        image_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        image_files = []
        for ext in image_ext:
            image_files.extend(Path(input_path).glob(f'*{ext}'))
        
        print(f"\nFound {len(image_files)} images to enhance")
        
        for i, img_path in enumerate(image_files, 1):
            if verbose:
                print(f"[{i}/{len(image_files)}] Enhancing: {img_path.name}")
            
            image = cv2.imread(str(img_path))
            if image is None:
                print(f"  Warning: Could not load {img_path}")
                continue
            
            enhanced = enhancer.enhance_xray(image)
            base_name = os.path.splitext(img_path.name)[0]
            output_path = os.path.join(output_dir, f'{base_name}_enhanced_{enhance_mode}.jpg')
            
            if len(enhanced.shape) == 2:
                enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
                cv2.imwrite(output_path, enhanced_bgr)
            else:
                cv2.imwrite(output_path, enhanced)
        
        print(f"\nAll enhanced images saved to: {output_dir}")


def benchmark_model(model_path: str, imgsz: int = 640, batch: int = 1,
                    iterations: int = 100, device: str = '0') -> Dict[str, Any]:
    from ultralytics import YOLO
    import torch
    
    print("\n" + "=" * 60)
    print(f"Benchmarking Model: {model_path}")
    print("=" * 60)
    
    if not os.path.exists(model_path):
        print(f"Error: Model not found: {model_path}")
        return {}
    
    model = YOLO(model_path)
    
    if torch.cuda.is_available():
        dummy_input = torch.randn(batch, 3, imgsz, imgsz).cuda()
    else:
        dummy_input = torch.randn(batch, 3, imgsz, imgsz)
    
    print("Warming up...")
    for _ in range(10):
        _ = model(dummy_input, verbose=False)
    
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    
    print(f"Running {iterations} iterations...")
    start_time = time.time()
    
    for _ in range(iterations):
        _ = model(dummy_input, verbose=False)
    
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    avg_time_ms = (total_time / iterations) * 1000
    fps = batch * iterations / total_time
    
    model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print("Benchmark Results")
    print("=" * 60)
    print(f"Model: {model_path}")
    print(f"Model size: {model_size_mb:.2f} MB")
    print(f"Image size: {imgsz}x{imgsz}")
    print(f"Batch size: {batch}")
    print(f"Average inference time: {avg_time_ms:.2f} ms")
    print(f"Throughput: {fps:.2f} FPS")
    print(f"Total time for {iterations} iterations: {total_time:.2f} s")
    print("=" * 60 + "\n")
    
    return {
        'model_path': model_path,
        'model_size_mb': model_size_mb,
        'image_size': imgsz,
        'batch_size': batch,
        'avg_time_ms': avg_time_ms,
        'fps': fps,
        'device': device
    }


def detect_3d(args):
    if not args.model or not args.input:
        print("Error: --model and --input are required for detect_3d mode")
        sys.exit(1)

    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"Error: --input must be a directory containing {args.num_views} view images")
        sys.exit(1)

    image_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_files = []
    for ext in image_ext:
        image_files.extend(sorted(Path(input_dir).glob(f'*{ext}')))

    if len(image_files) < args.num_views:
        print(f"Error: Found {len(image_files)} images, but {args.num_views} views are required")
        sys.exit(1)

    image_paths = [str(p) for p in image_files[:args.num_views]]
    print(f"Using {args.num_views} views for 3D reconstruction:")
    for i, p in enumerate(image_paths):
        print(f"  View {i}: {os.path.basename(p)}")

    use_multiscale_clahe = (args.enhance_mode == 'multiscale')
    enhance_mode = 'adaptive' if args.enhance_mode in ['adaptive', 'multiscale'] else 'standard'

    base_detector = XRayDefectDetector(
        model_path=args.model,
        use_enhancement=not args.no_enhance,
        conf_threshold=args.conf,
        iou_threshold=args.iou,
        device=args.device,
        imgsz=args.imgsz,
        dynamic_size=not args.no_dynamic and args.imgsz is None,
        multi_scale=args.multi_scale,
        min_size=args.min_imgsz,
        opt_size=args.imgsz or 640,
        max_size=args.max_imgsz,
        metadata_path=args.metadata,
        enhance_mode=enhance_mode,
        use_multiscale_clahe=use_multiscale_clahe
    )

    multi_view_detector = MultiViewDefectDetector(
        detector=base_detector,
        num_views=args.num_views,
        angular_range=args.angular_range,
        camera_distance=args.camera_distance
    )

    result = multi_view_detector.detect_multi_view(
        image_paths=image_paths,
        output_dir=args.output,
        visualize=True
    )

    return result


def generate_report(args):
    db_path = args.db_path or os.path.join("data", "defect_database.json")
    report_system = DefectReportSystem(db_path=db_path)

    print(f"\nGenerating report for last {args.report_days} days...")
    print(f"Database: {db_path}")
    print(f"Format: {args.report_format}")

    report_system.print_summary(days=args.report_days)

    report_path = report_system.generate_report(
        output_dir=args.output,
        time_period_days=args.report_days,
        report_format=args.report_format
    )

    if report_path:
        print(f"\nReport generated: {report_path}")
    else:
        print("\nNo data available for the specified period")


def update_model_online(args):
    base_model = args.base_model or args.model
    if not base_model:
        print("Error: --base_model or --model is required for update_model mode")
        sys.exit(1)

    updater = OnlineModelUpdater(
        base_model_path=base_model,
        device=args.device
    )

    if args.rollback_version:
        print(f"Rolling back to version: {args.rollback_version}")
        version = updater.rollback_model(args.rollback_version)
        if version:
            print(f"Rollback successful! Current version: {version.version}")
        return

    print("\nChecking update status...")
    updater.print_status()

    if args.mode == 'update_status':
        print("\nModel version history:")
        history = updater.get_model_history()
        for entry in history[:5]:
            print(f"\n  {entry['version']} ({entry['timestamp']})")
            print(f"    Samples: {entry['num_samples']}, Status: {entry['status']}")
            if entry['metrics']:
                print(f"    mAP@0.5: {entry['metrics'].get('map50', 'N/A'):.4f}")
        return

    if args.force_update:
        print("\nForcing model update...")
        new_version = updater.perform_update()
    else:
        print("\nAttempting model update...")
        new_version = updater.check_and_update()

    if new_version:
        print(f"\nModel updated successfully! New version: {new_version.version}")
        print(f"Model path: {new_version.model_path}")
        print("Metrics:")
        for k, v in new_version.metrics.items():
            print(f"  {k}: {v:.4f}")
    else:
        print("\nModel update was not performed or failed")


def main():
    args = parse_args()
    
    os.chdir(Path(__file__).parent)
    
    if args.mode == 'info':
        print_info()
        return
    
    if args.mode == 'enhance':
        if not args.input:
            print("Error: --input is required for enhance mode")
            sys.exit(1)
        enhance_images(args.input, args.output, args.enhance_mode, args.verbose)
        return
    
    if args.mode == 'benchmark':
        if not args.model:
            print("Error: --model is required for benchmark mode")
            sys.exit(1)
        benchmark_model(args.model, iterations=args.iterations, device=args.device)
        return
    
    if args.mode == 'detect_3d':
        detect_3d(args)
        return
    
    if args.mode == 'report':
        generate_report(args)
        return
    
    if args.mode in ['update_model', 'update_status']:
        update_model_online(args)
        return
    
    if args.mode == 'detect':
        if not args.model or not args.input:
            print("Error: --model and --input are required for detect mode")
            sys.exit(1)
        
        use_multiscale_clahe = (args.enhance_mode == 'multiscale')
        enhance_mode = 'adaptive' if args.enhance_mode in ['adaptive', 'multiscale'] else 'standard'
        
        detector = XRayDefectDetector(
            model_path=args.model,
            use_enhancement=not args.no_enhance,
            conf_threshold=args.conf,
            iou_threshold=args.iou,
            device=args.device,
            imgsz=args.imgsz,
            dynamic_size=not args.no_dynamic and args.imgsz is None,
            multi_scale=args.multi_scale,
            min_size=args.min_imgsz,
            opt_size=args.imgsz or 640,
            max_size=args.max_imgsz,
            metadata_path=args.metadata,
            enhance_mode=enhance_mode,
            use_multiscale_clahe=use_multiscale_clahe
        )
        
        if os.path.isdir(args.input):
            results = detector.detect_batch(
                args.input, args.output, verbose=args.verbose,
                target_precision=args.precision_mode
            )
            
            try:
                db_path = args.db_path or os.path.join("data", "defect_database.json")
                report_system = DefectReportSystem(db_path=db_path)
                
                for img_path, result in zip(sorted(Path(args.input).glob('*')), results):
                    if result and 'detections' in result:
                        for det in result['detections']:
                            report_system.add_detection_results(
                                image_path=str(img_path),
                                detections=[det],
                                inspection_line=args.inspection_line
                            )
                print("Detection results saved to database")
            except Exception as e:
                print(f"Warning: Could not save to database: {e}")

        elif os.path.isfile(args.input):
            result = detector.detect_single_image(
                args.input, args.output, verbose=args.verbose,
                target_precision=args.precision_mode
            )
            
            try:
                db_path = args.db_path or os.path.join("data", "defect_database.json")
                report_system = DefectReportSystem(db_path=db_path)
                if result and 'detections' in result:
                    report_system.add_detection_results(
                        image_path=args.input,
                        detections=result['detections'],
                        inspection_line=args.inspection_line
                    )
            except Exception as e:
                print(f"Warning: Could not save to database: {e}")
        else:
            print(f"Error: Input path not found: {args.input}")
            sys.exit(1)


if __name__ == '__main__':
    main()
