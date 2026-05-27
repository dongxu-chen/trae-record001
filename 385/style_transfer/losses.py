"""
感知损失函数
包含内容损失、风格损失、总变差损失、时序损失
支持自适应强度调度和多风格插值
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ContentLoss(nn.Module):
    """内容损失：基于特征图的L2距离"""

    def __init__(self):
        super(ContentLoss, self).__init__()
        self.target = None

    def set_target(self, target_features):
        """设置目标内容特征"""
        self.target = target_features.detach()

    def forward(self, input_features):
        """计算内容损失"""
        return F.mse_loss(input_features, self.target)


class StyleLoss(nn.Module):
    """风格损失：基于Gram矩阵的L2距离"""

    def __init__(self):
        super(StyleLoss, self).__init__()
        self.target_gram = None

    def set_target(self, target_features):
        """设置目标风格特征（计算Gram矩阵）"""
        self.target_gram = self._gram_matrix(target_features).detach()

    def _gram_matrix(self, x):
        """计算Gram矩阵"""
        b, c, h, w = x.size()
        features = x.view(b, c, h * w)
        gram = torch.bmm(features, features.transpose(1, 2))
        return gram / (c * h * w)

    def forward(self, input_features):
        """计算风格损失"""
        input_gram = self._gram_matrix(input_features)
        return F.mse_loss(input_gram, self.target_gram)


class TotalVariationLoss(nn.Module):
    """总变差损失：用于平滑图像，减少噪声"""

    def __init__(self):
        super(TotalVariationLoss, self).__init__()

    def forward(self, x):
        """计算总变差损失"""
        batch_size, channels, height, width = x.size()

        tv_h = torch.pow(x[:, :, 1:, :] - x[:, :, :-1, :], 2).sum()
        tv_w = torch.pow(x[:, :, :, 1:] - x[:, :, :, :-1], 2).sum()

        return (tv_h + tv_w) / (batch_size * channels * height * width)


class AdaptiveScheduler:
    """
    自适应强度调度器
    根据当前训练进度动态调整内容/风格损失权重

    策略:
    - 训练初期: 偏向内容保留，帮助定位结构
    - 训练中期: 逐渐增加风格权重
    - 训练后期: 稳定在目标强度
    """

    def __init__(
        self,
        target_intensity=1.0,
        warmup_steps=100,
        content_preservation_factor=0.5,
    ):
        """
        初始化自适应调度器

        Args:
            target_intensity: 目标风格强度
            warmup_steps: 预热步数，在此期间偏向内容保留
            content_preservation_factor: 内容保留因子，低强度时增加此值
        """
        self.target_intensity = target_intensity
        self.warmup_steps = warmup_steps
        self.content_preservation_factor = content_preservation_factor

    def compute_weights(self, current_step, total_steps, base_content_weight=1.0):
        """
        计算当前步的内容和风格权重

        Args:
            current_step: 当前训练步数
            total_steps: 总训练步数
            base_content_weight: 基础内容损失权重

        Returns:
            (content_weight, style_weight) 元组
        """
        progress = min(current_step / total_steps, 1.0)

        if current_step < self.warmup_steps:
            warmup_progress = current_step / self.warmup_steps
            intensity = self.target_intensity * (0.1 + 0.9 * warmup_progress)
        else:
            intensity = self.target_intensity

        if self.target_intensity < 1.0:
            content_boost = 1.0 + self.content_preservation_factor * (1.0 - self.target_intensity)
            content_weight = base_content_weight * content_boost
            style_weight = content_weight * intensity
        else:
            content_weight = base_content_weight
            style_weight = content_weight * intensity

        return content_weight, style_weight


class MultiStyleLoss(nn.Module):
    """
    多风格损失：支持风格插值
    可以在多个风格之间进行平滑过渡
    """

    def __init__(self, num_styles=2):
        """
        初始化多风格损失

        Args:
            num_styles: 风格数量
        """
        super(MultiStyleLoss, self).__init__()
        self.num_styles = num_styles
        self.target_grams = None
        self.style_weights = None

    def _gram_matrix(self, x):
        """计算Gram矩阵"""
        b, c, h, w = x.size()
        features = x.view(b, c, h * w)
        gram = torch.bmm(features, features.transpose(1, 2))
        return gram / (c * h * w)

    def set_targets(self, style_features_list, style_weights=None):
        """
        设置多个风格目标

        Args:
            style_features_list: 风格特征列表，每个元素是一个风格的特征字典
            style_weights: 风格权重列表，如果为None则平均分配
        """
        if style_weights is None:
            style_weights = [1.0 / len(style_features_list)] * len(style_features_list)

        assert len(style_features_list) == len(style_weights), \
            "风格特征数量必须与权重数量匹配"

        self.style_weights = style_weights
        self.target_grams = []

        for style_features in style_features_list:
            style_grams = {}
            for layer, features in style_features.items():
                style_grams[layer] = self._gram_matrix(features).detach()
            self.target_grams.append(style_grams)

    def interpolate_targets(self, interpolation_weights):
        """
        插值计算目标Gram矩阵

        Args:
            interpolation_weights: 插值权重 [w1, w2, ...]，和为1

        Returns:
            插值后的Gram矩阵字典
        """
        if self.target_grams is None:
            raise ValueError("请先调用 set_targets 设置风格目标")

        assert len(interpolation_weights) == len(self.target_grams), \
            "插值权重数量必须与风格数量匹配"

        interpolated_grams = {}

        for layer in self.target_grams[0].keys():
            weighted_gram = None
            for i, target_grams in enumerate(self.target_grams):
                if weighted_gram is None:
                    weighted_gram = interpolation_weights[i] * target_grams[layer]
                else:
                    weighted_gram += interpolation_weights[i] * target_grams[layer]
            interpolated_grams[layer] = weighted_gram

        return interpolated_grams

    def forward(self, input_features, interpolation_weights=None):
        """
        计算多风格损失

        Args:
            input_features: 输入特征字典
            interpolation_weights: 插值权重，如果为None则使用初始化的权重

        Returns:
            风格损失值
        """
        if interpolation_weights is None:
            interpolation_weights = self.style_weights

        target_grams = self.interpolate_targets(interpolation_weights)

        total_loss = 0.0
        num_layers = 0

        for layer, input_feat in input_features.items():
            if layer in target_grams:
                input_gram = self._gram_matrix(input_feat)
                total_loss += F.mse_loss(input_gram, target_grams[layer])
                num_layers += 1

        if num_layers > 0:
            total_loss /= num_layers

        return total_loss


class TemporalLoss(nn.Module):
    """
    帧间时序一致性损失
    用于视频风格迁移，避免帧间闪烁
    """

    def __init__(self, temporal_weight=1e3, loss_type='l1'):
        """
        初始化时序损失

        Args:
            temporal_weight: 时序损失权重
            loss_type: 损失类型，'l1' 或 'l2'
        """
        super(TemporalLoss, self).__init__()
        self.temporal_weight = temporal_weight
        self.loss_type = loss_type
        self.previous_frame = None

    def set_previous_frame(self, frame):
        """设置前一帧"""
        self.previous_frame = frame.detach()

    def reset(self):
        """重置前一帧"""
        self.previous_frame = None

    def forward(self, current_frame):
        """
        计算时序损失

        Args:
            current_frame: 当前帧张量

        Returns:
            时序损失值
        """
        if self.previous_frame is None:
            return torch.tensor(0.0, device=current_frame.device)

        if self.loss_type == 'l1':
            loss = F.l1_loss(current_frame, self.previous_frame)
        else:
            loss = F.mse_loss(current_frame, self.previous_frame)

        return self.temporal_weight * loss


class PerceptualLoss(nn.Module):
    """
    感知损失：组合内容损失、风格损失和总变差损失

    总损失 = content_weight * content_loss + style_weight * style_loss + tv_weight * tv_loss

    支持自适应强度调度:
    - 低强度时自动提升内容权重以保留更多纹理
    - 训练过程中动态调整权重

    支持多风格插值:
    - 可以在多个风格之间进行平滑过渡
    """

    def __init__(
        self,
        content_weight=1.0,
        style_weight=1e4,
        tv_weight=1e-6,
        content_layers=None,
        style_layers=None,
        use_adaptive_scheduling=True,
        target_intensity=None,
        warmup_steps=100,
        content_preservation_factor=0.5,
        use_multi_style=False,
        num_styles=2,
    ):
        super(PerceptualLoss, self).__init__()

        self.content_weight = content_weight
        self.style_weight = style_weight
        self.tv_weight = tv_weight

        if content_layers is None:
            content_layers = ['relu4_2']
        if style_layers is None:
            style_layers = ['relu1_1', 'relu2_1', 'relu3_1', 'relu4_1', 'relu5_1']

        self.content_layers = content_layers
        self.style_layers = style_layers

        self.content_losses = nn.ModuleDict({
            layer: ContentLoss() for layer in content_layers
        })

        if use_multi_style:
            self.style_loss = MultiStyleLoss(num_styles=num_styles)
        else:
            self.style_losses = nn.ModuleDict({
                layer: StyleLoss() for layer in style_layers
            })

        self.tv_loss = TotalVariationLoss()
        self.temporal_loss = TemporalLoss()

        self.use_adaptive_scheduling = use_adaptive_scheduling
        self.target_intensity = target_intensity if target_intensity is not None else style_weight / content_weight

        if use_adaptive_scheduling:
            self.scheduler = AdaptiveScheduler(
                target_intensity=self.target_intensity,
                warmup_steps=warmup_steps,
                content_preservation_factor=content_preservation_factor,
            )
        else:
            self.scheduler = None

        self.use_multi_style = use_multi_style
        self.current_step = 0
        self.total_steps = 500
        self.interpolation_weights = None

    def set_training_steps(self, total_steps):
        """设置总训练步数"""
        self.total_steps = total_steps

    def set_content_target(self, content_features):
        """设置内容目标特征"""
        for layer in self.content_layers:
            if layer in content_features:
                self.content_losses[layer].set_target(content_features[layer])

    def set_style_target(self, style_features):
        """设置单个风格目标特征"""
        if self.use_multi_style:
            self.style_loss.set_targets([style_features], [1.0])
        else:
            for layer in self.style_layers:
                if layer in style_features:
                    self.style_losses[layer].set_target(style_features[layer])

    def set_multi_style_targets(self, style_features_list, style_weights=None):
        """设置多个风格目标（用于风格插值）"""
        if not self.use_multi_style:
            raise ValueError("请在初始化时设置 use_multi_style=True")
        self.style_loss.set_targets(style_features_list, style_weights)

    def set_interpolation_weights(self, weights):
        """设置插值权重"""
        self.interpolation_weights = weights

    def update_step(self, step):
        """更新当前训练步，用于自适应调度"""
        self.current_step = step

    def set_previous_frame(self, frame):
        """设置前一帧（用于时序损失）"""
        self.temporal_loss.set_previous_frame(frame)

    def reset_temporal(self):
        """重置时序损失"""
        self.temporal_loss.reset()

    def forward(self, generated_features, generated_image=None):
        """
        计算总感知损失

        Args:
            generated_features: 生成图像的特征字典
            generated_image: 生成图像张量（用于TV损失和时序损失）

        Returns:
            总损失值
        """
        total_content_loss = 0.0
        total_style_loss = 0.0

        for layer in self.content_layers:
            if layer in generated_features and layer in self.content_losses:
                total_content_loss += self.content_losses[layer](
                    generated_features[layer]
                )

        total_content_loss /= len(self.content_layers)

        if self.use_multi_style:
            style_features = {
                layer: generated_features[layer]
                for layer in self.style_layers
                if layer in generated_features
            }
            total_style_loss = self.style_loss(style_features, self.interpolation_weights)
        else:
            for layer in self.style_layers:
                if layer in generated_features and layer in self.style_losses:
                    total_style_loss += self.style_losses[layer](
                        generated_features[layer]
                    )
            total_style_loss /= len(self.style_layers)

        if self.use_adaptive_scheduling and self.scheduler is not None:
            content_weight, style_weight = self.scheduler.compute_weights(
                self.current_step, self.total_steps, self.content_weight
            )
        else:
            content_weight = self.content_weight
            style_weight = self.style_weight

        total_loss = (
            content_weight * total_content_loss +
            style_weight * total_style_loss
        )

        if generated_image is not None:
            if self.tv_weight > 0:
                total_loss += self.tv_weight * self.tv_loss(generated_image)

            if self.temporal_loss.temporal_weight > 0:
                total_loss += self.temporal_loss(generated_image)

        return total_loss

    def get_style_strength(self):
        """获取风格强度"""
        return self.style_weight / self.content_weight

    def set_style_strength(self, strength):
        """
        设置风格强度

        Args:
            strength: 风格强度值，值越大风格越明显
        """
        self.style_weight = self.content_weight * strength
        self.target_intensity = strength
        if self.scheduler is not None:
            self.scheduler.target_intensity = strength
