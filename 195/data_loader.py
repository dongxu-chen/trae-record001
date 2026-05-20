import numpy as np
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
import spectral as spy
import torch
from torch.utils.data import Dataset, DataLoader, Subset
import scipy.io as sio
import os


def load_indian_pines(data_dir='./data'):
    os.makedirs(data_dir, exist_ok=True)
    
    data_url = 'http://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat'
    gt_url = 'http://www.ehu.eus/ccwintco/uploads/c/c4/Indian_pines_gt.mat'
    
    data_path = os.path.join(data_dir, 'Indian_pines_corrected.mat')
    gt_path = os.path.join(data_dir, 'Indian_pines_gt.mat')
    
    if not os.path.exists(data_path):
        import urllib.request
        print('Downloading Indian Pines data...')
        urllib.request.urlretrieve(data_url, data_path)
        urllib.request.urlretrieve(gt_url, gt_path)
        print('Download complete!')
    
    data = sio.loadmat(data_path)['indian_pines_corrected']
    gt = sio.loadmat(gt_path)['indian_pines_gt']
    
    return data, gt


def apply_pca(data, n_components=30, return_pca_obj=False):
    h, w, c = data.shape
    data_reshaped = data.reshape(-1, c)
    
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_reshaped)
    
    pca = PCA(n_components=n_components)
    data_pca = pca.fit_transform(data_scaled)
    
    explained_variance = np.sum(pca.explained_variance_ratio_)
    print(f'PCA with {n_components} components - explained variance ratio: {explained_variance:.4f}')
    
    data_pca_reshaped = data_pca.reshape(h, w, n_components)
    
    if return_pca_obj:
        return data_pca_reshaped, pca, scaler
    return data_pca_reshaped


def find_optimal_pca_components(data, variance_threshold=0.99, max_components=50):
    h, w, c = data.shape
    data_reshaped = data.reshape(-1, c)
    
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_reshaped)
    
    pca = PCA()
    pca.fit(data_scaled)
    
    cumulative_variance = np.cumsum(pca.explained_variance_ratio_)
    n_components = np.argmax(cumulative_variance >= variance_threshold) + 1
    n_components = min(n_components, max_components, c)
    
    print(f'Optimal PCA components for {variance_threshold*100:.1f}% variance: {n_components}')
    print(f'Actual variance explained: {cumulative_variance[n_components-1]:.4f}')
    
    return n_components, cumulative_variance, pca


def create_patches(data, gt, patch_size=5, remove_zero_labels=True):
    h, w, c = data.shape
    padding = patch_size // 2
    padded_data = np.pad(data, ((padding, padding), (padding, padding), (0, 0)), mode='reflect')
    
    patches = []
    labels = []
    coordinates = []
    
    for i in range(h):
        for j in range(w):
            if remove_zero_labels and gt[i, j] == 0:
                continue
            patch = padded_data[i:i+patch_size, j:j+patch_size, :]
            patches.append(patch)
            labels.append(gt[i, j] - 1)
            coordinates.append((i, j))
    
    return np.array(patches), np.array(labels), np.array(coordinates)


def split_data(patches, labels, train_ratio=0.15, val_ratio=0.05, random_state=42):
    n_samples = len(patches)
    indices = np.arange(n_samples)
    
    train_indices, test_indices = train_test_split(
        indices, test_size=1-train_ratio-val_ratio, 
        stratify=labels, random_state=random_state
    )
    
    val_ratio_adjusted = val_ratio / (train_ratio + val_ratio)
    train_indices, val_indices = train_test_split(
        train_indices, test_size=val_ratio_adjusted,
        stratify=labels[train_indices], random_state=random_state
    )
    
    return train_indices, val_indices, test_indices


def create_cv_splits(labels, n_splits=5, random_state=42):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    indices = np.arange(len(labels))
    splits = []
    
    for fold, (train_idx, test_idx) in enumerate(skf.split(indices, labels)):
        train_idx, val_idx = train_test_split(
            train_idx, test_size=0.1, stratify=labels[train_idx], 
            random_state=random_state
        )
        splits.append((train_idx, val_idx, test_idx))
        print(f'Fold {fold+1}: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}')
    
    return splits


class HyperSpectralDataset(Dataset):
    def __init__(self, patches, labels, transform=None):
        self.patches = patches
        self.labels = labels
        self.transform = transform
        
    def __len__(self):
        return len(self.patches)
    
    def __getitem__(self, idx):
        patch = self.patches[idx]
        label = self.labels[idx]
        
        if self.transform:
            patch = self.transform(patch)
        
        patch = np.transpose(patch, (2, 0, 1))
        patch = np.expand_dims(patch, axis=0)
        
        return torch.FloatTensor(patch), torch.LongTensor([label]).squeeze()


def create_data_loaders(data, gt, patch_size=5, n_components=30, 
                        batch_size=64, train_ratio=0.15, val_ratio=0.05,
                        train_transform=None, random_state=42,
                        auto_pca=False, variance_threshold=0.99):
    
    if auto_pca:
        n_components, _, _ = find_optimal_pca_components(data, variance_threshold)
    
    data_pca, pca_obj, scaler = apply_pca(data, n_components=n_components, return_pca_obj=True)
    patches, labels, coordinates = create_patches(data_pca, gt, patch_size=patch_size)
    
    train_indices, val_indices, test_indices = split_data(
        patches, labels, train_ratio, val_ratio, random_state
    )
    
    train_dataset = HyperSpectralDataset(
        patches[train_indices], labels[train_indices], transform=train_transform
    )
    val_dataset = HyperSpectralDataset(
        patches[val_indices], labels[val_indices], transform=None
    )
    test_dataset = HyperSpectralDataset(
        patches[test_indices], labels[test_indices], transform=None
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    info = {
        'n_components': n_components,
        'pca': pca_obj,
        'scaler': scaler,
        'coordinates': coordinates,
        'train_indices': train_indices,
        'val_indices': val_indices,
        'test_indices': test_indices
    }
    
    return train_loader, val_loader, test_loader, labels, info


def create_cv_data_loaders(patches, labels, train_idx, val_idx, test_idx, 
                          batch_size=64, train_transform=None):
    
    train_dataset = HyperSpectralDataset(
        patches[train_idx], labels[train_idx], transform=train_transform
    )
    val_dataset = HyperSpectralDataset(
        patches[val_idx], labels[val_idx], transform=None
    )
    test_dataset = HyperSpectralDataset(
        patches[test_idx], labels[test_idx], transform=None
    )
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    return train_loader, val_loader, test_loader


def prepare_cv_data(data, gt, patch_size=5, n_components=30, auto_pca=False, 
                   variance_threshold=0.99):
    
    if auto_pca:
        n_components, _, _ = find_optimal_pca_components(data, variance_threshold)
    
    data_pca, pca_obj, scaler = apply_pca(data, n_components=n_components, return_pca_obj=True)
    patches, labels, coordinates = create_patches(data_pca, gt, patch_size=patch_size)
    
    info = {
        'n_components': n_components,
        'pca': pca_obj,
        'scaler': scaler,
        'coordinates': coordinates
    }
    
    return patches, labels, info
