import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from config import MODEL_CONFIG


def default_conv(in_channels, out_channels, kernel_size, bias=True):
    return nn.Conv2d(
        in_channels, out_channels, kernel_size,
        padding=(kernel_size // 2), bias=bias)


class MeanShift(nn.Conv2d):
    def __init__(self, rgb_range, rgb_mean=(0.4488, 0.4371, 0.4040), rgb_std=(1.0, 1.0, 1.0), sign=-1):
        super(MeanShift, self).__init__(3, 3, kernel_size=1)
        std = torch.Tensor(rgb_std)
        self.weight.data = torch.eye(3).view(3, 3, 1, 1) / std.view(3, 1, 1, 1)
        self.bias.data = sign * rgb_range * torch.Tensor(rgb_mean) / std
        for p in self.parameters():
            p.requires_grad = False


class ResBlock(nn.Module):
    def __init__(self, conv, n_feats, kernel_size, bias=True, bn=False, act=nn.ReLU(True), res_scale=1):
        super(ResBlock, self).__init__()
        m = []
        for i in range(2):
            m.append(conv(n_feats, n_feats, kernel_size, bias=bias))
            if bn:
                m.append(nn.BatchNorm2d(n_feats))
            if i == 0:
                m.append(act)
        self.body = nn.Sequential(*m)
        self.res_scale = res_scale

    def forward(self, x):
        res = self.body(x).mul(self.res_scale)
        res += x
        return res


class Upsampler(nn.Sequential):
    def __init__(self, conv, scale, n_feats, bn=False, act=False, bias=True):
        m = []
        if (scale & (scale - 1)) == 0:
            for _ in range(int(math.log(scale, 2))):
                m.append(conv(n_feats, 4 * n_feats, 3, bias))
                m.append(nn.PixelShuffle(2))
                if bn:
                    m.append(nn.BatchNorm2d(n_feats))
                if act == 'relu':
                    m.append(nn.ReLU(True))
        elif scale == 3:
            m.append(conv(n_feats, 9 * n_feats, 3, bias))
            m.append(nn.PixelShuffle(3))
            if bn:
                m.append(nn.BatchNorm2d(n_feats))
            if act == 'relu':
                m.append(nn.ReLU(True))
        else:
            raise NotImplementedError
        super(Upsampler, self).__init__(*m)


class EDSR(nn.Module):
    def __init__(self, scale=4, num_features=64, num_res_blocks=16, res_scale=1.0, rgb_range=255, n_colors=3, conv=default_conv):
        super(EDSR, self).__init__()
        n_resblocks = num_res_blocks
        n_feats = num_features
        kernel_size = 3
        act = nn.ReLU(True)
        self.scale = scale

        self.sub_mean = MeanShift(rgb_range)
        self.add_mean = MeanShift(rgb_range, sign=1)

        self.head = nn.ModuleList([
            conv(n_colors, n_feats, kernel_size)
        ])

        self.body = nn.ModuleList([
            ResBlock(conv, n_feats, kernel_size, act=act, res_scale=res_scale) for _ in range(n_resblocks)
        ])
        self.body.append(conv(n_feats, n_feats, kernel_size))

        self.tail = nn.ModuleList([
            Upsampler(conv, scale, n_feats, act=False),
            conv(n_feats, n_colors, kernel_size)
        ])

    def forward(self, x):
        x = self.sub_mean(x)
        x = self.head[0](x)
        res = x
        for i, layer in enumerate(self.body[:-1]):
            x = layer(x)
        x = self.body[-1](x)
        x += res
        x = self.tail[0](x)
        x = self.tail[1](x)
        x = self.add_mean(x)
        return x


def create_edsr(scale=4, pretrained=False, **kwargs):
    cfg = MODEL_CONFIG['edsr'].copy()
    cfg.update(kwargs)
    cfg['scale'] = scale
    model = EDSR(**cfg)
    if pretrained:
        print("Note: Pretrained weights not bundled. Using random init.")
    return model
