"""
操作基元 - 定义搜索空间中的基本操作
包括不同卷积核大小的卷积、池化、跳层连接等
"""

import torch
import torch.nn as nn


class DropPath(nn.Module):
    """随机丢弃路径 (用于正则化)"""
    def __init__(self, drop_prob=0.0):
        super().__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        if self.drop_prob == 0.0 or not self.training:
            return x
        keep_prob = 1 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
        random_tensor.floor_()
        output = x.div(keep_prob) * random_tensor
        return output


class FactorizedReduce(nn.Module):
    """因子化降维 - 用于空间尺寸减半时保持通道数匹配"""
    def __init__(self, C_in, C_out, stride=2, affine=True):
        super().__init__()
        assert C_out % 2 == 0, "C_out must be even"
        self.relu = nn.ReLU(inplace=False)
        self.conv1 = nn.Conv2d(C_in, C_out // 2, 1, stride=stride, padding=0, bias=False)
        self.conv2 = nn.Conv2d(C_in, C_out // 2, 1, stride=stride, padding=0, bias=False)
        self.bn = nn.BatchNorm2d(C_out, affine=affine)

    def forward(self, x):
        x = self.relu(x)
        out = torch.cat([self.conv1(x), self.conv2(x[:, :, 1:, 1:])], dim=1)
        out = self.bn(out)
        return out


class ReLUConvBN(nn.Module):
    """ReLU -> Conv -> BN 组合"""
    def __init__(self, C_in, C_out, kernel_size, stride, padding, affine=True):
        super().__init__()
        self.op = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_out, kernel_size, stride=stride, padding=padding, bias=False),
            nn.BatchNorm2d(C_out, affine=affine)
        )

    def forward(self, x):
        return self.op(x)


class DilConv(nn.Module):
    """深度可分离卷积 (Dilated Convolution)"""
    def __init__(self, C_in, C_out, kernel_size, stride, padding, dilation, affine=True):
        super().__init__()
        self.op = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_in, kernel_size=kernel_size, stride=stride,
                      padding=padding, dilation=dilation, groups=C_in, bias=False),
            nn.Conv2d(C_in, C_out, kernel_size=1, padding=0, bias=False),
            nn.BatchNorm2d(C_out, affine=affine)
        )

    def forward(self, x):
        return self.op(x)


class SepConv(nn.Module):
    """深度可分离卷积 (Depthwise Separable Convolution)"""
    def __init__(self, C_in, C_out, kernel_size, stride, padding, affine=True):
        super().__init__()
        self.op = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_in, kernel_size=kernel_size, stride=stride,
                      padding=padding, groups=C_in, bias=False),
            nn.Conv2d(C_in, C_in, kernel_size=1, padding=0, bias=False),
            nn.BatchNorm2d(C_in, affine=affine),
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_in, kernel_size=kernel_size, stride=1,
                      padding=padding, groups=C_in, bias=False),
            nn.Conv2d(C_in, C_out, kernel_size=1, padding=0, bias=False),
            nn.BatchNorm2d(C_out, affine=affine)
        )

    def forward(self, x):
        return self.op(x)


class ConvBlock(nn.Module):
    """标准卷积块 - 支持不同卷积核大小"""
    def __init__(self, C_in, C_out, kernel_size, stride, affine=True):
        super().__init__()
        padding = kernel_size // 2
        self.op = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_out, kernel_size, stride=stride, padding=padding, bias=False),
            nn.BatchNorm2d(C_out, affine=affine)
        )

    def forward(self, x):
        return self.op(x)


class Identity(nn.Module):
    """恒等映射 - 跳层连接"""
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return x


class Zero(nn.Module):
    """零操作 - 表示不选择该连接"""
    def __init__(self, stride):
        super().__init__()
        self.stride = stride

    def forward(self, x):
        if self.stride == 1:
            return x * 0.0
        return x[:, :, ::self.stride, ::self.stride] * 0.0


class MaxPooling(nn.Module):
    """最大池化"""
    def __init__(self, kernel_size, stride, padding):
        super().__init__()
        self.op = nn.MaxPool2d(kernel_size, stride=stride, padding=padding)

    def forward(self, x):
        return self.op(x)


class AvgPooling(nn.Module):
    """平均池化"""
    def __init__(self, kernel_size, stride, padding):
        super().__init__()
        self.op = nn.AvgPool2d(kernel_size, stride=stride, padding=padding, count_include_pad=False)

    def forward(self, x):
        return self.op(x)


def get_search_primitives(C, stride):
    """
    获取搜索空间中的所有候选操作
    Args:
        C: 通道数
        stride: 步长
    Returns:
        操作列表
    """
    primitives = [
        ('conv3x3', ConvBlock(C, C, 3, stride)),
        ('conv5x5', ConvBlock(C, C, 5, stride)),
        ('conv7x7', ConvBlock(C, C, 7, stride)),
        ('sep_conv3x3', SepConv(C, C, 3, stride, 1)),
        ('sep_conv5x5', SepConv(C, C, 5, stride, 2)),
        ('max_pool3x3', MaxPooling(3, stride, 1)),
        ('avg_pool3x3', AvgPooling(3, stride, 1)),
        ('identity', Identity() if stride == 1 else FactorizedReduce(C, C, stride)),
    ]
    return primitives


class MixedOp(nn.Module):
    """
    混合操作 - 对所有候选操作进行加权求和
    权重由架构参数控制，通过softmax归一化
    """
    def __init__(self, C, stride):
        super().__init__()
        self._ops = nn.ModuleList()
        self._op_names = []
        
        for name, op in get_search_primitives(C, stride):
            self._ops.append(op)
            self._op_names.append(name)

    def forward(self, x, weights, temperature=1.0):
        """
        Args:
            x: 输入特征
            weights: 架构权重 (num_ops,)
            temperature: softmax温度系数
        Returns:
            加权求和后的输出
        """
        if temperature != 1.0:
            weights = weights / temperature
        
        normalized_weights = torch.softmax(weights, dim=0)
        output = 0.0
        for w, op in zip(normalized_weights, self._ops):
            output = output + w * op(x)
        return output

    @property
    def op_names(self):
        return self._op_names
