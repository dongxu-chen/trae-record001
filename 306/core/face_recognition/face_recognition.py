import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from typing import List, Tuple, Optional, Dict, Any
import os
from PIL import Image
import base64
import io
import time
from collections import deque

from config import config


class BasicBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, stride, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, 1, 1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        if stride != 1 or in_channels != out_channels:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.downsample = None
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return F.relu(out)


class FaceNet(nn.Module):
    def __init__(self, embedding_size: int = 128):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, 7, 2, 3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(3, 2, 1)
        
        self.layer1 = self._make_layer(64, 64, 2, stride=1)
        self.layer2 = self._make_layer(64, 128, 2, stride=2)
        self.layer3 = self._make_layer(128, 256, 2, stride=2)
        self.layer4 = self._make_layer(256, 512, 2, stride=2)
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512, embedding_size)
    
    def _make_layer(self, in_channels: int, out_channels: int, blocks: int, stride: int) -> nn.Sequential:
        layers = []
        layers.append(BasicBlock(in_channels, out_channels, stride))
        for _ in range(1, blocks):
            layers.append(BasicBlock(out_channels, out_channels))
        return nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return F.normalize(x, p=2, dim=1)


class LivenessDetector:
    def __init__(self):
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml'
        )
        
        self._blink_history: deque = deque(maxlen=30)
        self._head_position_history: deque = deque(maxlen=20)
        self._last_blink_time: Optional[float] = None
        self._blink_count = 0
        self._session_start_time = time.time()
        
        self.liveness_checks = {
            'blink_detected': False,
            'head_movement_detected': False,
            'texture_check_passed': False,
            'not_photo': False
        }
        
        self.liveness_score = 0.0
        self.is_live = False
    
    def reset(self) -> None:
        self._blink_history.clear()
        self._head_position_history.clear()
        self._last_blink_time = None
        self._blink_count = 0
        self._session_start_time = time.time()
        self.liveness_checks = {
            'blink_detected': False,
            'head_movement_detected': False,
            'texture_check_passed': False,
            'not_photo': False
        }
        self.liveness_score = 0.0
        self.is_live = False
    
    def detect_eyes(self, face_img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray, 1.1, 4)
        return [(x, y, w, h) for (x, y, w, h) in eyes]
    
    def detect_blink(self, face_img: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Tuple[bool, float]:
        x, y, w, h = face_bbox
        face_region = face_img[y:y+h, x:x+w]
        
        if face_region.size == 0:
            return False, 0.0
        
        eyes = self.detect_eyes(face_region)
        eye_count = len(eyes)
        
        self._blink_history.append(eye_count)
        
        if len(self._blink_history) >= 5:
            recent = list(self._blink_history)[-5:]
            if 0 in recent and (recent.count(2) >= 1 or recent.count(1) >= 1):
                self._blink_count += 1
                self._last_blink_time = time.time()
                self.liveness_checks['blink_detected'] = True
                return True, 1.0
        
        blink_confidence = min(1.0, self._blink_count / 3.0)
        return False, blink_confidence
    
    def track_head_movement(self, face_bbox: Tuple[int, int, int, int]) -> Tuple[bool, float]:
        x, y, w, h = face_bbox
        center_x = x + w / 2
        center_y = y + h / 2
        
        self._head_position_history.append((center_x, center_y))
        
        if len(self._head_position_history) >= 10:
            positions = np.array(self._head_position_history)
            movement = np.std(positions, axis=0)
            total_movement = np.sum(movement)
            
            if total_movement > 5.0:
                self.liveness_checks['head_movement_detected'] = True
                return True, min(1.0, total_movement / 30.0)
        
        movement_score = 0.0
        if len(self._head_position_history) >= 5:
            positions = np.array(self._head_position_history)
            movement = np.std(positions, axis=0)
            movement_score = min(1.0, np.sum(movement) / 20.0)
        
        return False, movement_score
    
    def analyze_texture(self, face_img: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Tuple[bool, float]:
        x, y, w, h = face_bbox
        face_region = face_img[y:y+h, x:x+w]
        
        if face_region.size == 0:
            return False, 0.0
        
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = 20 * np.log(np.abs(fft_shift) + 1)
        high_freq_ratio = np.mean(magnitude > np.median(magnitude) * 1.5)
        
        texture_score = min(1.0, (laplacian_var / 100.0) * 0.5 + high_freq_ratio * 0.5)
        
        if laplacian_var > 50 and high_freq_ratio > 0.3:
            self.liveness_checks['texture_check_passed'] = True
            return True, texture_score
        
        return False, texture_score
    
    def check_not_photo(self, face_img: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Tuple[bool, float]:
        x, y, w, h = face_bbox
        face_region = face_img[y:y+h, x:x+w]
        
        if face_region.size == 0:
            return False, 0.0
        
        hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
        saturation_var = np.var(hsv[:, :, 1])
        hue_var = np.var(hsv[:, :, 0])
        
        edges = cv2.Canny(face_region, 50, 150)
        edge_density = np.mean(edges > 0)
        
        color_variance = np.var(face_region.reshape(-1, 3), axis=0)
        color_diversity = np.mean(color_variance) / 1000.0
        
        photo_score = min(1.0, (saturation_var / 500.0) * 0.4 + edge_density * 0.3 + min(1.0, color_diversity) * 0.3)
        
        if saturation_var > 100 and edge_density > 0.05:
            self.liveness_checks['not_photo'] = True
            return True, photo_score
        
        return False, photo_score
    
    def check_liveness(self, frame: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Dict[str, Any]:
        blink_detected, blink_score = self.detect_blink(frame, face_bbox)
        head_moving, head_score = self.track_head_movement(face_bbox)
        texture_ok, texture_score = self.analyze_texture(frame, face_bbox)
        not_photo, photo_score = self.check_not_photo(frame, face_bbox)
        
        elapsed_time = time.time() - self._session_start_time
        time_factor = min(1.0, elapsed_time / 10.0)
        
        weights = {
            'blink': 0.25,
            'head': 0.20,
            'texture': 0.30,
            'photo': 0.25
        }
        
        self.liveness_score = (
            weights['blink'] * blink_score +
            weights['head'] * head_score +
            weights['texture'] * texture_score +
            weights['photo'] * photo_score
        ) * time_factor
        
        self.is_live = (
            self.liveness_checks['blink_detected'] and
            self.liveness_checks['texture_check_passed'] and
            self.liveness_checks['not_photo'] and
            self.liveness_score >= 0.5
        ) or (self.liveness_score >= 0.7)
        
        return {
            'is_live': self.is_live,
            'liveness_score': self.liveness_score,
            'checks': self.liveness_checks.copy(),
            'individual_scores': {
                'blink_score': blink_score,
                'head_movement_score': head_score,
                'texture_score': texture_score,
                'photo_score': photo_score
            },
            'blink_count': self._blink_count,
            'elapsed_time': elapsed_time
        }
    
    def draw_liveness_indicator(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], 
                                  liveness_result: Dict[str, Any]) -> np.ndarray:
        x, y, w, h = bbox
        is_live = liveness_result.get('is_live', False)
        score = liveness_result.get('liveness_score', 0.0)
        
        color = (0, 255, 0) if is_live else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        
        status_text = "活体" if is_live else "非活体"
        cv2.putText(frame, f"{status_text} ({score:.2f})", 
                   (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        checks = liveness_result.get('checks', {})
        y_offset = y + h + 20
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            color_check = (0, 255, 0) if passed else (0, 0, 255)
            cv2.putText(frame, f"{check_name}: {status}", 
                       (x, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_check, 1)
            y_offset += 18
        
        return frame


class SingleFaceLock:
    def __init__(self, max_allowed_faces: int = 1, grace_period: float = 5.0):
        self.max_allowed_faces = max_allowed_faces
        self.grace_period = grace_period
        
        self._is_locked = False
        self._lock_start_time: Optional[float] = None
        self._locked_student_id: Optional[str] = None
        self._lock_reason: Optional[str] = None
        
        self._multiple_face_start_time: Optional[float] = None
        self._face_count_history: deque = deque(maxlen=10)
    
    def check_single_face(self, face_count: int, student_id: str) -> Dict[str, Any]:
        self._face_count_history.append(face_count)
        
        avg_faces = np.mean(self._face_count_history) if self._face_count_history else face_count
        
        if face_count > self.max_allowed_faces and avg_faces > self.max_allowed_faces:
            if self._multiple_face_start_time is None:
                self._multiple_face_start_time = time.time()
            
            elapsed = time.time() - self._multiple_face_start_time
            
            if elapsed >= self.grace_period:
                if not self._is_locked:
                    self._is_locked = True
                    self._lock_start_time = time.time()
                    self._locked_student_id = student_id
                    self._lock_reason = f"检测到 {face_count} 张人脸，超过允许的 {self.max_allowed_faces} 张"
                
                return {
                    'violation_detected': True,
                    'should_lock': True,
                    'is_locked': self._is_locked,
                    'face_count': face_count,
                    'avg_face_count': avg_faces,
                    'elapsed_violation': elapsed,
                    'grace_period': self.grace_period,
                    'reason': self._lock_reason
                }
            else:
                return {
                    'violation_detected': True,
                    'should_lock': False,
                    'is_locked': False,
                    'face_count': face_count,
                    'avg_face_count': avg_faces,
                    'elapsed_violation': elapsed,
                    'grace_period': self.grace_period,
                    'reason': f"检测到 {face_count} 张人脸，宽限期 {self.grace_period - elapsed:.1f} 秒"
                }
        else:
            self._multiple_face_start_time = None
            
            if self._is_locked and self._locked_student_id == student_id:
                pass
            
            return {
                'violation_detected': False,
                'should_lock': False,
                'is_locked': self._is_locked,
                'face_count': face_count,
                'avg_face_count': avg_faces,
                'elapsed_violation': 0,
                'grace_period': self.grace_period,
                'reason': '正常'
            }
    
    def is_student_locked(self, student_id: str) -> bool:
        return self._is_locked and self._locked_student_id == student_id
    
    def unlock(self, student_id: Optional[str] = None) -> bool:
        if student_id is None or self._locked_student_id == student_id:
            self._is_locked = False
            self._lock_start_time = None
            self._locked_student_id = None
            self._lock_reason = None
            self._multiple_face_start_time = None
            self._face_count_history.clear()
            return True
        return False
    
    def get_lock_status(self) -> Dict[str, Any]:
        return {
            'is_locked': self._is_locked,
            'locked_student_id': self._locked_student_id,
            'lock_start_time': self._lock_start_time,
            'lock_reason': self._lock_reason,
            'lock_duration': time.time() - self._lock_start_time if self._lock_start_time else 0,
            'max_allowed_faces': self.max_allowed_faces,
            'grace_period': self.grace_period
        }


class FaceRecognition:
    def __init__(self, model_path: Optional[str] = None, use_cuda: bool = False):
        self.device = torch.device('cuda' if use_cuda and torch.cuda.is_available() else 'cpu')
        
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        self.model = FaceNet(embedding_size=128).to(self.device)
        self.model.eval()
        
        if model_path and os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            print(f"Loaded face recognition model from {model_path}")
        else:
            print("Warning: No pretrained model loaded. Using initialized weights for demo.")
        
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        
        self.known_faces: Dict[str, torch.Tensor] = {}
        self.threshold = config.FACE_RECOGNITION_THRESHOLD
        
        self.liveness_detector = LivenessDetector()
        self.single_face_lock = SingleFaceLock(
            max_allowed_faces=1,
            grace_period=config.MULTIPLE_FACE_GRACE_PERIOD
        )
        
        self._student_liveness: Dict[str, LivenessDetector] = {}
        self._student_lock_status: Dict[str, SingleFaceLock] = {}
    
    def _get_student_liveness(self, student_id: str) -> LivenessDetector:
        if student_id not in self._student_liveness:
            self._student_liveness[student_id] = LivenessDetector()
        return self._student_liveness[student_id]
    
    def _get_student_lock(self, student_id: str) -> SingleFaceLock:
        if student_id not in self._student_lock_status:
            self._student_lock_status[student_id] = SingleFaceLock(
                max_allowed_faces=1,
                grace_period=config.MULTIPLE_FACE_GRACE_PERIOD
            )
        return self._student_lock_status[student_id]
    
    def _load_image(self, image_data: np.ndarray) -> Image.Image:
        if len(image_data.shape) == 2:
            image_data = cv2.cvtColor(image_data, cv2.COLOR_GRAY2RGB)
        else:
            image_data = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
        return Image.fromarray(image_data)
    
    def detect_face(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        return [(x, y, w, h) for (x, y, w, h) in faces]
    
    def extract_face(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        x, y, w, h = bbox
        face_img = frame[y:y+h, x:x+w]
        if face_img.size == 0:
            return None
        return face_img
    
    def get_embedding(self, face_image: np.ndarray) -> Optional[torch.Tensor]:
        try:
            pil_image = self._load_image(face_image)
            tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                embedding = self.model(tensor)
            return embedding.cpu()
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def register_face(self, user_id: str, face_image: np.ndarray, 
                      require_liveness: bool = True) -> Dict[str, Any]:
        faces = self.detect_face(face_image)
        if not faces:
            return {'success': False, 'reason': '未检测到人脸'}
        
        if len(faces) > 1:
            return {'success': False, 'reason': '检测到多张人脸，请确保只有您一人'}
        
        face_img = self.extract_face(face_image, faces[0])
        if face_img is None:
            return {'success': False, 'reason': '人脸提取失败'}
        
        if require_liveness:
            liveness_result = self.liveness_detector.check_liveness(face_image, faces[0])
            if not liveness_result['is_live']:
                return {
                    'success': False, 
                    'reason': '活体检测未通过',
                    'liveness': liveness_result
                }
        
        embedding = self.get_embedding(face_img)
        if embedding is None:
            return {'success': False, 'reason': '特征提取失败'}
        
        self.known_faces[user_id] = embedding
        
        if user_id in self._student_liveness:
            del self._student_liveness[user_id]
        
        return {'success': True, 'face_count': len(faces)}
    
    def verify_face(self, user_id: str, face_image: np.ndarray,
                    check_liveness: bool = True,
                    check_single: bool = True) -> Tuple[bool, float, Dict[str, Any]]:
        if user_id not in self.known_faces:
            return False, 0.0, {'error': '用户未注册人脸'}
        
        faces = self.detect_face(face_image)
        face_count = len(faces)
        
        lock_info = {}
        if check_single and config.ENABLE_SINGLE_FACE_LOCK:
            lock = self._get_student_lock(user_id)
            lock_result = lock.check_single_face(face_count, user_id)
            lock_info = lock_result
            
            if lock_result.get('should_lock', False):
                return False, 0.0, {
                    'error': '考试已暂停',
                    'lock_info': lock_info,
                    'face_count': face_count
                }
        
        if not faces:
            return False, 0.0, {'face_count': 0, 'lock_info': lock_info}
        
        face_img = self.extract_face(face_image, faces[0])
        if face_img is None:
            return False, 0.0, {'face_count': face_count, 'lock_info': lock_info}
        
        liveness_result = {}
        if check_liveness and config.ENABLE_LIVENESS_DETECTION:
            liveness = self._get_student_liveness(user_id)
            liveness_result = liveness.check_liveness(face_image, faces[0])
            
            if not liveness_result.get('is_live', False):
                return False, 0.0, {
                    'error': '活体检测未通过',
                    'liveness': liveness_result,
                    'face_count': face_count,
                    'lock_info': lock_info
                }
        
        embedding = self.get_embedding(face_img)
        if embedding is None:
            return False, 0.0, {'face_count': face_count, 'lock_info': lock_info}
        
        known_embedding = self.known_faces[user_id]
        similarity = F.cosine_similarity(embedding, known_embedding).item()
        
        is_match = similarity >= self.threshold
        
        extra_info = {
            'face_count': face_count,
            'lock_info': lock_info,
            'liveness': liveness_result
        }
        
        return is_match, similarity, extra_info
    
    def recognize_face(self, face_image: np.ndarray) -> Tuple[Optional[str], float, Dict[str, Any]]:
        faces = self.detect_face(face_image)
        if not faces:
            return None, 0.0, {'face_count': 0}
        
        face_count = len(faces)
        
        face_img = self.extract_face(face_image, faces[0])
        if face_img is None:
            return None, 0.0, {'face_count': face_count}
        
        embedding = self.get_embedding(face_img)
        if embedding is None:
            return None, 0.0, {'face_count': face_count}
        
        best_match = None
        best_similarity = 0.0
        
        for user_id, known_embedding in self.known_faces.items():
            similarity = F.cosine_similarity(embedding, known_embedding).item()
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = user_id
        
        if best_similarity >= self.threshold:
            return best_match, best_similarity, {'face_count': face_count}
        return None, best_similarity, {'face_count': face_count}
    
    def verify_from_base64(self, user_id: str, base64_image: str) -> Tuple[bool, float, Dict[str, Any]]:
        try:
            image_data = base64.b64decode(base64_image.split(',')[-1])
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return self.verify_face(user_id, frame)
        except Exception as e:
            print(f"Error verifying from base64: {e}")
            return False, 0.0, {'error': str(e)}
    
    def detect_multiple_faces(self, frame: np.ndarray) -> Tuple[int, List[Tuple[int, int, int, int]]]:
        faces = self.detect_face(frame)
        return len(faces), faces
    
    def check_monitoring(self, student_id: str, frame: np.ndarray) -> Dict[str, Any]:
        face_count, faces = self.detect_multiple_faces(frame)
        
        result = {
            'timestamp': time.time(),
            'face_count': face_count,
            'faces': faces,
            'is_locked': False,
            'lock_info': None,
            'liveness': None,
            'recognition': None,
            'warnings': []
        }
        
        if config.ENABLE_SINGLE_FACE_LOCK:
            lock = self._get_student_lock(student_id)
            lock_result = lock.check_single_face(face_count, student_id)
            result['lock_info'] = lock_result
            result['is_locked'] = lock_result.get('should_lock', False)
            
            if lock_result.get('violation_detected', False):
                result['warnings'].append(lock_result.get('reason', ''))
        
        if face_count == 1 and student_id in self.known_faces:
            if config.ENABLE_LIVENESS_DETECTION:
                liveness = self._get_student_liveness(student_id)
                liveness_result = liveness.check_liveness(frame, faces[0])
                result['liveness'] = liveness_result
                
                if not liveness_result.get('is_live', False):
                    result['warnings'].append('活体检测未通过')
            
            is_match, similarity, extra = self.verify_face(
                student_id, frame, check_liveness=False, check_single=False
            )
            result['recognition'] = {
                'is_match': is_match,
                'similarity': similarity
            }
            
            if not is_match:
                result['warnings'].append('人脸不匹配')
        
        elif face_count == 0:
            result['warnings'].append('未检测到人脸')
        
        elif face_count > 1:
            result['warnings'].append(f'检测到{face_count}张人脸')
        
        return result
    
    def is_face_present(self, frame: np.ndarray) -> bool:
        faces = self.detect_face(frame)
        return len(faces) > 0
    
    def draw_faces(self, frame: np.ndarray, faces: List[Tuple[int, int, int, int]]) -> np.ndarray:
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        return frame
    
    def draw_monitoring_overlay(self, frame: np.ndarray, 
                                  monitoring_result: Dict[str, Any]) -> np.ndarray:
        faces = monitoring_result.get('faces', [])
        face_count = monitoring_result.get('face_count', 0)
        
        if face_count == 1:
            bbox = faces[0]
            x, y, w, h = bbox
            
            if monitoring_result.get('is_locked', False):
                color = (0, 0, 255)
                status_text = "已锁定"
            else:
                recognition = monitoring_result.get('recognition', {})
                liveness = monitoring_result.get('liveness', {})
                
                is_match = recognition.get('is_match', False)
                is_live = liveness.get('is_live', False)
                
                if is_match and is_live:
                    color = (0, 255, 0)
                    status_text = "正常"
                elif not is_match:
                    color = (0, 0, 255)
                    status_text = "身份不匹配"
                else:
                    color = (0, 165, 255)
                    status_text = "活体检测中"
                
                if liveness:
                    liveness_score = liveness.get('liveness_score', 0.0)
                    status_text += f" (活体: {liveness_score:.2f})"
                
                if recognition:
                    similarity = recognition.get('similarity', 0.0)
                    status_text += f" (相似度: {similarity:.2f})"
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, status_text, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        warnings = monitoring_result.get('warnings', [])
        for i, warning in enumerate(warnings):
            cv2.putText(frame, f"⚠️ {warning}", (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        if monitoring_result.get('is_locked', False):
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            
            lock_info = monitoring_result.get('lock_info', {})
            reason = lock_info.get('reason', '考试已暂停')
            
            cv2.putText(frame, "⚠️ 考试已暂停 ⚠️", 
                       (frame.shape[1] // 2 - 200, frame.shape[0] // 2 - 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.putText(frame, reason, 
                       (frame.shape[1] // 2 - 300, frame.shape[0] // 2 + 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(frame, "请联系监考老师", 
                       (frame.shape[1] // 2 - 150, frame.shape[0] // 2 + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        return frame
    
    def unlock_student(self, student_id: str) -> bool:
        if student_id in self._student_lock_status:
            return self._student_lock_status[student_id].unlock(student_id)
        return False
    
    def reset_student_liveness(self, student_id: str) -> None:
        if student_id in self._student_liveness:
            self._student_liveness[student_id].reset()
    
    def get_student_lock_status(self, student_id: str) -> Dict[str, Any]:
        if student_id in self._student_lock_status:
            return self._student_lock_status[student_id].get_lock_status()
        return {'is_locked': False}
    
    def save_model(self, path: str) -> None:
        torch.save(self.model.state_dict(), path)
    
    def load_model(self, path: str) -> None:
        if os.path.exists(path):
            self.model.load_state_dict(torch.load(path, map_location=self.device))
            self.model.eval()
