import os
import base64
import requests
import time
import re
import io
from typing import List, Dict, Tuple, Optional
from config.config import OCR_API_KEY, OCR_API_ENDPOINT, MIN_CONFIDENCE, VIOLATION_TYPES, REQUEST_TIMEOUT
from models import ViolationModel
from .image_preprocessor import ImagePreprocessor


class OCRAuditor:
    def __init__(self, video_id: int, enable_preprocessing: bool = True):
        self.video_id = video_id
        self.api_calls = 0
        self.api_errors = 0
        self.violations: List[Dict] = []
        self.enable_preprocessing = enable_preprocessing
        self.preprocessor = ImagePreprocessor() if enable_preprocessing else None
        self.preprocessing_stats = {
            'total_frames': 0,
            'rotated_frames': 0,
            'total_rotation_angle': 0.0,
            'preprocessing_time': 0.0
        }
        
        self.political_keywords = [
            '政府', '抗议', '游行', '示威', '革命', '政权', '政党', '领导人',
            '分裂', '独立', '反动', '颠覆', '煽动', '暴乱', '动乱',
            'government', 'protest', 'demonstration', 'riot', 'revolution'
        ]
        
        self.porn_keywords = [
            '色情', '淫荡', '裸体', '性', '性交', '卖淫', '嫖娼', '包养',
            'porn', 'sexy', 'nude', 'sex', 'fuck', 'pussy', 'dick'
        ]
        
        self.violence_keywords = [
            '暴力', '杀戮', '血腥', '恐怖', '爆炸', '枪支', '武器', '弹药',
            '杀人', '抢劫', '绑架', '勒索', '威胁', '殴打', '虐待',
            'violence', 'kill', 'blood', 'terror', 'gun', 'weapon', 'bomb'
        ]

    def extract_text(self, image_path: str) -> str:
        if not OCR_API_KEY:
            return self._mock_ocr(image_path)

        try:
            self.preprocessing_stats['total_frames'] += 1
            
            if self.enable_preprocessing and self.preprocessor:
                preprocessed_base64, stats = self.preprocessor.preprocess_for_ocr(image_path)
                self.preprocessing_stats['preprocessing_time'] += stats.get('processing_time', 0)
                if stats.get('rotation_applied', 0) != 0:
                    self.preprocessing_stats['rotated_frames'] += 1
                    self.preprocessing_stats['total_rotation_angle'] += abs(stats['rotation_applied'])
                
                image_data = base64.b64decode(preprocessed_base64)
            else:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
            
            payload = {
                'apikey': OCR_API_KEY,
                'language': 'chs',
                'isOverlayRequired': False,
                'OCREngine': 2
            }
            
            files = {'file': (os.path.basename(image_path), image_data, 'image/jpeg')}
            self.api_calls += 1
            
            response = requests.post(
                OCR_API_ENDPOINT,
                files=files,
                data=payload,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('IsErroredOnProcessing'):
                    self.api_errors += 1
                    return ''
                
                parsed_results = result.get('ParsedResults', [])
                text_parts = [r.get('ParsedText', '') for r in parsed_results]
                return '\n'.join(text_parts)
            else:
                self.api_errors += 1
                return ''
                
        except requests.Timeout:
            self.api_errors += 1
            return ''
        except Exception as e:
            self.api_errors += 1
            print(f"OCR API exception: {str(e)}")
            return ''

    def _mock_ocr(self, image_path: str) -> str:
        import random
        random.seed(os.path.getsize(image_path) if os.path.exists(image_path) else 0)
        
        mock_texts = [
            '',
            '',
            '',
            '',
            '',
            '这是正常的字幕内容',
            '欢迎观看本视频',
            '政府发言人发表讲话',
            '暴力犯罪是严重的社会问题',
            '色情内容不适合未成年人观看'
        ]
        
        text = random.choice(mock_texts)
        time.sleep(0.05)
        return text

    def analyze_text(self, text: str, timestamp: float, image_path: str, frame_id: int = None) -> List[Dict]:
        if not text:
            return []

        violations = []
        text_lower = text.lower()

        political_score = self._check_keywords(text_lower, self.political_keywords)
        if political_score >= MIN_CONFIDENCE:
            violations.append(self._create_violation(
                'text_politics', timestamp, political_score,
                f"文本涉政检测: {text[:50]}",
                text, image_path, frame_id
            ))

        porn_score = self._check_keywords(text_lower, self.porn_keywords)
        if porn_score >= MIN_CONFIDENCE:
            violations.append(self._create_violation(
                'text_porn', timestamp, porn_score,
                f"文本色情检测: {text[:50]}",
                text, image_path, frame_id
            ))

        violence_score = self._check_keywords(text_lower, self.violence_keywords)
        if violence_score >= MIN_CONFIDENCE:
            violations.append(self._create_violation(
                'text_violence', timestamp, violence_score,
                f"文本暴力检测: {text[:50]}",
                text, image_path, frame_id
            ))

        return violations

    def _check_keywords(self, text: str, keywords: List[str]) -> float:
        if not text:
            return 0.0

        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in text:
                found_keywords.append(keyword)

        if not found_keywords:
            return 0.0

        base_score = 0.5
        keyword_bonus = min(len(found_keywords) * 0.15, 0.4)
        
        return min(base_score + keyword_bonus, 1.0)

    def _create_violation(self, violation_type: str, timestamp: float, confidence: float,
                         description: str, ocr_text: str, image_path: str, frame_id: int) -> Dict:
        return {
            'video_id': self.video_id,
            'frame_id': frame_id,
            'violation_type': violation_type,
            'violation_type_name': VIOLATION_TYPES.get(violation_type, violation_type),
            'timestamp': timestamp,
            'confidence': confidence,
            'description': description,
            'ocr_text': ocr_text,
            'image_path': image_path
        }

    def save_violations(self, violations: List[Dict]):
        for v in violations:
            try:
                ViolationModel.create(
                    video_id=v['video_id'],
                    frame_id=v.get('frame_id'),
                    violation_type=v['violation_type'],
                    violation_type_name=v['violation_type_name'],
                    timestamp=v.get('timestamp'),
                    confidence=v['confidence'],
                    description=v.get('description'),
                    ocr_text=v.get('ocr_text'),
                    image_path=v.get('image_path')
                )
                self.violations.append(v)
            except Exception as e:
                print(f"Warning: Failed to save OCR violation: {e}")

    def analyze_frames(self, frames: List[Dict]) -> Tuple[List[Dict], int, int]:
        all_violations = []
        
        for frame in frames:
            text = self.extract_text(frame['image_path'])
            if text:
                violations = self.analyze_text(
                    text=text,
                    timestamp=frame['timestamp'],
                    image_path=frame['image_path'],
                    frame_id=frame.get('frame_number')
                )
                all_violations.extend(violations)
                self.save_violations(violations)

        return all_violations, self.api_calls, self.api_errors

    def get_preprocessing_summary(self) -> Dict:
        avg_rotation = (
            self.preprocessing_stats['total_rotation_angle'] / self.preprocessing_stats['rotated_frames']
            if self.preprocessing_stats['rotated_frames'] > 0
            else 0
        )
        return {
            'total_frames_processed': self.preprocessing_stats['total_frames'],
            'rotated_frames': self.preprocessing_stats['rotated_frames'],
            'rotation_rate': (
                self.preprocessing_stats['rotated_frames'] / self.preprocessing_stats['total_frames']
                if self.preprocessing_stats['total_frames'] > 0
                else 0
            ),
            'avg_rotation_angle': avg_rotation,
            'total_preprocessing_time': self.preprocessing_stats['preprocessing_time'],
            'avg_preprocessing_time': (
                self.preprocessing_stats['preprocessing_time'] / self.preprocessing_stats['total_frames']
                if self.preprocessing_stats['total_frames'] > 0
                else 0
            )
        }

    def extract_subtitle_text(self, video_path: str) -> List[Dict]:
        subtitle_file = os.path.splitext(video_path)[0] + '.srt'
        if not os.path.exists(subtitle_file):
            return []

        results = []
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            pattern = r'(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)\n\s*\n'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                start_time = self._srt_time_to_seconds(match[1])
                end_time = self._srt_time_to_seconds(match[2])
                text = match[3].strip()
                
                if text:
                    results.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': text
                    })
        except Exception as e:
            print(f"Error reading subtitle file: {e}")

        return results

    def _srt_time_to_seconds(self, srt_time: str) -> float:
        try:
            hours, minutes, seconds_ms = srt_time.split(':')
            seconds, ms = seconds_ms.split(',')
            return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(ms) / 1000
        except:
            return 0.0

    def analyze_subtitles(self, subtitles: List[Dict]) -> Tuple[List[Dict], int, int]:
        all_violations = []
        
        for sub in subtitles:
            violations = self.analyze_text(
                text=sub['text'],
                timestamp=sub['start_time'],
                image_path=None,
                frame_id=None
            )
            all_violations.extend(violations)
            self.save_violations(violations)

        return all_violations, self.api_calls, self.api_errors
