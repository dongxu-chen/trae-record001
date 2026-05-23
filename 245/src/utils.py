import os
import numpy as np
import torch
import torch.nn as nn
from skimage.metrics import peak_signal_noise_ratio as psnr_skimage
from skimage.metrics import structural_similarity as ssim_skimage
import cv2


def calculate_psnr(img1, img2, crop_border=0):
    if isinstance(img1, torch.Tensor):
        img1 = img1.cpu().numpy()
        img2 = img2.cpu().numpy()
    
    if img1.ndim == 4:
        img1 = img1.squeeze(0).squeeze(0)
        img2 = img2.squeeze(0).squeeze(0)
    elif img1.ndim == 3:
        img1 = img1.squeeze(0)
        img2 = img2.squeeze(0)
    
    if crop_border > 0:
        img1 = img1[crop_border:-crop_border, crop_border:-crop_border]
        img2 = img2[crop_border:-crop_border, crop_border:-crop_border]
    
    img1 = np.clip(img1 * 255.0, 0, 255).round()
    img2 = np.clip(img2 * 255.0, 0, 255).round()
    
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')
    return 20 * np.log10(255.0 / np.sqrt(mse))


def calculate_ssim(img1, img2, crop_border=0):
    if isinstance(img1, torch.Tensor):
        img1 = img1.cpu().numpy()
        img2 = img2.cpu().numpy()
    
    if img1.ndim == 4:
        img1 = img1.squeeze(0).squeeze(0)
        img2 = img2.squeeze(0).squeeze(0)
    elif img1.ndim == 3:
        img1 = img1.squeeze(0)
        img2 = img2.squeeze(0)
    
    if crop_border > 0:
        img1 = img1[crop_border:-crop_border, crop_border:-crop_border]
        img2 = img2[crop_border:-crop_border, crop_border:-crop_border]
    
    img1 = np.clip(img1 * 255.0, 0, 255).round() / 255.0
    img2 = np.clip(img2 * 255.0, 0, 255).round() / 255.0
    
    return ssim_skimage(img1, img2, data_range=1.0)


class AverageMeter:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0
    
    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def save_checkpoint(model, optimizer, epoch, psnr, ssim, save_path):
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'psnr': psnr,
        'ssim': ssim
    }, save_path)
    print(f"Checkpoint saved to {save_path}")


def load_checkpoint(model, checkpoint_path, optimizer=None, device='cuda'):
    if not os.path.exists(checkpoint_path):
        print(f"Checkpoint not found: {checkpoint_path}")
        return model, optimizer, 0, 0, 0
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    if optimizer is not None and 'optimizer_state_dict' in checkpoint:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    
    epoch = checkpoint.get('epoch', 0)
    psnr = checkpoint.get('psnr', 0)
    ssim = checkpoint.get('ssim', 0)
    
    print(f"Checkpoint loaded from {checkpoint_path} (Epoch {epoch})")
    return model, optimizer, epoch, psnr, ssim


def tensor_to_image(tensor):
    if tensor.is_cuda:
        tensor = tensor.cpu()
    
    img = tensor.squeeze().numpy()
    img = np.clip(img * 255.0, 0, 255).astype(np.uint8)
    return img


def save_image(img, save_path):
    if isinstance(img, torch.Tensor):
        img = tensor_to_image(img)
    elif isinstance(img, np.ndarray):
        if img.max() <= 1.0:
            img = (img * 255).astype(np.uint8)
        if img.ndim == 3:
            img = img.squeeze(0)
    
    cv2.imwrite(save_path, img)


def create_dirs(dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def get_config(config_path):
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config
