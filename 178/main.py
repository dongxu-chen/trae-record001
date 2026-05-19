"""
可微分神经网络架构搜索工具 - 主入口脚本
使用DARTS方法搜索CIFAR-10图像分类网络

使用方法:
    # 1. 运行完整的架构搜索流程
    python main.py --search
    
    # 2. 从检查点导出架构
    python main.py --export --checkpoint ./checkpoints/best_search_model.pt
    
    # 3. 训练搜索到的最终模型
    python main.py --train_final --model_code ./generated_model.py
    
    # 4. 快速演示 (使用预设架构)
    python main.py --demo
"""

import argparse
import torch
import os
import sys

from darts_nas.core.config import SearchConfig, TrainConfig
from darts_nas.search.search_cell import SearchNetwork
from darts_nas.search.architect import search_architecture
from darts_nas.search.advanced_search import search_architecture_advanced
from darts_nas.utils.data_loader import get_search_dataloaders, get_final_dataloaders
from darts_nas.models.architecture import (
    derive_architecture, save_architecture, 
    load_architecture, print_architecture
)
from darts_nas.models.genotype import save_model_code, save_full_search_model
from darts_nas.utils.trainer import train_final_model


def run_search(args):
    """执行架构搜索"""
    print("="*60)
    print("开始神经网络架构搜索 (DARTS)")
    print("="*60)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    # 配置
    config = SearchConfig()
    
    # 数据加载
    print("\n加载CIFAR-10数据集...")
    train_loader, valid_loader, test_loader = get_search_dataloaders(
        data_path=config.DATA_PATH,
        batch_size=config.BATCH_SIZE,
        num_workers=args.num_workers
    )
    print(f"训练集大小: {len(train_loader.dataset)}")
    print(f"验证集大小: {len(valid_loader.dataset)}")
    print(f"测试集大小: {len(test_loader.dataset)}")
    
    # 创建搜索网络
    print("\n创建搜索网络...")
    criterion = torch.nn.CrossEntropyLoss().to(device)
    drop_path_prob = args.drop_path_prob if args.drop_path_prob > 0 else config.DROP_PATH_PROB
    model = SearchNetwork(
        C=config.INIT_CHANNELS,
        num_classes=config.NUM_CLASSES,
        num_cells=config.NUM_CELLS,
        num_nodes=config.NUM_NODES_PER_CELL,
        drop_path_prob=drop_path_prob,  # DropPath强制探索多样化架构
        criterion=criterion
    ).to(device)
    
    print(f"默认使用一阶近似 (节省内存，提升速度)")
    print(f"DropPath概率: {drop_path_prob} (用于强制探索多样化架构)")
    if args.unrolled:
        print("注意: 已启用二阶近似 (更准确但更慢)")
    
    # 打印模型信息
    total_params = sum(p.numel() for p in model.parameters())
    arch_params = sum(p.numel() for p in model.arch_parameters())
    weight_params = total_params - arch_params
    print(f"总参数量: {total_params:,}")
    print(f"  - 架构参数: {arch_params:,}")
    print(f"  - 权重参数: {weight_params:,}")
    
    # 执行搜索
    print("\n开始架构搜索...")
    
    # 判断是否使用高级搜索（多目标优化 + 权重继承 + 知识蒸馏）
    use_advanced = args.multi_objective or args.weight_inheritance or args.distillation
    
    if use_advanced:
        model, search_history = search_architecture_advanced(
            model, train_loader, valid_loader, test_loader,
            config, device, unrolled=args.unrolled,
            save_path=args.save_path,
            use_multi_objective=args.multi_objective,
            use_weight_inheritance=args.weight_inheritance,
            use_distillation=args.distillation
        )
    else:
        model = search_architecture(
            model, train_loader, valid_loader, test_loader,
            config, device, unrolled=args.unrolled,
            save_path=args.save_path
        )
    
    # 导出最优架构
    print("\n导出最优架构...")
    alphas_normal = model.alphas_normal.detach().cpu()
    alphas_reduce = model.alphas_reduce.detach().cpu()
    
    architecture = derive_architecture(
        alphas_normal, alphas_reduce,
        num_nodes=config.NUM_NODES_PER_CELL,
        skip_threshold=config.SKIP_THRESHOLD
    )
    
    # 保存架构
    arch_path = os.path.join(args.save_path, 'best_architecture.json')
    save_architecture(architecture, arch_path)
    
    # 打印架构
    print_architecture(architecture)
    
    # 保存完整的模型状态（含BatchNorm参数和架构权重）
    print("\n保存完整模型状态...")
    saved_files = save_full_search_model(
        model, architecture, args.save_path, prefix='best'
    )
    
    print("\n架构搜索完成!")
    print(f"模型代码: {saved_files['model_code']}")
    print(f"架构定义: {saved_files['architecture']}")
    print(f"完整状态: {saved_files['model_state']}")


