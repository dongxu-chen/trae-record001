import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models


class ASPP(nn.Module):
    def __init__(self, in_channels, out_channels, atrous_rates):
        super().__init__()
        modules = []
        modules.append(nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        ))
        for rate in atrous_rates:
            modules.append(nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 3, padding=rate, dilation=rate, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            ))
        modules.append(nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        ))
        self.convs = nn.ModuleList(modules)
        self.project = nn.Sequential(
            nn.Conv2d(out_channels * len(modules), out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5)
        )

    def forward(self, x):
        res = []
        for conv in self.convs[:-1]:
            res.append(conv(x))
        img_size = x.shape[-2:]
        res.append(F.interpolate(self.convs[-1](x), size=img_size, mode='bilinear', align_corners=True))
        res = torch.cat(res, dim=1)
        return self.project(res)


class DeepLabV3Plus(nn.Module):
    def __init__(self, n_channels=6, n_classes=1, backbone='resnet50', pretrained_backbone=False):
        super().__init__()
        self.n_channels = n_channels
        self.n_classes = n_classes
        self.backbone_name = backbone
        
        if backbone == 'resnet50':
            self.backbone = models.resnet50(pretrained=pretrained_backbone)
            low_level_channels = 256
            high_level_channels = 2048
        elif backbone == 'resnet101':
            self.backbone = models.resnet101(pretrained=pretrained_backbone)
            low_level_channels = 256
            high_level_channels = 2048
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")
        
        if n_channels != 3:
            self.backbone.conv1 = nn.Conv2d(n_channels, 64, kernel_size=7, stride=2, padding=3, bias=False)
        
        self.aspp = ASPP(high_level_channels, 256, [6, 12, 18])
        self.low_level_project = nn.Sequential(
            nn.Conv2d(low_level_channels, 48, 1, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True)
        )
        self.decoder = nn.Sequential(
            nn.Conv2d(256 + 48, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5)
        )
        self.classifier = nn.Conv2d(256, n_classes, 1)

    def forward(self, x):
        input_size = x.shape[-2:]
        x = self.backbone.conv1(x)
        x = self.backbone.bn1(x)
        x = self.backbone.relu(x)
        x = self.backbone.maxpool(x)
        x = self.backbone.layer1(x)
        low_level_features = x
        x = self.backbone.layer2(x)
        x = self.backbone.layer3(x)
        x = self.backbone.layer4(x)
        high_level_features = x
        x = self.aspp(high_level_features)
        x = F.interpolate(x, size=low_level_features.shape[-2:], mode='bilinear', align_corners=True)
        low_level_features = self.low_level_project(low_level_features)
        x = torch.cat([x, low_level_features], dim=1)
        x = self.decoder(x)
        x = F.interpolate(x, size=input_size, mode='bilinear', align_corners=True)
        logits = self.classifier(x)
        return logits

    def predict(self, image1, image2, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.eval()
        with torch.no_grad():
            x = torch.cat([image1, image2], dim=1)
            x = x.to(device)
            logits = self.forward(x)
            if self.n_classes == 1:
                pred = torch.sigmoid(logits)
            else:
                pred = torch.softmax(logits, dim=1)
        return pred
