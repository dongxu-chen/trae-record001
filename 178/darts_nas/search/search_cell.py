"""
搜索阶段的Cell - 包含可学习的架构参数
"""

import torch
import torch.nn as nn
from darts_nas.core.ops import MixedOp, FactorizedReduce, DropPath


class SearchCell(nn.Module):
    """
    可搜索的Cell - 用于架构搜索阶段
    每个cell包含多个节点，节点之间的连接通过混合操作实现
    """
    def __init__(self, C_prev_prev, C_prev, C, reduction, reduction_prev, num_nodes=4, drop_path_prob=0.0):
        """
        Args:
            C_prev_prev: 前前层的通道数
            C_prev: 前层的通道数
            C: 当前cell的通道数
            reduction: 是否为降维cell (空间尺寸减半)
            reduction_prev: 前一个cell是否为降维cell
            num_nodes: cell中的节点数
            drop_path_prob: DropPath概率，用于强制探索多样化架构
        """
        super().__init__()
        self.num_nodes = num_nodes
        self.reduction = reduction
        self.drop_path_prob = drop_path_prob
        self._drop_path = DropPath(drop_path_prob) if drop_path_prob > 0 else None
        
        # 预处理输入
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
        
        # 创建混合操作
        self._ops = nn.ModuleList()
        self._edges = []
        
        for i in range(self.num_nodes):
            for j in range(i + 2):
                stride = 2 if reduction and j < 2 else 1
                op = MixedOp(C, stride)
                self._ops.append(op)
                self._edges.append((j, i + 2))  # (输入节点, 输出节点)
    
    def forward(self, s0, s1, arch_weights, temperature=1.0):
        """
        Args:
            s0: 前前层特征
            s1: 前层特征
            arch_weights: 架构权重字典 {'normal': [num_edges, num_ops], 'reduce': [num_edges, num_ops]}
            temperature: softmax温度系数
        Returns:
            输出特征
        """
        weights = arch_weights['reduce'] if self.reduction else arch_weights['normal']
        
        s0 = self.preprocess0(s0)
        s1 = self.preprocess1(s1)
        
        states = [s0, s1]
        offset = 0
        
        for i in range(self.num_nodes):
            node_inputs = []
            for j in range(i + 2):
                edge_idx = offset + j
                op = self._ops[edge_idx]
                w = weights[edge_idx]
                out = op(states[j], w, temperature)
                # 应用DropPath正则化，强制探索多样化架构
                if self._drop_path is not None and self.training:
                    out = self._drop_path(out)
                node_inputs.append(out)
            
            node_output = sum(node_inputs)
            states.append(node_output)
            offset += i + 2
        
        # 连接所有中间节点到输出
        return torch.cat(states[2:], dim=1)
    
    @property
    def num_edges(self):
        """返回cell中的边数"""
        return len(self._ops)
    
    @property
    def edges(self):
        """返回所有边的连接关系"""
        return self._edges


class SearchNetwork(nn.Module):
    """
    可微搜索网络 - 包含多个搜索cell
    """
    def __init__(self, C, num_classes, num_cells, num_nodes=4, drop_path_prob=0.0, criterion=nn.CrossEntropyLoss()):
        """
        Args:
            C: 初始通道数
            num_classes: 分类类别数
            num_cells: cell数量
            num_nodes: 每个cell的节点数
            drop_path_prob: DropPath概率，用于强制探索多样化架构
            criterion: 损失函数
        """
        super().__init__()
        self._C = C
        self._num_classes = num_classes
        self._num_cells = num_cells
        self._num_nodes = num_nodes
        self._drop_path_prob = drop_path_prob
        self._criterion = criterion
        
        # 初始stem层
        self.stem = nn.Sequential(
            nn.Conv2d(3, C * 3, 3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(C * 3)
        )
        
        # 创建cells
        self.cells = nn.ModuleList()
        C_prev_prev, C_prev, C_curr = C * 3, C * 3, C
        reduction_prev = False
        
        for i in range(num_cells):
            if i in [num_cells // 3, 2 * num_cells // 3]:
                C_curr *= 2
                reduction = True
            else:
                reduction = False
            
            cell = SearchCell(
                C_prev_prev, C_prev, C_curr, reduction, reduction_prev, num_nodes, drop_path_prob
            )
            self.cells.append(cell)
            
            C_prev_prev = C_prev
            C_prev = C_curr * num_nodes  # 每个cell输出是num_nodes个节点的拼接
            reduction_prev = reduction
        
        # 最终分类层
        self.global_pooling = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Linear(C_prev, num_classes)
        
        # 初始化架构参数
        self._initialize_alphas()
    
    def _initialize_alphas(self):
        """初始化架构参数 (alpha)"""
        num_ops = len(self.cells[0]._ops[0]._ops)
        num_edges = self.cells[0].num_edges
        
        # 普通cell和降维cell各有一套架构参数
        self.alphas_normal = nn.Parameter(
            1e-3 * torch.randn(num_edges, num_ops)
        )
        self.alphas_reduce = nn.Parameter(
            1e-3 * torch.randn(num_edges, num_ops)
        )
        
        self._arch_parameters = [
            self.alphas_normal,
            self.alphas_reduce,
        ]
    
    def arch_parameters(self):
        """返回架构参数列表"""
        return self._arch_parameters
    
    def weight_parameters(self):
        """返回网络权重参数列表 (不包含架构参数)"""
        for name, param in self.named_parameters():
            if 'alphas' not in name:
                yield param
    
    def forward(self, x, temperature=1.0):
        """前向传播"""
        arch_weights = {
            'normal': self.alphas_normal,
            'reduce': self.alphas_reduce,
        }
        
        s0 = s1 = self.stem(x)
        
        for cell in self.cells:
            s0, s1 = s1, cell(s0, s1, arch_weights, temperature)
        
        out = self.global_pooling(s1)
        out = out.view(out.size(0), -1)
        logits = self.classifier(out)
        
        return logits
    
    def loss(self, x, target, temperature=1.0):
        """计算损失"""
        logits = self(x, temperature)
        return self._criterion(logits, target)
    
    def get_architecture(self, temperature=1.0):
        """获取当前架构权重 (softmax后)"""
        return {
            'normal': torch.softmax(self.alphas_normal / temperature, dim=-1).detach().cpu(),
            'reduce': torch.softmax(self.alphas_reduce / temperature, dim=-1).detach().cpu(),
        }
