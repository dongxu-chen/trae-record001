import torch
import torch.nn as nn
from config import Config


class DiscriminatorBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 2):
        super(DiscriminatorBlock, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=4, stride=stride, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.leaky_relu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv(x)
        out = self.bn(out)
        out = self.leaky_relu(out)
        return out


class PatchDiscriminator(nn.Module):
    def __init__(self, in_channels: int = 3, num_filters: int = 64, num_blocks: int = 3):
        super(PatchDiscriminator, self).__init__()
        
        self.input_conv = nn.Sequential(
            nn.Conv2d(in_channels, num_filters, kernel_size=4, stride=2, padding=1, bias=False),
            nn.LeakyReLU(0.2, inplace=True)
        )
        
        blocks = []
        current_filters = num_filters
        for _ in range(num_blocks):
            blocks.append(DiscriminatorBlock(current_filters, current_filters * 2))
            current_filters *= 2
        self.blocks = nn.Sequential(*blocks)
        
        self.output_conv = nn.Conv2d(current_filters, 1, kernel_size=4, stride=1, padding=1, bias=False)
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.input_conv(x)
        out = self.blocks(out)
        out = self.output_conv(out)
        out = torch.sigmoid(out)
        return out


class RainDiscriminator(nn.Module):
    def __init__(self, in_channels: int = 3, num_filters: int = 64):
        super(RainDiscriminator, self).__init__()
        
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, num_filters, kernel_size=3, padding=1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters, num_filters * 2, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_filters * 2),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters * 2, num_filters * 4, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_filters * 4),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters * 4, num_filters * 8, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_filters * 8),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(num_filters * 8, 1),
            nn.Sigmoid()
        )
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.features(x)


class DomainDiscriminator(nn.Module):
    def __init__(self, in_channels: int = 3, num_filters: int = 64):
        super(DomainDiscriminator, self).__init__()
        
        self.conv_layers = nn.Sequential(
            nn.Conv2d(in_channels, num_filters, kernel_size=4, stride=2, padding=1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters, num_filters * 2, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_filters * 2),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters * 2, num_filters * 4, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_filters * 4),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters * 4, num_filters * 8, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(num_filters * 8),
            nn.LeakyReLU(0.2, inplace=True),
            
            nn.Conv2d(num_filters * 8, 1, kernel_size=4, stride=1, padding=0, bias=False),
            nn.AdaptiveAvgPool2d(1),
            nn.Sigmoid()
        )
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv_layers(x)
        return out.view(out.size(0), -1)


def build_discriminator(disc_type: str = 'patch') -> nn.Module:
    if disc_type == 'patch':
        model = PatchDiscriminator()
    elif disc_type == 'rain':
        model = RainDiscriminator()
    elif disc_type == 'domain':
        model = DomainDiscriminator()
    else:
        raise ValueError(f"Unknown discriminator type: {disc_type}")
    
    return model.to(Config.DEVICE)


class AdversarialLoss(nn.Module):
    def __init__(self, loss_type: str = 'lsgan'):
        super(AdversarialLoss, self).__init__()
        self.loss_type = loss_type
        
        if loss_type == 'vanilla':
            self.criterion = nn.BCELoss()
        elif loss_type == 'lsgan':
            self.criterion = nn.MSELoss()
        elif loss_type == 'wgan-gp':
            self.criterion = None
        else:
            raise ValueError(f"Unknown loss type: {loss_type}")

    def forward(self, pred: torch.Tensor, target_is_real: bool) -> torch.Tensor:
        if self.loss_type == 'wgan-gp':
            if target_is_real:
                return -pred.mean()
            else:
                return pred.mean()
        
        target = torch.ones_like(pred) if target_is_real else torch.zeros_like(pred)
        return self.criterion(pred, target)
