import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        vgg = models.vgg19(pretrained=True).features
        self.layers = nn.ModuleList([
            vgg[:2],
            vgg[2:7],
            vgg[7:12],
            vgg[12:21],
            vgg[21:30]
        ])
        
    def forward(self, x, return_all=False):
        features = []
        for layer in self.layers:
            x = layer(x)
            features.append(x)
        if return_all:
            return features
        return features[-1]


class Decoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.decoder = nn.Sequential(
            nn.Conv2d(512, 256, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(256, 128, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.Conv2d(128, 128, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 64, 3, padding=1),
            nn.ReLU(),
            nn.Upsample(scale_factor=2, mode='nearest'),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 3, 3, padding=1),
        )
        
    def forward(self, x):
        return self.decoder(x)


def calc_mean_std(feat, eps=1e-5):
    size = feat.size()
    assert len(size) == 4
    N, C = size[:2]
    feat_var = feat.view(N, C, -1).var(dim=2) + eps
    feat_std = feat_var.sqrt().view(N, C, 1, 1)
    feat_mean = feat.view(N, C, -1).mean(dim=2).view(N, C, 1, 1)
    return feat_mean, feat_std


def adaptive_instance_normalization(content_feat, style_feat):
    assert content_feat.size()[:2] == style_feat.size()[:2]
    size = content_feat.size()
    style_mean, style_std = calc_mean_std(style_feat)
    content_mean, content_std = calc_mean_std(content_feat)
    normalized_feat = (content_feat - content_mean.expand(size)) / content_std.expand(size)
    return normalized_feat * style_std.expand(size) + style_mean.expand(size)


class AdaINModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = Encoder()
        self.decoder = Decoder()
        
        for param in self.encoder.parameters():
            param.requires_grad = False
            
    def encode_content(self, x):
        return self.encoder(x, return_all=True)
    
    def encode_style(self, x):
        return self.encoder(x, return_all=True)
    
    def style_transfer(self, content_feat, style_feats, alpha=1.0):
        if isinstance(style_feats, list):
            style_feat = style_feats[-1]
        else:
            style_feat = style_feats
        t = adaptive_instance_normalization(content_feat, style_feat)
        t = alpha * t + (1 - alpha) * content_feat
        return t
    
    def decode(self, t):
        return self.decoder(t)
    
    def forward(self, content_img, style_img, alpha=1.0):
        content_feats = self.encode_content(content_img)
        style_feats = self.encode_style(style_img)
        t = self.style_transfer(content_feats[-1], style_feats, alpha)
        return self.decode(t), content_feats, style_feats


class AdaINLoss(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder
        self.mse = nn.MSELoss()
        
    def forward(self, stylized_img, content_feat, style_feats):
        stylized_feats = self.encoder(stylized_img, return_all=True)
        
        content_loss = self.mse(stylized_feats[-1], content_feat)
        
        style_loss = 0
        for stylized_feat, style_feat in zip(stylized_feats, style_feats):
            stylized_mean, stylized_std = calc_mean_std(stylized_feat)
            style_mean, style_std = calc_mean_std(style_feat)
            style_loss += self.mse(stylized_mean, style_mean) + self.mse(stylized_std, style_std)
            
        return content_loss, style_loss
