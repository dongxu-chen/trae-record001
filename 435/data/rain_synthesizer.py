import cv2
import numpy as np
from typing import Tuple, Optional
from config import Config


class RainSynthesizer:
    def __init__(self, intensity: str = 'medium'):
        if intensity not in Config.RAIN_INTENSITIES:
            raise ValueError(f"Intensity must be one of {list(Config.RAIN_INTENSITIES.keys())}")
        self.intensity = intensity
        self.params = Config.RAIN_INTENSITIES[intensity]

    def generate_rain_mask(self, image_shape: Tuple[int, int]) -> np.ndarray:
        h, w = image_shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)
        
        num_streaks = np.random.randint(*self.params['num_streaks'])
        
        for _ in range(num_streaks):
            length = np.random.randint(*self.params['length'])
            thickness = np.random.randint(*self.params['thickness'])
            opacity = np.random.uniform(*self.params['opacity'])
            
            angle = np.random.uniform(-30, 30)
            
            start_x = np.random.randint(0, w)
            start_y = np.random.randint(0, h)
            
            end_x = int(start_x + length * np.sin(np.radians(angle)))
            end_y = int(start_y + length * np.cos(np.radians(angle)))
            
            color = opacity
            cv2.line(mask, (start_x, start_y), (end_x, end_y), color, thickness)
        
        mask = cv2.GaussianBlur(mask, (3, 3), 0)
        return mask

    def add_rain(self, image: np.ndarray) -> np.ndarray:
        if image.dtype != np.float32:
            image = image.astype(np.float32) / 255.0
        
        rain_mask = self.generate_rain_mask(image.shape)
        
        rainy_image = image.copy()
        for c in range(3):
            rainy_image[:, :, c] = np.clip(image[:, :, c] + rain_mask * 0.7, 0, 1)
        
        return rainy_image

    def __call__(self, image: np.ndarray) -> np.ndarray:
        return self.add_rain(image)


class RandomRainSynthesizer:
    def __init__(self):
        self.intensities = list(Config.RAIN_INTENSITIES.keys())
    
    def __call__(self, image: np.ndarray) -> Tuple[np.ndarray, str]:
        intensity = np.random.choice(self.intensities)
        synthesizer = RainSynthesizer(intensity)
        rainy_image = synthesizer(image)
        return rainy_image, intensity
