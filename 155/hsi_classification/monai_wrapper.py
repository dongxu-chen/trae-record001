import os
import numpy as np
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.distributed import DistributedSampler
import monai
from monai.data import Dataset, DataLoader, CacheDataset
from monai.transforms import (
    Compose,
    EnsureChannelFirst,
    ScaleIntensity,
    RandFlip,
    RandRotate,
    RandZoom,
    ToTensor,
    Resize,
    NormalizeIntensity,
    RandGaussianNoise,
    RandBiasField,
    RandGibbsNoise,
    ConcatItemsd,
    EnsureTyped,
)
from monai.networks.nets import (
    UNet,
    ResNet,
    DenseNet121,
    EfficientNetBN,
    ViT,
    UNETR,
)
from monai.networks.layers import Norm
from monai.losses import DiceLoss, FocalLoss, DiceCELoss
from monai.metrics import DiceMetric, MeanIoU
from monai.inferers import sliding_window_inference
from monai.utils import set_determinism
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


class MonaiClassifier:
    def __init__(
        self,
        num_classes,
        input_channels=1,
        model_name='resnet50',
        spatial_dims=2,
        roi_size=(64, 64),
        device=None,
        seed=42,
        use_amp=True,
    ):
        set_determinism(seed=seed)
        
        self.num_classes = num_classes
        self.input_channels = input_channels
        self.model_name = model_name
        self.spatial_dims = spatial_dims
        self.roi_size = roi_size
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_amp = use_amp
        self.scaler = torch.cuda.amp.GradScaler(enabled=use_amp)
        
        self.model = self._build_model()
        self.model = self.model.to(self.device)
        
        self.best_metric = 0.0
        self.best_epoch = -1
        self.train_losses = []
        self.val_metrics = []
        
    def _build_model(self):
        if self.model_name == 'resnet18':
            model = ResNet(
                layers=[2, 2, 2, 2],
                block_type='basic',
                spatial_dims=self.spatial_dims,
                n_input_channels=self.input_channels,
                num_classes=self.num_classes,
                conv1_t_size=7,
                conv1_t_stride=1,
                feed_forward=False,
            )
        elif self.model_name == 'resnet50':
            model = ResNet(
                layers=[3, 4, 6, 3],
                block_type='bottleneck',
                spatial_dims=self.spatial_dims,
                n_input_channels=self.input_channels,
                num_classes=self.num_classes,
                conv1_t_size=7,
                conv1_t_stride=1,
                feed_forward=False,
            )
        elif self.model_name == 'densenet121':
            model = DenseNet121(
                spatial_dims=self.spatial_dims,
                in_channels=self.input_channels,
                out_channels=self.num_classes,
            )
        elif self.model_name == 'efficientnet-b0':
            model = EfficientNetBN(
                model_name='efficientnet-b0',
                spatial_dims=self.spatial_dims,
                in_channels=self.input_channels,
                num_classes=self.num_classes,
                pretrained=False,
            )
        elif self.model_name == 'vit':
            model = ViT(
                in_channels=self.input_channels,
                img_size=self.roi_size,
                patch_size=(16, 16) if self.spatial_dims == 2 else (8, 8, 8),
                hidden_size=768,
                mlp_dim=3072,
                num_heads=12,
                num_layers=12,
                num_classes=self.num_classes,
                classification=True,
            )
        else:
            raise ValueError(f"Unsupported model: {self.model_name}")
        
        return model
    
    def get_default_transforms(self, mode='train'):
        if mode == 'train':
            transforms = Compose([
                EnsureChannelFirst(channel_dim=None),
                ScaleIntensity(),
                NormalizeIntensity(),
                RandFlip(prob=0.5, spatial_axis=0),
                RandFlip(prob=0.5, spatial_axis=1),
                RandRotate(range_x=np.pi/12, prob=0.5, keep_size=True),
                RandZoom(min_zoom=0.9, max_zoom=1.1, prob=0.5),
                RandGaussianNoise(prob=0.15, std=0.01),
                ToTensor(),
            ])
        else:
            transforms = Compose([
                EnsureChannelFirst(channel_dim=None),
                ScaleIntensity(),
                NormalizeIntensity(),
                ToTensor(),
            ])
        return transforms
    
    def prepare_data(
        self,
        images,
        labels=None,
        transforms=None,
        cache_rate=0.0,
    ):
        if transforms is None:
            transforms = self.get_default_transforms(mode='train' if labels is not None else 'val')
        
        data_dicts = []
        for i, img in enumerate(images):
            if labels is not None:
                data_dicts.append({
                    'image': img.astype(np.float32),
                    'label': labels[i] if labels.ndim > 2 else labels
                })
            else:
                data_dicts.append({'image': img.astype(np.float32)})
        
        if cache_rate > 0:
            dataset = CacheDataset(
                data=data_dicts,
                transform=transforms,
                cache_rate=cache_rate,
                num_workers=4,
            )
        else:
            dataset = Dataset(data=data_dicts, transform=transforms)
        
        return dataset
    
    def create_dataloader(
        self,
        dataset,
        batch_size=16,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        distributed=False,
    ):
        sampler = None
        if distributed:
            sampler = DistributedSampler(dataset, shuffle=shuffle)
            shuffle = False
        
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
            optimizer = torch.optim.Adam(
                self.model.parameters(),
                lr=lr,
                weight_decay=weight_decay,
            )
        elif optimizer_type == 'adamw':
            optimizer = torch.optim.AdamW(
                self.model.parameters(),
                lr=lr,
                weight_decay=weight_decay,
            )
        elif optimizer_type == 'sgd':
            optimizer = torch.optim.SGD(
                self.model.parameters(),
                lr=lr,
                momentum=0.9,
                weight_decay=weight_decay,
                nesterov=True,
            )
        else:
            raise ValueError(f"Unsupported optimizer: {optimizer_type}")
        
        self.optimizer = optimizer
        return optimizer
    
    def configure_scheduler(self, scheduler_type='cosine', T_max=100, patience=10):
        if not hasattr(self, 'optimizer'):
            raise ValueError("Call configure_optimizer first!")
        
        if scheduler_type == 'cosine':
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer, T_max=T_max
            )
        elif scheduler_type == 'plateau':
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer, mode='max', patience=patience, factor=0.5
            )
        elif scheduler_type == 'step':
            scheduler = torch.optim.lr_scheduler.StepLR(
                self.optimizer, step_size=30, gamma=0.1
            )
        else:
            raise ValueError(f"Unsupported scheduler: {scheduler_type}")
        
        self.scheduler = scheduler
        return scheduler
    
    def configure_loss(self, loss_type='cross_entropy'):
        if loss_type == 'cross_entropy':
            loss_fn = nn.CrossEntropyLoss()
        elif loss_type == 'focal':
            loss_fn = FocalLoss(to_onehot_y=True, use_softmax=True)
        elif loss_type == 'dice_ce':
            loss_fn = DiceCELoss(to_onehot_y=True, softmax=True, lambda_dice=0.5, lambda_ce=0.5)
        else:
            raise ValueError(f"Unsupported loss: {loss_type}")
        
        self.loss_fn = loss_fn
        return loss_fn
    
    def train_epoch(self, train_loader, epoch, verbose=True):
        self.model.train()
        epoch_loss = 0
        step = 0
        
        pbar = tqdm(train_loader, desc=f'Epoch {epoch+1}') if verbose else train_loader
        
        for batch_data in pbar:
            step += 1
            inputs = batch_data['image'].to(self.device)
            labels = batch_data['label'].to(self.device).long()
            
            if labels.ndim > 1:
                labels = labels.squeeze(1)
            
            self.optimizer.zero_grad()
            
            with torch.cuda.amp.autocast(enabled=self.use_amp):
                outputs = self.model(inputs)
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
                val_inputs = val_data['image'].to(self.device)
                val_labels = val_data['label'].to(self.device).long()
                
                if val_labels.ndim > 1:
                    val_labels = val_labels.squeeze(1)
                
                with torch.cuda.amp.autocast(enabled=self.use_amp):
                    val_outputs = self.model(val_inputs)
                
                val_preds = torch.argmax(val_outputs, dim=1)
                num_correct += (val_preds == val_labels).sum().item()
                num_total += val_labels.size(0)
        
        accuracy = num_correct / num_total if num_total > 0 else 0
        return accuracy
    
    def fit(
        self,
        train_loader,
        val_loader=None,
        epochs=100,
        save_dir='./models',
        save_name='best_model.pth',
        verbose=True,
    ):
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
                    self.best_epoch = epoch
                    self.save_model(save_path)
                
                if verbose and (epoch + 1) % 5 == 0:
                    print(f"Epoch {epoch+1}/{epochs}, Train Loss: {train_loss:.4f}, "
                          f"Val Acc: {val_acc:.4f}, Best: {self.best_metric:.4f} at epoch {self.best_epoch+1}")
            else:
                if (epoch + 1) % 5 == 0:
                    self.save_model(save_path)
            
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
            for test_data in test_loader:
                test_inputs = test_data['image'].to(self.device)
                
                with torch.cuda.amp.autocast(enabled=self.use_amp):
                    test_outputs = self.model(test_inputs)
                
                preds = torch.argmax(test_outputs, dim=1)
                probs = torch.softmax(test_outputs, dim=1)
                
                predictions.extend(preds.cpu().numpy())
                probabilities.extend(probs.cpu().numpy())
        
        if return_probabilities:
            return np.array(predictions), np.array(probabilities)
        return np.array(predictions)
    
    def predict_sliding_window(self, image, roi_size=(64, 64), sw_batch_size=4, overlap=0.25):
        self.model.eval()
        
        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled=self.use_amp):
                outputs = sliding_window_inference(
                    inputs=image.to(self.device),
                    roi_size=roi_size,
                    sw_batch_size=sw_batch_size,
                    predictor=self.model,
                    overlap=overlap,
                    mode='gaussian',
                )
        
        return outputs
    
    def save_model(self, path):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict() if hasattr(self, 'optimizer') else None,
            'num_classes': self.num_classes,
            'input_channels': self.input_channels,
            'model_name': self.model_name,
            'best_metric': self.best_metric,
            'best_epoch': self.best_epoch,
        }, path)
        print(f"Model saved to {path}")
    
    def load_model(self, path, map_location=None):
        checkpoint = torch.load(path, map_location=map_location or self.device)
        
        self.num_classes = checkpoint['num_classes']
        self.input_channels = checkpoint['input_channels']
        self.model_name = checkpoint['model_name']
        self.model = self._build_model()
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model = self.model.to(self.device)
        self.best_metric = checkpoint.get('best_metric', 0.0)
        self.best_epoch = checkpoint.get('best_epoch', -1)
        
        print(f"Model loaded from {path}, Best metric: {self.best_metric:.4f}")
        return self
    
    def plot_training_curves(self, save_path=None):
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        
        axes[0].plot(self.train_losses, label='Train Loss')
        axes[0].set_title('Training Loss')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        if self.val_metrics:
            axes[1].plot(self.val_metrics, label='Val Accuracy', color='orange')
            axes[1].set_title('Validation Accuracy')
            axes[1].set_xlabel('Epoch')
            axes[1].set_ylabel('Accuracy')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
