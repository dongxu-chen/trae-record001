import numpy as np
import open3d as o3d


def generate_point_cloud_from_mesh(mesh, num_points=5000):
    pcd = mesh.sample_points_poisson_disk(num_points)
    return pcd


def generate_bunny_point_cloud(num_points=5000):
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=20)
    pcd = generate_point_cloud_from_mesh(mesh, num_points)
    return pcd


def generate_box_point_cloud(num_points=5000):
    mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=2.0, depth=2.0)
    mesh.compute_vertex_normals()
    pcd = generate_point_cloud_from_mesh(mesh, num_points)
    return pcd


def generate_random_transform():
    angle_x = np.random.uniform(-np.pi / 6, np.pi / 6)
    angle_y = np.random.uniform(-np.pi / 6, np.pi / 6)
    angle_z = np.random.uniform(-np.pi / 6, np.pi / 6)
    
    R_x = np.array([
        [1, 0, 0],
        [0, np.cos(angle_x), -np.sin(angle_x)],
        [0, np.sin(angle_x), np.cos(angle_x)]
    ])
    R_y = np.array([
        [np.cos(angle_y), 0, np.sin(angle_y)],
        [0, 1, 0],
        [-np.sin(angle_y), 0, np.cos(angle_y)]
    ])
    R_z = np.array([
        [np.cos(angle_z), -np.sin(angle_z), 0],
        [np.sin(angle_z), np.cos(angle_z), 0],
        [0, 0, 1]
    ])
    
    R = R_z @ R_y @ R_x
    t = np.random.uniform(-0.5, 0.5, size=3)
    
    transformation = np.eye(4)
    transformation[:3, :3] = R
    transformation[:3, 3] = t
    
    return transformation, angle_x, angle_y, angle_z, t


def add_noise(pcd, noise_std=0.01):
    points = np.asarray(pcd.points)
    noise = np.random.normal(0, noise_std, points.shape)
    pcd.points = o3d.utility.Vector3dVector(points + noise)
    return pcd


def main():
    print("生成测试点云数据...")
    
    source_pcd = generate_bunny_point_cloud(num_points=8000)
    source_pcd = add_noise(source_pcd, noise_std=0.005)
    
    transformation, angle_x, angle_y, angle_z, t = generate_random_transform()
    
    print(f"\n真实变换:")
    print(f"旋转角 (X, Y, Z): {np.degrees(angle_x):.2f}°, {np.degrees(angle_y):.2f}°, {np.degrees(angle_z):.2f}°")
    print(f"平移向量: {t}")
    print(f"变换矩阵:\n{transformation}")
    
    target_pcd = o3d.geometry.PointCloud()
    target_points = np.asarray(source_pcd.points) @ transformation[:3, :3].T + transformation[:3, 3]
    target_pcd.points = o3d.utility.Vector3dVector(target_points)
    
    idx = np.random.permutation(len(target_pcd.points))
    target_pcd.points = o3d.utility.Vector3dVector(np.asarray(target_pcd.points)[idx])
    
    target_pcd = add_noise(target_pcd, noise_std=0.005)
    
    o3d.io.write_point_cloud("source.ply", source_pcd)
    o3d.io.write_point_cloud("target.ply", target_pcd)
    np.savetxt("ground_truth_transformation.txt", transformation, fmt='%.8f')
    
    print(f"\n源点云已保存: source.ply ({len(source_pcd.points)} 点)")
    print(f"目标点云已保存: target.ply ({len(target_pcd.points)} 点)")
    print(f"真实变换矩阵已保存: ground_truth_transformation.txt")
    
    source_pcd.paint_uniform_color([1, 0.706, 0])
    target_pcd.paint_uniform_color([0, 0.651, 0.929])
    o3d.visualization.draw_geometries(
        [source_pcd, target_pcd],
        window_name="测试数据: 源点云(黄) vs 目标点云(蓝)",
        width=800, height=600
    )


if __name__ == "__main__":
    main()
