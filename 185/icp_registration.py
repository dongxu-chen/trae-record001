import numpy as np
import open3d as o3d
from scipy.spatial import KDTree
import copy
import time
import os
from collections import defaultdict


def load_point_cloud(file_path):
    pcd = o3d.io.read_point_cloud(file_path)
    print(f"加载点云: {file_path}")
    print(f"原始点数: {len(pcd.points)}")
    return pcd


def remove_outliers(pcd, method='statistical', nb_neighbors=20, std_ratio=2.0,
                    radius=0.1, min_neighbors=5):
    print(f"\n移除离群点，方法: {method}")
    original_num = len(pcd.points)
    
    if method == 'statistical':
        cl, ind = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors, std_ratio=std_ratio
        )
        pcd_clean = pcd.select_by_index(ind)
    elif method == 'radius':
        cl, ind = pcd.remove_radius_outlier(
            nb_points=min_neighbors, radius=radius
        )
        pcd_clean = pcd.select_by_index(ind)
    elif method == 'combined':
        cl, ind = pcd.remove_statistical_outlier(
            nb_neighbors=nb_neighbors, std_ratio=std_ratio
        )
        pcd_temp = pcd.select_by_index(ind)
        cl, ind = pcd_temp.remove_radius_outlier(
            nb_points=min_neighbors, radius=radius
        )
        pcd_clean = pcd_temp.select_by_index(ind)
    else:
        raise ValueError(f"未知的离群点移除方法: {method}")
    
    removed_num = original_num - len(pcd_clean.points)
    print(f"移除离群点: {removed_num} ({removed_num/original_num*100:.2f}%)")
    print(f"剩余点数: {len(pcd_clean.points)}")
    
    return pcd_clean


def voxel_downsample(pcd, voxel_size=0.05):
    down_pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    print(f"降采样后点数: {len(down_pcd.points)} (体素大小: {voxel_size})")
    return down_pcd


def compute_normals(pcd, radius=None, max_nn=30):
    if radius is None:
        radius = estimate_point_density(pcd) * 5
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
    )
    return pcd


def estimate_point_density(pcd, num_samples=1000):
    points = np.asarray(pcd.points)
    if len(points) < num_samples:
        num_samples = len(points)
    
    indices = np.random.choice(len(points), num_samples, replace=False)
    sample_points = points[indices]
    
    tree = KDTree(points)
    distances, _ = tree.query(sample_points, k=6)
    avg_distance = np.mean(distances[:, 1:])
    
    print(f"估计点云平均间距: {avg_distance:.6f}")
    return avg_distance


def compute_fpfh_features(pcd, voxel_size):
    radius_normal = voxel_size * 5
    radius_feature = voxel_size * 10
    
    print(f"计算FPFH特征...")
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100)
    )
    return pcd_fpfh


def ransac_global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size):
    distance_threshold = voxel_size * 2.0
    
    print(f"\n开始RANSAC全局配准...")
    print(f"距离阈值: {distance_threshold:.6f}")
    
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh,
        mutual_filter=True,
        max_correspondence_distance=distance_threshold,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        ransac_n=4,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold)
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(4000000, 500)
    )
    
    print(f"RANSAC完成，内点数量: {int(np.sum(result.correspondence_set[:, 0] >= 0))}")
    print(f"初始变换矩阵:\n{result.transformation}")
    
    return result.transformation


def adaptive_search_radius(source_points, target_points, base_radius, density_scale=1.5):
    tree_source = KDTree(source_points)
    distances_source, _ = tree_source.query(source_points, k=6)
    local_density_source = np.mean(distances_source[:, 1:], axis=1)
    
    tree_target = KDTree(target_points)
    distances_target, _ = tree_target.query(target_points, k=6)
    local_density_target = np.mean(distances_target[:, 1:], axis=1)
    
    avg_density = (np.mean(local_density_source) + np.mean(local_density_target)) / 2
    adaptive_radius = base_radius * avg_density * density_scale
    
    return max(adaptive_radius, base_radius * 0.5)


