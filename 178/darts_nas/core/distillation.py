"""
知识蒸馏模块
支持搜索到的轻量化模型从教师模型中学习，提升精度
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Dict, Tuple


class KDLoss(nn.Module):
    """
    知识蒸馏损失
    结合硬标签损失和软标签损失（KL散度）
    """
    
    def __init__(self, temperature: float = 4.0, alpha: float = 0.7, 
                 hard_loss_weight: float = 1.0, device: Optional[torch.device] = None):
        """
        Args:
            temperature: 蒸馏温度，越高软标签越平滑
            alpha: 软标签损失权重，硬标签损失权重为 1-alpha
            hard_loss_weight: 硬标签损失的额外权重
            device: 计算设备
        """
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha
        self.hard_loss_weight = hard_loss_weight
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.hard_criterion = nn.CrossEntropyLoss().to(self.device)
        self.soft_criterion = nn.KLDivLoss(reduction='batchmean').to(self.device)
    
    def forward(self, student_logits: torch.Tensor, teacher_logits: torch.Tensor, 
                labels: torch.Tensor) -> torch.Tensor:
        """
        计算蒸馏损失
        
        Args:
            student_logits: 学生模型输出logits
            teacher_logits: 教师模型输出logits
            labels: 真实标签
        
        Returns:
            总损失
        """
        # 硬标签损失
        hard_loss = self.hard_criterion(student_logits, labels)
        
        # 软标签损失 (KL散度)
        soft_student = F.log_softmax(student_logits / self.temperature, dim=1)
        soft_teacher = F.softmax(teacher_logits / self.temperature, dim=1)
        soft_loss = self.soft_criterion(soft_student, soft_teacher) * (self.temperature ** 2)
        
        # 综合损失
        total_loss = (
            self.hard_loss_weight * (1 - self.alpha) * hard_loss 
            + self.alpha * soft_loss
        )
        
        return total_loss


class FeatureDistillationLoss(nn.Module):
    """
    特征级蒸馏损失
    让学生模型的中间特征图匹配教师模型的特征图
    """
    
    def __init__(self, device: Optional[torch.device] = None):
        super().__init__()
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.mse_loss = nn.MSELoss().to(self.device)
    
    def forward(self, student_features: torch.Tensor, 
                teacher_features: torch.Tensor) -> torch.Tensor:
        """
        计算特征蒸馏损失
        
        Args:
            student_features: 学生模型的中间特征
            teacher_features: 教师模型的中间特征
        
        Returns:
            特征匹配损失
        """
        # 如果形状不匹配，使用1x1卷积对齐
        if student_features.shape != teacher_features.shape:
            student_features = self._align_features(student_features, teacher_features.shape)
        
        return self.mse_loss(student_features, teacher_features)
    
    def _align_features(self, features: torch.Tensor, target_shape: Tuple[int, ...]) -> torch.Tensor:
        """对齐特征形状"""
        B, C, H, W = features.shape
        _, T_C, T_H, T_W = target_shape
        
        # 通道对齐
        if C != T_C:
            align_conv = nn.Conv2d(C, T_C, kernel_size=1, bias=False).to(features.device)
            features = align_conv(features)
        
        # 空间尺寸对齐
        if H != T_H or W != T_W:
            features = F.interpolate(features, size=(T_H, T_W), mode='bilinear', align_corners=False)
        
        return features


class AttentionTransferLoss(nn.Module):
    """
    注意力转移损失 (Attention Transfer)
    通过注意力图进行知识蒸馏
    """
    
    def __init__(self, p: float = 2.0, device: Optional[torch.device] = None):
        """
        Args:
            p: 归一化指数
            device: 计算设备
        """
        super().__init__()
        self.p = p
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def _attention_map(self, features: torch.Tensor) -> torch.Tensor:
        """计算注意力图"""
        B, C, H, W = features.shape
        
        # 计算通道维度的统计量
        attention = torch.pow(torch.abs(features), self.p).sum(dim=1)  # [B, H, W]
        attention = attention.view(B, -1)  # [B, H*W]
        
        # 归一化
        attention = attention / attention.sum(dim=1, keepdim=True)
        attention = attention.view(B, H, W)
        
        return attention
    
    def forward(self, student_features: torch.Tensor, 
                teacher_features: torch.Tensor) -> torch.Tensor:
        """
        计算注意力转移损失
        
        Args:
            student_features: 学生模型特征
            teacher_features: 教师模型特征
        
        Returns:
            注意力匹配损失
        """
        student_attention = self._attention_map(student_features)
        teacher_attention = self._attention_map(teacher_features)
        
        # 如果空间尺寸不匹配，插值对齐
        if student_attention.shape != teacher_attention.shape:
            student_attention = F.interpolate(
                student_attention.unsqueeze(1), 
                size=teacher_attention.shape[-2:],
                mode='bilinear',
                align_corners=False
            ).squeeze(1)
        
        # MSE损失
        loss = F.mse_loss(student_attention, teacher_attention)
        return loss


class TeacherModel:
    """
    教师模型封装类
    支持加载预训练模型作为教师
    """
    
    def __init__(self, model: nn.Module, device: Optional[torch.device] = None,
                 is_normalized: bool = True):
        """
        Args:
            model: 教师模型
            device: 计算设备
            is_normalized: 教师模型是否已进行softmax归一化
        """
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = model.to(self.device)
        self.model.eval()
        self.is_normalized = is_normalized
        
        # 用于特征提取的钩子
        self._feature_hooks = []
        self._extracted_features = {}
    
    def get_logits(self, inputs: torch.Tensor) -> torch.Tensor:
        """获取教师模型的logits输出"""
        inputs = inputs.to(self.device)
        with torch.no_grad():
            logits = self.model(inputs)
        
        # 如果是概率输出，转换回logits
        if self.is_normalized:
            logits = torch.log(logits + 1e-10)
        
        return logits
    
    def register_feature_hook(self, layer_names: list):
        """
        注册特征提取钩子
        
        Args:
            layer_names: 需要提取特征的层名称列表
        """
        self._feature_hooks = []
        self._extracted_features = {}
        
        for name, module in self.model.named_modules():
            if name in layer_names:
                hook = module.register_forward_hook(
                    self._get_feature_hook(name)
                )
                self._feature_hooks.append(hook)
    
    def _get_feature_hook(self, layer_name: str):
        """获取特征提取钩子函数"""
        def hook(module, input, output):
            self._extracted_features[layer_name] = output.detach()
        return hook
    
    def get_features(self, inputs: torch.Tensor) -> Dict[str, torch.Tensor]:
        """获取中间特征"""
        inputs = inputs.to(self.device)
        self._extracted_features = {}
        
        with torch.no_grad():
            _ = self.model(inputs)
        
        return self._extracted_features
    
    def clear_hooks(self):
        """清除所有钩子"""
        for hook in self._feature_hooks:
            hook.remove()
        self._feature_hooks = []
        self._extracted_features = {}


def create_default_teacher(num_classes: int = 10, device: Optional[torch.device] = None) -> TeacherModel:
    """
    创建默认的教师模型 (WideResNet风格的大模型)
    
    Args:
        num_classes: 分类类别数
        device: 计算设备
    
    Returns:
        教师模型封装
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 创建一个较大的模型作为教师
    class WideResNetTeacher(nn.Module):
        def __init__(self, num_classes=10):
            super().__init__()
            
            self.stem = nn.Sequential(
                nn.Conv2d(3, 64, 3, stride=1, padding=1, bias=False),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True)
            )
            
            self.layer1 = self._make_layer(64, 128, 3, stride=2)
            self.layer2 = self._make_layer(128, 256, 3, stride=2)
            self.layer3 = self._make_layer(256, 512, 3, stride=2)
            
            self.avgpool = nn.AdaptiveAvgPool2d(1)
            self.fc = nn.Linear(512, num_classes)
            
            self._initialize_weights()
        
        def _make_layer(self, in_channels, out_channels, num_blocks, stride):
            layers = []
            layers.append(nn.Conv2d(in_channels, out_channels, 3, stride=stride, padding=1, bias=False))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU(inplace=True))
            
            for _ in range(num_blocks - 1):
                layers.append(nn.Conv2d(out_channels, out_channels, 3, stride=1, padding=1, bias=False))
                layers.append(nn.BatchNorm2d(out_channels))
                layers.append(nn.ReLU(inplace=True))
            
            return nn.Sequential(*layers)
        
        def _initialize_weights(self):
            for m in self.modules():
                if isinstance(m, nn.Conv2d):
                    nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                elif isinstance(m, nn.BatchNorm2d):
                    nn.init.constant_(m.weight, 1)
                    nn.init.constant_(m.bias, 0)
        
        def forward(self, x):
            x = self.stem(x)
            x = self.layer1(x)
            x = self.layer2(x)
            x = self.layer3(x)
            x = self.avgpool(x)
            x = x.view(x.size(0), -1)
            x = self.fc(x)
            return x
    
    teacher_model = WideResNetTeacher(num_classes=num_classes)
    return TeacherModel(teacher_model, device=device, is_normalized=False)


