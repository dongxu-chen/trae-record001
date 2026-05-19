import cv2
import numpy as np
from config import PLATE_TYPE_CONFIG, DETECTION_CONFIG


class PlateDetector:
    def __init__(self, config=None):
        self.config = config or DETECTION_CONFIG
        self.plate_types = PLATE_TYPE_CONFIG

    def detect(self, image):
        if image is None:
            return []
        
        candidates = []
        
        for plate_type, type_config in self.plate_types.items():
            plates = self._detect_by_color(image, plate_type, type_config)
            for plate in plates:
                plate['type'] = plate_type
                plate['type_name'] = type_config['name']
                candidates.append(plate)
        
        candidates = self._remove_duplicates(candidates)
        candidates = sorted(candidates, key=lambda x: x['confidence'], reverse=True)
        
        return candidates

    def _detect_by_color(self, image, plate_type, type_config):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        lower = np.array(type_config['hsv_lower'], dtype=np.uint8)
        upper = np.array(type_config['hsv_upper'], dtype=np.uint8)
        
        mask = cv2.inRange(hsv, lower, upper)
        
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            self.config['morph_kernel_size']
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        mask = cv2.GaussianBlur(mask, self.config['gaussian_kernel_size'], 0)
        
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        plates = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < self.config['min_area'] or area > self.config['max_area']:
                continue
            
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            
            width, height = rect[1]
            if width == 0 or height == 0:
                continue
            
            aspect_ratio = max(width, height) / min(width, height)
            
            if aspect_ratio < self.config['min_aspect_ratio'] or \
               aspect_ratio > self.config['max_aspect_ratio']:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            plate_region = image[y:y+h, x:x+w]
            
            if plate_region.size == 0:
                continue
            
            confidence = self._calculate_confidence(mask, contour, aspect_ratio, plate_type)
            
            plates.append({
                'bbox': (x, y, w, h),
                'rotated_box': box,
                'rect': rect,
                'aspect_ratio': aspect_ratio,
                'area': area,
                'confidence': confidence,
                'plate_image': plate_region
            })
        
        return plates

    def _calculate_confidence(self, mask, contour, aspect_ratio, plate_type):
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        
        mask_region = mask[y:y+h, x:x+w]
        color_density = np.sum(mask_region > 0) / (w * h) if w * h > 0 else 0
        
        if plate_type in ['blue', 'yellow']:
            optimal_ratio = 3.0
        else:
            optimal_ratio = 3.5
        
        ratio_score = 1 - abs(aspect_ratio - optimal_ratio) / optimal_ratio
        ratio_score = max(0, ratio_score)
        
        area_score = min(area / 5000, 1.0)
        
        confidence = (0.5 * color_density + 0.3 * ratio_score + 0.2 * area_score) * 100
        
        return min(confidence, 100)

    def _remove_duplicates(self, plates):
        if len(plates) <= 1:
            return plates
        
        plates_sorted = sorted(plates, key=lambda x: x['confidence'], reverse=True)
        
        unique_plates = []
        used_indices = set()
        
        for i, plate1 in enumerate(plates_sorted):
            if i in used_indices:
                continue
            
            unique_plates.append(plate1)
            x1, y1, w1, h1 = plate1['bbox']
            center1 = (x1 + w1 // 2, y1 + h1 // 2)
            
            for j, plate2 in enumerate(plates_sorted[i+1:], start=i+1):
                if j in used_indices:
                    continue
                
                x2, y2, w2, h2 = plate2['bbox']
                center2 = (x2 + w2 // 2, y2 + h2 // 2)
                
                distance = np.sqrt(
                    (center1[0] - center2[0]) ** 2 +
                    (center1[1] - center2[1]) ** 2
                )
                
                avg_size = (w1 + h1 + w2 + h2) / 4
                
                if distance < avg_size * 0.5:
                    used_indices.add(j)
        
        return unique_plates

    def detect_with_pyramid(self, image, scales=[1.0, 0.75, 0.5]):
        all_plates = []
        
        for scale in scales:
            if scale != 1.0:
                resized = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            else:
                resized = image
            
            plates = self.detect(resized)
            
            for plate in plates:
                x, y, w, h = plate['bbox']
                plate['bbox'] = (int(x / scale), int(y / scale), int(w / scale), int(h / scale))
                
                plate['rotated_box'] = (plate['rotated_box'] / scale).astype(np.int32)
                
                rect = list(plate['rect'])
                rect[0] = (rect[0][0] / scale, rect[0][1] / scale)
                rect[1] = (rect[1][0] / scale, rect[1][1] / scale)
                plate['rect'] = tuple(rect)
                
                plate['confidence'] *= (0.8 + 0.2 * scale)
                all_plates.append(plate)
        
        all_plates = self._remove_duplicates(all_plates)
        return sorted(all_plates, key=lambda x: x['confidence'], reverse=True)