def export_architecture(args):
    """从检查点导出架构"""
    print("="*60)
    print("从检查点导出架构")
    print("="*60)
    
    if not os.path.exists(args.checkpoint):
        print(f"错误: 检查点文件不存在: {args.checkpoint}")
        return
    
    # 加载检查点
    checkpoint = torch.load(args.checkpoint, map_location='cpu')
    
    if 'alphas_normal' not in checkpoint or 'alphas_reduce' not in checkpoint:
        print("错误: 检查点中不包含架构参数!")
        return
    
    alphas_normal = checkpoint['alphas_normal']
    alphas_reduce = checkpoint['alphas_reduce']
    
    print(f"检查点 epoch: {checkpoint.get('epoch', 'N/A')}")
    print(f"验证准确率: {checkpoint.get('valid_acc', 'N/A'):.2f}%")
    print(f"测试准确率: {checkpoint.get('test_acc', 'N/A'):.2f}%")
    
    # 导出架构
    config = SearchConfig()
    architecture = derive_architecture(
        alphas_normal, alphas_reduce,
        num_nodes=config.NUM_NODES_PER_CELL,
        skip_threshold=config.SKIP_THRESHOLD
    )
    
    # 保存架构
    save_dir = os.path.dirname(args.checkpoint)
    arch_path = os.path.join(save_dir, 'exported_architecture.json')
    save_architecture(architecture, arch_path)
    
    # 打印架构
    print_architecture(architecture)
    
    # 生成PyTorch模型代码
    model_code_path = os.path.join(save_dir, 'exported_model.py')
    save_model_code(
        architecture, model_code_path,
        num_classes=config.NUM_CLASSES,
        num_cells=TrainConfig.NUM_CELLS,
        init_channels=TrainConfig.INIT_CHANNELS,
        auxiliary=TrainConfig.AUXILIARY
    )
    
    print(f"\n架构导出完成!")
    print(f"架构文件: {arch_path}")
    print(f"模型代码: {model_code_path}")


def train_final(args):
    """训练搜索到的最终模型"""
    print("="*60)
    print("训练搜索到的最终模型")
    print("="*60)
    
    if not os.path.exists(args.model_code):
        print(f"错误: 模型代码文件不存在: {args.model_code}")
        return
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")
    
    config = TrainConfig()
    
    # 数据加载
    print("\n加载CIFAR-10数据集...")
    train_loader, test_loader = get_final_dataloaders(
        data_path=SearchConfig.DATA_PATH,
        batch_size=config.BATCH_SIZE,
        num_workers=args.num_workers,
        cutout=config.CUTOUT,
        cutout_length=config.CUTOUT_LENGTH
    )
    print(f"训练集大小: {len(train_loader.dataset)}")
    print(f"测试集大小: {len(test_loader.dataset)}")
    
    # 训练模型
    print("\n开始训练最终模型...")
    print(f"训练轮数: {config.EPOCHS}")
    print(f"初始通道数: {config.INIT_CHANNELS}")
    print(f"Cell数量: {config.NUM_CELLS}")
    
    model = train_final_model(
        args.model_code, train_loader, test_loader,
        config, device, save_path=args.save_path
    )
    
    print("\n最终模型训练完成!")


