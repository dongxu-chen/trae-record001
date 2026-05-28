import cv2
import numpy as np
from typing import Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum


class RainIntensity(Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


@dataclass
class RainEstimationResult:
    intensity: RainIntensity
    rain_score: float
    rain_density: float
    streak_count: int
    confidence: float
    visualization: np.ndarray = None
    
    def to_dict(self) -> dict:
        return {
            'intensity': self.intensity.value,
            'rain_score': self.rain_score,
            'rain_density': self.rain_density,
            'streak_count': self.streak_count,
            'confidence': self.confidence
        }


class RainStreakDetector:
    def __init__(self, min_streak_length: int = 10, max_streak_width: int = 5):
        self.min_streak_length = min_streak_length
        self.max_streak_width = max_streak_width

    def detect_streaks(self, image: np.ndarray) -> Tuple[np.ndarray, int]:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 7))
        kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 1))
        
        edges = cv2.Canny(gray, 50, 150)
        
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_vertical)
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, kernel_horizontal)
        
        rain_streaks = cv2.subtract(vertical_lines, horizontal_lines)
        
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(rain_streaks, connectivity=8)
        
        valid_streaks = np.zeros_like(rain_streaks)
        streak_count = 0
        
        for i in range(1, num_labels):
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            
            aspect_ratio = height / (width + 1e-6)
            
            if (aspect_ratio > 2.0 and 
                height >= self.min_streak_length and 
                width <= self.max_streak_width):
                valid_streaks[labels == i] = 255
                streak_count += 1
        
        return valid_streaks, streak_count


class RainDensityEstimator:
    def __init__(self):
        pass

    def estimate_density(self, image: np.ndarray, rain_mask: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        rain_pixels = np.sum(rain_mask > 0)
        total_pixels = rain_mask.size
        
        basic_density = rain_pixels / total_pixels
        
        mean_intensity = np.mean(gray[rain_mask > 0]) if rain_pixels > 0 else 0
        intensity_factor = mean_intensity / 255.0
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        
        edge_rain_ratio = np.sum(gradient_mag[rain_mask > 0] > 50) / (rain_pixels + 1e-6)
        
        density = basic_density * (1 + intensity_factor * 0.5) * (1 + edge_rain_ratio * 0.3)
        
        return min(density * 100, 1.0)


class FrequencyDomainAnalyzer:
    def __init__(self):
        pass

    def analyze_rain_frequency(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = 20 * np.log(np.abs(fshift) + 1)
        
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        
        mask_vertical = np.ones((rows, cols), np.uint8)
        mask_vertical[crow-5:crow+5, :] = 0
        
        vertical_energy = np.sum(magnitude * (1 - mask_vertical))
        total_energy = np.sum(magnitude)
        
        rain_frequency_ratio = vertical_energy / (total_energy + 1e-6)
        
        return rain_frequency_ratio * 10


class RainEstimator:
    def __init__(self, thresholds: Dict[str, float] = None):
        self.streak_detector = RainStreakDetector()
        self.density_estimator = RainDensityEstimator()
        self.frequency_analyzer = FrequencyDomainAnalyzer()
        
        self.thresholds = thresholds or {
            'none': 0.30,
            'light': 0.55,
            'medium': 0.80,
            'heavy': float('inf')
        }

    def estimate(self, image: np.ndarray, return_visualization: bool = True) -> RainEstimationResult:
        if image.dtype == np.float32 or image.dtype == np.float64:
            if image.max() <= 1.0:
                image = (image * 255).astype(np.uint8)
        
        rain_mask, streak_count = self.streak_detector.detect_streaks(image)
        
        rain_density = self.density_estimator.estimate_density(image, rain_mask)
        
        freq_score = self.frequency_analyzer.analyze_rain_frequency(image)
        
        rain_score = 0.5 * rain_density + 0.3 * min(streak_count / 100.0, 1.0) + 0.2 * freq_score
        
        if rain_score < self.thresholds['none']:
            intensity = RainIntensity.NONE
            confidence = 1.0 - rain_score / self.thresholds['none']
        elif rain_score < self.thresholds['light']:
            intensity = RainIntensity.LIGHT
            confidence = 1.0 - abs(rain_score - (self.thresholds['none'] + self.thresholds['light']) / 2) / (self.thresholds['light'] - self.thresholds['none'])
        elif rain_score < self.thresholds['medium']:
            intensity = RainIntensity.MEDIUM
            confidence = 1.0 - abs(rain_score - (self.thresholds['light'] + self.thresholds['medium']) / 2) / (self.thresholds['medium'] - self.thresholds['light'])
        else:
            intensity = RainIntensity.HEAVY
            confidence = min(rain_score / self.thresholds['medium'], 1.0)
        
        confidence = max(min(confidence, 1.0), 0.0)
        
        visualization = None
        if return_visualization:
            visualization = self._create_visualization(image, rain_mask, intensity, rain_score)
        
        return RainEstimationResult(
            intensity=intensity,
            rain_score=rain_score,
            rain_density=rain_density,
            streak_count=streak_count,
            confidence=confidence,
            visualization=visualization
        )

    def _create_visualization(self, image: np.ndarray, rain_mask: np.ndarray,
                             intensity: RainIntensity, rain_score: float) -> np.ndarray:
        vis = image.copy()
        
        rain_mask_colored = np.zeros_like(vis)
        rain_mask_colored[:, :, 0] = rain_mask
        
        vis = cv2.addWeighted(vis, 0.7, rain_mask_colored, 0.3, 0)
        
        text = f"Intensity: {intensity.value.upper()}"
        score_text = f"Score: {rain_score:.3f}"
        
        cv2.putText(vis, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(vis, score_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return vis

    def estimate_video(self, video_path: str, sample_interval: int = 10) -> List[RainEstimationResult]:
        results = []
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % sample_interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = self.estimate(frame_rgb, return_visualization=False)
                results.append(result)
            
            frame_count += 1
        
        cap.release()
        return results


def aggregate_video_rain_results(results: List[RainEstimationResult]) -> Dict:
    if not results:
        return {'dominant_intensity': 'none', 'average_score': 0.0}
    
    intensity_counts = {}
    total_score = 0.0
    
    for result in results:
        intensity = result.intensity.value
        intensity_counts[intensity] = intensity_counts.get(intensity, 0) + 1
        total_score += result.rain_score
    
    dominant_intensity = max(intensity_counts.items(), key=lambda x: x[1])[0]
    average_score = total_score / len(results)
    
    return {
        'dominant_intensity': dominant_intensity,
        'average_score': average_score,
        'intensity_distribution': intensity_counts,
        'total_frames': len(results)
    }
