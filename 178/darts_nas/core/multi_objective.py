"""
多目标优化模块 - 支持延迟、参数量、FLOPs同时优化
包含Pareto排序和多目标损失函数
"""

import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple, Dict


class FLOPsCounter:
    """
    FLOPs计算器 - 统计模型的浮点运算次数
    """
    def __init__(self, model, input_size=(1, 3, 32, 32)):
        self.model = model
        self.input_size = input_size
        self.flops = 0
        self.params = 0
        self._hooks = []
    
    def _conv_hook(self, module, input, output):
        """卷积层FLOPs计算"""
        in_channels = module.in_channels
        out_channels = module.out_channels
        kernel_size = module.kernel_size[0] if isinstance(module.kernel_size, tuple) else module.kernel_size
        output_size = output.shape[2] if len(output.shape) > 2 else 1
        
        groups = module.groups
        # FLOPs = 2 * batch * out_channels * out_h * out_w * in_channels * kernel^2 / groups
        flops = 2 * output.numel() * in_channels * kernel_size * kernel_size / groups
        self.flops += flops
        
        # 参数统计
        params = in_channels * out_channels * kernel_size * kernel_size / groups
        if module.bias is not None:
            params += out_channels
        self.params += params
    
    def _linear_hook(self, module, input, output):
        """全连接层FLOPs计算"""
        in_features = module.in_features
        out_features = module.out_features
        
        flops = 2 * input[0].shape[0] * in_features * out_features
        self.flops += flops
        
        params = in_features * out_features
        if module.bias is not None:
            params += out_features
        self.params += params
    
    def _bn_hook(self, module, input, output):
        """BatchNorm层FLOPs计算"""
        flops = 2 * input[0].numel()  # 均值和方差计算
        self.flops += flops
        
        if module.affine:
            self.params += 2 * module.num_features  # gamma和beta
    
    def _pool_hook(self, module, input, output):
        """池化层FLOPs计算"""
        flops = input[0].numel()  # 比较操作
        self.flops += flops
    
    def count(self):
        """统计FLOPs和参数量"""
        self.flops = 0
        self.params = 0
        
        # 注册钩子
        for module in self.model.modules():
            if isinstance(module, nn.Conv2d):
                self._hooks.append(module.register_forward_hook(self._conv_hook))
            elif isinstance(module, nn.Linear):
                self._hooks.append(module.register_forward_hook(self._linear_hook))
            elif isinstance(module, nn.BatchNorm2d):
                self._hooks.append(module.register_forward_hook(self._bn_hook))
            elif isinstance(module, (nn.MaxPool2d, nn.AvgPool2d, nn.AdaptiveAvgPool2d)):
                self._hooks.append(module.register_forward_hook(self._pool_hook))
        
        # 前向传播触发钩子
        device = next(self.model.parameters()).device
        dummy_input = torch.randn(*self.input_size).to(device)
        self.model.eval()
        with torch.no_grad():
            self.model(dummy_input)
        
        # 移除钩子
        for hook in self._hooks:
            hook.remove()
        self._hooks = []
        
        return self.flops, self.params


def count_flops_and_params(model, input_size=(1, 3, 32, 32)):
    """
    便捷函数：统计模型的FLOPs和参数量
    
    Args:
        model: PyTorch模型
        input_size: 输入张量尺寸 (batch, channels, height, width)
    
    Returns:
        flops: 浮点运算次数 (GFLOPs)
        params: 参数量 (M)
    """
    counter = FLOPsCounter(model, input_size)
    flops, params = counter.count()
    
    flops_gflops = flops / 1e9  # 转换为GFLOPs
    params_m = params / 1e6  # 转换为百万
    
    return flops_gflops, params_m


