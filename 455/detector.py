import torch
import numpy as np
import cv2
from typing import List, Tuple, Optional
from ultralytics import YOLO

from config import Config


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> np.ndarray:
    if len(boxes) == 0:
        return np.array([], dtype=np.int32)

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h

        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]

    return np.array(keep, dtype=np.int32)


class YOLODetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        conf: Optional[float] = None,
        iou: Optional[float] = None,
        imgsz: Optional[int] = None,
        device: Optional[str] = None,
        classes: Optional[List[int]] = None,
        high_res_enable: Optional[bool] = None,
        high_res_scale: Optional[float] = None,
        small_object_area: Optional[int] = None,
    ):
        self.model_path = model_path or Config.YOLO_MODEL_PATH
        self.conf = conf or Config.YOLO_CONF
        self.iou = iou or Config.YOLO_IOU
        self.imgsz = imgsz or Config.YOLO_IMGSZ
        self.device = device or Config.YOLO_DEVICE
        self.classes = classes or Config.YOLO_CLASSES
        self.high_res_enable = high_res_enable if high_res_enable is not None else Config.HIGH_RESOLUTION_ENABLE
        self.high_res_scale = high_res_scale or Config.HIGH_RESOLUTION_SCALE
        self.small_object_area = small_object_area or Config.SMALL_OBJECT_AREA_THRESHOLD
        self.high_res_conf = Config.HIGH_RESOLUTION_CONF

        if not torch.cuda.is_available() and self.device == "cuda":
            self.device = "cpu"

        self.model = YOLO(self.model_path)
        self.model.to(self.device)
        self.class_names = self.model.names

    def _detect_single(
        self,
        frame: np.ndarray,
        conf: Optional[float] = None,
        imgsz: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        conf = conf or self.conf
        imgsz = imgsz or self.imgsz

        results = self.model.predict(
            source=frame,
            conf=conf,
            iou=self.iou,
            imgsz=imgsz,
            device=self.device,
            classes=self.classes,
            verbose=False,
        )

        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            return (
                np.empty((0, 4), dtype=np.float32),
                np.empty((0,), dtype=np.float32),
                np.empty((0,), dtype=np.int32),
            )

        boxes = result.boxes.xyxy.cpu().numpy().astype(np.float32)
        confidences = result.boxes.conf.cpu().numpy().astype(np.float32)
        class_ids = result.boxes.cls.cpu().numpy().astype(np.int32)

        return boxes, confidences, class_ids

    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if not self.high_res_enable:
            boxes, confidences, class_ids = self._detect_single(frame)
            features = self._extract_features(boxes, confidences, class_ids)
            return boxes, confidences, class_ids, features

        h, w = frame.shape[:2]

        boxes_normal, conf_normal, class_normal = self._detect_single(frame)

        if len(boxes_normal) > 0:
            areas = (boxes_normal[:, 2] - boxes_normal[:, 0]) * (boxes_normal[:, 3] - boxes_normal[:, 1])
            small_mask = areas < self.small_object_area
            has_small_objects = np.any(small_mask)
        else:
            has_small_objects = True

        all_boxes = [boxes_normal]
        all_conf = [conf_normal]
        all_class = [class_normal]

        if has_small_objects:
            high_res_boxes, high_res_conf, high_res_class = self._high_resolution_detect(frame)
            if len(high_res_boxes) > 0:
                all_boxes.append(high_res_boxes)
                all_conf.append(high_res_conf)
                all_class.append(high_res_class)

        if len(all_boxes) > 1 or len(all_boxes[0]) > 0:
            merged_boxes = np.vstack(all_boxes) if all_boxes[0].size > 0 else all_boxes[1]
            merged_conf = np.hstack(all_conf) if all_conf[0].size > 0 else all_conf[1]
            merged_class = np.hstack(all_class) if all_class[0].size > 0 else all_class[1]

            if len(merged_boxes) > 0:
                keep = nms(merged_boxes, merged_conf, iou_threshold=self.iou)
                merged_boxes = merged_boxes[keep]
                merged_conf = merged_conf[keep]
                merged_class = merged_class[keep]
        else:
            merged_boxes = np.empty((0, 4), dtype=np.float32)
            merged_conf = np.empty((0,), dtype=np.float32)
            merged_class = np.empty((0,), dtype=np.int32)

        features = self._extract_features(merged_boxes, merged_conf, merged_class)

        return merged_boxes, merged_conf, merged_class, features

    def _high_resolution_detect(
        self,
        frame: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        h, w = frame.shape[:2]
        scale = self.high_res_scale

        crop_size = min(h, w) // 2
        stride = crop_size // 2

        high_res_boxes = []
        high_res_conf = []
        high_res_class = []

        crops = []
        offsets = []

        for y in range(0, h - crop_size + 1, stride):
            for x in range(0, w - crop_size + 1, stride):
                crop = frame[y:y + crop_size, x:x + crop_size]
                crops.append(crop)
                offsets.append((x, y))

        if h > crop_size:
            y = h - crop_size
            for x in range(0, w - crop_size + 1, stride):
                crop = frame[y:y + crop_size, x:x + crop_size]
                crops.append(crop)
                offsets.append((x, y))

        if w > crop_size:
            x = w - crop_size
            for y in range(0, h - crop_size + 1, stride):
                crop = frame[y:y + crop_size, x:x + crop_size]
                crops.append(crop)
                offsets.append((x, y))

        for crop, (offset_x, offset_y) in zip(crops, offsets):
            crop_h, crop_w = crop.shape[:2]
            new_h, new_w = int(crop_h * scale), int(crop_w * scale)

            if new_h < 64 or new_w < 64:
                continue

            resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            boxes, conf, cls = self._detect_single(
                resized,
                conf=self.high_res_conf,
                imgsz=min(self.imgsz * 2, 1280),
            )

            if len(boxes) == 0:
                continue

            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            small_mask = areas < (self.small_object_area * scale * scale * 1.5)
            boxes = boxes[small_mask]
            conf = conf[small_mask]
            cls = cls[small_mask]

            if len(boxes) == 0:
                continue

            boxes[:, 0] = boxes[:, 0] / scale + offset_x
            boxes[:, 1] = boxes[:, 1] / scale + offset_y
            boxes[:, 2] = boxes[:, 2] / scale + offset_x
            boxes[:, 3] = boxes[:, 3] / scale + offset_y

            boxes[:, 0] = np.clip(boxes[:, 0], 0, w)
            boxes[:, 1] = np.clip(boxes[:, 1], 0, h)
            boxes[:, 2] = np.clip(boxes[:, 2], 0, w)
            boxes[:, 3] = np.clip(boxes[:, 3], 0, h)

            valid = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
            boxes = boxes[valid]
            conf = conf[valid]
            cls = cls[valid]

            if len(boxes) > 0:
                high_res_boxes.append(boxes)
                high_res_conf.append(conf)
                high_res_class.append(cls)

        if len(high_res_boxes) > 0:
            merged_hr_boxes = np.vstack(high_res_boxes)
            merged_hr_conf = np.hstack(high_res_conf)
            merged_hr_class = np.hstack(high_res_class)

            if len(merged_hr_boxes) > 0:
                keep = nms(merged_hr_boxes, merged_hr_conf, iou_threshold=0.3)
                return merged_hr_boxes[keep], merged_hr_conf[keep], merged_hr_class[keep]

        return (
            np.empty((0, 4), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.empty((0,), dtype=np.int32),
        )

    def _extract_features(
        self,
        boxes: np.ndarray,
        confidences: np.ndarray,
        class_ids: np.ndarray,
    ) -> np.ndarray:
        if len(boxes) == 0:
            return np.empty((0, 128), dtype=np.float32)

        widths = boxes[:, 2] - boxes[:, 0]
        heights = boxes[:, 3] - boxes[:, 1]
        centers_x = (boxes[:, 0] + boxes[:, 2]) / 2
        centers_y = (boxes[:, 1] + boxes[:, 3]) / 2
        areas = widths * heights
        aspect_ratios = widths / (heights + 1e-6)

        class_onehot = np.zeros((len(class_ids), 80), dtype=np.float32)
        for i, cid in enumerate(class_ids):
            if 0 <= cid < 80:
                class_onehot[i, cid] = 1.0

        raw_features = np.column_stack([
            widths,
            heights,
            centers_x,
            centers_y,
            areas,
            aspect_ratios,
            confidences,
        ])

        features = np.zeros((len(raw_features), 128), dtype=np.float32)
        features[:, :7] = raw_features
        features[:, 7:87] = class_onehot[:, :80]

        if len(raw_features) > 1:
            mean = np.mean(raw_features, axis=0)
            std = np.std(raw_features, axis=0) + 1e-6
            features[:, :7] = (raw_features - mean) / std

        features = features / (np.linalg.norm(features, axis=1, keepdims=True) + 1e-6)

        return features

    def get_class_name(self, class_id: int) -> str:
        return self.class_names.get(int(class_id), f"class_{class_id}")
