import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, List


class StyleEncoder(nn.Module):
    def __init__(self, in_channels: int = 3, base_channels: int = 32):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, base_channels, 7, 1, 3),
            nn.InstanceNorm2d(base_channels),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(base_channels, base_channels * 2, 3, 2, 1),
            nn.InstanceNorm2d(base_channels * 2),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(base_channels * 2, base_channels * 4, 3, 2, 1),
            nn.InstanceNorm2d(base_channels * 4),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(base_channels * 4, base_channels * 4, 3, 1, 1),
            nn.InstanceNorm2d(base_channels * 4),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


class StyleDecoder(nn.Module):
    def __init__(self, out_channels: int = 3, base_channels: int = 128):
        super().__init__()
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(base_channels, base_channels // 2, 3, 2, 1, 1),
            nn.InstanceNorm2d(base_channels // 2),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose2d(base_channels // 2, base_channels // 4, 3, 2, 1, 1),
            nn.InstanceNorm2d(base_channels // 4),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(base_channels // 4, out_channels, 7, 1, 3),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(x)


class AdaIN(nn.Module):
    def __init__(self):
        super().__init__()
    
    def forward(self, content: torch.Tensor, style_mean: torch.Tensor, 
                style_std: torch.Tensor) -> torch.Tensor:
        content_mean = content.mean(dim=[2, 3], keepdim=True)
        content_std = content.std(dim=[2, 3], keepdim=True) + 1e-6
        
        normalized = (content - content_mean) / content_std
        return style_std * normalized + style_mean


class StyleTransferModel(nn.Module):
    def __init__(self, base_channels: int = 32, style_dim: int = 128):
        super().__init__()
        self.content_encoder = StyleEncoder(3, base_channels)
        self.style_encoder = StyleEncoder(3, base_channels)
        
        self.decoder = StyleDecoder(3, base_channels * 4)
        
        self.adain = AdaIN()
        
        self.style_projection = nn.Sequential(
            nn.Linear(base_channels * 4, style_dim),
            nn.ReLU(inplace=True),
            nn.Linear(style_dim, style_dim)
        )
        
        self.style_modulation = nn.Sequential(
            nn.Linear(style_dim, base_channels * 4 * 2),
            nn.ReLU(inplace=True)
        )
    
    def extract_style_features(self, style_image: torch.Tensor) -> dict:
        style_features = self.style_encoder(style_image)
        style_mean = style_features.mean(dim=[2, 3])
        style_std = style_features.std(dim=[2, 3]) + 1e-6
        
        style_embedding = self.style_projection(style_mean)
        style_params = self.style_modulation(style_embedding)
        style_gamma, style_beta = style_params.chunk(2, dim=1)
        
        return {
            'embedding': style_embedding,
            'gamma': style_gamma.unsqueeze(-1).unsqueeze(-1),
            'beta': style_beta.unsqueeze(-1).unsqueeze(-1),
            'mean': style_mean.unsqueeze(-1).unsqueeze(-1),
            'std': style_std.unsqueeze(-1).unsqueeze(-1)
        }
    
    def forward(self, content: torch.Tensor, style_features: dict, 
                alpha: float = 1.0) -> torch.Tensor:
        content_features = self.content_encoder(content)
        
        modulated = self.adain(
            content_features, 
            style_features['mean'], 
            style_features['std']
        )
        
        modulated = (1 - alpha) * content_features + alpha * modulated
        
        modulated = modulated * (1 + style_features['gamma']) + style_features['beta']
        
        output = self.decoder(modulated)
        return output * 255.0


class FastStyleTransfer(nn.Module):
    def __init__(self, num_styles: int = 1):
        super().__init__()
        self.num_styles = num_styles
        
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 32, 9, 1, 4),
            nn.InstanceNorm2d(32),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(32, 64, 3, 2, 1),
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(64, 128, 3, 2, 1),
            nn.InstanceNorm2d(128),
            nn.ReLU(inplace=True),
        )
        
        self.residual = nn.Sequential(*[
            nn.Sequential(
                nn.Conv2d(128, 128, 3, 1, 1),
                nn.InstanceNorm2d(128),
                nn.ReLU(inplace=True),
                nn.Conv2d(128, 128, 3, 1, 1),
                nn.InstanceNorm2d(128)
            ) for _ in range(5)
        ])
        
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 3, 2, 1, 1),
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
            
            nn.ConvTranspose2d(64, 32, 3, 2, 1, 1),
            nn.InstanceNorm2d(32),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(32, 3, 9, 1, 4),
            nn.Sigmoid()
        )
        
        self.style_embedding = nn.Embedding(num_styles, 128)
    
    def forward(self, x: torch.Tensor, style_idx: int = 0, 
                alpha: float = 1.0) -> torch.Tensor:
        x = x / 255.0
        
        style_feat = self.style_embedding(torch.tensor(style_idx, device=x.device))
        style_feat = style_feat.unsqueeze(-1).unsqueeze(-1)
        
        features = self.encoder(x)
        features = features + style_feat * 0.1
        
        for i, block in enumerate(self.residual):
            residual = features
            features = block(features)
            features = features + residual
        
        output = self.decoder(features)
        output = x * (1 - alpha) + output * alpha
        
        return output * 255.0


