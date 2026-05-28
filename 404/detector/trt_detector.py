import cv2
import numpy as np
from typing import List, Optional, Dict, Any
import time
import os

from config import (
    TRAFFIC_SIGN_CLASSES, CLASS_ZH_CN, CLASS_CATEGORIES,
    TRT_ENGINE_PATH, INPUT_WIDTH, INPUT_HEIGHT,
    CONF_THRESHOLD, IOU_THRESHOLD, MAX_DETECTIONS
)
from .yolo_detector import DetectionResult


class TRTDetector:
    def __init__(
        self,
        engine_path: Optional[str] = None,
        conf_threshold: float = CONF_THRESHOLD,
        iou_threshold: float = IOU_THRESHOLD,
        input_width: int = INPUT_WIDTH,
        input_height: int = INPUT_HEIGHT,
        max_detections: int = MAX_DETECTIONS,
        device: int = 0
    ):
        self.engine_path = engine_path or TRT_ENGINE_PATH
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_width = input_width
        self.input_height = input_height
        self.max_detections = max_detections
        self.device = device
        self.classes = TRAFFIC_SIGN_CLASSES
        self.class_zh = CLASS_ZH_CN
        self._category_map = self._build_category_map()

        self._trt_available = False
        self._engine = None
        self._context = None
        self._input_shape = None
        self._output_shape = None
        self._inputs = []
        self._outputs = []
        self._stream = None

        self._init_tensorrt()

    def _build_category_map(self) -> Dict[str, str]:
        category_map = {}
        for category, class_names in CLASS_CATEGORIES.items():
            for class_name in class_names:
                category_map[class_name] = category
        return category_map

    def _get_category(self, class_name: str) -> str:
        return self._category_map.get(class_name, "unknown")

    def _init_tensorrt(self):
        try:
            import tensorrt as trt
            import pycuda.driver as cuda
            import pycuda.autoinit

            TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

            if not os.path.exists(self.engine_path):
                print(f"[WARN] TensorRT engine not found: {self.engine_path}")
                print("[INFO] Please export YOLOv8 to TensorRT engine first.")
                print("[INFO] Using YOLO detector as fallback.")
                return

            runtime = trt.Runtime(TRT_LOGGER)

            with open(self.engine_path, "rb") as f:
                engine_data = f.read()

            self._engine = runtime.deserialize_cuda_engine(engine_data)
            self._context = self._engine.create_execution_context()

            self._stream = cuda.Stream()

            for binding in self._engine:
                size = trt.volume(self._engine.get_binding_shape(binding))
                dtype = trt.nptype(self._engine.get_binding_dtype(binding))
                host_mem = cuda.pagelocked_empty(size, dtype)
                device_mem = cuda.mem_alloc(host_mem.nbytes)

                if self._engine.binding_is_input(binding):
                    self._inputs.append({"host": host_mem, "device": device_mem})
                    self._input_shape = self._engine.get_binding_shape(binding)
                else:
                    self._outputs.append({"host": host_mem, "device": device_mem})
                    self._output_shape = self._engine.get_binding_shape(binding)

            self._trt_available = True
            print(f"[INFO] TensorRT engine loaded: {self.engine_path}")

        except ImportError as e:
            print(f"[WARN] TensorRT/PyCUDA not available: {e}")
            print("[INFO] Install TensorRT for GPU acceleration.")
        except Exception as e:
            print(f"[WARN] Failed to initialize TensorRT: {e}")

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)

        input_img = cv2.resize(image, (self.input_width, self.input_height))
        input_img = input_img.astype(np.float32) / 255.0
        input_img = np.transpose(input_img, (2, 0, 1))
        input_img = np.ascontiguousarray(input_img)
        input_img = np.expand_dims(input_img, axis=0)

        return input_img

    def _postprocess(
        self,
        outputs: np.ndarray,
        original_shape: tuple,
        conf_threshold: float
    ) -> List[DetectionResult]:
        detections = []
        if outputs is None or len(outputs.shape) < 2:
            return detections

        if outputs.shape[1] == 4 + len(self.classes) + 1:
            outputs = outputs[:, 4:]

        orig_h, orig_w = original_shape[:2]
        scale_x = orig_w / self.input_width
        scale_y = orig_h / self.input_height

        for det in outputs[0]:
            cx, cy, w, h = det[:4]
            scores = det[4:]

            class_id = int(np.argmax(scores))
            confidence = float(scores[class_id])

            if confidence < conf_threshold or class_id >= len(self.classes):
                continue

            x1 = int((cx - w / 2) * scale_x)
            y1 = int((cy - h / 2) * scale_y)
            x2 = int((cx + w / 2) * scale_x)
            y2 = int((cy + h / 2) * scale_y)

            x1 = max(0, min(x1, orig_w - 1))
            y1 = max(0, min(y1, orig_h - 1))
            x2 = max(0, min(x2, orig_w - 1))
            y2 = max(0, min(y2, orig_h - 1))

            class_name = self.classes[class_id]
            detection = DetectionResult(
                bbox=[x1, y1, x2, y2],
                confidence=confidence,
                class_id=class_id,
                class_name=class_name,
                class_name_zh=self.class_zh.get(class_name, class_name),
                category=self._get_category(class_name)
            )
            detections.append(detection)

        detections = self._nms(detections)
        detections.sort(key=lambda x: x.confidence, reverse=True)
        return detections[:self.max_detections]

    def _nms(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        if not detections:
            return []

        boxes = np.array([det.bbox for det in detections])
        scores = np.array([det.confidence for det in detections])

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            iou = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(iou <= self.iou_threshold)[0]
            order = order[inds + 1]

        return [detections[i] for i in keep]

    def detect(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> List[DetectionResult]:
        if not self._trt_available:
            print("[WARN] TensorRT not available, cannot perform detection")
            return []

        conf = conf_threshold or self.conf_threshold
        original_shape = image.shape

        input_img = self._preprocess(image)

        np.copyto(self._inputs[0]["host"], input_img.ravel())

        import pycuda.driver as cuda
        cuda.memcpy_htod_async(
            self._inputs[0]["device"],
            self._inputs[0]["host"],
            self._stream
        )

        self._context.execute_async_v2(
            bindings=[inp["device"] for inp in self._inputs] +
                     [out["device"] for out in self._outputs],
            stream_handle=self._stream.handle
        )

        for out in self._outputs:
            cuda.memcpy_dtoh_async(out["host"], out["device"], self._stream)

        self._stream.synchronize()

        outputs = self._outputs[0]["host"].reshape(self._output_shape)

        detections = self._postprocess(outputs, original_shape, conf)
        return detections

    def detect_single(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> Optional[DetectionResult]:
        detections = self.detect(image, conf_threshold)
        return detections[0] if detections else None

    @property
    def is_available(self) -> bool:
        return self._trt_available

    def get_inference_info(self) -> Dict[str, Any]:
        return {
            "tensorrt_available": self._trt_available,
            "engine_path": self.engine_path,
            "input_size": (self.input_width, self.input_height),
            "conf_threshold": self.conf_threshold,
            "iou_threshold": self.iou_threshold
        }
