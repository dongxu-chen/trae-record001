import numpy as np
import cv2
from scipy.ndimage import gaussian_filter


class MakeupStyle:
    def __init__(self, name):
        self.name = name
        self.lip_color = (180, 50, 100)
        self.eye_shadow_color = (100, 80, 120)
        self.blush_color = (200, 100, 120)
        self.foundation_color = (220, 180, 160)
        self.eyeliner_color = (20, 20, 20)
        
        self.lip_intensity = 0.7
        self.eye_intensity = 0.5
        self.blush_intensity = 0.4
        self.foundation_intensity = 0.3


class NaturalMakeup(MakeupStyle):
    def __init__(self):
        super().__init__("Natural")
        self.lip_color = (180, 80, 100)
        self.eye_shadow_color = (150, 120, 140)
        self.blush_color = (220, 140, 140)
        self.lip_intensity = 0.4
        self.eye_intensity = 0.2
        self.blush_intensity = 0.2


class GlamMakeup(MakeupStyle):
    def __init__(self):
        super().__init__("Glam")
        self.lip_color = (150, 30, 60)
        self.eye_shadow_color = (80, 40, 100)
        self.blush_color = (200, 60, 100)
        self.lip_intensity = 0.9
        self.eye_intensity = 0.7
        self.blush_intensity = 0.5


class DramaticMakeup(MakeupStyle):
    def __init__(self):
        super().__init__("Dramatic")
        self.lip_color = (50, 10, 30)
        self.eye_shadow_color = (30, 10, 50)
        self.blush_color = (180, 40, 80)
        self.lip_intensity = 1.0
        self.eye_intensity = 0.9
        self.blush_intensity = 0.6


class KoreanMakeup(MakeupStyle):
    def __init__(self):
        super().__init__("Korean")
        self.lip_color = (200, 100, 120)
        self.eye_shadow_color = (180, 160, 180)
        self.blush_color = (255, 150, 160)
        self.foundation_color = (230, 200, 180)
        self.lip_intensity = 0.6
        self.eye_intensity = 0.3
        self.blush_intensity = 0.5
        self.foundation_intensity = 0.4


