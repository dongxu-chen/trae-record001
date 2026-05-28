import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math

from detector.yolo_detector import DetectionResult


@dataclass
class DistanceEstimation:
    distance: float
    unit: str
    confidence: float
    method: str
    bbox: List[int]
    class_name: str


@dataclass
class SignDistanceResult:
    detection: DetectionResult
    distance: DistanceEstimation
    depth_map: Optional[np.ndarray] = None


class SignDistanceEstimator:
    def __init__(
        self,
        focal_length: float = 800.0,
        sensor_width: float = 36.0,
        image_width: int = 640,
        image_height: int = 480,
        camera_height: float = 1.5,
        known_sign_sizes: Optional[Dict[str, float]] = None,
        method: str = "pinhole"
    ):
        self.focal_length = focal_length
        self.sensor_width = sensor_width
        self.image_width = image_width
        self.image_height = image_height
        self.camera_height = camera_height
        self.method = method

        self.known_sign_sizes = known_sign_sizes or {
            "speed_limit_20": 0.6,
            "speed_limit_30": 0.6,
            "speed_limit_40": 0.6,
            "speed_limit_50": 0.6,
            "speed_limit_60": 0.6,
            "speed_limit_70": 0.6,
            "speed_limit_80": 0.6,
            "speed_limit_100": 0.6,
            "speed_limit_120": 0.6,
            "stop": 0.6,
            "yield": 0.6,
            "no_entry": 0.6,
            "no_parking": 0.6,
            "pedestrian_crossing": 0.8,
            "roundabout": 0.6,
            "keep_right": 0.6,
            "keep_left": 0.6,
            "road_construction": 1.0,
            "traffic_signals": 0.4,
        }

        self.fx = focal_length * (image_width / sensor_width)
        self.fy = focal_length * (image_height / sensor_width)

        self.cx = image_width / 2
        self.cy = image_height / 2

    def estimate_by_pinhole(
        self,
        bbox: List[int],
        real_size: Optional[float] = None
    ) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        bbox_width = x2 - x1
        bbox_height = y2 - y1

        bbox_center_x = (x1 + x2) / 2
        bbox_center_y = (y1 + y2) / 2

        if real_size is None:
            real_size = 0.6

        if bbox_width <= 0 or bbox_height <= 0:
            return -1, 0.0

        distance = (real_size * self.fx) / max(bbox_width, bbox_height)

        horizontal_offset = (bbox_center_x - self.cx) * distance / self.fx

        return distance, horizontal_offset

    def estimate_by_geometry(
        self,
        bbox: List[int]
    ) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        bbox_bottom_y = y2

        if bbox_bottom_y <= self.cy:
            return -1, 0.0

        angle = math.atan2(bbox_bottom_y - self.cy, self.fy)
        distance = self.camera_height / math.tan(angle)

        bbox_center_x = (x1 + x2) / 2
        horizontal_offset = (bbox_center_x - self.cx) * distance / self.fx

        return distance, horizontal_offset

    def estimate_by_stereo(
        self,
        bbox_left: List[int],
        bbox_right: List[int],
        baseline: float = 0.12
    ) -> float:
        x1_l, y1_l, x2_l, y2_l = bbox_left
        x1_r, y1_r, x2_r, y2_r = bbox_right

        center_x_left = (x1_l + x2_l) / 2
        center_x_right = (x1_r + x2_r) / 2

        disparity = abs(center_x_left - center_x_right)

        if disparity <= 0:
            return -1

        distance = (self.fx * baseline) / disparity
        return distance

    def estimate_distance(
        self,
        detection: DetectionResult,
        image_shape: Tuple[int, int]
    ) -> Optional[SignDistanceResult]:
        x1, y1, x2, y2 = detection.bbox

        real_size = self.known_sign_sizes.get(detection.class_name, 0.6)

        if self.method == "pinhole":
            distance, horizontal_offset = self.estimate_by_pinhole(
                detection.bbox, real_size
            )
            method_used = "pinhole"
        elif self.method == "geometry":
            distance, horizontal_offset = self.estimate_by_geometry(
                detection.bbox
            )
            method_used = "geometry"
        else:
            distance1, offset1 = self.estimate_by_pinhole(detection.bbox, real_size)
            distance2, offset2 = self.estimate_by_geometry(detection.bbox)

            if distance1 > 0 and distance2 > 0:
                distance = (distance1 * 0.6 + distance2 * 0.4)
                horizontal_offset = (offset1 * 0.6 + offset2 * 0.4)
            elif distance1 > 0:
                distance = distance1
                horizontal_offset = offset1
            else:
                distance = distance2
                horizontal_offset = offset2
            method_used = "hybrid"

        if distance <= 0:
            return None

        confidence = self._calculate_confidence(detection, distance)

        return SignDistanceResult(
            detection=detection,
            distance=DistanceEstimation(
                distance=round(distance, 2),
                unit="meters",
                confidence=round(confidence, 4),
                method=method_used,
                bbox=detection.bbox,
                class_name=detection.class_name
            ),
            depth_map=None
        )

    def _calculate_confidence(
        self,
        detection: DetectionResult,
        distance: float
    ) -> float:
        bbox_size = min(
            detection.bbox[2] - detection.bbox[0],
            detection.bbox[3] - detection.bbox[1]
        )

        size_factor = min(1.0, bbox_size / 50.0)
        distance_factor = max(0.3, 1.0 - distance / 100.0)
        det_confidence = detection.confidence

        total_conf = 0.4 * det_confidence + 0.3 * size_factor + 0.3 * distance_factor
        return max(0.1, min(1.0, total_conf))

    def estimate_batch(
        self,
        detections: List[DetectionResult],
        image_shape: Tuple[int, int]
    ) -> List[SignDistanceResult]:
        results = []
        for det in detections:
            dist_result = self.estimate_distance(det, image_shape)
            if dist_result:
                results.append(dist_result)
        return results

    def draw_distance(
        self,
        image: np.ndarray,
        distance_results: List[SignDistanceResult]
    ) -> np.ndarray:
        output = image.copy()

        for result in distance_results:
            x1, y1, x2, y2 = result.detection.bbox
            distance = result.distance.distance
            conf = result.distance.confidence

            color = self._get_distance_color(distance)

            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

            label = f"{distance:.1f}m ({conf:.2f})"
            (label_w, label_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )

            cv2.rectangle(
                output,
                (x1, y2 - label_h - 8),
                (x1 + label_w + 8, y2),
                color,
                -1
            )
            cv2.putText(
                output,
                label,
                (x1 + 4, y2 - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        return output

    def _get_distance_color(self, distance: float) -> Tuple[int, int, int]:
        if distance < 5:
            return (0, 0, 255)
        elif distance < 15:
            return (0, 165, 255)
        elif distance < 30:
            return (0, 255, 255)
        else:
            return (0, 255, 0)


class StereoDepthEstimator:
    def __init__(
        self,
        focal_length: float = 800.0,
        baseline: float = 0.12,
        min_disparity: int = 0,
        num_disparities: int = 128,
        block_size: int = 9
    ):
        self.focal_length = focal_length
        self.baseline = baseline

        self.stereo = cv2.StereoSGBM_create(
            minDisparity=min_disparity,
            numDisparities=num_disparities,
            blockSize=block_size,
            P1=8 * 3 * block_size ** 2,
            P2=32 * 3 * block_size ** 2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=2,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )

    def compute_disparity(
        self,
        left_image: np.ndarray,
        right_image: np.ndarray
    ) -> np.ndarray:
        left_gray = cv2.cvtColor(left_image, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right_image, cv2.COLOR_BGR2GRAY)

        disparity = self.stereo.compute(left_gray, right_gray)
        disparity = disparity.astype(np.float32) / 16.0

        return disparity

    def compute_depth(self, disparity: np.ndarray) -> np.ndarray:
        with np.errstate(divide='ignore'):
            depth = (self.focal_length * self.baseline) / (disparity + 1e-6)

        depth[disparity <= 0] = 0
        depth[depth > 100] = 100

        return depth

    def estimate_distance_from_depth(
        self,
        depth_map: np.ndarray,
        bbox: List[int]
    ) -> float:
        x1, y1, x2, y2 = bbox
        roi = depth_map[y1:y2, x1:x2]

        if roi.size == 0:
            return -1

        valid_depths = roi[roi > 0]
        if valid_depths.size == 0:
            return -1

        median_depth = np.median(valid_depths)
        return float(median_depth)


class ObjectTracking3D:
    def __init__(self, max_age: int = 5):
        self.tracks: Dict[int, Dict] = {}
        self.next_id = 0
        self.max_age = max_age

    def update(
        self,
        detections: List[DetectionResult],
        distances: List[float],
        image_shape: Tuple[int, int]
    ):
        pass