def find_correspondences_adaptive(source_points, target_points, base_radius, use_adaptive=True):
    if use_adaptive:
        max_correspondence_distance = adaptive_search_radius(
            source_points, target_points, base_radius
        )
    else:
        max_correspondence_distance = base_radius
    
    tree = KDTree(target_points)
    distances, indices = tree.query(source_points, distance_upper_bound=max_correspondence_distance)
    
    valid_mask = distances < max_correspondence_distance
    source_corr = source_points[valid_mask]
    target_corr = target_points[indices[valid_mask]]
    
    return source_corr, target_corr, valid_mask, max_correspondence_distance


def compute_transformation_svd(source_corr, target_corr):
    source_centroid = np.mean(source_corr, axis=0)
    target_centroid = np.mean(target_corr, axis=0)
    
    source_centered = source_corr - source_centroid
    target_centered = target_corr - target_centroid
    
    H = source_centered.T @ target_centered
    
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = Vt.T @ U.T
    
    t = target_centroid - R @ source_centroid
    
    transformation = np.eye(4)
    transformation[:3, :3] = R
    transformation[:3, 3] = t
    
    return transformation


def icp_registration(source, target, base_correspondence_distance=0.05, 
                     max_iterations=50, tolerance=1e-6, use_adaptive_radius=True,
                     initial_transformation=None):
    print("\n开始ICP配准...")
    print(f"基础对应距离: {base_correspondence_distance}")
    print(f"最大迭代次数: {max_iterations}")
    print(f"自适应搜索半径: {'开启' if use_adaptive_radius else '关闭'}")
    
    source_points = np.asarray(source.points)
    target_points = np.asarray(target.points)
    
    if initial_transformation is not None:
        transformation = initial_transformation.copy()
        print("使用初始变换矩阵")
    else:
        transformation = np.eye(4)
    
    transformation_history = [transformation.copy()]
    rmse_history = []
    radius_history = []
    
    prev_rmse = float('inf')
    
    for iteration in range(max_iterations):
        source_transformed = source_points @ transformation[:3, :3].T + transformation[:3, 3]
        
        source_corr, target_corr, valid_mask, used_radius = find_correspondences_adaptive(
            source_transformed, target_points, base_correspondence_distance, use_adaptive_radius
        )
        
        if len(source_corr) < 3:
            print(f"迭代 {iteration}: 对应点不足，停止迭代")
            break
        
        delta_transform = compute_transformation_svd(source_corr, target_corr)
        transformation = delta_transform @ transformation
        
        rmse = np.sqrt(np.mean(np.sum((source_corr @ delta_transform[:3, :3].T + 
                                       delta_transform[:3, 3] - target_corr) ** 2, axis=1)))
        
        rmse_change = abs(prev_rmse - rmse)
        print(f"迭代 {iteration + 1:3d}: RMSE = {rmse:.6f}, 对应点数 = {len(source_corr)}, "
              f"搜索半径 = {used_radius:.6f}, RMSE变化 = {rmse_change:.8f}")
        
        transformation_history.append(transformation.copy())
        rmse_history.append(rmse)
        radius_history.append(used_radius)
        
        if rmse_change < tolerance and iteration > 3:
            print(f"收敛于迭代 {iteration + 1}")
            break
            
        prev_rmse = rmse
    
    print("\n配准完成!")
    print(f"最终变换矩阵:\n{transformation}")
    
    history = {
        'transformations': transformation_history,
        'rmse': rmse_history,
        'radii': radius_history
    }
    
    return transformation, rmse, history