def estimate_latency(model, input_size=(1, 3, 32, 32), num_runs=100, device=None):
    """
    估计模型的推理延迟
    
    Args:
        model: PyTorch模型
        input_size: 输入张量尺寸
        num_runs: 运行次数取平均
        device: 计算设备
    
    Returns:
        latency_ms: 平均延迟 (毫秒)
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = model.to(device)
    model.eval()
    
    dummy_input = torch.randn(*input_size).to(device)
    
    # 预热
    with torch.no_grad():
        for _ in range(10):
            _ = model(dummy_input)
    
    # 计时
    if device.type == 'cuda':
        torch.cuda.synchronize()
    
    start_time = torch.cuda.Event(enable_timing=True) if device.type == 'cuda' else None
    end_time = torch.cuda.Event(enable_timing=True) if device.type == 'cuda' else None
    
    total_time = 0
    with torch.no_grad():
        for i in range(num_runs):
            if device.type == 'cuda':
                start_time.record()
                _ = model(dummy_input)
                end_time.record()
                torch.cuda.synchronize()
                total_time += start_time.elapsed_time(end_time)
            else:
                import time
                start = time.time()
                _ = model(dummy_input)
                total_time += (time.time() - start) * 1000
    
    avg_latency = total_time / num_runs
    return avg_latency


def compute_objectives(model, input_size=(1, 3, 32, 32), device=None):
    """
    计算所有目标指标
    
    Args:
        model: PyTorch模型
        input_size: 输入尺寸
        device: 计算设备
    
    Returns:
        dict: 包含各项目标的字典
    """
    flops, params = count_flops_and_params(model, input_size)
    latency = estimate_latency(model, input_size, device=device)
    
    return {
        'flops_gflops': flops,
        'params_million': params,
        'latency_ms': latency,
    }


class ParetoOptimizer:
    """
    Pareto多目标优化器
    支持最小化多个目标（如延迟、参数量、FLOPs）并最大化准确率
    """
    
    def __init__(self, objectives_config: Dict[str, dict]):
        """
        Args:
            objectives_config: 目标配置字典
                例如: {
                    'accuracy': {'weight': 1.0, 'maximize': True},
                    'flops_gflops': {'weight': 0.5, 'maximize': False},
                    'params_million': {'weight': 0.3, 'maximize': False},
                    'latency_ms': {'weight': 0.4, 'maximize': False},
                }
        """
        self.objectives_config = objectives_config
    
    def pareto_rank(self, solutions: List[Dict[str, float]]) -> np.ndarray:
        """
        计算Pareto排序（非支配排序）
        
        Args:
            solutions: 解列表，每个解是目标值字典
        
        Returns:
            ranks: 每个解的Pareto rank (0表示最优前沿)
        """
        n = len(solutions)
        ranks = np.zeros(n, dtype=int)
        dominated = [set() for _ in range(n)]
        domination_count = np.zeros(n, dtype=int)
        
        # 计算支配关系
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                
                if self._dominates(solutions[i], solutions[j]):
                    dominated[i].add(j)
                    domination_count[j] += 1
        
        # 非支配排序
        current_rank = 0
        remaining = set(range(n))
        
        while remaining:
            # 找到当前非支配集
            current_front = [i for i in remaining if domination_count[i] == 0]
            
            if not current_front:
                break
            
            for i in current_front:
                ranks[i] = current_rank
                remaining.remove(i)
                
                for j in dominated[i]:
                    domination_count[j] -= 1
            
            current_rank += 1
        
        return ranks
    
    def _dominates(self, sol_a: Dict[str, float], sol_b: Dict[str, float]) -> bool:
        """判断解a是否支配解b"""
        at_least_as_good = True
        strictly_better = False
        
        for obj_name, config in self.objectives_config.items():
            val_a = sol_a[obj_name]
            val_b = sol_b[obj_name]
            
            if config['maximize']:
                if val_a < val_b:
                    at_least_as_good = False
                    break
                elif val_a > val_b:
                    strictly_better = True
            else:
                if val_a > val_b:
                    at_least_as_good = False
                    break
                elif val_a < val_b:
                    strictly_better = True
        
        return at_least_as_good and strictly_better
    
    def compute_scalarized_score(self, objectives: Dict[str, float]) -> float:
        """
        计算标量化得分（线性加权）
        
        Args:
            objectives: 目标值字典
        
        Returns:
            综合得分（越大越好）
        """
        score = 0.0
        for obj_name, config in self.objectives_config.items():
            val = objectives[obj_name]
            weight = config['weight']
            
            if config['maximize']:
                score += val * weight
            else:
                score -= val * weight
        
        return score
    
    def select_best_solution(self, solutions: List[Dict[str, float]], 
                             use_pareto: bool = True) -> int:
        """
        选择最优解
        
        Args:
            solutions: 解列表
            use_pareto: 是否使用Pareto排序，否则使用线性加权
        
        Returns:
            最优解的索引
        """
        if use_pareto and len(solutions) > 1:
            ranks = self.pareto_rank(solutions)
            
            # 从Pareto前沿中选择得分最高的
            front_indices = [i for i, r in enumerate(ranks) if r == 0]
            
            if len(front_indices) == 1:
                return front_indices[0]
            
            # 在Pareto前沿中使用线性加权选择
            front_scores = [self.compute_scalarized_score(solutions[i]) for i in front_indices]
            best_front_idx = np.argmax(front_scores)
            return front_indices[best_front_idx]
        else:
            # 直接使用线性加权
            scores = [self.compute_scalarized_score(sol) for sol in solutions]
            return np.argmax(scores)


class MultiObjectiveLoss:
    """
    多目标损失函数
    结合分类损失和效率目标的正则化项
    """
    
    def __init__(self, config: Dict[str, dict], device: torch.device):
        """
        Args:
            config: 目标配置字典
            device: 计算设备
        """
        self.config = config
        self.device = device
        self.classification_criterion = nn.CrossEntropyLoss().to(device)
        
        # 目标值的归一化因子（运行时估计）
        self.normalization_factors = {}
    
    def update_normalization(self, objectives: Dict[str, float]):
        """更新归一化因子"""
        for obj_name in self.config.keys():
            if obj_name == 'accuracy':
                continue
            if obj_name in objectives:
                self.normalization_factors[obj_name] = max(1e-6, objectives[obj_name])
    
    def compute_loss(self, logits: torch.Tensor, targets: torch.Tensor,
                     objectives: Dict[str, float]) -> torch.Tensor:
        """
        计算多目标损失
        
        Args:
            logits: 模型输出logits
            targets: 目标标签
            objectives: 当前模型的目标指标
        
        Returns:
            综合损失
        """
        # 分类损失
        cls_loss = self.classification_criterion(logits, targets)
        
        # 效率目标正则化
        efficiency_loss = 0.0
        for obj_name, obj_config in self.config.items():
            if obj_name == 'accuracy':
                continue
            
            if obj_name in objectives and obj_config['weight'] > 0:
                norm_factor = self.normalization_factors.get(obj_name, 1.0)
                normalized_val = objectives[obj_name] / norm_factor
                
                if obj_config['maximize']:
                    # 最大化目标，损失为负
                    efficiency_loss -= normalized_val * obj_config['weight']
                else:
                    # 最小化目标，损失为正
                    efficiency_loss += normalized_val * obj_config['weight']
        
        total_loss = cls_loss + efficiency_loss
        return total_loss


def get_default_objectives_config():
    """获取默认的多目标配置"""
    return {
        'accuracy': {'weight': 1.0, 'maximize': True},
        'flops_gflops': {'weight': 0.3, 'maximize': False},
        'params_million': {'weight': 0.2, 'maximize': False},
        'latency_ms': {'weight': 0.25, 'maximize': False},
    }
