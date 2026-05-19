import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from monai.data import Dataset, CacheDataset
from monai.transforms import (
    Compose,
    EnsureChannelFirstd,
    ScaleIntensityd,
    NormalizeIntensityd,
    RandFlipd,
    RandRotated,
    RandZoomd,
    ToTensord,
    ConcatItemsd,
    RandGaussianNoised,
)
import warnings
warnings.filterwarnings('ignore')


class MultiModalFusionNet(nn.Module):
    def __init__(
        self,
        hsi_channels=200,
        lidar_channels=4,
        num_classes=10,
        spatial_dims=2,
        fusion_type='concatenate',
        hidden_dim=512,
    ):
        super().__init__()
        
        self.hsi_channels = hsi_channels
        self.lidar_channels = lidar_channels
        self.num_classes = num_classes
        self.fusion_type = fusion_type
        
        self.hsi_encoder = self._build_encoder(hsi_channels, hidden_dim // 2, spatial_dims)
        self.lidar_encoder = self._build_encoder(lidar_channels, hidden_dim // 2, spatial_dims)
        
        if fusion_type == 'concatenate':
            fusion_dim = hidden_dim
        elif fusion_type == 'attention':
            fusion_dim = hidden_dim // 2
            self.attention_fusion = CrossAttentionFusion(
                dim=hidden_dim // 2,
                num_heads=8,
                spatial_dims=spatial_dims,
            )
        elif fusion_type == 'bilinear':
            fusion_dim = (hidden_dim // 2) * (hidden_dim // 2) // 64
        elif fusion_type == 'gated':
            fusion_dim = hidden_dim // 2
            self.gated_fusion = GatedFusion(dim=hidden_dim // 2)
        else:
            raise ValueError(f"Unsupported fusion type: {fusion_type}")
        
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1) if spatial_dims == 2 else nn.AdaptiveAvgPool3d(1),
            nn.Flatten(),
            nn.Linear(fusion_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes),
        )
    
    def _build_encoder(self, in_channels, out_dim, spatial_dims):
        if spatial_dims == 2:
            return nn.Sequential(
                nn.Conv2d(in_channels, 64, kernel_size=3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(),
                nn.Conv2d(64, 128, kernel_size=3, padding=1, stride=2),
                nn.BatchNorm2d(128),
                nn.ReLU(),
                nn.Conv2d(128, 256, kernel_size=3, padding=1, stride=2),
                nn.BatchNorm2d(256),
                nn.ReLU(),
                nn.Conv2d(256, out_dim, kernel_size=3, padding=1, stride=2),
                nn.BatchNorm2d(out_dim),
                nn.ReLU(),
            )
        else:
            return nn.Sequential(
                nn.Conv3d(in_channels, 64, kernel_size=3, padding=1),
                nn.BatchNorm3d(64),
                nn.ReLU(),
                nn.Conv3d(64, 128, kernel_size=3, padding=1, stride=2),
                nn.BatchNorm3d(128),
                nn.ReLU(),
                nn.Conv3d(128, 256, kernel_size=3, padding=1, stride=2),
                nn.BatchNorm3d(256),
                nn.ReLU(),
                nn.Conv3d(256, out_dim, kernel_size=3, padding=1, stride=2),
                nn.BatchNorm3d(out_dim),
                nn.ReLU(),
            )
    
    def forward(self, hsi, lidar):
        hsi_features = self.hsi_encoder(hsi)
        lidar_features = self.lidar_encoder(lidar)
        
        if self.fusion_type == 'concatenate':
            fused = torch.cat([hsi_features, lidar_features], dim=1)
        elif self.fusion_type == 'attention':
            fused = self.attention_fusion(hsi_features, lidar_features)
        elif self.fusion_type == 'bilinear':
            fused = self._bilinear_pooling(hsi_features, lidar_features)
        elif self.fusion_type == 'gated':
            fused = self.gated_fusion(hsi_features, lidar_features)
        
        logits = self.classifier(fused)
        return logits
    
    def _bilinear_pooling(self, x, y):
        batch_size = x.size(0)
        h, w = x.size(2), x.size(3)
        
        x_flat = x.view(batch_size, -1, h * w)
        y_flat = y.view(batch_size, -1, h * w)
        
        outer = torch.bmm(x_flat.transpose(1, 2), y_flat)
        outer = outer.view(batch_size, h * w, -1)
        
        outer = torch.mean(outer, dim=1)
        outer = torch.sign(outer) * torch.sqrt(torch.abs(outer) + 1e-10)
        outer = F.normalize(outer, p=2, dim=1)
        
        return outer.unsqueeze(-1).unsqueeze(-1)


class CrossAttentionFusion(nn.Module):
    def __init__(self, dim, num_heads=8, spatial_dims=2):
        super().__init__()
        self.dim = dim
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5
        self.spatial_dims = spatial_dims
        
        self.to_q = nn.Conv2d(dim, dim, 1) if spatial_dims == 2 else nn.Conv3d(dim, dim, 1)
        self.to_k = nn.Conv2d(dim, dim, 1) if spatial_dims == 2 else nn.Conv3d(dim, dim, 1)
        self.to_v = nn.Conv2d(dim, dim, 1) if spatial_dims == 2 else nn.Conv3d(dim, dim, 1)
        
        self.to_out = nn.Conv2d(dim, dim, 1) if spatial_dims == 2 else nn.Conv3d(dim, dim, 1)
        
        self.norm1 = nn.BatchNorm2d(dim) if spatial_dims == 2 else nn.BatchNorm3d(dim)
        self.norm2 = nn.BatchNorm2d(dim) if spatial_dims == 2 else nn.BatchNorm3d(dim)
        
    def forward(self, x, y):
        batch_size = x.size(0)
        spatial_size = x.size()[2:]
        
        q = self.to_q(x).view(batch_size, self.num_heads, self.head_dim, -1)
        k = self.to_k(y).view(batch_size, self.num_heads, self.head_dim, -1)
        v = self.to_v(y).view(batch_size, self.num_heads, self.head_dim, -1)
        
        q = q.transpose(-1, -2)
        attn = torch.matmul(q, k) * self.scale
        attn = F.softmax(attn, dim=-1)
        
        out = torch.matmul(attn, v.transpose(-1, -2))
        out = out.transpose(-1, -2).contiguous().view(batch_size, self.dim, *spatial_size)
        
        out = self.to_out(out)
        out = self.norm1(out + x)
        
        return out


class GatedFusion(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.gate_hsi = nn.Sequential(
            nn.Conv2d(dim, dim, 1),
            nn.Sigmoid(),
        )
        self.gate_lidar = nn.Sequential(
            nn.Conv2d(dim, dim, 1),
            nn.Sigmoid(),
        )
        
    def forward(self, hsi, lidar):
        gate_hsi = self.gate_hsi(hsi)
        gate_lidar = self.gate_lidar(lidar)
        
        fused = hsi * gate_hsi + lidar * gate_lidar
        return fused


class MultiModalDataset(Dataset):
    def __init__(self, hsi_data, lidar_data, labels=None, transforms=None):
        self.hsi_data = hsi_data
        self.lidar_data = lidar_data
        self.labels = labels
        self.transforms = transforms
        
        assert len(hsi_data) == len(lidar_data), "HSI and LiDAR data must have same length"
        
    def __len__(self):
        return len(self.hsi_data)
    
    def __getitem__(self, idx):
        hsi = self.hsi_data[idx].astype(np.float32)
        lidar = self.lidar_data[idx].astype(np.float32)
        
        data_dict = {
            'hsi': hsi,
            'lidar': lidar,
        }
        
        if self.labels is not None:
            data_dict['label'] = self.labels[idx]
        
        if self.transforms is not None:
            data_dict = self.transforms(data_dict)
        
        return data_dict


class MultiModalClassifier:
    def __init__(
        self,
        num_classes,
        hsi_channels=200,
        lidar_channels=4,
        fusion_type='concatenate',
        spatial_dims=2,
        device=None,
        seed=42,
        use_amp=True,
    ):
        from monai.utils import set_determinism
        set_determinism(seed=seed)
        
        self.num_classes = num_classes
        self.hsi_channels = hsi_channels
        self.lidar_channels = lidar_channels
        self.fusion_type = fusion_type
        self.spatial_dims = spatial_dims
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_amp = use_amp
        self.scaler = torch.cuda.amp.GradScaler(enabled=use_amp)
        
        self.model = MultiModalFusionNet(
            hsi_channels=hsi_channels,
            lidar_channels=lidar_channels,
            num_classes=num_classes,
            spatial_dims=spatial_dims,
            fusion_type=fusion_type,
        )
        self.model = self.model.to(self.device)
        
        self.best_metric = 0.0
        self.train_losses = []
        self.val_metrics = []
        
    def get_default_transforms(self, mode='train'):
        keys = ['hsi', 'lidar']
        
        if mode == 'train':
            transforms = Compose([
                EnsureChannelFirstd(keys=keys, channel_dim=None),
                ScaleIntensityd(keys=keys),
                NormalizeIntensityd(keys=keys),
                RandFlipd(keys=keys, prob=0.5, spatial_axis=0),
                RandFlipd(keys=keys, prob=0.5, spatial_axis=1),
                RandRotated(keys=keys, range_x=np.pi/12, prob=0.5, keep_size=True),
                RandGaussianNoised(keys=['hsi'], prob=0.15, std=0.01),
                ToTensord(keys=keys + (['label'] if mode == 'train' else [])),
            ])
        else:
            transforms = Compose([
                EnsureChannelFirstd(keys=keys, channel_dim=None),
                ScaleIntensityd(keys=keys),
                NormalizeIntensityd(keys=keys),
                ToTensord(keys=keys + (['label'] if mode == 'train' else [])),
            ])
        
        return transforms
    
    def prepare_data(self, hsi_data, lidar_data, labels=None, transforms=None, cache_rate=0.0):
        if transforms is None:
            transforms = self.get_default_transforms(mode='train' if labels is not None else 'val')
        
        dataset = MultiModalDataset(hsi_data, lidar_data, labels, transforms=transforms)
        
        if cache_rate > 0:
            from monai.data import CacheDataset
            dataset = CacheDataset(data=dataset, cache_rate=cache_rate, num_workers=4)
        
        return dataset
    
    def create_dataloader(self, dataset, batch_size=16, shuffle=True, num_workers=4, pin_memory=True, distributed=False):
        from torch.utils.data.distributed import DistributedSampler
        
        sampler = None
        if distributed:
            sampler = DistributedSampler(dataset, shuffle=shuffle)
            shuffle = False
        
        from torch.utils.data import DataLoader
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=pin_memory,
            sampler=sampler,
        )
        return dataloader
    
    def configure_optimizer(self, lr=1e-4, weight_decay=1e-5, optimizer_type='adamw'):
        if optimizer_type == 'adam':
            optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        elif optimizer_type == 'adamw':
            optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)
        elif optimizer_type == 'sgd':
            optimizer = torch.optim.SGD(self.model.parameters(), lr=lr, momentum=0.9, weight_decay=weight_decay)
        else:
            raise ValueError(f"Unsupported optimizer: {optimizer_type}")
        
        self.optimizer = optimizer
        return optimizer
    
    def configure_scheduler(self, scheduler_type='cosine', T_max=100, patience=10):
        if not hasattr(self, 'optimizer'):
            raise ValueError("Call configure_optimizer first!")
        
        if scheduler_type == 'cosine':
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=T_max)
        elif scheduler_type == 'plateau':
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, mode='max', patience=patience, factor=0.5)
        elif scheduler_type == 'step':
            scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=30, gamma=0.1)
        else:
            raise ValueError(f"Unsupported scheduler: {scheduler_type}")
        
        self.scheduler = scheduler
        return scheduler
    
    def configure_loss(self, loss_type='cross_entropy'):
        if loss_type == 'cross_entropy':
            loss_fn = nn.CrossEntropyLoss()
        elif loss_type == 'focal':
            from monai.losses import FocalLoss
            loss_fn = FocalLoss(to_onehot_y=True, use_softmax=True)
        else:
            raise ValueError(f"Unsupported loss: {loss_type}")
        
        self.loss_fn = loss_fn
        return loss_fn
    
    def train_epoch(self, train_loader, epoch, verbose=True):
        from tqdm import tqdm
        
        self.model.train()
        epoch_loss = 0
        step = 0
        
        pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}') if verbose else train_loader
        
        for batch_data in pbar:
            step += 1
            hsi = batch_data['hsi'].to(self.device)
            lidar = batch_data['lidar'].to(self.device)
            labels = batch_data['label'].to(self.device).long()
            
            if labels.ndim > 1:
                labels = labels.squeeze(1)
            
            self.optimizer.zero_grad()
            
            with torch.cuda.amp.autocast(enabled=self.use_amp):
                outputs = self.model(hsi, lidar)
                loss = self.loss_fn(outputs, labels)
            
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
            
            epoch_loss += loss.item()
            
            if verbose:
                pbar.set_postfix(loss=loss.item())
        
        epoch_loss /= step
        return epoch_loss
    
    def validate(self, val_loader):
        self.model.eval()
        num_correct = 0
        num_total = 0
        
        with torch.no_grad():
            for val_data in val_loader:
                hsi = val_data['hsi'].to(self.device)
                lidar = val_data['lidar'].to(self.device)
                labels = val_data['label'].to(self.device).long()
                
                if labels.ndim > 1:
                    labels = labels.squeeze(1)
                
                with torch.cuda.amp.autocast(enabled=self.use_amp):
                    outputs = self.model(hsi, lidar)
                
                preds = torch.argmax(outputs, dim=1)
                num_correct += (preds == labels).sum().item()
                num_total += labels.size(0)
        
        accuracy = num_correct / num_total if num_total > 0 else 0
        return accuracy
    
    def fit(self, train_loader, val_loader=None, epochs=100, save_dir='./models', save_name='multimodal_best.pth', verbose=True):
        import os
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, save_name)
        
        if not hasattr(self, 'optimizer'):
            self.configure_optimizer()
        if not hasattr(self, 'scheduler'):
            self.configure_scheduler(T_max=epochs)
        if not hasattr(self, 'loss_fn'):
            self.configure_loss()
        
        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader, epoch, verbose)
            self.train_losses.append(train_loss)
            
            if val_loader is not None:
                val_acc = self.validate(val_loader)
                self.val_metrics.append(val_acc)
                
                if val_acc > self.best_metric:
                    self.best_metric = val_acc
                    self.save_model(save_path)
                
                if verbose and (epoch + 1) % 5 == 0:
                    print(f"Epoch {epoch+1}/{epochs}, Train Loss: {train_loss:.4f}, "
                          f"Val Acc: {val_acc:.4f}, Best: {self.best_metric:.4f}")
            
            if hasattr(self, 'scheduler'):
                if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(val_acc if val_loader is not None else train_loss)
                else:
                    self.scheduler.step()
        
        return self.train_losses, self.val_metrics
    
    def predict(self, test_loader, return_probabilities=False):
        self.model.eval()
        predictions = []
        probabilities = []
        
        with torch.no_grad():
            for batch_data in test_loader:
                hsi = batch_data['hsi'].to(self.device)
                lidar = batch_data['lidar'].to(self.device)
                
                with torch.cuda.amp.autocast(enabled=self.use_amp):
                    outputs = self.model(hsi, lidar)
                
                preds = torch.argmax(outputs, dim=1)
                probs = torch.softmax(outputs, dim=1)
                
                predictions.extend(preds.cpu().numpy())
                probabilities.extend(probs.cpu().numpy())
        
        if return_probabilities:
            return np.array(predictions), np.array(probabilities)
        return np.array(predictions)
    
    def save_model(self, path):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict() if hasattr(self, 'optimizer') else None,
            'num_classes': self.num_classes,
            'hsi_channels': self.hsi_channels,
            'lidar_channels': self.lidar_channels,
            'fusion_type': self.fusion_type,
            'best_metric': self.best_metric,
        }, path)
        print(f"Multi-modal model saved to {path}")
    
    def load_model(self, path, map_location=None):
        checkpoint = torch.load(path, map_location=map_location or self.device)
        
        self.num_classes = checkpoint['num_classes']
        self.hsi_channels = checkpoint['hsi_channels']
        self.lidar_channels = checkpoint['lidar_channels']
        self.fusion_type = checkpoint['fusion_type']
        
        self.model = MultiModalFusionNet(
            hsi_channels=self.hsi_channels,
            lidar_channels=self.lidar_channels,
            num_classes=self.num_classes,
            spatial_dims=self.spatial_dims,
            fusion_type=self.fusion_type,
        )
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model = self.model.to(self.device)
        self.best_metric = checkpoint.get('best_metric', 0.0)
        
        print(f"Multi-modal model loaded from {path}, Best metric: {self.best_metric:.4f}")
        return self


class LiDARProcessor:
    @staticmethod
    def compute_features(point_cloud, grid_size=(64, 64)):
        """
        Compute LiDAR features from point cloud
        Args:
            point_cloud: (N, 3+) array with x, y, z, intensity, etc.
            grid_size: output grid size
        Returns:
            features: (grid_size[0], grid_size[1], n_features) array
        """
        h, w = grid_size
        features = np.zeros((h, w, 4), dtype=np.float32)
        
        coords = point_cloud[:, :2]
        coords = coords - coords.min(axis=0)
        coords = coords / coords.max(axis=0) * np.array([h - 1, w - 1])
        coords = coords.astype(int)
        
        height = point_cloud[:, 2]
        intensity = point_cloud[:, 3] if point_cloud.shape[1] > 3 else np.ones(len(point_cloud))
        
        for i in range(h):
            for j in range(w):
                mask = (coords[:, 0] == i) & (coords[:, 1] == j)
                if mask.sum() > 0:
                    features[i, j, 0] = height[mask].mean()
                    features[i, j, 1] = height[mask].max() - height[mask].min()
                    features[i, j, 2] = intensity[mask].mean()
                    features[i, j, 3] = mask.sum()
        
        return features