def evaluate_registration_advanced(source, target, transformation, threshold=None):
    if threshold is None:
        threshold = estimate_point_density(target) * 3
        
    source_transformed = copy.deepcopy(source)
    source_transformed.transform(transformation)
    
    source_points = np.asarray(source_transformed.points)
    target_points = np.asarray(target.points)
    
    tree = KDTree(target_points)
    distances, _ = tree.query(source_points)
    
    rmse = np.sqrt(np.mean(distances ** 2))
    mean_distance = np.mean(distances)
    median_distance = np.median(distances)
    std_distance = np.std(distances)
    max_distance = np.max(distances)
    
    inlier_mask = distances < threshold
    inlier_ratio = np.sum(inlier_mask) / len(distances)
    
    source_inliers = source_points[inlier_mask]
    target_tree = KDTree(target_points)
    target_inlier_mask = np.zeros(len(target_points), dtype=bool)
    
    for point in source_inliers:
        dist, idx = target_tree.query(point, distance_upper_bound=threshold)
        if dist < threshold:
            target_inlier_mask[idx] = True
    
    overlap_coverage = np.sum(target_inlier_mask) / len(target_points)
    
    print(f"\n{'='*60}")
    print("配准精度评估报告")
    print(f"{'='*60}")
    print(f"评估阈值: {threshold:.6f}")
    print(f"\n距离统计:")
    print(f"  RMSE:                    {rmse:.6f}")
    print(f"  平均距离:                {mean_distance:.6f}")
    print(f"  中位距离:                {median_distance:.6f}")
    print(f"  距离标准差:              {std_distance:.6f}")
    print(f"  最大距离:                {max_distance:.6f}")
    print(f"\n重叠度分析:")
    print(f"  源点云内点比例:          {inlier_ratio:.4f} ({np.sum(inlier_mask)}/{len(distances)})")
    print(f"  目标点云覆盖率:          {overlap_coverage:.4f} ({np.sum(target_inlier_mask)}/{len(target_points)})")
    print(f"  综合重叠度:              {(inlier_ratio + overlap_coverage) / 2:.4f}")
    print(f"{'='*60}")
    
    metrics = {
        'rmse': rmse,
        'mean_distance': mean_distance,
        'median_distance': median_distance,
        'std_distance': std_distance,
        'max_distance': max_distance,
        'inlier_ratio': inlier_ratio,
        'overlap_coverage': overlap_coverage,
        'overall_overlap': (inlier_ratio + overlap_coverage) / 2,
        'threshold': threshold
    }
    
    return metrics


def evaluate_registration(source, target, transformation, threshold=None):
    metrics = evaluate_registration_advanced(source, target, transformation, threshold)
    return metrics['inlier_ratio'], metrics['mean_distance'], metrics['std_distance']


def pairwise_registration(source, target, voxel_size, use_fpfh=True, 
                          base_correspondence_distance=None, max_iterations=50,
                          use_adaptive_radius=True):
    print(f"\n{'='*60}")
    print("两两配准")
    print(f"{'='*60}")
    
    source_down = voxel_downsample(source, voxel_size)
    target_down = voxel_downsample(target, voxel_size)
    
    source_down = compute_normals(source_down)
    target_down = compute_normals(target_down)
    
    point_density = estimate_point_density(source_down)
    if base_correspondence_distance is None:
        base_correspondence_distance = point_density * 5
    
    initial_transformation = None
    if use_fpfh:
        source_fpfh = compute_fpfh_features(source_down, voxel_size)
        target_fpfh = compute_fpfh_features(target_down, voxel_size)
        initial_transformation = ransac_global_registration(
            source_down, target_down, source_fpfh, target_fpfh, voxel_size
        )
    
    transformation, rmse, history = icp_registration(
        source_down, target_down,
        base_correspondence_distance=base_correspondence_distance,
        max_iterations=max_iterations,
        use_adaptive_radius=use_adaptive_radius,
        initial_transformation=initial_transformation
    )
    
    metrics = evaluate_registration_advanced(source_down, target_down, transformation)
    
    return transformation, metrics, history


def multi_view_registration(point_clouds, voxel_size=0.05, use_fpfh=True,
                            base_correspondence_distance=None, max_iterations=50,
                            use_adaptive_radius=True, reference_idx=0):
    print(f"\n{'='*60}")
    print("多视角点云配准")
    print(f"{'='*60}")
    print(f"输入点云数量: {len(point_clouds)}")
    print(f"参考点云索引: {reference_idx}")
    
    num_clouds = len(point_clouds)
    transformations = [np.eye(4) for _ in range(num_clouds)]
    pairwise_metrics = {}
    all_histories = {}
    
    for i in range(num_clouds):
        if i == reference_idx:
            continue
        
        print(f"\n{'─'*60}")
        print(f"配准点云 {i} -> 参考点云 {reference_idx}")
        print(f"{'─'*60}")
        
        transformation, metrics, history = pairwise_registration(
            point_clouds[i], point_clouds[reference_idx],
            voxel_size=voxel_size,
            use_fpfh=use_fpfh,
            base_correspondence_distance=base_correspondence_distance,
            max_iterations=max_iterations,
            use_adaptive_radius=use_adaptive_radius
        )
        
        transformations[i] = transformation
        pairwise_metrics[(i, reference_idx)] = metrics
        all_histories[(i, reference_idx)] = history
    
    print(f"\n{'='*60}")
    print("多视角配准完成")
    print(f"{'='*60}")
    print(f"\n配准结果汇总:")
    for (i, j), metrics in pairwise_metrics.items():
        print(f"  点云 {i} -> 点云 {j}:")
        print(f"    RMSE = {metrics['rmse']:.6f}, 重叠度 = {metrics['overall_overlap']:.4f}")
    
    return transformations, pairwise_metrics, all_histories


