import os
import glob
import random
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms


class DIV2KDataset(Dataset):
    def __init__(self, hr_dir, scale_factor=4, patch_size=96, is_train=True):
        self.hr_dir = hr_dir
        self.scale_factor = scale_factor
        self.patch_size = patch_size
        self.is_train = is_train
        
        self.hr_paths = sorted(glob.glob(os.path.join(hr_dir, '*.png')))
        if len(self.hr_paths) == 0:
            self.hr_paths = sorted(glob.glob(os.path.join(hr_dir, '*.jpg')))
        
        print(f'Found {len(self.hr_paths)} images in {hr_dir}')
    
    def __len__(self):
        return len(self.hr_paths)
    
    def __getitem__(self, idx):
        hr_path = self.hr_paths[idx]
        hr_img = Image.open(hr_path).convert('RGB')
        
        if self.is_train:
            hr_patch = self._random_crop(hr_img, self.patch_size)
            lr_patch = self._downsample(hr_patch)
            
            hr_patch, lr_patch = self._augment(hr_patch, lr_patch)
            
            hr_tensor = transforms.ToTensor()(hr_patch)
            lr_tensor = transforms.ToTensor()(lr_patch)
            
            return lr_tensor, hr_tensor
        else:
            lr_img = self._downsample(hr_img)
            
            hr_tensor = transforms.ToTensor()(hr_img)
            lr_tensor = transforms.ToTensor()(lr_img)
            
            return lr_tensor, hr_tensor
    
    def _random_crop(self, img, patch_size):
        w, h = img.size
        x1 = random.randint(0, w - patch_size)
        y1 = random.randint(0, h - patch_size)
        return img.crop((x1, y1, x1 + patch_size, y1 + patch_size))
    
    def _downsample(self, hr_img):
        w, h = hr_img.size
        lr_w = w // self.scale_factor
        lr_h = h // self.scale_factor
        lr_img = hr_img.resize((lr_w, lr_h), Image.BICUBIC)
        return lr_img
    
    def _augment(self, hr, lr):
        if random.random() < 0.5:
            hr = hr.transpose(Image.FLIP_LEFT_RIGHT)
            lr = lr.transpose(Image.FLIP_LEFT_RIGHT)
        
        if random.random() < 0.5:
            hr = hr.transpose(Image.FLIP_TOP_BOTTOM)
            lr = lr.transpose(Image.FLIP_TOP_BOTTOM)
        
        angle = random.choice([0, 90, 180, 270])
        if angle != 0:
            hr = hr.rotate(angle)
            lr = lr.rotate(angle)
        
        return hr, lr


def get_train_loader(hr_dir, scale_factor=4, patch_size=96, batch_size=16, num_workers=4):
    dataset = DIV2KDataset(hr_dir, scale_factor, patch_size, is_train=True)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)


def get_valid_loader(hr_dir, scale_factor=4, batch_size=1, num_workers=4):
    dataset = DIV2KDataset(hr_dir, scale_factor, patch_size=0, is_train=False)
    return DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)


if __name__ == '__main__':
    import numpy as np
    
    sample_hr_dir = './data/DIV2K/DIV2K_train_HR'
    if os.path.exists(sample_hr_dir):
        dataset = DIV2KDataset(sample_hr_dir, scale_factor=4, patch_size=96, is_train=True)
        lr, hr = dataset[0]
        print(f'LR shape: {lr.shape}')
        print(f'HR shape: {hr.shape}')
        print(f'LR range: [{lr.min():.3f}, {lr.max():.3f}]')
        print(f'HR range: [{hr.min():.3f}, {hr.max():.3f}]')
    else:
        print('Dataset directory not found. Please download DIV2K dataset.')
