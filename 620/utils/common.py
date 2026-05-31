import os
import torch
import numpy as np
import cv2
from pathlib import Path
from config import PROCESS_CONFIG


def get_device():
    device = PROCESS_CONFIG['device']
    if device == 'auto':
        if torch.cuda.is_available():
            return torch.device('cuda')
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return torch.device('mps')
        else:
            return torch.device('cpu')
    return torch.device(device)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def tensor2img(tensor, rgb_range=255, out_type=np.uint8, min_max=(0, 1)):
    tensor = tensor.squeeze().float().cpu().clamp_(*min_max)
    tensor = (tensor - min_max[0]) / (min_max[1] - min_max[0])
    n_dim = tensor.dim()
    if n_dim == 4:
        n_img = len(tensor)
        img_np = make_grid(tensor, nrow=int(math.sqrt(n_img)), normalize=False).numpy()
        img_np = np.transpose(img_np[[2, 1, 0], :, :], (1, 2, 0))
    elif n_dim == 3:
        img_np = tensor.numpy()
        img_np = np.transpose(img_np[[2, 1, 0], :, :], (1, 2, 0))
    elif n_dim == 2:
        img_np = tensor.numpy()
    else:
        raise TypeError(f'Only support 4D, 3D and 2D tensor. But received with dimension: {n_dim}')
    if out_type == np.uint8:
        img_np = (img_np * rgb_range).round()
    return img_np.astype(out_type)


def img2tensor(img, bgr2rgb=True, float32=True):
    if img.ndim == 2:
        img = np.expand_dims(img, axis=2)
    if bgr2rgb:
        img = img.astype(np.float32) / 255.
        img = img[:, :, ::-1].transpose(2, 0, 1)
    else:
        img = img.astype(np.float32) / 255.
        img = img.transpose(2, 0, 1)
    if float32:
        img = torch.from_numpy(img).float()
    return img


def read_img(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    img = img.astype(np.float32) / 255.
    return img


def save_img(img, path):
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 1)
        img = (img * 255).round().astype(np.uint8)
    cv2.imwrite(path, img)


def calc_psnr(img1, img2, crop_border=0):
    assert img1.shape == img2.shape, f'Image shapes are different: {img1.shape}, {img2.shape}.'
    if crop_border != 0:
        img1 = img1[crop_border:-crop_border, crop_border:-crop_border, ...]
        img2 = img2[crop_border:-crop_border, crop_border:-crop_border, ...]
    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')
    return 10. * np.log10(255. * 255. / mse)


def ssim(img1, img2):
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)
    kernel = cv2.getGaussianKernel(11, 1.5)
    window = np.outer(kernel, kernel.transpose())
    mu1 = cv2.filter2D(img1, -1, window)
    mu2 = cv2.filter2D(img2, -1, window)
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2
    sigma1_sq = cv2.filter2D(img1 ** 2, -1, window) - mu1_sq
    sigma2_sq = cv2.filter2D(img2 ** 2, -1, window) - mu2_sq
    sigma12 = cv2.filter2D(img1 * img2, -1, window) - mu1_mu2
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return ssim_map.mean()


def calc_ssim(img1, img2, crop_border=0):
    assert img1.shape == img2.shape, f'Image shapes are different: {img1.shape}, {img2.shape}.'
    if crop_border != 0:
        img1 = img1[crop_border:-crop_border, crop_border:-crop_border, ...]
        img2 = img2[crop_border:-crop_border, crop_border:-crop_border, ...]
    if img1.ndim == 2:
        return ssim(img1, img2)
    elif img1.ndim == 3:
        ssims = []
        for i in range(img1.shape[2]):
            ssims.append(ssim(img1[..., i], img2[..., i]))
        return np.array(ssims).mean()
    else:
        raise ValueError('Wrong input image dimensions.')


def generate_weights(num_frames, center_weight=0.4, temporal_weight=0.15):
    weights = np.zeros(num_frames)
    center = num_frames // 2
    weights[center] = center_weight
    remaining = 1.0 - center_weight
    side_weight = remaining / (2 * center) if center > 0 else 0
    for i in range(center):
        decay = 1.0 - (i + 1) * temporal_weight / center
        weights[center - i - 1] = side_weight * decay
        weights[center + i + 1] = side_weight * decay
    return weights / weights.sum()


import math
from torchvision.utils import make_grid
