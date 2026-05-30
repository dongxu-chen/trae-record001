import os
import cv2
from torch.utils.data import Dataset, DataLoader
from config import Config
from utils.helpers import get_file_list
from .transforms import get_transforms


class SaliencyDataset(Dataset):
    def __init__(self, image_paths, image_size=None, transform=None):
        if image_size is None:
            image_size = Config.IMAGE_SIZE
        
        self.image_paths = image_paths
        self.image_size = image_size
        
        if transform is None:
            self.transform = get_transforms(image_size, train=False)
        else:
            self.transform = transform
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        original_h, original_w = image.shape[:2]
        
        if self.transform:
            tensor = self.transform(image)
        else:
            tensor = image
        
        return {
            'tensor': tensor,
            'original_size': (original_h, original_w),
            'image_path': image_path,
            'filename': os.path.basename(image_path)
        }


class SaliencyInferenceDataset(Dataset):
    def __init__(self, image_dir, image_size=None, extensions=None):
        if image_size is None:
            image_size = Config.IMAGE_SIZE
        
        if extensions is None:
            extensions = Config.ALLOWED_EXTENSIONS
        
        self.image_paths = get_file_list(image_dir, extensions)
        self.image_size = image_size
        self.transform = get_transforms(image_size, train=False)
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        original_h, original_w = image.shape[:2]
        
        tensor = self.transform(image)
        
        return {
            'tensor': tensor,
            'original_size': (original_h, original_w),
            'image_path': image_path,
            'filename': os.path.basename(image_path)
        }


def get_dataloader(image_paths, batch_size=None, image_size=None, shuffle=False, num_workers=0):
    if batch_size is None:
        batch_size = Config.BATCH_SIZE
    if image_size is None:
        image_size = Config.IMAGE_SIZE
    
    dataset = SaliencyDataset(image_paths, image_size)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return dataloader


def get_inference_dataloader(image_dir, batch_size=None, image_size=None, num_workers=0):
    if batch_size is None:
        batch_size = Config.BATCH_SIZE
    if image_size is None:
        image_size = Config.IMAGE_SIZE
    
    dataset = SaliencyInferenceDataset(image_dir, image_size)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return dataloader
