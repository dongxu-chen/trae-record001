import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.parametrizations import spectral_norm
import math


class PixelNorm(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(dim=1, keepdim=True) + 1e-8)


class AdaIN(nn.Module):
    def __init__(self, channels: int, style_dim: int):
        super().__init__()
        self.norm = nn.InstanceNorm2d(channels)
        self.style_fc = nn.Linear(style_dim, channels * 2)
        self.channels = channels

    def forward(self, x: torch.Tensor, style: torch.Tensor) -> torch.Tensor:
        style_params = self.style_fc(style)
        ys, yb = style_params.chunk(2, dim=1)
        ys = ys.unsqueeze(2).unsqueeze(3)
        yb = yb.unsqueeze(2).unsqueeze(3)
        return self.norm(x) * (1 + ys) + yb


class NoiseInjection(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.weight = nn.Parameter(torch.zeros(1, channels, 1, 1))

    def forward(self, x: torch.Tensor, noise: torch.Tensor = None) -> torch.Tensor:
        if noise is None:
            noise = torch.randn(x.size(0), 1, x.size(2), x.size(3), device=x.device)
        return x + self.weight * noise


class StyledConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, kernel_size: int, style_dim: int, use_sn: bool = False):
        super().__init__()
        conv = nn.Conv2d(in_ch, out_ch, kernel_size, 1, kernel_size // 2, bias=False)
        if use_sn:
            conv = spectral_norm(conv)
        self.conv = conv
        self.adain = AdaIN(out_ch, style_dim)
        self.noise = NoiseInjection(out_ch)
        self.activate = nn.LeakyReLU(0.2, True)

    def forward(self, x: torch.Tensor, style: torch.Tensor, noise: torch.Tensor = None) -> torch.Tensor:
        x = self.conv(x)
        x = self.noise(x, noise)
        x = self.adain(x, style)
        return self.activate(x)


class StyleGANDiscriminatorBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, use_sn: bool = True):
        super().__init__()
        conv1 = nn.Conv2d(in_ch, out_ch, 3, 1, 1, bias=False)
        conv2 = nn.Conv2d(out_ch, out_ch, 3, 1, 1, bias=False)
        if use_sn:
            conv1 = spectral_norm(conv1)
            conv2 = spectral_norm(conv2)
        self.conv1 = conv1
        self.conv2 = conv2
        self.activate = nn.LeakyReLU(0.2, True)
        self.downsample = nn.AvgPool2d(2, 2)
        skip = nn.Conv2d(in_ch, out_ch, 1, 1, 0, bias=False)
        if use_sn:
            skip = spectral_norm(skip)
        self.skip = skip

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.activate(self.conv1(x))
        h = self.activate(self.conv2(h))
        h = self.downsample(h)
        s = self.downsample(self.skip(x))
        return h + s


class SplitGroupBranch(nn.Module):
    def __init__(self, dim: int, dropout: float = 0.2):
        super().__init__()
        half = dim // 2
        self.branch_a = nn.Sequential(
            nn.Linear(half, half),
            nn.LeakyReLU(0.2, True),
            nn.Dropout(dropout),
        )
        self.branch_b = nn.Sequential(
            nn.Linear(half, half),
            nn.LeakyReLU(0.2, True),
            nn.Dropout(dropout),
        )
        self.gate = nn.Parameter(torch.tensor(0.5))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        xa, xb = x.chunk(2, dim=1)
        ha = self.branch_a(xa)
        hb = self.branch_b(xb)
        g = torch.sigmoid(self.gate)
        ha_out = g * ha + (1 - g) * hb
        hb_out = (1 - g) * ha + g * hb
        return torch.cat([ha_out, hb_out], dim=1)


