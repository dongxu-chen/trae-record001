import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import math


class FontStyle(Enum):
    NORMAL = "normal"
    BOLD = "bold"
    ITALIC = "italic"
    BOLD_ITALIC = "bold_italic"
    CONDENSED = "condensed"
    EXPANDED = "expanded"
    LIGHT = "light"
    HEAVY = "heavy"
    OBLIQUE = "oblique"
    HANDWRITING = "handwriting"


class StyleTransformer:
    def __init__(self):
        self.default_params = {
            'bold_stroke_width': 1.3,
            'light_stroke_width': 0.7,
            'heavy_stroke_width': 1.6,
            'italic_angle': 0.3,
            'oblique_angle': 0.2,
            'condensed_scale': 0.75,
            'expanded_scale': 1.25,
            'handwriting_jitter': 0.08,
            'handwriting_irregularity': 0.15
        }
    
    def transform(self, points: np.ndarray, style: Union[str, FontStyle], **kwargs) -> Optional[np.ndarray]:
        if points is None or len(points) == 0:
            return None
        
        if isinstance(style, str):
            try:
                style = FontStyle(style.lower())
            except ValueError:
                return points
        
        transform_method = {
            FontStyle.NORMAL: self._normal,
            FontStyle.BOLD: self._bold,
            FontStyle.ITALIC: self._italic,
            FontStyle.BOLD_ITALIC: self._bold_italic,
            FontStyle.CONDENSED: self._condensed,
            FontStyle.EXPANDED: self._expanded,
            FontStyle.LIGHT: self._light,
            FontStyle.HEAVY: self._heavy,
            FontStyle.OBLIQUE: self._oblique,
            FontStyle.HANDWRITING: self._handwriting
        }
        
        method = transform_method.get(style, self._normal)
        return method(points, **kwargs)
    
    def _normal(self, points: np.ndarray, **kwargs) -> np.ndarray:
        return points.copy()
    
    def _bold(self, points: np.ndarray, **kwargs) -> np.ndarray:
        stroke_width = kwargs.get('stroke_width', self.default_params['bold_stroke_width'])
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        direction_vectors = np.gradient(centered, axis=0)
        norm = np.linalg.norm(direction_vectors, axis=1, keepdims=True)
        norm = np.where(norm == 0, 1, norm)
        direction_vectors = direction_vectors / norm
        
        normal_vectors = np.column_stack([-direction_vectors[:, 1], direction_vectors[:, 0]])
        
        expanded = centered + normal_vectors * stroke_width * 5
        
        return expanded + centroid
    
    def _italic(self, points: np.ndarray, **kwargs) -> np.ndarray:
        angle = kwargs.get('angle', self.default_params['italic_angle'])
        
        result = points.copy()
        y_coords = points[:, 1]
        y_min, y_max = np.min(y_coords), np.max(y_coords)
        y_range = y_max - y_min if y_max > y_min else 1
        
        y_normalized = (y_coords - y_min) / y_range
        shear_offset = y_normalized * angle * 100
        
        result[:, 0] += shear_offset
        
        return result
    
    def _bold_italic(self, points: np.ndarray, **kwargs) -> np.ndarray:
        result = self._bold(points, **kwargs)
        result = self._italic(result, **kwargs)
        return result
    
    def _condensed(self, points: np.ndarray, **kwargs) -> np.ndarray:
        scale_x = kwargs.get('scale_x', self.default_params['condensed_scale'])
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        centered[:, 0] *= scale_x
        
        return centered + centroid
    
    def _expanded(self, points: np.ndarray, **kwargs) -> np.ndarray:
        scale_x = kwargs.get('scale_x', self.default_params['expanded_scale'])
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        centered[:, 0] *= scale_x
        
        return centered + centroid
    
    def _light(self, points: np.ndarray, **kwargs) -> np.ndarray:
        stroke_width = kwargs.get('stroke_width', self.default_params['light_stroke_width'])
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        direction_vectors = np.gradient(centered, axis=0)
        norm = np.linalg.norm(direction_vectors, axis=1, keepdims=True)
        norm = np.where(norm == 0, 1, norm)
        direction_vectors = direction_vectors / norm
        
        normal_vectors = np.column_stack([-direction_vectors[:, 1], direction_vectors[:, 0]])
        
        contracted = centered - normal_vectors * stroke_width * 5
        
        return contracted + centroid
    
    def _heavy(self, points: np.ndarray, **kwargs) -> np.ndarray:
        stroke_width = kwargs.get('stroke_width', self.default_params['heavy_stroke_width'])
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        direction_vectors = np.gradient(centered, axis=0)
        norm = np.linalg.norm(direction_vectors, axis=1, keepdims=True)
        norm = np.where(norm == 0, 1, norm)
        direction_vectors = direction_vectors / norm
        
        normal_vectors = np.column_stack([-direction_vectors[:, 1], direction_vectors[:, 0]])
        
        expanded = centered + normal_vectors * stroke_width * 5
        
        return expanded + centroid
    
    def _oblique(self, points: np.ndarray, **kwargs) -> np.ndarray:
        angle = kwargs.get('angle', self.default_params['oblique_angle'])
        
        result = points.copy()
        y_coords = points[:, 1]
        y_min, y_max = np.min(y_coords), np.max(y_coords)
        y_range = y_max - y_min if y_max > y_min else 1
        
        y_normalized = (y_coords - y_min) / y_range
        shear_offset = y_normalized * angle * 80
        
        result[:, 0] += shear_offset
        
        return result
    
    def _handwriting(self, points: np.ndarray, **kwargs) -> np.ndarray:
        jitter_amount = kwargs.get('jitter', self.default_params['handwriting_jitter'])
        irregularity = kwargs.get('irregularity', self.default_params['handwriting_irregularity'])
        
        result = points.copy()
        n_points = len(points)
        
        np.random.seed(42)
        jitter_x = np.random.normal(0, jitter_amount * 20, n_points)
        jitter_y = np.random.normal(0, jitter_amount * 15, n_points)
        
        result[:, 0] += jitter_x
        result[:, 1] += jitter_y
        
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        scales = 1 + np.random.normal(0, irregularity, n_points)
        
        scaled = centered * scales[:, np.newaxis]
        result = scaled + centroid
        
        return result
    
    def apply_custom_transform(self, points: np.ndarray, 
                              scale_x: float = 1.0,
                              scale_y: float = 1.0,
                              shear_x: float = 0.0,
                              shear_y: float = 0.0,
                              rotation: float = 0.0,
                              offset_x: float = 0.0,
                              offset_y: float = 0.0) -> np.ndarray:
        if points is None or len(points) == 0:
            return points
        
        result = points.copy()
        centroid = np.mean(points, axis=0)
        centered = points - centroid
        
        rotation_rad = np.radians(rotation)
        rotation_matrix = np.array([
            [np.cos(rotation_rad), -np.sin(rotation_rad)],
            [np.sin(rotation_rad), np.cos(rotation_rad)]
        ])
        
        shear_matrix = np.array([
            [1.0, shear_x],
            [shear_y, 1.0]
        ])
        
        scale_matrix = np.array([
            [scale_x, 0.0],
            [0.0, scale_y]
        ])
        
        transform_matrix = rotation_matrix @ shear_matrix @ scale_matrix
        
        transformed = centered @ transform_matrix.T
        
        transformed[:, 0] += offset_x
        transformed[:, 1] += offset_y
        
        return transformed + centroid


