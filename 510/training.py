import os
import math
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.utils.data as data
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as compare_psnr
from skimage.metrics import structural_similarity as compare_ssim

from models import VESPCN, create_vespcn_model, initialize_weights

logger = logging.getLogger(__name__)


class PerceptualLoss(nn.Module):

    def __init__(self):
        super().__init__()
        self.vgg = None
        self.register_buffer('mean', torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer('std', torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))
        self._build_vgg()

    def _build_vgg(self):
        try:
            from torchvision.models import vgg19, VGG19_Weights
            vgg = vgg19(weights=VGG19_Weights.DEFAULT)
            self.vgg = nn.Sequential(*list(vgg.features[:18]))
            for param in self.vgg.parameters():
                param.requires_grad = False
            self.vgg.eval()
        except Exception:
            self.vgg = None

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if self.vgg is None:
            return torch.tensor(0.0, device=pred.device, requires_grad=False)

        mean = self.mean.to(pred.device)
        std = self.std.to(pred.device)

        pred_norm = (pred - mean) / std
        target_norm = (target - mean) / std

        self.vgg = self.vgg.to(pred.device)
        with torch.no_grad():
            target_feat = self.vgg(target_norm)

        pred_feat = self.vgg(pred_norm)

        return F.l1_loss(pred_feat, target_feat.detach())


