import numpy as np
import cv2
import os
import glob
from pathlib import Path
import json
import pickle


class SFUGreyBallDataset:
    """
    SFU GreyBall Dataset Loader for Color Constancy.
    
    The dataset contains images captured under various illuminants
    with ground truth illuminant colors measured using a grey ball.
    
    Expected dataset structure:
    root/
        images/
            img_0001.png
            img_0002.png
            ...
        ground_truth.txt or metadata.json
        masks/ (optional)
            mask_0001.png
            ...
    """
    
    def __init__(self, root_dir, transform=None, target_size=None):
        """
        Initialize dataset loader.
        
        Args:
            root_dir: Root directory of the dataset
            transform: Optional transform to apply to images
            target_size: Optional target size (height, width) for resizing
        """
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.target_size = target_size
        self.images = []
        self.ground_truths = []
        self.masks = []
        self.metadata = {}
        
        self._load_dataset()
    
    def _load_dataset(self):
        """Load dataset from directory."""
        img_dir = self.root_dir / 'images'
        mask_dir = self.root_dir / 'masks'
        
        if img_dir.exists():
            img_paths = sorted(glob.glob(str(img_dir / '*.*')))
        else:
            img_paths = sorted(glob.glob(str(self.root_dir / '*.*')))
            img_paths = [p for p in img_paths if p.endswith(('.png', '.jpg', '.jpeg', '.tif', '.bmp'))]
        
        gt_file = self.root_dir / 'ground_truth.txt'
        gt_json = self.root_dir / 'metadata.json'
        
        if gt_file.exists():
            self._load_ground_truth_from_txt(gt_file)
        elif gt_json.exists():
            self._load_ground_truth_from_json(gt_json)
        else:
            print(f"Warning: No ground truth file found in {self.root_dir}")
            self.ground_truths = [np.ones(3) for _ in img_paths]
        
        for i, img_path in enumerate(img_paths):
            img = cv2.imread(img_path)
            if img is None:
                continue
            
            if self.target_size is not None:
                img = cv2.resize(img, (self.target_size[1], self.target_size[0]))
            
            if self.transform is not None:
                img = self.transform(img)
            
            self.images.append(img)
            
            mask_path = mask_dir / f'mask_{i:04d}.png' if mask_dir.exists() else None
            if mask_path is not None and mask_path.exists():
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if self.target_size is not None:
                    mask = cv2.resize(mask, (self.target_size[1], self.target_size[0]))
                self.masks.append(mask > 0)
            else:
                self.masks.append(None)
        
        self.metadata['num_samples'] = len(self.images)
        print(f"Loaded {len(self.images)} images from {self.root_dir}")
    
    def _load_ground_truth_from_txt(self, gt_file):
        """Load ground truth from text file."""
        self.ground_truths = []
        with open(gt_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    rgb = np.array([float(parts[0]), float(parts[1]), float(parts[2])])
                    rgb = rgb / np.linalg.norm(rgb)
                    self.ground_truths.append(rgb)
    
    def _load_ground_truth_from_json(self, gt_file):
        """Load ground truth from JSON file."""
        with open(gt_file, 'r') as f:
            data = json.load(f)
        
        self.ground_truths = []
        if 'images' in data:
            for img_data in data['images']:
                if 'illuminant' in img_data:
                    rgb = np.array(img_data['illuminant'], dtype=np.float32)
                    rgb = rgb / np.linalg.norm(rgb)
                    self.ground_truths.append(rgb)
                elif 'gt_rgb' in img_data:
                    rgb = np.array(img_data['gt_rgb'], dtype=np.float32)
                    rgb = rgb / np.linalg.norm(rgb)
                    self.ground_truths.append(rgb)
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        """Get sample by index."""
        return {
            'image': self.images[idx],
            'ground_truth': self.ground_truths[idx] if idx < len(self.ground_truths) else np.ones(3),
            'mask': self.masks[idx] if idx < len(self.masks) else None,
            'index': idx
        }
    
    def get_all(self):
        """Get all samples."""
        return self.images, self.ground_truths, self.masks
    
    def split(self, train_ratio=0.8, shuffle=True, seed=42):
        """
        Split dataset into train and test sets.
        
        Args:
            train_ratio: Ratio of training data
            shuffle: Whether to shuffle before splitting
            seed: Random seed
        
        Returns:
            train_dataset, test_dataset
        """
        indices = np.arange(len(self.images))
        if shuffle:
            np.random.seed(seed)
            np.random.shuffle(indices)
        
        split_idx = int(len(indices) * train_ratio)
        train_indices = indices[:split_idx]
        test_indices = indices[split_idx:]
        
        train_data = SFUGreyBallDataset.__new__(SFUGreyBallDataset)
        train_data.root_dir = self.root_dir
        train_data.transform = self.transform
        train_data.target_size = self.target_size
        train_data.images = [self.images[i] for i in train_indices]
        train_data.ground_truths = [self.ground_truths[i] for i in train_indices]
        train_data.masks = [self.masks[i] for i in train_indices]
        train_data.metadata = {'split': 'train', 'num_samples': len(train_indices)}
        
        test_data = SFUGreyBallDataset.__new__(SFUGreyBallDataset)
        test_data.root_dir = self.root_dir
        test_data.transform = self.transform
        test_data.target_size = self.target_size
        test_data.images = [self.images[i] for i in test_indices]
        test_data.ground_truths = [self.ground_truths[i] for i in test_indices]
        test_data.masks = [self.masks[i] for i in test_indices]
        test_data.metadata = {'split': 'test', 'num_samples': len(test_indices)}
        
        return train_data, test_data


def generate_synthetic_dataset(num_samples=50, image_size=(128, 128), 
                                seed=42, save_dir=None):
    """
    Generate synthetic dataset for color constancy evaluation.
    
    Creates images with known illuminants to evaluate algorithms.
    
    Args:
        num_samples: Number of samples to generate
        image_size: Size of generated images (height, width)
        seed: Random seed
        save_dir: Optional directory to save generated dataset
    
    Returns:
        images: Generated images (N, H, W, 3)
        illuminants: Ground truth illuminants (N, 3)
        masks: Optional masks
    """
    np.random.seed(seed)
    
    images = []
    illuminants = []
    masks = []
    
    standard_illuminants = [
        (1.0, 1.0, 1.0),
        (0.9, 0.85, 0.7),
        (0.7, 0.8, 1.0),
        (1.0, 0.8, 0.6),
        (0.6, 0.8, 0.9),
        (1.0, 0.6, 0.5),
        (0.5, 0.7, 1.0),
        (0.95, 0.9, 0.7),
        (0.7, 0.9, 0.85),
        (0.85, 0.75, 0.95),
    ]
    
    for i in range(num_samples):
        base_colors = np.random.rand(5, 3) * 200 + 55
        
        img = np.zeros((image_size[0], image_size[1], 3), dtype=np.uint8)
        
        h, w = image_size
        grid_h = h // 2
        grid_w = w // 3
        
        for row in range(2):
            for col in range(3):
                color_idx = row * 3 + col
                if color_idx < len(base_colors):
                    color = base_colors[color_idx].astype(np.uint8)
                    img[row*grid_h:(row+1)*grid_h, col*grid_w:(col+1)*grid_w] = color
        
        center_x = w // 2
        center_y = h // 2
        radius = min(w, h) // 8
        cv2.circle(img, (center_x, center_y), radius, (245, 245, 245), -1)
        
        gray_patch = np.ones((20, 20, 3), dtype=np.uint8) * 128
        img[h-30:h-10, w-30:w-10] = gray_patch
        
        noise = np.random.normal(0, 10, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        illum_idx = i % len(standard_illuminants)
        illum = np.array(standard_illuminants[illum_idx], dtype=np.float32)
        if num_samples > len(standard_illuminants):
            illum = illum + np.random.randn(3) * 0.1
            illum = np.abs(illum)
        
        illum = illum / np.linalg.norm(illum)
        
        img_float = img.astype(np.float32)
        img_corrected = img_float * (1.0 / (illum + 1e-8)).reshape(1, 1, 3)
        img_corrected = np.clip(img_corrected, 0, 255).astype(np.uint8)
        
        img_balanced = img_float * (illum / np.max(illum)).reshape(1, 1, 3)
        img_balanced = np.clip(img_balanced, 0, 255).astype(np.uint8)
        
        images.append(img_balanced)
        illuminants.append(illum)
        masks.append(None)
    
    if save_dir is not None:
        save_dir = Path(save_dir)
        (save_dir / 'images').mkdir(parents=True, exist_ok=True)
        (save_dir / 'masks').mkdir(parents=True, exist_ok=True)
        
        for i, (img, illum) in enumerate(zip(images, illuminants)):
            cv2.imwrite(str(save_dir / 'images' / f'img_{i:04d}.png'), img)
        
        with open(save_dir / 'ground_truth.txt', 'w') as f:
            for illum in illuminants:
                f.write(f'{illum[0]:.6f} {illum[1]:.6f} {illum[2]:.6f}\n')
        
        with open(save_dir / 'reference' / 'reference.json', 'w') as f:
            json.dump({'illuminants': [list(i) for i in illuminants]}, f, indent=2)
        
        print(f"Synthetic dataset saved to {save_dir}")
    
    return images, illuminants, masks


def apply_illuminant(image, illuminant):
    """
    Apply an illuminant to an image (simulate color cast).
    
    Args:
        image: Input image (H, W, 3)
        illuminant: Illuminant RGB values [R, G, B]
    
    Returns:
        result: Image with illuminant applied
    """
    img_float = image.astype(np.float32)
    illum = np.array(illuminant, dtype=np.float32).reshape(1, 1, 3)
    result = img_float * illum
    result = np.clip(result, 0, 255).astype(np.uint8)
    return result


def create_evaluation_protocol(dataset, methods, repeat=1):
    """
    Create evaluation protocol for color constancy methods.
    
    Args:
        dataset: Dataset object with images and ground truths
        methods: Dictionary of method names to functions
        repeat: Number of repetitions for stochastic methods
    
    Returns:
        protocol: Evaluation protocol dictionary
    """
    protocol = {
        'dataset_size': len(dataset),
        'methods': list(methods.keys()),
        'repeat': repeat,
        'metrics': ['angular_error', 'mean', 'median', 'trimean', 'best25', 'worst25']
    }
    return protocol
