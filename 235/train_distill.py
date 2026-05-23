import os
import argparse
import yaml
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm
import numpy as np

from models import ESPCN
from models.rrdb import SmallRRDBTeacher
from data import get_train_loader, get_valid_loader
from utils.metrics import calculate_psnr, calculate_ssim, AverageMeter


def parse_args():
    parser = argparse.ArgumentParser(description='Knowledge Distillation for ESPCN')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--scale', type=int, default=None, help='Scale factor (2 or 4)')
    parser.add_argument('--teacher_checkpoint', type=str, required=True, help='Path to teacher model checkpoint')
    parser.add_argument('--student_resume', type=str, default=None, help='Path to resume student checkpoint')
    parser.add_argument('--alpha', type=float, default=0.5, help='Distillation loss weight')
    parser.add_argument('--temperature', type=float, default=1.0, help='Temperature for soft targets')
    return parser.parse_args()


def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


class DistillationLoss(nn.Module):
    def __init__(self, alpha=0.5, temperature=1.0):
        super(DistillationLoss, self).__init__()
        self.alpha = alpha
        self.temperature = temperature
        self.mse_loss = nn.MSELoss()
        self.l1_loss = nn.L1Loss()
    
    def forward(self, student_out, teacher_out, target):
        hard_loss = self.mse_loss(student_out, target)
        
        soft_teacher = teacher_out / self.temperature
        soft_student = student_out / self.temperature
        distill_loss = self.l1_loss(soft_student, soft_teacher) * (self.temperature ** 2)
        
        total_loss = self.alpha * hard_loss + (1 - self.alpha) * distill_loss
        
        return total_loss, hard_loss, distill_loss


class FeatureDistillationLoss(nn.Module):
    def __init__(self, alpha=0.5, beta=1.0):
        super(FeatureDistillationLoss, self).__init__()
        self.alpha = alpha
        self.beta = beta
        self.mse_loss = nn.MSELoss()
    
    def forward(self, student_out, teacher_out, target):
        hard_loss = self.mse_loss(student_out, target)
        feature_loss = self.mse_loss(student_out, teacher_out)
        
        total_loss = self.alpha * hard_loss + self.beta * feature_loss
        
        return total_loss, hard_loss, feature_loss


def train_one_epoch_distill(student_model, teacher_model, train_loader, criterion, 
                            optimizer, device, epoch, writer, scale_factor):
    student_model.train()
    teacher_model.eval()
    
    loss_meter = AverageMeter()
    hard_loss_meter = AverageMeter()
    distill_loss_meter = AverageMeter()
    
    pbar = tqdm(train_loader, desc=f'Epoch {epoch} [Distill]')
    for i, (lr_imgs, hr_imgs) in enumerate(pbar):
        lr_imgs = lr_imgs.to(device)
        hr_imgs = hr_imgs.to(device)
        
        with torch.no_grad():
            teacher_out = teacher_model(lr_imgs)
        
        optimizer.zero_grad()
        student_out = student_model(lr_imgs)
        
        loss, hard_loss, distill_loss = criterion(student_out, teacher_out, hr_imgs)
        loss.backward()
        optimizer.step()
        
        loss_meter.update(loss.item(), lr_imgs.size(0))
        hard_loss_meter.update(hard_loss.item(), lr_imgs.size(0))
        distill_loss_meter.update(distill_loss.item(), lr_imgs.size(0))
        
        pbar.set_postfix({
            'loss': f'{loss_meter.avg:.6f}',
            'hard': f'{hard_loss_meter.avg:.6f}',
            'distill': f'{distill_loss_meter.avg:.6f}'
        })
        
        if writer is not None and i % 100 == 0:
            global_step = epoch * len(train_loader) + i
            writer.add_scalar('Distill/Total_loss', loss.item(), global_step)
            writer.add_scalar('Distill/Hard_loss', hard_loss.item(), global_step)
            writer.add_scalar('Distill/Distill_loss', distill_loss.item(), global_step)
    
    return loss_meter.avg


