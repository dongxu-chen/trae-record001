import subprocess
import sys
import os


def check_dependencies():
    required_packages = ["numpy", "open3d", "scipy"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} 未安装")
    
    if missing_packages:
        print(f"\n缺少依赖: {missing_packages}")
        print(f"请运行: pip install {' '.join(missing_packages)}")
        return False
    return True


def run_command(cmd, description):
    print(f"\n{'='*60}")
    print(f"执行: {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"\n错误: 命令执行失败，返回码: {result.returncode}")
        return False
    return True


def main():
    print("ICP点云配准演示 (完整版)")
    print("="*60)
    print("\n功能列表:")
    print("  ✓ FPFH特征匹配 + RANSAC初始变换估计")
    print("  ✓ 自适应KD-Tree搜索半径")
    print("  ✓ 逐次迭代动画可视化")
    print("  ✓ 离群点自动移除 (统计/半径/组合滤波)")
    print("  ✓ 增强配准精度评估 (RMSE、重叠覆盖率)")
    print("  ✓ 多视角点云同时配准与融合")
    print()
    
    if not check_dependencies():
        sys.exit(1)
    
    print("\n请选择演示模式:")
    print("  1. 双点云配准 - 完整流程 [推荐]")
    print("  2. 双点云配准 - 无FPFH初始估计")
    print("  3. 双点云配准 - 固定搜索半径")
    print("  4. 双点云配准 - 无离群点移除")
    print("  5. 多视角点云配准与融合")
    print("  6. 仅生成双点云测试数据")
    print("  7. 仅生成多视角测试数据")
    
    choice = input("\n请输入选项 (1-7, 默认1): ").strip() or "1"
    
    if choice == "6":
        run_command(f"{sys.executable} generate_test_data.py", "生成双点云测试数据")
        return
    elif choice == "7":
        num_views = input("请输入视角数量 (默认4): ").strip() or "4"
        run_command(f"{sys.executable} generate_multi_view_data.py --num_views {num_views}", 
                   "生成多视角测试数据")
        return
    
    if choice == "5":
        print("\n1. 生成多视角测试数据...")
        num_views = input("请输入视角数量 (默认4): ").strip() or "4"
        if not run_command(
            f"{sys.executable} generate_multi_view_data.py --num_views {num_views}",
            "生成多视角测试数据"
        ):
            sys.exit(1)
        
        print("\n2. 运行多视角配准...")
        cmd = (f"{sys.executable} multi_view_demo.py "
               f"--input_dir multi_view_data "
               f"--voxel_size 0.05 "
               f"--max_iter 50 "
               f"--reference_idx 0")
        if not run_command(cmd, "多视角点云配准与融合"):
            sys.exit(1)
    else:
        print("\n1. 生成测试数据...")
        if not run_command(f"{sys.executable} generate_test_data.py", "生成测试点云数据"):
            sys.exit(1)
        
        print("\n2. 运行ICP配准...")
        
        if choice == "1":
            cmd = (f"{sys.executable} icp_registration.py "
                   f"--source source.ply "
                   f"--target target.ply "
                   f"--voxel_size 0.05 "
                   f"--max_iter 50 "
                   f"--outlier_method statistical")
            desc = "完整ICP配准 (FPFH + 自适应 + 离群点移除)"
        elif choice == "2":
            cmd = (f"{sys.executable} icp_registration.py "
                   f"--source source.ply "
                   f"--target target.ply "
                   f"--voxel_size 0.05 "
                   f"--max_iter 50 "
                   f"--no_fpfh")
            desc = "仅ICP配准 (无FPFH初始估计)"
        elif choice == "3":
            cmd = (f"{sys.executable} icp_registration.py "
                   f"--source source.ply "
                   f"--target target.ply "
                   f"--voxel_size 0.05 "
                   f"--base_dist 0.1 "
                   f"--max_iter 50 "
                   f"--no_adaptive")
            desc = "ICP配准 (固定搜索半径)"
        elif choice == "4":
            cmd = (f"{sys.executable} icp_registration.py "
                   f"--source source.ply "
                   f"--target target.ply "
                   f"--voxel_size 0.05 "
                   f"--max_iter 50 "
                   f"--no_outlier_removal")
            desc = "ICP配准 (无离群点移除)"
        else:
            print("无效选项，使用默认模式")
            cmd = (f"{sys.executable} icp_registration.py "
                   f"--source source.ply "
                   f"--target target.ply "
                   f"--voxel_size 0.05 "
                   f"--max_iter 50")
            desc = "完整ICP配准"
        
        if not run_command(cmd, desc):
            sys.exit(1)
    
    print("\n" + "="*60)
    print("演示完成!")
    print("="*60)


if __name__ == "__main__":
    main()
