import torch
import torch.nn as nn
from torch.nn.utils.parametrizations import spectral_norm


class DCGANGenerator(nn.Module):
    def __init__(self, z_dim: int, img_channels: int, base_channels: int = 64, img_size: int = 32):
        super().__init__()
        self.z_dim = z_dim
        num_upsamples = max(1, int(torch.log2(torch.tensor(img_size)).item()) - 2)
        ch = base_channels * (2 ** num_upsamples)

        layers = []
        in_ch = z_dim
        for i in range(num_upsamples):
            out_ch = ch // 2
            layers.extend([
                nn.ConvTranspose2d(in_ch, out_ch, 4, 2, 1, bias=False),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(True),
            ])
            in_ch = out_ch
            ch = out_ch

        layers.extend([
            nn.ConvTranspose2d(in_ch, img_channels, 4, 2, 1, bias=False),
            nn.Tanh(),
        ])

        self.main = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.ConvTranspose2d, nn.Conv2d)):
                nn.init.normal_(m.weight, 0.0, 0.02)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.normal_(m.weight, 1.0, 0.02)
                nn.init.zeros_(m.bias)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        x = z.view(z.size(0), z.size(1), 1, 1)
        return self.main(x)


class DCGANDiscriminator(nn.Module):
    def __init__(self, img_channels: int, base_channels: int = 64, img_size: int = 32, use_spectral_norm: bool = False):
        super().__init__()
        num_downsamples = max(1, int(torch.log2(torch.tensor(img_size)).item()) - 2)
        ch = base_channels

        layers = []
        in_ch = img_channels
        for i in range(num_downsamples):
            out_ch = ch * 2
            conv = nn.Conv2d(in_ch, out_ch, 4, 2, 1, bias=False)
            if use_spectral_norm:
                conv = spectral_norm(conv)
            layers.extend([
                conv,
                nn.LeakyReLU(0.2, True),
            ])
            in_ch = out_ch
            ch = out_ch

        conv_final = nn.Conv2d(in_ch, 1, 4, 1, 0, bias=False)
        if use_spectral_norm:
            conv_final = spectral_norm(conv_final)
        layers.append(conv_final)

        self.main = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.normal_(m.weight, 0.0, 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.main(x).view(-1)
