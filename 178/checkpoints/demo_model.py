import torch
import torch.nn as nn
import torch.nn.functional as F


class DropPath(nn.Module):
    """随机丢弃路径"""
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
    """因子化降维"""
    def __init__(self, C_in, C_out, stride=2):
        super().__init__()
        assert C_out % 2 == 0
        self.relu = nn.ReLU(inplace=False)
        self.conv1 = nn.Conv2d(C_in, C_out // 2, 1, stride=stride, padding=0, bias=False)
        self.conv2 = nn.Conv2d(C_in, C_out // 2, 1, stride=stride, padding=0, bias=False)
        self.bn = nn.BatchNorm2d(C_out, affine=True)  # 启用可学习参数

    def forward(self, x):
        x = self.relu(x)
        out = torch.cat([self.conv1(x), self.conv2(x[:, :, 1:, 1:])], dim=1)
        out = self.bn(out)
        return out


class ConvBlock(nn.Module):
    """卷积块"""
    def __init__(self, C_in, C_out, kernel_size, stride):
        super().__init__()
        padding = kernel_size // 2
        self.op = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_out, kernel_size, stride=stride, padding=padding, bias=False),
            nn.BatchNorm2d(C_out, affine=True)  # 启用可学习参数
        )

    def forward(self, x):
        return self.op(x)


class SepConv(nn.Module):
    """深度可分离卷积"""
    def __init__(self, C_in, C_out, kernel_size, stride, padding):
        super().__init__()
        self.op = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_in, kernel_size=kernel_size, stride=stride,
                      padding=padding, groups=C_in, bias=False),
            nn.Conv2d(C_in, C_in, kernel_size=1, padding=0, bias=False),
            nn.BatchNorm2d(C_in, affine=True),  # 启用可学习参数
            nn.ReLU(inplace=False),
            nn.Conv2d(C_in, C_in, kernel_size=kernel_size, stride=1,
                      padding=padding, groups=C_in, bias=False),
            nn.Conv2d(C_in, C_out, kernel_size=1, padding=0, bias=False),
            nn.BatchNorm2d(C_out, affine=True)  # 启用可学习参数
        )

    def forward(self, x):
        return self.op(x)


class Identity(nn.Module):
    """恒等映射"""
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return x


def export_full_model_state(model, filepath, include_arch_weights=True):
    """
    导出完整的模型状态，包括所有BatchNorm的参数和running stats
    
    Args:
        model: 训练好的模型
        filepath: 保存路径
        include_arch_weights: 是否包含架构权重
    """
    state_dict = model.state_dict()
    
    # 收集BatchNorm的信息用于验证
    bn_info = {}
    for name, module in model.named_modules():
        if isinstance(module, nn.BatchNorm2d):
            bn_info[name] = {
                'weight_shape': tuple(module.weight.shape) if module.weight is not None else None,
                'bias_shape': tuple(module.bias.shape) if module.bias is not None else None,
                'running_mean_shape': tuple(module.running_mean.shape),
                'running_var_shape': tuple(module.running_var.shape),
                'affine': module.affine,
                'track_running_stats': module.track_running_stats,
            }
    
    save_data = {
        'model_state_dict': state_dict,
        'batchnorm_info': bn_info,
        'include_arch_weights': include_arch_weights,
    }
    
    # 如果包含架构权重
    if include_arch_weights and hasattr(model, 'alphas_normal'):
        save_data['alphas_normal'] = model.alphas_normal.detach().cpu()
        save_data['alphas_reduce'] = model.alphas_reduce.detach().cpu()
    
    torch.save(save_data, filepath)
    print(f"完整模型状态已保存到: {filepath}")
    print(f"BatchNorm层数: {len(bn_info)}")
    return save_data


class NormalCell(nn.Module):
    """Normal Cell - 搜索到的最优架构"""
    def __init__(self, C_prev_prev, C_prev, C, reduction_prev=False, drop_path_prob=0.0):
        super().__init__()
        self.num_nodes = 4
        self.drop_path_prob = drop_path_prob

        # 输入预处理
        if reduction_prev:
            self.preprocess0 = FactorizedReduce(C_prev_prev, C, stride=2)
        else:
            self.preprocess0 = nn.Sequential(
                nn.ReLU(inplace=False),
                nn.Conv2d(C_prev_prev, C, 1, stride=1, padding=0, bias=False),
                nn.BatchNorm2d(C)
            )

        self.preprocess1 = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_prev, C, 1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(C)
        )

        # 边操作
        self.op_2_0 = ConvBlock(C, C, 3, 1)
        self.op_2_1 = Identity()
        self.op_3_0 = SepConv(C, C, 3, 1, 1)
        self.op_3_1 = ConvBlock(C, C, 5, 1)
        self.op_4_0 = ConvBlock(C, C, 3, 1)
        self.op_4_1 = nn.AvgPool2d(3, stride=1, padding=1, count_include_pad=False)
        self.op_5_0 = SepConv(C, C, 5, 1, 2)
        self.op_5_1 = Identity()

    def forward(self, s0, s1):
        s0 = self.preprocess0(s0)
        s1 = self.preprocess1(s1)
        states = [s0, s1]

        node_2 = self.op_2_0(states[0]) + self.op_2_1(states[1])
        states.append(node_2)

        node_3 = self.op_3_0(states[0]) + self.op_3_1(states[2])
        states.append(node_3)

        node_4 = self.op_4_0(states[0]) + self.op_4_1(states[3])
        states.append(node_4)

        node_5 = self.op_5_0(states[2]) + self.op_5_1(states[4])
        states.append(node_5)

        return torch.cat([states[2], states[3], states[4], states[5]], dim=1)


