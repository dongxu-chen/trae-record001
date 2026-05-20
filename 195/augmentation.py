import numpy as np
import random


class Compose:
    def __init__(self, transforms):
        self.transforms = transforms
        
    def __call__(self, img):
        for t in self.transforms:
            img = t(img)
        return img


class RandomFlip:
    def __init__(self, p=0.5):
        self.p = p
        
    def __call__(self, img):
        if random.random() < self.p:
            img = np.flip(img, axis=0).copy()
        if random.random() < self.p:
            img = np.flip(img, axis=1).copy()
        return img


class RandomRotate:
    def __init__(self, p=0.5):
        self.p = p
        
    def __call__(self, img):
        if random.random() < self.p:
            k = random.choice([1, 2, 3])
            img = np.rot90(img, k=k, axes=(0, 1)).copy()
        return img


class GaussianNoise:
    def __init__(self, p=0.5, std=0.01):
        self.p = p
        self.std = std
        
    def __call__(self, img):
        if random.random() < self.p:
            noise = np.random.normal(0, self.std, img.shape)
            img = img + noise
        return img


class SpectralShift:
    def __init__(self, p=0.5, max_shift=2):
        self.p = p
        self.max_shift = max_shift
        
    def __call__(self, img):
        if random.random() < self.p:
            shift = random.randint(-self.max_shift, self.max_shift)
            img = np.roll(img, shift, axis=2)
            if shift > 0:
                img[:, :, :shift] = img[:, :, shift:shift+1]
            elif shift < 0:
                img[:, :, shift:] = img[:, :, shift-1:shift]
        return img


class SpectralPerturbation:
    def __init__(self, p=0.5, std=0.02, band_wise=True):
        self.p = p
        self.std = std
        self.band_wise = band_wise
        
    def __call__(self, img):
        if random.random() < self.p:
            h, w, c = img.shape
            if self.band_wise:
                noise = np.random.normal(0, self.std, (1, 1, c))
            else:
                noise = np.random.normal(0, self.std, img.shape)
            img = img + noise
        return img


class RandomBandBrightness:
    def __init__(self, p=0.5, factor=0.1, num_bands=None):
        self.p = p
        self.factor = factor
        self.num_bands = num_bands
        
    def __call__(self, img):
        if random.random() < self.p:
            h, w, c = img.shape
            num_bands = self.num_bands if self.num_bands else max(1, c // 10)
            band_indices = random.sample(range(c), min(num_bands, c))
            
            for band in band_indices:
                alpha = 1 + random.uniform(-self.factor, self.factor)
                img[:, :, band] = img[:, :, band] * alpha
        return img


class SpectralGaussianBlur:
    def __init__(self, p=0.5, kernel_size=3, sigma=1.0):
        self.p = p
        self.kernel_size = kernel_size
        self.sigma = sigma
        
    def __call__(self, img):
        if random.random() < self.p:
            from scipy.ndimage import gaussian_filter1d
            sigma = random.uniform(0.1, self.sigma)
            for i in range(img.shape[0]):
                for j in range(img.shape[1]):
                    img[i, j, :] = gaussian_filter1d(img[i, j, :], sigma=sigma)
        return img


class RandomBandDropout:
    def __init__(self, p=0.5, dropout_ratio=0.1):
        self.p = p
        self.dropout_ratio = dropout_ratio
        
    def __call__(self, img):
        if random.random() < self.p:
            h, w, c = img.shape
            num_drop = int(c * self.dropout_ratio)
            drop_indices = random.sample(range(c), max(1, num_drop))
            
            for band in drop_indices:
                img[:, :, band] = 0
        return img


class RandomErasing:
    def __init__(self, p=0.5, scale=(0.02, 0.1), ratio=(0.3, 3.3)):
        self.p = p
        self.scale = scale
        self.ratio = ratio
        
    def __call__(self, img):
        if random.random() < self.p:
            h, w, c = img.shape
            for _ in range(10):
                target_area = random.uniform(*self.scale) * h * w
                aspect_ratio = random.uniform(*self.ratio)
                
                patch_h = int(round(np.sqrt(target_area * aspect_ratio)))
                patch_w = int(round(np.sqrt(target_area / aspect_ratio)))
                
                if patch_h < h and patch_w < w:
                    x1 = random.randint(0, h - patch_h)
                    y1 = random.randint(0, w - patch_w)
                    img[x1:x1+patch_h, y1:y1+patch_w, :] = np.random.randn(patch_h, patch_w, c) * 0.1
                    break
        return img


class BrightnessAdjust:
    def __init__(self, p=0.5, factor=0.1):
        self.p = p
        self.factor = factor
        
    def __call__(self, img):
        if random.random() < self.p:
            alpha = 1 + random.uniform(-self.factor, self.factor)
            img = img * alpha
        return img


def get_train_transforms(p=0.5):
    return Compose([
        RandomFlip(p=p),
        RandomRotate(p=p),
        GaussianNoise(p=p, std=0.005),
        BrightnessAdjust(p=p, factor=0.05),
        SpectralPerturbation(p=p, std=0.01),
    ])


def get_strong_train_transforms(p=0.5):
    return Compose([
        RandomFlip(p=p),
        RandomRotate(p=p),
        GaussianNoise(p=p, std=0.01),
        SpectralShift(p=p, max_shift=3),
        RandomErasing(p=p, scale=(0.01, 0.05)),
        BrightnessAdjust(p=p, factor=0.1),
        SpectralPerturbation(p=p, std=0.02),
        RandomBandBrightness(p=p, factor=0.15),
        SpectralGaussianBlur(p=0.3, sigma=0.5),
        RandomBandDropout(p=0.3, dropout_ratio=0.05),
    ])


def get_spectral_transforms(p=0.5):
    return Compose([
        SpectralPerturbation(p=p, std=0.02),
        RandomBandBrightness(p=p, factor=0.1),
        SpectralGaussianBlur(p=p, sigma=0.8),
        RandomBandDropout(p=p, dropout_ratio=0.08),
    ])
