"""
PyTorch模型代码生成器 - 根据搜索到的架构生成完整的模型代码
"""

import json
from darts_nas.core.ops import (
    ConvBlock, SepConv, Identity, Zero,
    MaxPooling, AvgPooling, FactorizedReduce
)


OP_IMPORTS = '''import torch
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
'''


def get_op_code(op_name, C_in, C_out, stride):
    """根据操作名生成PyTorch代码"""
    if op_name == 'conv3x3':
        return f"ConvBlock({C_in}, {C_out}, 3, {stride})"
    elif op_name == 'conv5x5':
        return f"ConvBlock({C_in}, {C_out}, 5, {stride})"
    elif op_name == 'conv7x7':
        return f"ConvBlock({C_in}, {C_out}, 7, {stride})"
    elif op_name == 'sep_conv3x3':
        return f"SepConv({C_in}, {C_out}, 3, {stride}, 1)"
    elif op_name == 'sep_conv5x5':
        return f"SepConv({C_in}, {C_out}, 5, {stride}, 2)"
    elif op_name == 'max_pool3x3':
        return f"nn.MaxPool2d(3, stride={stride}, padding=1)"
    elif op_name == 'avg_pool3x3':
        return f"nn.AvgPool2d(3, stride={stride}, padding=1, count_include_pad=False)"
    elif op_name == 'identity':
        if stride == 1:
            return "Identity()"
        else:
            return f"FactorizedReduce({C_in}, {C_out}, stride={stride})"
    else:
        return "Identity()"


def generate_cell_code(gene, cell_name, num_nodes, is_reduction=False):
    """生成单个Cell的类代码"""
    code = []
    code.append(f"class {cell_name}(nn.Module):")
    code.append(f'    """{"Reduction" if is_reduction else "Normal"} Cell - 搜索到的最优架构"""')
    code.append(f"    def __init__(self, C_prev_prev, C_prev, C, reduction_prev=False, drop_path_prob=0.0):")
    code.append(f"        super().__init__()")
    code.append(f"        self.num_nodes = {num_nodes}")
    code.append(f"        self.drop_path_prob = drop_path_prob")
    code.append("")
    
    # 预处理
    code.append("        # 输入预处理")
    code.append("        if reduction_prev:")
    code.append(f"            self.preprocess0 = FactorizedReduce(C_prev_prev, C, stride=2)")
    code.append("        else:")
    code.append("            self.preprocess0 = nn.Sequential(")
    code.append("                nn.ReLU(inplace=False),")
    code.append("                nn.Conv2d(C_prev_prev, C, 1, stride=1, padding=0, bias=False),")
    code.append("                nn.BatchNorm2d(C)")
    code.append("            )")
    code.append("")
    code.append("        self.preprocess1 = nn.Sequential(")
    code.append("            nn.ReLU(inplace=False),")
    code.append("            nn.Conv2d(C_prev, C, 1, stride=1, padding=0, bias=False),")
    code.append("            nn.BatchNorm2d(C)")
    code.append("        )")
    code.append("")
    
    # 为每条边创建操作
    code.append("        # 边操作")
    
    # 按节点分组
    node_edges = {}
    for edge in gene:
        to_node = edge['to']
        if to_node not in node_edges:
            node_edges[to_node] = []
        node_edges[to_node].append(edge)
    
    for to_node in sorted(node_edges.keys()):
        edges = node_edges[to_node]
        for i, edge in enumerate(edges):
            from_node = edge['from']
            op_name = edge['op']
            stride = 2 if is_reduction and from_node < 2 else 1
            op_code = get_op_code(op_name, 'C', 'C', stride)
            code.append(f"        self.op_{to_node}_{i} = {op_code}")
    
    code.append("")
    
    # forward方法
    code.append("    def forward(self, s0, s1):")
    code.append("        s0 = self.preprocess0(s0)")
    code.append("        s1 = self.preprocess1(s1)")
    code.append("        states = [s0, s1]")
    code.append("")
    
    for to_node in sorted(node_edges.keys()):
        edges = node_edges[to_node]
        inputs = []
        for i, edge in enumerate(edges):
            from_node = edge['from']
            inputs.append(f"self.op_{to_node}_{i}(states[{from_node}])")
        
        if len(inputs) == 1:
            code.append(f"        node_{to_node} = {inputs[0]}")
        else:
            code.append(f"        node_{to_node} = {' + '.join(inputs)}")
        
        code.append(f"        states.append(node_{to_node})")
        code.append("")
    
    # 拼接所有中间节点
    concat_nodes = ", ".join([f"states[{i}]" for i in range(2, num_nodes + 2)])
    code.append(f"        return torch.cat([{concat_nodes}], dim=1)")
    code.append("")
    
    return "\n".join(code)


