import cv2
import math
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import ndimage
from scipy.stats import multivariate_normal


class RealESRGANDegradation:
    def __init__(self, scale=4, **kwargs):
        self.scale = scale
        self.blur_kernel_range = kwargs.get('blur_kernel_range', [7, 21])
        self.sinc_prob = kwargs.get('sinc_prob', 0.1)
        self.blur_sigma_range = kwargs.get('blur_sigma_range', [0.2, 3.0])
        self.gaussian_noise_range = kwargs.get('gaussian_noise_range', [0, 10])
        self.poisson_scale_range = kwargs.get('poisson_scale_range', [0.05, 3.0])
        self.gray_noise_prob = kwargs.get('gray_noise_prob', 0.4)
        self.jpeg_range = kwargs.get('jpeg_range', [30, 95])
        self.second_blur_prob = kwargs.get('second_blur_prob', 0.8)
        self.resize_range = kwargs.get('resize_range', [0.15, 1.5])
        
    def _generate_gaussian_kernel(self, kernel_size, sigma_x, sigma_y=None):
        if sigma_y is None:
            sigma_y = sigma_x
            
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        center = kernel_size // 2
        
        for x in range(kernel_size):
            for y in range(kernel_size):
                dx = x - center
                dy = y - center
                kernel[x, y] = np.exp(-(dx**2 / (2 * sigma_x**2) + dy**2 / (2 * sigma_y**2)))
        
        kernel = kernel / kernel.sum()
        return kernel
    
    def _generate_sinc_kernel(self, kernel_size, omega_c):
        if kernel_size % 2 == 0:
            kernel_size += 1
            
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
        center = kernel_size // 2
        
        for x in range(kernel_size):
            for y in range(kernel_size):
                dx = x - center
                dy = y - center
                r = np.sqrt(dx**2 + dy**2)
                if r == 0:
                    kernel[x, y] = omega_c / np.pi
                else:
                    kernel[x, y] = np.sin(omega_c * r) / (np.pi * r)
        
        kernel = kernel / kernel.sum()
        return kernel
    
    def _apply_blur(self, img, kernel):
        return cv2.filter2D(img, -1, kernel)
    
    def _add_gaussian_noise(self, img, sigma):
        noise = np.random.normal(0, sigma / 255.0, img.shape).astype(np.float32)
        noisy_img = img + noise
        return np.clip(noisy_img, 0, 1)
    
    def _add_poisson_noise(self, img, scale):
        noisy_img = np.random.poisson(img * 255.0 * scale) / (scale * 255.0)
        return np.clip(noisy_img.astype(np.float32), 0, 1)
    
    def _jpeg_compression(self, img, quality):
        img_uint8 = np.clip(img * 255, 0, 255).astype(np.uint8)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        _, encimg = cv2.imencode('.jpg', img_uint8, encode_param)
        decimg = cv2.imdecode(encimg, cv2.IMREAD_COLOR)
        return decimg.astype(np.float32) / 255.0
    
    def _random_resize(self, img):
        h, w = img.shape[:2]
        scale = random.uniform(*self.resize_range)
        new_h = int(h * scale)
        new_w = int(w * scale)
        
        interp_methods = [cv2.INTER_LINEAR, cv2.INTER_CUBIC, cv2.INTER_AREA]
        interp = random.choice(interp_methods)
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=interp)
        resized_back = cv2.resize(resized, (w, h), interpolation=interp)
        
        return resized_back
    
    def __call__(self, img_hr):
        img = img_hr.astype(np.float32) / 255.0 if img_hr.dtype == np.uint8 else img_hr.copy()
        
        if random.random() < 0.5:
            kernel_size = random.randrange(*self.blur_kernel_range, 2)
            sigma = random.uniform(*self.blur_sigma_range)
            
            if random.random() < self.sinc_prob:
                omega_c = random.uniform(0.1, 0.9)
                kernel = self._generate_sinc_kernel(kernel_size, omega_c)
            else:
                kernel = self._generate_gaussian_kernel(kernel_size, sigma)
            
            img = self._apply_blur(img, kernel)
        
        img = cv2.resize(
            img, 
            (img.shape[1] // self.scale, img.shape[0] // self.scale),
            interpolation=cv2.INTER_AREA
        )
        
        if random.random() < 0.5:
            if random.random() < 0.5:
                sigma = random.uniform(*self.gaussian_noise_range)
                gray_noise = random.random() < self.gray_noise_prob
                
                if gray_noise:
                    noise = np.random.normal(0, sigma / 255.0, img.shape[:2])
                    noise = np.stack([noise, noise, noise], axis=-1).astype(np.float32)
                else:
                    noise = np.random.normal(0, sigma / 255.0, img.shape).astype(np.float32)
                
                img = np.clip(img + noise, 0, 1)
            else:
                scale = random.uniform(*self.poisson_scale_range)
                img = self._add_poisson_noise(img, scale)
        
        if random.random() < 0.5:
            img = self._random_resize(img)
        
        jpeg_quality = random.randint(*self.jpeg_range)
        img = self._jpeg_compression(img, jpeg_quality)
        
        if random.random() < self.second_blur_prob:
            kernel_size = random.randrange(*self.blur_kernel_range, 2)
            sigma = random.uniform(*self.blur_sigma_range)
            kernel = self._generate_gaussian_kernel(kernel_size, sigma)
            img = self._apply_blur(img, kernel)
            
            jpeg_quality2 = random.randint(*self.jpeg_range)
            img = self._jpeg_compression(img, jpeg_quality2)
        
        img_lr = np.clip(img * 255, 0, 255).astype(np.uint8)
        
        return img_lr


class BatchDegradationWrapper:
    def __init__(self, scale=4, **kwargs):
        self.degradation = RealESRGANDegradation(scale=scale, **kwargs)
    
    def __call__(self, batch_hr):
        if isinstance(batch_hr, torch.Tensor):
            batch_hr = batch_hr.permute(0, 2, 3, 1).cpu().numpy()
            batch_hr = (batch_hr * 255).astype(np.uint8)
        
        batch_lr = []
        for img_hr in batch_hr:
            img_lr = self.degradation(img_hr)
            batch_lr.append(img_lr)
        
        batch_lr = np.stack(batch_lr, axis=0)
        batch_lr = batch_lr.astype(np.float32) / 255.0
        batch_lr = torch.from_numpy(batch_lr).permute(0, 3, 1, 2)
        
        return batch_lr


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    
    degrader = RealESRGANDegradation(scale=4)
    
    test_img = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    lr_img = degrader(test_img)
    
    print(f'HR shape: {test_img.shape}')
    print(f'LR shape: {lr_img.shape}')
    print(f'HR dtype: {test_img.dtype}')
    print(f'LR dtype: {lr_img.dtype}')
