#!/usr/bin/env python3
import numpy as np
import argparse
import sys

from lightfield import LightField
from depth_estimation import DepthEstimator
from fusion import MultiViewFusion
from evaluation import DepthEvaluator
from gui import LightFieldDepthGUI


def run_gui_demo():
    print("=" * 60)
    print("光场图像深度估计系统 - 交互演示")
    print("=" * 60)
    
    print("\n正在生成合成光场数据...")
    lf = LightField.generate_synthetic(
        num_rows=5, num_cols=5,
        height=200, width=200,
        num_depths=3)
    
    print(f"光场维度: {lf.num_rows} x {lf.num_cols} 子孔径视图")
    print(f"图像分辨率: {lf.height} x {lf.width}")
    
    print("\n启动交互界面...")
    print("交互功能:")
    print("  - 滑动条: 调整重聚焦平面")
    print("  - 单选按钮: 选择深度估计方法")
    print("  - 计算深度: 运行选定的深度估计算法")
    print("  - 优化深度: 对深度图进行后处理优化")
    print("  - 保存结果: 保存深度图和置信度图")
    print()
    
    gui = LightFieldDepthGUI(lf)
    gui.run()


def run_cli_benchmark():
    print("=" * 60)
    print("光场深度估计 - 命令行基准测试")
    print("=" * 60)
    
    lf = LightField.generate_synthetic(
        num_rows=5, num_cols=5,
        height=256, width=256,
        num_depths=4)
    
    print(f"\n光场: {lf.num_rows}x{lf.num_cols} 视图, {lf.height}x{lf.width} 像素")
    
    estimator = DepthEstimator(lf)
    fusion = MultiViewFusion(lf)
    evaluator = DepthEvaluator()
    
    methods = {
        '聚焦分析 (Focus)': 'focus',
        '散焦分析 (Defocus)': 'defocus',
        '视差估计 (Disparity)': 'disparity',
        '多方法融合 (Fusion)': 'fusion'
    }
    
    results = {}
    
    for method_name, method_key in methods.items():
        print(f"\n正在执行 {method_name}...")
        
        if method_key == 'focus':
            depth, conf = estimator.estimate_depth_from_focus()
        elif method_key == 'defocus':
            depth, conf = estimator.estimate_depth_from_defocus()
        elif method_key == 'disparity':
            depth, conf = estimator.estimate_disparity()
        elif method_key == 'fusion':
            depth, conf = fusion.multi_method_fusion()
        
        metrics = evaluator.full_evaluation(
            depth, conf,
            image=lf.get_center_view())
        
        results[method_name] = metrics
        print(f"  完成! 平滑度: {metrics['Smoothness']:.6f}, 平均置信度: {metrics['MeanConfidence']:.4f}")
    
    print("\n" + "=" * 60)
    print("方法对比结果")
    print("=" * 60)
    print(f"{'方法':<25} {'平滑度':<12} {'平均置信度':<12} {'深度标准差':<12}")
    print("-" * 60)
    
    for method_name in methods.keys():
        r = results[method_name]
        print(f"{method_name:<25} {r['Smoothness']:<12.6f} {r['MeanConfidence']:<12.4f} {r['StdDepth']:<12.6f}")
    
    print("=" * 60)


def run_custom_data(data_dir: str):
    print(f"从目录加载光场数据: {data_dir}")
    
    try:
        lf = LightField.from_directory(data_dir)
        print(f"成功加载: {lf.num_rows}x{lf.num_cols} 视图, {lf.height}x{lf.width} 像素")
        
        gui = LightFieldDepthGUI(lf)
        gui.run()
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='光场图像深度估计系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py demo           # 运行交互演示
  python main.py benchmark      # 运行基准测试
  python main.py --data ./data  # 使用自定义数据
        """
    )
    
    parser.add_argument('mode', nargs='?', default='demo',
                       choices=['demo', 'benchmark'],
                       help='运行模式')
    parser.add_argument('--data', type=str,
                       help='光场图像数据目录')
    
    args = parser.parse_args()
    
    if args.data:
        run_custom_data(args.data)
    elif args.mode == 'demo':
        run_gui_demo()
    elif args.mode == 'benchmark':
        run_cli_benchmark()


if __name__ == '__main__':
    main()
