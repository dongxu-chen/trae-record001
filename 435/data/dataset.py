import os
import cv2
import numpy as np
from torch.utils.data import Dataset, DataLoader
from typing import List, Tuple, Optional
from config import Config
from .rain_synthesizer import RandomRainSynthesizer


class RainRemovalDataset(Dataset):
    def __init__(self, image_paths: List[str], transform=None, use_random_intensity: bool = True):
        self.image_paths = image_paths
        self.transform = transform
        self.rain_synthesizer = RandomRainSynthesizer() if use_random_intensity else None
        self.use_random_intensity = use_random_intensity

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[np.ndarray, np.ndarray, str]:
        img_path = self.image_paths[idx]
        clean_image = cv2.imread(img_path)
        clean_image = cv2.cvtColor(clean_image, cv2.COLOR_BGR2RGB)
        clean_image = cv2.resize(clean_image, Config.IMAGE_SIZE)
        
        if clean_image.dtype != np.float32:
            clean_image = clean_image.astype(np.float32) / 255.0
        
        if self.use_random_intensity:
            rainy_image, intensity = self.rain_synthesizer(clean_image)
        else:
            rainy_image = clean_image.copy()
            intensity = 'none'
        
        if self.transform:
            clean_image = self.transform(clean_image)
            rainy_image = self.transform(rainy_image)
        
        return rainy_image, clean_image, intensity


def get_image_paths(data_dir: str) -> List[str]:
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    image_paths = []
    
    if not os.path.exists(data_dir):
        return image_paths
    
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith(image_extensions):
                image_paths.append(os.path.join(root, file))
    
    return image_paths


def create_dataloaders(train_dir: str, test_dir: str, batch_size: int = Config.BATCH_SIZE):
    train_paths = get_image_paths(train_dir)
    test_paths = get_image_paths(test_dir)
    
    train_dataset = RainRemovalDataset(train_paths, use_random_intensity=True)
    test_dataset = RainRemovalDataset(test_paths, use_random_intensity=True)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=0)
    
    return train_loader, test_loader
