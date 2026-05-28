import cv2
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass

from detector.yolo_detector import DetectionResult
from config import CONF_THRESHOLD


@dataclass
class StreamFrame:
    frame: np.ndarray
    timestamp: float
    detections: Optional[List[DetectionResult]] = None
    annotated_frame: Optional[np.ndarray] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "detections": [d.to_dict() for d in self.detections] if self.detections else []
        }
