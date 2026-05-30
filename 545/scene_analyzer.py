import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class SceneType(Enum):
    DARK = "dark"
    INDOOR = "indoor"
    OUTDOOR_DAY = "outdoor_day"
    OUTDOOR_NIGHT = "outdoor_night"
    HIGH_CONTRAST = "high_contrast"
    SUNSET = "sunset"
    NEUTRAL = "neutral"


@dataclass
class SceneFeatures:
    mean_brightness: float = 0.0
    std_brightness: float = 0.0
    dynamic_range: float = 0.0
    percentile_10: float = 0.0
    percentile_50: float = 0.0
    percentile_90: float = 0.0
    color_temperature: float = 0.0
    saturation_mean: float = 0.0
    histogram_peaks: List[float] = field(default_factory=list)
    scene_type: SceneType = SceneType.NEUTRAL
    confidence: float = 0.0


class SceneAnalyzer:
    def __init__(self):
        self.scene_params: Dict[SceneType, Dict[str, Any]] = self._init_scene_params()

    def _init_scene_params(self) -> Dict[SceneType, Dict[str, Any]]:
        return {
            SceneType.DARK: {
                'operator': 'reinhard',
                'params': {
                    'intensity': 2.0,
                    'light_adapt': 0.9,
                    'color_adapt': 0.3,
                    'gamma': 2.2
                }
            },
            SceneType.INDOOR: {
                'operator': 'reinhard',
                'params': {
                    'intensity': 0.5,
                    'light_adapt': 0.7,
                    'color_adapt': 0.5,
                    'gamma': 2.2
                }
            },
            SceneType.OUTDOOR_DAY: {
                'operator': 'aces',
                'params': {
                    'exposure': 0.9,
                    'saturation': 1.1,
                    'gamma': 2.2
                }
            },
            SceneType.OUTDOOR_NIGHT: {
                'operator': 'filmic',
                'params': {
                    'contrast': 1.3,
                    'shoulder': 0.4,
                    'linear': 0.15,
                    'linear_angle': 0.15,
                    'toe_num_a': 0.6,
                    'toe_num_b': 0.005,
                    'toe_den_a': 0.3,
                    'toe_den_b': 0.01,
                    'gamma': 2.2
                }
            },
            SceneType.HIGH_CONTRAST: {
                'operator': 'filmic',
                'params': {
                    'contrast': 0.8,
                    'shoulder': 0.6,
                    'linear': 0.08,
                    'linear_angle': 0.08,
                    'toe_num_a': 0.5,
                    'toe_num_b': 0.015,
                    'toe_den_a': 0.45,
                    'toe_den_b': 0.025,
                    'gamma': 2.2
                }
            },
            SceneType.SUNSET: {
                'operator': 'aces',
                'params': {
                    'exposure': 1.1,
                    'saturation': 1.3,
                    'gamma': 2.2
                }
            },
            SceneType.NEUTRAL: {
                'operator': 'reinhard',
                'params': {
                    'intensity': 0.0,
                    'light_adapt': 1.0,
                    'color_adapt': 0.0,
                    'gamma': 2.2
                }
            }
        }

    def analyze_image(self, hdr_image: np.ndarray) -> SceneFeatures:
        features = SceneFeatures()

        if hdr_image.dtype != np.float32:
            hdr_image = hdr_image.astype(np.float32)

        if len(hdr_image.shape) == 3:
            gray = cv2.cvtColor(hdr_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = hdr_image

        gray_normalized = np.clip(gray, 0, None)
        if gray_normalized.max() > 0:
            gray_normalized = gray_normalized / gray_normalized.max()

        features.mean_brightness = float(np.mean(gray_normalized))
        features.std_brightness = float(np.std(gray_normalized))
        features.percentile_10 = float(np.percentile(gray_normalized, 10))
        features.percentile_50 = float(np.percentile(gray_normalized, 50))
        features.percentile_90 = float(np.percentile(gray_normalized, 90))
        features.dynamic_range = features.percentile_90 - features.percentile_10

        features.color_temperature = self._estimate_color_temperature(hdr_image)
        features.saturation_mean = self._estimate_saturation(hdr_image)
        features.histogram_peaks = self._find_histogram_peaks(gray_normalized)

        scene_type, confidence = self._classify_scene(features)
        features.scene_type = scene_type
        features.confidence = confidence

        return features

    def _estimate_color_temperature(self, img: np.ndarray) -> float:
        if len(img.shape) != 3:
            return 5000.0

        b, g, r = cv2.split(img)
        r_mean = np.mean(r)
        b_mean = np.mean(b)

        if b_mean == 0:
            return 5000.0

        ratio = r_mean / b_mean
        temp = 5000 + (ratio - 1) * 5000
        return float(np.clip(temp, 2000, 10000))

    def _estimate_saturation(self, img: np.ndarray) -> float:
        if len(img.shape) != 3:
            return 0.5

        hsv = cv2.cvtColor(np.clip(img * 255, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1].mean() / 255.0
        return float(saturation)

    def _find_histogram_peaks(self, gray_img: np.ndarray, num_bins: int = 64) -> List[float]:
        hist, bin_edges = np.histogram(gray_img.flatten(), bins=num_bins, range=(0, 1))
        hist = hist.astype(float) / hist.sum()

        peaks = []
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > 0.01:
                peaks.append(float(bin_edges[i]))

        return sorted(peaks, key=lambda x: x, reverse=True)[:3]

    def _classify_scene(self, features: SceneFeatures) -> Tuple[SceneType, float]:
        scores: Dict[SceneType, float] = {}

        brightness = features.mean_brightness
        contrast = features.std_brightness
        dynamic_range = features.dynamic_range
        color_temp = features.color_temperature
        saturation = features.saturation_mean

        scores[SceneType.DARK] = self._calc_score(
            (brightness < 0.2, 0.6),
            (dynamic_range < 0.5, 0.2),
            (saturation < 0.4, 0.2)
        )

        scores[SceneType.OUTDOOR_NIGHT] = self._calc_score(
            (brightness < 0.3, 0.4),
            (dynamic_range > 0.4, 0.3),
            (saturation > 0.3, 0.3)
        )

        scores[SceneType.INDOOR] = self._calc_score(
            (0.2 < brightness < 0.5, 0.5),
            (3000 < color_temp < 6000, 0.3),
            (contrast < 0.3, 0.2)
        )

        scores[SceneType.OUTDOOR_DAY] = self._calc_score(
            (brightness > 0.4, 0.4),
            (dynamic_range > 0.5, 0.3),
            (saturation > 0.4, 0.3)
        )

        scores[SceneType.HIGH_CONTRAST] = self._calc_score(
            (dynamic_range > 0.6, 0.5),
            (contrast > 0.3, 0.3),
            (len(features.histogram_peaks) >= 2, 0.2)
        )

        scores[SceneType.SUNSET] = self._calc_score(
            (color_temp > 6000, 0.4),
            (saturation > 0.5, 0.3),
            (0.2 < brightness < 0.5, 0.3)
        )

        scores[SceneType.NEUTRAL] = 0.3

        best_scene = max(scores.keys(), key=lambda k: scores[k])
        total_score = sum(scores.values())
        confidence = scores[best_scene] / total_score if total_score > 0 else 0.0

        return best_scene, float(confidence)

    def _calc_score(self, *conditions) -> float:
        score = 0.0
        for condition, weight in conditions:
            if condition:
                score += weight
        return score

    def get_scene_params(self, scene_type: SceneType) -> Dict[str, Any]:
        return self.scene_params.get(scene_type, self.scene_params[SceneType.NEUTRAL])

    def set_scene_params(self, scene_type: SceneType, operator: str, params: Dict[str, float]):
        self.scene_params[scene_type] = {
            'operator': operator,
            'params': params.copy()
        }

    def analyze_batch(self, image_paths: List[str]) -> Dict[SceneType, List[str]]:
        from tone_mapping import ToneMapper

        scene_groups: Dict[SceneType, List[str]] = {st: [] for st in SceneType}

        for path in image_paths:
            try:
                img = ToneMapper.load_hdr(path)
                features = self.analyze_image(img)
                scene_groups[features.scene_type].append(path)
            except Exception as e:
                print(f"Error analyzing {path}: {e}")

        return scene_groups

    def get_scene_name(self, scene_type: SceneType) -> str:
        names = {
            SceneType.DARK: "暗部场景",
            SceneType.INDOOR: "室内场景",
            SceneType.OUTDOOR_DAY: "户外日间",
            SceneType.OUTDOOR_NIGHT: "户外夜间",
            SceneType.HIGH_CONTRAST: "高对比度",
            SceneType.SUNSET: "日落场景",
            SceneType.NEUTRAL: "中性场景"
        }
        return names.get(scene_type, scene_type.value)

    def select_optimal_operator(self, features: SceneFeatures) -> Tuple[ToneMappingOperator, Dict[str, float], float]:
        from tone_mapping import ToneMappingOperator

        operator_scores: Dict[ToneMappingOperator, float] = {}

        brightness = features.mean_brightness
        dynamic_range = features.dynamic_range
        contrast = features.std_brightness
        color_temp = features.color_temperature
        saturation = features.saturation_mean

        reinhard_score = self._calc_score(
            (brightness < 0.3, 0.4),
            (contrast < 0.3, 0.3),
            (dynamic_range < 0.5, 0.3)
        )
        operator_scores[ToneMappingOperator.REINHARD] = reinhard_score

        filmic_score = self._calc_score(
            (dynamic_range > 0.5, 0.4),
            (contrast > 0.3, 0.3),
            (brightness > 0.3, 0.3)
        )
        operator_scores[ToneMappingOperator.FILMIC] = filmic_score

        aces_score = self._calc_score(
            (saturation > 0.4, 0.35),
            (color_temp > 5000 or color_temp < 4000, 0.25),
            (brightness > 0.3, 0.2),
            (dynamic_range > 0.4, 0.2)
        )
        operator_scores[ToneMappingOperator.ACES] = aces_score

        best_op = max(operator_scores.keys(), key=lambda k: operator_scores[k])
        total_score = sum(operator_scores.values())
        confidence = operator_scores[best_op] / total_score if total_score > 0 else 0.0

        scene_params = self.get_scene_params(features.scene_type)
        if scene_params['operator'] == best_op.value:
            params = scene_params['params']
        else:
            params = self._get_default_params(best_op)

        return best_op, params, float(confidence)

    def _get_default_params(self, op: ToneMappingOperator) -> Dict[str, float]:
        from tone_mapping import ToneMappingOperator
        defaults = {
            ToneMappingOperator.REINHARD: {
                'intensity': 0.0,
                'light_adapt': 1.0,
                'color_adapt': 0.0,
                'gamma': 2.2
            },
            ToneMappingOperator.FILMIC: {
                'contrast': 1.0,
                'shoulder': 0.5,
                'linear': 0.1,
                'linear_angle': 0.1,
                'toe_num_a': 0.55,
                'toe_num_b': 0.01,
                'toe_den_a': 0.4,
                'toe_den_b': 0.02,
                'gamma': 2.2
            },
            ToneMappingOperator.ACES: {
                'exposure': 1.0,
                'saturation': 1.0,
                'gamma': 2.2
            }
        }
        return defaults.get(op, {})

    def auto_tone_map(self, hdr_image: np.ndarray) -> Tuple[np.ndarray, ToneMappingOperator, Dict[str, float], SceneFeatures]:
        from tone_mapping import ToneMapper

        features = self.analyze_image(hdr_image)
        best_op, params, confidence = self.select_optimal_operator(features)

        tonemapper = ToneMapper(use_gpu=False)
        for name, value in params.items():
            tonemapper.set_param(best_op, name, value)

        result = tonemapper.process(hdr_image, best_op)
        return result, best_op, params, features