class MakeupApplier:
    def __init__(self):
        self.makeup_styles = {
            'natural': NaturalMakeup(),
            'glam': GlamMakeup(),
            'dramatic': DramaticMakeup(),
            'korean': KoreanMakeup()
        }
    
    def apply_makeup(self, image, landmarks, style='natural', custom_style=None):
        if custom_style is not None:
            makeup_style = custom_style
        else:
            makeup_style = self.makeup_styles.get(style.lower(), NaturalMakeup())
        
        result = image.copy()
        
        face_mask = self._create_face_mask(image.shape, landmarks)
        
        if makeup_style.foundation_intensity > 0:
            result = self._apply_foundation(result, face_mask, makeup_style)
        
        if len(landmarks) >= 68:
            result = self._apply_lipstick(result, landmarks[48:68], makeup_style)
            result = self._apply_eyeshadow(result, landmarks, makeup_style)
            result = self._apply_blush(result, landmarks, makeup_style)
            result = self._apply_eyeliner(result, landmarks, makeup_style)
        
        result = self._blend_makeup(image, result, face_mask)
        
        return result
    
    def _create_face_mask(self, shape, landmarks):
        h, w = shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)
        
        if landmarks is None or len(landmarks) < 68:
            center = (w // 2, h // 2)
            radius = int(min(w, h) * 0.4)
            cv2.circle(mask, center, radius, 1.0, -1)
            return mask
        
        landmarks = np.array(landmarks, dtype=np.int32)
        face_contour = landmarks[0:17]
        face_contour = np.vstack([face_contour, landmarks[26:16:-1]])
        
        cv2.fillPoly(mask, [face_contour.reshape(-1, 1, 2)], 1.0)
        
        mask = gaussian_filter(mask, sigma=5)
        
        return mask
    
    def _apply_foundation(self, image, face_mask, style):
        result = image.copy().astype(np.float32)
        
        foundation = np.array(style.foundation_color, dtype=np.float32)
        
        alpha = style.foundation_intensity * face_mask[:, :, np.newaxis]
        
        result = result * (1 - alpha) + foundation * alpha
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def _apply_lipstick(self, image, lip_landmarks, style):
        result = image.copy()
        
        if len(lip_landmarks) < 20:
            return result
        
        lip_landmarks = np.array(lip_landmarks, dtype=np.int32)
        
        outer_lip = lip_landmarks[0:12]
        inner_lip = lip_landmarks[12:20]
        
        lip_mask = np.zeros(image.shape[:2], dtype=np.float32)
        
        hull = cv2.convexHull(lip_landmarks)
        cv2.fillPoly(lip_mask, [hull], 1.0)
        
        lip_mask = gaussian_filter(lip_mask, sigma=3)
        
        lip_color = np.array(style.lip_color, dtype=np.float32)
        
        alpha = style.lip_intensity * lip_mask[:, :, np.newaxis]
        
        result = result.astype(np.float32) * (1 - alpha) + lip_color * alpha
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def _apply_eyeshadow(self, image, landmarks, style):
        result = image.copy()
        
        eye_shadow_color = np.array(style.eye_shadow_color, dtype=np.float32)
        
        for eye_idx in range(2):
            if eye_idx == 0:
                eye_pts = landmarks[36:42]
            else:
                eye_pts = landmarks[42:48]
            
            eye_pts = np.array(eye_pts, dtype=np.int32)
            
            shadow_mask = np.zeros(image.shape[:2], dtype=np.float32)
            
            eye_center = np.mean(eye_pts, axis=0)
            eye_radius = np.max(np.linalg.norm(eye_pts - eye_center, axis=1))
            
            shadow_pts = []
            for pt in eye_pts:
                direction = pt - eye_center
                direction = direction / (np.linalg.norm(direction) + 1e-8)
                shadow_pt = pt + direction * eye_radius * 0.8
                shadow_pts.append(shadow_pt)
            
            shadow_pts = np.array(shadow_pts, dtype=np.int32)
            cv2.fillPoly(shadow_mask, [shadow_pts.reshape(-1, 1, 2)], 1.0)
            
            shadow_mask = gaussian_filter(shadow_mask, sigma=8)
            
            alpha = style.eye_intensity * shadow_mask[:, :, np.newaxis]
            
            result = result.astype(np.float32) * (1 - alpha) + eye_shadow_color * alpha
            result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def _apply_blush(self, image, landmarks, style):
        result = image.copy()
        
        blush_color = np.array(style.blush_color, dtype=np.float32)
        
        cheek_positions = [
            (int(landmarks[1][0] - 30), int(landmarks[29][1])),
            (int(landmarks[15][0] + 30), int(landmarks[29][1]))
        ]
        
        for cheek_pos in cheek_positions:
            blush_mask = np.zeros(image.shape[:2], dtype=np.float32)
            
            center = cheek_pos
            axes = (60, 40)
            cv2.ellipse(blush_mask, center, axes, 0, 0, 360, 1.0, -1)
            
            blush_mask = gaussian_filter(blush_mask, sigma=15)
            
            alpha = style.blush_intensity * blush_mask[:, :, np.newaxis]
            
            result = result.astype(np.float32) * (1 - alpha) + blush_color * alpha
            result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def _apply_eyeliner(self, image, landmarks, style):
        result = image.copy()
        
        eyeliner_color = style.eyeliner_color
        thickness = 2
        
        for eye_idx in range(2):
            if eye_idx == 0:
                eye_pts = landmarks[36:42]
            else:
                eye_pts = landmarks[42:48]
            
            eye_pts = np.array(eye_pts, dtype=np.int32)
            
            upper_lid = eye_pts[0:4]
            cv2.polylines(result, [upper_lid.reshape(-1, 1, 2)], False, eyeliner_color, thickness)
        
        return result
    
    def _blend_makeup(self, original, makeup_image, face_mask):
        alpha = 0.7 + 0.3 * face_mask[:, :, np.newaxis]
        result = original.astype(np.float32) * (1 - alpha * 0.3) + makeup_image.astype(np.float32) * alpha * 0.3
        result = np.clip(result, 0, 255).astype(np.uint8)
        return result


class MakeupTransfer:
    def __init__(self):
        pass
    
    def transfer_makeup(self, source_image, source_landmarks, 
                        target_image, target_landmarks):
        source_lab = cv2.cvtColor(source_image, cv2.COLOR_BGR2LAB)
        target_lab = cv2.cvtColor(target_image, cv2.COLOR_BGR2LAB)
        
        source_face_mask = self._create_face_mask(source_image.shape, source_landmarks)
        target_face_mask = self._create_face_mask(target_image.shape, target_landmarks)
        
        result_lab = target_lab.copy()
        
        for c in range(3):
            source_mean = np.mean(source_lab[:, :, c][source_face_mask > 0.5])
            target_mean = np.mean(target_lab[:, :, c][target_face_mask > 0.5])
            
            source_std = np.std(source_lab[:, :, c][source_face_mask > 0.5])
            target_std = np.std(target_lab[:, :, c][target_face_mask > 0.5])
            
            transferred = (target_lab[:, :, c] - target_mean) * (source_std / (target_std + 1e-8)) + source_mean
            
            alpha = target_face_mask[:, :, np.newaxis] if c == 0 else target_face_mask[:, :, np.newaxis] * 0.5
            result_lab[:, :, c] = target_lab[:, :, c] * (1 - alpha) + transferred * alpha
        
        result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
        result = cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)
        
        return result
    
    def _create_face_mask(self, shape, landmarks):
        h, w = shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)
        
        if landmarks is None or len(landmarks) < 68:
            center = (w // 2, h // 2)
            radius = int(min(w, h) * 0.4)
            cv2.circle(mask, center, radius, 1.0, -1)
            return mask
        
        landmarks = np.array(landmarks, dtype=np.int32)
        face_contour = landmarks[0:17]
        face_contour = np.vstack([face_contour, landmarks[26:16:-1]])
        
        cv2.fillPoly(mask, [face_contour.reshape(-1, 1, 2)], 1.0)
        
        mask = gaussian_filter(mask, sigma=8)
        
        return mask


class MakeupStyleInterpolator:
    def __init__(self):
        self.applier = MakeupApplier()
    
    def interpolate_styles(self, image, landmarks, style1, style2, alpha=0.5):
        style_a = self.applier.makeup_styles.get(style1.lower(), NaturalMakeup())
        style_b = self.applier.makeup_styles.get(style2.lower(), NaturalMakeup())
        
        interpolated = MakeupStyle("Interpolated")
        
        interpolated.lip_color = tuple(
            int(a * (1 - alpha) + b * alpha) for a, b in zip(style_a.lip_color, style_b.lip_color)
        )
        interpolated.eye_shadow_color = tuple(
            int(a * (1 - alpha) + b * alpha) for a, b in zip(style_a.eye_shadow_color, style_b.eye_shadow_color)
        )
        interpolated.blush_color = tuple(
            int(a * (1 - alpha) + b * alpha) for a, b in zip(style_a.blush_color, style_b.blush_color)
        )
        
        interpolated.lip_intensity = style_a.lip_intensity * (1 - alpha) + style_b.lip_intensity * alpha
        interpolated.eye_intensity = style_a.eye_intensity * (1 - alpha) + style_b.eye_intensity * alpha
        interpolated.blush_intensity = style_a.blush_intensity * (1 - alpha) + style_b.blush_intensity * alpha
        
        result = self.applier.apply_makeup(image, landmarks, custom_style=interpolated)
        
        return result, interpolated
    
    def create_style_morph_video(self, image, landmarks, style1, style2, num_frames=30):
        frames = []
        
        for i in range(num_frames):
            alpha = i / (num_frames - 1)
            frame, _ = self.interpolate_styles(image, landmarks, style1, style2, alpha)
            frames.append(frame)
        
        return frames


def apply_makeup_to_3d_model(vertices, texture, landmarks, style='natural'):
    applier = MakeupApplier()
    makeup_style = applier.makeup_styles.get(style.lower(), NaturalMakeup())
    
    textured_result = texture.copy()
    
    if landmarks is not None and len(landmarks) >= 68:
        lip_indices = landmarks[48:68]
        for idx in lip_indices:
            if idx < len(textured_result):
                textured_result[idx] = np.array(makeup_style.lip_color) * makeup_style.lip_intensity + \
                                      textured_result[idx] * (1 - makeup_style.lip_intensity)
    
    return textured_result


if __name__ == '__main__':
    print("Makeup Transfer Module")
    print("Available styles:", list(MakeupApplier().makeup_styles.keys()))