def merge_point_clouds(point_clouds, transformations, voxel_size=None):
    print(f"\n融合多视角点云...")
    
    merged_pcd = o3d.geometry.PointCloud()
    all_points = []
    all_colors = []
    
    colors = [
        [1, 0.706, 0], [0, 0.651, 0.929], [0.929, 0.490, 0.192],
        [0.494, 0.184, 0.556], [0.466, 0.674, 0.188], [0.301, 0.745, 0.933]
    ]
    
    for i, (pcd, transform) in enumerate(zip(point_clouds, transformations)):
        pcd_transformed = copy.deepcopy(pcd)
        pcd_transformed.transform(transform)
        
        color = colors[i % len(colors)]
        pcd_transformed.paint_uniform_color(color)
        
        all_points.append(np.asarray(pcd_transformed.points))
        all_colors.append(np.asarray(pcd_transformed.colors))
    
    merged_pcd.points = o3d.utility.Vector3dVector(np.vstack(all_points))
    merged_pcd.colors = o3d.utility.Vector3dVector(np.vstack(all_colors))
    
    print(f"融合前总点数: {len(merged_pcd.points)}")
    
    if voxel_size is not None:
        merged_pcd = merged_pcd.voxel_down_sample(voxel_size=voxel_size)
        print(f"融合后点数 (体素滤波): {len(merged_pcd.points)}")
    else:
        print(f"融合后点数: {len(merged_pcd.points)}")
    
    return merged_pcd


def create_animation_visualization(source, target, history, source_color=[1, 0.706, 0], 
                                   target_color=[0, 0.651, 0.929]):
    print("\n创建配准迭代动画...")
    print("按 → 键查看下一帧，按 ← 键查看上一帧，按 ESC 退出")
    
    target_pcd = copy.deepcopy(target)
    target_pcd.paint_uniform_color(target_color)
    
    source_pcd = copy.deepcopy(source)
    
    transformations = history['transformations']
    rmse_values = history['rmse']
    
    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window(window_name="ICP迭代动画", width=1000, height=700)
    
    current_frame = [0]
    
    source_pcd.paint_uniform_color(source_color)
    vis.add_geometry(source_pcd)
    vis.add_geometry(target_pcd)
    
    def update_frame(vis):
        source_pcd_temp = copy.deepcopy(source)
        source_pcd_temp.paint_uniform_color(source_color)
        source_pcd_temp.transform(transformations[current_frame[0]])
        
        source_pcd.points = source_pcd_temp.points
        source_pcd.colors = source_pcd_temp.colors
        
        vis.update_geometry(source_pcd)
        
        if current_frame[0] < len(rmse_values):
            rmse_text = f"迭代 {current_frame[0]}/{len(transformations)-1}, RMSE: {rmse_values[current_frame[0]]:.6f}"
        else:
            rmse_text = f"迭代 {current_frame[0]}/{len(transformations)-1} (初始)"
        print(f"\r{rmse_text}", end="")
        
        return False
    
    def next_frame(vis):
        if current_frame[0] < len(transformations) - 1:
            current_frame[0] += 1
            update_frame(vis)
        return False
    
    def prev_frame(vis):
        if current_frame[0] > 0:
            current_frame[0] -= 1
            update_frame(vis)
        return False
    
    def auto_play(vis):
        print("\n自动播放中... 按任意键暂停")
        for i in range(len(transformations)):
            current_frame[0] = i
            update_frame(vis)
            vis.poll_events()
            vis.update_renderer()
            time.sleep(0.3)
        print("\n播放完成")
        return False
    
    vis.register_key_callback(262, next_frame)
    vis.register_key_callback(263, prev_frame)
    vis.register_key_callback(32, auto_play)
    
    print("\n控制说明:")
    print("  → (右箭头): 下一帧")
    print("  ← (左箭头): 上一帧")
    print("  空格: 自动播放")
    print("  ESC: 退出")
    
    update_frame(vis)
    vis.run()
    vis.destroy_window()
    print()


