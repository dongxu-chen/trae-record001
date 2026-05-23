import os
import argparse
import yaml
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import numpy as np
from PIL import Image
from torchvision import transforms

from models import ESPCN, BatchDegradationWrapper
from models.rrdb import SmallRRDBTeacher
from data import get_train_loader, get_valid_loader
from utils.metrics import calculate_psnr, calculate_ssim, AverageMeter


def parse_args():
    parser = argparse.ArgumentParser(description='Train ESPCN with Real-ESRGAN Degradation')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--scale', type=int, default=None, help='Scale factor (2 or 4)')
    parser.add_argument('--resume', type=str, default=None, help='Path to resume checkpoint')
    parser.add_argument('--use_teacher', action='store_true', help='Use teacher model for perceptual loss')
    parser.add_argument('--teacher_checkpoint', type=str, default=None, help='Path to teacher model checkpoint')
    parser.add_argument('--perceptual_weight', type=float, default=0.1, help='Perceptual loss weight')
    return parser.parse_args()


def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


class PerceptualLoss(nn.Module):
    def __init__(self, teacher_model, weight=0.1):
        super(PerceptualLoss, self).__init__()
        self.teacher_model = teacher_model
        self.weight = weight
        self.mse_loss = nn.MSELoss()
    
    def forward(self, pred, target):
        mse = self.mse_loss(pred, target)
        
        with torch.no_grad():
            teacher_feat = self.teacher_model(target)
        
        perceptual = self.mse_loss(pred, teacher_feat)
        
        total_loss = mse + self.weight * perceptual
        
        return total_loss, mse, perceptual


def train_one_epoch_realesrgan(model, train_loader, degrader, criterion, 
                              optimizer, device, epoch, writer):
    model.train()
    loss_meter = AverageMeter()
    mse_meter = AverageMeter()
    perceptual_meter = AverageMeter()
    
    pbar = tqdm(train_loader, desc=f'Epoch {epoch} [Real-ESRGAN]')
    for i, (_, hr_imgs) in enumerate(pbar):
        hr_imgs = hr_imgs.to(device)
        
        lr_imgs = degrader(hr_imgs).to(device)
        
        optimizer.zero_grad()
        sr_imgs = model(lr_imgs)
        
        if hasattr(criterion, 'teacher_model'):
            loss, mse, perceptual = criterion(sr_imgs, hr_imgs)
            mse_meter.update(mse.item(), hr_imgs.size(0))
            perceptual_meter.update(perceptual.item(), hr_imgs.size(0))
        else:
            loss = criterion(sr_imgs, hr_imgs)
            mse_meter.update(loss.item(), hr_imgs.size(0))
        
        loss.backward()
        optimizer.step()
        
        loss_meter.update(loss.item(), hr_imgs.size(0))
        
        if hasattr(criterion, 'teacher_model'):
            pbar.set_postfix({
                'loss': f'{loss_meter.avg:.6f}',
                'mse': f'{mse_meter.avg:.6f}',
                'percep': f'{perceptual_meter.avg:.6f}'
            })
        else:
            pbar.set_postfix({'loss': f'{loss_meter.avg:.6f}'})
        
        if writer is not None and i % 100 == 0:
            global_step = epoch * len(train_loader) + i
            writer.add_scalar('RealESRGAN/Total_loss', loss.item(), global_step)
            writer.add_scalar('RealESRGAN/MSE_loss', mse_meter.val, global_step)
            if hasattr(criterion, 'teacher_model'):
                writer.add_scalar('RealESRGAN/Perceptual_loss', perceptual_meter.val, global_step)
    
    return loss_meter.avg


def validate_realesrgan(model, valid_loader, degrader, device, scale_factor, writer=None, epoch=None):
    model.eval()
    psnr_meter = AverageMeter()
    ssim_meter = AverageMeter()
    
    with torch.no_grad():
        for _, hr_imgs in tqdm(valid_loader, desc='Validation [Real-ESRGAN]'):
            hr_imgs = hr_imgs.to(device)
            
            lr_imgs = degrader(hr_imgs).to(device)
            sr_imgs = model(lr_imgs)
            
            psnr = calculate_psnr(sr_imgs, hr_imgs, crop_border=scale_factor)
            ssim = calculate_ssim(sr_imgs, hr_imgs, crop_border=scale_factor)
            
            psnr_meter.update(psnr, hr_imgs.size(0))
            ssim_meter.update(ssim, hr_imgs.size(0))
    
    if writer is not None and epoch is not None:
        writer.add_scalar('RealESRGAN/PSNR', psnr_meter.avg, epoch)
        writer.add_scalar('RealESRGAN/SSIM', ssim_meter.avg, epoch)
    
    return psnr_meter.avg, ssim_meter.avg


