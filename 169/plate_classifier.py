import cv2
import numpy as np
from config import PLATE_TYPE_CONFIG


class PlateClassifier:
    def __init__(self):
        self.plate_types = PLATE_TYPE_CONFIG

    def classify(self, plate_image, plate_text=None):
        if plate_image is None or plate_image.size == 0:
            return None
        
        color_type = self._classify_by_color(plate_image)
        text_type = self._classify_by_text(plate_text) if plate_text else None
        
        final_type = self._merge_results(color_type, text_type, plate_text)
        
        return final_type

    def _classify_by_color(self, plate_image):
        hsv = cv2.cvtColor(plate_image, cv2.COLOR_BGR2HSV)
        
        color_scores = {}
        
        for plate_type, config in self.plate_types.items():
            lower = np.array(config['hsv_lower'], dtype=np.uint8)
            upper = np.array(config['hsv_upper'], dtype=np.uint8)
            
            mask = cv2.inRange(hsv, lower, upper)
            score = np.sum(mask > 0) / (mask.shape[0] * mask.shape[1])
            
            color_scores[plate_type] = score
        
        sorted_types = sorted(color_scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_types and sorted_types[0][1] > 0.1:
            return {
                'type': sorted_types[0][0],
                'type_name': self.plate_types[sorted_types[0][0]]['name'],
                'confidence': sorted_types[0][1],
                'all_scores': color_scores
            }
        
        return None

    def _classify_by_text(self, plate_text):
        if not plate_text:
            return None
        
        plate_text = plate_text.upper().strip()
        
        if len(plate_text) == 8:
            if plate_text[0] in ['D', 'F', 'A', 'B', 'C', 'E']:
                return {
                    'type': 'new_energy_small',
                    'type_name': '新能源小车',
                    'confidence': 0.9
                }
            elif plate_text[0] in ['黄', '绿', '蓝']:
                return {
                    'type': 'new_energy_large',
                    'type_name': '新能源大车',
                    'confidence': 0.85
                }
            else:
                return {
                    'type': 'green',
                    'type_name': '绿牌(新能源)',
                    'confidence': 0.7
                }
        
        elif len(plate_text) == 7:
            hsv = self._get_dominant_color_hsv(plate_text)
            if hsv == 'yellow':
                return {
                    'type': 'yellow',
                    'type_name': '黄牌',
                    'confidence': 0.7
                }
            else:
                return {
                    'type': 'blue',
                    'type_name': '蓝牌',
                    'confidence': 0.6
                }
        
        return None

    def _get_dominant_color_hsv(self, plate_text):
        return 'unknown'

    def _merge_results(self, color_result, text_result, plate_text):
        if color_result and text_result:
            if color_result['type'] == text_result['type']:
                return {
                    'type': color_result['type'],
                    'type_name': color_result['type_name'],
                    'confidence': min(1.0, color_result['confidence'] + text_result['confidence']),
                    'source': 'color+text'
                }
            else:
                if color_result['confidence'] > text_result['confidence']:
                    return {
                        'type': color_result['type'],
                        'type_name': color_result['type_name'],
                        'confidence': color_result['confidence'],
                        'source': 'color'
                    }
                else:
                    return {
                        'type': text_result['type'],
                        'type_name': text_result['type_name'],
                        'confidence': text_result['confidence'],
                        'source': 'text'
                    }
        
        if color_result:
            return {
                'type': color_result['type'],
                'type_name': color_result['type_name'],
                'confidence': color_result['confidence'],
                'source': 'color'
            }
        
        if text_result:
            return {
                'type': text_result['type'],
                'type_name': text_result['type_name'],
                'confidence': text_result['confidence'],
                'source': 'text'
            }
        
        return {
            'type': 'unknown',
            'type_name': '未知',
            'confidence': 0.0,
            'source': 'none'
        }

    def get_plate_info(self, plate_type):
        return self.plate_types.get(plate_type, {})

    def validate_plate_length(self, plate_text, plate_type):
        if not plate_text:
            return False
        
        type_config = self.plate_types.get(plate_type)
        if not type_config:
            return True
        
        expected_length = type_config['char_count']
        return len(plate_text) == expected_length
