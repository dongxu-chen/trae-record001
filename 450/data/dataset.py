import os
import glob
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from typing import List, Tuple, Optional


class ReflectionDataset(Dataset):
    def __init__(
        self,
        image_dir: str,
        transmission_dir: Optional[str] = None,
        reflection_dir: Optional[str] = None,
        polarization_dir: Optional[str] = None,
        image_size: Tuple[int, int] = (256, 256),
        transform=None,
        use_polarization: bool = False,
        mode: str = 'train'
    ):
        self.image_dir = image_dir
        self.transmission_dir = transmission_dir
        self.reflection_dir = reflection_dir
        self.polarization_dir = polarization_dir
        self.image_size = image_size
        self.transform = transform
        self.use_polarization = use_polarization
        self.mode = mode
        
        self.image_paths = self._get_image_paths(image_dir)
        
        if transmission_dir and mode == 'train':
            self.transmission_paths = self._get_image_paths(transmission_dir)
            assert len(self.image_paths) == len(self.transmission_paths), \
                f"Image count ({len(self.image_paths)}) != transmission count ({len(self.transmission_paths)})"
        
        if reflection_dir and mode == 'train':
            self.reflection_paths = self._get_image_paths(reflection_dir)
            assert len(self.image_paths) == len(self.reflection_paths), \
                f"Image count ({len(self.image_paths)}) != reflection count ({len(self.reflection_paths)})"
        
        if polarization_dir and use_polarization:
            self.polarization_paths = self._get_image_paths(polarization_dir)
            assert len(self.image_paths) == len(self.polarization_paths), \
                f"Image count ({len(self.image_paths)}) != polarization count ({len(self.polarization_paths)})"
        
        self.default_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def _get_image_paths(self, directory: str) -> List[str]:
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        image_paths = []
        for ext in extensions:
            image_paths.extend(glob.glob(os.path.join(directory, ext)))
            image_paths.extend(glob.glob(os.path.join(directory, ext.upper())))
        return sorted(image_paths)

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> dict:
        img_path = self.image_paths[idx]
        image = self._load_image(img_path)
        
        if self.transform:
            image = self.transform(image)
        else:
            image = self.default_transform(image)
        
        sample = {'image': image, 'path': img_path}
        
        if self.use_polarization and hasattr(self, 'polarization_paths'):
            pol_path = self.polarization_paths[idx]
            pol_image = self._load_image(pol_path)
            if self.transform:
                pol_image = self.transform(pol_image)
            else:
                pol_image = self.default_transform(pol_image)
            sample['polarization'] = pol_image
        
        if self.mode == 'train':
            if self.transmission_dir and hasattr(self, 'transmission_paths'):
                t_path = self.transmission_paths[idx]
                transmission = self._load_image(t_path)
                transmission = transforms.ToTensor()(transmission)
                sample['transmission'] = transmission
            
            if self.reflection_dir and hasattr(self, 'reflection_paths'):
                r_path = self.reflection_paths[idx]
                reflection = self._load_image(r_path)
                reflection = transforms.ToTensor()(reflection)
                sample['reflection'] = reflection
        
        return sample

    def _load_image(self, path: str) -> np.ndarray:
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not load image: {path}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, self.image_size)
        return img


class PolarizationProcessor:
    @staticmethod
    def compute_stokes(images: List[np.ndarray], angles: List[float]) -> np.ndarray:
        assert len(images) == len(angles), "Number of images must match number of angles"
        
        images_gray = []
        for img in images:
            if len(img.shape) == 3:
                img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.shape[-1] == 3 else img[..., 0]
            else:
                img_gray = img
            images_gray.append(img_gray.astype(np.float32))
        
        images = np.array(images_gray, dtype=np.float32)
        angles = np.array(angles, dtype=np.float32)
        
        I0 = images[np.argmin(np.abs(angles - 0))]
        I45 = images[np.argmin(np.abs(angles - 45))]
        I90 = images[np.argmin(np.abs(angles - 90))]
        I135 = images[np.argmin(np.abs(angles - 135))]
        
        S0 = (I0 + I90 + I45 + I135) / 2.0
        S1 = I0 - I90
        S2 = I45 - I135
        
        stokes = np.stack([S0, S1, S2], axis=-1)
        return stokes

    @staticmethod
    def compute_degree_of_polarization(stokes: np.ndarray) -> np.ndarray:
        S0 = stokes[..., 0]
        S1 = stokes[..., 1]
        S2 = stokes[..., 2]
        
        numerator = np.sqrt(S1**2 + S2**2)
        denominator = S0 + 1e-8
        dolp = np.clip(numerator / denominator, 0, 1)
        
        return dolp

    @staticmethod
    def compute_angle_of_polarization(stokes: np.ndarray) -> np.ndarray:
        S1 = stokes[..., 1]
        S2 = stokes[..., 2]
        
        aop = 0.5 * np.arctan2(S2, S1 + 1e-8)
        aop = (aop + np.pi / 2) % np.pi
        
        return aop

    @staticmethod
    def extract_reflection_mask(stokes: np.ndarray, threshold: float = 0.3) -> np.ndarray:
        dolp = PolarizationProcessor.compute_degree_of_polarization(stokes)
        mask = (dolp > threshold).astype(np.float32)
        return mask

    @staticmethod
    def fuse_polarization(rgb_image: np.ndarray, stokes: np.ndarray) -> np.ndarray:
        dolp = PolarizationProcessor.compute_degree_of_polarization(stokes)
        aop = PolarizationProcessor.compute_angle_of_polarization(stokes)
        
        dolp_norm = (dolp - dolp.min()) / (dolp.max() - dolp.min() + 1e-8)
        aop_norm = (aop - aop.min()) / (aop.max() - aop.min() + 1e-8)
        
        fused = np.concatenate([rgb_image, dolp_norm[..., np.newaxis], aop_norm[..., np.newaxis]], axis=-1)
        return fused


def get_data_loader(
    image_dir: str,
    batch_size: int = 4,
    shuffle: bool = True,
    num_workers: int = 0,
    **kwargs
) -> DataLoader:
    dataset = ReflectionDataset(image_dir=image_dir, **kwargs)
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True
    )
    return dataloader


def denormalize(tensor: torch.Tensor) -> torch.Tensor:
    mean = torch.tensor([0.485, 0.456, 0.406], device=tensor.device).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=tensor.device).view(1, 3, 1, 1)
    return tensor * std + mean


def tensor_to_numpy(tensor: torch.Tensor, denorm: bool = True) -> np.ndarray:
    if denorm:
        tensor = denormalize(tensor)
    tensor = torch.clamp(tensor, 0, 1)
    img_np = tensor.permute(0, 2, 3, 1).cpu().numpy()
    return (img_np * 255).astype(np.uint8)
