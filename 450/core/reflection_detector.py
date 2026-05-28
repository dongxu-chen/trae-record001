import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DetectionConfig:
    confidence_threshold: float = 0.5
    specular_threshold: float = 0.85
    edge_weight: float = 0.3
    color_weight: float = 0.3
    gradient_weight: float = 0.2
    structural_weight: float = 0.2
    min_reflection_area: float = 0.01
    use_deep_detector: bool = False
    deep_model_path: Optional[str] = None


class ReflectionDetectorNet(nn.Module):
    def __init__(self):
        super().__init__()
        
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 32, 7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
            
            self._make_block(32, 64),
            self._make_block(64, 128),
            self._make_block(128, 256),
        )
        
        self.decoder = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(256, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(128, 64, 3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(64, 32, 3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(32, 1, 1),
            nn.Sigmoid()
        )
    
    def _make_block(self, in_ch: int, out_ch: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        mask = self.decoder(feat)
        mask = F.interpolate(mask, size=x.shape[2:], mode='bilinear', align_corners=True)
        return mask


class ReflectionDetector:
    _deep_model = None
    _deep_model_path = None
    
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        self._deep_net = None
        
        if self.config.use_deep_detector:
            self._init_deep_model()
    
    def _init_deep_model(self):
        if self._deep_net is None or ReflectionDetector._deep_model_path != self.config.deep_model_path:
            self._deep_net = ReflectionDetectorNet()
            if self.config.deep_model_path and os.path.exists(self.config.deep_model_path):
                checkpoint = torch.load(self.config.deep_model_path, map_location='cpu')
                self._deep_net.load_state_dict(checkpoint.get('model_state_dict', checkpoint))
            self._deep_net.eval()
            ReflectionDetector._deep_model_path = self.config.deep_model_path
        self._deep_net = ReflectionDetector._deep_model
    
    @staticmethod
    def detect(image: np.ndarray, threshold: float = 0.5) -> Tuple[bool, float]:
        detector = ReflectionDetector()
        confidence = detector.compute_confidence(image)
        has_reflection = confidence >= threshold
        return has_reflection, float(confidence)
    
    def compute_confidence(self, image: np.ndarray) -> float:
        image_float = image.astype(np.float32) / 255.0
        
        specular_score = self._specular_detection(image_float)
        edge_score = self._edge_detection(image_float)
        color_score = self._color_analysis(image_float)
        gradient_score = self._gradient_analysis(image_float)
        structural_score = self._structural_analysis(image_float)
        
        confidence = (
            self.config.specular_threshold * specular_score +
            self.config.edge_weight * edge_score +
            self.config.color_weight * color_score +
            self.config.gradient_weight * gradient_score +
            self.config.structural_weight * structural_score
        )
        
        total_weight = (
            self.config.specular_threshold +
            self.config.edge_weight +
            self.config.color_weight +
            self.config.gradient_weight +
            self.config.structural_weight
        )
        
        confidence /= total_weight
        return float(np.clip(confidence, 0, 1))
    
    def _specular_detection(self, image_float: np.ndarray) -> float:
        gray = cv2.cvtColor((image_float * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        
        bright_mask = gray > self.config.specular_threshold
        bright_ratio = np.sum(bright_mask) / (gray.shape[0] * gray.shape[1])
        
        if len(image_float.shape) == 3:
            max_ch = np.max(image_float, axis=-1)
            min_ch = np.min(image_float, axis=-1)
            saturation = np.where(max_ch > 0.01, (max_ch - min_ch) / (max_ch + 1e-8), 0)
            
            specular_mask = (gray > self.config.specular_threshold) & (saturation < 0.15)
            specular_ratio = np.sum(specular_mask) / (gray.shape[0] * gray.shape[1])
        else:
            specular_ratio = bright_ratio
        
        score = min(1.0, specular_ratio * 20)
        return score
    
    def _edge_detection(self, image_float: np.ndarray) -> float:
        gray = cv2.cvtColor((image_float * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_variance = np.var(laplacian)
        
        double_edge_score = min(1.0, lap_variance / 5000.0)
        edge_density_score = min(1.0, edge_ratio * 10)
        
        return 0.5 * double_edge_score + 0.5 * edge_density_score
    
    def _color_analysis(self, image_float: np.ndarray) -> float:
        if len(image_float.shape) < 3:
            return 0.0
        
        r, g, b = image_float[..., 0], image_float[..., 1], image_float[..., 2]
        
        color_spread = np.sqrt(np.var(r) + np.var(g) + np.var(b))
        spread_score = min(1.0, color_spread / 0.3)
        
        max_ch = np.max(image_float, axis=-1)
        min_ch = np.min(image_float, axis=-1)
        saturation = np.where(max_ch > 0.01, (max_ch - min_ch) / (max_ch + 1e-8), 0)
        
        low_sat_ratio = np.sum(saturation < 0.1) / saturation.size
        low_sat_score = min(1.0, low_sat_ratio * 5)
        
        brightness = (r + g + b) / 3.0
        high_bright_ratio = np.sum(brightness > 0.85) / brightness.size
        high_bright_score = min(1.0, high_bright_ratio * 10)
        
        return 0.3 * spread_score + 0.4 * low_sat_score + 0.3 * high_bright_score
    
    def _gradient_analysis(self, image_float: np.ndarray) -> float:
        gray = cv2.cvtColor((image_float * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(grad_x**2 + grad_y**2)
        
        mean_grad = np.mean(gradient_mag)
        high_grad_ratio = np.sum(gradient_mag > 0.3) / gradient_mag.size
        
        grad_score = min(1.0, (mean_grad / 0.2 + high_grad_ratio * 5) / 2)
        return grad_score
    
    def _structural_analysis(self, image_float: np.ndarray) -> float:
        gray = cv2.cvtColor((image_float * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        
        h, w = gray.shape
        block_h, block_w = h // 4, w // 4
        
        block_means = []
        for i in range(4):
            for j in range(4):
                block = gray[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
                block_means.append(np.mean(block))
        
        block_std = np.std(block_means)
        structural_score = min(1.0, block_std / 60.0)
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_mean = np.mean(np.abs(laplacian))
        focus_score = min(1.0, lap_mean / 30.0)
        
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        diff = np.abs(gray.astype(np.float32) - bilateral.astype(np.float32))
        texture_score = min(1.0, np.mean(diff) / 15.0)
        
        return 0.3 * structural_score + 0.3 * focus_score + 0.4 * texture_score
    
    def detect_mask(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        if self.config.use_deep_detector and self._deep_net is not None:
            return self._detect_mask_deep(image)
        else:
            return self._detect_mask_traditional(image)
    
    def _detect_mask_traditional(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        image_float = image.astype(np.float32) / 255.0
        
        if len(image_float.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
            max_ch = np.max(image_float, axis=-1)
            min_ch = np.min(image_float, axis=-1)
            saturation = np.where(max_ch > 0.01, (max_ch - min_ch) / (max_ch + 1e-8), 0)
        else:
            gray = image_float
            saturation = np.ones_like(gray)
        
        bright_mask = (gray > self.config.specular_threshold).astype(np.float32)
        
        low_sat_mask = (saturation < 0.15).astype(np.float32)
        
        edges = cv2.Canny((gray * 255).astype(np.uint8), 50, 150)
        edge_mask = (edges > 0).astype(np.float32)
        edge_mask = cv2.dilate(edge_mask, np.ones((5, 5)), iterations=1)
        
        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        high_freq_mask = (np.abs(laplacian) > 20).astype(np.float32)
        
        combined = 0.4 * bright_mask + 0.3 * low_sat_mask + 0.15 * edge_mask + 0.15 * high_freq_mask
        
        combined = cv2.GaussianBlur(combined, (7, 7), 0)
        
        reflection_mask = (combined > self.config.confidence_threshold).astype(np.uint8) * 255
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        reflection_mask = cv2.morphologyEx(reflection_mask, cv2.MORPH_CLOSE, kernel)
        reflection_mask = cv2.morphologyEx(reflection_mask, cv2.MORPH_OPEN, kernel)
        
        confidence = self.compute_confidence(image)
        
        return reflection_mask, confidence
    
    def _detect_mask_deep(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        h, w = image.shape[:2]
        
        x = image.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean) / std
        
        tensor = torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0)
        
        with torch.no_grad():
            mask_pred = self._deep_net(tensor)
        
        mask = mask_pred.squeeze().cpu().numpy()
        mask = cv2.resize(mask, (w, h))
        
        reflection_mask = (mask > self.config.confidence_threshold).astype(np.uint8) * 255
        confidence = float(np.mean(mask))
        
        return reflection_mask, confidence
    
    def detect_batch(
        self,
        images: List[np.ndarray],
        skip_no_reflection: bool = True
    ) -> List[Dict]:
        results = []
        
        for idx, image in enumerate(images):
            reflection_mask, confidence = self.detect_mask(image)
            
            has_reflection = confidence >= self.config.confidence_threshold
            
            reflection_area_ratio = np.sum(reflection_mask > 0) / (image.shape[0] * image.shape[1])
            
            if reflection_area_ratio < self.config.min_reflection_area:
                has_reflection = False
            
            results.append({
                'index': idx,
                'has_reflection': has_reflection,
                'confidence': confidence,
                'reflection_mask': reflection_mask,
                'reflection_area_ratio': reflection_area_ratio,
                'should_process': has_reflection if skip_no_reflection else True
            })
        
        return results


import os
