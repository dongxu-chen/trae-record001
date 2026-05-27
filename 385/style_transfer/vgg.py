"""
VGG19特征提取器
使用预训练的VGG19网络提取图像的内容和风格特征
"""

import torch
import torch.nn as nn
from torchvision import models


class VGG19Extractor(nn.Module):
    """VGG19特征提取器，用于提取内容和风格特征"""

    CONTENT_LAYERS = ['relu4_2']
    STYLE_LAYERS = ['relu1_1', 'relu2_1', 'relu3_1', 'relu4_1', 'relu5_1']
    ALL_LAYERS = CONTENT_LAYERS + STYLE_LAYERS

    def __init__(self, use_normalized_weights=True):
        super(VGG19Extractor, self).__init__()
        self._build_model()
        self.use_normalized_weights = use_normalized_weights

        self.register_buffer(
            'mean',
            torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        )
        self.register_buffer(
            'std',
            torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        )

    def _build_model(self):
        """构建VGG19模型"""
        vgg = models.vgg19(pretrained=True).features.eval()

        layer_names = {
            '0': 'relu1_1', '5': 'relu2_1', '10': 'relu3_1',
            '19': 'relu4_1', '21': 'relu4_2', '28': 'relu5_1'
        }

        self.layers = nn.ModuleDict()
        for name in self.ALL_LAYERS:
            self.layers[name] = None

        current_name = None
        for idx, layer in enumerate(vgg.children()):
            if str(idx) in layer_names:
                current_name = layer_names[str(idx)]
                self.layers[current_name] = nn.Sequential()

            if current_name is not None and self.layers[current_name] is not None:
                if isinstance(layer, nn.ReLU):
                    layer = nn.ReLU(inplace=False)
                self.layers[current_name].add_module(str(idx), layer)

        for param in self.parameters():
            param.requires_grad = False

    def forward(self, x, target_layers=None):
        """
        前向传播提取特征

        Args:
            x: 输入图像张量 [B, 3, H, W]
            target_layers: 需要提取的层名称列表，None表示提取所有层

        Returns:
            特征字典 {层名: 特征张量}
        """
        if target_layers is None:
            target_layers = self.ALL_LAYERS

        x = (x - self.mean) / self.std

        features = {}
        for layer_name in target_layers:
            if layer_name in self.layers and self.layers[layer_name] is not None:
                x = self.layers[layer_name](x)
                features[layer_name] = x.clone()

        return features

    def get_content_features(self, x):
        """提取内容特征"""
        return self.forward(x, self.CONTENT_LAYERS)

    def get_style_features(self, x):
        """提取风格特征"""
        return self.forward(x, self.STYLE_LAYERS)

    def get_all_features(self, x):
        """提取所有特征"""
        return self.forward(x, self.ALL_LAYERS)
