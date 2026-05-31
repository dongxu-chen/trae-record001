import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class BlendMode(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    SMOOTHSTEP = "smoothstep"
    RADIAL = "radial"


@dataclass
class BlendResult:
    char: str
    points: np.ndarray
    blend_ratio: float
    mode: BlendMode
    metrics: Dict[str, float] = field(default_factory=dict)


class ContourAligner:
    def __init__(self):
        pass
    
    def _resample_contour(self, points: np.ndarray, n_samples: int) -> np.ndarray:
        if len(points) == n_samples:
            return points
        
        distances = np.zeros(len(points))
        for i in range(1, len(points)):
            distances[i] = distances[i - 1] + np.linalg.norm(points[i] - points[i - 1])
        
        total_length = distances[-1] if distances[-1] > 0 else 1
        target_distances = np.linspace(0, total_length, n_samples)
        
        resampled = np.zeros((n_samples, 2))
        for i, target_d in enumerate(target_distances):
            idx = np.searchsorted(distances, target_d, side='right') - 1
            idx = np.clip(idx, 0, len(points) - 2)
            
            segment_len = distances[idx + 1] - distances[idx]
            if segment_len == 0:
                t = 0
            else:
                t = (target_d - distances[idx]) / segment_len
            
            resampled[i] = points[idx] * (1 - t) + points[idx + 1] * t
        
        return resampled
    
    def _find_alignment_offset(self, points1: np.ndarray, points2: np.ndarray) -> int:
        n = len(points1)
        min_error = float('inf')
        best_offset = 0
        
        for offset in range(0, n, max(1, n // 20)):
            rolled = np.roll(points2, offset, axis=0)
            error = np.mean(np.linalg.norm(points1 - rolled, axis=1))
            if error < min_error:
                min_error = error
                best_offset = offset
        
        return best_offset
    
    def align_contours(self, points1: np.ndarray, points2: np.ndarray, 
                      n_samples: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        if points1 is None or points2 is None:
            return points1, points2
        
        if n_samples is None:
            n_samples = max(len(points1), len(points2))
        
        resampled1 = self._resample_contour(points1, n_samples)
        resampled2 = self._resample_contour(points2, n_samples)
        
        offset = self._find_alignment_offset(resampled1, resampled2)
        aligned2 = np.roll(resampled2, offset, axis=0)
        
        return resampled1, aligned2
    
    def normalize_scale(self, points1: np.ndarray, points2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if points1 is None or points2 is None:
            return points1, points2
        
        def get_bbox_size(p):
            min_p = np.min(p, axis=0)
            max_p = np.max(p, axis=0)
            return max_p - min_p
        
        size1 = get_bbox_size(points1)
        size2 = get_bbox_size(points2)
        
        scale_factor = np.max(size1) / np.max(size2) if np.max(size2) > 0 else 1
        
        centroid2 = np.mean(points2, axis=0)
        scaled2 = (points2 - centroid2) * scale_factor + centroid2
        
        return points1, scaled2


class FontBlender:
    def __init__(self):
        self.aligner = ContourAligner()
        self.blend_modes = {
            BlendMode.LINEAR: self._linear_blend,
            BlendMode.EASE_IN: self._ease_in_blend,
            BlendMode.EASE_OUT: self._ease_out_blend,
            BlendMode.EASE_IN_OUT: self._ease_in_out_blend,
            BlendMode.SMOOTHSTEP: self._smoothstep_blend,
            BlendMode.RADIAL: self._radial_blend,
        }
    
    def get_available_modes(self) -> List[str]:
        return [mode.value for mode in BlendMode]
    
    def _linear_blend(self, t: float) -> float:
        return np.clip(t, 0.0, 1.0)
    
    def _ease_in_blend(self, t: float) -> float:
        t = np.clip(t, 0.0, 1.0)
        return t * t
    
    def _ease_out_blend(self, t: float) -> float:
        t = np.clip(t, 0.0, 1.0)
        return 1.0 - (1.0 - t) * (1.0 - t)
    
    def _ease_in_out_blend(self, t: float) -> float:
        t = np.clip(t, 0.0, 1.0)
        return t * t * (3.0 - 2.0 * t)
    
    def _smoothstep_blend(self, t: float) -> float:
        t = np.clip(t, 0.0, 1.0)
        return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    
    def _radial_blend(self, t: float) -> float:
        t = np.clip(t, 0.0, 1.0)
        return np.sin(t * np.pi / 2.0)
    
    def blend_glyph(self, points1: np.ndarray, points2: np.ndarray,
                   ratio: float = 0.5,
                   mode: Union[str, BlendMode] = BlendMode.LINEAR,
                   align: bool = True,
                   normalize_scale: bool = True,
                   char: str = "") -> Optional[BlendResult]:
        if points1 is None or points2 is None:
            return None
        
        if len(points1) == 0 or len(points2) == 0:
            return None
        
        if isinstance(mode, str):
            try:
                mode = BlendMode(mode.lower())
            except ValueError:
                mode = BlendMode.LINEAR
        
        blend_func = self.blend_modes.get(mode, self._linear_blend)
        
        p1, p2 = points1.copy(), points2.copy()
        
        if normalize_scale:
            p1, p2 = self.aligner.normalize_scale(p1, p2)
        
        if align:
            p1, p2 = self.aligner.align_contours(p1, p2)
        
        t = blend_func(ratio)
        
        blended = p1 * (1.0 - t) + p2 * t
        
        error1 = np.mean(np.linalg.norm(blended - p1, axis=1))
        error2 = np.mean(np.linalg.norm(blended - p2, axis=1))
        
        metrics = {
            'blend_t': t,
            'error_to_font1': float(error1),
            'error_to_font2': float(error2),
            'total_points': len(blended),
            'font1_points': len(points1),
            'font2_points': len(points2)
        }
        
        return BlendResult(
            char=char,
            points=blended,
            blend_ratio=ratio,
            mode=mode,
            metrics=metrics
        )
    
    def blend_batch(self, font1_glyphs: Dict[str, np.ndarray],
                   font2_glyphs: Dict[str, np.ndarray],
                   ratio: float = 0.5,
                   mode: Union[str, BlendMode] = BlendMode.LINEAR,
                   common_chars_only: bool = True) -> Dict[str, BlendResult]:
        results = {}
        
        if common_chars_only:
            chars = set(font1_glyphs.keys()) & set(font2_glyphs.keys())
        else:
            chars = set(font1_glyphs.keys()) | set(font2_glyphs.keys())
        
        for char in chars:
            p1 = font1_glyphs.get(char)
            p2 = font2_glyphs.get(char)
            
            if p1 is not None and p2 is not None:
                result = self.blend_glyph(p1, p2, ratio, mode, char=char)
                if result is not None:
                    results[char] = result
        
        return results
    
    def create_blend_sequence(self, points1: np.ndarray, points2: np.ndarray,
                             num_steps: int = 10,
                             mode: Union[str, BlendMode] = BlendMode.LINEAR,
                             char: str = "") -> List[BlendResult]:
        results = []
        ratios = np.linspace(0.0, 1.0, num_steps)
        
        for ratio in ratios:
            result = self.blend_glyph(points1, points2, float(ratio), mode, char=char)
            if result is not None:
                results.append(result)
        
        return results
    
    def blend_with_weights(self, points1: np.ndarray, points2: np.ndarray,
                          weights: np.ndarray,
                          mode: Union[str, BlendMode] = BlendMode.LINEAR,
                          char: str = "") -> Optional[BlendResult]:
        if points1 is None or points2 is None:
            return None
        
        if len(points1) == 0 or len(points2) == 0:
            return None
        
        if isinstance(mode, str):
            try:
                mode = BlendMode(mode.lower())
            except ValueError:
                mode = BlendMode.LINEAR
        
        blend_func = self.blend_modes.get(mode, self._linear_blend)
        
        p1, p2 = self.aligner.align_contours(points1, points2)
        
        weights = np.clip(weights, 0.0, 1.0)
        if len(weights.shape) == 1:
            weights = weights[:, np.newaxis]
        
        blended = p1 * (1.0 - weights) + p2 * weights
        
        metrics = {
            'weighted': True,
            'min_weight': float(np.min(weights)),
            'max_weight': float(np.max(weights)),
            'mean_weight': float(np.mean(weights))
        }
        
        return BlendResult(
            char=char,
            points=blended,
            blend_ratio=float(np.mean(weights)),
            mode=mode,
            metrics=metrics
        )


class FontMixer:
    def __init__(self):
        self.blender = FontBlender()
        self._fonts = {}
    
    def add_font(self, name: str, glyphs: Dict[str, np.ndarray]):
        self._fonts[name] = glyphs
    
    def remove_font(self, name: str):
        if name in self._fonts:
            del self._fonts[name]
    
    def list_fonts(self) -> List[str]:
        return list(self._fonts.keys())
    
    def get_font(self, name: str) -> Optional[Dict[str, np.ndarray]]:
        return self._fonts.get(name)
    
    def mix_two_fonts(self, font1_name: str, font2_name: str,
                     ratio: float = 0.5,
                     mode: Union[str, BlendMode] = BlendMode.LINEAR,
                     output_name: Optional[str] = None) -> Optional[Dict[str, np.ndarray]]:
        font1 = self.get_font(font1_name)
        font2 = self.get_font(font2_name)
        
        if font1 is None or font2 is None:
            return None
        
        blend_results = self.blender.blend_batch(font1, font2, ratio, mode)
        
        output_glyphs = {}
        for char, result in blend_results.items():
            output_glyphs[char] = result.points
        
        if output_name:
            self._fonts[output_name] = output_glyphs
        
        return output_glyphs
    
    def mix_many_fonts(self, font_ratios: Dict[str, float],
                       mode: Union[str, BlendMode] = BlendMode.LINEAR,
                       output_name: Optional[str] = None) -> Optional[Dict[str, np.ndarray]]:
        total_ratio = sum(font_ratios.values())
        if total_ratio == 0:
            return None
        
        normalized_ratios = {name: r / total_ratio for name, r in font_ratios.items()}
        
        all_chars = set()
        for font_name in normalized_ratios.keys():
            font = self.get_font(font_name)
            if font:
                all_chars.update(font.keys())
        
        output_glyphs = {}
        aligner = ContourAligner()
        
        for char in all_chars:
            char_points = []
            char_weights = []
            
            for font_name, weight in normalized_ratios.items():
                font = self.get_font(font_name)
                if font and char in font:
                    char_points.append(font[char])
                    char_weights.append(weight)
            
            if len(char_points) >= 2:
                n_samples = max(len(p) for p in char_points)
                resampled = []
                for p in char_points:
                    r, _ = aligner.align_contours(p, char_points[0], n_samples)
                    resampled.append(r)
                
                blended = np.zeros_like(resampled[0])
                for i, p in enumerate(resampled):
                    blended += p * char_weights[i]
                
                output_glyphs[char] = blended
            elif len(char_points) == 1:
                output_glyphs[char] = char_points[0]
        
        if output_name:
            self._fonts[output_name] = output_glyphs
        
        return output_glyphs
    
    def create_morph_animation(self, font1_name: str, font2_name: str,
                               num_frames: int = 20,
                               mode: Union[str, BlendMode] = BlendMode.LINEAR) -> List[Dict[str, np.ndarray]]:
        font1 = self.get_font(font1_name)
        font2 = self.get_font(font2_name)
        
        if font1 is None or font2 is None:
            return []
        
        common_chars = set(font1.keys()) & set(font2.keys())
        frames = []
        
        ratios = np.linspace(0.0, 1.0, num_frames)
        
        for ratio in ratios:
            frame = {}
            for char in common_chars:
                p1 = font1[char]
                p2 = font2[char]
                
                result = self.blender.blend_glyph(p1, p2, float(ratio), mode, char=char)
                if result:
                    frame[char] = result.points
            
            frames.append(frame)
        
        return frames
