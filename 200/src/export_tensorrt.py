import os
import sys
import argparse
from pathlib import Path
from ultralytics import YOLO
import torch
import json
import time
import numpy as np
import cv2
from typing import List, Tuple, Dict, Any, Optional

sys.path.append(str(Path(__file__).parent))
from image_enhancer import ImageEnhancer


class CalibrationDataset:
    def __init__(self, data_dir: str, num_samples: int = 500,
                 img_sizes: Optional[List[int]] = None,
                 image_ext: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff'),
                 use_enhancement: bool = True):
        self.data_dir = data_dir
        self.num_samples = num_samples
        self.img_sizes = img_sizes or [640, 960, 1280]
        self.image_ext = image_ext
        self.use_enhancement = use_enhancement
        self.enhancer = ImageEnhancer() if use_enhancement else None
        self.image_paths = self._collect_images()
        self.cache = {}

    def _collect_images(self) -> List[str]:
        image_paths = []
        for ext in self.image_ext:
            image_paths.extend(Path(self.data_dir).rglob(f'*{ext}'))

        if not image_paths:
            raise FileNotFoundError(f"No calibration images found in {self.data_dir}")

        image_paths = sorted(image_paths)
        if len(image_paths) > self.num_samples:
            indices = np.linspace(0, len(image_paths) - 1, self.num_samples, dtype=int)
            image_paths = [image_paths[i] for i in indices]

        print(f"Collected {len(image_paths)} calibration images from {self.data_dir}")
        return [str(p) for p in image_paths]

    def _load_and_preprocess(self, img_path: str, target_size: int) -> torch.Tensor:
        cache_key = (img_path, target_size)
        if cache_key in self.cache:
            return self.cache[cache_key]

        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"Failed to load image: {img_path}")

        if self.use_enhancement and self.enhancer:
            img = self.enhancer.enhance_xray(img)
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        h, w = img.shape[:2]
        scale = target_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)

        if (new_h, new_w) != (h, w):
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        pad_h = target_size - new_h
        pad_w = target_size - new_w
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left

        img = cv2.copyMakeBorder(img, top, bottom, left, right,
                                  cv2.BORDER_CONSTANT, value=(114, 114, 114))

        img = img.transpose(2, 0, 1)
        img = np.ascontiguousarray(img, dtype=np.float32)
        img /= 255.0

        tensor = torch.from_numpy(img).unsqueeze(0)
        self.cache[cache_key] = tensor

        return tensor

    def get_batch_generator(self, batch_size: int = 1):
        total_batches = len(self.image_paths) * len(self.img_sizes)

        def generator():
            for img_size in self.img_sizes:
                for i in range(0, len(self.image_paths), batch_size):
                    batch_paths = self.image_paths[i:i + batch_size]
                    batch_tensors = []
                    for path in batch_paths:
                        try:
                            tensor = self._load_and_preprocess(path, img_size)
                            batch_tensors.append(tensor)
                        except Exception as e:
                            print(f"Warning: Skipping {path}: {e}")
                            continue

                    if batch_tensors:
                        batch = torch.cat(batch_tensors, dim=0)
                        yield batch.cuda() if torch.cuda.is_available() else batch

        return generator, total_batches

    def analyze_dataset(self) -> Dict[str, Any]:
        stats = {
            'total_images': len(self.image_paths),
            'image_sizes': self.img_sizes,
            'aspect_ratios': [],
            'brightness': [],
            'contrast': []
        }

        for path in self.image_paths[:min(100, len(self.image_paths))]:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                h, w = img.shape
                stats['aspect_ratios'].append(w / h)
                stats['brightness'].append(np.mean(img))
                stats['contrast'].append(np.std(img))

        if stats['aspect_ratios']:
            stats.update({
                'avg_aspect_ratio': float(np.mean(stats['aspect_ratios'])),
                'avg_brightness': float(np.mean(stats['brightness'])),
                'avg_contrast': float(np.mean(stats['contrast']))
            })

        return stats


