import os
import random
import numpy as np
import cv2
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms


class FLIRDataset(Dataset):
    def __init__(self, root_dir, scale=4, patch_size=64, is_train=True):
        self.root_dir = root_dir
        self.scale = scale
        self.patch_size = patch_size
        self.is_train = is_train
        
        self.hr_dir = os.path.join(root_dir, 'HR')
        self.lr_dir = os.path.join(root_dir, 'LR')
        
        self.image_files = self._get_image_files()
        
        if is_train:
            self.transform = self._train_transform
        else:
            self.transform = self._val_transform
    
    def _get_image_files(self):
        if os.path.exists(self.hr_dir):
            files = sorted([f for f in os.listdir(self.hr_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))])
            if len(files) > 0:
                return files
        
        files = sorted([f for f in os.listdir(self.root_dir) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))])
        return files
    
    def _load_image(self, img_path):
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            img = np.array(Image.open(img_path).convert('L'))
        return img
    
    def _train_transform(self, hr_img):
        hr_patch_size = self.patch_size
        lr_patch_size = hr_patch_size // self.scale
        
        h, w = hr_img.shape
        if h < hr_patch_size or w < hr_patch_size:
            scale_factor = max(hr_patch_size / h, hr_patch_size / w)
            new_h = int(np.ceil(h * scale_factor))
            new_w = int(np.ceil(w * scale_factor))
            hr_img = cv2.resize(hr_img, (new_w, new_h), 
                               interpolation=cv2.INTER_NEAREST)
            h, w = hr_img.shape
        
        y = random.randint(0, h - hr_patch_size)
        x = random.randint(0, w - hr_patch_size)
        hr_patch = hr_img[y:y+hr_patch_size, x:x+hr_patch_size]
        
        if random.random() < 0.5:
            hr_patch = np.fliplr(hr_patch)
        
        if random.random() < 0.5:
            hr_patch = np.flipud(hr_patch)
        
        angle = random.choice([0, 90, 180, 270])
        if angle != 0:
            hr_patch = np.rot90(hr_patch, k=angle // 90)
        
        lr_patch = cv2.resize(hr_patch, (lr_patch_size, lr_patch_size), 
                             interpolation=cv2.INTER_NEAREST)
        
        lr_tensor = torch.from_numpy(lr_patch.copy()).float().unsqueeze(0) / 255.0
        hr_tensor = torch.from_numpy(hr_patch.copy()).float().unsqueeze(0) / 255.0
        
        return lr_tensor, hr_tensor
    
    def _val_transform(self, hr_img):
        h, w = hr_img.shape
        new_h = h - (h % self.scale)
        new_w = w - (w % self.scale)
        hr_img = hr_img[:new_h, :new_w]
        
        lr_img = cv2.resize(hr_img, (new_w // self.scale, new_h // self.scale), 
                           interpolation=cv2.INTER_NEAREST)
        
        lr_tensor = torch.from_numpy(lr_img.copy()).float().unsqueeze(0) / 255.0
        hr_tensor = torch.from_numpy(hr_img.copy()).float().unsqueeze(0) / 255.0
        
        return lr_tensor, hr_tensor
    
    def __len__(self):
        return len(self.image_files)
    
    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        
        hr_path = os.path.join(self.hr_dir, img_name) if os.path.exists(self.hr_dir) else \
                  os.path.join(self.root_dir, img_name)
        
        hr_img = self._load_image(hr_path)
        
        lr_path = os.path.join(self.lr_dir, img_name) if os.path.exists(self.lr_dir) else None
        
        if lr_path and os.path.exists(lr_path):
            lr_img = self._load_image(lr_path)
            lr_tensor = torch.from_numpy(lr_img.copy()).float().unsqueeze(0) / 255.0
            hr_tensor = torch.from_numpy(hr_img.copy()).float().unsqueeze(0) / 255.0
            return lr_tensor, hr_tensor
        
        return self.transform(hr_img)


def get_dataloaders(config):
    train_dataset = FLIRDataset(
        root_dir=config['train_dir'],
        scale=config['scale'],
        patch_size=config['patch_size'],
        is_train=True
    )
    
    val_dataset = FLIRDataset(
        root_dir=config['val_dir'],
        scale=config['scale'],
        is_train=False
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True,
        num_workers=config['num_workers'],
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=config['num_workers'],
        pin_memory=True
    )
    
    return train_loader, val_loader


def get_test_loader(config):
    test_dataset = FLIRDataset(
        root_dir=config['test_dir'],
        scale=config['scale'],
        is_train=False
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=0,
        pin_memory=True
    )
    
    return test_loader
