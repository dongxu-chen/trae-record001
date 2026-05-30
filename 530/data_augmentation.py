import cv2
import numpy as np
import torch
import random
from math import cos, sin, pi


class LargeAnglePoseAugmentation:
    def __init__(self, max_yaw=90, max_pitch=60, max_roll=30, probability=0.5):
        self.max_yaw = max_yaw
        self.max_pitch = max_pitch
        self.max_roll = max_roll
        self.probability = probability
    
    def __call__(self, image, landmarks=None):
        if random.random() > self.probability:
            if landmarks is not None:
                return image, landmarks, np.zeros(3)
            return image, np.zeros(3)
        
        yaw = random.uniform(-self.max_yaw, self.max_yaw) * pi / 180
        pitch = random.uniform(-self.max_pitch, self.max_pitch) * pi / 180
        roll = random.uniform(-self.max_roll, self.max_roll) * pi / 180
        
        angles = np.array([pitch, yaw, roll])
        
        rotated_image = self.rotate_image(image, yaw, pitch, roll)
        
        rotated_landmarks = None
        if landmarks is not None:
            rotated_landmarks = self.rotate_landmarks(landmarks, image.shape, yaw, pitch, roll)
        
        if landmarks is not None:
            return rotated_image, rotated_landmarks, angles
        return rotated_image, angles
    
    def rotate_image(self, image, yaw, pitch, roll):
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        R = self._compute_rotation_matrix(yaw, pitch, roll)
        
        corners = np.array([
            [0, 0, 0],
            [w, 0, 0],
            [w, h, 0],
            [0, h, 0]
        ], dtype=np.float32)
        
        corners_3d = corners - np.array([center[0], center[1], 0], dtype=np.float32)
        corners_rotated = np.dot(corners_3d, R.T)
        
        x_min, y_min = corners_rotated[:, :2].min(axis=0)
        x_max, y_max = corners_rotated[:, :2].max(axis=0)
        
        new_w = int(np.ceil(x_max - x_min))
        new_h = int(np.ceil(y_max - y_min))
        
        translation = np.array([-x_min, -y_min])
        
        M = np.eye(3)
        M[:2, :2] = R[:2, :2]
        M[:2, 2] = translation - np.dot(R[:2, :2], np.array([center[0], center[1]]))
        
        rotated_image = cv2.warpAffine(image, M[:2, :], (new_w, new_h), 
                                       flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=(0, 0, 0))
        
        rotated_image = cv2.resize(rotated_image, (w, h))
        
        return rotated_image
    
    def rotate_landmarks(self, landmarks, image_shape, yaw, pitch, roll):
        h, w = image_shape[:2]
        center = np.array([w // 2, h // 2])
        
        R = self._compute_rotation_matrix(yaw, pitch, roll)
        
        landmarks_3d = np.hstack([landmarks - center, np.zeros((len(landmarks), 1))])
        landmarks_rotated = np.dot(landmarks_3d, R.T)
        
        landmarks_2d = landmarks_rotated[:, :2] + center
        
        return landmarks_2d
    
    def _compute_rotation_matrix(self, yaw, pitch, roll):
        R_yaw = np.array([
            [cos(yaw), 0, sin(yaw)],
            [0, 1, 0],
            [-sin(yaw), 0, cos(yaw)]
        ])
        
        R_pitch = np.array([
            [1, 0, 0],
            [0, cos(pitch), -sin(pitch)],
            [0, sin(pitch), cos(pitch)]
        ])
        
        R_roll = np.array([
            [cos(roll), -sin(roll), 0],
            [sin(roll), cos(roll), 0],
            [0, 0, 1]
        ])
        
        R = np.dot(R_roll, np.dot(R_pitch, R_yaw))
        
        return R


class LightingAugmentation:
    def __init__(self, 
                 brightness_range=(-0.3, 0.3),
                 contrast_range=(-0.3, 0.3),
                 color_jitter_range=(-0.2, 0.2),
                 gamma_range=(0.7, 1.5),
                 probability=0.5):
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.color_jitter_range = color_jitter_range
        self.gamma_range = gamma_range
        self.probability = probability
    
    def __call__(self, image):
        if random.random() > self.probability:
            return image, np.zeros(27)
        
        light_params = np.random.randn(27).astype(np.float32) * 0.1
        light_params[0::9] += 0.5
        
        augmented = image.copy()
        
        brightness = random.uniform(*self.brightness_range)
        augmented = cv2.convertScaleAbs(augmented, alpha=1.0, beta=brightness * 255)
        
        contrast = random.uniform(*self.contrast_range)
        augmented = cv2.convertScaleAbs(augmented, alpha=1.0 + contrast, beta=0)
        
        for c in range(3):
            jitter = random.uniform(*self.color_jitter_range)
            augmented[:, :, c] = np.clip(augmented[:, :, c] + jitter * 255, 0, 255)
        
        gamma = random.uniform(*self.gamma_range)
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        augmented = cv2.LUT(augmented, table)
        
        return augmented, light_params


class MultiLightingGenerator:
    def __init__(self, num_lights=3):
        self.num_lights = num_lights
    
    def generate_multi_lighting(self, image, base_light=None):
        h, w = image.shape[:2]
        
        results = []
        light_params_list = []
        
        if base_light is None:
            base_light = np.zeros(27, dtype=np.float32)
            base_light[0::9] = 0.5
        
        results.append(image)
        light_params_list.append(base_light)
        
        for i in range(self.num_lights - 1):
            light_params = base_light.copy()
            light_params += np.random.randn(27).astype(np.float32) * 0.05
            
            shaded_image = self._apply_shading(image, light_params)
            results.append(shaded_image)
            light_params_list.append(light_params)
        
        return results, light_params_list
    
    def _apply_shading(self, image, light_params):
        h, w = image.shape[:2]
        
        y, x = np.mgrid[0:h, 0:w]
        center_x, center_y = w // 2, h // 2
        
        nx = (x - center_x) / (w // 2)
        ny = (y - center_y) / (h // 2)
        nz = np.sqrt(np.maximum(1 - nx**2 - ny**2, 0))
        
        normals = np.stack([nx, ny, nz], axis=-1)
        
        shading = self._compute_shading(normals, light_params)
        
        shaded_image = image.astype(np.float32) * shading[..., np.newaxis]
        shaded_image = np.clip(shaded_image, 0, 255).astype(np.uint8)
        
        return shaded_image
    
    def _compute_shading(self, normals, light_params):
        h, w = normals.shape[:2]
        
        sh_basis = np.zeros((h, w, 9), dtype=np.float32)
        
        x, y, z = normals[:, :, 0], normals[:, :, 1], normals[:, :, 2]
        
        sh_basis[:, :, 0] = 1 / np.sqrt(4 * np.pi)
        sh_basis[:, :, 1] = np.sqrt(3) / np.sqrt(4 * np.pi) * y
        sh_basis[:, :, 2] = np.sqrt(3) / np.sqrt(4 * np.pi) * z
        sh_basis[:, :, 3] = np.sqrt(3) / np.sqrt(4 * np.pi) * x
        sh_basis[:, :, 4] = np.sqrt(15) / np.sqrt(4 * np.pi) * x * y
        sh_basis[:, :, 5] = np.sqrt(15) / np.sqrt(4 * np.pi) * y * z
        sh_basis[:, :, 6] = np.sqrt(5) / np.sqrt(16 * np.pi) * (3 * z**2 - 1)
        sh_basis[:, :, 7] = np.sqrt(15) / np.sqrt(4 * np.pi) * x * z
        sh_basis[:, :, 8] = np.sqrt(15) / np.sqrt(16 * np.pi) * (x**2 - y**2)
        
        sh_coeffs = light_params.reshape(9, 3)
        shading = np.dot(sh_basis.reshape(-1, 9), sh_coeffs).reshape(h, w, 3)
        shading = np.mean(shading, axis=-1)
        shading = np.clip(shading, 0.3, 1.5)
        
        return shading


class FaceDataAugmentationPipeline:
    def __init__(self, config=None):
        self.pose_aug = LargeAnglePoseAugmentation(
            max_yaw=90, max_pitch=60, max_roll=30, probability=0.7
        )
        
        self.light_aug = LightingAugmentation(
            probability=0.6
        )
        
        self.multi_light_gen = MultiLightingGenerator(num_lights=3)
    
    def __call__(self, image, landmarks=None, apply_pose=True, apply_light=True):
        results = {
            'original': image,
            'augmented': image,
            'pose_angles': np.zeros(3),
            'light_params': np.zeros(27)
        }
        
        if apply_pose:
            if landmarks is not None:
                aug_image, aug_landmarks, angles = self.pose_aug(image, landmarks)
                results['augmented'] = aug_image
                results['augmented_landmarks'] = aug_landmarks
                results['pose_angles'] = angles
            else:
                aug_image, angles = self.pose_aug(image)
                results['augmented'] = aug_image
                results['pose_angles'] = angles
        
        if apply_light:
            aug_image, light_params = self.light_aug(results['augmented'])
            results['augmented'] = aug_image
            results['light_params'] = light_params
        
        return results
    
    def generate_multi_view_batch(self, image, num_views=4):
        batch = []
        angles_list = []
        
        for _ in range(num_views):
            yaw = random.uniform(-60, 60) * pi / 180
            pitch = random.uniform(-45, 45) * pi / 180
            roll = random.uniform(-20, 20) * pi / 180
            
            rotated = self._simple_rotate(image, yaw, pitch, roll)
            batch.append(rotated)
            angles_list.append(np.array([pitch, yaw, roll]))
        
        return batch, angles_list
    
    def _simple_rotate(self, image, yaw, pitch, roll):
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        angle_deg = (yaw + pitch + roll) * 180 / pi * 0.3
        
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h),
                                 flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT)
        
        return rotated


def random_occlusion(image, max_occlusion_ratio=0.3):
    h, w = image.shape[:2]
    
    if random.random() > 0.3:
        return image
    
    occlusion_type = random.choice(['rectangle', 'ellipse', 'blur'])
    
    occluded = image.copy()
    
    if occlusion_type == 'rectangle':
        ow = int(w * random.uniform(0.1, max_occlusion_ratio))
        oh = int(h * random.uniform(0.1, max_occlusion_ratio))
        ox = random.randint(0, w - ow)
        oy = random.randint(0, h - oh)
        occluded[oy:oy+oh, ox:ox+ow] = np.random.randint(0, 255, (oh, ow, 3), dtype=np.uint8)
    
    elif occlusion_type == 'ellipse':
        center = (random.randint(w//4, 3*w//4), random.randint(h//4, 3*h//4))
        axes = (int(w*random.uniform(0.1, max_occlusion_ratio)), 
                int(h*random.uniform(0.1, max_occlusion_ratio)))
        angle = random.uniform(0, 360)
        cv2.ellipse(occluded, center, axes, angle, 0, 360, 
                    (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), -1)
    
    elif occlusion_type == 'blur':
        ksize = random.choice([15, 21, 31])
        occluded = cv2.GaussianBlur(image, (ksize, ksize), 0)
    
    return occluded


def add_noise(image, noise_level=0.02):
    if random.random() > 0.3:
        return image
    
    noise = np.random.normal(0, noise_level * 255, image.shape).astype(np.int16)
    noisy = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return noisy
