import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MultiTaskConfig:
    shared_channels: int = 64
    num_shared_blocks: int = 6
    task_heads: List[str] = None
    reflection_weight: float = 1.0
    derain_weight: float = 0.8
    dehaze_weight: float = 0.8
    feature_sharing_ratio: float = 0.5
    
    def __post_init__(self):
        if self.task_heads is None:
            self.task_heads = ['reflection', 'derain', 'dehaze']


class ChannelAttention(nn.Module):
    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False)
        )
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.size()
        avg_out = self.fc(self.avg_pool(x).view(b, c))
        max_out = self.fc(self.max_pool(x).view(b, c))
        out = self.sigmoid(avg_out + max_out).view(b, c, 1, 1)
        return x * out


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size: int = 7):
        super().__init__()
        padding = kernel_size // 2
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=padding, bias=False)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        combined = torch.cat([avg_out, max_out], dim=1)
        attention = self.sigmoid(self.conv(combined))
        return x * attention


class CBAM(nn.Module):
    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        self.channel_att = ChannelAttention(channels, reduction)
        self.spatial_att = SpatialAttention()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_att(x)
        x = self.spatial_att(x)
        return x


class ResidualCBAMBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.cbam = CBAM(channels)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.cbam(out)
        out += residual
        out = self.relu(out)
        return out


class SharedEncoder(nn.Module):
    def __init__(self, in_channels: int = 3, shared_channels: int = 64, num_blocks: int = 6):
        super().__init__()
        
        self.entry = nn.Sequential(
            nn.Conv2d(in_channels, shared_channels, 7, padding=3, bias=False),
            nn.BatchNorm2d(shared_channels),
            nn.ReLU(inplace=True)
        )
        
        self.down1 = nn.Sequential(
            nn.Conv2d(shared_channels, shared_channels * 2, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels * 2),
            nn.ReLU(inplace=True)
        )
        
        self.down2 = nn.Sequential(
            nn.Conv2d(shared_channels * 2, shared_channels * 4, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels * 4),
            nn.ReLU(inplace=True)
        )
        
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualCBAMBlock(shared_channels * 4))
        self.shared_blocks = nn.Sequential(*blocks)
        
        self.cross_task_attention = CrossTaskAttention(shared_channels * 4)
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        f0 = self.entry(x)
        f1 = self.down1(f0)
        f2 = self.down2(f1)
        f_shared = self.shared_blocks(f2)
        
        return {
            'entry': f0,
            'down1': f1,
            'down2': f2,
            'shared': f_shared
        }


