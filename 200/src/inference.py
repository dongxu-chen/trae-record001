import os
import sys
import argparse
from pathlib import Path
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2
from ultralytics import YOLO
import torch

sys.path.append(str(Path(__file__).parent))
from image_enhancer import ImageEnhancer


class DynamicInferenceOptimizer:
    def __init__(self, min_size: int = 320, opt_size: int = 640, max_size: int = 1280,
                 size_step: int = 32, metadata_path: Optional[str] = None):
        self.min_size = min_size
        self.opt_size = opt_size
        self.max_size = max_size
        self.size_step = size_step
        self.supported_sizes = list(range(min_size, max_size + 1, size_step))
        self.size_cache = {}
        self.metadata = self._load_metadata(metadata_path)

    def _load_metadata(self, metadata_path: Optional[str]) -> Dict[str, Any]:
        if metadata_path and os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return {}

    def get_optimal_size(self, image_height: int, image_width: int,
                         target_precision: str = 'balanced') -> int:
        image_max_dim = max(image_height, image_width)
        image_aspect_ratio = max(image_height, image_width) / max(min(image_height, image_width), 1)

        cache_key = (image_height, image_width, target_precision)
        if cache_key in self.size_cache:
            return self.size_cache[cache_key]

        if target_precision == 'speed':
            base_size = min(self.opt_size, image_max_dim)
        elif target_precision == 'accuracy':
            base_size = min(self.max_size, image_max_dim)
        else:
            base_size = self.opt_size

        if image_aspect_ratio > 2.0:
            base_size = int(base_size * 1.2)

        optimal_size = self._round_to_supported(base_size)
        self.size_cache[cache_key] = optimal_size

        return optimal_size

    def _round_to_supported(self, size: int) -> int:
        size = max(self.min_size, min(self.max_size, size))
        return ((size + self.size_step - 1) // self.size_step) * self.size_step

    def resize_image(self, image: np.ndarray, target_size: int) -> Tuple[np.ndarray, Dict[str, Any]]:
        h, w = image.shape[:2]
        scale = target_size / max(h, w)
        new_h, new_w = int(h * scale), int(w * scale)

        if (new_h, new_w) != (h, w):
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            resized = image.copy()

        pad_h = target_size - new_h
        pad_w = target_size - new_w
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left

        padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                     cv2.BORDER_CONSTANT, value=(114, 114, 114))

        resize_info = {
            'original_shape': (h, w),
            'resized_shape': (new_h, new_w),
            'padded_shape': (target_size, target_size),
            'scale': scale,
            'pad_top': top,
            'pad_left': left,
            'pad_bottom': bottom,
            'pad_right': right
        }

        return padded, resize_info

    def scale_back_detections(self, detections: List[Dict[str, Any]],
                               resize_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        scale = resize_info['scale']
        pad_left = resize_info['pad_left']
        pad_top = resize_info['pad_top']

        for det in detections:
            bbox = det['bbox']
            bbox['x1'] = (bbox['x1'] - pad_left) / scale
            bbox['y1'] = (bbox['y1'] - pad_top) / scale
            bbox['x2'] = (bbox['x2'] - pad_left) / scale
            bbox['y2'] = (bbox['y2'] - pad_top) / scale
            bbox['center_x'] = (bbox['x1'] + bbox['x2']) / 2
            bbox['center_y'] = (bbox['y1'] + bbox['y2']) / 2
            bbox['width'] = bbox['x2'] - bbox['x1']
            bbox['height'] = bbox['y2'] - bbox['y1']
            det['area'] = bbox['width'] * bbox['height']

        return detections


class MultiScaleInference:
    def __init__(self, scales: Optional[List[int]] = None, weights: Optional[List[float]] = None,
                 merge_iou: float = 0.5):
        self.scales = scales or [640, 960, 1280]
        self.weights = weights or [0.3, 0.5, 0.2]
        self.merge_iou = merge_iou

    def detect_multi_scale(self, model, image: np.ndarray, conf_threshold: float,
                            iou_threshold: float, device: str,
                            optimizer: DynamicInferenceOptimizer) -> List[Dict[str, Any]]:
        all_detections = []
        scale_weights = []

        for scale, weight in zip(self.scales, self.weights):
            resized_img, resize_info = optimizer.resize_image(image, scale)

            with torch.no_grad():
                results = model(
                    resized_img,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    device=device,
                    verbose=False
                )

            scale_detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls_id = int(box.cls[0].cpu().numpy())

                        detection = {
                            'class_id': cls_id,
                            'confidence': conf * weight,
                            'bbox': {
                                'x1': float(x1), 'y1': float(y1),
                                'x2': float(x2), 'y2': float(y2),
                                'center_x': float((x1 + x2) / 2),
                                'center_y': float((y1 + y2) / 2),
                                'width': float(x2 - x1),
                                'height': float(y2 - y1)
                            },
                            'area': float((x2 - x1) * (y2 - y1)),
                            'scale': scale,
                            'scale_weight': weight
                        }
                        scale_detections.append(detection)

            scale_detections = optimizer.scale_back_detections(scale_detections, resize_info)
            all_detections.extend(scale_detections)
            scale_weights.extend([weight] * len(scale_detections))

        merged_detections = self._merge_detections(all_detections)
        return merged_detections

    def _merge_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not detections:
            return []

        detections_by_class = {}
        for det in detections:
            cls_id = det['class_id']
            if cls_id not in detections_by_class:
                detections_by_class[cls_id] = []
            detections_by_class[cls_id].append(det)

        merged = []
        for cls_id, class_dets in detections_by_class.items():
            class_dets.sort(key=lambda x: x['confidence'], reverse=True)
            merged.extend(self._nms(class_dets))

        return merged

    def _nms(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not detections:
            return []

        keep = []
        while detections:
            best = detections.pop(0)
            keep.append(best)

            detections = [
                det for det in detections
                if self._calculate_iou(best['bbox'], det['bbox']) < self.merge_iou
            ]

        return keep

    def _calculate_iou(self, box1: Dict[str, float], box2: Dict[str, float]) -> float:
        x1 = max(box1['x1'], box2['x1'])
        y1 = max(box1['y1'], box2['y1'])
        x2 = min(box1['x2'], box2['x2'])
        y2 = min(box1['y2'], box2['y2'])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1['x2'] - box1['x1']) * (box1['y2'] - box1['y1'])
        area2 = (box2['x2'] - box2['x1']) * (box2['y2'] - box2['y1'])
        union = area1 + area2 - intersection

        return intersection / max(union, 1e-6)


class XRayDefectDetector:
    def __init__(self, model_path: str, use_enhancement: bool = True,
                 conf_threshold: float = 0.25, iou_threshold: float = 0.45,
                 device: str = '0', classes: Optional[Dict[int, str]] = None,
                 imgsz: Optional[int] = None, dynamic_size: bool = True,
                 multi_scale: bool = False,
                 min_size: int = 320, opt_size: int = 640, max_size: int = 1280,
                 metadata_path: Optional[str] = None,
                 enhance_mode: str = 'adaptive', use_multiscale_clahe: bool = False):
        self.model_path = model_path
        self.use_enhancement = use_enhancement
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.classes = classes or {0: 'porosity', 1: 'crack', 2: 'slag_inclusion'}
        self.imgsz = imgsz
        self.dynamic_size = dynamic_size
        self.multi_scale = multi_scale
        self.class_colors = {
            0: (0, 255, 0),
            1: (255, 0, 0),
            2: (0, 0, 255)
        }

        print(f"Loading model from: {model_path}")
        self.model = YOLO(model_path)
        print("Model loaded successfully!")

        self.enhancer = ImageEnhancer(
            use_adaptive_clahe=(enhance_mode == 'adaptive'),
            use_multiscale=use_multiscale_clahe,
            auto_tune=True
        ) if use_enhancement else None

        self.optimizer = DynamicInferenceOptimizer(
            min_size=min_size,
            opt_size=opt_size,
            max_size=max_size,
            metadata_path=metadata_path
        )

        if multi_scale:
            self.ms_inference = MultiScaleInference(
                scales=[opt_size, min(opt_size * 1.5, max_size), max_size],
                weights=[0.3, 0.5, 0.2]
            )

        self._check_runtime()

    def _check_runtime(self):
        print("\n" + "=" * 60)
        print("Runtime Environment Check")
        print("=" * 60)

        if self.model_path.endswith('.engine'):
            print("Runtime: TensorRT")
        elif self.model_path.endswith('.onnx'):
            print("Runtime: ONNX")
        else:
            print("Runtime: PyTorch")

        if torch.cuda.is_available():
            print(f"CUDA: Available (Device: {torch.cuda.get_device_name(0)})")
        else:
            print("CUDA: Not Available (Using CPU)")

        print(f"Confidence Threshold: {self.conf_threshold}")
        print(f"IOU Threshold: {self.iou_threshold}")
        print(f"Image Enhancement: {'Enabled' if self.use_enhancement else 'Disabled'}")
        if self.use_enhancement and self.enhancer:
            print(f"  Enhancement Mode: {'Adaptive CLAHE' if self.enhancer.use_adaptive_clahe else 'Standard CLAHE'}")
            print(f"  Multi-scale CLAHE: {'Enabled' if self.enhancer.use_multiscale else 'Disabled'}")
        print(f"Dynamic Size: {'Enabled' if self.dynamic_size else 'Disabled'}")
        print(f"Multi-scale Inference: {'Enabled' if self.multi_scale else 'Disabled'}")
        if self.dynamic_size:
            print(f"  Size range: {self.optimizer.min_size} - {self.optimizer.max_size}")
            print(f"  Optimal size: {self.optimizer.opt_size}")
            print(f"  Supported sizes: {self.optimizer.supported_sizes}")
        print("=" * 60 + "\n")

    def preprocess(self, image: np.ndarray, target_size: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        processed = image.copy()

        if self.use_enhancement and self.enhancer:
            processed = self.enhancer.enhance_xray(processed)
            if len(processed.shape) == 2:
                processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)

        resize_info = {}
        if target_size:
            processed, resize_info = self.optimizer.resize_image(processed, target_size)

        return processed, resize_info

    def detect(self, image: np.ndarray, verbose: bool = False,
               target_precision: str = 'balanced') -> Tuple[List[Dict[str, Any]], float]:
        start_time = time.time()

        h, w = image.shape[:2]

        if self.multi_scale:
            detections = self.ms_inference.detect_multi_scale(
                self.model, image, self.conf_threshold,
                self.iou_threshold, self.device, self.optimizer
            )
        else:
            if self.imgsz:
                target_size = self.imgsz
            elif self.dynamic_size:
                target_size = self.optimizer.get_optimal_size(h, w, target_precision)
            else:
                target_size = 640

            processed_image, resize_info = self.preprocess(image, target_size)

            if verbose:
                print(f"Input size: {w}x{h}, Inference size: {target_size}x{target_size}")
                if resize_info:
                    print(f"Scale: {resize_info['scale']:.3f}, "
                          f"Pad: top={resize_info['pad_top']}, left={resize_info['pad_left']}")

            with torch.no_grad():
                results = self.model(
                    processed_image,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=verbose
                )

            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())
                        cls_id = int(box.cls[0].cpu().numpy())

                        detection = {
                            'class_id': cls_id,
                            'class_name': self.classes.get(cls_id, f'class_{cls_id}'),
                            'confidence': conf,
                            'bbox': {
                                'x1': float(x1), 'y1': float(y1),
                                'x2': float(x2), 'y2': float(y2),
                                'center_x': float((x1 + x2) / 2),
                                'center_y': float((y1 + y2) / 2),
                                'width': float(x2 - x1),
                                'height': float(y2 - y1)
                            },
                            'area': float((x2 - x1) * (y2 - y1))
                        }
                        detections.append(detection)

            if resize_info:
                detections = self.optimizer.scale_back_detections(detections, resize_info)

        for det in detections:
            if 'class_name' not in det:
                det['class_name'] = self.classes.get(det['class_id'], f'class_{det["class_id"]}')

        inference_time = (time.time() - start_time) * 1000

        if verbose:
            print(f"\nFound {len(detections)} defects in {inference_time:.2f} ms")
            for i, det in enumerate(detections):
                print(f"  [{i}] {det['class_name']}: {det['confidence']:.3f} | "
                      f"bbox: ({det['bbox']['x1']:.1f}, {det['bbox']['y1']:.1f}, "
                      f"{det['bbox']['x2']:.1f}, {det['bbox']['y2']:.1f})")

        return detections, inference_time

    def visualize(self, image: np.ndarray, detections: List[Dict[str, Any]],
                  show_labels: bool = True, show_conf: bool = True,
                  draw_scale: bool = True) -> np.ndarray:
        vis_image = image.copy()
        if len(vis_image.shape) == 2:
            vis_image = cv2.cvtColor(vis_image, cv2.COLOR_GRAY2BGR)

        for det in detections:
            cls_id = det['class_id']
            color = self.class_colors.get(cls_id, (255, 255, 255))

            x1 = int(det['bbox']['x1'])
            y1 = int(det['bbox']['y1'])
            x2 = int(det['bbox']['x2'])
            y2 = int(det['bbox']['y2'])

            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)

            if show_labels or show_conf:
                label = det['class_name']
                if show_conf:
                    label += f" {det['confidence']:.2f}"

                (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

                cv2.rectangle(vis_image, (x1, y1 - label_h - 10),
                              (x1 + label_w + 10, y1), color, -1)
                cv2.putText(vis_image, label, (x1 + 5, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            if draw_scale and 'scale' in det:
                scale_label = f"@{det['scale']}"
                cv2.putText(vis_image, scale_label, (x2 + 5, y1 + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        return vis_image

    def detect_single_image(self, image_path: str, output_dir: Optional[str] = None,
                            save_result: bool = True, verbose: bool = True,
                            target_precision: str = 'balanced') -> Dict[str, Any]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        detections, inference_time = self.detect(image, verbose=verbose, target_precision=target_precision)

        result = {
            'image_path': image_path,
            'image_size': {'height': image.shape[0], 'width': image.shape[1]},
            'detections': detections,
            'num_detections': len(detections),
            'inference_time_ms': inference_time,
            'inference_mode': 'multi_scale' if self.multi_scale else 'single_scale',
            'dynamic_size_enabled': self.dynamic_size,
            'detection_summary': self._get_summary(detections)
        }

        if save_result and output_dir:
            os.makedirs(output_dir, exist_ok=True)

            vis_image = self.visualize(image, detections)
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(output_dir, f'{base_name}_result.jpg')
            cv2.imwrite(output_path, vis_image)
            result['visualization_path'] = output_path

            json_path = os.path.join(output_dir, f'{base_name}_result.json')
            with open(json_path, 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            result['json_path'] = json_path

            if verbose:
                print(f"\nResults saved to: {output_path}")
                print(f"JSON saved to: {json_path}")

        return result

    def detect_batch(self, image_dir: str, output_dir: str,
                     extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff'),
                     verbose: bool = True, target_precision: str = 'balanced') -> List[Dict[str, Any]]:
        if not os.path.exists(image_dir):
            raise FileNotFoundError(f"Directory not found: {image_dir}")

        image_files = []
        for ext in extensions:
            image_files.extend(Path(image_dir).glob(f'*{ext}'))

        if not image_files:
            print(f"No images found in {image_dir}")
            return []

        print(f"\nProcessing {len(image_files)} images...")

        results = []
        total_time = 0
        size_stats = []

        for i, img_path in enumerate(image_files, 1):
            if verbose:
                print(f"\n[{i}/{len(image_files)}] Processing: {img_path.name}")

            try:
                result = self.detect_single_image(
                    str(img_path), output_dir, save_result=True,
                    verbose=verbose, target_precision=target_precision
                )
                results.append(result)
                total_time += result['inference_time_ms']
                size_stats.append(max(result['image_size']['height'], result['image_size']['width']))
            except Exception as e:
                print(f"Error processing {img_path}: {e}")

        if verbose and results:
            print("\n" + "=" * 60)
            print("Batch Processing Summary")
            print("=" * 60)
            print(f"Total images: {len(results)}")
            print(f"Total time: {total_time:.2f} ms")
            print(f"Average time: {total_time / len(results):.2f} ms/image")
            print(f"Average FPS: {1000 / (total_time / len(results)):.2f}")
            print(f"Image size range: {min(size_stats)} - {max(size_stats)} px")
            if self.dynamic_size:
                print(f"Optimal sizes: {set(self.optimizer._round_to_supported(s) for s in size_stats)}")
            print("=" * 60 + "\n")

        return results

    def _get_summary(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {
            'total': len(detections),
            'by_class': {}
        }

        for det in detections:
            cls_name = det['class_name']
            if cls_name not in summary['by_class']:
                summary['by_class'][cls_name] = {'count': 0, 'avg_confidence': 0.0, 'avg_area': 0.0}
            summary['by_class'][cls_name]['count'] += 1
            summary['by_class'][cls_name]['avg_confidence'] += det['confidence']
            summary['by_class'][cls_name]['avg_area'] += det.get('area', 0)

        for cls_name in summary['by_class']:
            count = summary['by_class'][cls_name]['count']
            if count > 0:
                summary['by_class'][cls_name]['avg_confidence'] /= count
                summary['by_class'][cls_name]['avg_area'] /= count

        return summary


def parse_args():
    parser = argparse.ArgumentParser(description='X-ray Defect Detection Inference')
    parser.add_argument('--model', type=str, required=True, help='model path (.pt, .onnx, .engine)')
    parser.add_argument('--input', type=str, required=True, help='input image or directory')
    parser.add_argument('--output', type=str, default='../outputs', help='output directory')
    parser.add_argument('--conf', type=float, default=0.25, help='confidence threshold')
    parser.add_argument('--iou', type=float, default=0.45, help='NMS IOU threshold')
    parser.add_argument('--device', type=str, default='0', help='cuda device')
    parser.add_argument('--imgsz', type=int, default=None, help='fixed inference size (disables dynamic)')
    parser.add_argument('--min_imgsz', type=int, default=320, help='minimum image size for dynamic')
    parser.add_argument('--max_imgsz', type=int, default=1280, help='maximum image size for dynamic')
    parser.add_argument('--no_enhance', action='store_true', help='disable image enhancement')
    parser.add_argument('--no_dynamic', action='store_true', help='disable dynamic size adjustment')
    parser.add_argument('--multi_scale', action='store_true', help='enable multi-scale inference')
    parser.add_argument('--enhance_mode', type=str, default='adaptive',
                        choices=['standard', 'adaptive', 'multiscale'], help='enhancement mode')
    parser.add_argument('--precision_mode', type=str, default='balanced',
                        choices=['speed', 'balanced', 'accuracy'], help='target precision mode')
    parser.add_argument('--metadata', type=str, default=None, help='model metadata path')
    parser.add_argument('--verbose', action='store_true', help='verbose output')
    return parser.parse_args()


def main():
    args = parse_args()

    os.chdir(Path(__file__).parent)

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
    elif os.path.isfile(args.input):
        result = detector.detect_single_image(
            args.input, args.output, verbose=args.verbose,
            target_precision=args.precision_mode
        )
    else:
        print(f"Error: Input path not found: {args.input}")
        sys.exit(1)


if __name__ == '__main__':
    main()
