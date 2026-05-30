import numpy as np
import cv2
import random
from typing import Tuple, List, Optional


class MaskGenerator:
    def __init__(self, height: int = 256, width: int = 256):
        self.height = height
        self.width = width
    
    def generate_mask(self, mask_type: str = 'random', **kwargs) -> np.ndarray:
        if mask_type == 'random':
            mask_types = ['stroke', 'bbox', 'watermark', 'text', 'scratch']
            mask_type = random.choice(mask_types)
        
        if mask_type == 'stroke':
            return self.stroke_mask(**kwargs)
        elif mask_type == 'bbox':
            return self.bbox_mask(**kwargs)
        elif mask_type == 'watermark':
            return self.watermark_mask(**kwargs)
        elif mask_type == 'text':
            return self.text_mask(**kwargs)
        elif mask_type == 'scratch':
            return self.scratch_mask(**kwargs)
        elif mask_type == 'irregular':
            return self.irregular_mask(**kwargs)
        else:
            raise ValueError(f"Unknown mask type: {mask_type}")
    
    def stroke_mask(self, max_vertex: int = 10, max_length: int = 100,
                    max_brush_width: int = 40, max_angle: int = 360,
                    min_vertex: int = 2, min_length: int = 20,
                    min_brush_width: int = 10, min_angle: int = 0,
                    num_strokes: int = None) -> np.ndarray:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        if num_strokes is None:
            num_strokes = random.randint(1, 5)
        
        for _ in range(num_strokes):
            num_vertex = random.randint(min_vertex, max_vertex)
            start_x = random.randint(0, self.width)
            start_y = random.randint(0, self.height)
            
            points = [(start_x, start_y)]
            for _ in range(num_vertex - 1):
                angle = random.uniform(min_angle, max_angle)
                length = random.uniform(min_length, max_length)
                brush_width = random.randint(min_brush_width, max_brush_width)
                
                if points:
                    prev_x, prev_y = points[-1]
                    rad = np.deg2rad(angle)
                    new_x = int(prev_x + length * np.cos(rad))
                    new_y = int(prev_y + length * np.sin(rad))
                    
                    new_x = max(0, min(new_x, self.width - 1))
                    new_y = max(0, min(new_y, self.height - 1))
                    
                    points.append((new_x, new_y))
                    
                    cv2.line(mask, (prev_x, prev_y), (new_x, new_y), 255, brush_width)
        
        return mask.astype(np.float32) / 255.0
    
    def bbox_mask(self, min_size: Tuple[int, int] = (30, 30),
                   max_size: Tuple[int, int] = (100, 100),
                   num_boxes: int = None,
                   max_overlap: bool = True) -> np.ndarray:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        if num_boxes is None:
            num_boxes = random.randint(1, 3)
        
        for _ in range(num_boxes):
            w = random.randint(min_size[0], max_size[0])
            h = random.randint(min_size[1], max_size[1])
            
            x = random.randint(0, max(0, self.width - w - 1))
            y = random.randint(0, max(0, self.height - h - 1))
            
            if not max_overlap and np.any(mask[y:y+h, x:x+w]):
                continue
            
            mask[y:y+h, x:x+w] = 255
        
        return mask.astype(np.float32) / 255.0
    
    def watermark_mask(self, text: str = None,
                      font_scale: float = None,
                      thickness: int = None,
                      rotation: int = None,
                      num_texts: int = 1) -> np.ndarray:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        if text is None:
            watermark_texts = ['WATERMARK', 'COPYRIGHT', 'SAMPLE', 'DEMO', 'PROOF']
            text = random.choice(watermark_texts)
        
        if font_scale is None:
            font_scale = random.uniform(1.0, 3.0)
        
        if thickness is None:
            thickness = random.randint(2, 5)
        
        if rotation is None:
            rotation = random.randint(-30, 30)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        for _ in range(num_texts):
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            
            center_x = random.randint(text_size[0] // 2, self.width - text_size[0] // 2)
            center_y = random.randint(text_size[1] // 2, self.height - text_size[1] // 2)
            
            M = cv2.getRotationMatrix2D((center_x, center_y), rotation, 1.0)
            
            text_mask = np.zeros_like(mask.shape, dtype=np.uint8)
            cv2.putText(text_mask, text, 
                        (center_x - text_size[0]//2, center_y + text_size[1]//2),
                        font, font_scale, 255, thickness)
            
            rotated_text = cv2.warpAffine(text_mask, M, (self.width, self.height))
            
            mask = np.maximum(mask, rotated_text)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        return mask.astype(np.float32) / 255.0
    
    def text_mask(self, text: str = None,
                 font_scale: float = 1.5,
                 thickness: int = 3) -> np.ndarray:
        return self.watermark_mask(text=text, font_scale=font_scale, 
                                 thickness=thickness, rotation=0)
    
    def scratch_mask(self, num_scratches: int = None,
                     min_length: int = 50,
                     max_length: int = 200,
                     min_thickness: int = 1,
                     max_thickness: int = 5) -> np.ndarray:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        if num_scratches is None:
            num_scratches = random.randint(3, 10)
        
        for _ in range(num_scratches):
            x1 = random.randint(0, self.width - 1)
            y1 = random.randint(0, self.height - 1)
            
            length = random.randint(min_length, max_length)
            angle = random.uniform(0, 2 * np.pi)
            thickness = random.randint(min_thickness, max_thickness)
            
            x2 = int(x1 + length * np.cos(angle))
            y2 = int(y1 + length * np.sin(angle))
            
            x2 = max(0, min(x2, self.width - 1))
            y2 = max(0, min(y2, self.height - 1))
            
            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2
            
            control_points = [
                (x1, y1),
                (mid_x + random.randint(-20, 20), mid_y + random.randint(-20, 20)),
                (x2, y2)
            ]
        
        pts = np.array([control_points], np.int32)
        cv2.polylines(mask, [pts], False, 255, thickness)
        
        return mask.astype(np.float32) / 255.0
    
    def irregular_mask(self, max_vertices: int = 20,
                       irregularity: float = 0.2,
                       spikeyness: float = 0.2) -> np.ndarray:
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        num_shapes = random.randint(1, 3)
        
        for _ in range(num_shapes):
            center_x = random.randint(self.width // 4, 3 * self.width // 4)
            center_y = random.randint(self.height // 4, 3 * self.height // 4)
            
            avg_radius = random.randint(20, 80)
            
            points = []
            for i in range(max_vertices):
                angle = 2 * np.pi * i / max_vertices
                
                radius_factor = 1 + random.uniform(-irregularity, irregularity)
                spike_factor = 1 + random.uniform(-spikeyness, spikeyness)
                
                radius = int(avg_radius * radius_factor * spike_factor)
                
                x = int(center_x + radius * np.cos(angle))
                y = int(center_y + radius * np.sin(angle))
                
                x = max(0, min(x, self.width - 1))
                y = max(0, min(y, self.height - 1))
                
                points.append((x, y))
            
            points = np.array([points], dtype=np.int32)
            cv2.fillPoly(mask, [points], 255)
        
        return mask.astype(np.float32) / 255.0
    
    def load_mask_from_file(self, mask_path: str,
                           threshold: int = 127,
                           invert: bool = False) -> np.ndarray:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise ValueError(f"Cannot load mask from {mask_path}")
        
        if mask.shape[:2] != (self.height, self.width):
            mask = cv2.resize(mask, (self.width, self.height))
        
        _, mask = cv2.threshold(mask, threshold, 255, cv2.THRESH_BINARY)
        
        if invert:
            mask = 255 - mask
        
        return mask.astype(np.float32) / 255.0
    
    def apply_mask_to_image(self, image: np.ndarray,
                          mask: np.ndarray,
                          fill_value: int = 255) -> np.ndarray:
        if len(image.shape) == 3:
            mask_3d = np.stack([mask] * 3, axis=-1)
        else:
            mask_3d = mask
        
        masked_image = image * (1 - mask_3d) + fill_value * mask_3d
        
        return masked_image
    
    def resize(self, height: int, width: int):
        self.height = height
        self.width = width
    
    def generate_batch(self, batch_size: int,
                        mask_type: str = 'random') -> List[np.ndarray]:
        masks = []
        for _ in range(batch_size):
            masks.append(self.generate_mask(mask_type))
        return masks
