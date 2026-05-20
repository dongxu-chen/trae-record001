import torch
import torch.nn as nn
import torch.nn.functional as F
from .attention import CBAM, BoundaryAttention, AttentionGate, SCSEModule


class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels, use_attention: bool = False, attention_type: str = 'cbam'):
        super().__init__()
        layers = [
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        ]
        
        if use_attention:
            if attention_type == 'cbam':
                layers.append(CBAM(out_channels))
            elif attention_type == 'scse':
                layers.append(SCSEModule(out_channels))
        
        self.double_conv = nn.Sequential(*layers)

    def forward(self, x):
        return self.double_conv(x)


class Down(nn.Module):
    def __init__(self, in_channels, out_channels, use_attention: bool = False):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels, use_attention)
        )

    def forward(self, x):
        return self.maxpool_conv(x)


class Up(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=True, use_attention: bool = False, use_attention_gate: bool = False):
        super().__init__()
        self.use_attention_gate = use_attention_gate
        
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        else:
            self.up = nn.ConvTranspose2d(in_channels // 2, in_channels // 2, kernel_size=2, stride=2)
        
        self.conv = DoubleConv(in_channels, out_channels, use_attention)
        
        if use_attention_gate:
            self.attention_gate = AttentionGate(out_channels, in_channels // 2)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
        
        if self.use_attention_gate:
            x2 = self.attention_gate(x2, x1)
        
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        return self.conv(x)


class UNet(nn.Module):
    def __init__(self, 
                 n_channels: int = 6, 
                 n_classes: int = 1, 
                 bilinear: bool = True,
                 use_attention: bool = True,
                 use_attention_gate: bool = True,
                 use_boundary_attention: bool = True):
        super().__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.bilinear = bilinear
        self.use_boundary_attention = use_boundary_attention
        factor = 2 if bilinear else 1

        self.inc = DoubleConv(n_channels, 64, use_attention)
        self.down1 = Down(64, 128, use_attention)
        self.down2 = Down(128, 256, use_attention)
        self.down3 = Down(256, 512, use_attention)
        self.down4 = Down(512, 1024 // factor, use_attention)
        
        self.up1 = Up(1024, 512 // factor, bilinear, use_attention, use_attention_gate)
        self.up2 = Up(512, 256 // factor, bilinear, use_attention, use_attention_gate)
        self.up3 = Up(256, 128 // factor, bilinear, use_attention, use_attention_gate)
        self.up4 = Up(128, 64, bilinear, use_attention, use_attention_gate)
        
        if use_boundary_attention:
            self.boundary_attention = BoundaryAttention(64)
        
        self.outc = OutConv(64, n_classes)

    def forward(self, x, return_boundary: bool = False):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        
        boundary_map = None
        if self.use_boundary_attention:
            x, boundary_map = self.boundary_attention(x)
        
        logits = self.outc(x)
        
        if return_boundary and boundary_map is not None:
            return logits, boundary_map
        return logits

    def predict(self, image1, image2, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.eval()
        with torch.no_grad():
            x = torch.cat([image1, image2], dim=1)
            x = x.to(device)
            output = self.forward(x)
            
            if isinstance(output, tuple):
                logits = output[0]
            else:
                logits = output
            
            if self.n_classes == 1:
                pred = torch.sigmoid(logits)
            else:
                pred = torch.softmax(logits, dim=1)
        return pred

    def get_boundary_loss(self, pred_boundary, target, device=None):
        if device is None:
            device = target.device
        
        target = target.float()
        target_edge = F.max_pool2d(target, 3, stride=1, padding=1) - target
        target_edge = torch.clamp(target_edge, 0, 1)
        
        pred_boundary = torch.sigmoid(pred_boundary)
        bce_loss = F.binary_cross_entropy_with_logits(pred_boundary, target_edge)
        
        intersection = (pred_boundary * target_edge).sum()
        union = pred_boundary.sum() + target_edge.sum() - intersection + 1e-8
        dice_loss = 1 - (2 * intersection + 1e-8) / (union + 1e-8)
        
        return bce_loss + dice_loss
