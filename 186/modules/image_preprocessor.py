import os
import base64
import io
import math
from typing import Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter


class ImagePreprocessor:
    def __init__(self, max_size: int = 1920, quality: int = 90):
        self.max_size = max_size
        self.quality = quality

    def preprocess_for_ocr(self, image_path: str) -> Tuple[str, dict]:
        stats = {
            'original_size': None,
            'processed_size': None,
            'rotation_applied': 0,
            'enhancement_applied': False,
            'processing_time': 0
        }

        try:
            import time
            start_time = time.time()

            img = Image.open(image_path)
            stats['original_size'] = img.size

            img = self._correct_orientation(img)
            
            rotation_angle = self._detect_rotation_angle(img)
            if abs(rotation_angle) > 1.0:
                img = img.rotate(rotation_angle, resample=Image.BICUBIC, expand=True)
                stats['rotation_applied'] = rotation_angle

            img = self._resize_image(img)
            
            img = self._enhance_image(img)
            stats['enhancement_applied'] = True

            img = self._denoise_image(img)

            stats['processed_size'] = img.size
            stats['processing_time'] = time.time() - start_time

            return self._image_to_base64(img), stats

        except Exception as e:
            print(f"Image preprocessing error: {e}")
            try:
                with open(image_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8'), stats
            except:
                return '', stats

    def _correct_orientation(self, img: Image.Image) -> Image.Image:
        try:
            exif = img._getexif()
            if exif:
                orientation = exif.get(0x0112, 1)
                
                if orientation == 2:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 3:
                    img = img.rotate(180)
                elif orientation == 4:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    img = img.rotate(-90).transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 6:
                    img = img.rotate(-90)
                elif orientation == 7:
                    img = img.rotate(90).transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 8:
                    img = img.rotate(90)
        except (AttributeError, KeyError, IndexError):
            pass

        return img

    def _detect_rotation_angle(self, img: Image.Image) -> float:
        try:
            gray_img = img.convert('L')
            
            edges = self._detect_edges(gray_img)
            
            angle = self._hough_line_transform(edges)
            
            return angle
        except Exception as e:
            print(f"Rotation detection error: {e}")
            return 0.0

    def _detect_edges(self, img: Image.Image) -> Image.Image:
        return img.filter(ImageFilter.FIND_EDGES)

    def _hough_line_transform(self, edge_img: Image.Image) -> float:
        try:
            width, height = edge_img.size
            pixels = edge_img.load()
            
            angles = []
            
            for y in range(0, height, 2):
                line_pixels = []
                for x in range(0, width, 2):
                    if pixels[x, y] > 128:
                        line_pixels.append((x, y))
                
                if len(line_pixels) >= 5:
                    angle = self._fit_line_angle(line_pixels)
                    if abs(angle) < 45:
                        angles.append(angle)
            
            if angles:
                return sum(angles) / len(angles)
            
            return 0.0
        except Exception as e:
            print(f"Hough transform error: {e}")
            return 0.0

    def _fit_line_angle(self, points: list) -> float:
        if len(points) < 2:
            return 0.0
        
        n = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_xx = sum(p[0] * p[0] for p in points)
        
        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            return 90.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        angle = math.degrees(math.atan(slope))
        
        return angle

    def _resize_image(self, img: Image.Image) -> Image.Image:
        width, height = img.size
        
        if max(width, height) <= self.max_size:
            return img
        
        if width >= height:
            new_width = self.max_size
            new_height = int(height * (self.max_size / width))
        else:
            new_height = self.max_size
            new_width = int(width * (self.max_size / height))
        
        return img.resize((new_width, new_height), Image.LANCZOS)

    def _enhance_image(self, img: Image.Image) -> Image.Image:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.3)
        
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        
        return img

    def _denoise_image(self, img: Image.Image) -> Image.Image:
        return img.filter(ImageFilter.MedianFilter(size=3))

    def _image_to_base64(self, img: Image.Image, format: str = 'JPEG') -> str:
        buffer = io.BytesIO()
        img.save(buffer, format=format, quality=self.quality)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def save_preprocessed_image(self, image_path: str, output_path: str) -> dict:
        try:
            img = Image.open(image_path)
            
            img = self._correct_orientation(img)
            
            rotation_angle = self._detect_rotation_angle(img)
            if abs(rotation_angle) > 1.0:
                img = img.rotate(rotation_angle, resample=Image.BICUBIC, expand=True)
            
            img = self._resize_image(img)
            img = self._enhance_image(img)
            img = self._denoise_image(img)
            
            img.save(output_path, quality=self.quality)
            
            return {
                'success': True,
                'output_path': output_path,
                'rotation_applied': rotation_angle
            }
        except Exception as e:
            print(f"Save preprocessed image error: {e}")
            return {'success': False, 'error': str(e)}


def preprocess_image(image_path: str, output_dir: str = None) -> Tuple[Optional[str], dict]:
    preprocessor = ImagePreprocessor()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"preprocessed_{os.path.basename(image_path)}")
        result = preprocessor.save_preprocessed_image(image_path, output_path)
        if result['success']:
            return output_path, result
    
    return preprocessor.preprocess_for_ocr(image_path)