def run_demo(args):
    """快速演示 - 使用预设的示例架构"""
    print("="*60)
    print("快速演示 - 使用预设示例架构")
    print("="*60)
    
    # 创建一个示例架构 (模拟搜索结果)
    demo_architecture = {
        "normal": [
            {"from": 0, "to": 2, "op": "conv3x3", "weight": 0.85},
            {"from": 1, "to": 2, "op": "identity", "weight": 0.78},
            {"from": 0, "to": 3, "op": "sep_conv3x3", "weight": 0.92},
            {"from": 2, "to": 3, "op": "conv5x5", "weight": 0.81},
            {"from": 0, "to": 4, "op": "conv3x3", "weight": 0.76},
            {"from": 3, "to": 4, "op": "avg_pool3x3", "weight": 0.69},
            {"from": 2, "to": 5, "op": "sep_conv5x5", "weight": 0.88},
            {"from": 4, "to": 5, "op": "identity", "weight": 0.74},
        ],
        "reduce": [
            {"from": 0, "to": 2, "op": "conv5x5", "weight": 0.91},
            {"from": 1, "to": 2, "op": "max_pool3x3", "weight": 0.83},
            {"from": 0, "to": 3, "op": "conv7x7", "weight": 0.79},
            {"from": 2, "to": 3, "op": "sep_conv3x3", "weight": 0.87},
            {"from": 1, "to": 4, "op": "conv3x3", "weight": 0.72},
            {"from": 3, "to": 4, "op": "identity", "weight": 0.85},
            {"from": 2, "to": 5, "op": "sep_conv5x5", "weight": 0.93},
            {"from": 4, "to": 5, "op": "avg_pool3x3", "weight": 0.68},
        ],
        "num_nodes": 4
    }
    
    # 保存示例架构
    os.makedirs(args.save_path, exist_ok=True)
    arch_path = os.path.join(args.save_path, 'demo_architecture.json')
    save_architecture(demo_architecture, arch_path)
    
    # 打印架构
    print_architecture(demo_architecture)
    
    # 生成PyTorch模型代码
    model_code_path = os.path.join(args.save_path, 'demo_model.py')
    save_model_code(
        demo_architecture, model_code_path,
        num_classes=10,
        num_cells=20,
        init_channels=36,
        auxiliary=True
    )
    
    print(f"\n演示完成!")
    print(f"示例架构已保存到: {arch_path}")
    print(f"生成的模型代码: {model_code_path}")
    print("\n你可以使用以下命令训练这个示例模型:")
    print(f"  python main.py --train_final --model_code {model_code_path}")


def main():
    parser = argparse.ArgumentParser(description='可微分神经网络架构搜索工具')
    
    # 模式选择
    parser.add_argument('--search', action='store_true', help='执行架构搜索')
    parser.add_argument('--export', action='store_true', help='从检查点导出架构')
    parser.add_argument('--train_final', action='store_true', help='训练搜索到的最终模型')
    parser.add_argument('--demo', action='store_true', help='运行快速演示')
    
    # 参数
    parser.add_argument('--checkpoint', type=str, default='./checkpoints/best_search_model.pt',
                        help='检查点路径 (用于导出架构)')
    parser.add_argument('--model_code', type=str, default='./generated_model.py',
                        help='生成的模型代码路径 (用于训练最终模型)')
    parser.add_argument('--save_path', type=str, default='./checkpoints',
                        help='保存路径')
    parser.add_argument('--num_workers', type=int, default=2,
                        help='数据加载线程数')
    parser.add_argument('--unrolled', action='store_true',
                        help='使用二阶近似 (更准确但更慢，默认使用一阶近似)')
    parser.add_argument('--drop_path_prob', type=float, default=0.2,
                        help='DropPath概率，越高探索越多 (默认: 0.2)')
    
    # 高级功能开关
    parser.add_argument('--multi_objective', action='store_true',
                        help='启用多目标优化 (延迟、参数量、FLOPs同时优化，使用Pareto排序)')
    parser.add_argument('--weight_inheritance', action='store_true',
                        help='启用权重继承策略 (从已训练权重初始化，加速收敛)')
    parser.add_argument('--distillation', action='store_true',
                        help='启用知识蒸馏 (搜索到的架构向教师模型蒸馏，提升精度)')
    parser.add_argument('--all_advanced', action='store_true',
                        help='启用所有高级功能 (多目标优化 + 权重继承 + 知识蒸馏)')
    
    args = parser.parse_args()
    
    # 如果启用所有高级功能
    if args.all_advanced:
        args.multi_objective = True
        args.weight_inheritance = True
        args.distillation = True
    
    # 如果没有指定模式，默认显示帮助
    if not any([args.search, args.export, args.train_final, args.demo]):
        parser.print_help()
        print("\n示例用法:")
        print("  # 基础搜索（一阶近似，batch size 128）")
        print("  python main.py --search")
        print("")
        print("  # 高级搜索（启用所有高级功能）")
        print("  python main.py --search --all_advanced")
        print("")
        print("  # 单独启用某个高级功能")
        print("  python main.py --search --multi_objective              # 多目标优化")
        print("  python main.py --search --weight_inheritance           # 权重继承")
        print("  python main.py --search --distillation                 # 知识蒸馏")
        print("  python main.py --search --multi_objective --distillation")
        print("")
        print("  # 其他功能")
        print("  python main.py --export --checkpoint ./checkpoints/best_search_model.pt")
        print("  python main.py --train_final --model_code ./checkpoints/searched_model.py")
        print("  python main.py --demo                # 快速演示")
        return
    
    if args.search:
        run_search(args)
    elif args.export:
        export_architecture(args)
    elif args.train_final:
        train_final(args)
    elif args.demo:
        run_demo(args)


if __name__ == '__main__':
    main()
