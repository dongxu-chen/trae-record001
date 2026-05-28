import os
import sys
from typing import Optional, List, Dict, Tuple
import numpy as np
import cv2
import json
import random
from collections import defaultdict

from config import (
    YOLO_MODEL_PATH, TRT_ENGINE_PATH,
    INPUT_WIDTH, INPUT_HEIGHT, FP16_QUANTIZATION, INT8_QUANTIZATION,
    TRT_ENGINE_DIR, WEIGHTS_DIR
)


class HardExampleMiner:
    def __init__(
        self,
        hard_example_dir: str = "hard_examples",
        hard_conf_threshold: float = 0.3,
        easy_conf_threshold: float = 0.8,
        max_hard_examples: int = 1000
    ):
        self.hard_example_dir = hard_example_dir
        self.hard_conf_threshold = hard_conf_threshold
        self.easy_conf_threshold = easy_conf_threshold
        self.max_hard_examples = max_hard_examples

        self.hard_examples: List[Dict] = []
        self.stats = {
            "total_evaluated": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "low_confidence": 0,
            "small_targets": 0
        }

        os.makedirs(self.hard_example_dir, exist_ok=True)
        self.annotations_file = os.path.join(self.hard_example_dir, "annotations.json")

    def is_hard_example(
        self,
        detections: List,
        gt_boxes: Optional[List] = None,
        image: Optional[np.ndarray] = None
    ) -> Tuple[bool, str]:
        if not detections:
            if gt_boxes:
                return True, "false_negative"
            return False, "no_detections"

        has_low_conf = any(d.confidence < self.hard_conf_threshold for d in detections)
        has_small = any(
            max(d.bbox[2] - d.bbox[0], d.bbox[3] - d.bbox[1]) < 32
            for d in detections
        )
        avg_conf = sum(d.confidence for d in detections) / len(detections)

        if has_low_conf:
            return True, "low_confidence"
        if avg_conf < self.hard_conf_threshold:
            return True, "low_avg_confidence"
        if has_small:
            return True, "small_target"

        if gt_boxes:
            matched = self._match_detections(detections, gt_boxes)
            if matched["false_negatives"] > 0:
                return True, "false_negative"
            if matched["false_positives"] > 0:
                return True, "false_positive"

        return False, "easy"

    def _match_detections(
        self,
        detections: List,
        gt_boxes: List,
        iou_threshold: float = 0.5
    ) -> Dict:
        matched_gt = set()
        false_positives = 0

        for det in detections:
            best_iou = 0
            best_gt_idx = -1

            for i, gt in enumerate(gt_boxes):
                if i in matched_gt:
                    continue
                iou = self._calculate_iou(det.bbox, gt)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = i

            if best_iou >= iou_threshold:
                matched_gt.add(best_gt_idx)
            else:
                false_positives += 1

        false_negatives = len(gt_boxes) - len(matched_gt)

        return {
            "true_positives": len(matched_gt),
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }

    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        inter = w * h

        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0

    def add_hard_example(
        self,
        image: np.ndarray,
        detections: List,
        gt_boxes: Optional[List] = None,
        reason: str = "unknown"
    ) -> str:
        if len(self.hard_examples) >= self.max_hard_examples:
            self.hard_examples.pop(0)

        example_id = f"hard_{len(self.hard_examples):06d}"
        image_path = os.path.join(self.hard_example_dir, f"{example_id}.jpg")

        cv2.imwrite(image_path, image)

        example_data = {
            "id": example_id,
            "image_path": image_path,
            "reason": reason,
            "detections": [d.to_dict() for d in detections],
            "gt_boxes": gt_boxes or [],
            "num_detections": len(detections),
            "avg_confidence": sum(d.confidence for d in detections) / len(detections) if detections else 0
        }

        self.hard_examples.append(example_data)
        self._update_stats(reason)

        return example_id

    def _update_stats(self, reason: str):
        self.stats["total_evaluated"] += 1
        if reason == "false_positive":
            self.stats["false_positives"] += 1
        elif reason == "false_negative":
            self.stats["false_negatives"] += 1
        elif reason in ["low_confidence", "low_avg_confidence"]:
            self.stats["low_confidence"] += 1
        elif reason == "small_target":
            self.stats["small_targets"] += 1

    def get_calibration_images(
        self,
        weight_hard: float = 0.7,
        max_images: int = 500
    ) -> List[str]:
        all_images = []

        num_hard = int(max_images * weight_hard)
        hard_images = [ex["image_path"] for ex in self.hard_examples[-num_hard:]]
        all_images.extend(hard_images)

        return all_images

    def save_annotations(self):
        with open(self.annotations_file, "w", encoding="utf-8") as f:
            json.dump({
                "stats": self.stats,
                "hard_examples": self.hard_examples
            }, f, indent=2, ensure_ascii=False)

    def load_annotations(self):
        if os.path.exists(self.annotations_file):
            with open(self.annotations_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.stats = data.get("stats", self.stats)
                self.hard_examples = data.get("hard_examples", [])

    def get_stats(self) -> Dict:
        return self.stats


class QuantizationCalibrator:
    def __init__(
        self,
        model,
        calibration_images: List[str],
        hard_example_miner: Optional[HardExampleMiner] = None,
        input_shape: Tuple[int, int, int, int] = (1, 3, 640, 640)
    ):
        self.model = model
        self.calibration_images = calibration_images
        self.hard_example_miner = hard_example_miner
        self.input_shape = input_shape
        self.calibration_stats = defaultdict(list)

    def collect_hard_examples(
        self,
        images: List[str],
        num_iterations: int = 3,
        conf_threshold: float = 0.3
    ) -> List[str]:
        if not self.hard_example_miner:
            return images

        print(f"[INFO] Collecting hard examples from {len(images)} images...")

        for img_path in images:
            img = cv2.imread(img_path)
            if img is None:
                continue

            try:
                results = self.model(
                    img,
                    conf=conf_threshold,
                    verbose=False
                )

                detections = []
                for r in results:
                    if r.boxes:
                        for box in r.boxes:
                            xyxy = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0].cpu().numpy())
                            class_id = int(box.cls[0].cpu().numpy())

                            from detector.yolo_detector import DetectionResult
                            det = DetectionResult(
                                bbox=[int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])],
                                confidence=conf,
                                class_id=class_id,
                                class_name=f"class_{class_id}",
                                class_name_zh=f"类别{class_id}",
                                category="unknown"
                            )
                            detections.append(det)

                is_hard, reason = self.hard_example_miner.is_hard_example(detections, image=img)
                if is_hard:
                    self.hard_example_miner.add_hard_example(img, detections, reason=reason)

            except Exception as e:
                print(f"[WARN] Error processing {img_path}: {e}")

        hard_images = self.hard_example_miner.get_calibration_images(
            weight_hard=0.7,
            max_images=len(images)
        )

        combined = list(set(images + hard_images))
        random.shuffle(combined)

        print(f"[INFO] Collected {len(hard_images)} hard examples")
        print(f"[INFO] Total calibration images: {len(combined)}")

        return combined

    def evaluate_quantization_accuracy(
        self,
        eval_images: List[str],
        original_predictions: Dict,
        quantized_predictions: Dict
    ) -> Dict:
        accuracy_stats = {
            "total_images": len(eval_images),
            "mAP_original": 0.0,
            "mAP_quantized": 0.0,
            "accuracy_drop": 0.0,
            "per_class_drop": {},
            "hard_example_drop": 0.0
        }

        return accuracy_stats

    def iterative_calibration(
        self,
        images: List[str],
        max_iterations: int = 3,
        accuracy_threshold: float = 0.02
    ) -> List[str]:
        current_images = images.copy()
        best_images = images.copy()

        for iteration in range(max_iterations):
            print(f"\n[INFO] Calibration iteration {iteration + 1}/{max_iterations}")

            current_images = self.collect_hard_examples(
                current_images,
                num_iterations=1
            )

            if self.hard_example_miner:
                stats = self.hard_example_miner.get_stats()
                print(f"[INFO] Hard example stats: {stats}")

        if self.hard_example_miner:
            self.hard_example_miner.save_annotations()

        return current_images


