import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class PolarizationEstimationConfig:
    n_channels: int = 3
    base_channels: int = 32
    image_size: Tuple[int, int] = (256, 256)
    use_attention: bool = True


class SEBlock(nn.Module):
    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        return x * y.expand_as(x)


class ResidualBlock(nn.Module):
    def __init__(self, channels: int, use_se: bool = True):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.se = SEBlock(channels) if use_se else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.se(out)
        out += residual
        out = self.relu(out)
        return out


class PolarizationEstimatorNet(nn.Module):
    def __init__(self, config: Optional[PolarizationEstimationConfig] = None):
        super().__init__()
        self.config = config or PolarizationEstimationConfig()
        
        ch = self.config.base_channels
        
        self.in_conv = nn.Sequential(
            nn.Conv2d(3, ch, kernel_size=7, stride=1, padding=3, bias=False),
            nn.BatchNorm2d(ch),
            nn.ReLU(inplace=True)
        )
        
        self.encoder1 = self._make_encoder_block(ch, ch * 2)
        self.encoder2 = self._make_encoder_block(ch * 2, ch * 4)
        self.encoder3 = self._make_encoder_block(ch * 4, ch * 8)
        
        self.mid_blocks = nn.Sequential(*[
            ResidualBlock(ch * 8, use_se=self.config.use_attention)
            for _ in range(4)
        ])
        
        self.decoder3 = self._make_decoder_block(ch * 8, ch * 4)
        self.decoder2 = self._make_decoder_block(ch * 4, ch * 2)
        self.decoder1 = self._make_decoder_block(ch * 2, ch)
        
        self.fusion = nn.Sequential(
            nn.Conv2d(ch, ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch, ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(ch),
            nn.ReLU(inplace=True)
        )
        
        self.out_dolp = nn.Sequential(
            nn.Conv2d(ch, 1, kernel_size=3, padding=1),
            nn.Sigmoid()
        )
        
        self.out_aop = nn.Sequential(
            nn.Conv2d(ch, 1, kernel_size=3, padding=1),
            nn.Sigmoid()
        )
        
        self.out_stokes = nn.Sequential(
            nn.Conv2d(ch, 3, kernel_size=3, padding=1),
            nn.Tanh()
        )

    def _make_encoder_block(self, in_channels: int, out_channels: int) -> nn.Module:
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            ResidualBlock(out_channels, use_se=self.config.use_attention)
        )

    def _make_decoder_block(self, in_channels: int, out_channels: int) -> nn.Module:
        return nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            ResidualBlock(out_channels, use_se=self.config.use_attention)
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        _, _, h, w = x.shape
        
        if (h, w) != self.config.image_size:
            x = F.interpolate(x, size=self.config.image_size, mode='bilinear', align_corners=True)
        
        feat0 = self.in_conv(x)
        feat1 = self.encoder1(feat0)
        feat2 = self.encoder2(feat1)
        feat3 = self.encoder3(feat2)
        
        feat_mid = self.mid_blocks(feat3)
        
        feat_d3 = self.decoder3(feat_mid) + feat2
        feat_d2 = self.decoder2(feat_d3) + feat1
        feat_d1 = self.decoder1(feat_d2) + feat0
        
        feat_fused = self.fusion(feat_d1)
        
        if (h, w) != self.config.image_size:
            feat_fused = F.interpolate(feat_fused, size=(h, w), mode='bilinear', align_corners=True)
        
        dolp = self.out_dolp(feat_fused)
        aop = self.out_aop(feat_fused) * np.pi
        stokes = self.out_stokes(feat_fused)
        
        return {
            'dolp': dolp,
            'aop': aop,
            'stokes': stokes
        }