class JointLoss(nn.Module):

    def __init__(self, interp_weight: float = 0.5, sr_weight: float = 0.5,
                 temporal_weight: float = 0.1, flow_weight: float = 0.05,
                 perceptual_weight: float = 0.1):
        super().__init__()
        self.interp_weight = interp_weight
        self.sr_weight = sr_weight
        self.temporal_weight = temporal_weight
        self.flow_weight = flow_weight
        self.perceptual_weight = perceptual_weight
        self.perceptual_loss = PerceptualLoss()

    def set_weights(self, interp_weight: float = None, sr_weight: float = None,
                    temporal_weight: float = None, flow_weight: float = None,
                    perceptual_weight: float = None):
        if interp_weight is not None:
            self.interp_weight = interp_weight
        if sr_weight is not None:
            self.sr_weight = sr_weight
        if temporal_weight is not None:
            self.temporal_weight = temporal_weight
        if flow_weight is not None:
            self.flow_weight = flow_weight
        if perceptual_weight is not None:
            self.perceptual_weight = perceptual_weight

    def _interp_loss(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        return F.l1_loss(pred, target)

    def _sr_loss(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        l1 = F.l1_loss(pred, target)
        perceptual = self.perceptual_loss(pred, target)
        return l1 + self.perceptual_weight * perceptual

    def _temporal_consistency_loss(self, interp_frame: torch.Tensor,
                                   prev_frame: torch.Tensor,
                                   next_frame: torch.Tensor,
                                   flow: torch.Tensor,
                                   motion_compensation: nn.Module) -> torch.Tensor:
        half_flow = flow * 0.5
        prev_warped = motion_compensation(prev_frame, half_flow)
        next_warped = motion_compensation(next_frame, -half_flow)
        mid_estimate = (prev_warped + next_warped) / 2.0
        return F.l1_loss(interp_frame, mid_estimate.detach())

    def _flow_smoothness_loss(self, flow: torch.Tensor) -> torch.Tensor:
        dx = flow[:, :, :, 1:] - flow[:, :, :, :-1]
        dy = flow[:, :, 1:, :] - flow[:, :, :-1, :]
        return dx.abs().mean() + dy.abs().mean()

    def forward(self, interp_pred: torch.Tensor, interp_target: torch.Tensor,
                sr_pred: torch.Tensor, sr_target: torch.Tensor,
                flow: torch.Tensor, prev_frame: torch.Tensor,
                next_frame: torch.Tensor,
                motion_compensation: nn.Module = None) -> Tuple[torch.Tensor, Dict[str, float]]:

        loss_interp = self._interp_loss(interp_pred, interp_target)
        loss_sr = self._sr_loss(sr_pred, sr_target)

        loss_temporal = torch.tensor(0.0, device=interp_pred.device)
        if motion_compensation is not None and self.temporal_weight > 0:
            loss_temporal = self._temporal_consistency_loss(
                interp_pred, prev_frame, next_frame, flow, motion_compensation
            )

        loss_flow = torch.tensor(0.0, device=flow.device)
        if self.flow_weight > 0:
            loss_flow = self._flow_smoothness_loss(flow)

        total = (self.interp_weight * loss_interp +
                 self.sr_weight * loss_sr +
                 self.temporal_weight * loss_temporal +
                 self.flow_weight * loss_flow)

        details = {
            'interp_loss': loss_interp.item(),
            'sr_loss': loss_sr.item(),
            'temporal_loss': loss_temporal.item(),
            'flow_loss': loss_flow.item(),
            'total_loss': total.item(),
        }

        return total, details


class VideoDataset(data.Dataset):

    def __init__(self, frame_dir: str, scale_factor: int = 2,
                 patch_size: int = 64, mode: str = 'train'):
        super().__init__()
        self.frame_dir = Path(frame_dir)
        self.scale_factor = scale_factor
        self.patch_size = patch_size
        self.mode = mode

        extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']
        self.frame_paths = []
        for ext in extensions:
            self.frame_paths.extend(sorted(self.frame_dir.glob(ext)))

        self.pairs = []
        for i in range(len(self.frame_paths) - 2):
            self.pairs.append((i, i + 1, i + 2))

    def __len__(self) -> int:
        return len(self.pairs)

    def _load_frame(self, path: Path) -> np.ndarray:
        img = Image.open(path).convert('RGB')
        return np.array(img, dtype=np.float32)

    def _augment(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        if self.mode != 'train':
            return frames

        h, w = frames[0].shape[:2]
        ps = self.patch_size

        if h > ps and w > ps:
            top = np.random.randint(0, h - ps)
            left = np.random.randint(0, w - ps)
            frames = [f[top:top + ps, left:left + ps] for f in frames]
        elif h < ps or w < ps:
            new_h = max(h, ps)
            new_w = max(w, ps)
            frames = [np.array(Image.fromarray(f.astype(np.uint8)).resize(
                (new_w, new_h), Image.BICUBIC), dtype=np.float32) for f in frames]

        if np.random.random() > 0.5:
            frames = [np.flip(f, axis=1).copy() for f in frames]
        if np.random.random() > 0.5:
            frames = [np.flip(f, axis=0).copy() for f in frames]

        return frames

    def _to_lr(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        lr_h = h // self.scale_factor
        lr_w = w // self.scale_factor
        if lr_h < 1 or lr_w < 1:
            return frame
        return np.array(
            Image.fromarray(frame.astype(np.uint8)).resize(
                (lr_w, lr_h), Image.BICUBIC
            ), dtype=np.float32
        )

    def _to_tensor(self, frame: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(frame.transpose(2, 0, 1) / 255.0)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, ...]:
        i0, i1, i2 = self.pairs[idx]

        frame0 = self._load_frame(self.frame_paths[i0])
        frame1 = self._load_frame(self.frame_paths[i1])
        frame2 = self._load_frame(self.frame_paths[i2])

        frame0, frame1, frame2 = self._augment([frame0, frame1, frame2])

        hr_frame1 = self._to_tensor(frame1)

        lr_frame0 = self._to_tensor(self._to_lr(frame0))
        lr_frame1 = self._to_tensor(self._to_lr(frame1))
        lr_frame2 = self._to_tensor(self._to_lr(frame2))

        return lr_frame0, lr_frame2, lr_frame1, hr_frame1


class Trainer:

    def __init__(self, model: VESPCN, train_loader: data.DataLoader,
                 val_loader: data.DataLoader, config: dict = None):
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader

        default_config = {
            'lr': 1e-4,
            'epochs': 100,
            'batch_size': 4,
            'interp_weight': 0.5,
            'sr_weight': 0.5,
            'temporal_weight': 0.1,
            'flow_weight': 0.05,
            'perceptual_weight': 0.1,
            'grad_clip': 0.5,
            'checkpoint_dir': 'checkpoints',
            'lr_scheduler': 'cosine',
            'lr_step_size': 30,
            'lr_gamma': 0.5,
        }
        if config:
            default_config.update(config)
        self.config = default_config

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)

        self.joint_loss = JointLoss(
            interp_weight=self.config['interp_weight'],
            sr_weight=self.config['sr_weight'],
            temporal_weight=self.config['temporal_weight'],
            flow_weight=self.config['flow_weight'],
            perceptual_weight=self.config['perceptual_weight'],
        ).to(self.device)

        self.optimizer = torch.optim.Adam(
            self.model.parameters(), lr=self.config['lr']
        )
        self._setup_scheduler()

        self.use_amp = torch.cuda.is_available()
        self.scaler = torch.cuda.amp.GradScaler(enabled=self.use_amp)

        self.current_epoch = 0
        self.history = {
            'train_loss': [],
            'val_psnr': [],
            'val_ssim': [],
            'lr': [],
            'loss_details': [],
        }

        self.checkpoint_dir = Path(self.config['checkpoint_dir'])
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.best_psnr = 0.0

    def _setup_scheduler(self):
        scheduler_type = self.config.get('lr_scheduler', 'cosine')
        if scheduler_type == 'step':
            self.scheduler = torch.optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=self.config.get('lr_step_size', 30),
                gamma=self.config.get('lr_gamma', 0.5)
            )
        elif scheduler_type == 'cosine':
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer,
                T_max=self.config['epochs'],
                eta_min=1e-7
            )
        elif scheduler_type == 'multistep':
            self.scheduler = torch.optim.lr_scheduler.MultiStepLR(
                self.optimizer,
                milestones=[50, 80],
                gamma=self.config.get('lr_gamma', 0.5)
            )
        else:
            self.scheduler = None

    def set_quality_weight(self, quality_weight: float):
        quality_weight = max(0.0, min(1.0, quality_weight))
        self.model.set_quality_weight(quality_weight)
        interp_w = quality_weight
        sr_w = 1.0 - quality_weight
        self.joint_loss.set_weights(interp_weight=interp_w, sr_weight=sr_w)

    def train_epoch(self) -> Tuple[float, Dict[str, float]]:
        self.model.train()
        total_loss = 0.0
        accumulated_details = {
            'interp_loss': 0.0,
            'sr_loss': 0.0,
            'temporal_loss': 0.0,
            'flow_loss': 0.0,
        }
        num_batches = 0

        for batch in self.train_loader:
            lr_prev, lr_next, lr_middle, hr_middle = batch
            lr_prev = lr_prev.to(self.device)
            lr_next = lr_next.to(self.device)
            lr_middle = lr_middle.to(self.device)
            hr_middle = hr_middle.to(self.device)

            with torch.cuda.amp.autocast(enabled=self.use_amp):
                flow = self.model.motion_estimation(lr_prev, lr_next)

                interp_frame = self.model.interpolate_frame(lr_prev, lr_next)

                sr_frame = self.model.enhance_resolution(interp_frame)

                loss, details = self.joint_loss(
                    interp_pred=interp_frame,
                    interp_target=lr_middle,
                    sr_pred=sr_frame,
                    sr_target=hr_middle,
                    flow=flow,
                    prev_frame=lr_prev,
                    next_frame=lr_next,
                    motion_compensation=self.model.motion_compensation,
                )

            self.optimizer.zero_grad()
            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config.get('grad_clip', 0.5)
            )
            self.scaler.step(self.optimizer)
            self.scaler.update()

            total_loss += details['total_loss']
            for k in accumulated_details:
                accumulated_details[k] += details.get(k, 0.0)
            num_batches += 1

        avg_loss = total_loss / max(num_batches, 1)
        for k in accumulated_details:
            accumulated_details[k] /= max(num_batches, 1)

        return avg_loss, accumulated_details

    @torch.no_grad()
    def validate(self) -> Tuple[float, float]:
        self.model.eval()
        total_psnr = 0.0
        total_ssim = 0.0
        num_samples = 0

        for batch in self.val_loader:
            lr_prev, lr_next, lr_middle, hr_middle = batch
            lr_prev = lr_prev.to(self.device)
            lr_next = lr_next.to(self.device)
            hr_middle = hr_middle.to(self.device)

            interp_frame = self.model.interpolate_frame(lr_prev, lr_next)
            sr_frame = self.model.enhance_resolution(interp_frame)

            sr_np = sr_frame.clamp(0, 1).cpu().numpy()
            hr_np = hr_middle.cpu().numpy()

            for b in range(sr_np.shape[0]):
                pred_img = sr_np[b].transpose(1, 2, 0)
                gt_img = hr_np[b].transpose(1, 2, 0)

                if pred_img.shape == gt_img.shape:
                    p = compare_psnr(gt_img, pred_img, data_range=1.0)
                    s = compare_ssim(gt_img, pred_img, data_range=1.0, channel_axis=2)
                    total_psnr += p
                    total_ssim += s
                num_samples += 1

        avg_psnr = total_psnr / max(num_samples, 1)
        avg_ssim = total_ssim / max(num_samples, 1)

        return avg_psnr, avg_ssim

    def train(self):
        logger.info("Starting training for %d epochs on device: %s",
                     self.config['epochs'], self.device)

        for epoch in range(self.current_epoch, self.config['epochs']):
            self.current_epoch = epoch
            epoch_start = time.time()

            train_loss, loss_details = self.train_epoch()

            val_psnr, val_ssim = self.validate()

            current_lr = self.optimizer.param_groups[0]['lr']

            self.history['train_loss'].append(train_loss)
            self.history['val_psnr'].append(val_psnr)
            self.history['val_ssim'].append(val_ssim)
            self.history['lr'].append(current_lr)
            self.history['loss_details'].append(loss_details)

            elapsed = time.time() - epoch_start

            logger.info(
                "Epoch %d/%d | Loss: %.6f | PSNR: %.2f dB | SSIM: %.4f | "
                "LR: %.2e | Time: %.1fs",
                epoch + 1, self.config['epochs'], train_loss,
                val_psnr, val_ssim, current_lr, elapsed
            )

            if val_psnr > self.best_psnr:
                self.best_psnr = val_psnr
                self.save_checkpoint(is_best=True)
                logger.info("New best PSNR: %.2f dB", val_psnr)

            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(
                    is_best=False,
                    filename='checkpoint_epoch_%d.pth' % (epoch + 1)
                )

            if self.scheduler:
                self.scheduler.step()

        logger.info("Training complete. Best PSNR: %.2f dB", self.best_psnr)

    def save_checkpoint(self, is_best: bool = False, filename: str = None):
        state = {
            'epoch': self.current_epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scaler_state_dict': self.scaler.state_dict(),
            'best_psnr': self.best_psnr,
            'history': self.history,
            'config': self.config,
        }

        if is_best:
            path = self.checkpoint_dir / 'best_model.pth'
        else:
            path = self.checkpoint_dir / (filename or 'checkpoint_epoch_%d.pth' % (self.current_epoch + 1))

        torch.save(state, str(path))
        logger.info("Checkpoint saved: %s", path)

    def load_checkpoint(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

        if 'scaler_state_dict' in checkpoint:
            self.scaler.load_state_dict(checkpoint['scaler_state_dict'])

        self.current_epoch = checkpoint.get('epoch', 0) + 1
        self.best_psnr = checkpoint.get('best_psnr', 0.0)

        if 'history' in checkpoint:
            self.history = checkpoint['history']

        if 'config' in checkpoint:
            self.config.update(checkpoint['config'])

        logger.info("Checkpoint loaded: %s, resuming from epoch %d", path, self.current_epoch)

    def get_training_history(self) -> Dict[str, List]:
        return {
            'train_loss': list(self.history['train_loss']),
            'val_psnr': list(self.history['val_psnr']),
            'val_ssim': list(self.history['val_ssim']),
            'lr': list(self.history['lr']),
        }


def create_trainer(model: VESPCN = None, train_dir: str = None,
                   val_dir: str = None, config: dict = None) -> Trainer:
    default_config = {
        'lr': 1e-4,
        'epochs': 100,
        'batch_size': 4,
        'interp_weight': 0.5,
        'sr_weight': 0.5,
        'temporal_weight': 0.1,
        'flow_weight': 0.05,
        'perceptual_weight': 0.1,
        'grad_clip': 0.5,
        'scale_factor': 2,
        'patch_size': 64,
        'num_workers': 4,
        'checkpoint_dir': 'checkpoints',
        'lr_scheduler': 'cosine',
    }
    if config:
        default_config.update(config)

    if model is None:
        model = create_vespcn_model(
            scale_factor=default_config['scale_factor'],
            device='cpu',
        )
        model.apply(initialize_weights)

    scale_factor = default_config['scale_factor']
    patch_size = default_config['patch_size']

    train_dataset = VideoDataset(
        train_dir, scale_factor=scale_factor,
        patch_size=patch_size, mode='train'
    )
    val_dataset = VideoDataset(
        val_dir, scale_factor=scale_factor,
        patch_size=patch_size, mode='val'
    )

    train_loader = data.DataLoader(
        train_dataset,
        batch_size=default_config['batch_size'],
        shuffle=True,
        num_workers=default_config['num_workers'],
        pin_memory=torch.cuda.is_available(),
        drop_last=True,
    )
    val_loader = data.DataLoader(
        val_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=default_config['num_workers'],
        pin_memory=torch.cuda.is_available(),
    )

    trainer = Trainer(model, train_loader, val_loader, default_config)
    return trainer