class ModelQuantizer:
    def __init__(
        self,
        yolo_model_path: Optional[str] = None,
        trt_engine_path: Optional[str] = None,
        input_width: int = INPUT_WIDTH,
        input_height: int = INPUT_HEIGHT,
        fp16: bool = FP16_QUANTIZATION,
        int8: bool = INT8_QUANTIZATION,
        calibration_images: Optional[List[str]] = None,
        use_hard_example_mining: bool = True,
        hard_example_dir: str = "hard_examples"
    ):
        self.yolo_model_path = yolo_model_path or YOLO_MODEL_PATH
        self.trt_engine_path = trt_engine_path or TRT_ENGINE_PATH
        self.input_width = input_width
        self.input_height = input_height
        self.fp16 = fp16
        self.int8 = int8
        self.calibration_images = calibration_images or []
        self.use_hard_example_mining = use_hard_example_mining

        self.hard_miner = HardExampleMiner(
            hard_example_dir=hard_example_dir
        ) if use_hard_example_mining else None

    def export_to_onnx(self, simplify: bool = True) -> Optional[str]:
        if not os.path.exists(self.yolo_model_path):
            print(f"[ERROR] YOLO model not found: {self.yolo_model_path}")
            return None

        try:
            from ultralytics import YOLO

            print(f"[INFO] Loading YOLO model: {self.yolo_model_path}")
            model = YOLO(self.yolo_model_path)

            onnx_path = os.path.join(
                WEIGHTS_DIR,
                os.path.splitext(os.path.basename(self.yolo_model_path))[0] + ".onnx"
            )

            print(f"[INFO] Exporting to ONNX: {onnx_path}")
            model.export(
                format="onnx",
                imgsz=(self.input_height, self.input_width),
                simplify=simplify,
                opset=12,
                dynamic=False
            )

            if os.path.exists(onnx_path):
                print(f"[INFO] ONNX model exported: {onnx_path}")
                return onnx_path
            else:
                print("[ERROR] ONNX export failed")
                return None

        except ImportError:
            print("[ERROR] ultralytics not installed")
            return None
        except Exception as e:
            print(f"[ERROR] ONNX export failed: {e}")
            return None

    def collect_calibration_data(
        self,
        source_images: List[str],
        num_iterations: int = 2
    ) -> List[str]:
        if not self.use_hard_example_mining or not self.hard_miner:
            return source_images

        try:
            from ultralytics import YOLO
            model = YOLO(self.yolo_model_path)

            calibrator = QuantizationCalibrator(
                model=model,
                calibration_images=source_images,
                hard_example_miner=self.hard_miner,
                input_shape=(1, 3, self.input_height, self.input_width)
            )

            calibrated_images = calibrator.iterative_calibration(
                source_images,
                max_iterations=num_iterations
            )

            print(f"[INFO] Calibration data collection complete")
            print(f"[INFO] Original: {len(source_images)} images")
            print(f"[INFO] After hard mining: {len(calibrated_images)} images")

            return calibrated_images

        except Exception as e:
            print(f"[WARN] Hard example mining failed: {e}")
            return source_images

    def export_to_tensorrt(
        self,
        onnx_path: Optional[str] = None,
        collect_hard_examples: bool = True,
        calibration_images: Optional[List[str]] = None
    ) -> bool:
        if onnx_path is None:
            onnx_path = self.export_to_onnx()
            if onnx_path is None:
                return False

        if not os.path.exists(onnx_path):
            print(f"[ERROR] ONNX model not found: {onnx_path}")
            return False

        if self.int8 and collect_hard_examples and self.use_hard_example_mining:
            calib_images = calibration_images or self.calibration_images
            if calib_images:
                print(f"[INFO] Collecting hard examples for INT8 calibration...")
                self.calibration_images = self.collect_calibration_data(calib_images)
            else:
                print("[WARN] No calibration images provided for hard example mining")

        try:
            import tensorrt as trt

            TRT_LOGGER = trt.Logger(trt.Logger.INFO)
            builder = trt.Builder(TRT_LOGGER)
            network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            network = builder.create_network(network_flags)
            parser = trt.OnnxParser(network, TRT_LOGGER)

            print(f"[INFO] Parsing ONNX model: {onnx_path}")
            with open(onnx_path, "rb") as f:
                if not parser.parse(f.read()):
                    print("[ERROR] Failed to parse ONNX model")
                    for i in range(parser.num_errors):
                        print(f"  Parser error {i}: {parser.get_error(i)}")
                    return False

            config = builder.create_builder_config()
            config.max_workspace_size = 1 << 30

            if self.fp16:
                if builder.platform_has_fast_fp16:
                    print("[INFO] Enabling FP16 precision")
                    config.set_flag(trt.BuilderFlag.FP16)
                else:
                    print("[WARN] FP16 not supported on this platform")

            if self.int8:
                if builder.platform_has_fast_int8:
                    print("[INFO] Enabling INT8 precision")
                    config.set_flag(trt.BuilderFlag.INT8)

                    calib_images = calibration_images or self.calibration_images
                    if calib_images:
                        print(f"[INFO] Using {len(calib_images)} images for calibration")
                        calibrator = self._create_int8_calibrator(calib_images)
                        if calibrator:
                            config.int8_calibrator = calibrator
                else:
                    print("[WARN] INT8 not supported on this platform")

            profile = builder.create_optimization_profile()
            for i in range(network.num_inputs):
                input_tensor = network.get_input(i)
                profile.set_shape(
                    input_tensor.name,
                    (1, 3, self.input_height, self.input_width),
                    (1, 3, self.input_height, self.input_width),
                    (1, 3, self.input_height, self.input_width)
                )
            config.add_optimization_profile(profile)

            print(f"[INFO] Building TensorRT engine: {self.trt_engine_path}")
            serialized_engine = builder.build_serialized_network(network, config)

            if serialized_engine is None:
                print("[ERROR] Failed to build TensorRT engine")
                return False

            os.makedirs(os.path.dirname(self.trt_engine_path), exist_ok=True)
            with open(self.trt_engine_path, "wb") as f:
                f.write(serialized_engine)

            print(f"[INFO] TensorRT engine saved: {self.trt_engine_path}")

            if self.hard_miner:
                self.hard_miner.save_annotations()

            return True

        except ImportError:
            print("[ERROR] TensorRT not installed")
            return False
        except Exception as e:
            print(f"[ERROR] TensorRT export failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _create_int8_calibrator(self, calibration_images: Optional[List[str]] = None):
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit

            images = calibration_images or self.calibration_images

            class Int8Calibrator(trt.IInt8EntropyCalibrator2):
                def __init__(self, calib_images, input_shape, cache_file):
                    trt.IInt8EntropyCalibrator2.__init__(self)
                    self.calibration_images = calib_images
                    self.input_shape = input_shape
                    self.cache_file = cache_file
                    self.current_idx = 0
                    self.d_input = cuda.mem_alloc(
                        int(np.prod(input_shape)) * np.float32().nbytes
                    )

                def get_batch_size(self):
                    return 1

                def get_batch(self, names):
                    if self.current_idx >= len(self.calibration_images):
                        return None

                    img_path = self.calibration_images[self.current_idx]
                    img = cv2.imread(img_path)
                    if img is None:
                        self.current_idx += 1
                        return self.get_batch(names)

                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    img = cv2.resize(img, (self.input_shape[3], self.input_shape[2]))
                    img = img.astype(np.float32) / 255.0
                    img = np.transpose(img, (2, 0, 1))
                    img = np.ascontiguousarray(img)
                    img = np.expand_dims(img, axis=0)

                    cuda.memcpy_htod(self.d_input, img)
                    self.current_idx += 1
                    return [int(self.d_input)]

                def read_calibration_cache(self):
                    if os.path.exists(self.cache_file):
                        with open(self.cache_file, "rb") as f:
                            return f.read()
                    return None

                def write_calibration_cache(self, cache):
                    with open(self.cache_file, "wb") as f:
                        f.write(cache)

            cache_file = os.path.join(TRT_ENGINE_DIR, "calibration_cache.bin")
            input_shape = (1, 3, self.input_height, self.input_width)

            return Int8Calibrator(images, input_shape, cache_file)

        except ImportError:
            print("[WARN] PyCUDA not available for INT8 calibration")
            return None

    def quantize_model(
        self,
        collect_hard_examples: bool = True,
        calibration_images: Optional[List[str]] = None
    ) -> bool:
        print("=" * 60)
        print("Model Quantization with Hard Example Calibration")
        print("=" * 60)
        print(f"YOLO model: {self.yolo_model_path}")
        print(f"TensorRT engine: {self.trt_engine_path}")
        print(f"FP16: {self.fp16}")
        print(f"INT8: {self.int8}")
        print(f"Hard example mining: {self.use_hard_example_mining}")
        print(f"Input size: {self.input_width}x{self.input_height}")
        print("=" * 60)

        if not os.path.exists(self.yolo_model_path):
            print(f"[ERROR] YOLO model not found: {self.yolo_model_path}")
            return False

        return self.export_to_tensorrt(
            collect_hard_examples=collect_hard_examples,
            calibration_images=calibration_images
        )

    def get_quantization_info(self) -> dict:
        info = {
            "yolo_model_path": self.yolo_model_path,
            "trt_engine_path": self.trt_engine_path,
            "fp16_enabled": self.fp16,
            "int8_enabled": self.int8,
            "input_size": f"{self.input_width}x{self.input_height}",
            "calibration_images_count": len(self.calibration_images),
            "hard_example_mining": self.use_hard_example_mining
        }

        if self.hard_miner:
            info["hard_examples"] = self.hard_miner.get_stats()

        return info
