import torch
import torch.nn as nn
from monai.networks.nets import UNet
from monai.networks.layers import Norm, Act
from typing import Tuple, Optional
from config import Config


class ResidualBlock3D(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        dropout: float = 0.0,
        stride: int = 1,
    ):
        super().__init__()
        self.conv1 = nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1, stride=stride)
        self.bn1 = nn.BatchNorm3d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm3d(out_channels)

        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size=1, stride=stride),
                nn.BatchNorm3d(out_channels),
            )
        else:
            self.shortcut = nn.Identity()

        if dropout > 0:
            self.dropout = nn.Dropout3d(dropout)
        else:
            self.dropout = None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.shortcut(x)

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        out += residual
        out = self.relu(out)

        if self.dropout is not None:
            out = self.dropout(out)

        return out


class DoubleConv3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.0, use_residual: bool = False):
        super().__init__()
        self.use_residual = use_residual
        if use_residual:
            self.conv = ResidualBlock3D(in_channels, out_channels, dropout)
        else:
            self.conv = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1),
                nn.BatchNorm3d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1),
                nn.BatchNorm3d(out_channels),
                nn.ReLU(inplace=True),
            )
            if dropout > 0:
                self.dropout = nn.Dropout3d(dropout)
            else:
                self.dropout = None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_residual:
            return self.conv(x)
        else:
            x = self.conv(x)
            if self.dropout is not None:
                x = self.dropout(x)
            return x


class Down3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.0, use_residual: bool = False):
        super().__init__()
        self.maxpool = nn.MaxPool3d(2)
        self.double_conv = DoubleConv3D(in_channels, out_channels, dropout, use_residual)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.maxpool(x)
        return self.double_conv(x)


class Up3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.0, use_residual: bool = False):
        super().__init__()
        self.up = nn.ConvTranspose3d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.double_conv = DoubleConv3D(in_channels, out_channels, dropout, use_residual)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x1 = self.up(x1)

        diffZ = x2.size()[2] - x1.size()[2]
        diffY = x2.size()[3] - x1.size()[3]
        diffX = x2.size()[4] - x1.size()[4]

        x1 = nn.functional.pad(x1, [diffX // 2, diffX - diffX // 2,
                                    diffY // 2, diffY - diffY // 2,
                                    diffZ // 2, diffZ - diffZ // 2])

        x = torch.cat([x2, x1], dim=1)
        return self.double_conv(x)


class OutConv3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = nn.Conv3d(in_channels, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class UNet3D(nn.Module):
    def __init__(
        self,
        in_channels: int = 1,
        num_classes: int = 3,
        channels: Tuple[int, ...] = (16, 32, 64, 128, 256),
        strides: Tuple[int, ...] = (2, 2, 2, 2),
        dropout: float = 0.2,
        use_residual: bool = True,
        use_checkpoint: bool = False,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.use_checkpoint = use_checkpoint

        self.inc = DoubleConv3D(in_channels, channels[0], dropout, use_residual)

        self.downs = nn.ModuleList()
        for i in range(len(channels) - 1):
            self.downs.append(Down3D(channels[i], channels[i + 1], dropout, use_residual))

        self.ups = nn.ModuleList()
        for i in range(len(channels) - 1, 0, -1):
            self.ups.append(Up3D(channels[i], channels[i - 1], dropout, use_residual))

        self.outc = OutConv3D(channels[0], num_classes)

    def _forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.inc(x)

        skip_connections = [x]

        for down in self.downs:
            x = down(x)
            skip_connections.append(x)

        skip_connections = skip_connections[::-1]

        for i, up in enumerate(self.ups):
            x = up(x, skip_connections[i + 1])

        logits = self.outc(x)
        return logits

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_checkpoint and self.training:
            return torch.utils.checkpoint.checkpoint(self._forward, x, use_reentrant=False)
        else:
            return self._forward(x)


def create_model(config: Config, use_monai: bool = True) -> nn.Module:
    if use_monai:
        model = UNet(
            spatial_dims=3,
            in_channels=config.in_channels,
            out_channels=config.num_classes,
            channels=config.channels,
            strides=config.strides,
            norm=Norm.BATCH,
            act=Act.PRELU,
            dropout=config.dropout,
        )
    else:
        model = UNet3D(
            in_channels=config.in_channels,
            num_classes=config.num_classes,
            channels=config.channels,
            strides=config.strides,
            dropout=config.dropout,
            use_residual=config.use_residual,
            use_checkpoint=config.use_checkpoint,
        )

    if config.use_checkpoint and not use_monai:
        for param in model.parameters():
            param.requires_grad = True

    return model


def save_model(model: nn.Module, path: str, epoch: int = None, optimizer=None, scheduler=None):
    checkpoint = {
        "model_state_dict": model.state_dict(),
    }
    if epoch is not None:
        checkpoint["epoch"] = epoch
    if optimizer is not None:
        checkpoint["optimizer_state_dict"] = optimizer.state_dict()
    if scheduler is not None:
        checkpoint["scheduler_state_dict"] = scheduler.state_dict()

    torch.save(checkpoint, path)
    print(f"Model saved to {path}")


def load_model(model: nn.Module, path: str, device: str = "cuda", optimizer=None, scheduler=None):
    checkpoint = torch.load(path, map_location=device)

    model.load_state_dict(checkpoint["model_state_dict"])

    if optimizer is not None and "optimizer_state_dict" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    if scheduler is not None and "scheduler_state_dict" in checkpoint:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

    epoch = checkpoint.get("epoch", 0)
    print(f"Model loaded from {path}, epoch: {epoch}")

    return model, optimizer, scheduler, epoch
