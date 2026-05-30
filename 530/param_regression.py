import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models
import config


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super(ConvBlock, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.pool = nn.MaxPool2d(2, 2)
    
    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.relu(x)
        x = self.pool(x)
        return x


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, 1, 1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, 1, 1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out += residual
        out = self.relu(out)
        return out


class ParamRegressionNet(nn.Module):
    def __init__(self, backbone='resnet50', pretrained=True):
        super(ParamRegressionNet, self).__init__()
        
        self.backbone_name = backbone
        self.param_dims = {
            'shape': config.SHAPE_DIM,
            'exp': config.EXP_DIM,
            'tex': config.TEX_DIM,
            'pose': config.POSE_DIM,
            'light': config.LIGHT_DIM
        }
        
        self.total_params = sum(self.param_dims.values())
        
        if backbone == 'resnet18':
            self.backbone = models.resnet18(pretrained=pretrained)
            num_ftrs = 512
        elif backbone == 'resnet34':
            self.backbone = models.resnet34(pretrained=pretrained)
            num_ftrs = 512
        elif backbone == 'resnet50':
            self.backbone = models.resnet50(pretrained=pretrained)
            num_ftrs = 2048
        elif backbone == 'mobilenet_v2':
            self.backbone = models.mobilenet_v2(pretrained=pretrained)
            num_ftrs = 1280
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")
        
        if 'resnet' in backbone:
            self.backbone.fc = nn.Identity()
        elif backbone == 'mobilenet_v2':
            self.backbone.classifier = nn.Identity()
        
        self.fc_layers = nn.Sequential(
            nn.Linear(num_ftrs, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, self.total_params)
        )
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.fc_layers.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        features = self.backbone(x)
        params = self.fc_layers(features)
        
        param_dict = {}
        start = 0
        for name, dim in self.param_dims.items():
            param_dict[name] = params[:, start:start + dim]
            start += dim
        
        return param_dict


class MultiScaleParamRegressionNet(nn.Module):
    def __init__(self, pretrained=True):
        super(MultiScaleParamRegressionNet, self).__init__()
        
        self.param_dims = {
            'shape': config.SHAPE_DIM,
            'exp': config.EXP_DIM,
            'tex': config.TEX_DIM,
            'pose': config.POSE_DIM,
            'light': config.LIGHT_DIM
        }
        
        self.total_params = sum(self.param_dims.values())
        
        resnet = models.resnet50(pretrained=pretrained)
        
        self.conv1 = resnet.conv1
        self.bn1 = resnet.bn1
        self.relu = resnet.relu
        self.maxpool = resnet.maxpool
        
        self.layer1 = resnet.layer1
        self.layer2 = resnet.layer2
        self.layer3 = resnet.layer3
        self.layer4 = resnet.layer4
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        self.fusion = nn.Sequential(
            nn.Linear(2048 + 1024 + 512, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, self.total_params)
        )
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        feat1 = self.layer1(x)
        feat2 = self.layer2(feat1)
        feat3 = self.layer3(feat2)
        feat4 = self.layer4(feat3)
        
        feat2_pool = self.avgpool(feat2).view(x.size(0), -1)
        feat3_pool = self.avgpool(feat3).view(x.size(0), -1)
        feat4_pool = self.avgpool(feat4).view(x.size(0), -1)
        
        combined = torch.cat([feat2_pool, feat3_pool, feat4_pool], dim=1)
        params = self.fusion(combined)
        
        param_dict = {}
        start = 0
        for name, dim in self.param_dims.items():
            param_dict[name] = params[:, start:start + dim]
            start += dim
        
        return param_dict


class LandmarkLoss(nn.Module):
    def __init__(self):
        super(LandmarkLoss, self).__init__()
        self.l2_loss = nn.MSELoss()
    
    def forward(self, pred_landmarks, target_landmarks):
        return self.l2_loss(pred_landmarks, target_landmarks)


class PhotometricLoss(nn.Module):
    def __init__(self):
        super(PhotometricLoss, self).__init__()
        self.l1_loss = nn.L1Loss()
    
    def forward(self, rendered_image, target_image):
        return self.l1_loss(rendered_image, target_image)


class PerceptualLoss(nn.Module):
    def __init__(self, device='cpu'):
        super(PerceptualLoss, self).__init__()
        vgg = models.vgg19(pretrained=True).features
        self.vgg_layers = vgg[:26].to(device)
        self.l1_loss = nn.L1Loss()
        
        for param in self.vgg_layers.parameters():
            param.requires_grad = False
    
    def forward(self, rendered_image, target_image):
        feat_rendered = self.vgg_layers(rendered_image)
        feat_target = self.vgg_layers(target_image)
        return self.l1_loss(feat_rendered, feat_target)


class TotalLoss(nn.Module):
    def __init__(self, weights=None, device='cpu'):
        super(TotalLoss, self).__init__()
        
        if weights is None:
            self.weights = {
                'landmark': 1.0,
                'photometric': 0.5,
                'perceptual': 0.1,
                'regularization': 1e-4
            }
        else:
            self.weights = weights
        
        self.landmark_loss = LandmarkLoss()
        self.photometric_loss = PhotometricLoss()
        self.perceptual_loss = PerceptualLoss(device=device)
    
    def forward(self, pred_dict, target_dict, params=None):
        loss = 0
        
        if 'landmarks' in pred_dict and 'landmarks' in target_dict:
            loss += self.weights['landmark'] * self.landmark_loss(
                pred_dict['landmarks'], target_dict['landmarks']
            )
        
        if 'image' in pred_dict and 'image' in target_dict:
            loss += self.weights['photometric'] * self.photometric_loss(
                pred_dict['image'], target_dict['image']
            )
            loss += self.weights['perceptual'] * self.perceptual_loss(
                pred_dict['image'], target_dict['image']
            )
        
        if params is not None and self.weights['regularization'] > 0:
            reg_loss = 0
            for key in ['shape', 'exp', 'tex']:
                if key in params:
                    reg_loss += torch.sum(params[key] ** 2)
            loss += self.weights['regularization'] * reg_loss
        
        return loss


def build_model(backbone='resnet50', pretrained=True, device='cpu'):
    model = ParamRegressionNet(backbone=backbone, pretrained=pretrained)
    model = model.to(device)
    return model


def save_checkpoint(model, optimizer, epoch, loss, checkpoint_path):
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }, checkpoint_path)


def load_checkpoint(model, optimizer, checkpoint_path, device='cpu'):
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    epoch = checkpoint['epoch']
    loss = checkpoint['loss']
    return model, optimizer, epoch, loss