class StyleTransferProcessor:
    def __init__(self, device: str = 'cuda', model_path: Optional[str] = None,
                 style_name: str = 'custom'):
        self.device = device
        self.style_name = style_name
        self.style_features = None
        self.style_image = None
        
        self.model = StyleTransferModel(base_channels=32)
        
        if model_path is not None:
            try:
                state_dict = torch.load(model_path, map_location=device)
                if 'model' in state_dict:
                    state_dict = state_dict['model']
                new_state_dict = {}
                for k, v in state_dict.items():
                    if k.startswith('module.'):
                        k = k[7:]
                    new_state_dict[k] = v
                self.model.load_state_dict(new_state_dict, strict=False)
                print(f'Loaded style transfer model from {model_path}')
            except Exception as e:
                print(f'Warning: Could not load style model: {e}')
        
        self.model = self.model.to(device)
        self.model.eval()
    
    def set_style_image(self, style_image: torch.Tensor):
        self.style_image = style_image.to(self.device)
        with torch.no_grad():
            self.style_features = self.model.extract_style_features(self.style_image)
    
    def set_style_from_path(self, style_path: str):
        import cv2
        import numpy as np
        
        style_img = cv2.imread(style_path)
        if style_img is None:
            raise ValueError(f'Cannot load style image: {style_path}')
        
        style_img = cv2.cvtColor(style_img, cv2.COLOR_BGR2RGB)
        style_tensor = torch.from_numpy(style_img).permute(2, 0, 1).float()
        style_tensor = style_tensor.unsqueeze(0).to(self.device)
        self.set_style_image(style_tensor)
    
    def transfer(self, content: torch.Tensor, alpha: float = 1.0) -> torch.Tensor:
        if self.style_features is None:
            return content
        
        with torch.no_grad():
            output = self.model(content, self.style_features, alpha)
        return output
    
    def transfer_sequence(self, frames: List[torch.Tensor], 
                          alpha: float = 1.0) -> List[torch.Tensor]:
        results = []
        for frame in frames:
            results.append(self.transfer(frame, alpha))
        return results
    
    def to(self, device: str):
        self.device = device
        self.model = self.model.to(device)
        if self.style_image is not None:
            self.style_image = self.style_image.to(device)
        if self.style_features is not None:
            for k, v in self.style_features.items():
                self.style_features[k] = v.to(device)
        return self
    
    def eval(self):
        self.model.eval()
        return self
    
    def train(self):
        self.model.train()
        return self


def create_style_processor(device: str = 'cuda', 
                           model_path: Optional[str] = None,
                           style_name: str = 'custom') -> StyleTransferProcessor:
    return StyleTransferProcessor(
        device=device, 
        model_path=model_path,
        style_name=style_name
    )
