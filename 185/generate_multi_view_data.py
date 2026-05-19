import numpy as np
import open3d as o3d
import os


def generate_point_cloud_from_mesh(mesh, num_points=5000):
    pcd = mesh.sample_points_poisson_disk(num_points)
    return pcd


def generate_bunny_point_cloud(num_points=5000):
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=30)
    pcd = generate_point_cloud_from_mesh(mesh, num_points)
    return pcd


def generate_box_point_cloud(num_points=5000):
    mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=2.0, depth=2.0)
    mesh.compute_vertex_normals()
    pcd = generate_point_cloud_from_mesh(mesh, num_points)
    return pcd


def generate_rotation_matrix(axis, angle):
    axis = axis / np.linalg.norm(axis)
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1 - c
    
    x, y, z = axis
    R = np.array([
        [t*x*x + c, t*x*y - s*z, t*x*z + s*y],
        [t*x*y + s*z, t*y*y + c, t*y*z - s*x],
        [t*x*z - s*y, t*y*z + s*x, t*z*z + c]
    ])
    return R


def generate_view_transforms(num_views=4, radius=3.0):
    transforms = []
    
    for i in range(num_views):
        angle_y = 2 * np.pi * i / num_views
        angle_x = np.random.uniform(-np.pi/6, np.pi/6)
        
        R_y = generate_rotation_matrix(np.array([0, 1, 0]), angle_y)
        R_x = generate_rotation_matrix(np.array([1, 0, 0]), angle_x)
        R = R_y @ R_x
        
        t = np.array([
            radius * np.sin(angle_y),
            0.5,
            radius * np.cos(angle_y)
        ])
        
        transformation = np.eye(4)
        transformation[:3, :3] = R
        transformation[:3, 3] = t
        
        transforms.append(transformation)
    
    return transforms


def add_noise(pcd, noise_std=0.01):
    points = np.asarray(pcd.points)
    noise = np.random.normal(0, noise_std, points.shape)
    pcd.points = o3d.utility.Vector3dVector(points + noise)
    return pcd


def add_outliers(pcd, outlier_ratio=0.05, outlier_scale=3.0):
    points = np.asarray(pcd.points)
    num_outliers = int(len(points) * outlier_ratio)
    
    centroid = np.mean(points, axis=0)
    outliers = centroid + np.random.uniform(-outlier_scale, outlier_scale, (num_outliers, 3))
    
    all_points = np.vstack([points, outliers])
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    print(f"添加离群点: {num_outliers} ({outlier_ratio*100:.1f}%)")
    
    return pcd


def generate_multi_view_point_clouds(num_views=4, num_points=8000, 
                                     noise_std=0.005, outlier_ratio=0.05,
                                     output_dir="multi_view_data"):
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"生成多视角点云数据...")
    print(f"视角数量: {num_views}")
    print(f"每个视角点数: {num_points}")
    
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=40)
    complete_pcd = generate_point_cloud_from_mesh(mesh, num_points * 2)
    
    view_transforms = generate_view_transforms(num_views, radius=0.0)
    
    point_clouds = []
    
    for i in range(num_views):
        pcd_view = o3d.geometry.PointCloud()
        
        view_center = np.array([
            np.sin(2 * np.pi * i / num_views) * 0.5,
            0,
            np.cos(2 * np.pi * i / num_views) * 0.5
        ])
        
        complete_points = np.asarray(complete_pcd.points)
        
        view_direction = view_center / (np.linalg.norm(view_center) + 1e-6)
        dot_products = complete_points @ view_direction
        
        visible_mask = dot_products > -0.3
        visible_points = complete_points[visible_mask]
        
        if len(visible_points) > num_points:
            indices = np.random.choice(len(visible_points), num_points, replace=False)
            visible_points = visible_points[indices]
        
        pcd_view.points = o3d.utility.Vector3dVector(visible_points)
        pcd_view.transform(view_transforms[i])
        
        pcd_view = add_noise(pcd_view, noise_std=noise_std)
        pcd_view = add_outliers(pcd_view, outlier_ratio=outlier_ratio)
        
        idx = np.random.permutation(len(pcd_view.points))
        pcd_view.points = o3d.utility.Vector3dVector(np.asarray(pcd_view.points)[idx])
        
        output_path = os.path.join(output_dir, f"view_{i:03d}.ply")
        o3d.io.write_point_cloud(output_path, pcd_view)
        print(f"视角 {i} 已保存: {output_path} ({len(pcd_view.points)} 点)")
        
        point_clouds.append(pcd_view)
    
    colors = [
        [1, 0.706, 0], [0, 0.651, 0.929], [0.929, 0.490, 0.192],
        [0.494, 0.184, 0.556], [0.466, 0.674, 0.188], [0.301, 0.745, 0.933]
    ]
    
    pcds_colored = []
    for i, pcd in enumerate(point_clouds):
        pcd_c = copy.deepcopy(pcd)
        pcd_c.paint_uniform_color(colors[i % len(colors)])
        pcds_colored.append(pcd_c)
    
    print("\n显示原始多视角点云...")
    o3d.visualization.draw_geometries(
        pcds_colored,
        window_name="多视角点云 (原始位置)",
        width=1000, height=700
    )
    
    print(f"\n多视角点云生成完成!")
    print(f"数据保存在: {output_dir}/")
    
    return point_clouds, view_transforms


def main():
    import copy
    import argparse
    
    parser = argparse.ArgumentParser(description="生成多视角点云测试数据")
    parser.add_argument("--num_views", type=int, default=4, help="视角数量")
    parser.add_argument("--num_points", type=int, default=8000, help="每个视角的点数")
    parser.add_argument("--noise_std", type=float, default=0.005, help="噪声标准差")
    parser.add_argument("--outlier_ratio", type=float, default=0.05, help="离群点比例")
    parser.add_argument("--output_dir", type=str, default="multi_view_data", help="输出目录")
    
    args = parser.parse_args()
    
    generate_multi_view_point_clouds(
        num_views=args.num_views,
        num_points=args.num_points,
        noise_std=args.noise_std,
        outlier_ratio=args.outlier_ratio,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
