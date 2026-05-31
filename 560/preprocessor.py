import cv2
import numpy as np
from typing import List, Tuple
from config import Config


class ImagePreprocessor:
    def __init__(self, image_size: int = Config.IMAGE_SIZE):
        self.image_size = image_size
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2)
        
        binary = self._remove_noise(binary)
        binary = self._center_char(binary)
        
        return binary
    
    def _remove_noise(self, binary: np.ndarray) -> np.ndarray:
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        if num_labels <= 1:
            return binary
        
        areas = stats[:, cv2.CC_STAT_AREA]
        max_area_idx = np.argmax(areas[1:]) + 1
        
        cleaned = np.zeros_like(binary.shape, dtype=np.uint8)
        cleaned[labels == max_area_idx] = 255
        
        return cleaned
    
    def _center_char(self, binary: np.ndarray) -> np.ndarray:
        coords = cv2.findNonZero(binary)
        if coords is None:
            return binary
        
        x, y, w, h = cv2.boundingRect(coords)
        center_x = x + w // 2
        center_y = y + h // 2
        
        canvas_center = binary.shape[1] // 2, binary.shape[0] // 2
        
        offset_x = canvas_center[0] - center_x
        offset_y = canvas_center[1] - center_y
        
        translation_matrix = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
        centered = cv2.warpAffine(binary, translation_matrix, (binary.shape[1], binary.shape[0]))
        
        return centered
    
    def resize_to_square(self, image: np.ndarray, pad_value: int = 20) -> np.ndarray:
        h, w = image.shape[:2]
        
        max_dim = max(h, w) + pad_value * 2
        square = np.zeros((max_dim, max_dim), dtype=np.uint8)
        
        x_offset = (max_dim - w) // 2
        y_offset = (max_dim - h) // 2
        
        square[y_offset:y_offset+h, x_offset:x_offset+w] = image
        
        resized = cv2.resize(square, (self.image_size, self.image_size))
        
        return resized


class ContourExtractor:
    def __init__(self, min_points: int = 100):
        self.min_points = min_points
    
    def extract_contour(self, binary_image: np.ndarray) -> np.ndarray:
        contours, hierarchy = cv2.findContours(
            binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        main_contour = max(contours, key=cv2.contourArea)
        
        epsilon = 0.001 * cv2.arcLength(main_contour, True)
        approx = cv2.approxPolyDP(main_contour, epsilon, True)
        
        return approx
    
    def sample_contour_points(self, contour: np.ndarray, num_points: int = 256) -> np.ndarray:
        if contour is None:
            return None
        
        contour = contour.reshape(-1, 2)
        
        if len(contour) < 2:
            return None
        
        contour_extended = np.vstack([contour, contour[:1]])
        
        distances = np.sqrt(np.sum(np.diff(contour_extended, axis=0)**2, axis=1))
        cum_dist = np.cumsum(distances)
        total_dist = cum_dist[-1]
        
        sample_distances = np.linspace(0, total_dist, num_points)
        
        sampled_points = []
        for d in sample_distances:
            idx = np.searchsorted(cum_dist, d, side='right') - 1
            idx = max(0, min(idx, len(contour) - 2))
            
            if idx < len(contour) - 1:
                t = (d - cum_dist[idx]) / (cum_dist[idx + 1] - cum_dist[idx]) if cum_dist[idx + 1] > cum_dist[idx] else 0
                point = contour[idx] + t * (contour[idx + 1] - contour[idx])
                sampled_points.append(point)
        
        return np.array(sampled_points, dtype=np.float32)
    
    def normalize_contour(self, points: np.ndarray) -> np.ndarray:
        if points is None or len(points) == 0:
            return None
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        max_dist = np.max(np.sqrt(np.sum(centered**2, axis=1)))
        
        if max_dist > 0:
            normalized = centered / max_dist
        else:
            normalized = centered
        
        return normalized
    
    def process_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        preprocessor = ImagePreprocessor()
        binary = preprocessor.preprocess(image)
        contour = self.extract_contour(binary)
        points = self.sample_contour_points(contour)
        
        return binary, points


class CharacterDataset:
    def __init__(self):
        self.chars = {}
    
    def add_character(self, char: str, image: np.ndarray, points: np.ndarray):
        self.chars[char] = {
            'image': image,
            'points': points,
            'has_sample': True
        }
    
    def get_character(self, char: str):
        return self.chars.get(char, None)
    
    def get_available_chars(self) -> List[str]:
        return list(self.chars.keys())
    
    def is_complete(self, required_chars: List[str]) -> bool:
        return all(char in self.chars for char in required_chars)
    
    def get_training_data(self) -> Tuple[List[str], List[np.ndarray]]:
        chars = []
        points_list = []
        
        for char, data in self.chars.items():
            if data['points'] is not None:
                chars.append(char)
                points_list.append(data['points'])
        
        return chars, points_list
