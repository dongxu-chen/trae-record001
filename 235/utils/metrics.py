import torch
import torch.nn.functional as F
import numpy as np
from skimage.metrics import structural_similarity as ssim_skimage


def calculate_psnr(img1, img2, crop_border=0):
    if crop_border > 0:
        img1 = img1[:, :, crop_border:-crop_border, crop_border:-crop_border]
        img2 = img2[:, :, crop_border:-crop_border, crop_border:-crop_border]
    
    mse = torch.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')
    psnr = 20 * torch.log10(1.0 / torch.sqrt(mse))
    return psnr.item()


def calculate_ssim(img1, img2, crop_border=0):
    img1_np = img1.squeeze(0).permute(1, 2, 0).cpu().numpy()
    img2_np = img2.squeeze(0).permute(1, 2, 0).cpu().numpy()
    
    if crop_border > 0:
        img1_np = img1_np[crop_border:-crop_border, crop_border:-crop_border, :]
        img2_np = img2_np[crop_border:-crop_border, crop_border:-crop_border, :]
    
    ssim_value = ssim_skimage(img1_np, img2_np, channel_axis=2, data_range=1.0)
    return ssim_value


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
