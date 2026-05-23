import torch
import torch.nn as nn
import torch.nn.functional as F


class ChannelAttention(nn.Module):
    def __init__(self, channels, reduction=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        
        self.fc = nn.Sequential(
            nn.Conv2d(channels, channels // reduction, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels // reduction, channels, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        y = self.avg_pool(x)
        y = self.fc(y)
        y = self.sigmoid(y)
        return x * y.expand_as(x)


class ResidualChannelAttentionBlock(nn.Module):
    def __init__(self, channels, reduction=16):
        super(ResidualChannelAttentionBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.ca = ChannelAttention(channels, reduction)
    
    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.ca(out)
        out = out + residual
        return out


class ResidualGroup(nn.Module):
    def __init__(self, channels, num_blocks, reduction=16):
        super(ResidualGroup, self).__init__()
        self.blocks = nn.Sequential(*[
            ResidualChannelAttentionBlock(channels, reduction) 
            for _ in range(num_blocks)
        ])
        self.conv = nn.Conv2d(channels, channels, 3, padding=1)
    
    def forward(self, x):
        residual = x
        out = self.blocks(x)
        out = self.conv(out)
        out = out + residual
        return out


class UpsampleBlock(nn.Module):
    def __init__(self, channels, scale):
        super(UpsampleBlock, self).__init__()
        self.conv = nn.Conv2d(channels, channels * scale * scale, 3, padding=1)
        self.pixel_shuffle = nn.PixelShuffle(scale)
    
    def forward(self, x):
        x = self.conv(x)
        x = self.pixel_shuffle(x)
        return x


class RCAN(nn.Module):
    def __init__(self, scale=4, num_channels=1, num_features=64, 
                 num_groups=10, num_blocks=20, reduction=16):
        super(RCAN, self).__init__()
        self.scale = scale
        self.num_channels = num_channels
        self.num_features = num_features
        
        self.conv_in = nn.Conv2d(num_channels, num_features, 3, padding=1)
        
        self.residual_groups = nn.Sequential(*[
            ResidualGroup(num_features, num_blocks, reduction)
            for _ in range(num_groups)
        ])
        
        self.conv_mid = nn.Conv2d(num_features, num_features, 3, padding=1)
        
        if scale in [2, 3]:
            self.upsample = UpsampleBlock(num_features, scale)
        elif scale == 4:
            self.upsample = nn.Sequential(
                UpsampleBlock(num_features, 2),
                UpsampleBlock(num_features, 2)
            )
        else:
            raise ValueError(f"Unsupported scale factor: {scale}")
        
        self.conv_out = nn.Conv2d(num_features, num_channels, 3, padding=1)
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        residual = F.interpolate(x, scale_factor=self.scale, mode='bilinear', align_corners=False)
        
        x = self.conv_in(x)
        
        residual_groups_out = x
        x = self.residual_groups(x)
        x = self.conv_mid(x)
        x = x + residual_groups_out
        
        x = self.upsample(x)
        x = self.conv_out(x)
        
        x = x + residual
        
        return x


def create_model(config):
    model = RCAN(
        scale=config.get('scale', 4),
        num_channels=config.get('num_channels', 1),
        num_features=config.get('num_features', 64),
        num_groups=config.get('num_groups', 10),
        num_blocks=config.get('num_blocks', 20),
        reduction=config.get('reduction', 16)
    )
    return model


class CharbonnierLoss(nn.Module):
    def __init__(self, epsilon=1e-3):
        super(CharbonnierLoss, self).__init__()
        self.epsilon = epsilon
    
    def forward(self, x, y):
        diff = x - y
        loss = torch.mean(torch.sqrt(diff * diff + self.epsilon * self.epsilon))
        return loss


def get_loss_function(config):
    loss_type = config.get('loss_type', 'l1')
    if loss_type == 'l1':
        return nn.L1Loss()
    elif loss_type == 'l2':
        return nn.MSELoss()
    elif loss_type == 'charbonnier':
        return CharbonnierLoss()
    else:
        raise ValueError(f"Unsupported loss type: {loss_type}")


def get_optimizer(model, config):
    optimizer_type = config.get('optimizer', 'adam')
    lr = config.get('learning_rate', 1e-4)
    
    if optimizer_type == 'adam':
        return torch.optim.Adam(model.parameters(), lr=lr, 
                               betas=config.get('betas', (0.9, 0.999)))
    elif optimizer_type == 'sgd':
        return torch.optim.SGD(model.parameters(), lr=lr, 
                              momentum=config.get('momentum', 0.9))
    else:
        raise ValueError(f"Unsupported optimizer type: {optimizer_type}")


def get_scheduler(optimizer, config):
    scheduler_type = config.get('scheduler', 'step')
    
    if scheduler_type == 'step':
        return torch.optim.lr_scheduler.StepLR(
            optimizer, 
            step_size=config.get('step_size', 200),
            gamma=config.get('gamma', 0.5)
        )
    elif scheduler_type == 'cosine':
        return torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=config.get('T_max', 500)
        )
    else:
        return None