def main():
    args = parse_args()
    config = load_config(args.config)
    
    if args.scale is not None:
        config['model']['scale_factor'] = args.scale
    
    scale_factor = config['model']['scale_factor']
    batch_size = config['training']['batch_size']
    num_epochs = config['training']['num_epochs']
    lr = config['training']['learning_rate']
    lr_decay_step = config['training']['lr_decay_step']
    lr_decay_gamma = config['training']['lr_decay_gamma']
    weight_decay = config['training']['weight_decay']
    
    patch_size = config['data']['patch_size']
    num_workers = config['data']['num_workers']
    train_dir = config['data']['div2k_train_dir']
    valid_dir = config['data']['div2k_valid_dir']
    
    checkpoint_dir = config['output']['checkpoint_dir']
    log_dir = config['output']['log_dir']
    
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')
    
    degrader = BatchDegradationWrapper(scale=scale_factor)
    print('Real-ESRGAN degradation model initialized')
    
    model = ESPCN(
        scale_factor=scale_factor,
        num_channels=config['model']['num_channels'],
        num_features=config['model']['num_features']
    ).to(device)
    
    print(f'Model parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad) / 1000:.2f}K')
    
    if args.use_teacher and args.teacher_checkpoint:
        print(f'Loading teacher model from {args.teacher_checkpoint}')
        teacher_model = SmallRRDBTeacher(scale=scale_factor, num_feat=48, num_block=6).to(device)
        teacher_checkpoint = torch.load(args.teacher_checkpoint, map_location=device)
        if 'model_state_dict' in teacher_checkpoint:
            teacher_model.load_state_dict(teacher_checkpoint['model_state_dict'])
        else:
            teacher_model.load_state_dict(teacher_checkpoint)
        teacher_model.eval()
        
        criterion = PerceptualLoss(teacher_model, weight=args.perceptual_weight)
        print(f'Using perceptual loss with weight {args.perceptual_weight}')
    else:
        criterion = nn.MSELoss()
        print('Using MSE loss')
    
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=lr_decay_step, gamma=lr_decay_gamma)
    
    start_epoch = 1
    best_psnr = 0.0
    
    if args.resume and os.path.exists(args.resume):
        checkpoint = torch.load(args.resume, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_psnr = checkpoint['best_psnr']
        print(f'Resumed from epoch {start_epoch}, best PSNR: {best_psnr:.2f}')
    
    if os.path.exists(train_dir) and os.path.exists(valid_dir):
        train_loader = get_train_loader(
            train_dir, scale_factor, patch_size, batch_size, num_workers
        )
        valid_loader = get_valid_loader(
            valid_dir, scale_factor, batch_size=1, num_workers=num_workers
        )
    else:
        print('WARNING: Dataset not found. Please download DIV2K dataset first.')
        return
    
    writer = SummaryWriter(os.path.join(log_dir, f'espcn_x{scale_factor}_realesrgan'))
    
    for epoch in range(start_epoch, num_epochs + 1):
        print(f'\nEpoch {epoch}/{num_epochs}')
        print(f'Learning rate: {optimizer.param_groups[0]["lr"]:.6f}')
        
        train_loss = train_one_epoch_realesrgan(
            model, train_loader, degrader, criterion, 
            optimizer, device, epoch, writer
        )
        psnr, ssim = validate_realesrgan(
            model, valid_loader, degrader, device, scale_factor, writer, epoch
        )
        
        scheduler.step()
        
        print(f'Train Loss: {train_loss:.6f}')
        print(f'Valid PSNR: {psnr:.2f} dB, SSIM: {ssim:.4f}')
        
        checkpoint_path = os.path.join(checkpoint_dir, f'espcn_x{scale_factor}_realesrgan_latest.pth')
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_psnr': best_psnr,
            'psnr': psnr,
            'ssim': ssim,
        }, checkpoint_path)
        
        if psnr > best_psnr:
            best_psnr = psnr
            best_path = os.path.join(checkpoint_dir, f'espcn_x{scale_factor}_realesrgan_best.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'psnr': psnr,
                'ssim': ssim,
            }, best_path)
            print(f'Saved best Real-ESRGAN model with PSNR: {best_psnr:.2f} dB')
    
    writer.close()
    print(f'\nReal-ESRGAN training completed. Best PSNR: {best_psnr:.2f} dB')


if __name__ == '__main__':
    main()
