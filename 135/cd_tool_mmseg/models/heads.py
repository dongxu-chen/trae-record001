# Copyright (c) Remote Sensing Change Detection Team. All rights reserved.

import torch
import torch.nn as nn
import torch.nn.functional as F
from .builder import HEADS


@HEADS.register_module()
class FCNHead(nn.Module):
    def __init__(self, in_channels, channels, num_classes=1, dropout_ratio=0.1, in_index=-1):
        super().__init__()
        self.in_channels = in_channels
        self.channels = channels
        self.num_classes = num_classes
        self.in_index = in_index

        self.convs = nn.Sequential(
            nn.Conv2d(in_channels, channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(dropout_ratio) if dropout_ratio > 0 else nn.Identity(),
            nn.Conv2d(channels, num_classes, kernel_size=1)
        )

    def forward(self, inputs):
        x = inputs[self.in_index] if isinstance(inputs, (list, tuple)) else inputs
        x = self.convs(x)
        return x

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)


@HEADS.register_module()
class ASPPHead(nn.Module):
    def __init__(self, in_channels, channels, num_classes=1, dilations=(1, 6, 12, 18), dropout_ratio=0.1):
        super().__init__()
        self.in_channels = in_channels
        self.channels = channels
        self.num_classes = num_classes

        self.aspp_modules = nn.ModuleList()
        
        for dilation in dilations:
            if dilation == 1:
                self.aspp_modules.append(nn.Sequential(
                    nn.Conv2d(in_channels, channels, kernel_size=1, bias=False),
                    nn.BatchNorm2d(channels),
                    nn.ReLU(inplace=True)
                ))
            else:
                self.aspp_modules.append(nn.Sequential(
                    nn.Conv2d(in_channels, channels, kernel_size=3, padding=dilation, dilation=dilation, bias=False),
                    nn.BatchNorm2d(channels),
                    nn.ReLU(inplace=True)
                ))

        self.image_pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True)
        )

        self.bottleneck = nn.Sequential(
            nn.Conv2d(channels * (len(dilations) + 1), channels, kernel_size=1, bias=False),
            nn.BatchNorm2d(channels),
            nn.ReLU(inplace=True),
            nn.Dropout2d(dropout_ratio) if dropout_ratio > 0 else nn.Identity()
        )

        self.cls_seg = nn.Conv2d(channels, num_classes, kernel_size=1)

    def forward(self, inputs):
        x = inputs[-1] if isinstance(inputs, (list, tuple)) else inputs
        batch_size, _, h, w = x.shape

        aspp_outs = []
        for module in self.aspp_modules:
            aspp_outs.append(module(x))

        image_feature = self.image_pool(x)
        image_feature = F.interpolate(image_feature, size=(h, w), mode='bilinear', align_corners=True)
        aspp_outs.append(image_feature)

        x = torch.cat(aspp_outs, dim=1)
        x = self.bottleneck(x)
        x = self.cls_seg(x)
        return x

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)


@HEADS.register_module()
class UNetHead(nn.Module):
    def __init__(self, in_channels, num_classes=1, in_index=-1):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.in_index = in_index

        self.conv = nn.Conv2d(in_channels, num_classes, kernel_size=1)

    def forward(self, inputs):
        x = inputs[self.in_index] if isinstance(inputs, (list, tuple)) else inputs
        x = self.conv(x)
        return x

    def init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
