"""
架构导出器 - 从搜索到的架构参数中导出离散网络结构
"""

import torch
import json
import numpy as np
from darts_nas.core.ops import get_search_primitives


def derive_architecture(alphas_normal, alphas_reduce, num_nodes=4, skip_threshold=0.1):
    """
    从架构参数中推导出离散架构
    Args:
        alphas_normal: 普通cell的架构参数 [num_edges, num_ops]
        alphas_reduce: 降维cell的架构参数 [num_edges, num_ops]
        num_nodes: 每个cell的节点数
        skip_threshold: 跳层连接的权重阈值
    Returns:
        架构字典，包含normal和reduce cell的结构
    """
    op_names = [name for name, _ in get_search_primitives(1, 1)]
    
    def _derive_cell(alphas):
        """推导单个cell的结构"""
        gene = []
        offset = 0
        
        for i in range(num_nodes):
            node_edges = []
            for j in range(i + 2):
                edge_idx = offset + j
                weights = torch.softmax(alphas[edge_idx], dim=-1)
                
                # 选择权重最大的操作
                best_op_idx = torch.argmax(weights).item()
                best_op_name = op_names[best_op_idx]
                best_weight = weights[best_op_idx].item()
                
                node_edges.append({
                    'from': j,
                    'to': i + 2,
                    'op': best_op_name,
                    'weight': best_weight
                })
            
            # 对每个节点，保留权重最高的两个输入边
            node_edges.sort(key=lambda x: x['weight'], reverse=True)
            selected_edges = node_edges[:2]
            
            for edge in selected_edges:
                gene.append(edge)
            
            offset += i + 2
        
        return gene
    
    normal_gene = _derive_cell(alphas_normal)
    reduce_gene = _derive_cell(alphas_reduce)
    
    architecture = {
        'normal': normal_gene,
        'reduce': reduce_gene,
        'num_nodes': num_nodes,
    }
    
    return architecture


def analyze_architecture(architecture):
    """
    分析搜索到的架构，统计使用的操作类型
    Args:
        architecture: 架构字典
    Returns:
        分析结果字典
    """
    def _count_ops(gene):
        op_counts = {}
        for edge in gene:
            op = edge['op']
            op_counts[op] = op_counts.get(op, 0) + 1
        return op_counts
    
    normal_ops = _count_ops(architecture['normal'])
    reduce_ops = _count_ops(architecture['reduce'])
    
    # 合并统计
    all_ops = {}
    for op, count in normal_ops.items():
        all_ops[op] = all_ops.get(op, 0) + count
    for op, count in reduce_ops.items():
        all_ops[op] = all_ops.get(op, 0) + count
    
    # 统计卷积核大小分布
    kernel_counts = {}
    for op in all_ops.keys():
        if '3x3' in op:
            kernel_counts['3x3'] = kernel_counts.get('3x3', 0) + all_ops[op]
        elif '5x5' in op:
            kernel_counts['5x5'] = kernel_counts.get('5x5', 0) + all_ops[op]
        elif '7x7' in op:
            kernel_counts['7x7'] = kernel_counts.get('7x7', 0) + all_ops[op]
    
    # 统计跳层连接数量
    skip_count = all_ops.get('identity', 0)
    
    analysis = {
        'total_edges': len(architecture['normal']) + len(architecture['reduce']),
        'normal_ops': normal_ops,
        'reduce_ops': reduce_ops,
        'all_ops': all_ops,
        'kernel_distribution': kernel_counts,
        'skip_connections': skip_count,
    }
    
    return analysis


def save_architecture(architecture, filepath):
    """保存架构到JSON文件"""
    with open(filepath, 'w') as f:
        json.dump(architecture, f, indent=2)
    print(f"架构已保存到: {filepath}")


def load_architecture(filepath):
    """从JSON文件加载架构"""
    with open(filepath, 'r') as f:
        architecture = json.load(f)
    return architecture


def print_architecture(architecture):
    """打印架构结构"""
    print("\n" + "="*60)
    print("搜索到的最优架构")
    print("="*60)
    
    print("\n--- Normal Cell (普通单元) ---")
    print(f"节点数: {architecture['num_nodes']}")
    for edge in architecture['normal']:
        print(f"  节点 {edge['from']} -> 节点 {edge['to']}: "
              f"{edge['op']} (权重: {edge['weight']:.4f})")
    
    print("\n--- Reduction Cell (降维单元) ---")
    print(f"节点数: {architecture['num_nodes']}")
    for edge in architecture['reduce']:
        print(f"  节点 {edge['from']} -> 节点 {edge['to']}: "
              f"{edge['op']} (权重: {edge['weight']:.4f})")
    
    # 打印分析结果
    analysis = analyze_architecture(architecture)
    print("\n--- 架构分析 ---")
    print(f"总边数: {analysis['total_edges']}")
    print(f"跳层连接数: {analysis['skip_connections']}")
    print("\n操作类型分布:")
    for op, count in sorted(analysis['all_ops'].items(), key=lambda x: -x[1]):
        print(f"  {op}: {count}")
    
    if analysis['kernel_distribution']:
        print("\n卷积核大小分布:")
        for kernel, count in sorted(analysis['kernel_distribution'].items()):
            print(f"  {kernel}: {count}")
    
    print("="*60 + "\n")
