import numpy as np
from typing import Dict, Tuple, List
from scipy.spatial.distance import euclidean


class FacialActionUnit:
    def __init__(self, au_id: str, name: str, description: str):
        self.au_id = au_id
        self.name = name
        self.description = description
        self.intensity = 0.0
        self.confidence = 0.0
        
    def update(self, intensity: float, confidence: float = 1.0):
        self.intensity = max(0.0, min(1.0, intensity))
        self.confidence = max(0.0, min(1.0, confidence))
        
    def get_value(self) -> float:
        return self.intensity * self.confidence


class ActionUnitAnalyzer:
    def __init__(self):
        self.smoothing_factor = 0.4
        self.prev_au_values = {}
        
        self.landmark_indices = {
            'inner_brow_l': 70,
            'inner_brow_r': 300,
            'outer_brow_l': 105,
            'outer_brow_r': 334,
            'mid_brow_l': 63,
            'mid_brow_r': 296,
            
            'eye_top_l': 386,
            'eye_bottom_l': 374,
            'eye_inner_l': 362,
            'eye_outer_l': 263,
            
            'eye_top_r': 159,
            'eye_bottom_r': 145,
            'eye_inner_r': 33,
            'eye_outer_r': 133,
            
            'cheek_raise_l': 117,
            'cheek_raise_r': 346,
            
            'nose_root_l': 192,
            'nose_root_r': 412,
            'nose_tip': 1,
            
            'mouth_upper_top': 13,
            'mouth_upper_bottom': 16,
            'mouth_lower_top': 17,
            'mouth_lower_bottom': 14,
            'mouth_left': 61,
            'mouth_right': 291,
            
            'lip_corner_l': 61,
            'lip_corner_r': 291,
            'lip_upper_l': 37,
            'lip_upper_r': 267,
            'lip_lower_l': 84,
            'lip_lower_r': 314,
            
            'chin': 152,
            'jaw_left': 58,
            'jaw_right': 288,
            
            'face_left': 234,
            'face_right': 454,
            'face_top': 10,
            'face_bottom': 152,
        }
        
        self.action_units = self._init_action_units()
        
        self.baseline_distances = {}
        self.baseline_set = False
        self.baseline_frame_count = 0
        self.baseline_max_frames = 30
        
    def _init_action_units(self) -> Dict[str, FacialActionUnit]:
        aus = {
            'AU1': FacialActionUnit('AU1', 'Inner Brow Raiser', '眉毛内侧上扬'),
            'AU2': FacialActionUnit('AU2', 'Outer Brow Raiser', '眉毛外侧上扬'),
            'AU4': FacialActionUnit('AU4', 'Brow Lowerer', '眉毛下压'),
            'AU5': FacialActionUnit('AU5', 'Upper Lid Raiser', '上眼睑抬起'),
            'AU6': FacialActionUnit('AU6', 'Cheek Raiser', '脸颊抬起'),
            'AU7': FacialActionUnit('AU7', 'Lid Tightener', '眼睑收紧'),
            'AU9': FacialActionUnit('AU9', 'Nose Wrinkler', '皱鼻'),
            'AU10': FacialActionUnit('AU10', 'Upper Lip Raiser', '上唇抬起'),
            'AU11': FacialActionUnit('AU11', 'Nasolabial Deepener', '鼻唇沟加深'),
            'AU12': FacialActionUnit('AU12', 'Lip Corner Puller', '嘴角拉伸'),
            'AU13': FacialActionUnit('AU13', 'Sharp Lip Puller', '锐唇拉起'),
            'AU14': FacialActionUnit('AU14', 'Dimpler', '酒窝'),
            'AU15': FacialActionUnit('AU15', 'Lip Corner Depressor', '嘴角下压'),
            'AU16': FacialActionUnit('AU16', 'Lower Lip Depressor', '下唇下压'),
            'AU17': FacialActionUnit('AU17', 'Chin Raiser', '下巴抬起'),
            'AU18': FacialActionUnit('AU18', 'Lip Puckerer', '噘嘴'),
            'AU20': FacialActionUnit('AU20', 'Lip Stretcher', '嘴唇拉伸'),
            'AU22': FacialActionUnit('AU22', 'Lip Funneler', '嘴唇呈漏斗状'),
            'AU23': FacialActionUnit('AU23', 'Lip Tightener', '嘴唇收紧'),
            'AU24': FacialActionUnit('AU24', 'Lip Pressor', '嘴唇按压'),
            'AU25': FacialActionUnit('AU25', 'Lips Part', '嘴唇分开'),
            'AU26': FacialActionUnit('AU26', 'Jaw Drop', '下颚下降'),
            'AU27': FacialActionUnit('AU27', 'Mouth Stretch', '嘴巴张大'),
            'AU28': FacialActionUnit('AU28', 'Lip Suck', '嘴唇内吸'),
            'AU43': FacialActionUnit('AU43', 'Eyes Closed', '闭眼'),
            'AU45': FacialActionUnit('AU45', 'Blink', '眨眼'),
            'AU61': FacialActionUnit('AU61', 'Eyes Turn Left', '眼睛左转'),
            'AU62': FacialActionUnit('AU62', 'Eyes Turn Right', '眼睛右转'),
            'AU63': FacialActionUnit('AU63', 'Eyes Up', '眼睛上看'),
            'AU64': FacialActionUnit('AU64', 'Eyes Down', '眼睛下看'),
        }
        return aus

    def _get_point(self, landmarks: list, idx: int, image_shape: Tuple[int, int]) -> np.ndarray:
        h, w = image_shape[:2]
        lm = landmarks[idx]
        return np.array([lm.x * w, lm.y * h, lm.z])

    def _get_face_width(self, landmarks: list, image_shape: Tuple[int, int]) -> float:
        left = self._get_point(landmarks, self.landmark_indices['face_left'], image_shape)
        right = self._get_point(landmarks, self.landmark_indices['face_right'], image_shape)
        return euclidean(left[:2], right[:2])

    def _get_face_height(self, landmarks: list, image_shape: Tuple[int, int]) -> float:
        top = self._get_point(landmarks, self.landmark_indices['face_top'], image_shape)
        bottom = self._get_point(landmarks, self.landmark_indices['face_bottom'], image_shape)
        return euclidean(top[:2], bottom[:2])

    def _collect_baseline(self, landmarks: list, image_shape: Tuple[int, int]):
        if self.baseline_frame_count >= self.baseline_max_frames:
            self.baseline_set = True
            return
        
        face_width = self._get_face_width(landmarks, image_shape)
        face_height = self._get_face_height(landmarks, image_shape)
        
        current_distances = {
            'brow_height_l': self._get_brow_height(landmarks, image_shape, 'left'),
            'brow_height_r': self._get_brow_height(landmarks, image_shape, 'right'),
            'eye_open_l': self._get_eye_open(landmarks, image_shape, 'left'),
            'eye_open_r': self._get_eye_open(landmarks, image_shape, 'right'),
            'mouth_open': self._get_mouth_open(landmarks, image_shape),
            'smile_amount': self._get_smile_amount(landmarks, image_shape),
            'cheek_height_l': self._get_cheek_height(landmarks, image_shape, 'left'),
            'cheek_height_r': self._get_cheek_height(landmarks, image_shape, 'right'),
            'face_width': face_width,
            'face_height': face_height,
        }
        
        if self.baseline_frame_count == 0:
            self.baseline_distances = current_distances
        else:
            alpha = 1.0 / (self.baseline_frame_count + 1)
            for key in current_distances:
                self.baseline_distances[key] = (
                    (1 - alpha) * self.baseline_distances[key] + 
                    alpha * current_distances[key]
                )
        
        self.baseline_frame_count += 1

    def _get_brow_height(self, landmarks: list, image_shape: Tuple[int, int], side: str) -> float:
        if side == 'left':
            brow = self._get_point(landmarks, self.landmark_indices['inner_brow_l'], image_shape)
            eye = self._get_point(landmarks, self.landmark_indices['eye_top_l'], image_shape)
        else:
            brow = self._get_point(landmarks, self.landmark_indices['inner_brow_r'], image_shape)
            eye = self._get_point(landmarks, self.landmark_indices['eye_top_r'], image_shape)
        
        face_width = self._get_face_width(landmarks, image_shape)
        distance = euclidean(brow[:2], eye[:2])
        
        return distance / face_width if face_width > 0 else 0

    def _get_eye_open(self, landmarks: list, image_shape: Tuple[int, int], side: str) -> float:
        if side == 'left':
            top = self._get_point(landmarks, self.landmark_indices['eye_top_l'], image_shape)
            bottom = self._get_point(landmarks, self.landmark_indices['eye_bottom_l'], image_shape)
            inner = self._get_point(landmarks, self.landmark_indices['eye_inner_l'], image_shape)
            outer = self._get_point(landmarks, self.landmark_indices['eye_outer_l'], image_shape)
        else:
            top = self._get_point(landmarks, self.landmark_indices['eye_top_r'], image_shape)
            bottom = self._get_point(landmarks, self.landmark_indices['eye_bottom_r'], image_shape)
            inner = self._get_point(landmarks, self.landmark_indices['eye_inner_r'], image_shape)
            outer = self._get_point(landmarks, self.landmark_indices['eye_outer_r'], image_shape)
        
        eye_height = euclidean(top[:2], bottom[:2])
        eye_width = euclidean(inner[:2], outer[:2])
        
        return eye_height / eye_width if eye_width > 0 else 0

    def _get_mouth_open(self, landmarks: list, image_shape: Tuple[int, int]) -> float:
        upper = self._get_point(landmarks, self.landmark_indices['mouth_upper_bottom'], image_shape)
        lower = self._get_point(landmarks, self.landmark_indices['mouth_lower_top'], image_shape)
        left = self._get_point(landmarks, self.landmark_indices['mouth_left'], image_shape)
        right = self._get_point(landmarks, self.landmark_indices['mouth_right'], image_shape)
        
        mouth_open = euclidean(upper[:2], lower[:2])
        mouth_width = euclidean(left[:2], right[:2])
        
        return mouth_open / mouth_width if mouth_width > 0 else 0

    def _get_smile_amount(self, landmarks: list, image_shape: Tuple[int, int]) -> float:
        left_corner = self._get_point(landmarks, self.landmark_indices['lip_corner_l'], image_shape)
        right_corner = self._get_point(landmarks, self.landmark_indices['lip_corner_r'], image_shape)
        mouth_center = self._get_point(landmarks, self.landmark_indices['mouth_upper_top'], image_shape)
        
        avg_y = (left_corner[1] + right_corner[1]) / 2
        face_width = self._get_face_width(landmarks, image_shape)
        
        return (mouth_center[1] - avg_y) / face_width if face_width > 0 else 0

    def _get_cheek_height(self, landmarks: list, image_shape: Tuple[int, int], side: str) -> float:
        if side == 'left':
            cheek = self._get_point(landmarks, self.landmark_indices['cheek_raise_l'], image_shape)
            eye = self._get_point(landmarks, self.landmark_indices['eye_bottom_l'], image_shape)
        else:
            cheek = self._get_point(landmarks, self.landmark_indices['cheek_raise_r'], image_shape)
            eye = self._get_point(landmarks, self.landmark_indices['eye_bottom_r'], image_shape)
        
        face_width = self._get_face_width(landmarks, image_shape)
        distance = euclidean(cheek[:2], eye[:2])
        
        return distance / face_width if face_width > 0 else 0

    def _get_lip_height(self, landmarks: list, image_shape: Tuple[int, int], side: str) -> float:
        if side == 'left':
            upper = self._get_point(landmarks, self.landmark_indices['lip_upper_l'], image_shape)
            lower = self._get_point(landmarks, self.landmark_indices['lip_lower_l'], image_shape)
        else:
            upper = self._get_point(landmarks, self.landmark_indices['lip_upper_r'], image_shape)
            lower = self._get_point(landmarks, self.landmark_indices['lip_lower_r'], image_shape)
        
        face_width = self._get_face_width(landmarks, image_shape)
        distance = euclidean(upper[:2], lower[:2])
        
        return distance / face_width if face_width > 0 else 0

    def _smooth_value(self, au_id: str, value: float) -> float:
        if au_id in self.prev_au_values:
            prev = self.prev_au_values[au_id]
            return (1 - self.smoothing_factor) * prev + self.smoothing_factor * value
        return value

    def analyze(self, landmarks: list, image_shape: Tuple[int, int]) -> Dict[str, float]:
        if not self.baseline_set:
            self._collect_baseline(landmarks, image_shape)
            return {au: 0.0 for au in self.action_units}
        
        face_width = self._get_face_width(landmarks, image_shape)
        
        brow_height_l = self._get_brow_height(landmarks, image_shape, 'left')
        brow_height_r = self._get_brow_height(landmarks, image_shape, 'right')
        eye_open_l = self._get_eye_open(landmarks, image_shape, 'left')
        eye_open_r = self._get_eye_open(landmarks, image_shape, 'right')
        mouth_open = self._get_mouth_open(landmarks, image_shape)
        smile = self._get_smile_amount(landmarks, image_shape)
        cheek_l = self._get_cheek_height(landmarks, image_shape, 'left')
        cheek_r = self._get_cheek_height(landmarks, image_shape, 'right')
        lip_h_l = self._get_lip_height(landmarks, image_shape, 'left')
        lip_h_r = self._get_lip_height(landmarks, image_shape, 'right')
        
        base = self.baseline_distances
        
        brow_change_l = (brow_height_l - base['brow_height_l']) / base['brow_height_l'] if base['brow_height_l'] > 0 else 0
        brow_change_r = (brow_height_r - base['brow_height_r']) / base['brow_height_r'] if base['brow_height_r'] > 0 else 0
        eye_change_l = (eye_open_l - base['eye_open_l']) / base['eye_open_l'] if base['eye_open_l'] > 0 else 0
        eye_change_r = (eye_open_r - base['eye_open_r']) / base['eye_open_r'] if base['eye_open_r'] > 0 else 0
        mouth_change = (mouth_open - base['mouth_open']) / base['mouth_open'] if base['mouth_open'] > 0 else 0
        smile_change = (smile - base['smile_amount']) / base['smile_amount'] if abs(base['smile_amount']) > 0.001 else smile
        cheek_change_l = (cheek_l - base['cheek_height_l']) / base['cheek_height_l'] if base['cheek_height_l'] > 0 else 0
        cheek_change_r = (cheek_r - base['cheek_height_r']) / base['cheek_height_r'] if base['cheek_height_r'] > 0 else 0
        
        au1 = max(0.0, min(1.0, brow_change_l * 2 + 0.5))
        au2 = max(0.0, min(1.0, (brow_change_l + brow_change_r) * 1.5 + 0.5))
        au4 = max(0.0, min(1.0, -brow_change_l * 3))
        
        au5_l = max(0.0, min(1.0, eye_change_l * 2 + 0.5))
        au5_r = max(0.0, min(1.0, eye_change_r * 2 + 0.5))
        au5 = (au5_l + au5_r) / 2
        
        au6_l = max(0.0, min(1.0, cheek_change_l * 3 + 0.3))
        au6_r = max(0.0, min(1.0, cheek_change_r * 3 + 0.3))
        au6 = (au6_l + au6_r) / 2
        
        au7_l = max(0.0, min(1.0, -eye_change_l * 3 + 0.5))
        au7_r = max(0.0, min(1.0, -eye_change_r * 3 + 0.5))
        au7 = (au7_l + au7_r) / 2
        
        au10 = max(0.0, min(1.0, (lip_h_l + lip_h_r) * 5 - 0.5))
        
        au12 = max(0.0, min(1.0, smile_change * 8 + 0.2))
        
        au15 = max(0.0, min(1.0, -smile_change * 6 + 0.2))
        
        au17 = max(0.0, min(1.0, mouth_change * 0.5))
        
        au20 = max(0.0, min(1.0, max(lip_h_l, lip_h_r) * 3))
        
        au25 = max(0.0, min(1.0, mouth_open * 3))
        
        au26 = max(0.0, min(1.0, mouth_open * 2.5))
        
        au27 = max(0.0, min(1.0, mouth_change * 2))
        
        au43_l = max(0.0, min(1.0, 1.0 - eye_open_l * 3))
        au43_r = max(0.0, min(1.0, 1.0 - eye_open_r * 3))
        au43 = max(au43_l, au43_r)
        
        au45 = max(0.0, min(1.0, (au43_l + au43_r) / 2))
        
        au_values = {
            'AU1': au1,
            'AU2': au2,
            'AU4': au4,
            'AU5': au5,
            'AU6': au6,
            'AU7': au7,
            'AU9': max(0.0, au6 * 0.5),
            'AU10': au10,
            'AU11': max(0.0, au6 * 0.7),
            'AU12': au12,
            'AU13': max(0.0, au12 * 0.6),
            'AU14': max(0.0, au12 * 0.4),
            'AU15': au15,
            'AU16': max(0.0, au15 * 0.8),
            'AU17': au17,
            'AU18': max(0.0, 1.0 - au20),
            'AU20': au20,
            'AU22': max(0.0, au25 * 0.6),
            'AU23': max(0.0, 1.0 - au25),
            'AU24': max(0.0, 1.0 - au25),
            'AU25': au25,
            'AU26': au26,
            'AU27': au27,
            'AU28': max(0.0, 1.0 - au25),
            'AU43': au43,
            'AU45': au45,
            'AU61': 0.0,
            'AU62': 0.0,
            'AU63': 0.0,
            'AU64': 0.0,
        }
        
        for au_id, intensity in au_values.items():
            au_values[au_id] = self._smooth_value(au_id, intensity)
            self.prev_au_values[au_id] = au_values[au_id]
            
            if au_id in self.action_units:
                self.action_units[au_id].update(au_values[au_id])
        
        return au_values

    def get_active_aus(self, threshold: float = 0.3) -> Dict[str, float]:
        active = {}
        for au_id, au in self.action_units.items():
            if au.intensity > threshold:
                active[au_id] = au.intensity
        return active

    def get_all_aus(self) -> Dict[str, float]:
        return {au_id: au.intensity for au_id, au in self.action_units.items()}

    def reset_baseline(self):
        self.baseline_set = False
        self.baseline_frame_count = 0
        self.baseline_distances.clear()
