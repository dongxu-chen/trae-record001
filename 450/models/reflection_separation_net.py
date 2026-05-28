import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels, mid_channels=None):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)


class Down(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        return self.maxpool_conv(x)


class Up(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=True):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels, in_channels // 2)
        else:
            self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class OutConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=1)

    def forward(self, x):
        return self.conv(x)


class ReflectionSeparationNet(nn.Module):
    def __init__(self, n_channels=3, bilinear=False, use_polarization=False):
        super().__init__()
        self.n_channels = n_channels
        self.bilinear = bilinear
        self.use_polarization = use_polarization
        
        factor = 2 if bilinear else 1
        
        input_channels = n_channels * 2 if use_polarization else n_channels
        
        self.inc = DoubleConv(input_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        self.down4 = Down(512, 1024 // factor)
        
        self.up1 = Up(1024, 512 // factor, bilinear)
        self.up2 = Up(512, 256 // factor, bilinear)
        self.up3 = Up(256, 128 // factor, bilinear)
        self.up4 = Up(128, 64, bilinear)
        
        self.out_transmission = OutConv(64, n_channels)
        self.out_reflection = OutConv(64, n_channels)
        self.out_alpha = OutConv(64, 1)

    def forward(self, x, polarization_img=None):
        if self.use_polarization and polarization_img is not None:
            x = torch.cat([x, polarization_img], dim=1)
        
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        
        transmission = torch.sigmoid(self.out_transmission(x))
        reflection = torch.sigmoid(self.out_reflection(x))
        alpha = torch.sigmoid(self.out_alpha(x))
        
        return transmission, reflection, alpha


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out


class PerceptualLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.l1_loss = nn.L1Loss()
        self.mse_loss = nn.MSELoss()

    def forward(self, pred_t, pred_r, pred_alpha, target_t, target_r, input_img):
        alpha = pred_alpha.clamp(0, 1)
        reconstructed = alpha * pred_t + (1 - alpha) * pred_r
        recon_loss = self.l1_loss(reconstructed, input_img)
        
        t_loss = self.l1_loss(pred_t, target_t)
        r_loss = self.l1_loss(pred_r, target_r)
        alpha_loss = self.mse_loss(pred_alpha, torch.abs(target_r).mean(dim=1, keepdim=True))
        
        grad_t_x, grad_t_y = self._gradient(pred_t)
        grad_target_t_x, grad_target_t_y = self._gradient(target_t)
        grad_loss_x = self.l1_loss(grad_t_x, grad_target_t_x)
        grad_loss_y = self.l1_loss(grad_t_y, grad_target_t_y)
        grad_loss = grad_loss_x + grad_loss_y
        
        total_loss = recon_loss + 0.5 * t_loss + 0.3 * r_loss + 0.1 * alpha_loss + 0.2 * grad_loss
        
        return {
            'total': total_loss,
            'recon': recon_loss,
            'transmission': t_loss,
            'reflection': r_loss,
            'alpha': alpha_loss,
            'gradient': grad_loss
        }

    def _gradient(self, x):
        grad_x = x[:, :, 1:, :] - x[:, :, :-1, :]
        grad_y = x[:, :, :, 1:] - x[:, :, :, :-1]
        return grad_x, grad_y
