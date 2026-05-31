import numpy as np
import cv2
from collections import deque
from config import SUBTITLE_CONFIG


class SubtitleEnhancer:
    def __init__(self, config=None, device=None):
        self.config = config or SUBTITLE_CONFIG
        self.enable = self.config.get('enable', False)
        self.min_area = self.config.get('min_area', 100)
        self.max_area_ratio = self.config.get('max_area_ratio', 0.5)
        self.aspect_ratio_range = self.config.get('aspect_ratio_range', (0.1, 10.0))
        self.sharpen_amount = self.config.get('sharpen_amount', 1.5)
        self.edge_enhance = self.config.get('edge_enhance', 1.2)
        self.contrast_adjust = self.config.get('contrast_adjust', 1.1)
        self.denoise_strength = self.config.get('denoise_strength', 5)
        self.detection_interval = self.config.get('detection_interval', 10)
        
        self.device = device
        self.frame_count = 0
        self.cached_text_regions = deque(maxlen=5)
        self.motion_history = None

    def reset(self):
        self.frame_count = 0
        self.cached_text_regions.clear()
        self.motion_history = None

    def detect_text_regions(self, frame):
        h, w = frame.shape[:2]
        img_uint8 = (frame * 255).astype(np.uint8)
        
        gray = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2GRAY)
        
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        edges = cv2.Canny(blur, 50, 150)
        
        struct_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(edges, struct_kernel, iterations=2)
        eroded = cv2.erode(dilated, struct_kernel, iterations=1)
        
        contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = []
        max_area = h * w * self.max_area_ratio
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area or area > max_area:
                continue
            
            x, y, w_rect, h_rect = cv2.boundingRect(contour)
            aspect_ratio = w_rect / h_rect if h_rect > 0 else 0
            
            min_ar, max_ar = self.aspect_ratio_range
            if aspect_ratio < min_ar or aspect_ratio > max_ar:
                continue
            
            roi_gray = gray[y:y + h_rect, x:x + w_rect]
            if roi_gray.size == 0:
                continue
            
            roi_mean = np.mean(roi_gray)
            roi_std = np.std(roi_gray)
            
            if roi_std < 20:
                continue
            
            text_regions.append({
                'bbox': (x, y, x + w_rect, y + h_rect),
                'area': area,
                'aspect_ratio': aspect_ratio,
                'contrast': roi_std,
                'mean_brightness': roi_mean,
            })
        
        merged_regions = self._merge_overlapping_regions(text_regions)
        
        return merged_regions

    def _merge_overlapping_regions(self, regions, iou_threshold=0.3):
        if len(regions) == 0:
            return []
        
        regions_sorted = sorted(regions, key=lambda r: r['area'], reverse=True)
        merged = []
        
        for region in regions_sorted:
            x1, y1, x2, y2 = region['bbox']
            overlaps = False
            
            for i, m in enumerate(merged):
                mx1, my1, mx2, my2 = m['bbox']
                
                overlap_x1 = max(x1, mx1)
                overlap_y1 = max(y1, my1)
                overlap_x2 = min(x2, mx2)
                overlap_y2 = min(y2, my2)
                
                if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                    overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                    min_area = min(region['area'], m['area'])
                    
                    if overlap_area / min_area > iou_threshold:
                        new_x1 = min(x1, mx1)
                        new_y1 = min(y1, my1)
                        new_x2 = max(x2, mx2)
                        new_y2 = max(y2, my2)
                        
                        merged[i] = {
                            'bbox': (new_x1, new_y1, new_x2, new_y2),
                            'area': (new_x2 - new_x1) * (new_y2 - new_y1),
                            'aspect_ratio': (new_x2 - new_x1) / (new_y2 - new_y1) if (new_y2 - new_y1) > 0 else 0,
                            'contrast': max(region['contrast'], m['contrast']),
                            'mean_brightness': (region['mean_brightness'] + m['mean_brightness']) / 2,
                        }
                        overlaps = True
                        break
            
            if not overlaps:
                merged.append(region)
        
        return merged

    def _stabilize_regions(self, regions):
        if len(self.cached_text_regions) == 0:
            return regions
        
        stable_regions = []
        for region in regions:
            x1, y1, x2, y2 = region['bbox']
            
            matched = None
            for cached in self.cached_text_regions:
                for cached_region in cached:
                    cx1, cy1, cx2, cy2 = cached_region['bbox']
                    
                    iou = self._calculate_iou(
                        (x1, y1, x2, y2),
                        (cx1, cy1, cx2, cy2)
                    )
                    
                    if iou > 0.5:
                        matched = cached_region
                        break
                if matched:
                    break
            
            if matched:
                mx1, my1, mx2, my2 = matched['bbox']
                stabilized = {
                    'bbox': (
                        int(x1 * 0.7 + mx1 * 0.3),
                        int(y1 * 0.7 + my1 * 0.3),
                        int(x2 * 0.7 + mx2 * 0.3),
                        int(y2 * 0.7 + my2 * 0.3),
                    ),
                    'area': region['area'],
                    'aspect_ratio': region['aspect_ratio'],
                    'contrast': region['contrast'],
                    'mean_brightness': region['mean_brightness'],
                }
                stable_regions.append(stabilized)
            else:
                stable_regions.append(region)
        
        return stable_regions

    def _calculate_iou(self, bbox1, bbox2):
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        x1 = max(x1_1, x1_2)
        y1 = max(y1_1, y1_2)
        x2 = min(x2_1, x2_2)
        y2 = min(y2_1, y2_2)
        
        if x2 <= x1 or y2 <= y1:
            return 0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0

    def _sharpen_subtitle(self, sub_img):
        blurred = cv2.GaussianBlur(sub_img, (0, 0), 3)
        sharpened = cv2.addWeighted(sub_img, 1 + self.sharpen_amount, blurred, -self.sharpen_amount, 0)
        return np.clip(sharpened, 0, 1)

    def _enhance_edges(self, sub_img):
        gray = cv2.cvtColor((sub_img * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX)
        
        edge_mask = np.stack([magnitude] * 3, axis=-1)
        enhanced = sub_img + edge_mask * (self.edge_enhance - 1)
        
        return np.clip(enhanced, 0, 1)

    def _adjust_contrast(self, sub_img):
        lab = cv2.cvtColor((sub_img * 255).astype(np.uint8), cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0].astype(np.float32)
        
        l_mean = np.mean(l_channel)
        l_std = np.std(l_channel)
        
        if l_std < 50:
            l_enhanced = (l_channel - l_mean) * self.contrast_adjust + l_mean
            l_enhanced = np.clip(l_enhanced, 0, 255)
            lab[:, :, 0] = l_enhanced.astype(np.uint8)
        
        adjusted = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR).astype(np.float32) / 255.0
        return adjusted

    def _denoise_subtitle(self, sub_img):
        denoised = cv2.fastNlMeansDenoisingColored(
            (sub_img * 255).astype(np.uint8),
            None,
            h=self.denoise_strength,
            hColor=self.denoise_strength,
            templateWindowSize=7,
            searchWindowSize=21
        )
        return denoised.astype(np.float32) / 255.0

    def _blend_subtitle(self, full_frame, enhanced_subtitle, x1, y1, x2, y2):
        h, w = full_frame.shape[:2]
        
        roi_h = y2 - y1
        roi_w = x2 - x1
        
        enhanced_resized = cv2.resize(
            enhanced_subtitle,
            (roi_w, roi_h),
            interpolation=cv2.INTER_LANCZOS4
        )
        
        mask = np.zeros((roi_h, roi_w), dtype=np.float32)
        center = (roi_w // 2, roi_h // 2)
        axes = (int(roi_w * 0.45), int(roi_h * 0.45))
        cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)
        
        mask = cv2.GaussianBlur(mask, (21, 21), 0)
        mask_3ch = np.stack([mask] * 3, axis=-1)
        
        blended_roi = (
            full_frame[y1:y2, x1:x2].astype(np.float32) * (1 - mask_3ch) +
            enhanced_resized * mask_3ch
        )
        
        result = full_frame.copy()
        result[y1:y2, x1:x2] = blended_roi
        
        return np.clip(result, 0, 1).astype(np.float32)

    def enhance_subtitles(self, frame):
        if not self.enable:
            return frame, []
        
        self.frame_count += 1
        
        if self.frame_count % self.detection_interval == 1:
            text_regions = self.detect_text_regions(frame)
            text_regions = self._stabilize_regions(text_regions)
            self.cached_text_regions.append(text_regions)
        else:
            text_regions = self.cached_text_regions[-1] if len(self.cached_text_regions) > 0 else []
        
        if len(text_regions) == 0:
            return frame, []
        
        enhanced_frame = frame.copy()
        enhanced_subtitles = []
        
        for region in text_regions:
            x1, y1, x2, y2 = region['bbox']
            
            if x2 <= x1 or y2 <= y1:
                continue
            
            subtitle_roi = frame[y1:y2, x1:x2]
            
            enhanced = self._denoise_subtitle(subtitle_roi)
            enhanced = self._adjust_contrast(enhanced)
            enhanced = self._sharpen_subtitle(enhanced)
            enhanced = self._enhance_edges(enhanced)
            
            enhanced_frame = self._blend_subtitle(enhanced_frame, enhanced, x1, y1, x2, y2)
            
            enhanced_subtitles.append({
                'bbox': (x1, y1, x2, y2),
                'confidence': min(1.0, region['contrast'] / 50.0),
            })
        
        return enhanced_frame, enhanced_subtitles

    def process(self, frame):
        return self.enhance_subtitles(frame)


def detect_text_in_frame(frame):
    try:
        h, w = frame.shape[:2]
        img_uint8 = (frame * 255).astype(np.uint8)
        
        gray = cv2.cvtColor(img_uint8, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        
        struct_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(edges, struct_kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < h * w * 0.5:
                x, y, w_rect, h_rect = cv2.boundingRect(contour)
                if 0.1 < w_rect / h_rect < 10.0:
                    regions.append((x, y, x + w_rect, y + h_rect))
        
        return regions
    except:
        return []


def enhance_text_region(img, amount=1.5):
    try:
        blurred = cv2.GaussianBlur(img, (0, 0), 3)
        sharpened = cv2.addWeighted(img, 1 + amount, blurred, -amount, 0)
        return np.clip(sharpened, 0, 1)
    except:
        return img
