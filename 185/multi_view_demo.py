import os
import sys
import numpy as np
import open3d as o3d
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icp_registration as icp


def load_multi_view_point_clouds(input_dir):
    pcd_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.ply')])
    print(f"在 {input_dir} 中找到 {len(pcd_files)} 个点云文件")
    
    point_clouds = []
    for f in pcd_files:
        file_path = os.path.join(input_dir, f)
        pcd = o3d.io.read_point_cloud(file_path)
        print(f"  加载 {f}: {len(pcd.points)} 点")
        point_clouds.append(pcd)
    
    return point_clouds, pcd_files


def preprocess_multi_view(point_clouds, voxel_size=0.05, remove_outliers_flag=True,
                         outlier_method='statistical'):
    print(f"\n{'='*60}")
    print("预处理多视角点云")
    print(f"{'='*60}")
    
    processed_clouds = []
    for i, pcd in enumerate(point_clouds):
        print(f"\n处理点云 {i}:")
        processed = icp.preprocess_point_cloud(
            pcd, voxel_size=voxel_size,
            remove_outliers_flag=remove_outliers_flag,
            outlier_method=outlier_method
        )
        processed_clouds.append(processed)
    
    return processed_clouds


def run_multi_view_registration(point_clouds, voxel_size=0.05, use_fpfh=True,
                               base_correspondence_distance=None, max_iterations=50,
                               use_adaptive_radius=True, reference_idx=0,
                               remove_outliers_flag=True, outlier_method='statistical'):
    
    processed_clouds = preprocess_multi_view(
        point_clouds, voxel_size=voxel_size,
        remove_outliers_flag=remove_outliers_flag,
        outlier_method=outlier_method
    )
    
    transformations, pairwise_metrics, all_histories = icp.multi_view_registration(
        processed_clouds, voxel_size=voxel_size, use_fpfh=use_fpfh,
        base_correspondence_distance=base_correspondence_distance,
        max_iterations=max_iterations,
        use_adaptive_radius=use_adaptive_radius,
        reference_idx=reference_idx
    )
    
    return processed_clouds, transformations, pairwise_metrics, all_histories


def main():
    parser = argparse.ArgumentParser(description="多视角点云配准演示")
    parser.add_argument("--input_dir", type=str, default="multi_view_data", 
                       help="多视角点云目录")
    parser.add_argument("--generate_data", action="store_true", 
                       help="先生成测试数据再运行配准")
    parser.add_argument("--num_views", type=int, default=4, help="视角数量")
    parser.add_argument("--voxel_size", type=float, default=0.05, help="体素滤波大小")
    parser.add_argument("--no_fpfh", action="store_true", help="禁用FPFH初始变换估计")
    parser.add_argument("--no_adaptive", action="store_true", help="禁用自适应搜索半径")
    parser.add_argument("--no_outlier_removal", action="store_true", help="禁用离群点移除")
    parser.add_argument("--outlier_method", type=str, default="statistical", 
                       choices=["statistical", "radius", "combined"], help="离群点移除方法")
    parser.add_argument("--reference_idx", type=int, default=0, help="参考点云索引")
    parser.add_argument("--max_iter", type=int, default=50, help="最大迭代次数")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("多视角点云配准系统")
    print(f"{'='*60}")
    
    if args.generate_data or not os.path.exists(args.input_dir):
        print(f"\n生成多视角测试数据...")
        from generate_multi_view_data import generate_multi_view_point_clouds
        point_clouds, _ = generate_multi_view_point_clouds(
            num_views=args.num_views,
            output_dir=args.input_dir
        )
    else:
        point_clouds, _ = load_multi_view_point_clouds(args.input_dir)
    
    if len(point_clouds) < 2:
        print("错误: 需要至少2个点云进行配准")
        sys.exit(1)
    
    processed_clouds, transformations, pairwise_metrics, all_histories = run_multi_view_registration(
        point_clouds,
        voxel_size=args.voxel_size,
        use_fpfh=not args.no_fpfh,
        use_adaptive_radius=not args.no_adaptive,
        remove_outliers_flag=not args.no_outlier_removal,
        outlier_method=args.outlier_method,
        reference_idx=args.reference_idx,
        max_iterations=args.max_iter
    )
    
    print(f"\n{'='*60}")
    print("保存变换矩阵")
    print(f"{'='*60}")
    icp.save_transformations(transformations)
    
    print(f"\n{'='*60}")
    print("可视化配准结果")
    print(f"{'='*60}")
    merged_pcd = icp.visualize_multi_view_registration(
        processed_clouds, transformations, reference_idx=args.reference_idx
    )
    
    merged_output = "merged_point_cloud.ply"
    o3d.io.write_point_cloud(merged_output, merged_pcd)
    print(f"\n融合点云已保存到: {merged_output}")
    
    print(f"\n{'='*60}")
    print("配准完成!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
