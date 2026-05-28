import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
from typing import Dict, Tuple
import time

from config import Config
from data import create_dataloaders, get_image_paths
from models import build_model, build_discriminator, AdversarialLoss
from utils import (
    calculate_psnr, calculate_ssim, AverageMeter,
    CombinedLossWithEdge, HeavyRainLoss, gradient_penalty
)


class GANTrainer:
    def __init__(self, device: torch.device = Config.DEVICE):
        self.device = device
        
        self.generator = build_model('resnet')
        self.discriminator = build_discriminator(Config.DISCRIMINATOR_TYPE)
        
        print(f"Generator parameters: {sum(p.numel() for p in self.generator.parameters()) / 1e6:.2f}M")
        print(f"Discriminator parameters: {sum(p.numel() for p in self.discriminator.parameters()) / 1e6:.2f}M")
        
        if Config.USE_EDGE_LOSS:
            self.pixel_criterion = CombinedLossWithEdge(
                alpha=Config.PIXEL_LOSS_WEIGHT * 0.6,
                beta=Config.PIXEL_LOSS_WEIGHT * 0.2,
                gamma=Config.EDGE_LOSS_WEIGHT
            )
        else:
            self.pixel_criterion = nn.MSELoss()
        
        self.heavy_rain_criterion = HeavyRainLoss(
            alpha=0.5,
            beta=Config.EDGE_LOSS_WEIGHT,
            gamma=Config.TV_LOSS_WEIGHT
        )
        
        self.adv_criterion = AdversarialLoss(loss_type=Config.GAN_LOSS_TYPE)
        
        self.optimizer_g = optim.Adam(self.generator.parameters(), lr=Config.LEARNING_RATE, betas=(0.5, 0.999))
        self.optimizer_d = optim.Adam(self.discriminator.parameters(), lr=Config.DISCRIMINATOR_LR, betas=(0.5, 0.999))
        
        self.scheduler_g = optim.lr_scheduler.CosineAnnealingLR(self.optimizer_g, T_max=Config.NUM_EPOCHS)
        self.scheduler_d = optim.lr_scheduler.CosineAnnealingLR(self.optimizer_d, T_max=Config.NUM_EPOCHS)
        
        self.best_psnr = 0

    def train_step(self, rainy_imgs: torch.Tensor, clean_imgs: torch.Tensor, 
                   intensities: list) -> Dict[str, float]:
        batch_size = rainy_imgs.size(0)
        
        self.optimizer_d.zero_grad()
        
        with torch.no_grad():
            fake_imgs = self.generator(rainy_imgs)
        
        real_pred = self.discriminator(clean_imgs)
        fake_pred = self.discriminator(fake_imgs.detach())
        
        loss_d_real = self.adv_criterion(real_pred, True)
        loss_d_fake = self.adv_criterion(fake_pred, False)
        loss_d = (loss_d_real + loss_d_fake) * 0.5
        
        if Config.GAN_LOSS_TYPE == 'wgan-gp':
            gp = gradient_penalty(self.discriminator, clean_imgs, fake_imgs, self.device)
            loss_d = loss_d + 10 * gp
        
        loss_d.backward()
        self.optimizer_d.step()
        
        self.optimizer_g.zero_grad()
        
        fake_imgs = self.generator(rainy_imgs)
        
        loss_pixel = self.pixel_criterion(fake_imgs, clean_imgs)
        
        adv_pred = self.discriminator(fake_imgs)
        loss_adv = self.adv_criterion(adv_pred, True)
        
        loss_heavy_rain = 0
        heavy_rain_count = 0
        for i, intensity in enumerate(intensities):
            if intensity == 'heavy':
                hr_loss, _ = self.heavy_rain_criterion(fake_imgs[i:i+1], clean_imgs[i:i+1])
                loss_heavy_rain += hr_loss
                heavy_rain_count += 1
        
        if heavy_rain_count > 0:
            loss_heavy_rain = loss_heavy_rain / heavy_rain_count
            loss_g = loss_pixel + Config.ADV_LOSS_WEIGHT * loss_adv + loss_heavy_rain * 0.5
        else:
            loss_g = loss_pixel + Config.ADV_LOSS_WEIGHT * loss_adv
        
        loss_g.backward()
        self.optimizer_g.step()
        
        with torch.no_grad():
            psnr = calculate_psnr(fake_imgs, clean_imgs)
            ssim = calculate_ssim(fake_imgs, clean_imgs)
        
        return {
            'loss_g': loss_g.item(),
            'loss_d': loss_d.item(),
            'loss_pixel': loss_pixel.item(),
            'loss_adv': loss_adv.item(),
            'loss_heavy_rain': loss_heavy_rain.item() if heavy_rain_count > 0 else 0,
            'psnr': psnr,
            'ssim': ssim
        }

    def train_one_epoch(self, train_loader: DataLoader, epoch: int) -> Dict[str, float]:
        self.generator.train()
        self.discriminator.train()
        
        loss_g_meter = AverageMeter()
        loss_d_meter = AverageMeter()
        loss_pixel_meter = AverageMeter()
        loss_adv_meter = AverageMeter()
        loss_hr_meter = AverageMeter()
        psnr_meter = AverageMeter()
        ssim_meter = AverageMeter()
        
        for batch_idx, (rainy_imgs, clean_imgs, intensities) in enumerate(train_loader):
            rainy_imgs = rainy_imgs.permute(0, 3, 1, 2).float().to(self.device)
            clean_imgs = clean_imgs.permute(0, 3, 1, 2).float().to(self.device)
            
            metrics = self.train_step(rainy_imgs, clean_imgs, intensities)
            
            batch_size = rainy_imgs.size(0)
            loss_g_meter.update(metrics['loss_g'], batch_size)
            loss_d_meter.update(metrics['loss_d'], batch_size)
            loss_pixel_meter.update(metrics['loss_pixel'], batch_size)
            loss_adv_meter.update(metrics['loss_adv'], batch_size)
            loss_hr_meter.update(metrics['loss_heavy_rain'], batch_size)
            psnr_meter.update(metrics['psnr'], batch_size)
            ssim_meter.update(metrics['ssim'], batch_size)
            
            if batch_idx % 10 == 0:
                print(f"Epoch [{epoch+1}] Batch [{batch_idx}/{len(train_loader)}] "
                      f"Loss_G: {metrics['loss_g']:.4f} Loss_D: {metrics['loss_d']:.4f} "
                      f"PSNR: {metrics['psnr']:.2f} SSIM: {metrics['ssim']:.4f}")
        
        return {
            'loss_g': loss_g_meter.avg,
            'loss_d': loss_d_meter.avg,
            'loss_pixel': loss_pixel_meter.avg,
            'loss_adv': loss_adv_meter.avg,
            'loss_heavy_rain': loss_hr_meter.avg,
            'psnr': psnr_meter.avg,
            'ssim': ssim_meter.avg
        }

    def validate(self, val_loader: DataLoader) -> Dict[str, float]:
        self.generator.eval()
        self.discriminator.eval()
        
        loss_g_meter = AverageMeter()
        psnr_meter = AverageMeter()
        ssim_meter = AverageMeter()
        
        intensity_metrics = {}
        
        with torch.no_grad():
            for batch_idx, (rainy_imgs, clean_imgs, intensities) in enumerate(val_loader):
                rainy_imgs = rainy_imgs.permute(0, 3, 1, 2).float().to(self.device)
                clean_imgs = clean_imgs.permute(0, 3, 1, 2).float().to(self.device)
                
                fake_imgs = self.generator(rainy_imgs)
                loss_pixel = self.pixel_criterion(fake_imgs, clean_imgs)
                
                batch_size = rainy_imgs.size(0)
                loss_g_meter.update(loss_pixel.item(), batch_size)
                
                psnr = calculate_psnr(fake_imgs, clean_imgs)
                ssim = calculate_ssim(fake_imgs, clean_imgs)
                psnr_meter.update(psnr, batch_size)
                ssim_meter.update(ssim, batch_size)
                
                for i, intensity in enumerate(intensities):
                    if intensity not in intensity_metrics:
                        intensity_metrics[intensity] = {'psnr': [], 'ssim': []}
                    intensity_metrics[intensity]['psnr'].append(calculate_psnr(fake_imgs[i:i+1], clean_imgs[i:i+1]))
                    intensity_metrics[intensity]['ssim'].append(calculate_ssim(fake_imgs[i:i+1], clean_imgs[i:i+1]))
        
        intensity_results = {}
        for intensity, metrics in intensity_metrics.items():
            intensity_results[intensity] = {
                'psnr': np.mean(metrics['psnr']),
                'ssim': np.mean(metrics['ssim']),
                'count': len(metrics['psnr'])
            }
        
        return {
            'loss': loss_g_meter.avg,
            'psnr': psnr_meter.avg,
            'ssim': ssim_meter.avg,
            'intensity_metrics': intensity_results
        }

    def save_checkpoint(self, epoch: int, metrics: Dict[str, float], save_dir: str):
        os.makedirs(save_dir, exist_ok=True)
        
        checkpoint = {
            'epoch': epoch,
            'generator_state_dict': self.generator.state_dict(),
            'discriminator_state_dict': self.discriminator.state_dict(),
            'optimizer_g_state_dict': self.optimizer_g.state_dict(),
            'optimizer_d_state_dict': self.optimizer_d.state_dict(),
            'metrics': metrics
        }
        
        checkpoint_path = os.path.join(save_dir, f'gan_checkpoint_epoch_{epoch}.pth')
        torch.save(checkpoint, checkpoint_path)
        
        best_path = os.path.join(save_dir, 'gan_best_model.pth')
        torch.save(checkpoint, best_path)
        
        print(f"GAN checkpoint saved: {checkpoint_path}")

    def load_checkpoint(self, checkpoint_path: str):
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.generator.load_state_dict(checkpoint['generator_state_dict'])
        self.discriminator.load_state_dict(checkpoint['discriminator_state_dict'])
        self.optimizer_g.load_state_dict(checkpoint['optimizer_g_state_dict'])
        self.optimizer_d.load_state_dict(checkpoint['optimizer_d_state_dict'])
        epoch = checkpoint['epoch']
        metrics = checkpoint['metrics']
        return epoch, metrics

    def train(self, train_loader: DataLoader, val_loader: DataLoader):
        print("Starting GAN training with adversarial loss and edge preservation...")
        
        for epoch in range(Config.NUM_EPOCHS):
            start_time = time.time()
            
            train_metrics = self.train_one_epoch(train_loader, epoch)
            val_metrics = self.validate(val_loader)
            
            self.scheduler_g.step()
            self.scheduler_d.step()
            
            elapsed = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"Epoch [{epoch+1}/{Config.NUM_EPOCHS}] - Time: {elapsed:.2f}s")
            print(f"{'='*60}")
            print(f"Train - Loss_G: {train_metrics['loss_g']:.4f}, "
                  f"Loss_D: {train_metrics['loss_d']:.4f}, "
                  f"Pixel: {train_metrics['loss_pixel']:.4f}, "
                  f"Adv: {train_metrics['loss_adv']:.4f}")
            print(f"        PSNR: {train_metrics['psnr']:.2f}, SSIM: {train_metrics['ssim']:.4f}")
            print(f"Val   - Loss: {val_metrics['loss']:.4f}, "
                  f"PSNR: {val_metrics['psnr']:.2f}, SSIM: {val_metrics['ssim']:.4f}")
            
            if 'intensity_metrics' in val_metrics:
                print("Intensity breakdown:")
                for intensity, metrics in val_metrics['intensity_metrics'].items():
                    print(f"  {intensity:8s} - PSNR: {metrics['psnr']:.2f}, "
                          f"SSIM: {metrics['ssim']:.4f}, Count: {metrics['count']}")
            
            if val_metrics['psnr'] > self.best_psnr:
                self.best_psnr = val_metrics['psnr']
                self.save_checkpoint(epoch + 1, val_metrics, Config.CHECKPOINT_DIR)
                print(f"New best model! PSNR: {self.best_psnr:.2f}")
        
        print("\n" + "=" * 60)
        print("GAN Training completed!")
        print(f"Best PSNR: {self.best_psnr:.2f}")
        print("=" * 60)


def main():
    device = Config.DEVICE
    print(f"Using device: {device}")
    
    train_paths = get_image_paths(Config.TRAIN_DATA_DIR)
    test_paths = get_image_paths(Config.TEST_DATA_DIR)
    
    print(f"Found {len(train_paths)} training images")
    print(f"Found {len(test_paths)} test images")
    
    train_loader, val_loader = create_dataloaders(
        Config.TRAIN_DATA_DIR,
        Config.TEST_DATA_DIR,
        Config.BATCH_SIZE
    )
    
    trainer = GANTrainer(device)
    
    trainer.train(train_loader, val_loader)


if __name__ == '__main__':
    main()
