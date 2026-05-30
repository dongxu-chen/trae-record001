import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.ndimage import gaussian_filter
import config


class DetailEnhancementNet(nn.Module):
    def __init__(self, in_channels=3, num_filters=64):
        super(DetailEnhancementNet, self).__init__()
        
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, num_filters, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_filters, num_filters, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            
            nn.Conv2d(num_filters, num_filters * 2, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_filters * 2, num_filters * 2, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            
            nn.Conv2d(num_filters * 2, num_filters * 4, 3, padding=1),
            nn.ReLU(inplace=True),
        )
        
        self.decoder = nn.Sequential(
            nn.Conv2d(num_filters * 4, num_filters * 2, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            
            nn.Conv2d(num_filters * 2, num_filters, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            
            nn.Conv2d(num_filters, num_filters, 3, padding=1),
            nn.ReLU(inplace=True),
        )
        
        self.normal_head = nn.Conv2d(num_filters, 3, 3, padding=1)
        self.displacement_head = nn.Conv2d(num_filters, 1, 3, padding=1)
        
    def forward(self, x):
        features = self.encoder(x)
        decoded = self.decoder(features)
        
        normal_map = self.normal_head(decoded)
        normal_map = F.normalize(normal_map, p=2, dim=1)
        
        displacement = self.displacement_head(decoded)
        
        return normal_map, displacement


class WrinkleGenerator:
    def __init__(self, image_size=512):
        self.image_size = image_size
        
    def generate_wrinkle_pattern(self, landmarks, intensity=0.5):
        h, w = self.image_size, self.image_size
        wrinkle_map = np.zeros((h, w), dtype=np.float32)
        
        if landmarks is None or len(landmarks) < 68:
            return wrinkle_map
        
        landmarks = np.array(landmarks)
        
        forehead_pts = landmarks[17:27]
        self._add_forehead_wrinkles(wrinkle_map, forehead_pts, intensity)
        
        eye_outer_pts = np.vstack([landmarks[36:42], landmarks[42:48]])
        self._add_crows_feet(wrinkle_map, eye_outer_pts, intensity)
        
        mouth_pts = landmarks[48:60]
        self._add_mouth_lines(wrinkle_map, mouth_pts, intensity)
        
        nose_pts = landmarks[27:36]
        self._add_nose_lines(wrinkle_map, nose_pts, intensity)
        
        return wrinkle_map
    
    def _add_forehead_wrinkles(self, wrinkle_map, pts, intensity):
        center_y = np.mean(pts[:, 1])
        center_x = np.mean(pts[:, 0])
        width = np.ptp(pts[:, 0])
        
        for i in range(3):
            y = int(center_y - 20 + i * 15)
            for x in range(int(center_x - width/2), int(center_x + width/2)):
                if 0 <= y < wrinkle_map.shape[0] and 0 <= x < wrinkle_map.shape[1]:
                    wrinkle_map[y, x] += intensity * (1 - abs(x - center_x) / (width/2))
                    if y + 1 < wrinkle_map.shape[0]:
                        wrinkle_map[y+1, x] += intensity * 0.5 * (1 - abs(x - center_x) / (width/2))
    
    def _add_crows_feet(self, wrinkle_map, pts, intensity):
        for eye_idx in range(2):
            eye_pts = pts[eye_idx*6:(eye_idx+1)*6]
            outer_corner = eye_pts[3]
            
            for i in range(4):
                angle = np.pi * 0.2 + i * np.pi * 0.15
                length = 30
                for t in np.linspace(0, 1, 20):
                    x = int(outer_corner[0] + t * length * np.cos(angle))
                    y = int(outer_corner[1] + t * length * np.sin(angle))
                    if 0 <= y < wrinkle_map.shape[0] and 0 <= x < wrinkle_map.shape[1]:
                        wrinkle_map[y, x] += intensity * (1 - t)
    
    def _add_mouth_lines(self, wrinkle_map, pts, intensity):
        left_corner = pts[0]
        right_corner = pts[6]
        
        for i in range(3):
            y_offset = i * 8
            for t in np.linspace(0, 1, 15):
                x = int(left_corner[0] + t * 20 - 10)
                y = int(left_corner[1] + 15 + y_offset + t * 10)
                if 0 <= y < wrinkle_map.shape[0] and 0 <= x < wrinkle_map.shape[1]:
                    wrinkle_map[y, x] += intensity * 0.6
                
                x = int(right_corner[0] - t * 20 + 10)
                y = int(right_corner[1] + 15 + y_offset + t * 10)
                if 0 <= y < wrinkle_map.shape[0] and 0 <= x < wrinkle_map.shape[1]:
                    wrinkle_map[y, x] += intensity * 0.6
    
    def _add_nose_lines(self, wrinkle_map, pts, intensity):
        nose_tip = pts[3]
        nose_bridge = pts[0]
        
        for side in [-1, 1]:
            for t in np.linspace(0, 1, 15):
                x = int(nose_bridge[0] + side * 10 * t + side * t * 15)
                y = int(nose_bridge[1] + (nose_tip[1] - nose_bridge[1]) * t)
                if 0 <= y < wrinkle_map.shape[0] and 0 <= x < wrinkle_map.shape[1]:
                    wrinkle_map[y, x] += intensity * 0.5


class PoreGenerator:
    def __init__(self, density=5000, pore_size=3):
        self.density = density
        self.pore_size = pore_size
    
    def generate_pores(self, face_mask, density_scale=1.0):
        h, w = face_mask.shape[:2]
        pore_map = np.zeros((h, w), dtype=np.float32)
        
        num_pores = int(self.density * density_scale)
        
        coords = np.argwhere(face_mask > 0)
        if len(coords) == 0:
            return pore_map
        
        for _ in range(num_pores):
            idx = np.random.randint(0, len(coords))
            y, x = coords[idx]
            
            pore = np.exp(-np.arange(-self.pore_size, self.pore_size+1)**2 / (2 * (self.pore_size/2)**2))
            
            for dy in range(-self.pore_size, self.pore_size+1):
                for dx in range(-self.pore_size, self.pore_size+1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        pore_map[ny, nx] += pore[dy+self.pore_size] * pore[dx+self.pore_size] * 0.3
        
        return np.clip(pore_map, 0, 1)


class NormalMapGenerator:
    def __init__(self, height_scale=0.1):
        self.height_scale = height_scale
    
    def compute_normals_from_depth(self, depth_map):
        h, w = depth_map.shape
        
        dx = cv2.Sobel(depth_map, cv2.CV_32F, 1, 0, ksize=3)
        dy = cv2.Sobel(depth_map, cv2.CV_32F, 0, 1, ksize=3)
        
        dx = dx * self.height_scale
        dy = dy * self.height_scale
        
        normal_map = np.zeros((h, w, 3), dtype=np.float32)
        normal_map[:, :, 0] = -dx
        normal_map[:, :, 1] = -dy
        normal_map[:, :, 2] = 1.0
        
        norm = np.linalg.norm(normal_map, axis=2, keepdims=True)
        normal_map = normal_map / (norm + 1e-8)
        
        normal_map = (normal_map + 1) / 2
        
        return normal_map
    
    def enhance_with_details(self, base_normals, wrinkle_map, pore_map):
        detail_height = wrinkle_map * 0.5 + pore_map * 0.3
        detail_normals = self.compute_normals_from_depth(detail_height)
        
        base_normals_float = base_normals.astype(np.float32) / 255.0 * 2 - 1
        detail_normals_float = detail_normals * 2 - 1
        
        combined = base_normals_float + detail_normals_float * 0.3
        combined = combined / (np.linalg.norm(combined, axis=2, keepdims=True) + 1e-8)
        
        combined = (combined + 1) / 2 * 255
        
        return combined.astype(np.uint8)


class DisplacementMapGenerator:
    def __init__(self, base_resolution=512):
        self.base_resolution = base_resolution
        
    def generate_displacement_map(self, vertices, triangles, uv_coords=None):
        h = w = self.base_resolution
        displacement_map = np.zeros((h, w), dtype=np.float32)
        
        if uv_coords is None:
            return displacement_map
        
        for i, tri in enumerate(triangles):
            for j in range(3):
                uv = uv_coords[tri[j]]
                x = int(uv[0] * (w - 1))
                y = int(uv[1] * (h - 1))
                if 0 <= y < h and 0 <= x < w:
                    displacement_map[y, x] = vertices[tri[j], 2]
        
        displacement_map = gaussian_filter(displacement_map, sigma=2)
        
        return displacement_map
    
    def add_fine_details(self, displacement_map, wrinkle_map, pore_map):
        enhanced = displacement_map.copy()
        
        enhanced += wrinkle_map * 0.1
        enhanced += pore_map * 0.02
        
        return enhanced


class FaceDetailEnhancer:
    def __init__(self, device='cpu'):
        self.device = device
        
        self.wrinkle_gen = WrinkleGenerator()
        self.pore_gen = PoreGenerator()
        self.normal_gen = NormalMapGenerator()
        self.disp_gen = DisplacementMapGenerator()
        
        try:
            self.detail_net = DetailEnhancementNet().to(device)
            self.detail_net.eval()
        except:
            self.detail_net = None
    
    def enhance_face(self, image, landmarks, vertices=None):
        h, w = image.shape[:2]
        
        face_mask = self._create_face_mask(image.shape, landmarks)
        
        wrinkle_map = self.wrinkle_gen.generate_wrinkle_pattern(landmarks, intensity=0.7)
        
        pore_map = self.pore_gen.generate_pores(face_mask, density_scale=0.8)
        
        if vertices is not None:
            base_normals = self._compute_vertex_normals(vertices, image.shape)
        else:
            base_normals = np.zeros((h, w, 3), dtype=np.uint8) + 128
            base_normals[:, :, 2] = 255
        
        normal_map = self.normal_gen.enhance_with_details(base_normals, wrinkle_map, pore_map)
        
        displacement = self.disp_gen.generate_displacement_map(
            vertices if vertices is not None else np.zeros((100, 3)), 
            np.zeros((100, 3), dtype=int)
        )
        displacement = self.disp_gen.add_fine_details(displacement, wrinkle_map, pore_map)
        
        detailed_image = self._apply_details_to_image(image, wrinkle_map, pore_map)
        
        return {
            'wrinkle_map': wrinkle_map,
            'pore_map': pore_map,
            'normal_map': normal_map,
            'displacement_map': displacement,
            'detailed_image': detailed_image,
            'face_mask': face_mask
        }
    
    def _create_face_mask(self, shape, landmarks):
        h, w = shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        if landmarks is None or len(landmarks) < 68:
            center = (w // 2, h // 2)
            radius = int(min(w, h) * 0.4)
            cv2.circle(mask, center, radius, 1, -1)
            return mask
        
        landmarks = np.array(landmarks, dtype=np.int32)
        face_contour = landmarks[0:17]
        face_contour = np.vstack([face_contour, landmarks[26:16:-1]])
        
        cv2.fillPoly(mask, [face_contour.reshape(-1, 1, 2)], 1)
        
        return mask
    
    def _compute_vertex_normals(self, vertices, image_shape):
        h, w = image_shape[:2]
        normals = np.zeros((h, w, 3), dtype=np.float32)
        
        grid_size = int(np.sqrt(len(vertices)))
        
        for i in range(min(grid_size - 1, h - 1)):
            for j in range(min(grid_size - 1, w - 1)):
                idx = i * grid_size + j
                if idx + grid_size + 1 < len(vertices):
                    v0 = vertices[idx]
                    v1 = vertices[idx + 1]
                    v2 = vertices[idx + grid_size]
                    
                    normal = np.cross(v1 - v0, v2 - v0)
                    normal = normal / (np.linalg.norm(normal) + 1e-8)
                    
                    if i < h and j < w:
                        normals[i, j] = (normal + 1) / 2 * 255
        
        return normals.astype(np.uint8)
    
    def _apply_details_to_image(self, image, wrinkle_map, pore_map):
        result = image.copy().astype(np.float32)
        
        detail_shading = (wrinkle_map[:, :, np.newaxis] + pore_map[:, :, np.newaxis]) * 30
        
        result -= detail_shading
        result = np.clip(result, 0, 255)
        
        return result.astype(np.uint8)


def save_normal_map(normal_map, filepath):
    cv2.imwrite(filepath, cv2.cvtColor(normal_map, cv2.COLOR_RGB2BGR))
    print(f"Normal map saved to {filepath}")


def save_displacement_map(disp_map, filepath, normalize=True):
    if normalize:
        disp_map = cv2.normalize(disp_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    cv2.imwrite(filepath, disp_map)
    print(f"Displacement map saved to {filepath}")
