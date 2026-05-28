import torch
import torch.nn.functional as F
import numpy as np
from typing import Tuple


def calculate_psnr(img1: torch.Tensor, img2: torch.Tensor, max_val: float = 1.0) -> float:
    mse = torch.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')
    psnr = 20 * torch.log10(max_val / torch.sqrt(mse))
    return psnr.item()


def calculate_ssim(img1: torch.Tensor, img2: torch.Tensor, 
                   window_size: int = 11, sigma: float = 1.5, 
                   max_val: float = 1.0) -> float:
    if img1.dim() == 4:
        ssim_values = []
        for i in range(img1.size(0)):
            ssim_val = _ssim_single(img1[i], img2[i], window_size, sigma, max_val)
            ssim_values.append(ssim_val)
        return np.mean(ssim_values)
    else:
        return _ssim_single(img1, img2, window_size, sigma, max_val)


def _ssim_single(img1: torch.Tensor, img2: torch.Tensor, 
                 window_size: int = 11, sigma: float = 1.5, 
                 max_val: float = 1.0) -> float:
    if img1.shape != img2.shape:
        raise ValueError('Input images must have the same dimensions.')
    
    _, h, w = img1.shape
    
    if h < window_size or w < window_size:
        raise ValueError(f'Input images should be larger than window size ({window_size}).')
    
    gaussian_window = _create_gaussian_window(window_size, sigma, img1.shape[0])
    gaussian_window = gaussian_window.to(img1.device)
    
    K1 = 0.01
    K2 = 0.03
    L = max_val
    
    C1 = (K1 * L) ** 2
    C2 = (K2 * L) ** 2
    
    mu1 = F.conv2d(img1.unsqueeze(0), gaussian_window, padding=window_size//2, groups=img1.shape[0])
    mu2 = F.conv2d(img2.unsqueeze(0), gaussian_window, padding=window_size//2, groups=img1.shape[0])
    
    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2
    
    sigma1_sq = F.conv2d(img1.unsqueeze(0) * img1.unsqueeze(0), gaussian_window, 
                         padding=window_size//2, groups=img1.shape[0]) - mu1_sq
    sigma2_sq = F.conv2d(img2.unsqueeze(0) * img2.unsqueeze(0), gaussian_window, 
                         padding=window_size//2, groups=img1.shape[0]) - mu2_sq
    sigma12 = F.conv2d(img1.unsqueeze(0) * img2.unsqueeze(0), gaussian_window, 
                       padding=window_size//2, groups=img1.shape[0]) - mu1_mu2
    
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    
    return ssim_map.mean().item()


def _create_gaussian_window(window_size: int, sigma: float, channels: int) -> torch.Tensor:
    gauss = torch.Tensor([np.exp(-(x - window_size//2)**2 / float(2 * sigma**2)) 
                          for x in range(window_size)])
    gauss = gauss / gauss.sum()
    _1D_window = gauss.unsqueeze(1)
    _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
    window = _2D_window.expand(channels, 1, window_size, window_size).contiguous()
    return window


class AverageMeter:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0
    
    def update(self, val: float, n: int = 1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count
