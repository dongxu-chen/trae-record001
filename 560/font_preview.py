import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, ImageDraw, ImageFont
import os


class PreviewMode(Enum):
    SINGLE_GLYPH = "single_glyph"
    TEXT_LINE = "text_line"
    PARAGRAPH = "paragraph"
    GRID = "grid"
    COMPARISON = "comparison"


@dataclass
class PreviewConfig:
    font_size: int = 48
    line_spacing: float = 1.5
    char_spacing: int = 5
    background_color: Tuple[int, int, int] = (255, 255, 255)
    foreground_color: Tuple[int, int, int] = (0, 0, 0)
    stroke_width: int = 2
    padding: int = 40
    show_grid: bool = False
    show_baseline: bool = False
    show_bounding_box: bool = False
    dpi: int = 300
    antialiasing: bool = True


@dataclass
class PreviewResult:
    image: np.ndarray
    text: str
    config: PreviewConfig
    glyph_count: int
    render_time: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)


class GlyphRenderer:
    def __init__(self, font_units: int = 1000, ascender: int = 800, descender: int = -200):
        self.font_units = font_units
        self.ascender = ascender
        self.descender = descender
        self.baseline_offset = abs(descender)
        
        self.test_texts = {
            'basic': 'The quick brown fox jumps over the lazy dog',
            'chinese': '天地玄黄，宇宙洪荒。日月盈昃，辰宿列张。',
            'mixed': 'Hello 世界！This is a test 测试文本。',
            'numbers': '0123456789 + - * / = % $ € £ ¥',
            'punctuation': '.,!?;:()[]{}"\'-_+/\\<>@#$%^&*=',
            'all_chars': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
            'sentence': '人生如逆旅，我亦是行人。Life is a journey, not a destination.',
            'long_text': '春江潮水连海平，海上明月共潮生。滟滟随波千万里，何处春江无月明。'
        }
    
    def _get_font_scale(self, font_size: int) -> float:
        font_height = self.ascender - self.descender
        return font_size / font_height
    
    def _scale_glyph(self, points: np.ndarray, scale: float, offset_x: int, 
                    offset_y: int, image_height: int) -> np.ndarray:
        if points is None or len(points) == 0:
            return np.array([])
        
        scaled = points * scale
        
        y_min = np.min(scaled[:, 1])
        y_max = np.max(scaled[:, 1])
        
        baseline_y = image_height - offset_y - self.baseline_offset * scale
        
        adjusted = scaled.copy()
        adjusted[:, 0] += offset_x
        adjusted[:, 1] = baseline_y - (scaled[:, 1] - self.descender * scale)
        
        return adjusted
    
    def render_glyph(self, points: np.ndarray, config: PreviewConfig) -> Optional[np.ndarray]:
        if points is None or len(points) == 0:
            return None
        
        scale = self._get_font_scale(config.font_size)
        image_size = int(config.font_size * 2.5)
        
        image = np.full((image_size, image_size, 3), config.background_color, dtype=np.uint8)
        
        offset_x = (image_size - np.max(points[:, 0]) * scale) / 2
        offset_y = config.padding
        
        scaled_points = self._scale_glyph(points, scale, offset_x, offset_y, image_size)
        
        if len(scaled_points) == 0:
            return image
        
        if config.show_grid:
            self._draw_grid(image, 50)
        
        if config.show_baseline:
            baseline_y = image_size - offset_y - self.baseline_offset * scale
            cv2.line(image, (0, int(baseline_y)), (image_size, int(baseline_y)), 
                     (200, 0, 0), 1)
        
        if config.show_bounding_box:
            x, y, w, h = cv2.boundingRect(scaled_points.astype(np.int32))
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 200, 0), 1)
        
        pts = scaled_points.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(image, [pts], True, config.foreground_color, config.stroke_width)
        
        return image
    
    def render_text(self, text: str, glyphs: Dict[str, np.ndarray], 
                   config: PreviewConfig) -> PreviewResult:
        if not text or not glyphs:
            blank = np.full((200, 400, 3), config.background_color, dtype=np.uint8)
            return PreviewResult(image=blank, text=text, config=config, glyph_count=0)
        
        scale = self._get_font_scale(config.font_size)
        line_height = int(config.font_size * config.line_spacing)
        
        lines = text.split('\n')
        max_line_width = 0
        line_widths = []
        
        for line in lines:
            width = 0
            for char in line:
                if char in glyphs and glyphs[char] is not None:
                    pts = glyphs[char]
                    char_width = (np.max(pts[:, 0]) - np.min(pts[:, 0])) * scale if len(pts) > 0 else config.font_size * 0.6
                    width += char_width + config.char_spacing
                else:
                    width += config.font_size * 0.6 + config.char_spacing
            line_widths.append(int(width))
            max_line_width = max(max_line_width, int(width))
        
        image_width = max_line_width + config.padding * 2
        image_height = len(lines) * line_height + config.padding * 2
        
        image = np.full((image_height, image_width, 3), config.background_color, dtype=np.uint8)
        
        glyph_count = 0
        missing_chars = []
        
        for line_idx, line in enumerate(lines):
            x = config.padding
            y = config.padding + line_idx * line_height + line_height
            
            for char in line:
                if char == ' ':
                    x += config.font_size * 0.4 + config.char_spacing
                    continue
                
                if char in glyphs and glyphs[char] is not None:
                    pts = glyphs[char]
                    scaled_pts = self._scale_glyph(pts, scale, x, 0, image_height)
                    scaled_pts[:, 1] += y - (image_height - config.padding - self.baseline_offset * scale)
                    
                    if len(scaled_pts) > 0:
                        pts_int = scaled_pts.astype(np.int32).reshape((-1, 1, 2))
                        cv2.polylines(image, [pts_int], True, config.foreground_color, config.stroke_width)
                    
                    char_width = (np.max(pts[:, 0]) - np.min(pts[:, 0])) * scale if len(pts) > 0 else config.font_size * 0.6
                    x += char_width + config.char_spacing
                    glyph_count += 1
                else:
                    missing_chars.append(char)
                    x += config.font_size * 0.6 + config.char_spacing
        
        if config.show_baseline:
            for line_idx in range(len(lines)):
                y = config.padding + line_idx * line_height + line_height
                cv2.line(image, (0, int(y)), (image_width, int(y)), (200, 0, 0), 1)
        
        return PreviewResult(
            image=image,
            text=text,
            config=config,
            glyph_count=glyph_count,
            metrics={
                'lines': len(lines),
                'chars': len(text),
                'missing_chars': len(missing_chars),
                'image_width': image_width,
                'image_height': image_height
            }
        )
    
    def render_glyph_grid(self, glyphs: Dict[str, np.ndarray], 
                         config: PreviewConfig,
                         cols: int = 10,
                         char_order: Optional[List[str]] = None) -> PreviewResult:
        if not glyphs:
            blank = np.full((400, 600, 3), config.background_color, dtype=np.uint8)
            return PreviewResult(image=blank, text="", config=config, glyph_count=0)
        
        if char_order is None:
            char_order = sorted(glyphs.keys())
        
        total_glyphs = len(char_order)
        rows = (total_glyphs + cols - 1) // cols
        
        scale = self._get_font_scale(config.font_size)
        cell_width = int(config.font_size * 1.5)
        cell_height = int(config.font_size * 2.0)
        
        image_width = cols * cell_width + config.padding * 2
        image_height = rows * cell_height + config.padding * 2
        
        image = np.full((image_height, image_width, 3), config.background_color, dtype=np.uint8)
        
        glyph_count = 0
        
        for idx, char in enumerate(char_order):
            if char not in glyphs or glyphs[char] is None:
                continue
            
            row = idx // cols
            col = idx % cols
            
            x = config.padding + col * cell_width + cell_width * 0.25
            y = config.padding + row * cell_height + cell_height * 0.2
            
            pts = glyphs[char]
            scaled_pts = self._scale_glyph(pts, scale, x, 0, image_height)
            scaled_pts[:, 1] += y - (image_height - config.padding - self.baseline_offset * scale)
            
            if len(scaled_pts) > 0:
                if config.show_bounding_box:
                    bx, by, bw, bh = cv2.boundingRect(scaled_pts.astype(np.int32))
                    cv2.rectangle(image, (bx, by), (bx + bw, by + bh), (0, 200, 0), 1)
                
                pts_int = scaled_pts.astype(np.int32).reshape((-1, 1, 2))
                cv2.polylines(image, [pts_int], True, config.foreground_color, config.stroke_width)
                
                label_y = config.padding + (row + 1) * cell_height - 5
                label_x = config.padding + col * cell_width + cell_width // 2
                cv2.putText(image, repr(char), (label_x - 8, label_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
                
                glyph_count += 1
        
        return PreviewResult(
            image=image,
            text=f"Glyph Grid: {glyph_count} glyphs",
            config=config,
            glyph_count=glyph_count,
            metrics={
                'rows': rows,
                'cols': cols,
                'total_cells': total_glyphs
            }
        )
    
    def render_comparison(self, text: str, 
                         fonts: Dict[str, Dict[str, np.ndarray]],
                         config: PreviewConfig,
                         labels: Optional[Dict[str, str]] = None) -> PreviewResult:
        if not text or not fonts:
            blank = np.full((400, 600, 3), config.background_color, dtype=np.uint8)
            return PreviewResult(image=blank, text=text, config=config, glyph_count=0)
        
        results = []
        for font_name, glyphs in fonts.items():
            result = self.render_text(text, glyphs, config)
            results.append((font_name, result))
        
        max_width = max(r.image.shape[1] for _, r in results)
        label_height = 40
        total_height = sum(r.image.shape[0] + label_height for _, r in results) + config.padding * 2
        
        image = np.full((total_height, max_width + config.padding * 2, 3), 
                       config.background_color, dtype=np.uint8)
        
        y_offset = config.padding
        glyph_count = 0
        
        for font_name, result in results:
            label = labels.get(font_name, font_name) if labels else font_name
            
            cv2.putText(image, label, (config.padding, y_offset + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            h, w = result.image.shape[:2]
            image[y_offset + label_height:y_offset + label_height + h, 
                  config.padding:config.padding + w] = result.image
            
            y_offset += label_height + h
            glyph_count += result.glyph_count
        
        return PreviewResult(
            image=image,
            text=text,
            config=config,
            glyph_count=glyph_count,
            metrics={
                'fonts_compared': len(fonts),
                'labels': list(fonts.keys())
            }
        )
    
    def _draw_grid(self, image: np.ndarray, spacing: int):
        h, w = image.shape[:2]
        for x in range(0, w, spacing):
            cv2.line(image, (x, 0), (x, h), (240, 240, 240), 1)
        for y in range(0, h, spacing):
            cv2.line(image, (0, y), (w, y), (240, 240, 240), 1)
    
    def get_test_text(self, key: str = 'basic') -> str:
        return self.test_texts.get(key, self.test_texts['basic'])
    
    def list_test_texts(self) -> List[str]:
        return list(self.test_texts.keys())


class FontPreviewer:
    def __init__(self, glyphs: Optional[Dict[str, np.ndarray]] = None):
        self.glyphs = glyphs or {}
        self.renderer = GlyphRenderer()
        self.history = []
        self.max_history = 20
    
    def set_glyphs(self, glyphs: Dict[str, np.ndarray]):
        self.glyphs = glyphs
    
    def add_glyphs(self, glyphs: Dict[str, np.ndarray]):
        self.glyphs.update(glyphs)
    
    def remove_glyphs(self, chars: List[str]):
        for char in chars:
            if char in self.glyphs:
                del self.glyphs[char]
    
    def get_available_chars(self) -> List[str]:
        return sorted([c for c, p in self.glyphs.items() if p is not None])
    
    def _save_to_history(self, result: PreviewResult):
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def preview_text(self, text: str, 
                    font_size: int = 48,
                    line_spacing: float = 1.5,
                    char_spacing: int = 5,
                    **kwargs) -> PreviewResult:
        config = PreviewConfig(
            font_size=font_size,
            line_spacing=line_spacing,
            char_spacing=char_spacing,
            **kwargs
        )
        
        result = self.renderer.render_text(text, self.glyphs, config)
        self._save_to_history(result)
        return result
    
    def preview_glyph(self, char: str, 
                     font_size: int = 120,
                     show_baseline: bool = True,
                     show_bounding_box: bool = False,
                     **kwargs) -> Optional[PreviewResult]:
        if char not in self.glyphs or self.glyphs[char] is None:
            return None
        
        config = PreviewConfig(
            font_size=font_size,
            show_baseline=show_baseline,
            show_bounding_box=show_bounding_box,
            **kwargs
        )
        
        image = self.renderer.render_glyph(self.glyphs[char], config)
        
        result = PreviewResult(
            image=image,
            text=repr(char),
            config=config,
            glyph_count=1
        )
        self._save_to_history(result)
        return result
    
    def preview_grid(self, chars: Optional[List[str]] = None,
                    font_size: int = 32,
                    cols: int = 10,
                    **kwargs) -> PreviewResult:
        if chars is None:
            chars = self.get_available_chars()
        
        config = PreviewConfig(
            font_size=font_size,
            show_bounding_box=False,
            **kwargs
        )
        
        result = self.renderer.render_glyph_grid(
            self.glyphs, config, cols=cols, char_order=chars
        )
        self._save_to_history(result)
        return result
    
    def preview_comparison(self, text: str,
                          other_fonts: Dict[str, Dict[str, np.ndarray]],
                          font_size: int = 36,
                          labels: Optional[Dict[str, str]] = None,
                          **kwargs) -> PreviewResult:
        all_fonts = {'Current': self.glyphs}
        all_fonts.update(other_fonts)
        
        all_labels = {'Current': 'Current Font'}
        if labels:
            all_labels.update(labels)
        
        config = PreviewConfig(font_size=font_size, **kwargs)
        
        result = self.renderer.render_comparison(text, all_fonts, config, all_labels)
        self._save_to_history(result)
        return result
    
    def test_kerning(self, pairs: Optional[List[Tuple[str, str]]] = None) -> Dict[str, float]:
        if pairs is None:
            pairs = [
                ('A', 'V'), ('W', 'a'), ('T', 'e'), ('L', 'y'),
                ('P', 'a'), ('f', '.'), ('o', 'o'), ('r', 'n')
            ]
        
        kerning_values = {}
        scale = self.renderer._get_font_scale(48)
        
        for c1, c2 in pairs:
            if c1 not in self.glyphs or c2 not in self.glyphs:
                continue
            
            p1 = self.glyphs[c1]
            p2 = self.glyphs[c2]
            
            right_edge_c1 = np.max(p1[:, 0]) if len(p1) > 0 else 0
            left_edge_c2 = np.min(p2[:, 0]) if len(p2) > 0 else 0
            
            spacing = (left_edge_c2 - right_edge_c1) * scale
            kerning_values[f"{c1}{c2}"] = spacing
        
        return kerning_values
    
    def analyze_glyph_coverage(self, text: str) -> Dict[str, Union[int, List[str]]]:
        unique_chars = set(text)
        available = set(self.get_available_chars())
        
        covered = unique_chars & available
        missing = unique_chars - available
        
        return {
            'total_unique': len(unique_chars),
            'covered_count': len(covered),
            'missing_count': len(missing),
            'coverage_percent': len(covered) / len(unique_chars) * 100 if unique_chars else 100,
            'covered_chars': sorted(covered),
            'missing_chars': sorted(missing)
        }
    
    def quick_preview(self, text: str = None) -> np.ndarray:
        if text is None:
            text = self.renderer.get_test_text('basic')
        
        result = self.preview_text(text, font_size=48)
        return result.image
    
    def export_preview(self, result: PreviewResult, output_path: str):
        image_bgr = cv2.cvtColor(result.image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, image_bgr)
    
    def get_history(self) -> List[PreviewResult]:
        return self.history.copy()
    
    def clear_history(self):
        self.history = []
