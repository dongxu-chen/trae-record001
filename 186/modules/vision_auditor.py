import os
import base64
import requests
import time
from typing import List, Dict, Tuple, Optional
from config.config import VISION_API_KEY, VISION_API_ENDPOINT, MIN_CONFIDENCE, VIOLATION_TYPES, REQUEST_TIMEOUT
from models import ViolationModel


class VisionAuditor:
    def __init__(self, video_id: int):
        self.video_id = video_id
        self.api_calls = 0
        self.api_errors = 0
        self.violations: List[Dict] = []

    def _encode_image(self, image_path: str) -> str:
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to encode image: {str(e)}")

    def _build_request_payload(self, image_content: str) -> Dict:
        return {
            "requests": [
                {
                    "image": {
                        "content": image_content
                    },
                    "features": [
                        {"type": "SAFE_SEARCH_DETECTION", "maxResults": 1},
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                        {"type": "TEXT_DETECTION", "maxResults": 5}
                    ]
                }
            ]
        }

    def analyze_image(self, image_path: str, timestamp: float, frame_id: int = None) -> List[Dict]:
        if not VISION_API_KEY:
            return self._mock_analyze_image(image_path, timestamp, frame_id)

        violations = []
        try:
            image_content = self._encode_image(image_path)
            payload = self._build_request_payload(image_content)
            
            params = {"key": VISION_API_KEY}
            self.api_calls += 1
            
            response = requests.post(
                VISION_API_ENDPOINT,
                params=params,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                violations = self._parse_vision_response(result, timestamp, frame_id, image_path)
            else:
                self.api_errors += 1
                print(f"Vision API error: {response.status_code} - {response.text}")
                
        except requests.Timeout:
            self.api_errors += 1
            print("Vision API request timed out")
        except Exception as e:
            self.api_errors += 1
            print(f"Vision API exception: {str(e)}")

        return violations

    def _parse_vision_response(self, response: Dict, timestamp: float, frame_id: int, image_path: str) -> List[Dict]:
        violations = []
        
        try:
            if not response.get('responses'):
                return violations

            result = response['responses'][0]
            
            safe_search = result.get('safeSearchAnnotation', {})
            
            violence_score = self._get_likelihood_score(safe_search.get('violence', 'VERY_UNLIKELY'))
            if violence_score >= MIN_CONFIDENCE:
                violations.append(self._create_violation(
                    'violence', timestamp, violence_score, 
                    f"暴力内容检测: {safe_search.get('violence')}",
                    frame_id, image_path
                ))
            
            adult_score = self._get_likelihood_score(safe_search.get('adult', 'VERY_UNLIKELY'))
            if adult_score >= MIN_CONFIDENCE:
                violations.append(self._create_violation(
                    'porn', timestamp, adult_score,
                    f"色情内容检测: {safe_search.get('adult')}",
                    frame_id, image_path
                ))
            
            political_score = self._detect_political_content(result)
            if political_score >= MIN_CONFIDENCE:
                violations.append(self._create_violation(
                    'politics', timestamp, political_score,
                    "涉政内容检测",
                    frame_id, image_path
                ))

        except Exception as e:
            print(f"Error parsing vision response: {str(e)}")

        return violations

    def _get_likelihood_score(self, likelihood: str) -> float:
        scores = {
            'VERY_UNLIKELY': 0.0,
            'UNLIKELY': 0.25,
            'POSSIBLE': 0.5,
            'LIKELY': 0.75,
            'VERY_LIKELY': 1.0
        }
        return scores.get(likelihood, 0.0)

    def _detect_political_content(self, result: Dict) -> float:
        labels = result.get('labelAnnotations', [])
        political_keywords = ['flag', 'government', 'protest', 'demonstration', 'military', 'weapon', 'gun']
        
        max_score = 0.0
        for label in labels:
            desc = label.get('description', '').lower()
            score = label.get('score', 0.0)
            if any(keyword in desc for keyword in political_keywords):
                max_score = max(max_score, score)
        
        texts = result.get('textAnnotations', [])
        if texts:
            text_content = texts[0].get('description', '').lower()
            political_text_keywords = ['政府', '抗议', '游行', '军队', '武器', '革命', '政权']
            if any(keyword in text_content for keyword in political_text_keywords):
                max_score = max(max_score, 0.8)

        return max_score

    def _create_violation(self, violation_type: str, timestamp: float, confidence: float, 
                         description: str, frame_id: int, image_path: str) -> Dict:
        return {
            'video_id': self.video_id,
            'frame_id': frame_id,
            'violation_type': violation_type,
            'violation_type_name': VIOLATION_TYPES.get(violation_type, violation_type),
            'timestamp': timestamp,
            'confidence': confidence,
            'description': description,
            'image_path': image_path
        }

    def _mock_analyze_image(self, image_path: str, timestamp: float, frame_id: int) -> List[Dict]:
        violations = []
        import random
        random.seed(os.path.getsize(image_path) if os.path.exists(image_path) else 0)
        
        if random.random() < 0.1:
            v_type = random.choice(['violence', 'porn', 'politics'])
            confidence = random.uniform(MIN_CONFIDENCE, 0.95)
            violations.append(self._create_violation(
                v_type, timestamp, confidence,
                f"Mock检测: {VIOLATION_TYPES.get(v_type)}",
                frame_id, image_path
            ))
        
        time.sleep(0.1)
        return violations

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
                    image_path=v.get('image_path')
                )
                self.violations.append(v)
            except Exception as e:
                print(f"Warning: Failed to save violation: {e}")

    def analyze_frames(self, frames: List[Dict]) -> Tuple[List[Dict], int, int]:
        all_violations = []
        
        for frame in frames:
            violations = self.analyze_image(
                image_path=frame['image_path'],
                timestamp=frame['timestamp'],
                frame_id=frame.get('frame_number')
            )
            all_violations.extend(violations)
            self.save_violations(violations)

        return all_violations, self.api_calls, self.api_errors