def visualize_multi_view_registration(point_clouds, transformations, reference_idx=0):
    print(f"\n多视角配准结果可视化...")
    
    colors = [
        [1, 0.706, 0], [0, 0.651, 0.929], [0.929, 0.490, 0.192],
        [0.494, 0.184, 0.556], [0.466, 0.674, 0.188], [0.301, 0.745, 0.933]
    ]
    
    pcds_before = []
    pcds_after = []
    
    for i, (pcd, transform) in enumerate(zip(point_clouds, transformations)):
        color = colors[i % len(colors)]
        
        pcd_before = copy.deepcopy(pcd)
        pcd_before.paint_uniform_color(color)
        pcds_before.append(pcd_before)
        
        pcd_after = copy.deepcopy(pcd)
        pcd_after.transform(transform)
        pcd_after.paint_uniform_color(color)
        pcds_after.append(pcd_after)
    
    print("\n配准前可视化 (原始位置)...")
    o3d.visualization.draw_geometries(
        pcds_before,
        window_name="配准前: 多视角点云 (原始位置)",
        width=1000, height=700
    )
    
    print("配准后可视化 (对齐到参考坐标系)...")
    o3d.visualization.draw_geometries(
        pcds_after,
        window_name=f"配准后: 对齐到点云 {reference_idx}",
        width=1000, height=700
    )
    
    merged_pcd = merge_point_clouds(point_clouds, transformations)
    print("融合结果可视化...")
    o3d.visualization.draw_geometries(
        [merged_pcd],
        window_name="融合点云",
        width=1000, height=700
    )
    
    return merged_pcd


def visualize_registration(source, target, transformation, source_color=[1, 0.706, 0], 
                           target_color=[0, 0.651, 0.929]):
    source_before = copy.deepcopy(source)
    source_after = copy.deepcopy(source)
    target_pcd = copy.deepcopy(target)
    
    source_before.paint_uniform_color(source_color)
    source_after.paint_uniform_color([1, 0, 0])
    target_pcd.paint_uniform_color(target_color)
    
    source_after.transform(transformation)
    
    print("\n可视化说明:")
    print(f"黄色: 源点云 (配准前)")
    print(f"红色: 源点云 (配准后)")
    print(f"蓝色: 目标点云")
    
    o3d.visualization.draw_geometries(
        [source_before, target_pcd],
        window_name="配准前: 源点云(黄) vs 目标点云(蓝)",
        width=800, height=600
    )
    
    o3d.visualization.draw_geometries(
        [source_after, target_pcd],
        window_name="配准后: 源点云(红) vs 目标点云(蓝)",
        width=800, height=600
    )
    
    o3d.visualization.draw_geometries(
        [source_before, source_after, target_pcd],
        window_name="对比: 配准前(黄) vs 配准后(红) vs 目标(蓝)",
        width=800, height=600
    )


def save_transformation(transformation, output_path):
    np.savetxt(output_path, transformation, fmt='%.8f')
    print(f"\n变换矩阵已保存到: {output_path}")


def save_transformations(transformations, output_dir="transformations"):
    os.makedirs(output_dir, exist_ok=True)
    for i, transform in enumerate(transformations):
        output_path = os.path.join(output_dir, f"transformation_{i:03d}.txt")
        np.savetxt(output_path, transform, fmt='%.8f')
        print(f"变换矩阵 {i} 已保存到: {output_path}")


