import torch
import torch.nn as nn
import torch.nn.functional as F
from config import Config


class ResidualBlock(nn.Module):
    def __init__(self, num_channels: int):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(num_channels, num_channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(num_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(num_channels, num_channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(num_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += residual
        return out


class RainResidualNetwork(nn.Module):
    def __init__(self, num_res_blocks: int = Config.NUM_RES_BLOCKS, num_channels: int = Config.NUM_CHANNELS):
        super(RainResidualNetwork, self).__init__()
        
        self.conv_input = nn.Conv2d(3, num_channels, kernel_size=3, padding=1, bias=False)
        self.relu_input = nn.ReLU(inplace=True)
        
        res_blocks = []
        for _ in range(num_res_blocks):
            res_blocks.append(ResidualBlock(num_channels))
        self.res_blocks = nn.Sequential(*res_blocks)
        
        self.conv_mid = nn.Conv2d(num_channels, num_channels, kernel_size=3, padding=1, bias=False)
        self.bn_mid = nn.BatchNorm2d(num_channels)
        
        self.conv_output = nn.Conv2d(num_channels, 3, kernel_size=3, padding=1, bias=False)
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv_input(x)
        out = self.relu_input(out)
        
        residual = out
        out = self.res_blocks(out)
        out = self.conv_mid(out)
        out = self.bn_mid(out)
        out += residual
        
        out = self.conv_output(out)
        
        out = torch.clamp(out, 0, 1)
        return out


class RainStemResidualNetwork(nn.Module):
    def __init__(self, num_res_blocks: int = Config.NUM_RES_BLOCKS, num_channels: int = Config.NUM_CHANNELS):
        super(RainStemResidualNetwork, self).__init__()
        
        self.stem = nn.Sequential(
            nn.Conv2d(3, num_channels // 2, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(num_channels // 2),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_channels // 2, num_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(num_channels),
            nn.ReLU(inplace=True)
        )
        
        res_blocks = []
        for _ in range(num_res_blocks):
            res_blocks.append(ResidualBlock(num_channels))
        self.res_blocks = nn.Sequential(*res_blocks)
        
        self.head = nn.Sequential(
            nn.Conv2d(num_channels, num_channels // 2, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(num_channels // 2),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_channels // 2, 3, kernel_size=3, padding=1, bias=False)
        )
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.stem(x)
        out = self.res_blocks(out)
        out = self.head(out)
        out = torch.clamp(out, 0, 1)
        return out


def build_model(model_type: str = 'resnet') -> nn.Module:
    if model_type == 'resnet':
        model = RainResidualNetwork()
    elif model_type == 'stem_resnet':
        model = RainStemResidualNetwork()
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    return model.to(Config.DEVICE)
