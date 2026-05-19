"""
权重继承策略模块
当架构变化时，从已训练的权重中初始化新架构的权重，加速收敛
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from copy import deepcopy


class WeightInheritor:
    """
    权重继承器 - 实现从已训练模型到新架构的权重迁移
    """
    
    def __init__(self, source_model: nn.Module, match_threshold: float = 0.5):
        """
        Args:
            source_model: 已训练的源模型（提供权重）
            match_threshold: 操作匹配阈值，低于此值不继承
        """
        self.source_model = source_model
        self.match_threshold = match_threshold
        self.source_state_dict = source_model.state_dict()
        self.source_named_modules = dict(source_model.named_modules())
    
    def inherit_weights(self, target_model: nn.Module, architecture: Optional[Dict] = None) -> nn.Module:
        """
        将源模型的权重继承到目标模型
        
        Args:
            target_model: 目标模型（需要初始化权重）
            architecture: 可选的架构信息，用于更精确的匹配
        
        Returns:
            继承了权重的目标模型
        """
        target_state_dict = target_model.state_dict()
        source_keys = set(self.source_state_dict.keys())
        target_keys = set(target_state_dict.keys())
        
        inherited_count = 0
        total_count = len(target_keys)
        
        # 策略1: 完全匹配的键直接复制
        common_keys = source_keys & target_keys
        for key in common_keys:
            source_tensor = self.source_state_dict[key]
            target_tensor = target_state_dict[key]
            
            if source_tensor.shape == target_tensor.shape:
                target_state_dict[key] = source_tensor.clone()
                inherited_count += 1
        
        # 策略2: 按模块类型进行智能匹配
        target_named_modules = dict(target_model.named_modules())
        
        for target_name, target_module in target_named_modules.items():
            # 跳过没有参数的模块
            if not list(target_module.parameters()):
                continue
            
            # 查找最佳匹配的源模块
            best_source_name, best_score = self._find_best_match(
                target_name, target_module, self.source_named_modules
            )
            
            if best_source_name and best_score >= self.match_threshold:
                source_module = self.source_named_modules[best_source_name]
                if self._inherit_module_weights(source_module, target_module):
                    inherited_count += sum(1 for _ in target_module.parameters())
        
        # 加载继承后的权重
        target_model.load_state_dict(target_state_dict)
        
        print(f"权重继承完成: {inherited_count}/{total_count} 参数被继承")
        return target_model
    
    def _find_best_match(self, target_name: str, target_module: nn.Module, 
                        source_modules: Dict[str, nn.Module]) -> Tuple[Optional[str], float]:
        """
        为目标模块找到最佳匹配的源模块
        
        Args:
            target_name: 目标模块名称
            target_module: 目标模块
            source_modules: 源模块字典
        
        Returns:
            (最佳匹配的源模块名称, 匹配分数)
        """
        best_match = None
        best_score = 0.0
        
        target_type = type(target_module).__name__
        
        for source_name, source_module in source_modules.items():
            # 类型必须匹配
            if type(source_module).__name__ != target_type:
                continue
            
            # 计算名称相似度
            name_score = self._name_similarity(target_name, source_name)
            
            # 计算结构相似度
            struct_score = self._structure_similarity(source_module, target_module)
            
            # 综合分数
            total_score = 0.4 * name_score + 0.6 * struct_score
            
            if total_score > best_score:
                best_score = total_score
                best_match = source_name
        
        return best_match, best_score
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """计算两个名称的相似度（基于共同子串）"""
        # 提取数字和关键字
        def extract_tokens(name):
            tokens = []
            current = ''
            for char in name:
                if char.isdigit() or char == '_':
                    if current:
                        tokens.append(current)
                        current = ''
                    tokens.append(char)
                else:
                    current += char
            if current:
                tokens.append(current)
            return tokens
        
        tokens1 = extract_tokens(name1)
        tokens2 = extract_tokens(name2)
        
        # 计算Jaccard相似度
        set1, set2 = set(tokens1), set(tokens2)
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _structure_similarity(self, module1: nn.Module, module2: nn.Module) -> float:
        """计算两个模块的结构相似度"""
        # 比较参数形状
        params1 = list(module1.parameters())
        params2 = list(module2.parameters())
        
        if not params1 or not params2:
            return 0.0
        
        # 计算形状匹配度
        shape_score = 0.0
        for p1, p2 in zip(params1, params2):
            if p1.shape == p2.shape:
                shape_score += 1.0
            else:
                # 部分匹配（如通道数接近）
                if len(p1.shape) == len(p2.shape):
                    dim_match = sum(1 for d1, d2 in zip(p1.shape, p2.shape) if d1 == d2)
                    shape_score += dim_match / len(p1.shape)
        
        return shape_score / max(len(params1), len(params2))
    
    def _inherit_module_weights(self, source_module: nn.Module, target_module: nn.Module) -> bool:
        """
        将源模块的权重继承到目标模块
        
        Args:
            source_module: 源模块
            target_module: 目标模块
        
        Returns:
            是否成功继承
        """
        # 处理不同类型的模块
        if isinstance(source_module, nn.Conv2d) and isinstance(target_module, nn.Conv2d):
            return self._inherit_conv_weights(source_module, target_module)
        
        elif isinstance(source_module, nn.Linear) and isinstance(target_module, nn.Linear):
            return self._inherit_linear_weights(source_module, target_module)
        
        elif isinstance(source_module, nn.BatchNorm2d) and isinstance(target_module, nn.BatchNorm2d):
            return self._inherit_bn_weights(source_module, target_module)
        
        elif isinstance(source_module, nn.Sequential) and isinstance(target_module, nn.Sequential):
            return self._inherit_sequential_weights(source_module, target_module)
        
        return False
    
    def _inherit_conv_weights(self, source_conv: nn.Conv2d, target_conv: nn.Conv2d) -> bool:
        """
        继承卷积层权重，支持不同卷积核大小和通道数
        
        策略:
        - 卷积核: 中心对齐复制，超出部分随机初始化
        - 通道: 按最小通道数复制，剩余部分随机初始化
        """
        source_weight = source_conv.weight.data
        target_weight = target_conv.weight.data
        
        # 获取维度信息
        s_out, s_in, s_kh, s_kw = source_weight.shape
        t_out, t_in, t_kh, t_kw = target_weight.shape
        
        # 计算中心偏移
        kh_offset = (s_kh - t_kh) // 2 if s_kh > t_kh else (t_kh - s_kh) // 2
        kw_offset = (s_kw - t_kw) // 2 if s_kw > t_kw else (t_kw - s_kw) // 2
        
        # 确定复制范围
        min_out = min(s_out, t_out)
        min_in = min(s_in, t_in)
        min_kh = min(s_kh, t_kh)
        min_kw = min(s_kw, t_kw)
        
        # 复制权重（中心对齐）
        if s_kh >= t_kh and s_kw >= t_kw:
            # 源卷积核更大，取中心部分
            target_weight[:min_out, :min_in, :, :] = source_weight[
                :min_out, :min_in, 
                kh_offset:kh_offset + t_kh, 
                kw_offset:kw_offset + t_kw
            ]
        else:
            # 目标卷积核更大，填充中心
            target_weight[:min_out, :min_in, 
                         kh_offset:kh_offset + s_kh, 
                         kw_offset:kw_offset + s_kw] = source_weight[:min_out, :min_in, :, :]
        
        # 继承偏置（如果存在）
        if source_conv.bias is not None and target_conv.bias is not None:
            min_bias = min(source_conv.bias.shape[0], target_conv.bias.shape[0])
            target_conv.bias.data[:min_bias] = source_conv.bias.data[:min_bias]
        
        return True
    
    def _inherit_linear_weights(self, source_linear: nn.Linear, target_linear: nn.Linear) -> bool:
        """继承全连接层权重"""
        source_weight = source_linear.weight.data
        target_weight = target_linear.weight.data
        
        s_out, s_in = source_weight.shape
        t_out, t_in = target_weight.shape
        
        min_out = min(s_out, t_out)
        min_in = min(s_in, t_in)
        
        target_weight[:min_out, :min_in] = source_weight[:min_out, :min_in]
        
        if source_linear.bias is not None and target_linear.bias is not None:
            min_bias = min(source_linear.bias.shape[0], target_linear.bias.shape[0])
            target_linear.bias.data[:min_bias] = source_linear.bias.data[:min_bias]
        
        return True
    
    def _inherit_bn_weights(self, source_bn: nn.BatchNorm2d, target_bn: nn.BatchNorm2d) -> bool:
        """继承BatchNorm层的权重和running stats"""
        min_feat = min(source_bn.num_features, target_bn.num_features)
        
        if source_bn.weight is not None and target_bn.weight is not None:
            target_bn.weight.data[:min_feat] = source_bn.weight.data[:min_feat]
        
        if source_bn.bias is not None and target_bn.bias is not None:
            target_bn.bias.data[:min_feat] = source_bn.bias.data[:min_feat]
        
        if source_bn.running_mean is not None and target_bn.running_mean is not None:
            target_bn.running_mean.data[:min_feat] = source_bn.running_mean.data[:min_feat]
        
        if source_bn.running_var is not None and target_bn.running_var is not None:
            target_bn.running_var.data[:min_feat] = source_bn.running_var.data[:min_feat]
        
        return True
    
    def _inherit_sequential_weights(self, source_seq: nn.Sequential, 
                                   target_seq: nn.Sequential) -> bool:
        """继承Sequential容器中的子模块权重"""
        success_count = 0
        min_len = min(len(source_seq), len(target_seq))
        
        for i in range(min_len):
            if self._inherit_module_weights(source_seq[i], target_seq[i]):
                success_count += 1
        
        return success_count > 0


class WeightInheritanceManager:
    """
    权重继承管理器 - 在搜索过程中管理权重继承
    定期保存检查点，当架构显著变化时触发权重继承
    """
    
    def __init__(self, save_dir: str = './checkpoints/weight_inheritance',
                 inheritance_interval: int = 5,
                 architecture_change_threshold: float = 0.3):
        """
        Args:
            save_dir: 检查点保存目录
            inheritance_interval: 继承间隔（epoch数）
            architecture_change_threshold: 架构变化阈值，超过则触发继承
        """
        self.save_dir = save_dir
        self.inheritance_interval = inheritance_interval
        self.architecture_change_threshold = architecture_change_threshold
        
        self.checkpoint_history = []
        self.last_architecture = None
        self.best_model_state = None
        
        import os
        os.makedirs(save_dir, exist_ok=True)
    
    def save_checkpoint(self, model: nn.Module, architecture: Dict, epoch: int, 
                       accuracy: float, objectives: Dict):
        """
        保存模型检查点用于后续继承
        
        Args:
            model: 当前模型
            architecture: 当前架构
            epoch: 当前epoch
            accuracy: 验证准确率
            objectives: 其他目标指标
        """
        checkpoint_path = f"{self.save_dir}/checkpoint_epoch{epoch}.pt"
        
        checkpoint_data = {
            'epoch': epoch,
            'model_state_dict': deepcopy(model.state_dict()),
            'architecture': deepcopy(architecture),
            'accuracy': accuracy,
            'objectives': deepcopy(objectives),
        }
        
        torch.save(checkpoint_data, checkpoint_path)
        
        # 保留历史记录（最多保留最近10个）
        self.checkpoint_history.append({
            'path': checkpoint_path,
            'epoch': epoch,
            'accuracy': accuracy,
            'objectives': objectives,
        })
        
        if len(self.checkpoint_history) > 10:
            oldest = self.checkpoint_history.pop(0)
            import os
            if os.path.exists(oldest['path']):
                os.remove(oldest['path'])
        
        # 保存最佳模型
        if self.best_model_state is None or accuracy > self.best_model_state['accuracy']:
            self.best_model_state = checkpoint_data
            torch.save(checkpoint_data, f"{self.save_dir}/best_checkpoint.pt")
        
        self.last_architecture = deepcopy(architecture)
    
    def should_inherit(self, current_architecture: Dict, epoch: int) -> bool:
        """
        判断是否应该触发权重继承
        
        Args:
            current_architecture: 当前架构
            epoch: 当前epoch
        
        Returns:
            是否触发继承
        """
        # 定期继承
        if epoch % self.inheritance_interval == 0 and epoch > 0:
            return True
        
        # 架构显著变化时继承
        if self.last_architecture is not None:
            change_score = self._compute_architecture_change(
                self.last_architecture, current_architecture
            )
            if change_score > self.architecture_change_threshold:
                return True
        
        return False
    
    def _compute_architecture_change(self, arch1: Dict, arch2: Dict) -> float:
        """计算两个架构之间的变化程度"""
        if 'normal' not in arch1 or 'normal' not in arch2:
            return 1.0
        
        changes = 0
        total = 0
        
        for cell_type in ['normal', 'reduce']:
            edges1 = arch1.get(cell_type, [])
            edges2 = arch2.get(cell_type, [])
            
            for e1, e2 in zip(edges1, edges2):
                total += 1
                if e1['op'] != e2['op']:
                    changes += 1
        
        return changes / total if total > 0 else 0.0
    
    def inherit_from_best(self, target_model: nn.Module) -> nn.Module:
        """
        从最佳检查点继承权重
        
        Args:
            target_model: 目标模型
        
        Returns:
            继承权重后的模型
        """
        if self.best_model_state is None:
            print("没有可用的最佳检查点，跳过权重继承")
            return target_model
        
        # 创建临时源模型
        source_model = deepcopy(target_model)
        source_model.load_state_dict(self.best_model_state['model_state_dict'])
        
        # 执行权重继承
        inheritor = WeightInheritor(source_model)
        return inheritor.inherit_weights(target_model, self.best_model_state.get('architecture'))