def generate_network_code(architecture, num_classes=10, num_cells=20, init_channels=36, 
                          auxiliary=True, auxiliary_weight=0.4):
    """生成完整的网络模型代码"""
    normal_gene = architecture['normal']
    reduce_gene = architecture['reduce']
    num_nodes = architecture['num_nodes']
    
    code = []
    code.append(OP_IMPORTS)
    code.append("")
    
    # 生成Normal Cell
    code.append(generate_cell_code(normal_gene, "NormalCell", num_nodes, is_reduction=False))
    code.append("")
    
    # 生成Reduction Cell
    code.append(generate_cell_code(reduce_gene, "ReductionCell", num_nodes, is_reduction=True))
    code.append("")
    
    # 生成主网络类
    code.append(f"class SearchedNetwork(nn.Module):")
    code.append('    """搜索到的最优网络架构"""')
    code.append(f"    def __init__(self, C={init_channels}, num_classes={num_classes}, "
                f"layers={num_cells}, auxiliary={auxiliary}, drop_path_prob=0.0):")
    code.append(f"        super().__init__()")
    code.append(f"        self._auxiliary = auxiliary")
    code.append(f"        self._layers = layers")
    code.append(f"        self.drop_path_prob = drop_path_prob")
    code.append("")
    code.append("        # Stem层")
    code.append(f"        self.stem = nn.Sequential(")
    code.append(f"            nn.Conv2d(3, C * 3, 3, stride=1, padding=1, bias=False),")
    code.append(f"            nn.BatchNorm2d(C * 3)")
    code.append(f"        )")
    code.append("")
    code.append("        # Cells")
    code.append("        self.cells = nn.ModuleList()")
    code.append("        C_prev_prev, C_prev, C_curr = C * 3, C * 3, C")
    code.append("        reduction_prev = False")
    code.append(f"        self.auxiliary_cell_idx = 2 * layers // 3  # 辅助分类器位置")
    code.append("")
    
    code.append("        for i in range(layers):")
    code.append(f"            if i in [layers // 3, 2 * layers // 3]:")
    code.append("                C_curr *= 2")
    code.append("                reduction = True")
    code.append("                cell = ReductionCell(C_prev_prev, C_prev, C_curr, reduction_prev, drop_path_prob)")
    code.append("            else:")
    code.append("                reduction = False")
    code.append("                cell = NormalCell(C_prev_prev, C_prev, C_curr, reduction_prev, drop_path_prob)")
    code.append("")
    code.append("            self.cells.append(cell)")
    code.append(f"            C_prev_prev = C_prev")
    code.append(f"            C_prev = C_curr * {num_nodes}  # {num_nodes}个节点拼接")
    code.append("            reduction_prev = reduction")
    code.append("")
    code.append("            # 辅助分类器")
    code.append("            if auxiliary and i == self.auxiliary_cell_idx:")
    code.append("                C_to_aux = C_prev")
    code.append("                self.auxiliary_head = nn.Sequential(")
    code.append("                    nn.ReLU(inplace=False),")
    code.append("                    nn.AdaptiveAvgPool2d(1),")
    code.append("                    nn.Conv2d(C_to_aux, 128, 1, bias=False),")
    code.append("                    nn.BatchNorm2d(128),")
    code.append("                    nn.ReLU(inplace=True),")
    code.append("                    nn.Conv2d(128, 768, 1, bias=False),")
    code.append("                    nn.BatchNorm2d(768),")
    code.append("                    nn.ReLU(inplace=True),")
    code.append("                    nn.Flatten(),")
    code.append(f"                    nn.Linear(768, {num_classes})")
    code.append("                )")
    code.append("")
    
    code.append("        # 最终分类器")
    code.append("        self.global_pooling = nn.AdaptiveAvgPool2d(1)")
    code.append(f"        self.classifier = nn.Linear(C_prev, {num_classes})")
    code.append("")
    code.append("    def forward(self, x):")
    code.append("        s0 = s1 = self.stem(x)")
    code.append("        aux_logits = None")
    code.append("")
    code.append("        for i, cell in enumerate(self.cells):")
    code.append("            s0, s1 = s1, cell(s0, s1)")
    code.append("            if self._auxiliary and i == self.auxiliary_cell_idx and self.training:")
    code.append("                aux_logits = self.auxiliary_head(s1)")
    code.append("")
    code.append("        out = self.global_pooling(s1)")
    code.append("        out = out.view(out.size(0), -1)")
    code.append("        logits = self.classifier(out)")
    code.append("")
    code.append("        if self._auxiliary and self.training:")
    code.append("            return logits, aux_logits")
    code.append("        return logits")
    code.append("")
    
    return "\n".join(code)


def save_model_code(architecture, filepath, num_classes=10, num_cells=20, 
                    init_channels=36, auxiliary=True, auxiliary_weight=0.4):
    """保存生成的模型代码到文件"""
    code = generate_network_code(
        architecture, num_classes, num_cells, init_channels, auxiliary, auxiliary_weight
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"模型代码已生成并保存到: {filepath}")
    return code


def save_full_search_model(model, architecture, save_dir, prefix='best'):
    """
    保存搜索模型的完整状态，包括：
    - 模型代码
    - 架构定义
    - 完整模型状态（含BatchNorm参数）
    - 架构权重
    
    Args:
        model: 训练好的搜索模型
        architecture: 导出的架构字典
        save_dir: 保存目录
        prefix: 文件名前缀
    """
    import os
    import torch
    import torch.nn as nn
    os.makedirs(save_dir, exist_ok=True)
    
    # 1. 保存模型代码
    model_code_path = os.path.join(save_dir, f'{prefix}_model.py')
    save_model_code(
        architecture, model_code_path,
        num_classes=10, num_cells=20, init_channels=36, auxiliary=True
    )
    
    # 2. 保存架构定义
    arch_path = os.path.join(save_dir, f'{prefix}_architecture.json')
    from darts_nas.models.architecture import save_architecture
    save_architecture(architecture, arch_path)
    
    # 3. 保存完整模型状态
    model_state_path = os.path.join(save_dir, f'{prefix}_full_state.pt')
    
    state_dict = model.state_dict()
    
    # 收集BatchNorm信息
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
        'alphas_normal': model.alphas_normal.detach().cpu(),
        'alphas_reduce': model.alphas_reduce.detach().cpu(),
        'architecture': architecture,
    }
    
    torch.save(save_data, model_state_path)
    print(f"完整模型状态已保存到: {model_state_path}")
    print(f"BatchNorm层数: {len(bn_info)}")
    
    return {
        'model_code': model_code_path,
        'architecture': arch_path,
        'model_state': model_state_path,
    }