class PolarizationEstimator:
    def __init__(
        self,
        config: Optional[PolarizationEstimationConfig] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        self.config = config or PolarizationEstimationConfig()
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        
        self.model = PolarizationEstimatorNet(self.config).to(self.device)
        
        if model_path and os.path.exists(model_path):
            self.load_checkpoint(model_path)
        
        self.model.eval()
    
    def load_checkpoint(self, checkpoint_path: str):
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        if 'model_state_dict' in checkpoint:
            self.model.load_state_dict(checkpoint['model_state_dict'])
        else:
            self.model.load_state_dict(checkpoint)
        print(f"Loaded polarization estimator from {checkpoint_path}")
    
    @torch.no_grad()
    def estimate(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        h, w = image.shape[:2]
        
        x = self._preprocess(image)
        x = x.to(self.device)
        
        outputs = self.model(x)
        
        dolp = outputs['dolp'].squeeze().cpu().numpy()
        aop = outputs['aop'].squeeze().cpu().numpy()
        stokes = outputs['stokes'].permute(0, 2, 3, 1).squeeze().cpu().numpy()
        
        if dolp.shape[:2] != (h, w):
            dolp = cv2.resize(dolp, (w, h))
            aop = cv2.resize(aop, (w, h))
            stokes = cv2.resize(stokes, (w, h))
        
        return {
            'dolp': dolp,
            'aop': aop,
            'stokes': stokes,
            'polarization_mask': self._generate_polarization_mask(dolp)
        }
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        if image.shape[:2] != self.config.image_size:
            image = cv2.resize(image, (self.config.image_size[1], self.config.image_size[0]))
        
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        image = image.astype(np.float32) / 255.0
        
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        image = (image - mean) / std
        
        tensor = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
        return tensor
    
    def _generate_polarization_mask(self, dolp: np.ndarray, threshold: float = 0.3) -> np.ndarray:
        mask = (dolp > threshold).astype(np.uint8) * 255
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    
    @torch.no_grad()
    def estimate_batch(self, images: list) -> list:
        results = []
        for img in images:
            results.append(self.estimate(img))
        return results
    
    def visualize_polarization(self, image: np.ndarray, results: Dict[str, np.ndarray]) -> np.ndarray:
        h, w = image.shape[:2]
        
        dolp_vis = (results['dolp'] * 255).astype(np.uint8)
        dolp_vis = cv2.applyColorMap(dolp_vis, cv2.COLORMAP_JET)
        
        aop_vis = (results['aop'] / np.pi * 255).astype(np.uint8)
        aop_vis = cv2.applyColorMap(aop_vis, cv2.COLORMAP_HSV)
        
        mask_vis = cv2.cvtColor(results['polarization_mask'], cv2.COLOR_GRAY2BGR)
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
        
        vis_height = max(h, 256)
        combined = np.zeros((vis_height, w * 4, 3), dtype=np.uint8)
        
        if image_rgb.shape[:2] != (vis_height, w):
            image_rgb = cv2.resize(image_rgb, (w, vis_height))
        
        combined[:vis_height, :w] = image_rgb
        combined[:vis_height, w:2*w] = cv2.resize(dolp_vis, (w, vis_height))
        combined[:vis_height, 2*w:3*w] = cv2.resize(aop_vis, (w, vis_height))
        combined[:vis_height, 3*w:] = cv2.resize(mask_vis, (w, vis_height))
        
        return combined


class TraditionalPolarizationEstimator:
    def __init__(self):
        pass
    
    def estimate(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        h, w = image.shape[:2]
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        
        edges = cv2.Canny(gray, 50, 150)
        
        intensity = gray.astype(np.float32) / 255.0
        
        gradients_x = cv2.Sobel(intensity, cv2.CV_32F, 1, 0, ksize=3)
        gradients_y = cv2.Sobel(intensity, cv2.CV_32F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(gradients_x**2 + gradients_y**2)
        
        laplacian = cv2.Laplacian(intensity, cv2.CV_32F)
        specularity = np.abs(laplacian)
        
        specularity_norm = (specularity - specularity.min()) / (specularity.max() - specularity.min() + 1e-8)
        gradient_norm = (gradient_mag - gradient_mag.min()) / (gradient_mag.max() - gradient_mag.min() + 1e-8)
        
        edges_norm = edges.astype(np.float32) / 255.0
        
        dolp = 0.4 * specularity_norm + 0.3 * edges_norm + 0.3 * (1.0 - gradient_norm)
        dolp = np.clip(dolp, 0, 1)
        
        aop = np.arctan2(gradients_y, gradients_x + 1e-8)
        aop = (aop + np.pi) % np.pi
        
        S0 = intensity
        S1 = dolp * np.cos(2 * aop)
        S2 = dolp * np.sin(2 * aop)
        stokes = np.stack([S0, S1, S2], axis=-1)
        
        return {
            'dolp': dolp,
            'aop': aop,
            'stokes': stokes,
            'polarization_mask': (dolp > 0.3).astype(np.uint8) * 255
        }
    
    def estimate_from_color(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        h, w = image.shape[:2]
        
        image_float = image.astype(np.float32) / 255.0
        
        r, g, b = image_float[..., 0], image_float[..., 1], image_float[..., 2]
        
        max_channel = np.max(image_float, axis=-1)
        min_channel = np.min(image_float, axis=-1)
        saturation = np.where(max_channel > 0, (max_channel - min_channel) / (max_channel + 1e-8), 0)
        
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        
        chroma = np.sqrt((r - g)**2 + (g - b)**2 + (b - r)**2)
        
        specular_mask = (luminance > 0.8) & (saturation < 0.2)
        
        diff_from_white = np.sqrt((r - 1.0)**2 + (g - 1.0)**2 + (b - 1.0)**2)
        dolp = 0.5 * (1.0 - saturation) + 0.3 * (1.0 - chroma) + 0.2 * luminance
        dolp = np.clip(dolp, 0, 1)
        
        aop = np.zeros_like(dolp)
        for i in range(h):
            for j in range(w):
                if specular_mask[i, j]:
                    aop[i, j] = np.pi / 4
                else:
                    aop[i, j] = np.arctan2(g[i, j] - b[i, j], r[i, j] - g[i, j] + 1e-8) % np.pi
        
        stokes = np.stack([luminance, dolp * np.cos(2 * aop), dolp * np.sin(2 * aop)], axis=-1)
        
        return {
            'dolp': dolp,
            'aop': aop,
            'stokes': stokes,
            'polarization_mask': specular_mask.astype(np.uint8) * 255
        }



