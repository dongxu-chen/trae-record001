import cv2
import numpy as np
from matplotlib import cm
from matplotlib.colors import Normalize


class ConfidenceHeatmap:
    def __init__(self):
        self.colormap = cm.get_cmap('jet')
        self.normalizer = Normalize(vmin=0, vmax=1)

    def generate_heatmap(self, image, plate_result):
        if image is None or plate_result is None:
            return None, {}
        
        bbox = plate_result.get('bbox')
        ocr_confidence = plate_result.get('ocr_confidence', 0)
        detection_confidence = plate_result.get('detection_confidence', 0)
        ocr_text = plate_result.get('ocr_text', '')
        
        if not bbox:
            return None, {}
        
        x, y, w, h = bbox
        
        plate_region = image[y:y+h, x:x+w].copy()
        
        if plate_region.size == 0:
            return None, {}
        
        heatmap_data = self._generate_heatmap_data(plate_region, ocr_text, ocr_confidence)
        
        heatmap_overlay = self._create_heatmap_overlay(plate_region, heatmap_data)
        
        quality_score = self._calculate_quality_score(plate_result, plate_region)
        
        analysis = self._analyze_quality(plate_result, plate_region, quality_score)
        
        result = {
            'bbox': bbox,
            'ocr_text': ocr_text,
            'ocr_confidence': ocr_confidence,
            'detection_confidence': detection_confidence,
            'quality_score': quality_score,
            'analysis': analysis,
            'heatmap_overlay': heatmap_overlay,
            'heatmap_data': heatmap_data
        }
        
        return heatmap_overlay, result

    def _generate_heatmap_data(self, plate_image, ocr_text, ocr_confidence):
        h, w = plate_image.shape[:2]
        heatmap = np.zeros((h, w), dtype=np.float32)
        
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(sobelx**2 + sobely**2)
        edge_magnitude = cv2.normalize(edge_magnitude, None, 0, 1, cv2.NORM_MINMAX)
        
        local_variance = self._local_variance(gray, kernel_size=5)
        local_variance = cv2.normalize(local_variance, None, 0, 1, cv2.NORM_MINMAX)
        
        brightness = gray.astype(np.float32) / 255.0
        brightness_score = 1 - np.abs(brightness - 0.5) * 2
        brightness_score = cv2.normalize(brightness_score, None, 0, 1, cv2.NORM_MINMAX)
        
        heatmap = 0.4 * edge_magnitude + 0.3 * local_variance + 0.3 * brightness_score
        
        if ocr_text and len(ocr_text) > 0:
            char_count = len(ocr_text)
            char_width = w / char_count
            
            for i in range(char_count):
                char_x1 = int(i * char_width)
                char_x2 = int((i + 1) * char_width)
                
                char_confidence = max(0.3, min(1.0, ocr_confidence + np.random.uniform(-0.1, 0.1)))
                
                gradient = np.linspace(char_confidence * 0.7, char_confidence, char_x2 - char_x1)
                for j in range(char_x1, min(char_x2, w)):
                    heatmap[:, j] *= gradient[j - char_x1]
        
        heatmap = cv2.GaussianBlur(heatmap, (5, 5), 0)
        heatmap = cv2.normalize(heatmap, None, 0, 1, cv2.NORM_MINMAX)
        
        return heatmap

    def _local_variance(self, image, kernel_size=5):
        image_float = image.astype(np.float32)
        kernel = np.ones((kernel_size, kernel_size), dtype=np.float32) / (kernel_size * kernel_size)
        
        mean = cv2.filter2D(image_float, -1, kernel)
        mean_sq = cv2.filter2D(image_float ** 2, -1, kernel)
        variance = mean_sq - mean ** 2
        
        return variance

    def _create_heatmap_overlay(self, plate_image, heatmap_data):
        h, w = plate_image.shape[:2]
        
        heatmap_colored = self.colormap(heatmap_data)
        heatmap_colored = (heatmap_colored[:, :, :3] * 255).astype(np.uint8)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_RGB2BGR)
        
        alpha = 0.4
        overlay = cv2.addWeighted(plate_image, 1 - alpha, heatmap_colored, alpha, 0)
        
        return overlay

    def _calculate_quality_score(self, plate_result, plate_image):
        scores = []
        
        ocr_conf = plate_result.get('ocr_confidence', 0)
        if ocr_conf:
            scores.append(('ocr_confidence', ocr_conf, 0.4))
        
        det_conf = plate_result.get('detection_confidence', 0)
        if det_conf:
            scores.append(('detection_confidence', det_conf / 100.0, 0.2))
        
        gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray) / 255.0
        brightness_score = 1 - abs(brightness - 0.5) * 2
        scores.append(('brightness', max(0, brightness_score), 0.15))
        
        contrast = np.std(gray) / 128.0
        contrast_score = min(1.0, contrast)
        scores.append(('contrast', contrast_score, 0.15))
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = np.var(laplacian)
        sharpness_score = min(1.0, sharpness / 1000.0)
        scores.append(('sharpness', sharpness_score, 0.1))
        
        total_score = sum(score * weight for _, score, weight in scores)
        
        return {
            'total': total_score,
            'components': {name: score for name, score, _ in scores}
        }

    def _analyze_quality(self, plate_result, plate_image, quality_score):
        analysis = {
            'overall_quality': self._rate_quality(quality_score['total']),
            'issues': [],
            'recommendations': [],
            'quality_score': quality_score['total'],
            'component_scores': quality_score['components']
        }
        
        components = quality_score['components']
        
        if components.get('brightness', 1) < 0.3:
            analysis['issues'].append('光照条件差')
            analysis['recommendations'].append('建议使用红外补光或改善照明条件')
        
        if components.get('contrast', 1) < 0.3:
            analysis['issues'].append('对比度不足')
            analysis['recommendations'].append('建议调整相机曝光参数')
        
        if components.get('sharpness', 1) < 0.3:
            analysis['issues'].append('图像模糊')
            analysis['recommendations'].append('建议检查相机对焦或降低车速')
        
        if components.get('ocr_confidence', 1) < 0.5:
            analysis['issues'].append('OCR识别置信度低')
            analysis['recommendations'].append('建议人工复核该车牌')
        
        if plate_result.get('ocr_text') and len(plate_result['ocr_text']) not in [7, 8]:
            analysis['issues'].append('车牌字符数异常')
            analysis['recommendations'].append('建议检查车牌完整性')
        
        if not analysis['issues']:
            analysis['issues'].append('无明显问题')
        
        return analysis

    def _rate_quality(self, score):
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'fair'
        elif score >= 0.2:
            return 'poor'
        else:
            return 'very_poor'

    def generate_full_image_heatmap(self, image, plate_results):
        if image is None or not plate_results:
            return image
        
        result_image = image.copy()
        
        for plate_result in plate_results:
            heatmap_overlay, analysis = self.generate_heatmap(image, plate_result)
            
            if heatmap_overlay is not None:
                x, y, w, h = plate_result['bbox']
                result_image[y:y+h, x:x+w] = heatmap_overlay
                
                result_image = self._draw_quality_indicator(
                    result_image, 
                    plate_result['bbox'], 
                    analysis.get('quality_score', {}).get('total', 0),
                    analysis.get('analysis', {}).get('overall_quality', 'unknown')
                )
        
        return result_image

    def _draw_quality_indicator(self, image, bbox, quality_score, quality_level):
        x, y, w, h = bbox
        
        color_map = {
            'excellent': (0, 255, 0),
            'good': (0, 200, 255),
            'fair': (0, 165, 255),
            'poor': (0, 0, 255),
            'very_poor': (128, 0, 128),
            'unknown': (128, 128, 128)
        }
        
        color = color_map.get(quality_level, (128, 128, 128))
        
        bar_height = 8
        bar_width = int(w * quality_score)
        
        cv2.rectangle(image, (x, y + h + 5), (x + w, y + h + 5 + bar_height), (50, 50, 50), -1)
        cv2.rectangle(image, (x, y + h + 5), (x + bar_width, y + h + 5 + bar_height), color, -1)
        
        label = f"{quality_score:.2f} - {quality_level}"
        cv2.putText(image, label, (x, y + h + 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return image

    def generate_quality_report(self, image, plate_results):
        report = {
            'timestamp': None,
            'image_size': image.shape[:2] if image is not None else None,
            'plate_count': len(plate_results),
            'plates': []
        }
        
        for plate_result in plate_results:
            _, analysis = self.generate_heatmap(image, plate_result)
            if analysis:
                report['plates'].append({
                    'plate_text': plate_result.get('ocr_text'),
                    'bbox': plate_result.get('bbox'),
                    'ocr_confidence': plate_result.get('ocr_confidence'),
                    'detection_confidence': plate_result.get('detection_confidence'),
                    'quality_analysis': analysis.get('analysis'),
                    'quality_score': analysis.get('quality_score', {}).get('total')
                })
        
        avg_quality = np.mean([p['quality_score'] for p in report['plates']]) if report['plates'] else 0
        report['average_quality'] = avg_quality
        
        return report

    def create_heatmap_legend(self, width=300, height=30):
        legend = np.zeros((height, width, 3), dtype=np.uint8)
        
        for i in range(width):
            color = self.colormap(i / width)[:3]
            color_bgr = (int(color[2] * 255), int(color[1] * 255), int(color[0] * 255))
            cv2.rectangle(legend, (i, 0), (i + 1, height), color_bgr, -1)
        
        cv2.putText(legend, 'Low', (5, height - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(legend, 'High', (width - 40, height - 8), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return legend
