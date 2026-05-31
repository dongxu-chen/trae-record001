import cv2
import numpy as np
from typing import Dict, Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont
import os


class OverlayEngine:
    def __init__(self):
        self.position_options = {
            "top": 0.1,
            "center": 0.5,
            "bottom": 0.85,
            "top_left": (0.1, 0.1),
            "top_right": (0.9, 0.1),
            "bottom_left": (0.1, 0.85),
            "bottom_right": (0.9, 0.85),
            "center_left": (0.1, 0.5),
            "center_right": (0.9, 0.5)
        }
        
        self.font_paths = self._get_system_fonts()

    def _get_system_fonts(self) -> Dict[str, str]:
        font_candidates = {
            "default": None,
            "arial": "C:/Windows/Fonts/arial.ttf",
            "arial_bold": "C:/Windows/Fonts/arialbd.ttf",
            "times": "C:/Windows/Fonts/times.ttf",
            "calibri": "C:/Windows/Fonts/calibri.ttf",
            "verdana": "C:/Windows/Fonts/verdana.ttf",
            "impact": "C:/Windows/Fonts/impact.ttf"
        }
        
        available = {}
        for name, path in font_candidates.items():
            if path is None or os.path.exists(path):
                available[name] = path
        
        return available

    def _get_text_size(self, 
                       text: str, 
                       font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        dummy_img = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])

    def _wrap_text(self, 
                   text: str, 
                   font: ImageFont.FreeTypeFont, 
                   max_width: int) -> List[str]:
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            width, _ = self._get_text_size(test_line, font)
            
            if width <= max_width or not current_line:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines if lines else [text]

    def _calculate_position(self, 
                            position: str, 
                            img_size: Tuple[int, int], 
                            text_size: Tuple[int, int]) -> Tuple[int, int]:
        img_w, img_h = img_size
        text_w, text_h = text_size
        
        pos = self.position_options.get(position, 0.85)
        
        if isinstance(pos, tuple):
            x = int(pos[0] * img_w - text_w / 2)
            y = int(pos[1] * img_h - text_h / 2)
        else:
            x = int((img_w - text_w) / 2)
            y = int(pos * img_h - text_h / 2)
        
        x = max(10, min(x, img_w - text_w - 10))
        y = max(10, min(y, img_h - text_h - 10))
        
        return (x, y)

    def add_text_overlay(self,
                         image: np.ndarray,
                         title: str,
                         subtitle: str = "",
                         position: str = "bottom",
                         font_size: int = 48,
                         font_family: str = "default",
                         text_color: Tuple[int, int, int] = (255, 255, 255),
                         bg_color: Optional[Tuple[int, int, int, int]] = (0, 0, 0, 180),
                         padding: int = 20,
                         line_spacing: int = 10,
                         max_width_ratio: float = 0.9) -> np.ndarray:
        img_pil = Image.fromarray(image)
        draw = ImageDraw.Draw(img_pil, "RGBA")
        
        img_w, img_h = img_pil.size
        max_text_width = int(img_w * max_width_ratio)
        
        try:
            font_path = self.font_paths.get(font_family)
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
                subtitle_font = ImageFont.truetype(font_path, int(font_size * 0.65))
            else:
                font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        title_lines = self._wrap_text(title, font, max_text_width)
        subtitle_lines = self._wrap_text(subtitle, subtitle_font, max_text_width) if subtitle else []
        
        all_lines = title_lines + subtitle_lines
        line_heights = []
        line_widths = []
        
        for i, line in enumerate(all_lines):
            f = font if i < len(title_lines) else subtitle_font
            w, h = self._get_text_size(line, f)
            line_widths.append(w)
            line_heights.append(h)
        
        total_height = sum(line_heights) + line_spacing * (len(all_lines) - 1)
        max_width = max(line_widths)
        
        bg_width = max_width + padding * 2
        bg_height = total_height + padding * 2
        
        text_x, text_y = self._calculate_position(
            position, 
            (img_w, img_h), 
            (bg_width, bg_height)
        )
        
        if bg_color:
            draw.rounded_rectangle(
                [(text_x, text_y), (text_x + bg_width, text_y + bg_height)],
                radius=10,
                fill=bg_color
            )
        
        current_y = text_y + padding
        for i, line in enumerate(all_lines):
            f = font if i < len(title_lines) else subtitle_font
            line_w = line_widths[i]
            line_h = line_heights[i]
            
            line_x = text_x + (bg_width - line_w) // 2
            
            shadow_offset = 2
            draw.text(
                (line_x + shadow_offset, current_y + shadow_offset),
                line,
                font=f,
                fill=(0, 0, 0, 200)
            )
            
            draw.text(
                (line_x, current_y),
                line,
                font=f,
                fill=text_color
            )
            
            current_y += line_h + line_spacing
        
        return np.array(img_pil)

    def add_gradient_overlay(self,
                             image: np.ndarray,
                             direction: str = "bottom",
                             intensity: float = 0.5,
                             color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        h, w = image.shape[:2]
        gradient = np.zeros((h, w), dtype=np.float32)
        
        if direction == "bottom":
            for i in range(h):
                gradient[i, :] = (i / h) * intensity
        elif direction == "top":
            for i in range(h):
                gradient[i, :] = (1 - i / h) * intensity
        elif direction == "left":
            for i in range(w):
                gradient[:, i] = (1 - i / w) * intensity
        elif direction == "right":
            for i in range(w):
                gradient[:, i] = (i / w) * intensity
        elif direction == "center":
            center_y, center_x = h // 2, w // 2
            y, x = np.ogrid[:h, :w]
            dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
            gradient = (1 - dist / max_dist) * intensity
        
        result = image.copy().astype(np.float32)
        for c in range(3):
            result[:, :, c] = result[:, :, c] * (1 - gradient) + color[c] * gradient
        
        return result.astype(np.uint8)

    def add_border(self,
                   image: np.ndarray,
                   border_size: int = 10,
                   border_color: Tuple[int, int, int] = (255, 255, 255)) -> np.ndarray:
        return cv2.copyMakeBorder(
            image,
            border_size, border_size, border_size, border_size,
            cv2.BORDER_CONSTANT,
            value=border_color
        )

    def add_blur_background(self,
                            image: np.ndarray,
                            blur_strength: int = 25) -> np.ndarray:
        blurred = cv2.GaussianBlur(image, (blur_strength, blur_strength), 0)
        return blurred

    def create_thumbnail_template(self,
                                  image: np.ndarray,
                                  title: str,
                                  style: str = "modern") -> np.ndarray:
        result = image.copy()
        
        if style == "modern":
            result = self.add_gradient_overlay(result, "bottom", 0.6)
            result = self.add_text_overlay(
                result,
                title,
                position="bottom",
                font_size=52,
                font_family="impact",
                padding=25
            )
        elif style == "minimal":
            result = self.add_text_overlay(
                result,
                title,
                position="center",
                font_size=64,
                bg_color=None,
                padding=30
            )
        elif style == "bold":
            result = self.add_border(result, 15, (0, 0, 0))
            result = self.add_gradient_overlay(result, "bottom", 0.7)
            result = self.add_text_overlay(
                result,
                title,
                position="bottom",
                font_size=56,
                font_family="impact",
                text_color=(255, 200, 0),
                padding=30
            )
        elif style == "clean":
            result = self.add_text_overlay(
                result,
                title,
                position="bottom",
                font_size=42,
                font_family="arial",
                bg_color=(255, 255, 255, 230),
                text_color=(30, 30, 30),
                padding=20
            )
        
        return result

    def generate_title_variations(self, base_title: str) -> List[str]:
        variations = [
            base_title,
            base_title.upper(),
            f"🔥 {base_title} 🔥",
            f"必看！{base_title}",
            f"{base_title} - 完整教程"
        ]
        return variations

    def get_style_font_mapping(self) -> Dict[str, Dict]:
        return {
            "technology": {
                "fonts": ["impact", "arial_bold", "calibri"],
                "font_sizes": [56, 52, 48],
                "text_colors": [(0, 200, 255), (100, 255, 255), (255, 255, 255)],
                "bg_colors": [(0, 20, 40, 200), (0, 0, 0, 180)],
                "positions": ["bottom", "center", "top"],
                "styles": ["modern", "bold"]
            },
            "cute": {
                "fonts": ["arial", "verdana", "calibri"],
                "font_sizes": [52, 48, 44],
                "text_colors": [(255, 150, 180), (255, 200, 100), (255, 255, 255)],
                "bg_colors": [(255, 200, 220, 200), (255, 240, 200, 180), (0, 0, 0, 150)],
                "positions": ["bottom", "center"],
                "styles": ["clean", "modern"]
            },
            "warm": {
                "fonts": ["arial", "verdana", "times"],
                "font_sizes": [52, 48, 44],
                "text_colors": [(255, 200, 100), (255, 150, 50), (255, 255, 255)],
                "bg_colors": [(50, 20, 0, 180), (0, 0, 0, 180)],
                "positions": ["bottom", "top"],
                "styles": ["modern", "bold"]
            },
            "cool": {
                "fonts": ["calibri", "arial", "verdana"],
                "font_sizes": [52, 48, 44],
                "text_colors": [(100, 200, 255), (150, 220, 255), (255, 255, 255)],
                "bg_colors": [(0, 30, 60, 180), (0, 0, 0, 180)],
                "positions": ["bottom", "center"],
                "styles": ["modern", "clean"]
            },
            "professional": {
                "fonts": ["arial_bold", "calibri", "arial"],
                "font_sizes": [48, 44, 40],
                "text_colors": [(255, 255, 255), (200, 200, 200), (50, 50, 50)],
                "bg_colors": [(30, 30, 30, 200), (255, 255, 255, 230)],
                "positions": ["bottom", "top"],
                "styles": ["clean", "modern"]
            },
            "artistic": {
                "fonts": ["impact", "arial_bold", "times"],
                "font_sizes": [60, 56, 52],
                "text_colors": [(255, 255, 255), (255, 200, 100), (255, 100, 150)],
                "bg_colors": [(0, 0, 0, 150), None],
                "positions": ["center", "bottom", "top"],
                "styles": ["minimal", "modern"]
            },
            "default": {
                "fonts": ["impact", "arial_bold", "arial"],
                "font_sizes": [52, 48, 44],
                "text_colors": [(255, 255, 255)],
                "bg_colors": [(0, 0, 0, 180)],
                "positions": ["bottom"],
                "styles": ["modern"]
            }
        }

    def recommend_font_by_style(self, video_style: str) -> Dict:
        style_mapping = self.get_style_font_mapping()
        
        if video_style not in style_mapping:
            video_style = "default"
        
        style_config = style_mapping[video_style]
        
        return {
            "recommended_fonts": style_config["fonts"],
            "recommended_font_sizes": style_config["font_sizes"],
            "recommended_text_colors": style_config["text_colors"],
            "recommended_bg_colors": style_config["bg_colors"],
            "recommended_positions": style_config["positions"],
            "recommended_styles": style_config["styles"],
            "primary_font": style_config["fonts"][0],
            "primary_font_size": style_config["font_sizes"][0],
            "primary_text_color": style_config["text_colors"][0],
            "primary_bg_color": style_config["bg_colors"][0] if style_config["bg_colors"][0] else None,
            "primary_position": style_config["positions"][0],
            "primary_style": style_config["styles"][0]
        }

    def generate_style_based_thumbnails(self, 
                                         image: np.ndarray, 
                                         title: str, 
                                         video_style: str,
                                         num_variations: int = 3) -> List[Tuple[str, np.ndarray]]:
        recommendations = self.recommend_font_by_style(video_style)
        
        variations = []
        
        for i in range(min(num_variations, len(recommendations["recommended_fonts"]))):
            font = recommendations["recommended_fonts"][i]
            font_size = recommendations["recommended_font_sizes"][i]
            text_color = recommendations["recommended_text_colors"][i % len(recommendations["recommended_text_colors"])]
            bg_color = recommendations["recommended_bg_colors"][i % len(recommendations["recommended_bg_colors"])]
            position = recommendations["recommended_positions"][i % len(recommendations["recommended_positions"])]
            
            result = self.add_text_overlay(
                image,
                title=title,
                position=position,
                font_size=font_size,
                font_family=font,
                text_color=text_color,
                bg_color=bg_color
            )
            
            variation_name = f"{video_style}_风格_{i+1}"
            variations.append((variation_name, result))
        
        for style in recommendations["recommended_styles"][:1]:
            result = self.create_thumbnail_template(image, title, style)
            variations.append((f"{style}_模板", result))
        
        return variations

    def get_style_description(self, style_name: str) -> str:
        descriptions = {
            "technology": "🔵 科技感风格 - 冷色调、现代感字体、高对比度",
            "cute": "🌸 可爱风格 - 暖粉色调、圆润字体、柔和背景",
            "warm": "🌅 温暖风格 - 橙黄色调、亲切字体、温馨感觉",
            "cool": "❄️ 冷静风格 - 蓝色调、简洁字体、专业感",
            "professional": "💼 专业风格 - 黑白灰调、稳重字体、商务感",
            "artistic": "🎨 艺术风格 - 多彩搭配、创意字体、个性表达",
            "default": "📌 默认风格 - 经典搭配、通用适用"
        }
        return descriptions.get(style_name, descriptions["default"])
