import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from typing import Dict
import time

from config import Config
from data import create_dataloaders, get_image_paths
from models import build_model
from utils import calculate_psnr, calculate_ssim, AverageMeter


class CombinedLoss(nn.Module):
    def __init__(self, alpha: float = 0.8):
        super(CombinedLoss, self).__init__()
        self.mse_loss = nn.MSELoss()
        self.l1_loss = nn.L1Loss()
        self.alpha = alpha

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        mse = self.mse_loss(pred, target)
        l1 = self.l1_loss(pred, target)
        return self.alpha * mse + (1 - self.alpha) * l1


def train_one_epoch(model: nn.Module, 
                    train_loader: DataLoader, 
                    criterion: nn.Module, 
                    optimizer: optim.Optimizer, 
                    device: torch.device) -> Dict[str, float]:
    model.train()
    
    losses = AverageMeter()
    psnrs = AverageMeter()
    ssims = AverageMeter()
    
    for batch_idx, (rainy_imgs, clean_imgs, _) in enumerate(train_loader):
        rainy_imgs = rainy_imgs.permute(0, 3, 1, 2).float().to(device)
        clean_imgs = clean_imgs.permute(0, 3, 1, 2).float().to(device)
        
        optimizer.zero_grad()
        
        outputs = model(rainy_imgs)
        
        loss = criterion(outputs, clean_imgs)
        
        loss.backward()
        optimizer.step()
        
        batch_size = rainy_imgs.size(0)
        losses.update(loss.item(), batch_size)
        
        with torch.no_grad():
            psnr = calculate_psnr(outputs, clean_imgs)
            ssim = calculate_ssim(outputs, clean_imgs)
            psnrs.update(psnr, batch_size)
            ssims.update(ssim, batch_size)
    
    return {
        'loss': losses.avg,
        'psnr': psnrs.avg,
        'ssim': ssims.avg
    }


def validate(model: nn.Module, 
             val_loader: DataLoader, 
             criterion: nn.Module, 
             device: torch.device) -> Dict[str, float]:
    model.eval()
    
    losses = AverageMeter()
    psnrs = AverageMeter()
    ssims = AverageMeter()
    
    intensity_metrics = {}
    
    with torch.no_grad():
        for batch_idx, (rainy_imgs, clean_imgs, intensities) in enumerate(val_loader):
            rainy_imgs = rainy_imgs.permute(0, 3, 1, 2).float().to(device)
            clean_imgs = clean_imgs.permute(0, 3, 1, 2).float().to(device)
            
            outputs = model(rainy_imgs)
            loss = criterion(outputs, clean_imgs)
            
            batch_size = rainy_imgs.size(0)
            losses.update(loss.item(), batch_size)
            
            psnr = calculate_psnr(outputs, clean_imgs)
            ssim = calculate_ssim(outputs, clean_imgs)
            psnrs.update(psnr, batch_size)
            ssims.update(ssim, batch_size)
            
            for i, intensity in enumerate(intensities):
                if intensity not in intensity_metrics:
                    intensity_metrics[intensity] = {'psnr': [], 'ssim': []}
                intensity_metrics[intensity]['psnr'].append(calculate_psnr(outputs[i:i+1], clean_imgs[i:i+1]))
                intensity_metrics[intensity]['ssim'].append(calculate_ssim(outputs[i:i+1], clean_imgs[i:i+1]))
    
    intensity_results = {}
    for intensity, metrics in intensity_metrics.items():
        intensity_results[intensity] = {
            'psnr': np.mean(metrics['psnr']),
            'ssim': np.mean(metrics['ssim']),
            'count': len(metrics['psnr'])
        }
    
    return {
        'loss': losses.avg,
        'psnr': psnrs.avg,
        'ssim': ssims.avg,
        'intensity_metrics': intensity_results
    }


def save_checkpoint(model: nn.Module, 
                    optimizer: optim.Optimizer, 
                    epoch: int, 
                    metrics: Dict[str, float], 
                    save_dir: str):
    os.makedirs(save_dir, exist_ok=True)
    
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'metrics': metrics
    }
    
    checkpoint_path = os.path.join(save_dir, f'checkpoint_epoch_{epoch}.pth')
    torch.save(checkpoint, checkpoint_path)
    
    best_path = os.path.join(save_dir, 'best_model.pth')
    torch.save(checkpoint, best_path)
    
    print(f"Checkpoint saved: {checkpoint_path}")


def load_checkpoint(model: nn.Module, 
                    optimizer: optim.Optimizer, 
                    checkpoint_path: str) -> tuple:
    checkpoint = torch.load(checkpoint_path, map_location=Config.DEVICE)
    model.load_state_dict(checkpoint['model_state_dict'])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    epoch = checkpoint['epoch']
    metrics = checkpoint['metrics']
    return model, optimizer, epoch, metrics


def main():
    device = Config.DEVICE
    print(f"Using device: {device}")
    
    train_paths = get_image_paths(Config.TRAIN_DATA_DIR)
    test_paths = get_image_paths(Config.TEST_DATA_DIR)
    
    print(f"Found {len(train_paths)} training images")
    print(f"Found {len(test_paths)} test images")
    
    if len(train_paths) == 0:
        print("Warning: No training images found. Using synthetic data generation.")
    
    train_loader, val_loader = create_dataloaders(
        Config.TRAIN_DATA_DIR, 
        Config.TEST_DATA_DIR, 
        Config.BATCH_SIZE
    )
    
    model = build_model('resnet')
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")
    
    criterion = CombinedLoss(alpha=0.8)
    optimizer = optim.Adam(model.parameters(), lr=Config.LEARNING_RATE)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=Config.NUM_EPOCHS)
    
    best_psnr = 0
    
    print("Starting training...")
    for epoch in range(Config.NUM_EPOCHS):
        start_time = time.time()
        
        train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_metrics = validate(model, val_loader, criterion, device)
        
        scheduler.step()
        
        elapsed = time.time() - start_time
        
        print(f"\nEpoch [{epoch+1}/{Config.NUM_EPOCHS}] - Time: {elapsed:.2f}s")
        print(f"  Train - Loss: {train_metrics['loss']:.4f}, PSNR: {train_metrics['psnr']:.2f}, SSIM: {train_metrics['ssim']:.4f}")
        print(f"  Val   - Loss: {val_metrics['loss']:.4f}, PSNR: {val_metrics['psnr']:.2f}, SSIM: {val_metrics['ssim']:.4f}")
        
        if 'intensity_metrics' in val_metrics:
            print("  Intensity breakdown:")
            for intensity, metrics in val_metrics['intensity_metrics'].items():
                print(f"    {intensity:8s} - PSNR: {metrics['psnr']:.2f}, SSIM: {metrics['ssim']:.4f}, Count: {metrics['count']}")
        
        if val_metrics['psnr'] > best_psnr:
            best_psnr = val_metrics['psnr']
            save_checkpoint(model, optimizer, epoch + 1, val_metrics, Config.CHECKPOINT_DIR)
            print(f"  New best model! PSNR: {best_psnr:.2f}")
    
    print("\nTraining completed!")
    print(f"Best PSNR: {best_psnr:.2f}")


if __name__ == '__main__':
    main()