def validate_distill(student_model, valid_loader, device, scale_factor, writer=None, epoch=None):
    student_model.eval()
    psnr_meter = AverageMeter()
    ssim_meter = AverageMeter()
    
    with torch.no_grad():
        for lr_imgs, hr_imgs in tqdm(valid_loader, desc='Validation [Distill]'):
            lr_imgs = lr_imgs.to(device)
            hr_imgs = hr_imgs.to(device)
            
            sr_imgs = student_model(lr_imgs)
            
            psnr = calculate_psnr(sr_imgs, hr_imgs, crop_border=scale_factor)
            ssim = calculate_ssim(sr_imgs, hr_imgs, crop_border=scale_factor)
            
            psnr_meter.update(psnr, lr_imgs.size(0))
            ssim_meter.update(ssim, lr_imgs.size(0))
    
    if writer is not None and epoch is not None:
        writer.add_scalar('Distill/PSNR', psnr_meter.avg, epoch)
        writer.add_scalar('Distill/SSIM', ssim_meter.avg, epoch)
    
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
    
    print(f'Loading teacher model from {args.teacher_checkpoint}')
    teacher_model = SmallRRDBTeacher(scale=scale_factor, num_feat=48, num_block=6).to(device)
    
    teacher_checkpoint = torch.load(args.teacher_checkpoint, map_location=device)
    if 'model_state_dict' in teacher_checkpoint:
        teacher_model.load_state_dict(teacher_checkpoint['model_state_dict'])
    else:
        teacher_model.load_state_dict(teacher_checkpoint)
    teacher_model.eval()
    
    print(f'Teacher parameters: {sum(p.numel() for p in teacher_model.parameters()) / 1e6:.2f}M')
    
    student_model = ESPCN(
        scale_factor=scale_factor,
        num_channels=config['model']['num_channels'],
        num_features=config['model']['num_features']
    ).to(device)
    
    print(f'Student parameters: {sum(p.numel() for p in student_model.parameters()) / 1000:.2f}K')
    
    criterion = DistillationLoss(alpha=args.alpha, temperature=args.temperature)
    optimizer = optim.Adam(student_model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=lr_decay_step, gamma=lr_decay_gamma)
    
    start_epoch = 1
    best_psnr = 0.0
    
    if args.student_resume and os.path.exists(args.student_resume):
        checkpoint = torch.load(args.student_resume, map_location=device)
        student_model.load_state_dict(checkpoint['model_state_dict'])
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
    
    writer = SummaryWriter(os.path.join(log_dir, f'espcn_x{scale_factor}_distill'))
    
    print(f'Distillation config: alpha={args.alpha}, T={args.temperature}')
    
    for epoch in range(start_epoch, num_epochs + 1):
        print(f'\nEpoch {epoch}/{num_epochs}')
        print(f'Learning rate: {optimizer.param_groups[0]["lr"]:.6f}')
        
        train_loss = train_one_epoch_distill(
            student_model, teacher_model, train_loader, criterion, 
            optimizer, device, epoch, writer, scale_factor
        )
        psnr, ssim = validate_distill(
            student_model, valid_loader, device, scale_factor, writer, epoch
        )
        
        scheduler.step()
        
        print(f'Train Loss: {train_loss:.6f}')
        print(f'Valid PSNR: {psnr:.2f} dB, SSIM: {ssim:.4f}')
        
        checkpoint_path = os.path.join(checkpoint_dir, f'espcn_x{scale_factor}_distill_latest.pth')
        torch.save({
            'epoch': epoch,
            'model_state_dict': student_model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_psnr': best_psnr,
            'psnr': psnr,
            'ssim': ssim,
        }, checkpoint_path)
        
        if psnr > best_psnr:
            best_psnr = psnr
            best_path = os.path.join(checkpoint_dir, f'espcn_x{scale_factor}_distill_best.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': student_model.state_dict(),
                'psnr': psnr,
                'ssim': ssim,
            }, best_path)
            print(f'Saved best distilled model with PSNR: {best_psnr:.2f} dB')
    
    writer.close()
    print(f'\nDistillation completed. Best PSNR: {best_psnr:.2f} dB')


if __name__ == '__main__':
    main()
