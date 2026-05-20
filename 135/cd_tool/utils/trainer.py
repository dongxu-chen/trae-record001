import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import autocast, GradScaler
from typing import Optional, Dict, Tuple, Callable
import numpy as np
from tqdm import tqdm
from .metrics import Evaluator


class MixedPrecisionTrainer:
    def __init__(self,
                 model: nn.Module,
                 optimizer: optim.Optimizer,
                 scheduler: Optional[optim.lr_scheduler._LRScheduler] = None,
                 device: Optional[torch.device] = None,
                 use_amp: bool = True,
                 gradient_accumulation_steps: int = 1,
                 max_grad_norm: Optional[float] = 1.0,
                 boundary_loss_weight: float = 0.1,
                 num_classes: int = 1):
        
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = model.to(self.device)
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.use_amp = use_amp and self.device.type == 'cuda'
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.max_grad_norm = max_grad_norm
        self.boundary_loss_weight = boundary_loss_weight
        self.num_classes = num_classes
        
        self.scaler = GradScaler(enabled=self.use_amp)
        self.evaluator = Evaluator(num_classes=num_classes)
        
        self.current_step = 0
        self.current_epoch = 0

    def _compute_loss(self, 
                      logits: torch.Tensor, 
                      target: torch.Tensor,
                      valid_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        
        if valid_mask is not None:
            logits = logits * valid_mask
            target = target * valid_mask
        
        if self.num_classes == 1:
            loss = F.binary_cross_entropy_with_logits(logits, target.float())
        else:
            loss = F.cross_entropy(logits, target.long())
        
        return loss

    def train_epoch(self, 
                    dataloader: DataLoader,
                    epoch: int,
                    return_boundary: bool = False,
                    valid_mask_index: Optional[int] = None) -> Dict[str, float]:
        
        self.model.train()
        total_loss = 0.0
        total_seg_loss = 0.0
        total_boundary_loss = 0.0
        num_batches = len(dataloader)
        
        self.optimizer.zero_grad()
        
        pbar = tqdm(dataloader, desc=f'Epoch {epoch}')
        for batch_idx, data in enumerate(pbar):
            img1, img2 = data[0], data[1]
            target = data[2] if len(data) > 2 else None
            valid_mask = data[valid_mask_index] if valid_mask_index is not None else None
            
            img1 = img1.to(self.device)
            img2 = img2.to(self.device)
            if target is not None:
                target = target.to(self.device)
            if valid_mask is not None:
                valid_mask = valid_mask.to(self.device)
            
            x = torch.cat([img1, img2], dim=1)
            
            with autocast(enabled=self.use_amp):
                if return_boundary and hasattr(self.model, 'use_boundary_attention') and self.model.use_boundary_attention:
                    logits, pred_boundary = self.model(x, return_boundary=True)
                    seg_loss = self._compute_loss(logits, target, valid_mask)
                    boundary_loss = self.model.get_boundary_loss(pred_boundary, target, self.device)
                    loss = seg_loss + self.boundary_loss_weight * boundary_loss
                    total_boundary_loss += boundary_loss.item()
                else:
                    logits = self.model(x)
                    loss = self._compute_loss(logits, target, valid_mask)
                    seg_loss = loss
                
                loss = loss / self.gradient_accumulation_steps
            
            if self.use_amp:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()
            
            if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                if self.use_amp:
                    if self.max_grad_norm is not None:
                        self.scaler.unscale_(self.optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    if self.max_grad_norm is not None:
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                    self.optimizer.step()
                
                self.optimizer.zero_grad()
                self.current_step += 1
            
            total_loss += loss.item() * self.gradient_accumulation_steps
            total_seg_loss += seg_loss.item()
            
            pbar.set_postfix({
                'loss': f'{total_loss / (batch_idx + 1):.4f}',
                'seg_loss': f'{total_seg_loss / (batch_idx + 1):.4f}'
            })
        
        if self.scheduler is not None:
            self.scheduler.step()
        
        self.current_epoch += 1
        
        results = {
            'loss': total_loss / num_batches,
            'seg_loss': total_seg_loss / num_batches
        }
        if return_boundary:
            results['boundary_loss'] = total_boundary_loss / num_batches
        
        return results

    @torch.no_grad()
    def validate(self, 
                 dataloader: DataLoader,
                 valid_mask_index: Optional[int] = None) -> Dict[str, float]:
        
        self.model.eval()
        self.evaluator.reset()
        total_loss = 0.0
        num_batches = len(dataloader)
        
        for data in tqdm(dataloader, desc='Validating'):
            img1, img2 = data[0], data[1]
            target = data[2] if len(data) > 2 else None
            valid_mask = data[valid_mask_index] if valid_mask_index is not None else None
            
            img1 = img1.to(self.device)
            img2 = img2.to(self.device)
            if target is not None:
                target = target.to(self.device)
            if valid_mask is not None:
                valid_mask = valid_mask.to(self.device)
            
            x = torch.cat([img1, img2], dim=1)
            
            with autocast(enabled=self.use_amp):
                logits = self.model(x)
                loss = self._compute_loss(logits, target, valid_mask)
            
            total_loss += loss.item()
            
            if self.num_classes == 1:
                pred = torch.sigmoid(logits)
            else:
                pred = torch.softmax(logits, dim=1)
            
            self.evaluator.add_batch(pred, target)
        
        metrics = self.evaluator.get_metrics()
        metrics['loss'] = total_loss / num_batches
        
        return metrics

    def save_checkpoint(self, path: str, extra_state: Optional[Dict] = None):
        state = {
            'epoch': self.current_epoch,
            'step': self.current_step,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scaler_state_dict': self.scaler.state_dict() if self.use_amp else None,
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
        }
        if extra_state:
            state.update(extra_state)
        torch.save(state, path)

    def load_checkpoint(self, path: str, load_optimizer: bool = True, load_scheduler: bool = True):
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        if load_optimizer and 'optimizer_state_dict' in checkpoint:
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        if load_scheduler and self.scheduler and 'scheduler_state_dict' in checkpoint:
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        
        if self.use_amp and 'scaler_state_dict' in checkpoint and checkpoint['scaler_state_dict'] is not None:
            self.scaler.load_state_dict(checkpoint['scaler_state_dict'])
        
        self.current_epoch = checkpoint.get('epoch', 0)
        self.current_step = checkpoint.get('step', 0)
        
        return checkpoint


class DiceLoss(nn.Module):
    def __init__(self, smooth: float = 1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        inputs = torch.sigmoid(inputs)
        inputs = inputs.view(-1)
        targets = targets.view(-1)
        intersection = (inputs * targets).sum()
        dice = (2. * intersection + self.smooth) / (inputs.sum() + targets.sum() + self.smooth)
        return 1 - dice


class FocalLoss(nn.Module):
    def __init__(self, alpha: float = 0.8, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        pt = torch.exp(-bce)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * bce
        return focal_loss.mean()


class CombinedLoss(nn.Module):
    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5, focal_weight: float = 0.0):
        super().__init__()
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight
        self.focal_weight = focal_weight
        self.dice_loss = DiceLoss()
        self.focal_loss = FocalLoss()

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(inputs, targets)
        dice = self.dice_loss(inputs, targets)
        focal = self.focal_loss(inputs, targets)
        
        total_loss = (self.bce_weight * bce + 
                      self.dice_weight * dice + 
                      self.focal_weight * focal)
        return total_loss
