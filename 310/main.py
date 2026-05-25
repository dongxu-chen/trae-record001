"""
光束追踪法光学模拟 - 主程序
============================

功能：
- 追踪光线在透镜、反射镜间传播
- 计算成像位置和像差
- 支持球面/非球面透镜
- 支持折射/反射模型
- 输出光路图和点列图
- 支持多波长色散模拟

使用方法：
    python main.py --example 1    # 运行单透镜示例
    python main.py --example 2    # 运行双胶合透镜示例
    python main.py --example 3    # 运行反射望远镜示例
    python main.py --all          # 运行所有示例
"""

import argparse
import sys
import os

def run_example(example_num):
    if example_num == 1:
        from example1_singlet_lens import main as run_ex1
        return run_ex1()
    elif example_num == 2:
        from example2_doublet_lens import main as run_ex2
        return run_ex2()
    elif example_num == 3:
        from example3_reflective_telescope import main as run_ex3
        return run_ex3()
    else:
        print(f"错误: 无效的示例编号 {example_num}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='光束追踪法光学模拟 - 光线追迹与像差分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--example', type=int, choices=[1, 2, 3],
                        help='要运行的示例编号 (1=单透镜, 2=双胶合透镜, 3=反射望远镜)')
    parser.add_argument('--all', action='store_true',
                        help='运行所有示例')
    parser.add_argument('--no-display', action='store_true',
                        help='不显示图形，仅保存到文件')

    args = parser.parse_args()

    if args.no_display:
        import matplotlib
        matplotlib.use('Agg')

    print("=" * 60)
    print("  光束追踪法光学模拟系统")
    print("  Ray Tracing Optical Simulation")
    print("=" * 60)
    print()

    if args.all:
        for i in range(1, 4):
            print(f"\n{'=' * 60}")
            print(f"  正在运行示例 {i}...")
            print('=' * 60)
            run_example(i)
    elif args.example is not None:
        run_example(args.example)
    else:
        print("请选择要运行的示例:")
        print("  1. 单球面透镜 (Single Spherical Lens)")
        print("  2. 双胶合消色差透镜 (Achromatic Doublet)")
        print("  3. 牛顿式反射望远镜 (Newtonian Reflector)")
        print()
        print("使用方法:")
        print("  python main.py --example 1")
        print("  python main.py --all")
        print()

        choice = input("请输入示例编号 (1-3) 或 'all' 运行全部: ").strip()

        if choice.lower() == 'all':
            for i in range(1, 4):
                print(f"\n{'=' * 60}")
                print(f"  正在运行示例 {i}...")
                print('=' * 60)
                run_example(i)
        elif choice.isdigit() and 1 <= int(choice) <= 3:
            run_example(int(choice))
        else:
            print("无效输入，退出程序。")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("所有模拟完成！生成的图像文件已保存在当前目录。")
    print("=" * 60)

if __name__ == '__main__':
    main()
