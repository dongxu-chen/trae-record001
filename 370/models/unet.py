"""
U-Net 变化检测模型
基于U-Net架构的双时相图像变化检测网络
"""

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


class UNet(nn.Module):
    def __init__(self, in_channels, out_channels, bilinear=True):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.bilinear = bilinear

        factor = 2 if bilinear else 1

        self.inc = DoubleConv(in_channels, 64)
        self.down1 = Down(64, 128)
        self.down2 = Down(128, 256)
        self.down3 = Down(256, 512)
        self.down4 = Down(512, 1024 // factor)

        self.up1 = Up(1024, 512 // factor, bilinear)
        self.up2 = Up(512, 256 // factor, bilinear)
        self.up3 = Up(256, 128 // factor, bilinear)
        self.up4 = Up(128, 64, bilinear)

        self.outc = OutConv(64, out_channels)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x1, x2):
        x = torch.cat([x1, x2], dim=1)

        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)

        logits = self.outc(x)
        return logits


class WeightedCrossEntropyLoss(nn.Module):
    def __init__(self, class_weights=None, num_classes=5,
                 use_inverse_frequency=True, use_median_frequency=True,
                 max_weight_ratio=10.0):
        super().__init__()
        self.class_weights = class_weights
        self.num_classes = num_classes
        self.use_inverse_frequency = use_inverse_frequency
        self.use_median_frequency = use_median_frequency
        self.max_weight_ratio = max_weight_ratio
        self.register_buffer('class_counts', torch.zeros(num_classes))
        self.register_buffer('total_samples', torch.tensor(0.0))

    def compute_class_weights(self, target):
        if self.class_weights is not None:
            return self.class_weights.to(target.device)

        with torch.no_grad():
            for c in range(self.num_classes):
                self.class_counts[c] += (target == c).sum().float()
            self.total_samples += target.numel()

        if self.total_samples > 0 and self.use_inverse_frequency:
            if self.use_median_frequency:
                frequencies = self.class_counts / self.total_samples
                median_freq = torch.median(frequencies[frequencies > 0])
                weights = torch.ones(self.num_classes)
                for c in range(self.num_classes):
                    if frequencies[c] > 0:
                        weights[c] = median_freq / frequencies[c]
                    else:
                        weights[c] = self.max_weight_ratio
            else:
                counts = self.class_counts.clamp(min=1.0)
                weights = self.total_samples / (self.num_classes * counts)

            weights = torch.clamp(weights, max=self.max_weight_ratio)
            weights = weights / weights.sum() * self.num_classes
        else:
            weights = torch.ones(self.num_classes)

        return weights.to(target.device)

    def forward(self, pred, target):
        weights = self.compute_class_weights(target)
        ce_loss = F.cross_entropy(
            pred, target,
            weight=weights,
            reduction='mean',
            ignore_index=-1
        )
        return ce_loss


class WeightedFocalLoss(nn.Module):
    def __init__(self, class_weights=None, num_classes=5,
                 alpha=0.25, gamma=2.0):
        super().__init__()
        self.class_weights = class_weights
        self.num_classes = num_classes
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, pred, target):
        pred_soft = F.softmax(pred, dim=1)
        pred_log_soft = F.log_softmax(pred, dim=1)

        target_onehot = F.one_hot(
            target.clamp(0, self.num_classes - 1),
            num_classes=self.num_classes
        ).permute(0, 3, 1, 2).float()

        focal_weight = target_onehot * (1 - pred_soft) ** self.gamma
        focal_weight = self.alpha * focal_weight + (1 - self.alpha) * (1 - target_onehot) * pred_soft ** self.gamma

        if self.class_weights is not None:
            weight = self.class_weights.to(pred.device)
            focal_weight = focal_weight * weight.view(1, -1, 1, 1)

        focal_loss = -focal_weight * pred_log_soft * target_onehot
        return focal_loss.sum(dim=1).mean()


class DiceLoss(nn.Module):
    def __init__(self, smooth=1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, pred, target):
        pred_soft = F.softmax(pred, dim=1)
        num_classes = pred.shape[1]
        loss = 0.0
        for c in range(num_classes):
            pred_flat = pred_soft[:, c, :, :].contiguous().view(-1)
            target_flat = (target == c).float().contiguous().view(-1)
            intersection = (pred_flat * target_flat).sum()
            dice = (2.0 * intersection + self.smooth) / (pred_flat.sum() + target_flat.sum() + self.smooth)
            loss += (1.0 - dice)
        return loss / num_classes


class TverskyLoss(nn.Module):
    def __init__(self, alpha=0.3, beta=0.7, smooth=1.0):
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.smooth = smooth

    def forward(self, pred, target):
        pred_soft = F.softmax(pred, dim=1)
        num_classes = pred.shape[1]
        loss = 0.0

        for c in range(num_classes):
            pred_flat = pred_soft[:, c, :, :].contiguous().view(-1)
            target_flat = (target == c).float().contiguous().view(-1)

            tp = (pred_flat * target_flat).sum()
            fp = (pred_flat * (1 - target_flat)).sum()
            fn = ((1 - pred_flat) * target_flat).sum()

            tversky = (tp + self.smooth) / (tp + self.alpha * fp + self.beta * fn + self.smooth)
            loss += (1.0 - tversky)

        return loss / num_classes


class ChangeDetectionLoss(nn.Module):
    def __init__(self, num_classes=5, class_weights=None,
                 use_focal=False, use_tversky=False,
                 focal_alpha=0.25, focal_gamma=2.0,
                 tversky_alpha=0.3, tversky_beta=0.7,
                 wce_weight=1.0, dice_weight=0.5,
                 focal_weight=0.5, tversky_weight=0.3):
        super().__init__()
        self.num_classes = num_classes
        self.wce_weight = wce_weight
        self.dice_weight = dice_weight
        self.focal_weight = focal_weight
        self.tversky_weight = tversky_weight

        self.wce_loss = WeightedCrossEntropyLoss(
            class_weights=class_weights,
            num_classes=num_classes,
            use_inverse_frequency=True,
            use_median_frequency=True,
            max_weight_ratio=10.0
        )

        self.dice_loss = DiceLoss()

        self.use_focal = use_focal
        self.use_tversky = use_tversky

        if use_focal:
            self.focal_loss = WeightedFocalLoss(
                class_weights=class_weights,
                num_classes=num_classes,
                alpha=focal_alpha,
                gamma=focal_gamma
            )

        if use_tversky:
            self.tversky_loss = TverskyLoss(
                alpha=tversky_alpha,
                beta=tversky_beta
            )

    def forward(self, pred, target):
        total_loss = 0.0

        if self.wce_weight > 0:
            total_loss += self.wce_weight * self.wce_loss(pred, target)

        if self.dice_weight > 0:
            total_loss += self.dice_weight * self.dice_loss(pred, target)

        if self.use_focal and self.focal_weight > 0:
            total_loss += self.focal_weight * self.focal_loss(pred, target)

        if self.use_tversky and self.tversky_weight > 0:
            total_loss += self.tversky_weight * self.tversky_loss(pred, target)

        return total_loss

    def get_class_weights(self):
        if self.wce_loss.total_samples > 0:
            counts = self.wce_loss.class_counts
            total = self.wce_loss.total_samples
            weights = total / (self.num_classes * counts.clamp(min=1.0))
            weights = torch.clamp(weights, max=self.wce_loss.max_weight_ratio)
            return weights.detach().cpu().numpy()
        return None
