import numpy as np
from typing import Dict, Tuple
from scipy.spatial.distance import euclidean


class ParameterCompressor:
    @staticmethod
    def sigmoid_compress(x: float, midpoint: float = 0.5, steepness: float = 5.0) -> float:
        x_clamped = max(0.0, min(1.0, x))
        return 1.0 / (1.0 + np.exp(-steepness * (x_clamped - midpoint)))

    @staticmethod
    def piecewise_linear(x: float, thresholds: list = None) -> float:
        if thresholds is None:
            thresholds = [(0.0, 0.0), (0.3, 0.5), (0.7, 0.9), (1.0, 1.0)]
        
        x_clamped = max(0.0, min(1.0, x))
        
        for i in range(len(thresholds) - 1):
            x0, y0 = thresholds[i]
            x1, y1 = thresholds[i + 1]
            if x0 <= x_clamped <= x1:
                if x1 - x0 == 0:
                    return y0
                t = (x_clamped - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        
        return x_clamped

    @staticmethod
    def tanh_compress(x: float, scale: float = 2.0) -> float:
        return np.tanh(scale * x)

    @staticmethod
    def soft_clamp(x: float, min_val: float = 0.0, max_val: float = 1.0, 
                   margin: float = 0.1) -> float:
        if x < min_val - margin:
            return min_val
        elif x > max_val + margin:
            return max_val
        elif x < min_val:
            t = (x - (min_val - margin)) / margin
            return min_val * t + min_val * (1 - t)
        elif x > max_val:
            t = (x - max_val) / margin
            return max_val * (1 - t) + max_val * t
        return x


class IrisEdgeDetector:
    @staticmethod
    def fit_ellipse(points: np.ndarray) -> Tuple[np.ndarray, float, float, float]:
        if len(points) < 5:
            center = np.mean(points, axis=0)
            return center, 1.0, 1.0, 0.0
        
        try:
            points_2d = points[:, :2].astype(np.float32)
            (cx, cy), (ma, Mi), angle = cv2.fitEllipse(points_2d)
            return np.array([cx, cy]), ma / 2, Mi / 2, np.radians(angle)
        except:
            center = np.mean(points, axis=0)[:2]
            return center, 1.0, 1.0, 0.0

    @staticmethod
    def get_iris_center_from_edges(iris_edges: np.ndarray) -> np.ndarray:
        if len(iris_edges) < 2:
            return np.mean(iris_edges, axis=0) if len(iris_edges) > 0 else np.zeros(2)
        
        center = np.mean(iris_edges, axis=0)[:2]
        
        if len(iris_edges) >= 4:
            try:
                import cv2
                points_2d = iris_edges[:, :2].astype(np.float32)
                (cx, cy), _ = cv2.minEnclosingCircle(points_2d)
                center = np.array([cx, cy])
            except:
                pass
        
        return center


class ExpressionExtractor:
    def __init__(self):
        self.smoothing_factor = 0.3
        self.prev_expressions = None
        self.compressor = ParameterCompressor()
        self.iris_detector = IrisEdgeDetector()
        
        self.enable_compression = True
        self.compression_method = 'piecewise'
        
        self.compression_thresholds = {
            'mouth_open': [(0.0, 0.0), (0.2, 0.3), (0.5, 0.7), (1.0, 1.0)],
            'jaw_open': [(0.0, 0.0), (0.3, 0.4), (0.6, 0.8), (1.0, 1.0)],
            'smile': [(0.0, 0.0), (0.3, 0.4), (0.7, 0.85), (1.0, 1.0)],
            'frown': [(0.0, 0.0), (0.3, 0.35), (0.7, 0.8), (1.0, 1.0)],
            'default': [(0.0, 0.0), (0.3, 0.5), (0.7, 0.9), (1.0, 1.0)]
        }
        
        self.landmark_indices = {
            'left_eye_top': 386,
            'left_eye_bottom': 374,
            'left_eye_inner': 362,
            'left_eye_outer': 263,
            'left_eye_iris_center': 473,
            'left_eye_iris_top': 475,
            'left_eye_iris_bottom': 477,
            'left_eye_iris_left': 474,
            'left_eye_iris_right': 476,
            
            'right_eye_top': 159,
            'right_eye_bottom': 145,
            'right_eye_inner': 33,
            'right_eye_outer': 133,
            'right_eye_iris_center': 468,
            'right_eye_iris_top': 470,
            'right_eye_iris_bottom': 472,
            'right_eye_iris_left': 469,
            'right_eye_iris_right': 471,
            
            'mouth_upper_lip_top': 13,
            'mouth_lower_lip_bottom': 14,
            'mouth_left_corner': 61,
            'mouth_right_corner': 291,
            'mouth_upper_lip_bottom': 16,
            'mouth_lower_lip_top': 17,
            'mouth_center_top': 0,
            'mouth_center_bottom': 17,
            
            'mouth_upper_lip_left': 37,
            'mouth_upper_lip_right': 267,
            'mouth_lower_lip_left': 84,
            'mouth_lower_lip_right': 314,
            
            'left_eyebrow_inner': 70,
            'left_eyebrow_outer': 105,
            'right_eyebrow_inner': 300,
            'right_eyebrow_outer': 334,
            
            'nose_tip': 1,
            'face_left': 234,
            'face_right': 454,
            'face_top': 10,
            'face_bottom': 152,
            
            'left_cheek': 234,
            'right_cheek': 454,
            'chin': 152
        }

    def _get_point(self, landmarks: list, idx: int, image_shape: Tuple[int, int]) -> np.ndarray:
        h, w = image_shape[:2]
        lm = landmarks[idx]
        return np.array([lm.x * w, lm.y * h, lm.z])

    def _compress_parameter(self, value: float, param_name: str) -> float:
        if not self.enable_compression:
            return value
        
        thresholds = self.compression_thresholds.get(param_name, 
                                                      self.compression_thresholds['default'])
        
        if self.compression_method == 'piecewise':
            return self.compressor.piecewise_linear(value, thresholds)
        elif self.compression_method == 'sigmoid':
            return self.compressor.sigmoid_compress(value)
        elif self.compression_method == 'tanh':
            return self.compressor.tanh_compress(value)
        else:
            return value

    def _normalize_distance(self, distance: float, face_width: float) -> float:
        return min(1.0, max(0.0, distance / face_width if face_width > 0 else 0))

    def _get_face_width(self, landmarks: list, image_shape: Tuple[int, int]) -> float:
        left = self._get_point(landmarks, self.landmark_indices['face_left'], image_shape)
        right = self._get_point(landmarks, self.landmark_indices['face_right'], image_shape)
        return euclidean(left[:2], right[:2])

    def _get_iris_center_precise(self, landmarks: list, eye_side: str, 
                                  image_shape: Tuple[int, int]) -> Tuple[np.ndarray, float, float]:
        if eye_side == 'left':
            iris_indices = [
                self.landmark_indices['left_eye_iris_top'],
                self.landmark_indices['left_eye_iris_bottom'],
                self.landmark_indices['left_eye_iris_left'],
                self.landmark_indices['left_eye_iris_right']
            ]
        else:
            iris_indices = [
                self.landmark_indices['right_eye_iris_top'],
                self.landmark_indices['right_eye_iris_bottom'],
                self.landmark_indices['right_eye_iris_left'],
                self.landmark_indices['right_eye_iris_right']
            ]
        
        iris_points = np.array([
            self._get_point(landmarks, idx, image_shape) for idx in iris_indices
        ])
        
        iris_center = self.iris_detector.get_iris_center_from_edges(iris_points)
        
        iris_width = euclidean(iris_points[2][:2], iris_points[3][:2])
        iris_height = euclidean(iris_points[0][:2], iris_points[1][:2])
        
        return iris_center, iris_width, iris_height

    def extract_eye_params(self, landmarks: list, image_shape: Tuple[int, int]) -> Dict[str, float]:
        face_width = self._get_face_width(landmarks, image_shape)
        
        left_top = self._get_point(landmarks, self.landmark_indices['left_eye_top'], image_shape)
        left_bottom = self._get_point(landmarks, self.landmark_indices['left_eye_bottom'], image_shape)
        left_inner = self._get_point(landmarks, self.landmark_indices['left_eye_inner'], image_shape)
        left_outer = self._get_point(landmarks, self.landmark_indices['left_eye_outer'], image_shape)
        
        right_top = self._get_point(landmarks, self.landmark_indices['right_eye_top'], image_shape)
        right_bottom = self._get_point(landmarks, self.landmark_indices['right_eye_bottom'], image_shape)
        right_inner = self._get_point(landmarks, self.landmark_indices['right_eye_inner'], image_shape)
        right_outer = self._get_point(landmarks, self.landmark_indices['right_eye_outer'], image_shape)
        
        left_eye_open = euclidean(left_top[:2], left_bottom[:2])
        left_eye_width = euclidean(left_inner[:2], left_outer[:2])
        left_eye_open_ratio = left_eye_open / left_eye_width if left_eye_width > 0 else 0
        
        right_eye_open = euclidean(right_top[:2], right_bottom[:2])
        right_eye_width = euclidean(right_inner[:2], right_outer[:2])
        right_eye_open_ratio = right_eye_open / right_eye_width if right_eye_width > 0 else 0
        
        left_iris_center, left_iris_w, left_iris_h = self._get_iris_center_precise(
            landmarks, 'left', image_shape
        )
        right_iris_center, right_iris_w, right_iris_h = self._get_iris_center_precise(
            landmarks, 'right', image_shape
        )
        
        left_eye_center_x = (left_inner[0] + left_outer[0]) / 2
        left_eye_center_y = (left_inner[1] + left_outer[1]) / 2
        right_eye_center_x = (right_inner[0] + right_outer[0]) / 2
        right_eye_center_y = (right_inner[1] + right_outer[1]) / 2
        
        left_eye_x = (left_iris_center[0] - left_eye_center_x) / (left_eye_width / 2) if left_eye_width > 0 else 0
        left_eye_y = (left_iris_center[1] - left_eye_center_y) / (left_eye_open / 2) if left_eye_open > 0 else 0
        right_eye_x = (right_iris_center[0] - right_eye_center_x) / (right_eye_width / 2) if right_eye_width > 0 else 0
        right_eye_y = (right_iris_center[1] - right_eye_center_y) / (right_eye_open / 2) if right_eye_open > 0 else 0
        
        eye_x = (left_eye_x + right_eye_x) / 2
        eye_y = (left_eye_y + right_eye_y) / 2
        
        blink_left = max(0.0, min(1.0, 1.0 - (left_eye_open_ratio - 0.15) / 0.25))
        blink_right = max(0.0, min(1.0, 1.0 - (right_eye_open_ratio - 0.15) / 0.25))
        
        eye_open_left = max(0.0, min(1.0, (left_eye_open_ratio - 0.1) / 0.3))
        eye_open_right = max(0.0, min(1.0, (right_eye_open_ratio - 0.1) / 0.3))
        
        blink_left = self._compress_parameter(blink_left, 'blink')
        blink_right = self._compress_parameter(blink_right, 'blink')
        
        return {
            'eye_open_left': eye_open_left,
            'eye_open_right': eye_open_right,
            'eye_x': max(-1.0, min(1.0, eye_x)),
            'eye_y': max(-1.0, min(1.0, eye_y)),
            'blink_left': blink_left,
            'blink_right': blink_right,
            'iris_width_left': left_iris_w,
            'iris_width_right': right_iris_w
        }

    def extract_mouth_params(self, landmarks: list, image_shape: Tuple[int, int]) -> Dict[str, float]:
        face_width = self._get_face_width(landmarks, image_shape)
        
        upper_lip_top = self._get_point(landmarks, self.landmark_indices['mouth_upper_lip_top'], image_shape)
        lower_lip_bottom = self._get_point(landmarks, self.landmark_indices['mouth_lower_lip_bottom'], image_shape)
        upper_lip_bottom = self._get_point(landmarks, self.landmark_indices['mouth_upper_lip_bottom'], image_shape)
        lower_lip_top = self._get_point(landmarks, self.landmark_indices['mouth_lower_lip_top'], image_shape)
        mouth_left = self._get_point(landmarks, self.landmark_indices['mouth_left_corner'], image_shape)
        mouth_right = self._get_point(landmarks, self.landmark_indices['mouth_right_corner'], image_shape)
        mouth_center_top = self._get_point(landmarks, self.landmark_indices['mouth_center_top'], image_shape)
        
        mouth_open = euclidean(upper_lip_bottom[:2], lower_lip_top[:2])
        mouth_width = euclidean(mouth_left[:2], mouth_right[:2])
        
        mouth_open_ratio = mouth_open / mouth_width if mouth_width > 0 else 0
        jaw_open = euclidean(upper_lip_top[:2], lower_lip_bottom[:2]) / face_width if face_width > 0 else 0
        
        mouth_center_y = (mouth_left[1] + mouth_right[1]) / 2
        smile_ratio = (mouth_center_y - mouth_center_top[1]) / mouth_width if mouth_width > 0 else 0
        
        mouth_wide = (mouth_width / face_width - 0.3) / 0.15 if face_width > 0 else 0
        
        upper_lip_left = self._get_point(landmarks, self.landmark_indices['mouth_upper_lip_left'], image_shape)
        upper_lip_right = self._get_point(landmarks, self.landmark_indices['mouth_upper_lip_right'], image_shape)
        lower_lip_left = self._get_point(landmarks, self.landmark_indices['mouth_lower_lip_left'], image_shape)
        lower_lip_right = self._get_point(landmarks, self.landmark_indices['mouth_lower_lip_right'], image_shape)
        
        lip_height_left = euclidean(upper_lip_left[:2], lower_lip_left[:2]) / mouth_width if mouth_width > 0 else 0
        lip_height_right = euclidean(upper_lip_right[:2], lower_lip_right[:2]) / mouth_width if mouth_width > 0 else 0
        lip_asymmetry = abs(lip_height_left - lip_height_right)
        
        mouth_open_val = max(0.0, min(1.0, mouth_open_ratio / 0.4))
        jaw_open_val = max(0.0, min(1.0, (jaw_open - 0.15) / 0.2))
        mouth_wide_val = max(0.0, min(1.0, mouth_wide))
        mouth_narrow_val = max(0.0, min(1.0, -mouth_wide))
        smile_val = max(0.0, min(1.0, (smile_ratio + 0.1) / 0.2))
        frown_val = max(0.0, min(1.0, (-smile_ratio - 0.05) / 0.15))
        
        mouth_open_val = self._compress_parameter(mouth_open_val, 'mouth_open')
        jaw_open_val = self._compress_parameter(jaw_open_val, 'jaw_open')
        smile_val = self._compress_parameter(smile_val, 'smile')
        frown_val = self._compress_parameter(frown_val, 'frown')
        
        return {
            'mouth_open': mouth_open_val,
            'jaw_open': jaw_open_val,
            'mouth_wide': mouth_wide_val,
            'mouth_narrow': mouth_narrow_val,
            'smile': smile_val,
            'frown': frown_val,
            'lip_asymmetry': lip_asymmetry
        }

    def extract_eyebrow_params(self, landmarks: list, image_shape: Tuple[int, int]) -> Dict[str, float]:
        face_width = self._get_face_width(landmarks, image_shape)
        
        left_inner = self._get_point(landmarks, self.landmark_indices['left_eyebrow_inner'], image_shape)
        left_outer = self._get_point(landmarks, self.landmark_indices['left_eyebrow_outer'], image_shape)
        right_inner = self._get_point(landmarks, self.landmark_indices['right_eyebrow_inner'], image_shape)
        right_outer = self._get_point(landmarks, self.landmark_indices['right_eyebrow_outer'], image_shape)
        
        nose_tip = self._get_point(landmarks, self.landmark_indices['nose_tip'], image_shape)
        face_top = self._get_point(landmarks, self.landmark_indices['face_top'], image_shape)
        
        face_height = euclidean(face_top[:2], nose_tip[:2])
        
        left_inner_height = (nose_tip[1] - left_inner[1]) / face_height if face_height > 0 else 0
        left_outer_height = (nose_tip[1] - left_outer[1]) / face_height if face_height > 0 else 0
        right_inner_height = (nose_tip[1] - right_inner[1]) / face_height if face_height > 0 else 0
        right_outer_height = (nose_tip[1] - right_outer[1]) / face_height if face_height > 0 else 0
        
        brow_inner_up = ((left_inner_height + right_inner_height) / 2 - 0.5) / 0.15
        brow_outer_up = ((left_outer_height + right_outer_height) / 2 - 0.5) / 0.15
        brow_left_up = (left_inner_height - 0.5) / 0.15
        brow_right_up = (right_inner_height - 0.5) / 0.15
        
        return {
            'brow_inner_up': max(-1.0, min(1.0, brow_inner_up)),
            'brow_outer_up': max(-1.0, min(1.0, brow_outer_up)),
            'brow_left_up': max(-1.0, min(1.0, brow_left_up)),
            'brow_right_up': max(-1.0, min(1.0, brow_right_up))
        }

    def extract_all_expressions(self, landmarks: list, image_shape: Tuple[int, int]) -> Dict[str, float]:
        eye_params = self.extract_eye_params(landmarks, image_shape)
        mouth_params = self.extract_mouth_params(landmarks, image_shape)
        eyebrow_params = self.extract_eyebrow_params(landmarks, image_shape)
        
        all_params = {**eye_params, **mouth_params, **eyebrow_params}
        
        if self.prev_expressions is not None:
            for key in all_params:
                if key in self.prev_expressions:
                    all_params[key] = (
                        self.smoothing_factor * all_params[key] +
                        (1 - self.smoothing_factor) * self.prev_expressions[key]
                    )
        
        self.prev_expressions = all_params.copy()
        
        return all_params
