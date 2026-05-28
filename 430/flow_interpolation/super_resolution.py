import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple


class ResidualBlockSR(nn.Module):
    def __init__(self, channels: int = 64):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, 1, 1)
        self.conv2 = nn.Conv2d(channels, channels, 3, 1, 1)
        self.relu = nn.LeakyReLU(0.2, inplace=True)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.relu(self.conv1(x))
        out = self.conv2(out)
        return out + residual


class UpsampleBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, scale_factor: int = 2):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels * scale_factor ** 2, 3, 1, 1)
        self.pixel_shuffle = nn.PixelShuffle(scale_factor)
        self.relu = nn.LeakyReLU(0.2, inplace=True)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = self.pixel_shuffle(x)
        x = self.relu(x)
        return x


class SuperResolutionModel(nn.Module):
    def __init__(self, scale: int = 2, num_blocks: int = 16, channels: int = 64):
        super().__init__()
        self.scale = scale
        
        self.conv_input = nn.Sequential(
            nn.Conv2d(3, channels, 7, 1, 3),
            nn.LeakyReLU(0.2, inplace=True)
        )
        
        self.residual_blocks = nn.Sequential(*[
            ResidualBlockSR(channels) for _ in range(num_blocks)
        ])
        
        self.conv_mid = nn.Sequential(
            nn.Conv2d(channels, channels, 3, 1, 1),
            nn.BatchNorm2d(channels)
        )
        
        upsample_blocks = []
        current_scale = 1
        while current_scale < scale:
            factor = min(2, scale // current_scale)
            upsample_blocks.append(UpsampleBlock(channels, channels, factor))
            current_scale *= factor
        
        self.upsample = nn.Sequential(*upsample_blocks)
        
        self.conv_output = nn.Sequential(
            nn.Conv2d(channels, channels // 2, 3, 1, 1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(channels // 2, 3, 7, 1, 3)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x / 255.0
        
        x = self.conv_input(x)
        residual = x
        x = self.residual_blocks(x)
        x = self.conv_mid(x) + residual
        x = self.upsample(x)
        x = self.conv_output(x)
        
        x = torch.clamp(x, 0, 1) * 255.0
        return x


class BilinearUpsampler(nn.Module):
    def __init__(self, scale: int = 2):
        super().__init__()
        self.scale = scale
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, _, h, w = x.shape
        return F.interpolate(x, size=(h * self.scale, w * self.scale), 
                            mode='bilinear', align_corners=False)


class SuperResolutionProcessor:
    def __init__(self, scale: int = 2, device: str = 'cuda', 
                 model_path: Optional[str] = None, use_esrgan: bool = True):
        self.scale = scale
        self.device = device
        self.use_esrgan = use_esrgan
        
        if use_esrgan:
            self.model = SuperResolutionModel(scale=scale)
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
                    print(f'Loaded super-resolution model from {model_path}')
                except Exception as e:
                    print(f'Warning: Could not load SR model: {e}')
                    print('Using initialized SR model weights')
            self.model = self.model.to(device)
            self.model.eval()
        else:
            self.model = BilinearUpsampler(scale=scale).to(device)
    
    def upscale(self, image: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return self.model(image)
    
    def upscale_batch(self, images: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return self.model(images)
    
    def to(self, device: str):
        self.device = device
        self.model = self.model.to(device)
        return self
    
    def eval(self):
        if hasattr(self.model, 'eval'):
            self.model.eval()
        return self
    
    def train(self):
        if hasattr(self.model, 'train'):
            self.model.train()
        return self


def create_sr_processor(scale: int = 2, device: str = 'cuda', 
                        model_path: Optional[str] = None, 
                        use_esrgan: bool = True) -> SuperResolutionProcessor:
    return SuperResolutionProcessor(
        scale=scale, 
        device=device, 
        model_path=model_path, 
        use_esrgan=use_esrgan
    )