class FontStyleTransfer:
    def __init__(self):
        self.transformer = StyleTransformer()
        self.style_presets = {
            'bold': {'style': FontStyle.BOLD, 'params': {'stroke_width': 1.3}},
            'italic': {'style': FontStyle.ITALIC, 'params': {'angle': 0.3}},
            'bold_italic': {'style': FontStyle.BOLD_ITALIC, 'params': {'stroke_width': 1.3, 'angle': 0.3}},
            'condensed': {'style': FontStyle.CONDENSED, 'params': {'scale_x': 0.75}},
            'expanded': {'style': FontStyle.EXPANDED, 'params': {'scale_x': 1.25}},
            'light': {'style': FontStyle.LIGHT, 'params': {'stroke_width': 0.7}},
            'heavy': {'style': FontStyle.HEAVY, 'params': {'stroke_width': 1.6}},
            'oblique': {'style': FontStyle.OBLIQUE, 'params': {'angle': 0.2}},
            'handwriting': {'style': FontStyle.HANDWRITING, 'params': {'jitter': 0.08, 'irregularity': 0.15}},
        }
    
    def get_available_styles(self) -> List[str]:
        return list(self.style_presets.keys())
    
    def transfer_style(self, points: np.ndarray, 
                      style: Union[str, FontStyle], **custom_params) -> Optional[np.ndarray]:
        if isinstance(style, str) and style in self.style_presets:
            preset = self.style_presets[style]
            params = preset['params'].copy()
            params.update(custom_params)
            return self.transformer.transform(points, preset['style'], **params)
        else:
            return self.transformer.transform(points, style, **custom_params)
    
    def transfer_batch(self, points_dict: Dict[str, np.ndarray], 
                      style: Union[str, FontStyle], **custom_params) -> Dict[str, np.ndarray]:
        result = {}
        for char, points in points_dict.items():
            transformed = self.transfer_style(points, style, **custom_params)
            if transformed is not None:
                result[char] = transformed
        return result
    
    def create_style_variations(self, points: np.ndarray, 
                               styles: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
        if styles is None:
            styles = self.get_available_styles()
        
        variations = {}
        for style_name in styles:
            if style_name in self.style_presets:
                transformed = self.transfer_style(points, style_name)
                if transformed is not None:
                    variations[style_name] = transformed
        
        return variations
    
    def interpolate_style(self, points: np.ndarray, 
                         style1: str, style2: str, alpha: float = 0.5) -> Optional[np.ndarray]:
        if points is None or len(points) == 0:
            return None
        
        points1 = self.transfer_style(points, style1)
        points2 = self.transfer_style(points, style2)
        
        if points1 is None or points2 is None:
            return None
        
        return points1 * (1 - alpha) + points2 * alpha
    
    def get_style_info(self, style_name: str) -> dict:
        if style_name not in self.style_presets:
            return {}
        
        preset = self.style_presets[style_name]
        return {
            'name': style_name,
            'enum': preset['style'].value,
            'parameters': preset['params']
        }


class StylePreviewGenerator:
    def __init__(self):
        self.style_transfer = FontStyleTransfer()
    
    def generate_style_grid(self, points: np.ndarray, cols: int = 3) -> List[List[Tuple[str, np.ndarray]]]:
        styles = self.style_transfer.get_available_styles()
        variations = self.style_transfer.create_style_variations(points, styles)
        
        grid = []
        row = []
        
        for i, (style_name, transformed_points) in enumerate(variations.items()):
            row.append((style_name, transformed_points))
            
            if (i + 1) % cols == 0:
                grid.append(row)
                row = []
        
        if row:
            grid.append(row)
        
        return grid
    
    def generate_comparison_image(self, original: np.ndarray, 
                                  styled: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        result = {'original': original}
        result.update(styled)
        return result
