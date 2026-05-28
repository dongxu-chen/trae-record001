import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time

from config import (
    TRAFFIC_SIGN_CLASSES, CLASS_ZH_CN, CLASS_CATEGORIES,
    YOLO_MODEL_PATH, INPUT_WIDTH, INPUT_HEIGHT,
    CONF_THRESHOLD, IOU_THRESHOLD, MAX_DETECTIONS
)


@dataclass
class DetectionResult:
    bbox: List[int]
    confidence: float
    class_id: int
    class_name: str
    class_name_zh: str
    category: str
    is_small_target: bool = False
    scale: str = "normal"

    def to_dict(self) -> Dict:
        return {
            "bbox": self.bbox,
            "confidence": round(self.confidence, 4),
            "class_id": self.class_id,
            "class_name": self.class_name,
            "class_name_zh": self.class_name_zh,
            "category": self.category,
            "is_small_target": self.is_small_target,
            "scale": self.scale
        }


class EnhancedFPN:
    def __init__(
        self,
        num_classes: int = 40,
        small_target_threshold: int = 32,
        high_res_scale: float = 2.0
    ):
        self.num_classes = num_classes
        self.small_target_threshold = small_target_threshold
        self.high_res_scale = high_res_scale
        self.anchor_sizes = {
            "small": [8, 16, 32],
            "medium": [32, 64, 128],
            "large": [64, 128, 256]
        }

    def is_small_target(self, bbox: List[int]) -> bool:
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        return max(w, h) < self.small_target_threshold

    def enhance_small_targets(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        h, w = image.shape[:2]
        new_h = int(h * self.high_res_scale)
        new_w = int(w * self.high_res_scale)
        enhanced = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        return enhanced, self.high_res_scale

    def fusion_detections(
        self,
        normal_dets: List[DetectionResult],
        high_res_dets: List[DetectionResult],
        scale_factor: float
    ) -> List[DetectionResult]:
        scaled_high_res = []
        for det in high_res_dets:
            scaled_bbox = [
                int(det.bbox[0] / scale_factor),
                int(det.bbox[1] / scale_factor),
                int(det.bbox[2] / scale_factor),
                int(det.bbox[3] / scale_factor)
            ]
            scaled_det = DetectionResult(
                bbox=scaled_bbox,
                confidence=det.confidence,
                class_id=det.class_id,
                class_name=det.class_name,
                class_name_zh=det.class_name_zh,
                category=det.category,
                is_small_target=self.is_small_target(scaled_bbox),
                scale="high_res"
            )
            scaled_high_res.append(scaled_det)

        normal_dets = [
            DetectionResult(
                bbox=d.bbox,
                confidence=d.confidence,
                class_id=d.class_id,
                class_name=d.class_name,
                class_name_zh=d.class_name_zh,
                category=d.category,
                is_small_target=self.is_small_target(d.bbox),
                scale="normal"
            )
            for d in normal_dets
        ]

        all_dets = normal_dets + scaled_high_res
        all_dets = self._weighted_nms(all_dets)
        return all_dets

    def _weighted_nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        if len(detections) == 0:
            return []

        high_res_weight = 1.2
        for det in detections:
            if det.scale == "high_res" and det.is_small_target:
                det.confidence = min(det.confidence * high_res_weight, 1.0)

        detections.sort(key=lambda x: x.confidence, reverse=True)
        boxes = np.array([d.bbox for d in detections])
        scores = np.array([d.confidence for d in detections])

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)

        order = scores.argsort()[::-1]
        keep = []
        suppressed = set()

        for i in range(len(order)):
            if order[i] in suppressed:
                continue
            keep.append(order[i])

            for j in range(i + 1, len(order)):
                if order[j] in suppressed:
                    continue

                xx1 = max(x1[order[i]], x1[order[j]])
                yy1 = max(y1[order[i]], y1[order[j]])
                xx2 = min(x2[order[i]], x2[order[j]])
                yy2 = min(y2[order[i]], y2[order[j]])

                w = max(0.0, xx2 - xx1)
                h = max(0.0, yy2 - yy1)
                inter = w * h

                if inter > 0:
                    iou = inter / (areas[order[i]] + areas[order[j]] - inter)

                    det_i = detections[order[i]]
                    det_j = detections[order[j]]

                    if iou > IOU_THRESHOLD * 0.8:
                        if det_i.scale == "high_res" and det_i.is_small_target:
                            suppressed.add(order[j])
                        elif det_j.scale == "high_res" and det_j.is_small_target:
                            suppressed.add(order[i])
                            keep[-1] = order[j]
                        elif det_i.confidence > det_j.confidence:
                            suppressed.add(order[j])
                        else:
                            suppressed.add(order[i])
                            keep[-1] = order[j]

        final_dets = [detections[i] for i in keep]
        final_dets.sort(key=lambda x: x.confidence, reverse=True)
        return final_dets[:MAX_DETECTIONS]


class YOLODetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = CONF_THRESHOLD,
        iou_threshold: float = IOU_THRESHOLD,
        input_width: int = INPUT_WIDTH,
        input_height: int = INPUT_HEIGHT,
        max_detections: int = MAX_DETECTIONS,
        use_enhanced_fpn: bool = True,
        small_target_threshold: int = 32,
        high_res_scale: float = 2.0
    ):
        self.model_path = model_path or YOLO_MODEL_PATH
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_width = input_width
        self.input_height = input_height
        self.max_detections = max_detections
        self.use_enhanced_fpn = use_enhanced_fpn
        self.classes = TRAFFIC_SIGN_CLASSES
        self.class_zh = CLASS_ZH_CN
        self._category_map = self._build_category_map()

        self.enhanced_fpn = EnhancedFPN(
            num_classes=len(self.classes),
            small_target_threshold=small_target_threshold,
            high_res_scale=high_res_scale
        ) if use_enhanced_fpn else None

        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
            self._initialized = True
        except ImportError:
            print("[WARN] ultralytics not installed. Install with: pip install ultralytics")
            self._initialized = False
        except Exception as e:
            print(f"[WARN] Failed to load YOLO model: {e}")
            self._initialized = False

    def _build_category_map(self) -> Dict[str, str]:
        category_map = {}
        for category, class_names in CLASS_CATEGORIES.items():
            for class_name in class_names:
                category_map[class_name] = category
        return category_map

    def _get_category(self, class_name: str) -> str:
        return self._category_map.get(class_name, "unknown")

    def _detect_single_scale(
        self,
        image: np.ndarray,
        conf_threshold: float
    ) -> List[DetectionResult]:
        detections = []

        try:
            results = self.model(
                image,
                conf=conf_threshold,
                iou=self.iou_threshold,
                imgsz=(self.input_height, self.input_width),
                max_det=self.max_detections,
                verbose=False
            )

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue

                for box in boxes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())

                    if class_id >= len(self.classes):
                        continue

                    class_name = self.classes[class_id]
                    bbox = [
                        int(xyxy[0]), int(xyxy[1]),
                        int(xyxy[2]), int(xyxy[3])
                    ]

                    detection = DetectionResult(
                        bbox=bbox,
                        confidence=conf,
                        class_id=class_id,
                        class_name=class_name,
                        class_name_zh=self.class_zh.get(class_name, class_name),
                        category=self._get_category(class_name)
                    )
                    detections.append(detection)
        except Exception as e:
            print(f"[ERROR] Detection failed: {e}")

        return detections

    def detect(self, image: np.ndarray, conf_threshold: Optional[float] = None) -> List[DetectionResult]:
        if not self._initialized:
            print("[ERROR] YOLO detector not initialized")
            return []

        conf = conf_threshold or self.conf_threshold
        normal_dets = self._detect_single_scale(image, conf)

        if self.use_enhanced_fpn and self.enhanced_fpn:
            has_small = any(
                self.enhanced_fpn.is_small_target(d.bbox)
                for d in normal_dets
            ) or len(normal_dets) == 0

            if has_small or True:
                high_res_img, scale = self.enhanced_fpn.enhance_small_targets(image)
                high_res_dets = self._detect_single_scale(high_res_img, conf * 0.8)

                if high_res_dets:
                    fused = self.enhanced_fpn.fusion_detections(
                        normal_dets, high_res_dets, scale
                    )
                    return fused

        return [
            DetectionResult(
                bbox=d.bbox,
                confidence=d.confidence,
                class_id=d.class_id,
                class_name=d.class_name,
                class_name_zh=d.class_name_zh,
                category=d.category,
                is_small_target=self.enhanced_fpn.is_small_target(d.bbox) if self.enhanced_fpn else False,
                scale="normal"
            )
            for d in normal_dets
        ]

    def detect_single(self, image: np.ndarray, conf_threshold: Optional[float] = None) -> Optional[DetectionResult]:
        detections = self.detect(image, conf_threshold)
        return detections[0] if detections else None

    def draw_detections(self, image: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        output = image.copy()
        colors = {
            "speed_limit": (0, 0, 255),
            "prohibitory": (0, 0, 255),
            "indicative": (0, 255, 0),
            "warning": (0, 255, 255),
            "unknown": (128, 128, 128)
        }

        small_target_color = (255, 0, 255)

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = colors.get(det.category, (255, 255, 255))

            if det.is_small_target:
                color = small_target_color
                thickness = 3
            else:
                thickness = 2

            cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness)

            scale_tag = " [HR]" if det.scale == "high_res" else ""
            small_tag = " [S]" if det.is_small_target else ""
            label = f"{det.class_name_zh}: {det.confidence:.2f}{scale_tag}{small_tag}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            cv2.rectangle(output, (x1, y1 - label_h - 4), (x1 + label_w + 4, y1), color, -1)
            cv2.putText(output, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return output

    def get_detection_report(self, detections: List[DetectionResult]) -> dict:
        small_count = sum(1 for d in detections if d.is_small_target)
        high_res_count = sum(1 for d in detections if d.scale == "high_res")

        return {
            "total_detections": len(detections),
            "small_targets": small_count,
            "high_res_detections": high_res_count,
            "categories": {},
            "avg_confidence": sum(d.confidence for d in detections) / len(detections) if detections else 0.0
        }