class MappingNetwork(nn.Module):
    def __init__(self, z_dim: int, style_dim: int, n_layers: int = 8, dropout: float = 0.2):
        super().__init__()
        half = style_dim // 2
        self.pixel_norm = PixelNorm()
        self.input_fc = nn.Sequential(
            nn.Linear(z_dim, style_dim),
            nn.LeakyReLU(0.2, True),
            nn.Dropout(dropout),
        )

        self.split_groups = nn.ModuleList()
        self.projections = nn.ModuleList()
        for i in range(n_layers // 2):
            self.split_groups.append(SplitGroupBranch(style_dim, dropout))
            self.projections.append(nn.Sequential(
                nn.Linear(style_dim, style_dim),
                nn.LeakyReLU(0.2, True),
                nn.Dropout(dropout),
            ))

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        x = self.pixel_norm(z)
        x = self.input_fc(x)
        for sg, proj in zip(self.split_groups, self.projections):
            x = sg(x)
            x = proj(x)
        return x


class StyleGAN2Generator(nn.Module):
    def __init__(self, z_dim: int, img_channels: int, style_dim: int = 512,
                 base_channels: int = 64, img_size: int = 32, n_layers_style: int = 8,
                 use_sn: bool = False, mapping_dropout: float = 0.2):
        super().__init__()
        self.z_dim = z_dim
        self.style_dim = style_dim
        self.img_size = img_size
        self.base_channels = base_channels

        self.mapping = MappingNetwork(z_dim, style_dim, n_layers_style, dropout=mapping_dropout)

        log_size = int(math.log2(img_size))
        self.num_layers = (log_size - 2) * 2

        self.const_input = nn.Parameter(
            torch.randn(1, base_channels * 4, 4, 4)
        )

        self.style_conv1 = StyledConv(base_channels * 4, base_channels * 4, 3, style_dim, use_sn)
        self.to_rgb1 = nn.Conv2d(base_channels * 4, img_channels, 1, bias=False)

        self.convs = nn.ModuleList()
        self.to_rgbs = nn.ModuleList()
        self.noises = nn.ModuleList()

        in_ch = base_channels * 4
        for i in range(log_size - 3):
            out_ch = max(base_channels, in_ch // 2)
            self.convs.append(StyledConv(in_ch, out_ch, 3, style_dim, use_sn))
            self.convs.append(StyledConv(out_ch, out_ch, 3, style_dim, use_sn))
            self.to_rgbs.append(nn.Conv2d(out_ch, img_channels, 1, bias=False))
            in_ch = out_ch

        self.upsample = nn.Upsample(scale_factor=2, mode="nearest")
        self.tanh = nn.Tanh()

    def forward(self, z: torch.Tensor, return_styles: bool = False) -> torch.Tensor:
        styles = self.mapping(z)
        batch_size = z.size(0)

        x = self.const_input.expand(batch_size, -1, -1, -1)
        noise = None
        x = self.style_conv1(x, styles, noise)

        if self.num_layers == 0:
            return self.tanh(self.to_rgb1(x))

        out = self.to_rgb1(x)

        style_idx = 0
        for i in range(len(self.to_rgbs)):
            x = self.upsample(x)
            s1 = styles if self.num_layers <= 2 else styles
            s2 = styles if self.num_layers <= 2 else styles
            x = self.convs[style_idx](x, s1)
            x = self.convs[style_idx + 1](x, s2)
            style_idx += 2

            out = self.upsample(out)
            out = out + self.to_rgbs[i](x)

        if return_styles:
            return self.tanh(out), styles
        return self.tanh(out)


class StyleGAN2Discriminator(nn.Module):
    def __init__(self, img_channels: int, style_dim: int = 512, base_channels: int = 64,
                 img_size: int = 32, use_sn: bool = True):
        super().__init__()
        log_size = int(math.log2(img_size))

        self.from_rgb = nn.Conv2d(img_channels, base_channels * 4, 1, bias=False)
        if use_sn:
            self.from_rgb = spectral_norm(self.from_rgb)

        self.blocks = nn.ModuleList()
        in_ch = base_channels * 4
        for _ in range(log_size - 2):
            out_ch = max(base_channels, in_ch // 2)
            self.blocks.append(StyleGANDiscriminatorBlock(in_ch, out_ch, use_sn))
            in_ch = out_ch

        final_size = max(1, 4)
        fc_in = in_ch * final_size * final_size
        fc = nn.Linear(fc_in, 1)
        if use_sn:
            fc = spectral_norm(fc)
        self.fc = fc
        self.activate = nn.LeakyReLU(0.2, True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.activate(self.from_rgb(x))
        for block in self.blocks:
            h = block(h)
        h = h.view(h.size(0), -1)
        return self.fc(h).view(-1)