class CrossTaskAttention(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.query = nn.Conv2d(channels, channels // 8, 1)
        self.key = nn.Conv2d(channels, channels // 8, 1)
        self.value = nn.Conv2d(channels, channels, 1)
        self.gamma = nn.Parameter(torch.zeros(1))
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


class TaskDecoder(nn.Module):
    def __init__(self, shared_channels: int, out_channels: int = 3):
        super().__init__()
        
        self.up1 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(shared_channels * 4, shared_channels * 2, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels * 2),
            nn.ReLU(inplace=True),
            ResidualCBAMBlock(shared_channels * 2)
        )
        
        self.up2 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(shared_channels * 2, shared_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels),
            nn.ReLU(inplace=True),
            ResidualCBAMBlock(shared_channels)
        )
        
        self.out_conv = nn.Sequential(
            nn.Conv2d(shared_channels, shared_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(shared_channels, out_channels, 1)
        )
    
    def forward(
        self,
        shared_feat: torch.Tensor,
        skip1: Optional[torch.Tensor] = None,
        skip2: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        x = self.up1(shared_feat)
        if skip1 is not None:
            if x.shape[2:] != skip1.shape[2:]:
                skip1 = F.interpolate(skip1, size=x.shape[2:], mode='bilinear', align_corners=True)
            x = x + skip1
        
        x = self.up2(x)
        if skip2 is not None:
            if x.shape[2:] != skip2.shape[2:]:
                skip2 = F.interpolate(skip2, size=x.shape[2:], mode='bilinear', align_corners=True)
            x = x + skip2
        
        x = self.out_conv(x)
        return x


class ReflectionHead(nn.Module):
    def __init__(self, shared_channels: int):
        super().__init__()
        self.decoder = TaskDecoder(shared_channels, out_channels=3)
        self.alpha_head = nn.Sequential(
            nn.Conv2d(shared_channels * 4, shared_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=4, mode='bilinear', align_corners=True),
            nn.Conv2d(shared_channels, 1, 1),
            nn.Sigmoid()
        )
    
    def forward(
        self,
        shared_feat: torch.Tensor,
        skip1: Optional[torch.Tensor] = None,
        skip2: Optional[torch.Tensor] = None,
        original_size: Optional[Tuple[int, int]] = None
    ) -> Dict[str, torch.Tensor]:
        transmission = torch.sigmoid(self.decoder(shared_feat, skip1, skip2))
        alpha = self.alpha_head(shared_feat)
        
        if original_size:
            transmission = F.interpolate(transmission, size=original_size, mode='bilinear', align_corners=True)
            alpha = F.interpolate(alpha, size=original_size, mode='bilinear', align_corners=True)
        
        return {'transmission': transmission, 'alpha': alpha}


class DerainHead(nn.Module):
    def __init__(self, shared_channels: int):
        super().__init__()
        self.decoder = TaskDecoder(shared_channels, out_channels=3)
        self.rain_mask_head = nn.Sequential(
            nn.Conv2d(shared_channels * 4, shared_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=4, mode='bilinear', align_corners=True),
            nn.Conv2d(shared_channels, 1, 1),
            nn.Sigmoid()
        )
    
    def forward(
        self,
        shared_feat: torch.Tensor,
        skip1: Optional[torch.Tensor] = None,
        skip2: Optional[torch.Tensor] = None,
        original_size: Optional[Tuple[int, int]] = None
    ) -> Dict[str, torch.Tensor]:
        clean = torch.sigmoid(self.decoder(shared_feat, skip1, skip2))
        rain_mask = self.rain_mask_head(shared_feat)
        
        if original_size:
            clean = F.interpolate(clean, size=original_size, mode='bilinear', align_corners=True)
            rain_mask = F.interpolate(rain_mask, size=original_size, mode='bilinear', align_corners=True)
        
        return {'clean': clean, 'rain_mask': rain_mask}


class DehazeHead(nn.Module):
    def __init__(self, shared_channels: int):
        super().__init__()
        self.decoder = TaskDecoder(shared_channels, out_channels=3)
        self.transmission_head = nn.Sequential(
            nn.Conv2d(shared_channels * 4, shared_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=4, mode='bilinear', align_corners=True),
            nn.Conv2d(shared_channels, 1, 1),
            nn.Sigmoid()
        )
        self.alight_head = nn.Sequential(
            nn.Conv2d(shared_channels * 4, shared_channels // 2, 3, padding=1, bias=False),
            nn.BatchNorm2d(shared_channels // 2),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(shared_channels // 2, 3),
            nn.Sigmoid()
        )
    
    def forward(
        self,
        shared_feat: torch.Tensor,
        skip1: Optional[torch.Tensor] = None,
        skip2: Optional[torch.Tensor] = None,
        original_size: Optional[Tuple[int, int]] = None
    ) -> Dict[str, torch.Tensor]:
        clean = torch.sigmoid(self.decoder(shared_feat, skip1, skip2))
        t_map = self.transmission_head(shared_feat)
        a_light = self.alight_head(shared_feat)
        
        if original_size:
            clean = F.interpolate(clean, size=original_size, mode='bilinear', align_corners=True)
            t_map = F.interpolate(t_map, size=original_size, mode='bilinear', align_corners=True)
        
        return {'clean': clean, 'transmission_map': t_map, 'airlight': a_light}


class MultiTaskLoss(nn.Module):
    def __init__(self, config: Optional[MultiTaskConfig] = None):
        super().__init__()
        self.config = config or MultiTaskConfig()
        self.l1_loss = nn.L1Loss()
        self.mse_loss = nn.MSELoss()
    
    def forward(
        self,
        predictions: Dict[str, Dict[str, torch.Tensor]],
        targets: Dict[str, torch.Tensor],
        input_image: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        total_loss = torch.tensor(0.0, device=input_image.device)
        loss_dict = {}
        
        if 'reflection' in predictions:
            refl_pred = predictions['reflection']
            refl_target_t = targets.get('transmission', denormalize(input_image))
            refl_target_alpha = targets.get('alpha', torch.ones_like(input_image[:, :1]) * 0.8)
            
            t_loss = self.l1_loss(refl_pred['transmission'], refl_target_t)
            a_loss = self.mse_loss(refl_pred['alpha'], refl_target_alpha)
            
            reconstructed = refl_pred['alpha'] * refl_pred['transmission'] + (1 - refl_pred['alpha']) * input_image
            recon_loss = self.l1_loss(reconstructed, input_image)
            
            refl_loss = t_loss + 0.1 * a_loss + 0.5 * recon_loss
            loss_dict['reflection_loss'] = refl_loss
            total_loss = total_loss + self.config.reflection_weight * refl_loss
        
        if 'derain' in predictions:
            derain_pred = predictions['derain']
            derain_target = targets.get('clean', denormalize(input_image))
            
            clean_loss = self.l1_loss(derain_pred['clean'], derain_target)
            
            rain_streak = input_image - derain_pred['clean']
            rain_loss = self.l1_loss(derain_pred['rain_mask'], rain_streak.mean(dim=1, keepdim=True).abs())
            
            derain_loss = clean_loss + 0.3 * rain_loss
            loss_dict['derain_loss'] = derain_loss
            total_loss = total_loss + self.config.derain_weight * derain_loss
        
        if 'dehaze' in predictions:
            dehaze_pred = predictions['dehaze']
            dehaze_target = targets.get('clean', denormalize(input_image))
            
            clean_loss = self.l1_loss(dehaze_pred['clean'], dehaze_target)
            
            t_map = dehaze_pred['transmission_map']
            a_light = dehaze_pred['airlight'].view(-1, 3, 1, 1)
            reconstructed_hazy = t_map * dehaze_pred['clean'] + (1 - t_map) * a_light
            haze_recon_loss = self.l1_loss(reconstructed_hazy, input_image)
            
            dehaze_loss = clean_loss + 0.5 * haze_recon_loss
            loss_dict['dehaze_loss'] = dehaze_loss
            total_loss = total_loss + self.config.dehaze_weight * dehaze_loss
        
        loss_dict['total_loss'] = total_loss
        return loss_dict


def denormalize(tensor: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor([0.485, 0.456, 0.406], device=tensor.device).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=tensor.device).view(1, 3, 1, 1)
    return torch.clamp(tensor * std + mean, 0, 1)


class JointMultiTaskNet(nn.Module):
    def __init__(self, config: Optional[MultiTaskConfig] = None):
        super().__init__()
        self.config = config or MultiTaskConfig()
        
        self.encoder = SharedEncoder(
            shared_channels=self.config.shared_channels,
            num_blocks=self.config.num_shared_blocks
        )
        
        self.task_heads = nn.ModuleDict()
        if 'reflection' in self.config.task_heads:
            self.task_heads['reflection'] = ReflectionHead(self.config.shared_channels)
        if 'derain' in self.config.task_heads:
            self.task_heads['derain'] = DerainHead(self.config.shared_channels)
        if 'dehaze' in self.config.task_heads:
            self.task_heads['dehaze'] = DehazeHead(self.config.shared_channels)
    
    def forward(
        self,
        x: torch.Tensor,
        tasks: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, torch.Tensor]]:
        if tasks is None:
            tasks = self.config.task_heads
        
        original_size = x.shape[2:]
        
        encoder_out = self.encoder(x)
        shared_feat = encoder_out['shared']
        
        predictions = {}
        for task_name in tasks:
            if task_name in self.task_heads:
                predictions[task_name] = self.task_heads[task_name](
                    shared_feat,
                    skip1=encoder_out['down1'],
                    skip2=encoder_out['entry'],
                    original_size=original_size
                )
        
        return predictions


class MultiTaskProcessor:
    def __init__(
        self,
        config: Optional[MultiTaskConfig] = None,
        model_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        self.config = config or MultiTaskConfig()
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        
        self.model = JointMultiTaskNet(self.config).to(self.device)
        
        if model_path:
            self.load_checkpoint(model_path)
        
        self.model.eval()
        self.loss_fn = MultiTaskLoss(self.config)
    
    def load_checkpoint(self, path: str):
        import os
        if os.path.exists(path):
            checkpoint = torch.load(path, map_location=self.device)
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            self.model.load_state_dict(state_dict)
    
    @torch.no_grad()
    def process(
        self,
        image: np.ndarray,
        tasks: Optional[List[str]] = None
    ) -> Dict[str, np.ndarray]:
        if tasks is None:
            tasks = self.config.task_heads
        
        h, w = image.shape[:2]
        x = self._preprocess(image)
        x = x.to(self.device)
        
        predictions = self.model(x, tasks)
        
        results = {'input': image}
        for task_name, task_pred in predictions.items():
            for key, tensor in task_pred.items():
                arr = tensor.squeeze().cpu().numpy()
                if arr.ndim == 3:
                    arr = np.transpose(arr, (1, 2, 0))
                elif arr.ndim == 2:
                    pass
                
                if arr.dtype in [np.float32, np.float64]:
                    if arr.max() <= 1.0:
                        arr = (arr * 255).astype(np.uint8)
                
                if arr.shape[0] != h or arr.shape[1] != w:
                    if arr.ndim == 3:
                        arr = cv2.resize(arr, (w, h))
                    else:
                        arr = cv2.resize(arr, (w, h))
                
                results[f'{task_name}_{key}'] = arr
        
        return results
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        img = image.copy()
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        img = cv2.resize(img, (256, 256))
        img = img.astype(np.float32) / 255.0
        
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img = (img - mean) / std
        
        tensor = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0)
        return tensor
    
    def process_joint(
        self,
        image: np.ndarray,
        reflection_weight: float = 0.5,
        derain_weight: float = 0.25,
        dehaze_weight: float = 0.25
    ) -> Dict[str, np.ndarray]:
        tasks = []
        if reflection_weight > 0 and 'reflection' in self.config.task_heads:
            tasks.append('reflection')
        if derain_weight > 0 and 'derain' in self.config.task_heads:
            tasks.append('derain')
        if dehaze_weight > 0 and 'dehaze' in self.config.task_heads:
            tasks.append('dehaze')
        
        if not tasks:
            tasks = self.config.task_heads
        
        results = self.process(image, tasks)
        
        clean_images = []
        weights = []
        
        if 'reflection_transmission' in results and reflection_weight > 0:
            clean_images.append(results['reflection_transmission'].astype(np.float32))
            weights.append(reflection_weight)
        
        if 'derain_clean' in results and derain_weight > 0:
            clean_images.append(results['derain_clean'].astype(np.float32))
            weights.append(derain_weight)
        
        if 'dehaze_clean' in results and dehaze_weight > 0:
            clean_images.append(results['dehaze_clean'].astype(np.float32))
            weights.append(dehaze_weight)
        
        if clean_images:
            total_weight = sum(weights)
            fused = np.zeros_like(clean_images[0])
            for img, w in zip(clean_images, weights):
                fused += img * (w / total_weight)
            results['fused_clean'] = np.clip(fused, 0, 255).astype(np.uint8)
        
        return results
