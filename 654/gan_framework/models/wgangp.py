import torch
import torch.nn as nn
from torch.nn.utils.parametrizations import spectral_norm


class ResBlockG(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, 1, 1, bias=False)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, 1, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.skip = nn.Conv2d(in_ch, out_ch, 1, 1, 0, bias=False) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = torch.relu(self.bn1(self.conv1(x)))
        h = self.bn2(self.conv2(h))
        return torch.relu(h + self.skip(x))


class ResBlockD(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, use_sn: bool = False):
        super().__init__()
        conv1 = nn.Conv2d(in_ch, out_ch, 3, 1, 1, bias=False)
        conv2 = nn.Conv2d(out_ch, out_ch, 3, 1, 1, bias=False)
        if use_sn:
            conv1 = spectral_norm(conv1)
            conv2 = spectral_norm(conv2)
        self.conv1 = conv1
        self.conv2 = conv2
        self.skip_conv = nn.Conv2d(in_ch, out_ch, 1, 1, 0, bias=False)
        if use_sn:
            self.skip_conv = spectral_norm(self.skip_conv)
        self.avgpool = nn.AvgPool2d(2, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = torch.relu(self.conv1(x))
        h = self.conv2(h)
        h += self.skip_conv(x)
        h = torch.relu(h)
        return self.avgpool(h)


class WGGANGenerator(nn.Module):
    def __init__(self, z_dim: int, img_channels: int, base_channels: int = 64, img_size: int = 32):
        super().__init__()
        self.z_dim = z_dim
        self.init_size = img_size // 4
        ch = base_channels * 4

        self.fc = nn.Linear(z_dim, ch * self.init_size * self.init_size)
        self.bn0 = nn.BatchNorm2d(ch)

        self.res1 = ResBlockG(ch, ch)
        self.upsample1 = nn.Upsample(scale_factor=2, mode="nearest")
        self.res2 = ResBlockG(ch, ch // 2)
        self.bn2 = nn.BatchNorm2d(ch // 2)
        self.upsample2 = nn.Upsample(scale_factor=2, mode="nearest")

        self.conv_out = nn.Conv2d(ch // 2, img_channels, 3, 1, 1, bias=False)
        self.tanh = nn.Tanh()
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Conv2d)):
                nn.init.normal_(m.weight, 0.0, 0.02)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.normal_(m.weight, 1.0, 0.02)
                nn.init.zeros_(m.bias)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        h = self.fc(z)
        h = h.view(h.size(0), -1, self.init_size, self.init_size)
        h = torch.relu(self.bn0(h))

        h = self.res1(h)
        h = self.upsample1(h)
        h = self.res2(h)
        h = self.bn2(h)
        h = self.upsample2(h)

        return self.tanh(self.conv_out(h))


class WGGANCritic(nn.Module):
    def __init__(self, img_channels: int, base_channels: int = 64, img_size: int = 32, use_spectral_norm: bool = True):
        super().__init__()
        ch = base_channels

        self.res1 = ResBlockD(img_channels, ch, use_sn=use_spectral_norm)
        self.res2 = ResBlockD(ch, ch * 2, use_sn=use_spectral_norm)
        self.res3 = ResBlockD(ch * 2, ch * 4, use_sn=use_spectral_norm)

        final_size = img_size // 8
        if final_size < 1:
            final_size = 1
        self.fc = nn.Linear(ch * 4 * final_size * final_size, 1)
        if use_spectral_norm:
            self.fc = spectral_norm(self.fc)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Conv2d)) and not hasattr(m, "parametrizations"):
                nn.init.normal_(m.weight, 0.0, 0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.res1(x)
        h = self.res2(h)
        h = self.res3(h)
        h = h.view(h.size(0), -1)
        return self.fc(h).view(-1)


def compute_gradient_penalty(
    critic: nn.Module,
    real_samples: torch.Tensor,
    fake_samples: torch.Tensor,
    device: torch.device,
    edge_ratio: float = 0.3,
    edge_threshold: float = 0.15,
    edge_weight: float = 2.0,
) -> torch.Tensor:
    batch_size = real_samples.size(0)
    n_edge = int(batch_size * edge_ratio)
    n_uniform = batch_size - n_edge

    alpha_uniform = torch.rand(n_uniform, 1, 1, 1, device=device)

    side = torch.randint(0, 2, (n_edge, 1, 1, 1), device=device).float()
    edge_offset = torch.rand(n_edge, 1, 1, 1, device=device) * edge_threshold
    alpha_edge = side * (1.0 - edge_offset) + (1.0 - side) * edge_offset

    alpha = torch.cat([alpha_uniform, alpha_edge], dim=0)

    perm = torch.randperm(batch_size, device=device)
    alpha = alpha[perm]

    interpolates = (alpha * real_samples + (1 - alpha) * fake_samples).requires_grad_(True)
    d_interpolates = critic(interpolates)

    gradients = torch.autograd.grad(
        outputs=d_interpolates,
        inputs=interpolates,
        grad_outputs=torch.ones_like(d_interpolates),
        create_graph=True,
        retain_graph=True,
    )[0]

    gradients = gradients.view(gradients.size(0), -1)
    grad_norm = gradients.norm(2, dim=1)

    uniform_penalty = ((grad_norm[:n_uniform] - 1) ** 2).mean()

    edge_mask = (alpha.view(batch_size) < edge_threshold) | (alpha.view(batch_size) > (1 - edge_threshold))
    edge_penalty = ((grad_norm - 1) ** 2)
    edge_penalty = edge_penalty * torch.where(
        edge_mask,
        torch.tensor(edge_weight, device=device),
        torch.tensor(1.0, device=device),
    )
    edge_penalty = edge_penalty.mean()

    gradient_penalty = 0.5 * uniform_penalty + 0.5 * edge_penalty
    return gradient_penalty