def preprocess_point_cloud(pcd, voxel_size=0.05, remove_outliers_flag=True,
                          outlier_method='statistical', nb_neighbors=20, std_ratio=2.0):
    print(f"\n预处理点云...")
    
    if remove_outliers_flag:
        pcd = remove_outliers(pcd, method=outlier_method, 
                              nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    
    pcd = voxel_downsample(pcd, voxel_size)
    pcd = compute_normals(pcd)
    
    return pcd


def main(source_path, target_path, voxel_size=0.05, base_correspondence_distance=None,
         max_iterations=50, use_fpfh=True, use_adaptive_radius=True,
         remove_outliers_flag=True, outlier_method='statistical',
         output_transform_path="transformation.txt"):
    
    source = load_point_cloud(source_path)
    target = load_point_cloud(target_path)
    
    if remove_outliers_flag:
        print("\n" + "="*60)
        print("预处理: 离群点移除")
        print("="*60)
        source = remove_outliers(source, method=outlier_method)
        target = remove_outliers(target, method=outlier_method)
    
    source_down = voxel_downsample(source, voxel_size)
    target_down = voxel_downsample(target, voxel_size)
    
    point_density = estimate_point_density(source_down)
    
    if base_correspondence_distance is None:
        base_correspondence_distance = point_density * 5
        print(f"自动设置基础对应距离: {base_correspondence_distance:.6f}")
    
    source_down = compute_normals(source_down)
    target_down = compute_normals(target_down)
    
    initial_transformation = None
    if use_fpfh:
        print("\n" + "="*60)
        print("阶段1: FPFH特征匹配 + RANSAC初始变换估计")
        print("="*60)
        
        source_fpfh = compute_fpfh_features(source_down, voxel_size)
        target_fpfh = compute_fpfh_features(target_down, voxel_size)
        
        initial_transformation = ransac_global_registration(
            source_down, target_down, source_fpfh, target_fpfh, voxel_size
        )
        
        print("\n初始变换评估:")
        evaluate_registration(source_down, target_down, initial_transformation)
    
    print("\n" + "="*60)
    print("阶段2: ICP精细配准")
    print("="*60)
    
    transformation, rmse, history = icp_registration(
        source_down, target_down,
        base_correspondence_distance=base_correspondence_distance,
        max_iterations=max_iterations,
        use_adaptive_radius=use_adaptive_radius,
        initial_transformation=initial_transformation
    )
    
    evaluate_registration_advanced(source_down, target_down, transformation)
    
    save_transformation(transformation, output_transform_path)
    
    print("\n" + "="*60)
    print("阶段3: 可视化")
    print("="*60)
    
    create_animation_visualization(source_down, target_down, history)
    
    visualize_registration(source_down, target_down, transformation)
    
    return transformation, history


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ICP点云配准 (完整版)")
    parser.add_argument("--source", required=True, help="源点云文件路径 (PLY格式)")
    parser.add_argument("--target", required=True, help="目标点云文件路径 (PLY格式)")
    parser.add_argument("--voxel_size", type=float, default=0.05, help="体素滤波大小")
    parser.add_argument("--base_dist", type=float, default=None, help="基础对应距离 (默认自动估计)")
    parser.add_argument("--max_iter", type=int, default=50, help="最大迭代次数")
    parser.add_argument("--no_fpfh", action="store_true", help="禁用FPFH初始变换估计")
    parser.add_argument("--no_adaptive", action="store_true", help="禁用自适应搜索半径")
    parser.add_argument("--no_outlier_removal", action="store_true", help="禁用离群点移除")
    parser.add_argument("--outlier_method", type=str, default="statistical", 
                       choices=["statistical", "radius", "combined"], help="离群点移除方法")
    parser.add_argument("--output", type=str, default="transformation.txt", help="变换矩阵输出路径")
    
    args = parser.parse_args()
    
    main(
        source_path=args.source,
        target_path=args.target,
        voxel_size=args.voxel_size,
        base_correspondence_distance=args.base_dist,
        max_iterations=args.max_iter,
        use_fpfh=not args.no_fpfh,
        use_adaptive_radius=not args.no_adaptive,
        remove_outliers_flag=not args.no_outlier_removal,
        outlier_method=args.outlier_method,
        output_transform_path=args.output
    )