class ReductionCell(nn.Module):
    """Reduction Cell - 搜索到的最优架构"""
    def __init__(self, C_prev_prev, C_prev, C, reduction_prev=False, drop_path_prob=0.0):
        super().__init__()
        self.num_nodes = 4
        self.drop_path_prob = drop_path_prob

        # 输入预处理
        if reduction_prev:
            self.preprocess0 = FactorizedReduce(C_prev_prev, C, stride=2)
        else:
            self.preprocess0 = nn.Sequential(
                nn.ReLU(inplace=False),
                nn.Conv2d(C_prev_prev, C, 1, stride=1, padding=0, bias=False),
                nn.BatchNorm2d(C)
            )

        self.preprocess1 = nn.Sequential(
            nn.ReLU(inplace=False),
            nn.Conv2d(C_prev, C, 1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(C)
        )

        # 边操作
        self.op_2_0 = ConvBlock(C, C, 5, 2)
        self.op_2_1 = nn.MaxPool2d(3, stride=2, padding=1)
        self.op_3_0 = ConvBlock(C, C, 7, 2)
        self.op_3_1 = SepConv(C, C, 3, 1, 1)
        self.op_4_0 = ConvBlock(C, C, 3, 2)
        self.op_4_1 = Identity()
        self.op_5_0 = SepConv(C, C, 5, 1, 2)
        self.op_5_1 = nn.AvgPool2d(3, stride=1, padding=1, count_include_pad=False)

    def forward(self, s0, s1):
        s0 = self.preprocess0(s0)
        s1 = self.preprocess1(s1)
        states = [s0, s1]

        node_2 = self.op_2_0(states[0]) + self.op_2_1(states[1])
        states.append(node_2)

        node_3 = self.op_3_0(states[0]) + self.op_3_1(states[2])
        states.append(node_3)

        node_4 = self.op_4_0(states[1]) + self.op_4_1(states[3])
        states.append(node_4)

        node_5 = self.op_5_0(states[2]) + self.op_5_1(states[4])
        states.append(node_5)

        return torch.cat([states[2], states[3], states[4], states[5]], dim=1)


class SearchedNetwork(nn.Module):
    """搜索到的最优网络架构"""
    def __init__(self, C=36, num_classes=10, layers=20, auxiliary=True, drop_path_prob=0.0):
        super().__init__()
        self._auxiliary = auxiliary
        self._layers = layers
        self.drop_path_prob = drop_path_prob

        # Stem层
        self.stem = nn.Sequential(
            nn.Conv2d(3, C * 3, 3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(C * 3)
        )

        # Cells
        self.cells = nn.ModuleList()
        C_prev_prev, C_prev, C_curr = C * 3, C * 3, C
        reduction_prev = False
        self.auxiliary_cell_idx = 2 * layers // 3  # 辅助分类器位置

        for i in range(layers):
            if i in [layers // 3, 2 * layers // 3]:
                C_curr *= 2
                reduction = True
                cell = ReductionCell(C_prev_prev, C_prev, C_curr, reduction_prev, drop_path_prob)
            else:
                reduction = False
                cell = NormalCell(C_prev_prev, C_prev, C_curr, reduction_prev, drop_path_prob)

            self.cells.append(cell)
            C_prev_prev = C_prev
            C_prev = C_curr * 4  # 4个节点拼接
            reduction_prev = reduction

            # 辅助分类器
            if auxiliary and i == self.auxiliary_cell_idx:
                C_to_aux = C_prev
                self.auxiliary_head = nn.Sequential(
                    nn.ReLU(inplace=False),
                    nn.AdaptiveAvgPool2d(1),
                    nn.Conv2d(C_to_aux, 128, 1, bias=False),
                    nn.BatchNorm2d(128),
                    nn.ReLU(inplace=True),
                    nn.Conv2d(128, 768, 1, bias=False),
                    nn.BatchNorm2d(768),
                    nn.ReLU(inplace=True),
                    nn.Flatten(),
                    nn.Linear(768, 10)
                )

        # 最终分类器
        self.global_pooling = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Linear(C_prev, 10)

    def forward(self, x):
        s0 = s1 = self.stem(x)
        aux_logits = None

        for i, cell in enumerate(self.cells):
            s0, s1 = s1, cell(s0, s1)
            if self._auxiliary and i == self.auxiliary_cell_idx and self.training:
                aux_logits = self.auxiliary_head(s1)

        out = self.global_pooling(s1)
        out = out.view(out.size(0), -1)
        logits = self.classifier(out)

        if self._auxiliary and self.training:
            return logits, aux_logits
        return logits
