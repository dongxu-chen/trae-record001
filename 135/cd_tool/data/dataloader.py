import os
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from typing import Tuple, Optional, List


class MaskedNormalize:
    def __init__(self, 
                 invalid_value: float = 0.0, 
                 eps: float = 1e-8,
                 use_masked_stats: bool = True):
        self.invalid_value = invalid_value
        self.eps = eps
        self.use_masked_stats = use_masked_stats

    def __call__(self, tensor: torch.Tensor, mask: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        if mask is None:
            mask = (tensor != self.invalid_value).any(dim=0, keepdim=True).float()
        
        if self.use_masked_stats:
            valid_mask = mask.repeat(tensor.shape[0], 1, 1)
            valid_pixels = tensor[valid_mask > 0]
            if len(valid_pixels) > 0:
                mean = valid_pixels.mean()
                std = valid_pixels.std() + self.eps
            else:
                mean = tensor.mean()
                std = tensor.std() + self.eps
        else:
            mean = tensor.mean()
            std = tensor.std() + self.eps
        
        normalized = (tensor - mean) / std
        normalized = normalized * mask
        return normalized, mask


class ChangeDetectionDataset(Dataset):
    def __init__(self, 
                 root_dir: str,
                 img1_dir: str = 'A',
                 img2_dir: str = 'B',
                 label_dir: Optional[str] = 'label',
                 mask_dir: Optional[str] = None,
                 transform=None,
                 img_size: Tuple[int, int] = (256, 256),
                 use_masked_normalize: bool = True,
                 invalid_value: float = 0.0):
        self.root_dir = root_dir
        self.img1_dir = os.path.join(root_dir, img1_dir)
        self.img2_dir = os.path.join(root_dir, img2_dir)
        self.label_dir = os.path.join(root_dir, label_dir) if label_dir else None
        self.mask_dir = os.path.join(root_dir, mask_dir) if mask_dir else None
        self.transform = transform
        self.img_size = img_size
        self.use_masked_normalize = use_masked_normalize
        self.masked_normalize = MaskedNormalize(invalid_value=invalid_value)
        self.img_files = sorted(os.listdir(self.img1_dir))

    def __len__(self) -> int:
        return len(self.img_files)

    def __getitem__(self, idx: int):
        img_name = self.img_files[idx]
        img1_path = os.path.join(self.img1_dir, img_name)
        img2_path = os.path.join(self.img2_dir, img_name)
        
        img1 = cv2.imread(img1_path, cv2.IMREAD_UNCHANGED)
        img2 = cv2.imread(img2_path, cv2.IMREAD_UNCHANGED)
        
        if len(img1.shape) == 2:
            img1 = cv2.cvtColor(img1, cv2.COLOR_GRAY2RGB)
        elif img1.shape[2] == 4:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGRA2RGB)
        else:
            img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
            
        if len(img2.shape) == 2:
            img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2RGB)
        elif img2.shape[2] == 4:
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGRA2RGB)
        else:
            img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
        
        img1 = cv2.resize(img1, self.img_size)
        img2 = cv2.resize(img2, self.img_size)
        
        valid_mask = None
        if self.mask_dir:
            mask_path = os.path.join(self.mask_dir, img_name)
            valid_mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            valid_mask = cv2.resize(valid_mask, self.img_size)
            valid_mask = (valid_mask > 127).astype(np.float32)
        
        label = None
        if self.label_dir:
            label_path = os.path.join(self.label_dir, img_name)
            label = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE)
            label = cv2.resize(label, self.img_size)
            label = (label > 127).astype(np.float32)
        
        img1 = torch.from_numpy(img1.transpose(2, 0, 1)).float() / 255.0
        img2 = torch.from_numpy(img2.transpose(2, 0, 1)).float() / 255.0
        
        if valid_mask is not None:
            valid_mask = torch.from_numpy(valid_mask).float().unsqueeze(0)
            if self.use_masked_normalize:
                img1, _ = self.masked_normalize(img1, valid_mask)
                img2, _ = self.masked_normalize(img2, valid_mask)
        elif self.use_masked_normalize:
            img1, _ = self.masked_normalize(img1)
            img2, _ = self.masked_normalize(img2)
        
        if self.transform:
            img1 = self.transform(img1)
            img2 = self.transform(img2)
        
        outputs = [img1, img2]
        
        if label is not None:
            label = torch.from_numpy(label).float().unsqueeze(0)
            outputs.append(label)
        
        if valid_mask is not None:
            outputs.append(valid_mask)
        
        return tuple(outputs)


def get_transforms(train: bool = True, 
                   mean: Optional[List[float]] = None,
                   std: Optional[List[float]] = None):
    transform_list = [transforms.ToPILImage()]
    
    if train:
        transform_list.extend([
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(15)
        ])
    
    transform_list.append(transforms.ToTensor())
    
    if mean is not None and std is not None:
        transform_list.append(transforms.Normalize(mean=mean, std=std))
    
    return transforms.Compose(transform_list)


class ImagePairLoader:
    def __init__(self, img_size: Tuple[int, int] = (256, 256)):
        self.img_size = img_size
        self.masked_normalize = MaskedNormalize()

    def load_image(self, path: str) -> np.ndarray:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, self.img_size)
        return img

    def load_pair(self, path1: str, path2: str) -> Tuple[np.ndarray, np.ndarray]:
        img1 = self.load_image(path1)
        img2 = self.load_image(path2)
        return img1, img2

    def to_tensor(self, img: np.ndarray, 
                  use_masked_norm: bool = True,
                  mask: Optional[np.ndarray] = None) -> torch.Tensor:
        img_tensor = torch.from_numpy(img.transpose(2, 0, 1)).float() / 255.0
        
        if use_masked_norm:
            if mask is not None:
                mask_tensor = torch.from_numpy(mask).float().unsqueeze(0)
                img_tensor, _ = self.masked_normalize(img_tensor, mask_tensor)
            else:
                img_tensor, _ = self.masked_normalize(img_tensor)
        
        return img_tensor.unsqueeze(0)

    @staticmethod
    def compute_dataset_stats(dataset: Dataset, num_samples: int = 100) -> Tuple[List[float], List[float]]:
        all_pixels = []
        for i in range(min(num_samples, len(dataset))):
            data = dataset[i]
            img1 = data[0]
            all_pixels.append(img1.view(3, -1))
        
        all_pixels = torch.cat(all_pixels, dim=1)
        mean = all_pixels.mean(dim=1).tolist()
        std = all_pixels.std(dim=1).tolist()
        return mean, std
