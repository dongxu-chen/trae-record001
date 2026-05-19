import re
import cv2
import numpy as np
from config import OCR_CONFIG, PLATE_TYPE_CONFIG


class OCRRecognizer:
    def __init__(self, config=None):
        self.config = config or OCR_CONFIG
        self._ocr = None
        self._init_ocr()
        
        self.new_energy_prefixes = {'D', 'F', 'A', 'B', 'C', 'E', 'G', 'H'}
        self.provinces = '京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领'
    
    def _init_ocr(self):
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=self.config['use_angle_cls'],
                lang=self.config['lang'],
                show_log=self.config['show_log'],
                det_model_dir=self.config['det_model_dir'],
                rec_model_dir=self.config['rec_model_dir'],
                cls_model_dir=self.config['cls_model_dir']
            )
        except Exception as e:
            print(f"Warning: Failed to initialize PaddleOCR: {e}")
            self._ocr = None
    
    def recognize(self, plate_image):
        if plate_image is None or plate_image.size == 0:
            return None
        
        if self._ocr is None:
            return self._fallback_recognize(plate_image)
        
        try:
            result = self._ocr.ocr(plate_image, cls=True)
            
            if not result or len(result) == 0:
                return None
            
            plate_text, confidence = self._parse_ocr_result(result)
            plate_text = self._validate_and_correct_plate(plate_text)
            
            return {
                'text': plate_text,
                'confidence': confidence,
                'raw_result': result
            }
            
        except Exception as e:
            print(f"OCR recognition error: {e}")
            return None
    
    def _parse_ocr_result(self, result):
        texts = []
        confidences = []
        
        for line in result:
            if not line:
                continue
            
            for word_info in line:
                if len(word_info) >= 2:
                    text = word_info[1][0]
                    confidence = word_info[1][1]
                    texts.append(text)
                    confidences.append(confidence)
        
        if not texts:
            return None, 0.0
        
        combined_text = ''.join(texts)
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        return combined_text, avg_confidence
    
    def _validate_and_correct_plate(self, plate_text):
        if not plate_text:
            return None
        
        plate_text = plate_text.upper().strip()
        plate_text = re.sub(r'[^\w·]', '', plate_text)
        plate_text = plate_text.replace('·', '')
        
        plate_type = self._detect_plate_type(plate_text)
        
        if plate_type == 'new_energy':
            corrected = self._correct_new_energy_plate(plate_text)
        elif plate_type == 'normal':
            corrected = self._correct_normal_plate(plate_text)
        else:
            corrected = self._adaptive_correction(plate_text)
        
        if self._is_valid_format(corrected):
            return corrected
        
        return self._flexible_match(plate_text)
    
    def _detect_plate_type(self, text):
        if not text or len(text) < 2:
            return 'unknown'
        
        if len(text) >= 6 and len(text) <= 8:
            if text[0] in self.provinces:
                if len(text) == 8:
                    return 'new_energy'
                elif len(text) == 7:
                    if text[1] in self.new_energy_prefixes and len(text) == 8:
                        return 'new_energy'
                    return 'normal'
                elif len(text) == 6:
                    return 'new_energy'
        
        return 'unknown'
    
    def _correct_new_energy_plate(self, text):
        if len(text) < 6 or len(text) > 8:
            return self._adjust_new_energy_length(text)
        
        corrected = list(text)
        
        if corrected[0] not in self.provinces:
            corrected[0] = self._correct_province(corrected[0])
        
        if len(corrected) >= 2:
            if corrected[1] in self.new_energy_prefixes:
                pass
            elif corrected[1].isdigit():
                digit_map = {'0': 'D', '1': 'I', '4': 'A', '6': 'G', '8': 'B'}
                if corrected[1] in digit_map:
                    corrected[1] = digit_map[corrected[1]]
        
        for i in range(2, min(len(corrected), 8)):
            corrected[i] = self._correct_digit(corrected[i])
        
        result = ''.join(corrected)
        
        if len(result) < 8:
            result = self._pad_new_energy_plate(result)
        elif len(result) > 8:
            result = result[:8]
        
        return result
    
    def _adjust_new_energy_length(self, text):
        if len(text) < 6:
            return text
        
        if len(text) == 6:
            if text[0] in self.provinces and text[1] in self.new_energy_prefixes:
                return text + '0'
            return text
        
        if len(text) > 8:
            if text[0] in self.provinces:
                return text[:8]
        
        return text[:8] if len(text) > 8 else text.ljust(8, '0')
    
    def _pad_new_energy_plate(self, text):
        if len(text) >= 8:
            return text[:8]
        
        if len(text) == 7:
            if text[1] in self.new_energy_prefixes:
                return text[:2] + '0' + text[2:]
            return text + '0'
        
        if len(text) == 6:
            if text[1] in self.new_energy_prefixes:
                return text[:2] + '00' + text[2:]
            return text + '00'
        
        return text.ljust(8, '0')
    
    def _correct_normal_plate(self, text):
        if len(text) != 7:
            return self._adjust_normal_length(text)
        
        corrected = list(text)
        
        if corrected[0] not in self.provinces:
            corrected[0] = self._correct_province(corrected[0])
        
        if len(corrected) >= 2 and not corrected[1].isalpha():
            corrected[1] = self._correct_letter(corrected[1])
        
        for i in range(2, 7):
            corrected[i] = self._correct_digit(corrected[i])
        
        return ''.join(corrected)
    
    def _adjust_normal_length(self, text):
        if len(text) < 7:
            if len(text) == 6 and text[0] in self.provinces:
                return text + '0'
            return text.ljust(7, '0')
        elif len(text) > 7:
            if text[0] in self.provinces:
                return text[:7]
            return text[:7]
        
        return text
    
    def _adaptive_correction(self, text):
        length = len(text)
        
        if length < 6:
            return text
        
        if length == 6:
            if text[0] in self.provinces and text[1] in self.new_energy_prefixes:
                return self._correct_new_energy_plate(text)
            return self._correct_normal_plate(text + '0')
        
        if length == 7:
            if text[0] in self.provinces:
                if text[1] in self.new_energy_prefixes:
                    corrected = self._correct_new_energy_plate(text + '0')
                    if self._is_valid_new_energy(corrected):
                        return corrected
                return self._correct_normal_plate(text)
        
        if length == 8:
            if text[0] in self.provinces and text[1] in self.new_energy_prefixes:
                return self._correct_new_energy_plate(text)
            return self._correct_normal_plate(text[:7])
        
        if length > 8:
            if text[0] in self.provinces:
                if text[1] in self.new_energy_prefixes:
                    return self._correct_new_energy_plate(text[:8])
                return self._correct_normal_plate(text[:7])
        
        return text
    
    def _correct_province(self, char):
        province_map = {
            '1': 'I', 'I': '1',
            '0': 'O', 'O': '0',
            'Q': '0', 'D': '0',
            'Z': '2', 'S': '5',
            'B': '8', 'G': '6',
            'g': '9', 'q': '9',
            'l': '1', 'L': '1',
            'o': '0'
        }
        
        if char in province_map:
            candidate = province_map[char]
            if candidate in self.provinces:
                return candidate
        
        for province in self.provinces:
            if province == char or province.lower() == char.lower():
                return province
        
        return char
    
    def _correct_letter(self, char):
        letter_map = {
            '0': 'O', '1': 'I', '4': 'A',
            '6': 'G', '8': 'B', '5': 'S',
            '2': 'Z', '9': 'Q'
        }
        
        if char in letter_map:
            return letter_map[char]
        
        if char.isalpha():
            return char.upper()
        
        return char
    
    def _correct_digit(self, char):
        digit_map = {
            'O': '0', 'o': '0', 'Q': '0', 'D': '0',
            'I': '1', 'l': '1', 'L': '1',
            'Z': '2', 'S': '5', 'B': '8',
            'G': '6', 'g': '9', 'q': '9'
        }
        
        if char in digit_map:
            return digit_map[char]
        
        if char.isdigit():
            return char
        
        return char
    
    def _is_valid_format(self, text):
        if not text or len(text) < 6 or len(text) > 8:
            return False
        
        if text[0] not in self.provinces:
            return False
        
        if len(text) == 8:
            return self._is_valid_new_energy(text)
        elif len(text) == 7:
            return self._is_valid_normal(text)
        elif len(text) == 6:
            return self._is_valid_short_format(text)
        
        return False
    
    def _is_valid_new_energy(self, text):
        if len(text) != 8:
            return False
        
        if text[0] not in self.provinces:
            return False
        
        if text[1] not in self.new_energy_prefixes and not text[1].isalpha():
            return False
        
        for char in text[2:]:
            if not char.isalnum():
                return False
        
        return True
    
    def _is_valid_normal(self, text):
        if len(text) != 7:
            return False
        
        if text[0] not in self.provinces:
            return False
        
        if not text[1].isalpha() or not text[1].isupper():
            return False
        
        for char in text[2:]:
            if not char.isalnum():
                return False
        
        return True
    
    def _is_valid_short_format(self, text):
        if len(text) != 6:
            return False
        
        if text[0] not in self.provinces:
            return False
        
        if text[1] not in self.new_energy_prefixes and not text[1].isalpha():
            return False
        
        for char in text[2:]:
            if not char.isalnum():
                return False
        
        return True
    
    def _flexible_match(self, text):
        if not text or len(text) < 2:
            return text
        
        candidates = []
        
        if len(text) >= 7:
            normal_candidate = self._correct_normal_plate(text[:7])
            if self._is_valid_normal(normal_candidate):
                candidates.append((normal_candidate, 7))
        
        if len(text) >= 6:
            if len(text) >= 8:
                new_energy_candidate = self._correct_new_energy_plate(text[:8])
            else:
                new_energy_candidate = self._correct_new_energy_plate(text)
            if self._is_valid_new_energy(new_energy_candidate):
                candidates.append((new_energy_candidate, 8))
        
        if len(text) == 6:
            short_candidate = self._correct_new_energy_plate(text)
            if self._is_valid_short_format(short_candidate):
                candidates.append((short_candidate, 6))
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return self._best_effort_correction(text)
    
    def _best_effort_correction(self, text):
        corrected = list(text)
        
        if len(corrected) > 0 and corrected[0] not in self.provinces:
            corrected[0] = self._correct_province(corrected[0])
        
        if len(corrected) > 1 and not corrected[1].isalpha():
            corrected[1] = self._correct_letter(corrected[1])
        
        for i in range(2, len(corrected)):
            corrected[i] = self._correct_digit(corrected[i])
        
        return ''.join(corrected)
    
    def _fallback_recognize(self, plate_image):
        return {
            'text': None,
            'confidence': 0.0,
            'error': 'PaddleOCR not available'
        }
    
    def recognize_with_augmentation(self, plate_image):
        results = []
        
        original_result = self.recognize(plate_image)
        if original_result and original_result['text']:
            results.append(original_result)
        
        flipped = cv2.flip(plate_image, 1)
        flipped_result = self.recognize(flipped)
        if flipped_result and flipped_result['text']:
            results.append(flipped_result)
        
        bright = self._adjust_brightness(plate_image, 1.2)
        bright_result = self.recognize(bright)
        if bright_result and bright_result['text']:
            results.append(bright_result)
        
        dark = self._adjust_brightness(plate_image, 0.8)
        dark_result = self.recognize(dark)
        if dark_result and dark_result['text']:
            results.append(dark_result)
        
        clahe_img = self._apply_clahe(plate_image)
        clahe_result = self.recognize(clahe_img)
        if clahe_result and clahe_result['text']:
            results.append(clahe_result)
        
        if not results:
            return None
        
        valid_results = [r for r in results if self._is_valid_format(r['text'])]
        if valid_results:
            return max(valid_results, key=lambda x: x['confidence'])
        
        return max(results, key=lambda x: x['confidence'])
    
    def _apply_clahe(self, image):
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    def _adjust_brightness(self, image, factor):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
