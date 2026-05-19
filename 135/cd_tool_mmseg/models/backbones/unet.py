# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import torch
import torch.nn as nn
import torch.nn.functional as F
from ..builder import BACKBONES


class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels, mid_channels=None, use_batch_norm=True):
        super().__init__()
        if not mid_channels:
            mid_channels = out_channels
        layers = [
            nn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1),
        ]
        if use_batch_norm:
            layers.append(nn.BatchNorm2d(mid_channels))
        layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1))
        if use_batch_norm:
            layers.append(nn.BatchNorm2d(out_channels))
        layers.append(nn.ReLU(inplace=True))
        self.double_conv = nn.Sequential(*layers)

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


@BACKBONES.register_module()
class UNetBackbone(nn.Module):
    def __init__(self, in_channels=6, base_channels=64, num_stages=4, out_indices=(0, 1, 2, 3)):
        super().__init__()
        self.in_channels = in_channels
        self.base_channels = base_channels
        self.num_stages = num_stages
        self.out_indices = out_indices

        self.inc = DoubleConv(in_channels, base_channels)
        
        self.down_layers = nn.ModuleList()
        in_ch = base_channels
        for i in range(num_stages):
            out_ch = base_channels * (2 ** (i + 1))
            self.down_layers.append(Down(in_ch, out_ch))
            in_ch = out_ch

        self.num_channels = [base_channels * (2 ** i) for i in range(num_stages + 1)]

    def forward(self, x):
        x = self.inc(x)
        outs = [x]

        for down_layer in self.down_layers:
            x = down_layer(x)
            outs.append(x)

        return tuple([outs[i] for i in self.out_indices])

    def init_weights(self, pretrained=None):
        if pretrained is None:
            for m in self.modules():
                if isinstance(m, nn.Conv2d):
                    nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                    if m.bias is not None:
                        nn.init.constant_(m.bias, 0)
                elif isinstance(m, nn.BatchNorm2d):
                    nn.init.constant_(m.weight, 1)
                    nn.init.constant_(m.bias, 0)
