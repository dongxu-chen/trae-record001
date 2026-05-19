# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import torch
import torch.nn as nn
import torch.nn.functional as F
from .builder import NECKS


class UpConv(nn.Module):
    def __init__(self, in_channels, out_channels, scale_factor=2):
        super().__init__()
        self.up = nn.Upsample(scale_factor=scale_factor, mode='bilinear', align_corners=True)
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x1, x2=None):
        x1 = self.up(x1)
        if x2 is not None:
            x1 = torch.cat([x2, x1], dim=1)
        x1 = self.conv(x1)
        return x1


@NECKS.register_module()
class FPNNeck(nn.Module):
    def __init__(self, in_channels, out_channels, num_outs, conv_cfg=None, norm_cfg=None, activation=None):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.num_outs = num_outs

        self.lateral_convs = nn.ModuleList()
        for in_ch in in_channels:
            self.lateral_convs.append(nn.Sequential(
                nn.Conv2d(in_ch, out_channels, kernel_size=1),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            ))

        self.fpn_convs = nn.ModuleList()
        for _ in range(num_outs):
            self.fpn_convs.append(nn.Sequential(
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            ))

    def forward(self, inputs):
        assert len(inputs) == len(self.in_channels)

        laterals = []
        for i, lateral_conv in enumerate(self.lateral_convs):
            laterals.append(lateral_conv(inputs[i]))

        for i in range(len(laterals) - 1, 0, -1):
            prev_shape = laterals[i - 1].shape[2:]
            laterals[i - 1] = laterals[i - 1] + F.interpolate(laterals[i], size=prev_shape, mode='bilinear', align_corners=True)

        outs = []
        for i, fpn_conv in enumerate(self.fpn_convs):
            outs.append(fpn_conv(laterals[i]))

        return tuple(outs)

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)


@NECKS.register_module()
class UNetNeck(nn.Module):
    def __init__(self, in_channels, out_channels=None):
        super().__init__()
        self.in_channels = in_channels
        
        if out_channels is None:
            out_channels = in_channels[:-1]
        
        self.out_channels = out_channels
        self.up_convs = nn.ModuleList()
        
        for i in range(len(in_channels) - 1, 0, -1):
            in_ch = in_channels[i] + in_channels[i-1]
            out_ch = out_channels[i-1]
            self.up_convs.append(nn.Sequential(
                nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
                nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(inplace=True)
            ))

    def forward(self, inputs):
        assert len(inputs) == len(self.in_channels)
        
        x = inputs[-1]
        outs = []
        
        for i, up_conv in enumerate(self.up_convs):
            idx = len(inputs) - 2 - i
            x = up_conv(torch.cat([F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=True), inputs[idx]], dim=1))
            outs.append(x)
        
        return tuple(outs)

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