class DistillationTrainer:
    """
    蒸馏训练器
    整合多种蒸馏损失，训练学生模型
    """
    
    def __init__(self, teacher: TeacherModel, 
                 temperature: float = 4.0,
                 alpha: float = 0.7,
                 feature_weight: float = 0.3,
                 attention_weight: float = 0.0,
                 device: Optional[torch.device] = None):
        """
        Args:
            teacher: 教师模型
            temperature: 蒸馏温度
            alpha: 软标签权重
            feature_weight: 特征蒸馏权重
            attention_weight: 注意力蒸馏权重
            device: 计算设备
        """
        self.teacher = teacher
        self.device = device if device else torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.kd_loss = KDLoss(temperature, alpha, device=self.device)
        self.feature_loss = FeatureDistillationLoss(device=self.device) if feature_weight > 0 else None
        self.attention_loss = AttentionTransferLoss(device=self.device) if attention_weight > 0 else None
        
        self.feature_weight = feature_weight
        self.attention_weight = attention_weight
    
    def train_step(self, student_model: nn.Module, inputs: torch.Tensor, 
                   labels: torch.Tensor, optimizer: torch.optim.Optimizer,
                   grad_clip: float = 5.0) -> Dict[str, float]:
        """
        执行一步蒸馏训练
        
        Args:
            student_model: 学生模型
            inputs: 输入数据
            labels: 标签
            optimizer: 优化器
            grad_clip: 梯度裁剪阈值
        
        Returns:
            损失字典
        """
        student_model.train()
        inputs = inputs.to(self.device)
        labels = labels.to(self.device)
        
        # 获取教师模型输出
        with torch.no_grad():
            teacher_logits = self.teacher.get_logits(inputs)
        
        optimizer.zero_grad()
        
        # 学生模型前向传播
        student_logits = student_model(inputs)
        
        # 计算蒸馏损失
        loss = self.kd_loss(student_logits, teacher_logits, labels)
        
        # 特征蒸馏（如果启用）
        if self.feature_loss is not None and self.feature_weight > 0:
            # 这里可以扩展为提取中间特征进行匹配
            pass
        
        # 注意力蒸馏（如果启用）
        if self.attention_loss is not None and self.attention_weight > 0:
            # 这里可以扩展为提取注意力图进行匹配
            pass
        
        # 反向传播
        loss.backward()
        nn.utils.clip_grad_norm_(student_model.parameters(), grad_clip)
        optimizer.step()
        
        # 计算准确率
        _, predicted = student_logits.max(1)
        correct = predicted.eq(labels).sum().item()
        accuracy = 100.0 * correct / labels.size(0)
        
        return {
            'loss': loss.item(),
            'accuracy': accuracy,
        }
    
    def validate(self, student_model: nn.Module, val_loader: torch.utils.data.DataLoader) -> Dict[str, float]:
        """
        验证学生模型
        
        Args:
            student_model: 学生模型
            val_loader: 验证数据加载器
        
        Returns:
            验证指标字典
        """
        student_model.eval()
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs = inputs.to(self.device)
                labels = labels.to(self.device)
                
                teacher_logits = self.teacher.get_logits(inputs)
                student_logits = student_model(inputs)
                
                loss = self.kd_loss(student_logits, teacher_logits, labels)
                total_loss += loss.item() * inputs.size(0)
                
                _, predicted = student_logits.max(1)
                total_correct += predicted.eq(labels).sum().item()
                total_samples += labels.size(0)
        
        avg_loss = total_loss / total_samples
        accuracy = 100.0 * total_correct / total_samples
        
        return {
            'loss': avg_loss,
            'accuracy': accuracy,
        }
