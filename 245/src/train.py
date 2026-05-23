import os
import sys
import argparse
import time
import torch
import torch.nn as nn
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dataset import get_dataloaders
from src.model import create_model, get_loss_function, get_optimizer, get_scheduler
from src.utils import (
    calculate_psnr, calculate_ssim, AverageMeter,
    save_checkpoint, load_checkpoint, create_dirs
)


def train_one_epoch(model, train_loader, criterion, optimizer, device, epoch, writer):
    model.train()
    
    losses = AverageMeter()
    
    pbar = tqdm(train_loader, desc=f"Epoch {epoch}")
    for i, (lr_imgs, hr_imgs) in enumerate(pbar):
        lr_imgs = lr_imgs.to(device)
        hr_imgs = hr_imgs.to(device)
        
        optimizer.zero_grad()
        
        sr_imgs = model(lr_imgs)
        
        loss = criterion(sr_imgs, hr_imgs)
        
        loss.backward()
        optimizer.step()
        
        losses.update(loss.item(), lr_imgs.size(0))
        
        pbar.set_postfix({'Loss': f'{losses.avg:.6f}'})
        
        if writer is not None:
            global_step = epoch * len(train_loader) + i
            writer.add_scalar('Train/Loss', loss.item(), global_step)
    
    return losses.avg


def validate(model, val_loader, device, epoch=None, writer=None):
    model.eval()
    
    psnrs = AverageMeter()
    ssims = AverageMeter()
    
    with torch.no_grad():
        for i, (lr_imgs, hr_imgs) in enumerate(tqdm(val_loader, desc="Validation")):
            lr_imgs = lr_imgs.to(device)
            hr_imgs = hr_imgs.to(device)
            
            sr_imgs = model(lr_imgs)
            
            sr_imgs = torch.clamp(sr_imgs, 0, 1)
            
            psnr = calculate_psnr(sr_imgs, hr_imgs, crop_border=4)
            ssim = calculate_ssim(sr_imgs, hr_imgs, crop_border=4)
            
            psnrs.update(psnr, lr_imgs.size(0))
            ssims.update(ssim, lr_imgs.size(0))
    
    if writer is not None and epoch is not None:
        writer.add_scalar('Val/PSNR', psnrs.avg, epoch)
        writer.add_scalar('Val/SSIM', ssims.avg, epoch)
    
    return psnrs.avg, ssims.avg


def train(config):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    create_dirs([config['model_save_dir'], config['log_dir'], config['result_dir']])
    
    train_loader, val_loader = get_dataloaders(config)
    print(f"Train dataset size: {len(train_loader.dataset)}")
    print(f"Val dataset size: {len(val_loader.dataset)}")
    
    model = create_model(config)
    model = model.to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {total_params:,}")
    
    criterion = get_loss_function(config)
    optimizer = get_optimizer(model, config)
    scheduler = get_scheduler(optimizer, config)
    
    start_epoch = 0
    best_psnr = 0
    best_ssim = 0
    
    if config.get('resume', False) and config.get('checkpoint_path', None):
        model, optimizer, start_epoch, best_psnr, best_ssim = load_checkpoint(
            model, config['checkpoint_path'], optimizer, device
        )
    
    writer = SummaryWriter(config['log_dir']) if config.get('use_tensorboard', True) else None
    
    print(f"Start training from epoch {start_epoch + 1}")
    print(f"Total epochs: {config['num_epochs']}")
    
    for epoch in range(start_epoch + 1, config['num_epochs'] + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch, writer)
        
        val_psnr, val_ssim = validate(model, val_loader, device, epoch, writer)
        
        if scheduler is not None:
            scheduler.step()
        
        print(f"Epoch {epoch}/{config['num_epochs']} - "
              f"Train Loss: {train_loss:.6f} - "
              f"Val PSNR: {val_psnr:.4f} - "
              f"Val SSIM: {val_ssim:.4f}")
        
        if val_psnr > best_psnr:
            best_psnr = val_psnr
            best_ssim = val_ssim
            best_model_path = os.path.join(config['model_save_dir'], 'best_model.pth')
            save_checkpoint(model, optimizer, epoch, best_psnr, best_ssim, best_model_path)
            print(f"Best model saved! PSNR: {best_psnr:.4f}, SSIM: {best_ssim:.4f}")
        
        if epoch % config.get('save_interval', 10) == 0:
            model_path = os.path.join(config['model_save_dir'], f'model_epoch_{epoch}.pth')
            save_checkpoint(model, optimizer, epoch, val_psnr, val_ssim, model_path)
        
        print(f"Best - PSNR: {best_psnr:.4f}, SSIM: {best_ssim:.4f}")
        print("-" * 80)
    
    if writer is not None:
        writer.close()
    
    print("Training completed!")
    print(f"Best results - PSNR: {best_psnr:.4f}, SSIM: {best_ssim:.4f}")


def main():
    parser = argparse.ArgumentParser(description='RCAN Training for Infrared Image Super-Resolution')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    train(config)


if __name__ == '__main__':
    main()
