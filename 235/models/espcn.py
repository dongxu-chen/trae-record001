import torch
import torch.nn as nn
import torch.nn.functional as F


def pixel_shuffle_custom(input, scale_factor):
    batch_size, channels, height, width = input.size()
    num_channels = channels // (scale_factor * scale_factor)
    
    x = input.view(batch_size, scale_factor, scale_factor, num_channels, height, width)
    x = x.permute(0, 3, 4, 1, 5, 2).contiguous()
    x = x.view(batch_size, num_channels, height * scale_factor, width * scale_factor)
    return x


class ESPCN(nn.Module):
    def __init__(self, scale_factor=4, num_channels=3, num_features=64):
        super(ESPCN, self).__init__()
        self.scale_factor = scale_factor
        self.num_channels = num_channels
        
        self.conv1 = nn.Conv2d(num_channels, num_features, kernel_size=5, padding=2)
        self.conv2 = nn.Conv2d(num_features, num_features, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(num_features, num_features, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(num_features, num_channels * (scale_factor ** 2), kernel_size=3, padding=1)
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.orthogonal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x):
        x = F.tanh(self.conv1(x))
        x = F.tanh(self.conv2(x))
        x = F.tanh(self.conv3(x))
        x = pixel_shuffle_custom(self.conv4(x), self.scale_factor)
        return torch.clamp(x, 0.0, 1.0)


def espcn_x2(**kwargs):
    return ESPCN(scale_factor=2, **kwargs)


def espcn_x4(**kwargs):
    return ESPCN(scale_factor=4, **kwargs)


if __name__ == '__main__':
    model = ESPCN(scale_factor=4)
    x = torch.randn(1, 3, 64, 64)
    out = model(x)
    print(f'Input shape: {x.shape}')
    print(f'Output shape: {out.shape}')
    print(f'Total parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad) / 1000:.2f}K')