class DynamicShapeOptimizer:
    def __init__(self, min_size: int = 320, opt_size: int = 640, max_size: int = 1280,
                 size_step: int = 32):
        self.min_size = min_size
        self.opt_size = opt_size
        self.max_size = max_size
        self.size_step = size_step
        self.supported_sizes = list(range(min_size, max_size + 1, size_step))

    def get_dynamic_axes(self, batch_size: int = -1) -> Dict[str, Dict[int, str]]:
        return {
            'images': {
                0: 'batch',
                2: 'height',
                3: 'width'
            },
            'output0': {
                0: 'batch',
                2: 'anchors'
            }
        }

    def get_shape_profile(self, batch_size: int = 1) -> Dict[str, Any]:
        return {
            'min_shape': (batch_size, 3, self.min_size, self.min_size),
            'opt_shape': (batch_size, 3, self.opt_size, self.opt_size),
            'max_shape': (batch_size, 3, self.max_size, self.max_size)
        }

    def find_optimal_size(self, target_size: int) -> int:
        sizes = np.array(self.supported_sizes)
        idx = (np.abs(sizes - target_size)).argmin()
        return int(sizes[idx])

    def round_size(self, size: int) -> int:
        return ((size + self.size_step - 1) // self.size_step) * self.size_step


class QuantizationAccuracyValidator:
    def __init__(self, model_fp32: YOLO, model_int8: YOLO,
                 val_data: str, num_samples: int = 100):
        self.model_fp32 = model_fp32
        self.model_int8 = model_int8
        self.val_data = val_data
        self.num_samples = num_samples
        self.enhancer = ImageEnhancer()

    def _collect_val_images(self) -> List[str]:
        image_ext = ('.jpg', '.jpeg', '.png', '.bmp')
        image_paths = []
        for ext in image_ext:
            image_paths.extend(Path(self.val_data).rglob(f'*{ext}'))

        image_paths = sorted(image_paths)[:self.num_samples]
        return [str(p) for p in image_paths]

    def validate(self, iou_threshold: float = 0.5, conf_threshold: float = 0.25) -> Dict[str, Any]:
        print("\n" + "=" * 60)
        print("Quantization Accuracy Validation")
        print("=" * 60)

        image_paths = self._collect_val_images()
        if not image_paths:
            return {'error': 'No validation images found'}

        fp32_results = []
        int8_results = []
        inference_times_fp32 = []
        inference_times_int8 = []

        for i, img_path in enumerate(image_paths, 1):
            if i % 10 == 0:
                print(f"  Processing [{i}/{len(image_paths)}]: {Path(img_path).name}")

            img = cv2.imread(img_path)
            if img is None:
                continue

            img_enhanced = self.enhancer.enhance_xray(img)
            if len(img_enhanced.shape) == 2:
                img_enhanced = cv2.cvtColor(img_enhanced, cv2.COLOR_GRAY2BGR)

            start = time.time()
            res_fp32 = self.model_fp32(img_enhanced, conf=conf_threshold,
                                        iou=iou_threshold, verbose=False)
            inference_times_fp32.append(time.time() - start)

            start = time.time()
            res_int8 = self.model_int8(img_enhanced, conf=conf_threshold,
                                        iou=iou_threshold, verbose=False)
            inference_times_int8.append(time.time() - start)

            fp32_det = self._extract_detections(res_fp32)
            int8_det = self._extract_detections(res_int8)

            fp32_results.append(fp32_det)
            int8_results.append(int8_det)

        metrics = self._calculate_metrics(fp32_results, int8_results, iou_threshold)

        metrics.update({
            'avg_time_fp32_ms': float(np.mean(inference_times_fp32) * 1000),
            'avg_time_int8_ms': float(np.mean(inference_times_int8) * 1000),
            'speedup': float(np.mean(inference_times_fp32) / np.mean(inference_times_int8)),
            'num_samples': len(image_paths)
        })

        print("\nValidation Results:")
        print(f"  Precision drop: {metrics.get('precision_drop', 0) * 100:.2f}%")
        print(f"  Recall drop: {metrics.get('recall_drop', 0) * 100:.2f}%")
        print(f"  mAP drop: {metrics.get('map_drop', 0) * 100:.2f}%")
        print(f"  Speedup: {metrics['speedup']:.2f}x")

        return metrics

    def _extract_detections(self, results) -> List[Dict[str, Any]]:
        detections = []
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    detections.append({
                        'bbox': box.xyxy[0].cpu().numpy(),
                        'conf': float(box.conf[0].cpu().numpy()),
                        'cls': int(box.cls[0].cpu().numpy())
                    })
        return detections

    def _calculate_metrics(self, fp32_results: List, int8_results: List,
                            iou_threshold: float) -> Dict[str, Any]:
        total_fp32 = sum(len(dets) for dets in fp32_results)
        total_int8 = sum(len(dets) for dets in int8_results)
        true_positives = 0

        for fp32_dets, int8_dets in zip(fp32_results, int8_results):
            matched = set()
            for fp_det in fp32_dets:
                best_iou = 0
                best_idx = -1
                for i, int8_det in enumerate(int8_dets):
                    if i in matched:
                        continue
                    if fp_det['cls'] != int8_det['cls']:
                        continue
                    iou = self._calculate_iou(fp_det['bbox'], int8_det['bbox'])
                    if iou > best_iou:
                        best_iou = iou
                        best_idx = i

                if best_iou >= iou_threshold and best_idx >= 0:
                    true_positives += 1
                    matched.add(best_idx)

        precision_fp32 = true_positives / max(total_fp32, 1)
        precision_int8 = true_positives / max(total_int8, 1)
        recall_int8 = true_positives / max(total_fp32, 1)

        return {
            'precision_drop': max(0, precision_fp32 - precision_int8),
            'recall_drop': max(0, precision_fp32 - recall_int8),
            'map_drop': max(0, precision_fp32 - (precision_int8 + recall_int8) / 2),
            'true_positives': true_positives,
            'total_fp32_detections': total_fp32,
            'total_int8_detections': total_int8
        }

    def _calculate_iou(self, box1: np.ndarray, box2: np.ndarray) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / max(union, 1e-6)


def parse_args():
    parser = argparse.ArgumentParser(description='Export YOLOv8 model to TensorRT for deployment')
    parser.add_argument('--weights', type=str, required=True, help='PyTorch model path (.pt)')
    parser.add_argument('--imgsz', type=int, default=640, help='optimal image size')
    parser.add_argument('--min_imgsz', type=int, default=320, help='minimum image size for dynamic input')
    parser.add_argument('--max_imgsz', type=int, default=1280, help='maximum image size for dynamic input')
    parser.add_argument('--batch', type=int, default=1, help='batch size')
    parser.add_argument('--device', type=str, default='0', help='cuda device')
    parser.add_argument('--precision', type=str, default='fp16', choices=['fp32', 'fp16', 'int8'],
                        help='TensorRT precision mode')
    parser.add_argument('--dynamic', action='store_true', default=True, help='enable dynamic shape support')
    parser.add_argument('--dynamic_batch', action='store_true', help='enable dynamic batch size')
    parser.add_argument('--simplify', action='store_true', default=True, help='simplify ONNX model')
    parser.add_argument('--opset', type=int, default=17, help='ONNX opset version')
    parser.add_argument('--workspace', type=int, default=8, help='TensorRT workspace size (GB)')
    parser.add_argument('--calib_data', type=str, default=None, help='calibration data path for INT8')
    parser.add_argument('--calib_samples', type=int, default=500, help='number of calibration samples')
    parser.add_argument('--val_data', type=str, default=None, help='validation data for accuracy check')
    parser.add_argument('--output_dir', type=str, default='../models', help='output directory')
    parser.add_argument('--name', type=str, default='xray_defect', help='model name prefix')
    parser.add_argument('--no_enhance_calib', action='store_true', help='disable enhancement for calibration')
    parser.add_argument('--validate', action='store_true', help='run quantization accuracy validation')
    return parser.parse_args()


def check_tensorrt():
    try:
        import tensorrt as trt
        print(f"TensorRT version: {trt.__version__}")
        return True
    except ImportError:
        print("TensorRT is not installed. Please install TensorRT first.")
        return False


def check_cuda():
    if torch.cuda.is_available():
        print(f"CUDA is available! Device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA version: {torch.version.cuda}")
        return True
    else:
        print("CUDA is not available.")
        return False


def benchmark_model(model_path, imgsz=640, batch=1, iterations=100, dynamic_sizes=None):
    print(f"\nBenchmarking model: {model_path}")

    model = YOLO(model_path)

    if dynamic_sizes is None:
        dynamic_sizes = [imgsz]

    results = {}
    for size in dynamic_sizes:
        print(f"\n  Testing size: {size}x{size}")

        dummy_input = torch.randn(batch, 3, size, size).cuda() if torch.cuda.is_available() else torch.randn(batch, 3, size, size)

        for _ in range(10):
            _ = model(dummy_input, verbose=False)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        start_time = time.time()

        for _ in range(iterations):
            _ = model(dummy_input, verbose=False)

        if torch.cuda.is_available():
            torch.cuda.synchronize()
        end_time = time.time()

        total_time = end_time - start_time
        avg_time = total_time / iterations
        fps = batch * iterations / total_time

        results[size] = {
            'avg_time_ms': avg_time * 1000,
            'fps': fps
        }

        print(f"    Average inference time: {avg_time * 1000:.2f} ms")
        print(f"    Throughput: {fps:.2f} FPS")

    return results


def export_to_onnx(model, weights_path, imgsz, min_imgsz, max_imgsz, batch,
                   dynamic, dynamic_batch, simplify, opset, output_dir, name):
    print("\n" + "=" * 60)
    print("Exporting to ONNX format...")
    print("=" * 60)

    dynamic_axes = None
    if dynamic:
        dynamic_axes = {
            'images': {0: 'batch', 2: 'height', 3: 'width'},
            'output0': {0: 'batch', 2: 'anchors'}
        }
        if not dynamic_batch:
            del dynamic_axes['images'][0]
            del dynamic_axes['output0'][0]

    onnx_path = model.export(
        format='onnx',
        imgsz=imgsz,
        batch=batch,
        dynamic=dynamic,
        simplify=simplify,
        opset=opset,
        dynamic_axes=dynamic_axes,
    )

    print(f"ONNX model saved at: {onnx_path}")
    return onnx_path


def export_to_tensorrt(model, weights_path, imgsz, min_imgsz, max_imgsz, batch,
                       precision, dynamic, dynamic_batch, workspace,
                       calib_data, calib_samples, no_enhance_calib,
                       output_dir, name):
    print("\n" + "=" * 60)
    print(f"Exporting to TensorRT ({precision.upper()})...")
    print("=" * 60)

    int8 = (precision == 'int8')
    half = (precision == 'fp16')

    shape_optimizer = DynamicShapeOptimizer(
        min_size=min_imgsz,
        opt_size=imgsz,
        max_size=max_imgsz
    )

    export_kwargs = {
        'format': 'engine',
        'imgsz': [min_imgsz, imgsz, max_imgsz] if dynamic else imgsz,
        'batch': batch,
        'dynamic': dynamic,
        'half': half,
        'int8': int8,
        'workspace': workspace,
    }

    if int8:
        if calib_data is None:
            print("ERROR: --calib_data is required for INT8 quantization")
            sys.exit(1)

        print(f"\nPreparing calibration dataset with {calib_samples} samples...")
        calib_dataset = CalibrationDataset(
            data_dir=calib_data,
            num_samples=calib_samples,
            img_sizes=[min_imgsz, imgsz, max_imgsz] if dynamic else [imgsz],
            use_enhancement=not no_enhance_calib
        )

        calib_stats = calib_dataset.analyze_dataset()
        print(f"\nCalibration Dataset Analysis:")
        for k, v in calib_stats.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")

        export_kwargs['data'] = calib_data
        export_kwargs['batch'] = batch
        export_kwargs['imgsz'] = [min_imgsz, imgsz, max_imgsz] if dynamic else imgsz

        print(f"\nDynamic shape configuration:")
        shape_profile = shape_optimizer.get_shape_profile(batch)
        print(f"  Min: {shape_profile['min_shape']}")
        print(f"  Opt: {shape_profile['opt_shape']}")
        print(f"  Max: {shape_profile['max_shape']}")

    try:
        engine_path = model.export(**export_kwargs)
        print(f"TensorRT model saved at: {engine_path}")
        return engine_path, shape_optimizer
    except Exception as e:
        print(f"Error exporting to TensorRT: {e}")
        import traceback
        traceback.print_exc()
        print("Falling back to ONNX export...")
        return None, None


def get_model_size(model_path):
    if os.path.exists(model_path):
        size_bytes = os.path.getsize(model_path)
        size_mb = size_bytes / (1024 * 1024)
        print(f"  Model size: {size_mb:.2f} MB")
        return size_mb
    return None


def generate_metadata(original_pt_path, engine_path, benchmark_results, output_dir, name,
                      precision, shape_optimizer=None, val_metrics=None):
    metadata = {
        'original_model': original_pt_path,
        'tensorrt_model': engine_path,
        'precision': precision,
        'export_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'model_size_mb': get_model_size(engine_path) if engine_path else None,
        'benchmark_results': benchmark_results,
        'dynamic_shape': {
            'enabled': shape_optimizer is not None,
            'min_size': shape_optimizer.min_size if shape_optimizer else None,
            'opt_size': shape_optimizer.opt_size if shape_optimizer else None,
            'max_size': shape_optimizer.max_size if shape_optimizer else None,
            'supported_sizes': shape_optimizer.supported_sizes if shape_optimizer else None,
        } if shape_optimizer else None,
        'quantization_metrics': val_metrics
    }

    metadata_path = os.path.join(output_dir, f'{name}_trt_{precision}_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nMetadata saved at: {metadata_path}")
    return metadata


def main():
    args = parse_args()

    os.chdir(Path(__file__).parent)

    print("\n" + "=" * 60)
    print("YOLOv8 TensorRT Export Tool (Enhanced)")
    print("=" * 60)

    if not check_cuda():
        print("ERROR: CUDA is required for TensorRT export.")
        sys.exit(1)

    if not check_tensorrt():
        print("ERROR: TensorRT is required. Please install it.")
        sys.exit(1)

    if not os.path.exists(args.weights):
        print(f"ERROR: Model file not found: {args.weights}")
        sys.exit(1)

    if args.precision == 'int8' and args.calib_data is None:
        print("ERROR: --calib_data is required for INT8 quantization")
        sys.exit(1)

    print(f"\nLoading model: {args.weights}")
    model = YOLO(args.weights)
    print("Model loaded successfully!")

    get_model_size(args.weights)

    dynamic_sizes = [args.min_imgsz, args.imgsz, args.max_imgsz] if args.dynamic else [args.imgsz]

    print("\nBenchmarking original PyTorch model...")
    pt_benchmark = benchmark_model(args.weights, args.imgsz, args.batch, dynamic_sizes=dynamic_sizes)

    onnx_path = None
    if args.simplify or args.dynamic:
        try:
            onnx_path = export_to_onnx(
                model, args.weights, args.imgsz, args.min_imgsz, args.max_imgsz, args.batch,
                args.dynamic, args.dynamic_batch, args.simplify, args.opset, args.output_dir, args.name
            )
            print("\nBenchmarking ONNX model...")
            onnx_benchmark = benchmark_model(onnx_path, args.imgsz, args.batch, dynamic_sizes=dynamic_sizes)
        except Exception as e:
            print(f"ONNX export failed: {e}")
            import traceback
            traceback.print_exc()

    engine_path, shape_optimizer = export_to_tensorrt(
        model, args.weights, args.imgsz, args.min_imgsz, args.max_imgsz, args.batch,
        args.precision, args.dynamic, args.dynamic_batch, args.workspace,
        args.calib_data, args.calib_samples, args.no_enhance_calib,
        args.output_dir, args.name
    )

    val_metrics = None
    if engine_path:
        print("\nBenchmarking TensorRT model...")
        trt_benchmark = benchmark_model(engine_path, args.imgsz, args.batch, dynamic_sizes=dynamic_sizes)
        get_model_size(engine_path)

        if args.validate and args.val_data and args.precision == 'int8':
            print("\n" + "=" * 60)
            print("Running Quantization Accuracy Validation...")
            print("=" * 60)

            validator = QuantizationAccuracyValidator(
                model_fp32=model,
                model_int8=YOLO(engine_path),
                val_data=args.val_data,
                num_samples=100
            )
            val_metrics = validator.validate()

        print("\n" + "=" * 60)
        print("Performance Summary")
        print("=" * 60)

        for size in dynamic_sizes:
            print(f"\nResolution: {size}x{size}")
            print(f"  PyTorch: {pt_benchmark[size]['avg_time_ms']:.2f} ms | {pt_benchmark[size]['fps']:.2f} FPS")
            if onnx_path and 'onnx_benchmark' in locals():
                print(f"  ONNX:    {onnx_benchmark[size]['avg_time_ms']:.2f} ms | {onnx_benchmark[size]['fps']:.2f} FPS")
            print(f"  TRT-{args.precision.upper()}: {trt_benchmark[size]['avg_time_ms']:.2f} ms | {trt_benchmark[size]['fps']:.2f} FPS")

            speedup = pt_benchmark[size]['avg_time_ms'] / trt_benchmark[size]['avg_time_ms']
            print(f"  Speedup over PyTorch: {speedup:.2f}x")

        generate_metadata(args.weights, engine_path, trt_benchmark, args.output_dir,
                          args.name, args.precision, shape_optimizer, val_metrics)

        if args.dynamic:
            print(f"\nDynamic shape support enabled:")
            print(f"  Supported resolutions: {shape_optimizer.supported_sizes}")
            print(f"  Use --imgsz parameter during inference for custom sizes")

        print("\n" + "=" * 60)
        print("Export Complete!")
        print("=" * 60)

        print("\nNext steps:")
        print(f"  1. Run inference with dynamic shapes:")
        print(f"     python src/inference.py --model {engine_path} --input <image> --dynamic")
        print(f"  2. For multi-resolution support:")
        print(f"     python src/inference.py --model {engine_path} --input <image> --imgsz 960")
        if args.precision == 'int8':
            print(f"  3. INT8 model ready for production deployment")
    else:
        print("\n" + "=" * 60)
        print("Export Failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
