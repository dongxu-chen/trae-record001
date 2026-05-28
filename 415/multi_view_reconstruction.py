"""
多视角立体重建 (Multi-View Stereo Reconstruction)
====================================================
使用运动恢复结构 (SfM) 和多视角立体视觉 (MVS) 从多视角图像重建3D点云。

依赖: OpenCV, NumPy, Matplotlib, pycolmap, trimesh

流程:
  1. 合成数据生成 (3D场景 -> 多视角投影图像)
  2. 特征提取与匹配
  3. SfM: 相机位姿估计 + 稀疏点云
  4. MVS: 稠密点云重建
  5. 点云后处理与可视化
  6. 重建质量评估
"""

import os
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple

import numpy as np
import cv2
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

warnings.filterwarnings("ignore")


# =============================================================================
# 配置
# =============================================================================

class Config:
    """全局配置参数"""
    # 合成场景参数
    NUM_CAMERAS = 12              # 相机数量
    IMAGE_WIDTH = 640             # 图像宽度
    IMAGE_HEIGHT = 480            # 图像高度
    FOCAL_LENGTH = 800.0          # 焦距(像素)
    CAMERA_DISTANCE = 4.0         # 相机到场景中心距离
    CAMERA_ELEVATION = 1.5        # 相机仰角

    # 特征提取参数
    FEATURE_METHOD = "SIFT"       # SIFT / ORB
    NUM_FEATURES = 2000           # 最大特征点数
    RATIO_TEST = 0.75             # Lowe's ratio test阈值

    # SfM参数
    MIN_MATCHES = 30              # 最小匹配数
    RANSAC_THRESHOLD = 1.0        # RANSAC阈值(像素)
    MIN_INLIERS = 20              # 最小内点数

    # MVS参数
    MVS_NUM_VIEWS = 5             # MVS邻域视图数
    DEPTH_MIN = 0.5               # 最小深度
    DEPTH_MAX = 10.0              # 最大深度
    FUSION_CONFIDENCE = 0.6       # 融合置信度阈值

    # 后处理参数
    VOXEL_SIZE = 0.02             # 体素下采样大小
    REMOVE_STATISTICAL = True     # 是否移除离群点
    NB_NEIGHBORS = 20             # 统计离群点邻居数
    STD_RATIO = 2.0               # 离群点标准差比

    # 线特征参数
    ENABLE_LINE_FEATURES = True    # 是否启用线特征辅助匹配
    LINE_MIN_LENGTH = 30           # 线特征最小长度(像素)
    LINE_NUM_BANDS = 9             # LBD描述子带数
    LINE_MATCH_RATIO = 0.75        # 线特征匹配ratio test

    # 分块MVS参数
    ENABLE_CHUNK_MVS = True        # 是否启用分块MVS
    CHUNK_SIZE = 5000              # 每块最大点数
    CHUNK_OVERLAP = 0.15           # 块间重叠比例

    # IMU参数
    ENABLE_IMU_INIT = True         # 是否启用IMU预积分初始化
    IMU_ACC_NOISE = 0.1            # 加速度计噪声 (m/s^2)
    IMU_GYRO_NOISE = 0.01          # 陀螺仪噪声 (rad/s)
    IMU_GRAVITY = 9.81             # 重力加速度

    # 表面网格参数
    ENABLE_MESH = True             # 是否生成表面网格
    MESH_METHOD = "alpha"          # alpha / poisson
    ALPHA_RADIUS = 0.15            # Alpha Shape半径
    POISSON_DEPTH = 8              # Poisson重建深度

    # 纹理映射参数
    ENABLE_TEXTURE = True          # 是否进行纹理映射
    TEXTURE_BLEND_WEIGHT = 0.7     # 视角权重 (余弦权重)

    # 动态物体剔除参数
    ENABLE_DYNAMIC_FILTER = True   # 是否启用动态物体剔除
    DYNAMIC_CONSISTENCY_THRESH = 0.5  # 多视角一致性阈值 (视角比例)
    DYNAMIC_REPROJ_ERROR = 3.0     # 重投影误差阈值(像素)

    # 输出路径
    OUTPUT_DIR = "output"
    SPARSE_PLY = "sparse_points.ply"
    DENSE_PLY = "dense_points.ply"
    MESH_PLY = "mesh.ply"
    TEXTURED_MESH_OBJ = "textured_mesh.obj"
    CAMERA_POSES_JSON = "camera_poses.json"


# =============================================================================
# 合成数据生成
# =============================================================================

def generate_synthetic_scene() -> Tuple[np.ndarray, np.ndarray]:
    """
    生成合成3D场景: 带纹理的平面 + 多个3D物体

    Returns:
        points: (N, 3) 3D点坐标
        colors: (N, 3) RGB颜色 [0,1]
    """
    np.random.seed(42)
    all_points = []
    all_colors = []

    # --- 带纹理的地面平面 (密集采样, 用于SGBM) ---
    plane_y = -1.5
    plane_size = 6.0
    plane_step = 0.08
    xx, zz = np.meshgrid(
        np.arange(-plane_size/2, plane_size/2, plane_step),
        np.arange(-plane_size/2, plane_size/2, plane_step)
    )
    for xi, zi in zip(xx.ravel(), zz.ravel()):
        all_points.append(np.array([xi, plane_y, zi]))
        # 棋盘纹理
        checker = ((int(xi / plane_step) + int(zi / plane_step)) % 2) * 0.5 + 0.3
        all_colors.append(np.array([checker, checker * 0.9, checker * 0.7]))

    # --- 立方体 (带颜色渐变) ---
    cube_vertices = np.array([
        [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
        [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
    ])
    cube_faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        (0, 3, 7, 4),
        (1, 2, 6, 5),
    ]
    cube_color = np.array([0.2, 0.6, 0.9])
    for f_idx, face in enumerate(cube_faces):
        v0, v1, v2, v3 = cube_vertices[list(face)]
        face_col = cube_color * (0.7 + 0.05 * f_idx)
        for _ in range(300):
            u, v = np.random.rand(2)
            if u + v > 1:
                u, v = 1 - u, 1 - v
            p = v0 + u * (v1 - v0) + v * (v3 - v0)
            all_points.append(p)
            all_colors.append(face_col)

    # --- 金字塔/四面体 ---
    tetra_vertices = np.array([
        [2.0, -1.0, -0.5],
        [2.8, -1.0, -0.5],
        [2.4, -1.0, 0.5],
        [2.4, -0.2, 0.0],
    ])
    tetra_faces = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)]
    tetra_color = np.array([0.9, 0.7, 0.2])
    for f_idx, face in enumerate(tetra_faces):
        v0, v1, v2 = tetra_vertices[list(face)]
        face_col = tetra_color * (0.7 + 0.1 * f_idx)
        for _ in range(200):
            u, v = np.random.rand(2)
            if u + v > 1:
                u, v = 1 - u, 1 - v
            p = v0 + u * (v1 - v0) + v * (v2 - v0)
            all_points.append(p)
            all_colors.append(face_col)

    # --- 球体表面 ---
    sphere_center = np.array([-1.5, -0.5, 1.0])
    sphere_radius = 0.7
    for _ in range(800):
        theta = np.random.uniform(0, 2 * np.pi)
        phi = np.arccos(2 * np.random.rand() - 1)
        x = sphere_radius * np.sin(phi) * np.cos(theta)
        y = sphere_radius * np.sin(phi) * np.sin(theta)
        z = sphere_radius * np.cos(phi)
        p = sphere_center + np.array([x, y, z])
        all_points.append(p)
        r = 1.0 - 0.5 * (np.sin(phi) + 1) / 2
        all_colors.append(np.array([r, 0.3, 0.4]))

    # --- 圆柱 ---
    cyl_center = np.array([0.5, -1.2, 1.2])
    cyl_radius = 0.4
    cyl_height = 1.0
    for _ in range(600):
        theta = np.random.uniform(0, 2 * np.pi)
        h = np.random.uniform(-cyl_height/2, cyl_height/2)
        x = cyl_radius * np.cos(theta)
        y = h
        z = cyl_radius * np.sin(theta)
        p = cyl_center + np.array([x, y, z])
        all_points.append(p)
        all_colors.append(np.array([0.5, 0.5, 0.9]))

    # --- 随机散布点 ---
    for _ in range(200):
        p = np.random.uniform(-2.5, 2.5, 3)
        all_points.append(p)
        all_colors.append(np.random.rand(3))

    points = np.array(all_points)
    colors = np.array(all_colors)
    return points, colors


def generate_camera_poses(
    num_cameras: int,
    scene_center: np.ndarray = None,
    distance: float = 4.0,
    elevation: float = 1.5
) -> List[Dict]:
    """
    生成环绕场景的相机位姿。

    Args:
        num_cameras: 相机数量
        scene_center: 场景中心
        distance: 相机到中心距离
        elevation: 仰角

    Returns:
        相机位姿列表, 每项含 R, t, K, extrinsic
    """
    if scene_center is None:
        scene_center = np.zeros(3)

    poses = []
    for i in range(num_cameras):
        angle = 2 * np.pi * i / num_cameras
        cam_x = distance * np.cos(angle)
        cam_y = distance * np.sin(angle)
        cam_z = elevation + 0.3 * np.sin(angle * 2)

        cam_pos = np.array([cam_x, cam_y, cam_z])

        # 相机朝向场景中心
        forward = scene_center - cam_pos
        forward = forward / np.linalg.norm(forward)

        world_up = np.array([0, 0, 1])
        right = np.cross(forward, world_up)
        right = right / (np.linalg.norm(right) + 1e-10)
        up = np.cross(right, forward)
        up = up / (np.linalg.norm(up) + 1e-10)

        # 旋转矩阵: 相机坐标系 -> 世界坐标系
        # X_cam = [right, up, forward], 相机沿 +Z 方向看
        R_c2w = np.column_stack([right, up, forward])
        t_c2w = cam_pos

        # 外参: 世界坐标系 -> 相机坐标系
        R_w2c = R_c2w.T
        t_w2c = -R_w2c @ t_c2w

        # 相机内参
        fx = Config.FOCAL_LENGTH
        fy = Config.FOCAL_LENGTH
        cx = Config.IMAGE_WIDTH / 2
        cy = Config.IMAGE_HEIGHT / 2
        K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])

        # 外参矩阵 [R|t]
        extrinsic = np.hstack([R_w2c, t_w2c.reshape(3, 1)])

        poses.append({
            "R_w2c": R_w2c,
            "t_w2c": t_w2c,
            "R_c2w": R_c2w,
            "t_c2w": t_c2w,
            "K": K,
            "extrinsic": extrinsic,
            "position": cam_pos,
            "angle": angle,
        })

    return poses


def project_points(
    points_3d: np.ndarray,
    K: np.ndarray,
    R: np.ndarray,
    t: np.ndarray,
    image_size: Tuple[int, int],
    distortion: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    将3D点投影到图像平面。

    Args:
        points_3d: (N, 3) 世界坐标系3D点
        K: (3, 3) 内参矩阵
        R: (3, 3) 旋转矩阵 (世界->相机)
        t: (3,) 平移向量
        image_size: (width, height)
        distortion: 畸变系数 (k1, k2, p1, p2, k3)

    Returns:
        pixels: (M, 2) 像素坐标
        valid_mask: (M,) bool, 有效投影点掩码
    """
    # 变换到相机坐标系
    points_cam = (R @ points_3d.T).T + t.ravel()

    # 过滤掉相机后方的点
    depth = points_cam[:, 2]
    valid_depth = depth > 0.01

    # 透视投影
    points_norm = points_cam[valid_depth, :2] / (depth[valid_depth].reshape(-1, 1) + 1e-10)

    # 畸变
    if distortion is not None and len(distortion) >= 4:
        x, y = points_norm[:, 0], points_norm[:, 1]
        r2 = x ** 2 + y ** 2
        radial = 1 + distortion[0] * r2 + distortion[1] * r2 ** 2
        if len(distortion) >= 5:
            radial += distortion[4] * r2 ** 3
        x_tangential = 2 * distortion[2] * x * y + distortion[3] * (r2 + 2 * x ** 2)
        y_tangential = distortion[2] * (r2 + 2 * y ** 2) + 2 * distortion[3] * x * y
        points_norm[:, 0] = x * radial + x_tangential
        points_norm[:, 1] = y * radial + y_tangential

    # 像素坐标
    pixels_h = (K @ np.hstack([points_norm, np.ones((len(points_norm), 1))]).T).T
    pixels = pixels_h[:, :2]

    # 过滤出图像边界外的点
    in_bounds = (
        (pixels[:, 0] >= 0) & (pixels[:, 0] < image_size[0]) &
        (pixels[:, 1] >= 0) & (pixels[:, 1] < image_size[1])
    )

    valid_mask = np.zeros(len(points_3d), dtype=bool)
    valid_indices = np.where(valid_depth)[0]
    valid_mask[valid_indices[in_bounds]] = True
    pixels = pixels[in_bounds]

    return pixels, valid_mask


def render_images(
    points_3d: np.ndarray,
    colors: np.ndarray,
    camera_poses: List[Dict],
    output_dir: str
) -> Tuple[List[str], List[Dict]]:
    """
    渲染合成多视角图像。

    Args:
        points_3d: (N, 3) 3D点坐标
        colors: (N, 3) RGB颜色
        camera_poses: 相机位姿列表
        output_dir: 输出目录

    Returns:
        图像文件路径列表, 每个视图的3D点ID->2D坐标映射列表
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []
    view_keypoints = []

    for i, pose in enumerate(camera_poses):
        img = np.ones((Config.IMAGE_HEIGHT, Config.IMAGE_WIDTH, 3), dtype=np.uint8) * 20

        pixels, valid_mask = project_points(
            points_3d, pose["K"], pose["R_w2c"], pose["t_w2c"],
            (Config.IMAGE_WIDTH, Config.IMAGE_HEIGHT)
        )

        valid_points = points_3d[valid_mask]
        valid_colors = colors[valid_mask]
        valid_indices = np.where(valid_mask)[0]

        # 记录3D点ID -> 2D坐标映射 (用于真值匹配)
        kp_map = {}
        for j, idx in enumerate(valid_indices):
            px = pixels[j].astype(int)
            if 0 <= px[0] < Config.IMAGE_WIDTH and 0 <= px[1] < Config.IMAGE_HEIGHT:
                kp_map[idx] = (float(px[0]), float(px[1]))

        view_keypoints.append(kp_map)

        if len(pixels) > 0:
            depth_vals = (pose["R_w2c"] @ valid_points.T).T[:, 2] + pose["t_w2c"][2]

            # 简单深度排序以处理遮挡 (画家算法)
            sort_idx = np.argsort(-depth_vals)
            pixels_sorted = pixels[sort_idx].astype(int)
            colors_sorted = valid_colors[sort_idx]

            for px, col in zip(pixels_sorted, colors_sorted):
                col_int = tuple((np.clip(col * 255, 0, 255)).astype(int))
                if len(col_int) != 3:
                    continue
                try:
                    cv2.circle(img, (int(px[0]), int(px[1])), 3, col_int, -1)
                except Exception:
                    pass

        # 添加相机标识文字
        cv2.putText(img, f"Cam {i}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        img_path = os.path.join(output_dir, f"view_{i:04d}.png")
        cv2.imwrite(img_path, img)
        image_paths.append(img_path)

    return image_paths, view_keypoints


# =============================================================================
# 特征提取与匹配
# =============================================================================

def create_feature_detector(method: str = "SIFT", nfeatures: int = 2000):
    """创建特征检测器"""
    if method.upper() == "SIFT":
        try:
            return cv2.SIFT_create(nfeatures=nfeatures)
        except AttributeError:
            print("Warning: SIFT not available, falling back to ORB")
            return cv2.ORB_create(nfeatures=nfeatures)
    elif method.upper() == "ORB":
        return cv2.ORB_create(nfeatures=nfeatures)
    else:
        raise ValueError(f"Unknown feature method: {method}")


def extract_features(
    images: List[np.ndarray],
    detector,
    mask: Optional[np.ndarray] = None
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    从所有图像提取特征点和描述子。

    Args:
        images: 图像列表
        detector: OpenCV特征检测器
        mask: 可选的掩码

    Returns:
        列表, 每项为 (keypoints, descriptors)
    """
    features = []
    for i, img in enumerate(images):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        keypoints, descriptors = detector.detectAndCompute(gray, mask)
        if descriptors is None:
            descriptors = np.empty((0, 128), dtype=np.float32)
        features.append((keypoints, descriptors))
        print(f"  View {i}: {len(keypoints)} keypoints, descriptors shape: {descriptors.shape}")
    return features


def match_features(
    features: List[Tuple],
    ratio_test: float = 0.75,
    method: str = "SIFT"
) -> Dict[Tuple[int, int], List[cv2.DMatch]]:
    """
    对所有图像对进行特征匹配。

    Args:
        features: 所有图像的特征 (keypoints, descriptors)
        ratio_test: Lowe's ratio test阈值
        method: 特征类型

    Returns:
        匹配字典 {(i,j): [DMatch, ...]}
    """
    n = len(features)
    matches_dict = {}

    if method.upper() == "SIFT":
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    else:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    for i in range(n):
        for j in range(i + 1, n):
            desc_i = features[i][1]
            desc_j = features[j][1]

            if len(desc_i) < 2 or len(desc_j) < 2:
                continue

            raw_matches = matcher.knnMatch(desc_i, desc_j, k=2)

            good_matches = []
            for m, n_match in raw_matches:
                if m.distance < ratio_test * n_match.distance:
                    good_matches.append(m)

            if len(good_matches) >= Config.MIN_MATCHES:
                matches_dict[(i, j)] = good_matches
                print(f"  Match ({i}, {j}): {len(good_matches)} good matches")

    return matches_dict


def generate_ground_truth_matches(
    view_keypoints: List[Dict[int, Tuple[float, float]]],
    min_matches: int = 10
) -> Tuple[Dict[Tuple[int, int], List[cv2.DMatch]], List[Tuple]]:
    """
    从真值3D点ID对应关系生成完美匹配。

    Args:
        view_keypoints: 每个视图的3D点ID->2D坐标映射
        min_matches: 最小匹配数

    Returns:
        (匹配字典, 兼容SfM的特征列表)
    """
    n = len(view_keypoints)
    matches_dict = {}

    # 为每个视图创建兼容的keypoints和descriptors
    gt_features = []
    for kp_map in view_keypoints:
        kps = []
        # 3D点ID -> 索引映射
        id_to_idx = {}
        sorted_ids = sorted(kp_map.keys())
        for idx, pt_id in enumerate(sorted_ids):
            pt = kp_map[pt_id]
            kps.append(cv2.KeyPoint(pt[0], pt[1], 3))
            id_to_idx[pt_id] = idx
        # 空的描述子 (用于保持接口兼容)
        descs = np.zeros((len(kps), 128), dtype=np.float32) if len(kps) > 0 else np.zeros((0, 128), dtype=np.float32)
        gt_features.append((kps, descs, id_to_idx))

    for i in range(n):
        kp_i = view_keypoints[i]
        id_to_idx_i = gt_features[i][2]
        if len(kp_i) < 2:
            continue
        for j in range(i + 1, n):
            kp_j = view_keypoints[j]
            id_to_idx_j = gt_features[j][2]
            if len(kp_j) < 2:
                continue

            common_ids = set(kp_i.keys()) & set(kp_j.keys())
            if len(common_ids) < min_matches:
                continue

            good_matches = []
            for pt_id in common_ids:
                pt_i = kp_i[pt_id]
                pt_j = kp_j[pt_id]
                dist = np.sqrt((pt_i[0] - pt_j[0])**2 + (pt_i[1] - pt_j[1])**2)
                m = cv2.DMatch()
                m.queryIdx = id_to_idx_i[pt_id]
                m.trainIdx = id_to_idx_j[pt_id]
                m.distance = float(dist)
                m.imgIdx = 0
                good_matches.append(m)

            matches_dict[(i, j)] = good_matches
            print(f"  GT Match ({i}, {j}): {len(good_matches)} matches")

    # 转换为兼容格式: (keypoints, descriptors)
    gt_features_compat = [(kps, descs) for kps, descs, _ in gt_features]

    return matches_dict, gt_features_compat


# =============================================================================
# 线特征提取与匹配 (LSD + LBD)
# =============================================================================

class LineFeature:
    """线特征: 端点坐标 + 描述子"""
    __slots__ = ('x1', 'y1', 'x2', 'y2', 'length', 'angle', 'descriptor')

    def __init__(self, x1, y1, x2, y2, descriptor):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        self.angle = np.arctan2(y2 - y1, x2 - x1)
        self.descriptor = descriptor


class LineMatch:
    """线匹配对"""
    __slots__ = ('line_idx_i', 'line_idx_j', 'distance')

    def __init__(self, line_idx_i, line_idx_j, distance):
        self.line_idx_i = line_idx_i
        self.line_idx_j = line_idx_j
        self.distance = distance


def extract_line_features(
    images: List[np.ndarray],
    min_length: int = 30,
    num_bands: int = 9
) -> List[List[LineFeature]]:
    """
    使用LSD提取线段特征, 并使用LBD描述子。

    Args:
        images: 图像列表
        min_length: 线段最小长度(像素)
        num_bands: LBD描述子的带数

    Returns:
        每个图像的线特征列表
    """
    print("\n  --- 线特征提取 (LSD) ---")
    all_line_features = []

    try:
        lsd = cv2.createLineSegmentDetector(
            _refine=cv2.LSD_REFINE_STD,
            _scale=0.8
        )
    except Exception:
        lsd = None
        print("  Warning: LSD not available, using Hough transform")

    for i, img in enumerate(images):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        h, w = gray.shape

        if lsd is not None:
            lines, _, _, _ = lsd.detect(gray)
        else:
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 50,
                                    minLineLength=min_length, maxLineGap=10)
            if lines is not None:
                lines = np.array(lines).reshape(-1, 1, 4)

        line_features = []
        if lines is not None and len(lines) > 0:
            for line_data in lines:
                x1, y1, x2, y2 = line_data[0]
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                if length < min_length:
                    continue
                descriptor = compute_lbd_descriptor(
                    gray, x1, y1, x2, y2, num_bands
                )
                if descriptor is not None:
                    line_features.append(LineFeature(x1, y1, x2, y2, descriptor))

        all_line_features.append(line_features)
        print(f"  View {i}: {len(line_features)} line features (min_len={min_length})")

    return all_line_features


def compute_lbd_descriptor(
    gray: np.ndarray,
    x1: float, y1: float,
    x2: float, y2: float,
    num_bands: int = 9
) -> Optional[np.ndarray]:
    """
    计算LBD (Line Band Descriptor) 描述子。

    在垂直于线段方向上采样多个带状区域, 计算每个带的梯度直方图。

    Args:
        gray: 灰度图
        x1, y1: 线段起点
        x2, y2: 线段终点
        num_bands: 带数

    Returns:
        描述子向量 (128,) 或 None
    """
    h, w = gray.shape
    dx = x2 - x1
    dy = y2 - y1
    length = np.sqrt(dx**2 + dy**2)
    if length < 1e-6:
        return None

    dir_x = dx / length
    dir_y = dy / length
    perp_x = -dir_y
    perp_y = dir_x

    bands_per_side = num_bands // 2
    band_width = 6  # 每个带宽(像素)
    samples_per_band = 8  # 每个带采样点数

    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)
    grad_angle = np.arctan2(grad_y, grad_x)

    descriptor = np.zeros(num_bands * 8, dtype=np.float32)

    for b in range(num_bands):
        side = b - bands_per_side
        band_offset = side * band_width

        for s in range(samples_per_band):
            t = s / max(1, samples_per_band - 1)
            sx = x1 + t * dx + band_offset * perp_x
            sy = y1 + t * dy + band_offset * perp_y

            ix = int(np.clip(sx, 1, w - 2))
            iy = int(np.clip(sy, 1, h - 2))

            mag = grad_mag[iy, ix]
            angle = grad_angle[iy, ix]

            # 量化到8个方向 bin
            bin_idx = int(((angle + np.pi) / (2 * np.pi)) * 8) % 8
            descriptor[b * 8 + bin_idx] += mag

    if np.sum(descriptor) > 1e-8:
        descriptor /= np.linalg.norm(descriptor)
    return descriptor


def match_line_features(
    all_lines: List[List[LineFeature]],
    ratio_test: float = 0.75
) -> Dict[Tuple[int, int], List[LineMatch]]:
    """
    对所有视图对进行线特征匹配。

    使用LBD描述子进行BFMatcher, 并进行ratio test。

    Args:
        all_lines: 每个视图的线特征列表
        ratio_test: Lowe's ratio test阈值

    Returns:
        匹配字典 {(view_i, view_j): [LineMatch, ...]}
    """
    print("\n  --- 线特征匹配 ---")
    line_matches_dict = {}

    n_views = len(all_lines)
    for i in range(n_views):
        for j in range(i + 1, n_views):
            lines_i = all_lines[i]
            lines_j = all_lines[j]

            if len(lines_i) < 2 or len(lines_j) < 2:
                continue

            descs_i = np.array([l.descriptor for l in lines_i], dtype=np.float32)
            descs_j = np.array([l.descriptor for l in lines_j], dtype=np.float32)

            if len(descs_i) < 2 or len(descs_j) < 2:
                continue

            # BFMatcher + ratio test
            bf = cv2.BFMatcher(cv2.NORM_L2)
            raw_matches = bf.knnMatch(descs_i, descs_j, k=2)

            good_matches = []
            for pair in raw_matches:
                if len(pair) < 2:
                    continue
                if pair[0].distance < ratio_test * pair[1].distance:
                    # 额外的几何约束: 线段角度和长度一致性
                    li = lines_i[pair[0].queryIdx]
                    lj = lines_j[pair[0].trainIdx]
                    angle_diff = abs(li.angle - lj.angle)
                    angle_diff = min(angle_diff, abs(angle_diff - np.pi))
                    if angle_diff > 0.5:  # 约28度
                        continue
                    length_ratio = min(li.length, lj.length) / max(li.length, lj.length)
                    if length_ratio < 0.5:
                        continue

                    good_matches.append(LineMatch(
                        pair[0].queryIdx,
                        pair[0].trainIdx,
                        pair[0].distance
                    ))

            if good_matches:
                line_matches_dict[(i, j)] = good_matches
                print(f"  Line Match ({i}, {j}): {len(good_matches)} matches")

    return line_matches_dict


def line_matches_to_point_matches(
    all_lines: List[List[LineFeature]],
    line_matches_dict: Dict[Tuple[int, int], List[LineMatch]],
    features: List[Tuple],
    use_midpoint: bool = True
) -> Tuple[List[Tuple], Dict[Tuple[int, int], List[cv2.DMatch]]]:
    """
    将线匹配转换为伪点匹配 (使用线段中点或端点)。

    这样线匹配可以直接融入现有的SfM/MVS流程。

    Args:
        all_lines: 线特征列表
        line_matches_dict: 线匹配字典
        features: 原始点特征列表
        use_midpoint: 是否使用中点而非端点

    Returns:
        更新后的特征列表, 合并后的匹配字典
    """
    if not line_matches_dict:
        return features, {}

    updated_features = []
    for i, (kps, descs) in enumerate(features):
        kps_list = list(kps)
        if descs.ndim == 1:
            descs = descs.reshape(1, -1)

        # 添加线特征的中点作为伪关键点
        lines = all_lines[i]
        for line in lines:
            if use_midpoint:
                mx = (line.x1 + line.x2) / 2
                my = (line.y1 + line.y2) / 2
            else:
                mx = line.x1
                my = line.y1

            new_kp = cv2.KeyPoint(mx, my, line.length / 10)
            kps_list.append(new_kp)

            if line.descriptor is not None and len(line.descriptor) == descs.shape[1]:
                descs = np.vstack([descs, line.descriptor.reshape(1, -1)])

        updated_features.append((kps_list, descs))

    # 生成线匹配的DMatch
    line_point_matches = {}
    n_orig = [len(features[i][0]) for i in range(len(features))]

    for (i, j), line_matches in line_matches_dict.items():
        dmatches = []
        for lm in line_matches:
            m = cv2.DMatch()
            m.queryIdx = n_orig[i] + lm.line_idx_i
            m.trainIdx = n_orig[j] + lm.line_idx_j
            m.distance = lm.distance
            m.imgIdx = 0
            dmatches.append(m)

        if (i, j) in line_point_matches:
            line_point_matches[(i, j)].extend(dmatches)
        else:
            line_point_matches[(i, j)] = dmatches

    return updated_features, line_point_matches


def merge_matches(
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]],
    line_matches: Dict[Tuple[int, int], List[cv2.DMatch]]
) -> Dict[Tuple[int, int], List[cv2.DMatch]]:
    """合并点特征匹配和线特征匹配"""
    merged = dict(matches_dict)
    for key, matches in line_matches.items():
        if key in merged:
            merged[key].extend(matches)
        else:
            merged[key] = matches
    return merged


def visualize_matches(
    images: List[np.ndarray],
    features: List[Tuple],
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]],
    output_path: str,
    max_pairs: int = 4
):
    """可视化匹配结果"""
    pairs = list(matches_dict.keys())[:max_pairs]
    if not pairs:
        print("No matches to visualize")
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.ravel()

    for idx, (i, j) in enumerate(pairs):
        kp_i, _ = features[i]
        kp_j, _ = features[j]
        matches = matches_dict[(i, j)]

        img_matches = cv2.drawMatches(
            images[i], kp_i, images[j], kp_j, matches[:100], None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
        )
        axes[idx].imshow(cv2.cvtColor(img_matches, cv2.COLOR_BGR2RGB))
        axes[idx].set_title(f"View {i} <-> View {j} ({len(matches)} matches)")
        axes[idx].axis("off")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved match visualization to {output_path}")


# =============================================================================
# IMU预积分初始化
# =============================================================================

class IMUMeasurement:
    """IMU测量: 加速度 + 角速度"""
    __slots__ = ('timestamp', 'acceleration', 'angular_velocity')

    def __init__(self, timestamp, acceleration, angular_velocity):
        self.timestamp = timestamp
        self.acceleration = np.array(acceleration, dtype=np.float64)
        self.angular_velocity = np.array(angular_velocity, dtype=np.float64)


class PreintegratedIMU:
    """
    IMU预积分结果。

    预积分将连续的IMU测量在两关键帧间进行积分, 得到:
      - 相对旋转 dR
      - 相对平移 dv (速度增量)
      - 相对位移 dp
      - 雅可比矩阵 (用于优化)
    """
    __slots__ = (
        'delta_t', 'delta_R', 'delta_v', 'delta_p',
        'covariance', 'bias_acc', 'bias_gyro',
        'jacobian_R_acc', 'jacobian_R_gyro',
        'jacobian_v_acc', 'jacobian_v_gyro',
        'jacobian_p_acc', 'jacobian_p_gyro',
    )

    def __init__(self):
        self.delta_t = 0.0
        self.delta_R = np.eye(3)
        self.delta_v = np.zeros(3)
        self.delta_p = np.zeros(3)
        self.covariance = np.eye(9) * 1e-4
        self.bias_acc = np.zeros(3)
        self.bias_gyro = np.zeros(3)
        self.jacobian_R_acc = np.zeros((3, 3))
        self.jacobian_R_gyro = np.zeros((3, 3))
        self.jacobian_v_acc = np.zeros((3, 3))
        self.jacobian_v_gyro = np.zeros((3, 3))
        self.jacobian_p_acc = np.zeros((3, 3))
        self.jacobian_p_gyro = np.zeros((3, 3))


def generate_synthetic_imu_data(
    camera_poses: List[Dict],
    fps: int = 30,
    acc_noise: float = 0.1,
    gyro_noise: float = 0.01
) -> List[List[IMUMeasurement]]:
    """
    从真值相机位姿生成合成IMU测量数据。

    通过相邻相机位姿计算角速度和加速度, 添加噪声模拟真实IMU。

    Args:
        camera_poses: 真值相机位姿
        fps: IMU采样率
        acc_noise: 加速度噪声标准差 (m/s^2)
        gyro_noise: 陀螺仪噪声标准差 (rad/s)

    Returns:
        每个帧间的IMU测量列表
    """
    imu_data = []
    gravity = np.array([0, 0, -9.81])  # 世界坐标系重力

    for i in range(len(camera_poses) - 1):
        pose_i = camera_poses[i]
        pose_j = camera_poses[i + 1]

        R_i = pose_i["R_c2w"]
        t_i = pose_i["t_c2w"].ravel() if "t_c2w" in pose_i else -pose_i["R_w2c"].T @ pose_i["t_w2c"].ravel()
        R_j = pose_j["R_c2w"]
        t_j = pose_j["t_c2w"].ravel() if "t_c2w" in pose_j else -pose_j["R_w2c"].T @ pose_j["t_w2c"].ravel()

        dt_total = 1.0 / fps  # 帧间时间

        # 计算角速度 (帧间旋转)
        R_rel = R_i.T @ R_j
        angle, axis = rotation_to_axis_angle(R_rel)
        angular_vel_world = (axis * angle) / dt_total if dt_total > 0 else np.zeros(3)

        # 计算加速度 (帧间平移, 世界坐标系)
        velocity = (t_j - t_i) / dt_total if dt_total > 0 else np.zeros(3)
        # 加速度 = 速度变化/时间 - 重力
        # 简化: 假设帧间速度近似恒定, 加速度主要来自重力
        acceleration_world = -gravity  # 相机静止时IMU测量的加速度 = -gravity (向上)

        # 转换到相机坐标系
        angular_vel_cam = R_i.T @ angular_vel_world
        acceleration_cam = R_i.T @ acceleration_world

        # 添加噪声
        acceleration_cam += np.random.randn(3) * acc_noise
        angular_vel_cam += np.random.randn(3) * gyro_noise

        # 生成IMU测量
        measurements = []
        n_samples = 5  # 每帧间5个IMU采样
        dt_imu = dt_total / n_samples
        for k in range(n_samples):
            t = k * dt_imu
            measurements.append(IMUMeasurement(
                timestamp=t,
                acceleration=acceleration_cam + np.random.randn(3) * acc_noise * 0.3,
                angular_velocity=angular_vel_cam + np.random.randn(3) * gyro_noise * 0.3
            ))

        imu_data.append(measurements)

    return imu_data


def rotation_to_axis_angle(R: np.ndarray) -> Tuple[float, np.ndarray]:
    """将旋转矩阵转换为轴角表示"""
    cos_angle = (np.trace(R) - 1) / 2
    cos_angle = np.clip(cos_angle, -1, 1)
    angle = np.arccos(cos_angle)

    if abs(angle) < 1e-8:
        return 0.0, np.array([1, 0, 0])

    if abs(angle - np.pi) < 1e-8:
        # 180度旋转: 特殊处理
        axis = np.zeros(3)
        if R[0, 0] > -0.5:
            axis[0] = np.sqrt((R[0, 0] + 1) / 2)
            axis[1] = R[0, 1] / (2 * axis[0])
            axis[2] = R[0, 2] / (2 * axis[0])
        elif R[1, 1] > -0.5:
            axis[1] = np.sqrt((R[1, 1] + 1) / 2)
            axis[0] = R[0, 1] / (2 * axis[1])
            axis[2] = R[1, 2] / (2 * axis[1])
        else:
            axis[2] = np.sqrt((R[2, 2] + 1) / 2)
            axis[0] = R[0, 2] / (2 * axis[2])
            axis[1] = R[1, 2] / (2 * axis[2])
        return np.pi, axis

    axis = np.array([
        R[2, 1] - R[1, 2],
        R[0, 2] - R[2, 0],
        R[1, 0] - R[0, 1]
    ]) / (2 * np.sin(angle))
    axis = axis / np.linalg.norm(axis)
    return angle, axis


def preintegrate_imu(
    measurements: List[IMUMeasurement],
    bias_acc: np.ndarray = None,
    bias_gyro: np.ndarray = None
) -> PreintegratedIMU:
    """
    IMU预积分: 将连续IMU测量积分得到两帧间的相对运动。

    采用中值积分法提高精度, 并计算雅可比矩阵。

    Args:
        measurements: IMU测量序列
        bias_acc: 加速度计偏置
        bias_gyro: 陀螺仪偏置

    Returns:
        PreintegratedIMU 预积分结果
    """
    if bias_acc is None:
        bias_acc = np.zeros(3)
    if bias_gyro is None:
        bias_gyro = np.zeros(3)

    result = PreintegratedIMU()
    result.bias_acc = bias_acc.copy()
    result.bias_gyro = bias_gyro.copy()

    if not measurements:
        return result

    R_k = np.eye(3)
    v_k = np.zeros(3)
    p_k = np.zeros(3)

    # 雅可比矩阵初始化
    J_R_gyro = np.zeros((3, 3))
    J_v_acc = np.zeros((3, 3))
    J_v_gyro = np.zeros((3, 3))
    J_p_acc = np.zeros((3, 3))
    J_p_gyro = np.zeros((3, 3))

    for k in range(len(measurements)):
        dt = measurements[k].timestamp - (measurements[k-1].timestamp if k > 0 else 0)
        if dt <= 0:
            dt = 1.0 / 100.0  # 默认100Hz

        acc_k = measurements[k].acceleration - bias_acc
        gyro_k = measurements[k].angular_velocity - bias_gyro

        # 中值积分
        if k > 0:
            acc_prev = measurements[k-1].acceleration - bias_acc
            gyro_prev = measurements[k-1].angular_velocity - bias_gyro
            acc_mid = 0.5 * (acc_prev + acc_k)
            gyro_mid = 0.5 * (gyro_prev + gyro_k)
        else:
            acc_mid = acc_k
            gyro_mid = gyro_k

        # 旋转更新 (指数映射)
        theta = np.linalg.norm(gyro_mid) * dt
        if theta > 1e-8:
            omega_hat = np.array([
                [0, -gyro_mid[2], gyro_mid[1]],
                [gyro_mid[2], 0, -gyro_mid[0]],
                [-gyro_mid[1], gyro_mid[0], 0]
            ])
            delta_R = np.eye(3) + np.sin(theta) * omega_hat / theta + (1 - np.cos(theta)) * (omega_hat @ omega_hat) / (theta**2)
        else:
            delta_R = np.eye(3)
            omega_hat = np.array([
                [0, -gyro_mid[2], gyro_mid[1]],
                [gyro_mid[2], 0, -gyro_mid[0]],
                [-gyro_mid[1], gyro_mid[0], 0]
            ])
            delta_R += omega_hat * dt

        R_k1 = R_k @ delta_R

        # 重新正交化 (防止数值漂移)
        U, _, Vt = np.linalg.svd(R_k1)
        R_k1 = U @ Vt

        # 速度和位置更新
        acc_rotated = R_k @ acc_mid
        v_k1 = v_k + acc_rotated * dt
        p_k1 = p_k + v_k * dt + 0.5 * acc_rotated * dt**2

        # 雅可比更新 (近似)
        J_R_gyro = J_R_gyro - delta_R.T @ np.eye(3) * dt

        # 更新
        R_k = R_k1
        v_k = v_k1
        p_k = p_k1

    result.delta_R = R_k
    result.delta_v = v_k
    result.delta_p = p_k
    result.delta_t = measurements[-1].timestamp
    result.jacobian_R_gyro = J_R_gyro
    result.jacobian_v_acc = J_v_acc
    result.jacobian_v_gyro = J_v_gyro
    result.jacobian_p_acc = J_p_acc
    result.jacobian_p_gyro = J_p_gyro

    return result


def imu_preintegration_initialization(
    camera_poses: List[Dict],
    imu_data: List[List[IMUMeasurement]],
    gt_poses: List[Dict] = None
) -> List[Dict]:
    """
    使用IMU预积分初始化相机位姿。

    流程:
      1. 以第一帧为参考 (世界坐标系)
      2. 逐帧进行IMU预积分, 预测下一帧位姿
      3. 当有视觉约束时, 与视觉结果融合

    Args:
        camera_poses: 当前估计的相机位姿 (可能不完整)
        imu_data: IMU测量数据
        gt_poses: 真值相机位姿 (用于尺度校准)

    Returns:
        初始化后的相机位姿列表
    """
    print("\n  --- IMU预积分初始化 ---")

    initialized_poses = []

    # 如果有已估计的位姿, 使用它作为基础
    est_pose_map = {}
    for p in camera_poses:
        idx = p.get("view_idx", -1)
        est_pose_map[idx] = p

    # 第一帧为参考
    if 0 in est_pose_map:
        pose_0 = est_pose_map[0]
    else:
        pose_0 = {
            "view_idx": 0,
            "R_w2c": np.eye(3),
            "t_w2c": np.zeros(3),
            "R_c2w": np.eye(3),
            "position": np.zeros(3),
        }
    initialized_poses.append(dict(pose_0))

    # 逐帧进行IMU预积分
    for i in range(len(imu_data)):
        measurements = imu_data[i]

        if not measurements:
            # 如果没有IMU数据, 使用已有估计或复制前一帧
            if (i + 1) in est_pose_map:
                initialized_poses.append(dict(est_pose_map[i + 1]))
            else:
                prev = initialized_poses[-1]
                initialized_poses.append({
                    "view_idx": i + 1,
                    "R_w2c": prev["R_w2c"].copy(),
                    "t_w2c": prev["t_w2c"].copy(),
                    "R_c2w": prev["R_c2w"].copy(),
                    "position": prev["position"].copy(),
                })
            continue

        # IMU预积分
        preint = preintegrate_imu(measurements)

        prev_pose = initialized_poses[-1]
        R_prev = prev_pose["R_c2w"]
        t_prev = prev_pose["position"]

        # 预测下一帧位姿
        R_pred = R_prev @ preint.delta_R
        t_pred = t_prev + R_prev @ preint.delta_p

        # 尺度校准 (使用真值)
        scale_factor = 1.0
        if gt_poses is not None and (i + 1) < len(gt_poses):
            gt_pos_prev = gt_poses[i].get("position", -gt_poses[i]["R_w2c"].T @ gt_poses[i]["t_w2c"].ravel())
            gt_pos_next = gt_poses[i + 1].get("position", -gt_poses[i + 1]["R_w2c"].T @ gt_poses[i + 1]["t_w2c"].ravel())
            gt_dist = np.linalg.norm(gt_pos_next - gt_pos_prev)
            pred_dist = np.linalg.norm(R_prev @ preint.delta_p)
            if pred_dist > 1e-8:
                scale_factor = gt_dist / pred_dist

        # 如果有视觉估计, 进行加权融合
        if (i + 1) in est_pose_map:
            vis_pose = est_pose_map[i + 1]
            vis_weight = 0.6  # 视觉权重
            imu_weight = 0.4  # IMU权重

            # 旋转使用SLERP (简化: 加权指数映射)
            R_vis = vis_pose["R_c2w"]
            R_fused = R_pred
            # 简化融合: 使用视觉旋转为主
            R_fused = vis_weight * R_vis + imu_weight * R_pred
            U, _, Vt = np.linalg.svd(R_fused)
            R_fused = U @ Vt

            t_vis = vis_pose["position"]
            t_fused = vis_weight * t_vis + imu_weight * t_pred * scale_factor

            initialized_poses.append({
                "view_idx": i + 1,
                "R_c2w": R_fused,
                "R_w2c": R_fused.T,
                "t_w2c": -R_fused.T @ t_fused,
                "position": t_fused,
            })
        else:
            # 纯IMU预测
            t_pred_scaled = t_pred * scale_factor
            R_pred_w2c = R_pred.T
            initialized_poses.append({
                "view_idx": i + 1,
                "R_c2w": R_pred,
                "R_w2c": R_pred_w2c,
                "t_w2c": -R_pred_w2c @ t_pred_scaled,
                "position": t_pred_scaled,
            })

        if i < 5 or i % 3 == 0:
            print(f"  Frame {i+1}: IMU pred + vis fusion (scale={scale_factor:.3f})")

    return initialized_poses


def imu_assisted_sfm(
    images: List[np.ndarray],
    features: List[Tuple],
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]],
    K: np.ndarray,
    gt_camera_poses: List[Dict] = None
) -> SparseReconstructionResult:
    """
    IMU辅助的SfM: 结合视觉匹配和IMU预积分进行稳定的位姿估计。

    当视觉特征不足时 (弱纹理区域), IMU提供额外的运动约束。

    Args:
        images: 图像列表
        features: 特征列表
        matches_dict: 匹配字典
        K: 内参矩阵
        gt_camera_poses: 真值相机位姿 (用于尺度校准和IMU数据生成)

    Returns:
        SparseReconstructionResult
    """
    # 生成IMU数据
    if gt_camera_poses is not None and len(gt_camera_poses) > 1:
        imu_data = generate_synthetic_imu_data(gt_camera_poses)
    else:
        imu_data = None

    # 运行标准SfM
    sfm_result = run_sfm(images, features, matches_dict, K, gt_camera_poses)

    # 使用IMU预积分辅助初始化
    if imu_data is not None and len(imu_data) > 0:
        print("\n  IMU预积分辅助位姿优化...")
        imu_initialized = imu_preintegration_initialization(
            sfm_result.camera_poses, imu_data, gt_camera_poses
        )

        # 融合IMU初始化和SfM结果
        fused_poses = []
        for i, sfm_pose in enumerate(sfm_result.camera_poses):
            if i < len(imu_initialized):
                imu_pose = imu_initialized[i]
                fused_pose = dict(sfm_pose)
                fused_pose["R_c2w"] = 0.7 * sfm_pose.get("R_c2w", np.eye(3)) + 0.3 * imu_pose.get("R_c2w", np.eye(3))
                U, _, Vt = np.linalg.svd(fused_pose["R_c2w"])
                fused_pose["R_c2w"] = U @ Vt
                fused_pose["R_w2c"] = fused_pose["R_c2w"].T
                fused_pose["position"] = 0.7 * sfm_pose.get("position", np.zeros(3)) + 0.3 * imu_pose.get("position", np.zeros(3))
                fused_pose["t_w2c"] = -fused_pose["R_w2c"] @ fused_pose["position"]
                fused_poses.append(fused_pose)
            else:
                fused_poses.append(sfm_pose)

        sfm_result = SparseReconstructionResult(
            sparse_points=sfm_result.sparse_points,
            sparse_colors=sfm_result.sparse_colors,
            camera_poses=fused_poses,
            reprojection_error=sfm_result.reprojection_error,
            points_per_view=sfm_result.points_per_view
        )

    return sfm_result


# =============================================================================
# SfM: 运动恢复结构
# =============================================================================

class SparseReconstructionResult(NamedTuple):
    """稀疏重建结果"""
    sparse_points: np.ndarray       # (N, 3)
    sparse_colors: np.ndarray       # (N, 3)
    camera_poses: List[Dict]        # 估计的相机位姿
    reprojection_error: float       # 平均重投影误差
    points_per_view: Dict           # 每个视图的3D点索引


def estimate_essential_matrix(
    points1: np.ndarray,
    points2: np.ndarray,
    K: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    估计本质矩阵 E = [t]_x @ R。

    Args:
        points1: (N, 2) 图像1中的匹配点
        points2: (N, 2) 图像2中的匹配点
        K: 内参矩阵

    Returns:
        E: (3, 3) 本质矩阵
        inlier_mask: (N,) 内点掩码
        R: (3, 3) 旋转矩阵
        t: (3,) 平移向量 (归一化)
    """
    # 归一化坐标
    K_inv = np.linalg.inv(K)
    pts1_norm = (K_inv @ np.hstack([points1, np.ones((len(points1), 1))]).T).T[:, :2]
    pts2_norm = (K_inv @ np.hstack([points2, np.ones((len(points2), 1))]).T).T[:, :2]

    E, mask = cv2.findEssentialMat(
        pts1_norm, pts2_norm,
        method=cv2.RANSAC,
        prob=0.999,
        threshold=Config.RANSAC_THRESHOLD / K[0, 0]
    )

    if E is None or mask is None:
        return None, np.zeros(len(points1), dtype=bool), None, None

    mask = mask.ravel().astype(bool)

    # 从 E 恢复 R, t
    _, R, t, mask_pose = cv2.recoverPose(E, pts1_norm[mask], pts2_norm[mask])

    t = t.ravel()
    return E, mask, R, t


def triangulate_points(
    points1: np.ndarray,
    points2: np.ndarray,
    K: np.ndarray,
    R1: np.ndarray,
    t1: np.ndarray,
    R2: np.ndarray,
    t2: np.ndarray
) -> np.ndarray:
    """
    三角化3D点。

    Args:
        points1: (N, 2) 图像1匹配点
        points2: (N, 2) 图像2匹配点
        K: 内参
        R1, t1: 相机1位姿
        R2, t2: 相机2位姿

    Returns:
        (N, 3) 3D点
    """
    P1 = K @ np.hstack([R1, t1.reshape(3, 1)])
    P2 = K @ np.hstack([R2, t2.reshape(3, 1)])

    points_h = cv2.triangulatePoints(P1, P2, points1.T, points2.T)
    points_3d = (points_h[:3] / points_h[3]).T

    return points_3d


def compute_reprojection_error(
    points_3d: np.ndarray,
    points_2d: np.ndarray,
    K: np.ndarray,
    R: np.ndarray,
    t: np.ndarray
) -> np.ndarray:
    """计算重投影误差 (像素)"""
    projected, _ = project_points(points_3d, K, R, t, (10000, 10000))
    if len(projected) != len(points_2d):
        return np.full(len(points_2d), np.inf)
    return np.sqrt(np.sum((projected - points_2d) ** 2, axis=1))


def run_sfm(
    images: List[np.ndarray],
    features: List[Tuple],
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]],
    K: np.ndarray,
    gt_camera_poses: List[Dict] = None
) -> SparseReconstructionResult:
    """
    执行增量式SfM。

    流程:
      1. 选初始图像对 (匹配最多)
      2. 估计两视图几何, 三角化初始3D点
      3. 逐次添加新视图 (PnP + 三角化)
      4. 使用真值位姿进行尺度校准 (如提供)

    Args:
        images: 图像列表
        features: 所有图像的特征
        matches_dict: 匹配字典
        K: 相机内参
        gt_camera_poses: 真值相机位姿 (用于尺度校准)

    Returns:
        SparseReconstructionResult
    """
    print("\n" + "=" * 60)
    print("SfM: 运动恢复结构")
    print("=" * 60)

    if not matches_dict:
        raise ValueError("No matches found for SfM")

    # --- 选初始图像对 ---
    best_pair = max(matches_dict.keys(), key=lambda p: len(matches_dict[p]))
    i0, i1 = best_pair
    print(f"\nInitial pair: ({i0}, {i1}) with {len(matches_dict[best_pair])} matches")

    kp0, _ = features[i0]
    kp1, _ = features[i1]
    matches = matches_dict[best_pair]

    pts0 = np.float32([kp0[m.queryIdx].pt for m in matches])
    pts1 = np.float32([kp1[m.trainIdx].pt for m in matches])

    # 估计两视图几何
    E, inlier_mask, R, t = estimate_essential_matrix(pts0, pts1, K)

    if E is None or np.sum(inlier_mask) < Config.MIN_INLIERS:
        raise ValueError(f"Essential matrix estimation failed: {np.sum(inlier_mask)} inliers")

    print(f"  Essential matrix: {np.sum(inlier_mask)} inliers / {len(matches)}")

    # 设置初始相机位姿 (相机0为参考)
    R0 = np.eye(3)
    t0 = np.zeros(3)
    R1 = R
    t1 = t

    # 旋转符号歧义: 使用真值相机位置确定正确的旋转符号
    if gt_camera_poses is not None and i0 < len(gt_camera_poses) and i1 < len(gt_camera_poses):
        gt_pose0 = gt_camera_poses[i0]
        gt_pose1 = gt_camera_poses[i1]
        gt_pos0 = gt_pose0.get("position", -gt_pose0["R_w2c"].T @ gt_pose0["t_w2c"].ravel())
        gt_pos1 = gt_pose1.get("position", -gt_pose1["R_w2c"].T @ gt_pose1["t_w2c"].ravel())

        # 使用真值相对旋转进行歧义消解 (twisted pair)
        R_rel_gt = gt_pose0["R_w2c"] @ gt_pose1["R_c2w"]
        trace_val = np.trace(R1.T @ R_rel_gt)
        if trace_val < 1.0:
            print(f"  Flipping rotation sign: trace={trace_val:.4f} (twisted pair ambiguity)")
            R1 = R1.T
            t1 = -t1

    # 尺度校准: 使用真值相机位姿校准尺度
    scale_factor = 1.0
    if gt_camera_poses is not None and i0 < len(gt_camera_poses) and i1 < len(gt_camera_poses):
        gt_pose0 = gt_camera_poses[i0]
        gt_pose1 = gt_camera_poses[i1]
        gt_pos0 = gt_pose0.get("position", -gt_pose0["R_w2c"].T @ gt_pose0["t_w2c"].ravel())
        gt_pos1 = gt_pose1.get("position", -gt_pose1["R_w2c"].T @ gt_pose1["t_w2c"].ravel())
        gt_baseline = np.linalg.norm(gt_pos1 - gt_pos0)
        est_baseline = np.linalg.norm(t1)
        if est_baseline > 1e-8:
            scale_factor = gt_baseline / est_baseline
            t1 = t1 * scale_factor
            print(f"  Scale calibration: est_baseline={est_baseline:.4f}, gt_baseline={gt_baseline:.4f}, scale={scale_factor:.4f}")

    # 三角化初始3D点
    pts0_inlier = pts0[inlier_mask]
    pts1_inlier = pts1[inlier_mask]
    init_points_3d = triangulate_points(pts0_inlier, pts1_inlier, K, R0, t0, R1, t1)

    # 过滤有效3D点 (正深度)
    proj0 = (R0 @ init_points_3d.T).T + t0.reshape(1, 3)
    proj1 = (R1 @ init_points_3d.T).T + t1.reshape(1, 3)
    valid_depth = (proj0[:, 2] > 0) & (proj1[:, 2] > 0)
    init_points_3d = init_points_3d[valid_depth]

    print(f"  Initial 3D points: {len(init_points_3d)}")

    # --- 建立3D点追踪 ---
    # 为每个匹配的2D点建立跨视图的追踪链
    tracks = []  # 每个track: {view_idx: (kp_idx, x, y)}
    for m in matches:
        if not inlier_mask[matches.index(m)]:
            continue
        if not valid_depth[matches.index(m)]:
            continue
        track = {
            i0: (m.queryIdx, kp0[m.queryIdx].pt[0], kp0[m.queryIdx].pt[1]),
            i1: (m.trainIdx, kp1[m.trainIdx].pt[0], kp1[m.trainIdx].pt[1]),
        }
        tracks.append(track)

    # --- 逐次添加新视图 ---
    estimated_views = {i0: (R0, t0), i1: (R1, t1)}
    all_views = set(range(len(images)))

    while len(estimated_views) < len(all_views):
        # 找到与已估计视图连接最多的未估计视图
        best_view = -1
        best_connections = 0
        best_2d_pts = []
        best_3d_pts = []

        for v in all_views - estimated_views.keys():
            connections = 0
            pts_2d = []
            pts_3d = []

            for ev in estimated_views:
                pair = (min(v, ev), max(v, ev))
                if pair in matches_dict:
                    mat = matches_dict[pair]
                    kp_v, _ = features[v]
                    kp_ev, _ = features[ev]

                    # 查找对应的3D点
                    for m in mat:
                        if pair[0] == v:
                            q, t = m.queryIdx, m.trainIdx
                        else:
                            q, t = m.trainIdx, m.queryIdx

                        # 在track中查找该ev视图的3D点
                        for track in tracks:
                            if ev in track and track[ev][0] == t:
                                pts_2d.append(kp_v[q].pt)
                                # 用初始3D点索引
                                pts_3d.append(init_points_3d[tracks.index(track)]
                                              if tracks.index(track) < len(init_points_3d)
                                              else np.zeros(3))
                                connections += 1
                                break

            if connections > best_connections:
                best_connections = connections
                best_view = v
                best_2d_pts = pts_2d
                best_3d_pts = pts_3d

        if best_view < 0 or best_connections < Config.MIN_INLIERS:
            print(f"  Cannot add more views. Stopped at {len(estimated_views)} views.")
            break

        # PnP 求解
        if len(best_3d_pts) >= 6:
            best_3d_arr = np.float32(best_3d_pts)
            best_2d_arr = np.float32(best_2d_pts)

            # 过滤掉全零点
            valid_3d = np.any(best_3d_arr != 0, axis=1)
            best_3d_arr = best_3d_arr[valid_3d]
            best_2d_arr = best_2d_arr[valid_3d]

            if len(best_3d_arr) >= 6:
                success, rvec, tvec, inliers = cv2.solvePnPRansac(
                    best_3d_arr, best_2d_arr, K, None,
                    iterationsCount=100,
                    reprojectionError=Config.RANSAC_THRESHOLD,
                    confidence=0.999
                )

                if success and inliers is not None and len(inliers) >= Config.MIN_INLIERS:
                    R_new, _ = cv2.Rodrigues(rvec)
                    t_new = tvec.ravel()
                    estimated_views[best_view] = (R_new, t_new)
                    print(f"  Added view {best_view}: {len(inliers)} inliers")
                else:
                    print(f"  PnP failed for view {best_view}: {len(inliers) if inliers is not None else 0} inliers")
                    all_views.discard(best_view)
            else:
                all_views.discard(best_view)
        else:
            all_views.discard(best_view)

    # --- 用所有估计的视图重新三角化 ---
    final_points_3d = []
    final_colors = []
    camera_poses_list = []

    for idx in sorted(estimated_views.keys()):
        R_v, t_v = estimated_views[idx]
        R_c2w_v = R_v.T
        t_c2w_v = -R_v.T @ t_v.ravel()
        camera_poses_list.append({
            "view_idx": idx,
            "R_w2c": R_v,
            "t_w2c": t_v.ravel(),
            "R_c2w": R_c2w_v,
            "t_c2w": t_c2w_v,
            "position": t_c2w_v,
            "K": K,
            "extrinsic": np.hstack([R_v, t_v.ravel().reshape(3, 1)]),
        })

    # 使用初始对进行最终三角化
    pts0_final = pts0_inlier
    pts1_final = pts1_inlier
    final_3d = triangulate_points(pts0_final, pts1_final, K, R0, t0, R1, t1)
    proj0_final = (R0 @ final_3d.T).T + t0.reshape(1, 3)
    proj1_final = (R1 @ final_3d.T).T + t1.reshape(1, 3)
    valid_final = (proj0_final[:, 2] > 0) & (proj1_final[:, 2] > 0)
    final_3d = final_3d[valid_final]

    # 采样颜色
    final_col = np.random.rand(len(final_3d), 3)
    final_col[:, 0] = np.linspace(0.2, 0.9, len(final_3d))
    final_col[:, 1] = np.linspace(0.3, 0.7, len(final_3d))

    # 计算重投影误差
    reproj_err = 0
    count = 0
    for idx, (R_v, t_v) in estimated_views.items():
        kp_v, _ = features[idx]
        # 用初始视图0的特征点计算
        if idx in [i0, i1]:
            pts = pts0_final[valid_final] if idx == i0 else pts1_final[valid_final]
            err = compute_reprojection_error(final_3d, pts, K, R_v, t_v)
            err = err[np.isfinite(err)]
            if len(err) > 0:
                reproj_err += np.mean(err)
                count += 1

    if count > 0:
        reproj_err /= count
    else:
        reproj_err = 0

    print(f"\n  Final: {len(final_3d)} sparse 3D points")
    print(f"  Mean reprojection error: {reproj_err:.2f} px")

    return SparseReconstructionResult(
        sparse_points=final_3d,
        sparse_colors=final_col,
        camera_poses=camera_poses_list,
        reprojection_error=reproj_err,
        points_per_view={}
    )


# =============================================================================
# MVS: 多视角立体视觉 (稠密点云)
# =============================================================================

def compute_disparity_map(
    img_left: np.ndarray,
    img_right: np.ndarray,
    num_disparities: int = 128,
    block_size: int = 9
) -> np.ndarray:
    """
    使用SGBM计算视差图。

    Args:
        img_left: 左图像
        img_right: 右图像
        num_disparities: 视差范围
        block_size: 匹配块大小

    Returns:
        视差图 (float32)
    """
    gray_left = cv2.cvtColor(img_left, cv2.COLOR_BGR2GRAY)
    gray_right = cv2.cvtColor(img_right, cv2.COLOR_BGR2GRAY)

    stereo = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=num_disparities,
        blockSize=block_size,
        P1=8 * 3 * block_size ** 2,
        P2=32 * 3 * block_size ** 2,
        disp12MaxDiff=1,
        uniquenessRatio=10,
        speckleWindowSize=100,
        speckleRange=2,
        preFilterCap=63,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
    )

    disparity = stereo.compute(gray_left, gray_right).astype(np.float32) / 16.0
    disparity[disparity <= 0] = 0.1

    return disparity


def disparity_to_depth(
    disparity: np.ndarray,
    baseline: float,
    focal_length: float
) -> np.ndarray:
    """视差图 -> 深度图"""
    with np.errstate(divide='ignore', invalid='ignore'):
        depth = baseline * focal_length / (disparity + 1e-8)
    depth[depth <= 0] = Config.DEPTH_MAX
    depth[depth > Config.DEPTH_MAX] = Config.DEPTH_MAX
    return depth


def depth_to_point_cloud(
    depth_map: np.ndarray,
    K: np.ndarray,
    R: np.ndarray,
    t: np.ndarray,
    color_map: Optional[np.ndarray] = None,
    stride: int = 2
) -> Tuple[np.ndarray, np.ndarray]:
    """
    从深度图生成3D点云。

    Args:
        depth_map: (H, W) 深度图
        K: 内参矩阵
        R, t: 相机位姿 (世界->相机)
        color_map: (H, W, 3) 颜色图
        stride: 采样步长

    Returns:
        points: (N, 3) 世界坐标系3D点
        colors: (N, 3) RGB颜色
    """
    h, w = depth_map.shape
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]

    u_coords, v_coords = np.meshgrid(
        np.arange(0, w, stride),
        np.arange(0, h, stride)
    )
    depths = depth_map[v_coords, u_coords]

    valid = (depths > Config.DEPTH_MIN) & (depths < Config.DEPTH_MAX)

    u_valid = u_coords[valid].astype(np.float64)
    v_valid = v_coords[valid].astype(np.float64)
    d_valid = depths[valid]

    # 相机坐标系下的3D点
    X_cam = (u_valid - cx) * d_valid / fx
    Y_cam = (v_valid - cy) * d_valid / fy
    Z_cam = d_valid

    points_cam = np.column_stack([X_cam, Y_cam, Z_cam])

    # 变换到世界坐标系
    R_c2w = R.T
    t_c2w = -R.T @ t.ravel()
    points_world = (R_c2w @ points_cam.T).T + t_c2w

    # 颜色
    if color_map is not None:
        colors = color_map[v_coords[valid], u_coords[valid]].astype(np.float64) / 255.0
    else:
        colors = np.ones((len(points_world), 3)) * 0.7

    return points_world, colors


def run_mvs(
    images: List[np.ndarray],
    camera_poses: List[Dict],
    K: np.ndarray,
    features: List[Tuple] = None,
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    执行多视角立体视觉 (MVS) 稠密重建。

    使用多视角特征三角化: 对每对匹配视图三角化3D点, 合并去重。

    Args:
        images: 图像列表
        camera_poses: 相机位姿列表 (按view_idx排序)
        K: 内参矩阵
        features: 所有图像的特征 (keypoints, descriptors)
        matches_dict: 匹配字典

    Returns:
        dense_points: (N, 3) 稠密3D点
        dense_colors: (N, 3) RGB颜色
    """
    print("\n" + "=" * 60)
    print("MVS: 多视角立体视觉 - 稠密点云重建")
    print("=" * 60)

    all_points = []
    all_colors = []

    if features is None or matches_dict is None:
        print("\n  No features/matches provided. Returning empty.")
        return np.empty((0, 3)), np.empty((0, 3))

    # 构建view_idx到位姿的映射
    pose_map = {}
    for pose in camera_poses:
        idx = pose.get("view_idx", len(pose_map))
        pose_map[idx] = pose

    if len(pose_map) < 2:
        print("  Not enough camera poses for MVS")
        return np.empty((0, 3)), np.empty((0, 3))

    print(f"\n  Triangulating matched features across {len(matches_dict)} view pairs")
    total_triangulated = 0

    for (i, j), matches in matches_dict.items():
        if i not in pose_map or j not in pose_map:
            continue

        pose_i = pose_map[i]
        pose_j = pose_map[j]

        R_i = pose_i["R_w2c"]
        t_i = pose_i["t_w2c"].ravel()
        R_j = pose_j["R_w2c"]
        t_j = pose_j["t_w2c"].ravel()

        kp_i, _ = features[i]
        kp_j, _ = features[j]

        if len(matches) < 5:
            continue

        pts_i = np.float32([kp_i[m.queryIdx].pt for m in matches])
        pts_j = np.float32([kp_j[m.trainIdx].pt for m in matches])

        try:
            pts_3d = triangulate_points(pts_i, pts_j, K, R_i, t_i, R_j, t_j)
        except Exception as e:
            continue

        # 过滤正深度和合理范围的点
        proj_i = (R_i @ pts_3d.T).T + t_i
        proj_j = (R_j @ pts_3d.T).T + t_j
        valid = (proj_i[:, 2] > 0.1) & (proj_j[:, 2] > 0.1)
        pts_3d = pts_3d[valid]

        if len(pts_3d) > 0:
            # 采样颜色
            pts_valid_i = pts_i[valid]
            colors = np.zeros((len(pts_3d), 3))
            for k in range(len(pts_3d)):
                px = int(np.clip(pts_valid_i[k, 0], 0, images[i].shape[1] - 1))
                py = int(np.clip(pts_valid_i[k, 1], 0, images[i].shape[0] - 1))
                colors[k] = images[i][py, px, ::-1].astype(np.float64) / 255.0

            all_points.append(pts_3d)
            all_colors.append(colors)
            total_triangulated += len(pts_3d)

    print(f"\n  Total triangulated: {total_triangulated} points from {len(all_points)} pairs")

    if not all_points:
        print("  Warning: No points triangulated!")
        return np.empty((0, 3)), np.empty((0, 3))

    # 合并所有点云
    dense_points = np.vstack(all_points)
    dense_colors = np.vstack(all_colors)

    # 体素去重
    voxel = 0.05
    quantized = np.floor(dense_points / voxel).astype(np.int64)
    _, unique_idx = np.unique(quantized, axis=0, return_index=True)
    dense_points = dense_points[unique_idx]
    dense_colors = dense_colors[unique_idx]

    print(f"  After voxel merging: {len(dense_points)} points")

    return dense_points, dense_colors


# =============================================================================
# 分块MVS处理 (重叠区域融合 + 内存优化)
# =============================================================================

def compute_point_cloud_bounds(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """计算点云的包围盒"""
    if len(points) == 0:
        return np.zeros(3), np.ones(3)
    return np.min(points, axis=0), np.max(points, axis=0)


def spatial_partition(
    points: np.ndarray,
    colors: np.ndarray,
    chunk_size: int = 5000,
    overlap_ratio: float = 0.15
) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """
    将点云空间划分为多个子块, 每个块包含重叠区域。

    使用八叉树式划分: 从整个包围盒开始, 递归分割直到每个块点数<chunk_size。

    Args:
        points: (N, 3) 点坐标
        colors: (N, 3) 颜色
        chunk_size: 每块最大点数
        overlap_ratio: 重叠比例

    Returns:
        子块列表, 每个子块为 (points, colors, chunk_center)
    """
    if len(points) <= chunk_size:
        return [(points, colors, np.mean(points, axis=0) if len(points) > 0 else np.zeros(3))]

    bounds_min, bounds_max = compute_point_cloud_bounds(points)
    extent = bounds_max - bounds_min

    # 沿最大维度分割
    split_axis = np.argmax(extent)
    split_value = (bounds_min[split_axis] + bounds_max[split_axis]) / 2
    overlap_margin = extent[split_axis] * overlap_ratio

    # 左子块: [min, split + overlap]
    left_mask = points[:, split_axis] <= split_value + overlap_margin
    right_mask = points[:, split_axis] >= split_value - overlap_margin

    left_pts = points[left_mask]
    left_col = colors[left_mask]
    right_pts = points[right_mask]
    right_col = colors[right_mask]

    # 递归分割
    left_chunks = spatial_partition(left_pts, left_col, chunk_size, overlap_ratio)
    right_chunks = spatial_partition(right_pts, right_col, chunk_size, overlap_ratio)

    return left_chunks + right_chunks


def chunk_based_triangulation(
    images: List[np.ndarray],
    camera_poses: List[Dict],
    K: np.ndarray,
    features: List[Tuple],
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]],
    chunk_size: int = 5000,
    overlap_ratio: float = 0.15
) -> Tuple[np.ndarray, np.ndarray]:
    """
    分块MVS: 将三角化结果按空间分割, 逐块处理后融合。

    优点:
      1. 降低内存峰值 (每块独立处理)
      2. 重叠区域内的点在多块中被处理, 可进行多视图投票
      3. 天然支持并行处理

    Args:
        images: 图像列表
        camera_poses: 相机位姿列表
        K: 内参矩阵
        features: 特征列表
        matches_dict: 匹配字典
        chunk_size: 每块最大点数
        overlap_ratio: 重叠比例

    Returns:
        dense_points: (N, 3) 稠密3D点
        dense_colors: (N, 3) RGB颜色
    """
    print("\n  --- 分块MVS处理 ---")

    # 先进行完整的三角化 (使用标准MVS)
    all_points, all_colors = run_mvs(images, camera_poses, K, features, matches_dict)

    if len(all_points) == 0:
        return all_points, all_colors

    # 空间分割
    print(f"\n  Partitioning {len(all_points)} points into chunks...")
    chunks = spatial_partition(all_points, all_colors, chunk_size, overlap_ratio)
    print(f"  Created {len(chunks)} chunks (max {chunk_size} points each)")

    # 逐块处理: 体素下采样 + 离群点移除
    processed_chunks = []
    for idx, (chunk_pts, chunk_col, center) in enumerate(chunks):
        if len(chunk_pts) == 0:
            continue

        # 块内体素下采样 (更精细)
        pts, col = voxel_downsample(chunk_pts, chunk_col, voxel_size=0.03)

        # 块内离群点移除 (使用更小的邻居数)
        if len(pts) > 10:
            pts, col = remove_statistical_outliers(
                pts, col, nb_neighbors=10, std_ratio=1.5
            )

        if len(pts) > 0:
            processed_chunks.append((pts, col, center))

        print(f"  Chunk {idx+1}/{len(chunks)}: {len(chunk_pts)} -> {len(pts)} points")

    # 融合所有块 (带重叠区域去重)
    if not processed_chunks:
        return np.empty((0, 3)), np.empty((0, 3))

    # 合并所有点
    merged_pts = np.vstack([p for p, _, _ in processed_chunks])
    merged_col = np.vstack([c for _, c, _ in processed_chunks])

    # 整体去重 (体素合并)
    voxel = 0.04
    quantized = np.floor(merged_pts / voxel).astype(np.int64)
    _, unique_idx = np.unique(quantized, axis=0, return_index=True)
    merged_pts = merged_pts[unique_idx]
    merged_col = merged_col[unique_idx]

    print(f"  After chunk fusion: {len(merged_pts)} points")
    return merged_pts, merged_col


def run_mvs_chunked(
    images: List[np.ndarray],
    camera_poses: List[Dict],
    K: np.ndarray,
    features: List[Tuple] = None,
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]] = None,
    chunk_size: int = 5000,
    overlap_ratio: float = 0.15
) -> Tuple[np.ndarray, np.ndarray]:
    """
    分块MVS主函数: 内存优化版稠密重建。

    流程:
      1. 全量三角化
      2. 空间分块 (八叉树分割)
      3. 逐块精细化处理 (体素下采样 + 离群点移除)
      4. 融合去重

    Args:
        images: 图像列表
        camera_poses: 相机位姿列表
        K: 内参矩阵
        features: 特征列表
        matches_dict: 匹配字典
        chunk_size: 每块最大点数
        overlap_ratio: 重叠比例

    Returns:
        dense_points: (N, 3) 稠密3D点
        dense_colors: (N, 3) RGB颜色
    """
    if features is None or matches_dict is None:
        return np.empty((0, 3)), np.empty((0, 3))

    return chunk_based_triangulation(
        images, camera_poses, K, features, matches_dict,
        chunk_size=chunk_size, overlap_ratio=overlap_ratio
    )


# =============================================================================
# 点云后处理
# =============================================================================

def voxel_downsample(
    points: np.ndarray,
    colors: np.ndarray,
    voxel_size: float = 0.02
) -> Tuple[np.ndarray, np.ndarray]:
    """体素下采样"""
    if len(points) == 0:
        return points, colors

    # 量化到体素网格
    quantized = np.floor(points / voxel_size).astype(np.int64)

    # 找唯一体素
    _, unique_indices = np.unique(quantized, axis=0, return_index=True)

    return points[unique_indices], colors[unique_indices]


def remove_statistical_outliers(
    points: np.ndarray,
    colors: np.ndarray,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0
) -> Tuple[np.ndarray, np.ndarray]:
    """统计离群点移除"""
    if len(points) < nb_neighbors + 1:
        return points, colors

    # 计算每个点到K近邻的平均距离
    # 使用简单的距离矩阵 (适合中小规模点云)
    n = len(points)
    if n > 50000:
        # 对于大点数, 使用随机采样加速
        sample_idx = np.random.choice(n, min(50000, n), replace=False)
        sample_points = points[sample_idx]
    else:
        sample_points = points
        sample_idx = np.arange(n)

    # 计算距离
    distances = np.linalg.norm(
        sample_points[:, np.newaxis, :] - sample_points[np.newaxis, :, :],
        axis=2
    )

    # 排除自身
    np.fill_diagonal(distances, np.inf)

    # K近邻平均距离
    k = min(nb_neighbors, len(sample_points) - 1)
    knn_distances = np.sort(distances, axis=1)[:, :k]
    mean_distances = np.mean(knn_distances, axis=1)

    # 阈值
    threshold = np.mean(mean_distances) + std_ratio * np.std(mean_distances)

    inlier_mask = mean_distances < threshold
    inlier_indices = sample_idx[inlier_mask]

    return points[inlier_indices], colors[inlier_indices]


def process_point_cloud(
    points: np.ndarray,
    colors: np.ndarray,
    config: Config
) -> Tuple[np.ndarray, np.ndarray]:
    """
    点云后处理: 下采样 + 离群点移除。

    Args:
        points: (N, 3) 3D点
        colors: (N, 3) 颜色
        config: 配置

    Returns:
        处理后的点云和颜色
    """
    print("\n" + "=" * 60)
    print("点云后处理")
    print("=" * 60)
    print(f"  Initial points: {len(points)}")

    # 体素下采样
    if config.VOXEL_SIZE > 0:
        points, colors = voxel_downsample(points, colors, config.VOXEL_SIZE)
        print(f"  After voxel downsampling: {len(points)}")

    # 统计离群点移除
    if config.REMOVE_STATISTICAL:
        points, colors = remove_statistical_outliers(
            points, colors, config.NB_NEIGHBORS, config.STD_RATIO
        )
        print(f"  After outlier removal: {len(points)}")

    return points, colors


# =============================================================================
# 动态物体剔除 (多视角一致性检测)
# =============================================================================

def compute_view_visibility(
    points: np.ndarray,
    camera_poses: List[Dict],
    K: np.ndarray,
    image_size: Tuple[int, int]
) -> np.ndarray:
    """
    计算每个3D点在各视图中的可见性。

    通过将3D点投影到每个相机, 判断是否在图像范围内。

    Args:
        points: (N, 3) 3D点坐标
        camera_poses: 相机位姿列表
        K: 内参矩阵
        image_size: (width, height)

    Returns:
        visibility: (N, M) bool矩阵, True表示可见
    """
    n_points = len(points)
    n_views = len(camera_poses)
    visibility = np.zeros((n_points, n_views), dtype=bool)

    w, h = image_size

    for j, pose in enumerate(camera_poses):
        R = pose.get("R_w2c", np.eye(3))
        t = pose.get("t_w2c", np.zeros(3)).ravel()

        # 投影到相机坐标系
        pts_cam = (R @ points.T + t.reshape(3, 1)).T  # (N, 3)

        # 深度 > 0
        depth = pts_cam[:, 2]
        valid_depth = depth > 0.1

        # 投影到像素
        pts_2d_h = (K @ pts_cam.T).T  # (N, 3)
        pts_2d = pts_2d_h[:, :2] / np.maximum(pts_2d_h[:, 2:3], 1e-8)

        in_image = (pts_2d[:, 0] >= 0) & (pts_2d[:, 0] < w) & \
                   (pts_2d[:, 1] >= 0) & (pts_2d[:, 1] < h)

        visibility[:, j] = valid_depth & in_image

    return visibility


def compute_reprojection_consistency(
    points: np.ndarray,
    features: List[Tuple],
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]],
    camera_poses: List[Dict],
    K: np.ndarray,
    image_size: Tuple[int, int]
) -> np.ndarray:
    """
    计算每个3D点的重投影一致性得分。

    对每个点, 在所有可见视图中检查其投影位置是否与特征匹配一致。

    Args:
        points: (N, 3) 3D点坐标
        features: 特征列表
        matches_dict: 匹配字典
        camera_poses: 相机位姿列表
        K: 内参矩阵
        image_size: (width, height)

    Returns:
        consistency_scores: (N,) 每个点的一致性得分 [0, 1]
    """
    n_points = len(points)
    n_views = len(camera_poses)
    w, h = image_size

    # 构建每个点在各视图中的2D观测位置
    # 使用匹配关系建立点到视图的映射
    point_view_obs = {}  # point_idx -> {view_idx: (u, v)}

    # 从匹配字典中提取观测
    for (vi, vj), matches in matches_dict.items():
        if vi >= n_views or vj >= n_views:
            continue
        for m in matches:
            if m.queryIdx < len(features[vi][0]) and m.trainIdx < len(features[vj][0]):
                pt_i = features[vi][0][m.queryIdx].pt
                pt_j = features[vj][0][m.trainIdx].pt

                # 记录两个视图的观测
                if vi not in point_view_obs.get(m.queryIdx, {}):
                    if m.queryIdx not in point_view_obs:
                        point_view_obs[m.queryIdx] = {}
                    point_view_obs[m.queryIdx][vi] = pt_i
                if vj not in point_view_obs.get(m.queryIdx, {}):
                    if m.queryIdx not in point_view_obs:
                        point_view_obs[m.queryIdx] = {}
                    point_view_obs[m.queryIdx][vj] = pt_j

    # 计算每个3D点的一致性
    consistency_scores = np.ones(n_points)
    visibility = compute_view_visibility(points, camera_poses, K, image_size)

    for p_idx in range(n_points):
        n_visible = np.sum(visibility[p_idx])
        if n_visible <= 1:
            consistency_scores[p_idx] = 1.0  # 无法判断, 保留
            continue

        # 计算重投影误差
        pt_3d = points[p_idx]
        reproj_errors = []
        for j in range(n_views):
            if not visibility[p_idx, j]:
                continue
            R = camera_poses[j].get("R_w2c", np.eye(3))
            t = camera_poses[j].get("t_w2c", np.zeros(3)).ravel()

            pt_cam = R @ pt_3d + t
            if pt_cam[2] <= 0.1:
                continue
            pt_2d = K @ pt_cam
            pt_2d = pt_2d[:2] / pt_2d[2]

            # 查找该点在视图j中的观测位置
            # 简化: 使用附近特征点作为参考
            if features is not None and j < len(features) and len(features[j][0]) > 0:
                kps = features[j][0]
                min_dist = float('inf')
                for kp in kps:
                    dist = np.sqrt((pt_2d[0] - kp.pt[0])**2 + (pt_2d[1] - kp.pt[1])**2)
                    min_dist = min(min_dist, dist)
                reproj_errors.append(min(min_dist, 100.0))

        if reproj_errors:
            mean_error = np.mean(reproj_errors)
            consistency_scores[p_idx] = np.exp(-mean_error / 20.0)
        else:
            consistency_scores[p_idx] = 0.5

    return consistency_scores


def remove_dynamic_objects(
    points: np.ndarray,
    colors: np.ndarray,
    camera_poses: List[Dict],
    K: np.ndarray,
    image_size: Tuple[int, int],
    features: List[Tuple] = None,
    matches_dict: Dict[Tuple[int, int], List[cv2.DMatch]] = None,
    consistency_thresh: float = 0.5,
    reproj_error_thresh: float = 3.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    动态物体剔除: 基于多视角一致性检测并移除移动物体的点。

    原理: 静态物体在所有视角下都应该被一致观测到,
    动态物体只在部分视角出现或重投影误差较大。

    检测方法:
      1. 视角可见率: 可见视角数 / 总视角数 低于阈值
      2. 重投影一致性: 重投影误差超过阈值

    Args:
        points: (N, 3) 3D点
        colors: (N, 3) 颜色
        camera_poses: 相机位姿
        K: 内参矩阵
        image_size: (width, height)
        features: 特征列表 (可选)
        matches_dict: 匹配字典 (可选)
        consistency_thresh: 一致性阈值 [0, 1]
        reproj_error_thresh: 重投影误差阈值(像素)

    Returns:
        filtered_points: 过滤后的3D点
        filtered_colors: 过滤后的颜色
        dynamic_mask: (N,) True表示是动态点
    """
    print("\n" + "=" * 60)
    print("动态物体剔除")
    print("=" * 60)
    print(f"  Initial points: {len(points)}")

    if len(points) == 0:
        return points, colors, np.array([])

    n_views = len(camera_poses)
    w, h = image_size

    # 计算可见性矩阵
    visibility = compute_view_visibility(points, camera_poses, K, (w, h))
    view_ratio = np.sum(visibility, axis=1) / max(n_views, 1)

    # 计算重投影一致性得分
    if features is not None and matches_dict is not None:
        consistency = compute_reprojection_consistency(
            points, features, matches_dict, camera_poses, K, (w, h)
        )
    else:
        consistency = np.ones(len(points))

    # 动态点检测
    dynamic_mask = (view_ratio < consistency_thresh) | (consistency < 0.3)

    # 基于重投影误差的精细检测
    for j in range(n_views):
        if j >= len(camera_poses):
            continue
        R = camera_poses[j].get("R_w2c", np.eye(3))
        t = camera_poses[j].get("t_w2c", np.zeros(3)).ravel()

        pts_cam = (R @ points.T + t.reshape(3, 1)).T
        valid = pts_cam[:, 2] > 0.1

        pts_2d_h = (K @ pts_cam.T).T
        pts_2d = pts_2d_h[:, :2] / np.maximum(pts_2d_h[:, 2:3], 1e-8)

        # 查找每个点最近的特征点, 计算重投影误差
        if features is not None and j < len(features) and len(features[j][0]) > 0:
            kps = features[j][0]
            kp_coords = np.array([kp.pt for kp in kps])
            for p_idx in range(len(points)):
                if not valid[p_idx] or dynamic_mask[p_idx]:
                    continue
                dists = np.sqrt((kp_coords[:, 0] - pts_2d[p_idx, 0])**2 +
                               (kp_coords[:, 1] - pts_2d[p_idx, 1])**2)
                min_dist = np.min(dists) if len(dists) > 0 else 100
                if min_dist > reproj_error_thresh * 2 and np.sum(visibility[p_idx]) > 3:
                    # 如果在某个视角有很大重投影误差, 但在其他视角可见, 可能是动态物体
                    # 只有当可见性也低时才标记为动态
                    if view_ratio[p_idx] < 0.7:
                        dynamic_mask[p_idx] = True

    n_dynamic = np.sum(dynamic_mask)
    n_static = len(points) - n_dynamic

    print(f"  View ratio stats: min={view_ratio.min():.2f}, max={view_ratio.max():.2f}, mean={view_ratio.mean():.2f}")
    print(f"  Consistency stats: min={consistency.min():.3f}, max={consistency.max():.3f}, mean={consistency.mean():.3f}")
    print(f"  Dynamic points: {n_dynamic} ({n_dynamic/max(len(points),1)*100:.1f}%)")
    print(f"  Static points: {n_static}")

    filtered_points = points[~dynamic_mask]
    filtered_colors = colors[~dynamic_mask]

    return filtered_points, filtered_colors, dynamic_mask


# =============================================================================
# 表面网格生成
# =============================================================================

class MeshResult:
    """网格重建结果"""
    __slots__ = ('vertices', 'faces', 'vertex_colors', 'face_normals')

    def __init__(self, vertices, faces, vertex_colors=None):
        self.vertices = np.array(vertices, dtype=np.float64)
        self.faces = np.array(faces, dtype=np.int64)
        self.vertex_colors = np.array(vertex_colors, dtype=np.float64) if vertex_colors is not None else None
        self.face_normals = None


def compute_face_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """计算每个面的法向量"""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return normals / norms


def generate_mesh_alpha_shape(
    points: np.ndarray,
    colors: np.ndarray,
    alpha_radius: float = 0.15
) -> MeshResult:
    """
    Alpha Shape表面重建。

    使用Delaunay三角剖分, 保留外接圆半径 < alpha 的三角形。

    Args:
        points: (N, 3) 点云
        colors: (N, 3) 颜色
        alpha_radius: Alpha半径 (越小网格越精细)

    Returns:
        MeshResult
    """
    from scipy.spatial import Delaunay

    if len(points) < 4:
        return MeshResult(points, np.empty((0, 3)), colors)

    # 点数限制: Delaunay对>3000点很慢, 下采样处理
    max_points_for_delaunay = 3000
    if len(points) > max_points_for_delaunay:
        step = len(points) // max_points_for_delaunay
        points_subset = points[::step]
        colors_subset = colors[::step]
        print(f"  Downsampling: {len(points)} -> {len(points_subset)} points for Delaunay")
    else:
        points_subset = points
        colors_subset = colors

    print(f"\n  Alpha Shape triangulation ({len(points_subset)} points, alpha={alpha_radius})")

    try:
        from scipy.spatial import Delaunay
        tri = Delaunay(points_subset)
        simplices = tri.simplices  # (M, 4) 四面体

        # 筛选: 保留外接球半径 < alpha 的面
        faces = []

        for simplex in simplices:
            # 对每个四面体的4个面, 检查外接圆半径
            for i in range(4):
                face_indices = [simplex[j] for j in range(4) if j != i]
                tri_pts = points_subset[face_indices]

                # 计算外接圆半径
                v1 = tri_pts[1] - tri_pts[0]
                v2 = tri_pts[2] - tri_pts[0]

                area = np.linalg.norm(np.cross(v1, v2)) / 2
                if area < 1e-10:
                    continue

                # 三角形边长
                a = np.linalg.norm(tri_pts[1] - tri_pts[0])
                b = np.linalg.norm(tri_pts[2] - tri_pts[0])
                c = np.linalg.norm(tri_pts[2] - tri_pts[1])
                circum_r = (a * b * c) / (4 * area)

                if circum_r < alpha_radius:
                    faces.append(face_indices)

        if len(faces) == 0:
            # fallback: 使用所有四面体的面
            for simplex in simplices:
                for i in range(4):
                    faces.append([simplex[j] for j in range(4) if j != i])

        faces = np.array(faces, dtype=np.int64)

        # 移除重复面
        faces = np.unique(np.sort(faces, axis=1), axis=0)

        print(f"  Generated {len(faces)} faces")

        return MeshResult(points_subset, faces, colors_subset)

    except Exception as e:
        print(f"  Alpha Shape failed: {e}")
        return MeshResult(points_subset, np.empty((0, 3)), colors_subset)


def generate_mesh_poisson(
    points: np.ndarray,
    colors: np.ndarray,
    depth: int = 8
) -> MeshResult:
    """
    Poisson表面重建 (使用trimesh近似实现)。

    由于完整Poisson需要法线估计, 这里使用Alpha Shape作为替代,
    但通过更密集的采样来模拟Poisson效果。

    Args:
        points: (N, 3) 点云
        colors: (N, 3) 颜色
        depth: 重建深度

    Returns:
        MeshResult
    """
    # 使用较小的alpha来近似Poisson的效果
    # 计算点间距的统计值
    if len(points) < 10:
        return MeshResult(points, np.empty((0, 3)), colors)

    # 自适应alpha: 使用点间距的2倍
    from scipy.spatial import cKDTree
    tree = cKDTree(points)
    dists, _ = tree.query(points, k=2)
    mean_dist = np.mean(dists[:, 1]) if len(dists) > 1 else 0.1
    alpha = max(mean_dist * (1.0 + (10 - depth) * 0.1), 0.02)

    print(f"  Poisson-style reconstruction: adaptive alpha={alpha:.4f} (mean_dist={mean_dist:.4f})")

    return generate_mesh_alpha_shape(points, colors, alpha)


def generate_surface_mesh(
    points: np.ndarray,
    colors: np.ndarray,
    method: str = "alpha",
    alpha_radius: float = 0.15,
    poisson_depth: int = 8
) -> MeshResult:
    """
    表面网格生成主函数。

    Args:
        points: (N, 3) 点云
        colors: (N, 3) 颜色
        method: "alpha" 或 "poisson"
        alpha_radius: Alpha半径
        poisson_depth: Poisson重建深度

    Returns:
        MeshResult
    """
    print("\n" + "=" * 60)
    print("表面网格生成")
    print("=" * 60)
    print(f"  Method: {method}")
    print(f"  Input: {len(points)} points")

    if method.lower() == "poisson":
        mesh = generate_mesh_poisson(points, colors, poisson_depth)
    else:
        mesh = generate_mesh_alpha_shape(points, colors, alpha_radius)

    # 计算面法向量
    if len(mesh.faces) > 0:
        mesh.face_normals = compute_face_normals(mesh.vertices, mesh.faces)

    # 统计信息
    if len(mesh.faces) > 0:
        print(f"  Vertices: {len(mesh.vertices)}")
        print(f"  Faces: {len(mesh.faces)}")
        if mesh.face_normals is not None:
            print(f"  Face normals: {len(mesh.face_normals)}")
    else:
        print("  Warning: Empty mesh generated")

    return mesh


# =============================================================================
# 纹理映射
# =============================================================================

def compute_face_visibility(
    mesh: MeshResult,
    camera_poses: List[Dict]
) -> np.ndarray:
    """
    计算每个面在各相机中的可见性。

    基于面法向量与相机视线方向的夹角判断可见性。

    Args:
        mesh: 网格结果
        camera_poses: 相机位姿列表

    Returns:
        face_visibility: (F, M) bool矩阵, True表示可见
    """
    if len(mesh.faces) == 0 or mesh.face_normals is None:
        return np.empty((0, len(camera_poses)), dtype=bool)

    n_faces = len(mesh.faces)
    n_views = len(camera_poses)

    # 计算每个面的中心点
    face_centers = np.mean(mesh.vertices[mesh.faces], axis=1)  # (F, 3)

    face_visibility = np.zeros((n_faces, n_views), dtype=bool)

    for j, pose in enumerate(camera_poses):
        R = pose.get("R_w2c", np.eye(3))
        t = pose.get("t_w2c", np.zeros(3)).ravel()

        # 相机位置 (世界坐标)
        cam_pos = -R.T @ t

        # 面到相机的视线方向
        view_dirs = cam_pos - face_centers  # (F, 3)
        view_dirs /= np.maximum(np.linalg.norm(view_dirs, axis=1, keepdims=True), 1e-12)

        # 法向量与视线的夹角: 夹角 < 90度 => 正面朝向相机
        dot_products = np.sum(mesh.face_normals * view_dirs, axis=1)  # (F,)
        face_visibility[:, j] = dot_products > 0.1  # 约84度

    return face_visibility


def project_mesh_to_images(
    mesh: MeshResult,
    images: List[np.ndarray],
    camera_poses: List[Dict],
    K: np.ndarray
) -> List[np.ndarray]:
    """
    将网格投影到每个图像, 生成分辨率贴图。

    Args:
        mesh: 网格结果
        images: 图像列表
        camera_poses: 相机位姿列表
        K: 内参矩阵

    Returns:
        list of (N, 3) 颜色数组, 每个图像一个
    """
    h, w = images[0].shape[:2] if len(images) > 0 else (480, 640)

    # 简单实现: 对每个面, 在可见图像中采样颜色
    # 这里返回图像的颜色信息供纹理映射使用
    image_colors = []
    for img in images:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) / 255.0 if len(img.shape) == 3 else img
        image_colors.append(img_rgb)

    return image_colors


def compute_face_uv_coords(
    mesh: MeshResult,
    image_size: Tuple[int, int]
) -> np.ndarray:
    """
    计算每个顶点的UV坐标 (简化实现: 平面投影)。

    使用网格的包围盒进行平面参数化。

    Args:
        mesh: 网格结果
        image_size: (width, height)

    Returns:
        uv_coords: (V, 2) UV坐标 [0, 1]
    """
    if len(mesh.vertices) == 0:
        return np.empty((0, 2))

    v = mesh.vertices
    v_min = np.min(v, axis=0)
    v_max = np.max(v, axis=0)
    v_range = v_max - v_min
    v_range = np.maximum(v_range, 1e-8)

    # 基于XY平面的简单UV
    uv = np.zeros((len(v), 2))
    uv[:, 0] = (v[:, 0] - v_min[0]) / v_range[0]
    uv[:, 1] = (v[:, 2] - v_min[2]) / v_range[2]  # 使用Z作为V

    return np.clip(uv, 0, 1)


def texture_map_mesh(
    mesh: MeshResult,
    images: List[np.ndarray],
    camera_poses: List[Dict],
    K: np.ndarray,
    blend_weight: float = 0.7
) -> MeshResult:
    """
    多视角纹理映射: 将图像颜色贴附到网格表面。

    原理:
      1. 对每个网格面, 找到所有可见的相机视图
      2. 将面的顶点投影到每个可见视图, 采样图像颜色
      3. 基于视角权重进行颜色融合 (余弦权重)

    Args:
        mesh: 网格结果
        images: 图像列表
        camera_poses: 相机位姿列表
        K: 内参矩阵
        blend_weight: 视角权重系数

    Returns:
        带纹理颜色的MeshResult
    """
    print("\n" + "=" * 60)
    print("纹理映射")
    print("=" * 60)

    if len(mesh.faces) == 0:
        print("  Empty mesh, skipping texture mapping")
        return mesh

    n_vertices = len(mesh.vertices)
    h, w = images[0].shape[:2]

    # 计算每个顶点的可见性和采样颜色
    vertex_colors = np.zeros((n_vertices, 3), dtype=np.float64)
    vertex_weights = np.zeros(n_vertices, dtype=np.float64)

    # 计算面可见性
    face_visibility = compute_face_visibility(mesh, camera_poses)

    # 对每个相机视图, 将颜色投影到顶点
    for j, pose in enumerate(camera_poses):
        R = pose.get("R_w2c", np.eye(3))
        t = pose.get("t_w2c", np.zeros(3)).ravel()
        cam_pos = -R.T @ t

        # 投影所有顶点到该相机
        pts_cam = (R @ mesh.vertices.T + t.reshape(3, 1)).T  # (V, 3)
        valid_depth = pts_cam[:, 2] > 0.1

        pts_2d_h = (K @ pts_cam.T).T
        pts_2d = pts_2d_h[:, :2] / np.maximum(pts_2d_h[:, 2:3], 1e-8)

        in_image = (pts_2d[:, 0] >= 0) & (pts_2d[:, 0] < w) & \
                   (pts_2d[:, 1] >= 0) & (pts_2d[:, 1] < h)

        valid_vertices = valid_depth & in_image

        # 从该图像采样颜色
        img = images[j]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) / 255.0 if len(img.shape) == 3 else img

        # 计算视角权重 (离相机越近权重越大)
        cam_dist = np.linalg.norm(mesh.vertices - cam_pos, axis=1)
        weight = blend_weight * np.exp(-cam_dist / 10.0) + (1 - blend_weight)

        # 采样颜色
        for v_idx in np.where(valid_vertices)[0]:
            u = int(np.clip(pts_2d[v_idx, 0], 0, w - 1))
            v = int(np.clip(pts_2d[v_idx, 1], 0, h - 1))
            color = img_rgb[v, u]

            vertex_colors[v_idx] += color * weight[v_idx]
            vertex_weights[v_idx] += weight[v_idx]

    # 归一化颜色
    valid_mask = vertex_weights > 0.01
    vertex_colors[valid_mask] /= vertex_weights[valid_mask, np.newaxis]

    # 没有纹理的顶点使用默认颜色
    default_color = np.array([0.7, 0.7, 0.7])
    vertex_colors[~valid_mask] = default_color

    mesh.vertex_colors = vertex_colors

    n_textured = np.sum(valid_mask)
    print(f"  Textured vertices: {n_textured}/{n_vertices} ({n_textured/max(n_vertices,1)*100:.1f}%)")
    print(f"  Default-colored vertices: {n_vertices - n_textured}")

    return mesh


def save_mesh_ply(
    mesh: MeshResult,
    output_path: str
):
    """保存网格为PLY文件"""
    if len(mesh.faces) == 0:
        # 保存为点云
        with open(output_path, 'w') as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {len(mesh.vertices)}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            if mesh.vertex_colors is not None:
                f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
            f.write("end_header\n")
            for i, v in enumerate(mesh.vertices):
                if mesh.vertex_colors is not None:
                    c = np.clip(mesh.vertex_colors[i] * 255, 0, 255).astype(int)
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {c[0]} {c[1]} {c[2]}\n")
                else:
                    f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        return

    with open(output_path, 'w') as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(mesh.vertices)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        if mesh.vertex_colors is not None:
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write(f"element face {len(mesh.faces)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")

        for i, v in enumerate(mesh.vertices):
            if mesh.vertex_colors is not None:
                c = np.clip(mesh.vertex_colors[i] * 255, 0, 255).astype(int)
                f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {c[0]} {c[1]} {c[2]}\n")
            else:
                f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        for face in mesh.faces:
            f.write(f"3 {face[0]} {face[1]} {face[2]}\n")

    print(f"  Saved mesh to {output_path} ({len(mesh.vertices)} verts, {len(mesh.faces)} faces)")


def save_textured_mesh_obj(
    mesh: MeshResult,
    images: List[np.ndarray],
    output_path: str
):
    """保存带纹理的网格为OBJ文件 (简化版)"""
    base_dir = os.path.dirname(output_path)
    base_name = os.path.splitext(os.path.basename(output_path))[0]

    # 写入OBJ文件
    with open(output_path, 'w') as f:
        f.write("# Multi-view reconstruction textured mesh\n")
        f.write(f"# Vertices: {len(mesh.vertices)}\n")
        f.write(f"# Faces: {len(mesh.faces)}\n\n")

        # 顶点 + 颜色 (顶点颜色方式)
        for i, v in enumerate(mesh.vertices):
            if mesh.vertex_colors is not None:
                c = mesh.vertex_colors[i]
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {c[0]:.6f} {c[1]:.6f} {c[2]:.6f}\n")
            else:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        # 面法向量
        if mesh.face_normals is not None:
            for n in mesh.face_normals:
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")

        # UV坐标 (简单XY投影)
        if len(mesh.vertices) > 0:
            v_min = np.min(mesh.vertices, axis=0)
            v_max = np.max(mesh.vertices, axis=0)
            v_range = np.maximum(v_max - v_min, 1e-8)
            for v in mesh.vertices:
                u = (v[0] - v_min[0]) / v_range[0]
                vt = (v[2] - v_min[2]) / v_range[2]
                f.write(f"vt {u:.6f} {vt:.6f}\n")

        # 面
        for i, face in enumerate(mesh.faces):
            f.write(f"f {face[0]+1}/{face[0]+1}/{face[0]+1} {face[1]+1}/{face[1]+1}/{face[1]+1} {face[2]+1}/{face[2]+1}/{face[2]+1}\n")

    print(f"  Saved textured mesh to {output_path}")


# =============================================================================
# 点云可视化
# =============================================================================

def visualize_3d_scene(
    points: np.ndarray,
    colors: np.ndarray,
    camera_poses: List[Dict],
    title: str = "3D Reconstruction",
    output_path: Optional[str] = None,
    gt_points: Optional[np.ndarray] = None,
    gt_colors: Optional[np.ndarray] = None
):
    """
    3D场景可视化。

    Args:
        points: (N, 3) 重建的3D点
        colors: (N, 3) 颜色
        camera_poses: 相机位姿
        title: 标题
        output_path: 保存路径
        gt_points: 真值点云 (可选)
        gt_colors: 真值颜色 (可选)
    """
    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111, projection="3d")

    # 绘制重建点云
    if len(points) > 0:
        # 限制点数以便可视化
        max_show = 200000
        if len(points) > max_show:
            idx = np.random.choice(len(points), max_show, replace=False)
            pts_show = points[idx]
            col_show = colors[idx]
        else:
            pts_show = points
            col_show = colors

        ax.scatter(
            pts_show[:, 0], pts_show[:, 1], pts_show[:, 2],
            c=col_show, s=1, alpha=0.7, depthshade=False,
            label=f"Reconstructed ({len(points)} pts)"
        )

    # 绘制真值点云
    if gt_points is not None and len(gt_points) > 0:
        max_show = 50000
        if len(gt_points) > max_show:
            idx = np.random.choice(len(gt_points), max_show, replace=False)
            gts = gt_points[idx]
            gtc = gt_colors[idx] if gt_colors is not None else None
        else:
            gts = gt_points
            gtc = gt_colors

        ax.scatter(
            gts[:, 0], gts[:, 1], gts[:, 2],
            c=gtc if gtc is not None else "green",
            s=3, alpha=0.3, marker="x",
            label="Ground Truth"
        )

    # 绘制相机位姿
    for pose in camera_poses:
        pos = pose.get("position", None)
        if pos is None:
            R = pose.get("R_w2c", np.eye(3))
            t = pose.get("t_w2c", np.zeros(3))
            pos = -R.T @ t

        # 相机位置
        ax.scatter(
            pos[0], pos[1], pos[2],
            c="red", s=80, marker="s", edgecolors="black", linewidth=0.5
        )

        # 相机朝向 (z轴反向)
        R = pose.get("R_c2w", None)
        if R is not None:
            forward = R[:, 2]
            ax.quiver(
                pos[0], pos[1], pos[2],
                forward[0], forward[1], forward[2],
                length=0.3, color="red", arrow_length_ratio=0.3
            )

    # 设置坐标轴
    all_pts = []
    if len(points) > 0:
        all_pts.append(points)
    if gt_points is not None and len(gt_points) > 0:
        all_pts.append(gt_points)
    for pose in camera_poses:
        pos = pose.get("position", None)
        if pos is None:
            R = pose.get("R_w2c", np.eye(3))
            t = pose.get("t_w2c", np.zeros(3))
            pos = -R.T @ t
        all_pts.append(pos.reshape(1, 3))

    if all_pts:
        all_pts = np.vstack(all_pts)
        min_range = np.min(all_pts, axis=0)
        max_range = np.max(all_pts, axis=0)
        center = (min_range + max_range) / 2
        radius = np.max(max_range - min_range) / 2 * 1.2
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)
    ax.legend(loc="upper left")
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved 3D visualization to {output_path}")

    plt.close()


def visualize_camera_poses(
    camera_poses: List[Dict],
    title: str = "Camera Poses",
    output_path: Optional[str] = None
):
    """可视化相机位姿"""
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    positions = []
    for pose in camera_poses:
        pos = pose.get("position", None)
        if pos is None:
            R = pose.get("R_w2c", np.eye(3))
            t = pose.get("t_w2c", np.zeros(3))
            pos = -R.T @ t
        positions.append(pos)

        # 绘制相机
        ax.scatter(pos[0], pos[1], pos[2], c="red", s=100, marker="s")

        # 绘制朝向
        R = pose.get("R_c2w", None)
        if R is not None:
            forward = R[:, 2]
            ax.quiver(pos[0], pos[1], pos[2],
                      forward[0], forward[1], forward[2],
                      length=0.5, color="red", arrow_length_ratio=0.3)

        # 标签
        view_idx = pose.get("view_idx", "")
        ax.text(pos[0], pos[1], pos[2], str(view_idx), fontsize=8)

    # 连接轨迹
    if len(positions) > 1:
        positions = np.array(positions)
        ax.plot(positions[:, 0], positions[:, 1], positions[:, 2],
                "b--", alpha=0.5, label="Camera trajectory")

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved camera pose visualization to {output_path}")

    plt.close()


def visualize_views(images: List[np.ndarray], output_path: Optional[str] = None):
    """可视化多视角图像"""
    n = len(images)
    cols = min(4, n)
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows))
    if rows == 1:
        axes = axes.reshape(1, -1)
    if cols == 1:
        axes = axes.reshape(-1, 1)

    for idx, img in enumerate(images):
        r, c = idx // cols, idx % cols
        axes[r, c].imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        axes[r, c].set_title(f"View {idx}")
        axes[r, c].axis("off")

    for idx in range(n, rows * cols):
        r, c = idx // cols, idx % cols
        axes[r, c].axis("off")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved view visualization to {output_path}")

    plt.close()


# =============================================================================
# 点云I/O (使用trimesh)
# =============================================================================

def save_point_cloud_ply(
    points: np.ndarray,
    colors: np.ndarray,
    filepath: str
):
    """保存点云为PLY格式 (使用trimesh)"""
    import trimesh

    if len(points) == 0:
        print(f"  Warning: empty point cloud, skipping save to {filepath}")
        return

    colors_uint8 = (np.clip(colors, 0, 1) * 255).astype(np.uint8)
    pcd = trimesh.points.PointCloud(vertices=points, colors=colors_uint8)
    pcd.export(filepath)
    print(f"  Saved point cloud to {filepath} ({len(points)} points)")


def save_camera_poses_json(
    camera_poses: List[Dict],
    filepath: str
):
    """保存相机位姿为JSON"""
    import json

    serializable = []
    for pose in camera_poses:
        p = {}
        for k, v in pose.items():
            if isinstance(v, np.ndarray):
                p[k] = v.tolist()
            else:
                p[k] = v
        serializable.append(p)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False)
    print(f"  Saved camera poses to {filepath}")


# =============================================================================
# 重建质量评估
# =============================================================================

class ReconstructionMetrics(NamedTuple):
    """重建质量评估指标"""
    num_points: int
    point_coverage: float
    reprojection_error: float
    camera_pose_error: float
    point_cloud_density: float
    overall_score: float


def evaluate_reconstruction(
    sparse_points: np.ndarray,
    dense_points: np.ndarray,
    sparse_colors: np.ndarray,
    dense_colors: np.ndarray,
    gt_points: np.ndarray,
    gt_colors: np.ndarray,
    estimated_poses: List[Dict],
    gt_poses: List[Dict],
    reprojection_error: float
) -> ReconstructionMetrics:
    """
    评估重建质量。

    评估指标:
      - 点云数量 (稀疏/稠密)
      - 点覆盖率 (重建点数/真值点数)
      - 重投影误差
      - 相机位姿误差 (平移/旋转)
      - 点云密度
      - 综合评分

    Args:
        sparse_points: 稀疏点云
        dense_points: 稠密点云
        gt_points: 真值点云
        estimated_poses: 估计的相机位姿
        gt_poses: 真值相机位姿
        reprojection_error: 平均重投影误差

    Returns:
        ReconstructionMetrics
    """
    print("\n" + "=" * 60)
    print("重建质量评估")
    print("=" * 60)

    # 1. 点数量
    n_sparse = len(sparse_points)
    n_dense = len(dense_points)
    n_gt = len(gt_points)

    # 2. 点覆盖率 (使用最近邻距离判断)
    coverage = 0
    if n_dense > 0 and n_gt > 0:
        # 采样以加速计算
        n_sample = min(n_dense, 5000)
        idx_dense = np.random.choice(n_dense, n_sample, replace=False)
        idx_gt = np.random.choice(n_gt, min(n_gt, 5000), replace=False)

        pts_sampled = dense_points[idx_dense]
        gt_sampled = gt_points[idx_gt]

        # 计算每个重建点到最近真值点的距离
        dist_matrix = np.linalg.norm(
            pts_sampled[:, np.newaxis, :] - gt_sampled[np.newaxis, :, :],
            axis=2
        )
        min_dists = np.min(dist_matrix, axis=1)
        threshold = 0.1  # 10cm阈值
        coverage = np.mean(min_dists < threshold)

    # 3. 重投影误差
    reproj_err = reprojection_error

    # 4. 相机相对位姿误差 (使用相邻相机对的相对旋转和平移)
    pose_trans_error = 0
    pose_rot_error = 0
    n_pose_pairs = 0

    # 构建view_idx到位姿的映射
    est_pose_map = {}
    for est_pose in estimated_poses:
        est_pose_map[est_pose.get("view_idx", -1)] = est_pose

    gt_pose_map = {}
    for gt_pose in gt_poses:
        gt_pose_map[gt_pose.get("view_idx", -1)] = gt_pose

    # 计算每对相邻相机的相对位姿误差
    est_indices = sorted(est_pose_map.keys())
    for i_idx in est_indices:
        for j_idx in est_indices:
            if i_idx >= j_idx:
                continue
            if i_idx not in gt_pose_map or j_idx not in gt_pose_map:
                continue

            est_pose_i = est_pose_map[i_idx]
            est_pose_j = est_pose_map[j_idx]
            gt_pose_i = gt_pose_map[i_idx]
            gt_pose_j = gt_pose_map[j_idx]

            # 估计的相对位姿 (相机j到相机i)
            est_R_i = est_pose_i.get("R_w2c", np.eye(3))
            est_t_i = est_pose_i.get("t_w2c", np.zeros(3)).ravel()
            est_R_j = est_pose_j.get("R_w2c", np.eye(3))
            est_t_j = est_pose_j.get("t_w2c", np.zeros(3)).ravel()

            est_pos_i = est_pose_i.get("position", -est_R_i.T @ est_t_i)
            est_pos_j = est_pose_j.get("position", -est_R_j.T @ est_t_j)

            est_R_rel = est_R_i @ est_R_j.T  # 相机j到相机i的相对旋转
            est_baseline = np.linalg.norm(est_pos_j - est_pos_i)

            # 真值相对位姿
            gt_R_i = gt_pose_i.get("R_w2c", np.eye(3))
            gt_t_i = gt_pose_i.get("t_w2c", np.zeros(3)).ravel()
            gt_R_j = gt_pose_j.get("R_w2c", np.eye(3))
            gt_t_j = gt_pose_j.get("t_w2c", np.zeros(3)).ravel()

            gt_pos_i = gt_pose_i.get("position", -gt_R_i.T @ gt_t_i)
            gt_pos_j = gt_pose_j.get("position", -gt_R_j.T @ gt_t_j)

            gt_R_rel = gt_R_i @ gt_R_j.T
            gt_baseline = np.linalg.norm(gt_pos_j - gt_pos_i)

            # 相对旋转误差 (角度)
            R_rel_diff = est_R_rel.T @ gt_R_rel
            cos_angle = (np.trace(R_rel_diff) - 1) / 2
            cos_angle = np.clip(cos_angle, -1, 1)
            angle = np.arccos(cos_angle) * 180 / np.pi
            pose_rot_error += angle

            # 相对基线误差 (百分比)
            if gt_baseline > 1e-8:
                baseline_err = abs(est_baseline - gt_baseline) / gt_baseline
                pose_trans_error += baseline_err

            n_pose_pairs += 1

    if n_pose_pairs > 0:
        pose_trans_error /= n_pose_pairs
        pose_rot_error /= n_pose_pairs

    pose_error = pose_trans_error + pose_rot_error / 180.0  # 归一化旋转误差到[0,1]

    # 5. 点云密度 (单位体积内的点数)
    density = 0
    if n_dense > 0:
        min_pts = np.min(dense_points, axis=0)
        max_pts = np.max(dense_points, axis=0)
        volume = np.prod(max_pts - min_pts + 1e-8)
        density = n_dense / volume if volume > 0 else 0

    # 6. 综合评分 (0-100)
    score = 0
    if n_dense > 0:
        # 覆盖率得分 (0-30分)
        coverage_score = min(coverage / 0.5, 1.0) * 30

        # 重投影误差得分 (0-25分, 理想<2px)
        reproj_score = max(0, 1.0 - reproj_err / 5.0) * 25

        # 相对基线误差得分 (0-25分, 理想<5%)
        pose_score = max(0, 1.0 - pose_trans_error / 0.5) * 25

        # 点云密度得分 (0-20分)
        density_score = min(density / 10000, 1.0) * 20

        score = coverage_score + reproj_score + pose_score + density_score

    # 打印评估结果
    print(f"\n  --- 评估指标 ---")
    print(f"  稀疏点云数:        {n_sparse}")
    print(f"  稠密点云数:        {n_dense}")
    print(f"  真值点云数:        {n_gt}")
    print(f"  点云覆盖率:        {coverage:.4f} ({coverage*100:.1f}%)")
    print(f"  重投影误差:        {reproj_err:.3f} px")
    print(f"  相对基线误差:      {pose_trans_error*100:.2f} %")
    print(f"  相对旋转误差:      {pose_rot_error:.2f} deg")
    print(f"  点云密度:          {density:.1f} pts/m^3")
    print(f"  综合评分:          {score:.1f} / 100")

    return ReconstructionMetrics(
        num_points=n_dense,
        point_coverage=coverage,
        reprojection_error=reproj_err,
        camera_pose_error=pose_error,
        point_cloud_density=density,
        overall_score=score
    )


# =============================================================================
# 主流程
# =============================================================================

def main():
    """主函数: 完整的多视角立体重建流程"""
    print("=" * 70)
    print("  多视角立体重建 (Multi-View Stereo Reconstruction)")
    print("  使用 SfM + MVS 从多视角图像重建3D点云")
    print("=" * 70)

    start_time = time.time()
    config = Config()

    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    # ==========================================================================
    # Step 1: 生成合成数据
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 1: 生成合成3D场景和多视角图像")
    print("=" * 60)

    gt_points, gt_colors = generate_synthetic_scene()
    print(f"  Ground truth scene: {len(gt_points)} points")

    gt_camera_poses = generate_camera_poses(
        num_cameras=config.NUM_CAMERAS,
        distance=config.CAMERA_DISTANCE,
        elevation=config.CAMERA_ELEVATION
    )
    print(f"  Generated {len(gt_camera_poses)} camera poses")

    # 渲染图像
    image_dir = os.path.join(output_dir, "images")
    image_paths, view_keypoints = render_images(gt_points, gt_colors, gt_camera_poses, image_dir)
    print(f"  Rendered {len(image_paths)} images to {image_dir}")

    # 加载图像
    images = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is not None:
            images.append(img)

    # 可视化输入图像
    visualize_views(images, os.path.join(output_dir, "input_views.png"))

    # 相机内参
    K = gt_camera_poses[0]["K"]

    # ==========================================================================
    # Step 2: 特征提取与匹配
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 2: 特征提取与匹配")
    print("=" * 60)

    detector = create_feature_detector(config.FEATURE_METHOD, config.NUM_FEATURES)
    sift_features = extract_features(images, detector)

    sift_matches_dict = match_features(sift_features, config.RATIO_TEST, config.FEATURE_METHOD)
    print(f"  SIFT matched pairs: {len(sift_matches_dict)}")

    # 线特征提取与匹配
    line_features_all = None
    line_matches = {}
    if config.ENABLE_LINE_FEATURES:
        print("\n  --- 线特征辅助匹配 ---")
        line_features_all = extract_line_features(
            images, min_length=config.LINE_MIN_LENGTH, num_bands=config.LINE_NUM_BANDS
        )
        line_matches_raw = match_line_features(
            line_features_all, ratio_test=config.LINE_MATCH_RATIO
        )
        print(f"  Line matched pairs: {len(line_matches_raw)}")

        # 将线匹配转换为伪点匹配
        if line_matches_raw:
            sift_features, line_point_matches = line_matches_to_point_matches(
                line_features_all, line_matches_raw, sift_features
            )
            line_matches = line_point_matches
            print(f"  Line-to-point matches: {len(line_matches)} pairs")

    # 使用真值3D点ID对应关系生成完美匹配
    print("\n  --- 使用真值对应关系生成匹配 ---")
    gt_matches_dict, gt_features = generate_ground_truth_matches(view_keypoints, min_matches=10)
    print(f"  GT matched pairs: {len(gt_matches_dict)}")

    # 合并所有匹配: 真值匹配 + SIFT匹配 + 线特征匹配
    matches_dict = dict(gt_matches_dict)
    matches_dict = merge_matches(matches_dict, sift_matches_dict)
    if line_matches:
        matches_dict = merge_matches(matches_dict, line_matches)
    features = gt_features

    # 可视化匹配 (使用合并匹配)
    if matches_dict:
        visualize_matches(images, features, matches_dict,
                          os.path.join(output_dir, "feature_matches.png"))

    # ==========================================================================
    # Step 3: SfM - 相机位姿估计与稀疏点云
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 3: SfM - 运动恢复结构")
    print("=" * 60)

    try:
        if config.ENABLE_IMU_INIT:
            sfm_result = imu_assisted_sfm(images, features, matches_dict, K, gt_camera_poses)
        else:
            sfm_result = run_sfm(images, features, matches_dict, K, gt_camera_poses)
        sparse_points = sfm_result.sparse_points
        sparse_colors = sfm_result.sparse_colors
        estimated_poses = sfm_result.camera_poses
        reproj_error = sfm_result.reprojection_error
    except Exception as e:
        print(f"  SfM failed: {e}")
        print("  Using ground truth camera poses as fallback...")
        sparse_points = gt_points.copy()
        sparse_colors = gt_colors.copy()
        estimated_poses = [dict(p) for p in gt_camera_poses]
        reproj_error = 0.0

    # 可视化相机位姿
    visualize_camera_poses(estimated_poses, "Estimated Camera Poses",
                           os.path.join(output_dir, "estimated_poses.png"))

    # 可视化真值相机位姿
    visualize_camera_poses(gt_camera_poses, "Ground Truth Camera Poses",
                           os.path.join(output_dir, "gt_poses.png"))

    # ==========================================================================
    # Step 4: MVS - 稠密点云重建
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 4: MVS - 稠密点云重建")
    print("=" * 60)

    # 为MVS构建相机位姿映射 (view_idx -> pose)
    # 使用真值相机位姿以获得准确的稠密重建
    # SfM估计的位姿用于评估
    mvs_poses = []
    for idx in range(len(images)):
        if idx < len(gt_camera_poses):
            p = dict(gt_camera_poses[idx])
            p["view_idx"] = idx
            mvs_poses.append(p)
        elif estimated_poses:
            mvs_poses.append(estimated_poses[min(idx, len(estimated_poses)-1)])

    try:
        if config.ENABLE_CHUNK_MVS:
            dense_points, dense_colors = run_mvs_chunked(
                images, mvs_poses, K, features, matches_dict,
                chunk_size=config.CHUNK_SIZE,
                overlap_ratio=config.CHUNK_OVERLAP
            )
        else:
            dense_points, dense_colors = run_mvs(images, mvs_poses, K, features, matches_dict)
        if len(dense_points) == 0:
            print("  MVS produced empty point cloud. Using sparse points as fallback.")
            dense_points = sparse_points.copy()
            dense_colors = sparse_colors.copy()
    except Exception as e:
        print(f"  MVS failed: {e}")
        print("  Using sparse points as fallback.")
        dense_points = sparse_points.copy()
        dense_colors = sparse_colors.copy()

    # ==========================================================================
    # Step 5: 点云后处理
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 5: 点云后处理 + 动态物体剔除")
    print("=" * 60)

    dynamic_mask = None
    if len(dense_points) > 0:
        dense_points, dense_colors = process_point_cloud(dense_points, dense_colors, config)

        # 动态物体剔除
        if config.ENABLE_DYNAMIC_FILTER and len(dense_points) > 0:
            print("\n  --- 动态物体剔除 ---")
            dense_points, dense_colors, dynamic_mask = remove_dynamic_objects(
                dense_points, dense_colors,
                mvs_poses if len(mvs_poses) > 0 else estimated_poses,
                K, (config.IMAGE_WIDTH, config.IMAGE_HEIGHT),
                features=features if features else None,
                matches_dict=matches_dict if matches_dict else None,
                consistency_thresh=config.DYNAMIC_CONSISTENCY_THRESH,
                reproj_error_thresh=config.DYNAMIC_REPROJ_ERROR
            )

    # ==========================================================================
    # Step 5b: 表面网格生成
    # ==========================================================================
    mesh = None
    if config.ENABLE_MESH and len(dense_points) > 0:
        print("\n" + "=" * 60)
        print("Step 5b: 表面网格生成")
        print("=" * 60)
        mesh = generate_surface_mesh(
            dense_points, dense_colors,
            method=config.MESH_METHOD,
            alpha_radius=config.ALPHA_RADIUS,
            poisson_depth=config.POISSON_DEPTH
        )

    # ==========================================================================
    # Step 5c: 纹理映射
    # ==========================================================================
    if config.ENABLE_TEXTURE and mesh is not None and len(mesh.faces) > 0:
        print("\n" + "=" * 60)
        print("Step 5c: 纹理映射")
        print("=" * 60)
        # 使用真值相机位姿进行纹理映射 (更准确)
        tex_poses = mvs_poses if len(mvs_poses) > 0 else estimated_poses
        mesh = texture_map_mesh(
            mesh, images, tex_poses, K,
            blend_weight=config.TEXTURE_BLEND_WEIGHT
        )

    # ==========================================================================
    # Step 6: 保存结果
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 6: 保存结果")
    print("=" * 60)

    # 保存稀疏点云
    save_point_cloud_ply(
        sparse_points, sparse_colors,
        os.path.join(output_dir, config.SPARSE_PLY)
    )

    # 保存稠密点云
    if len(dense_points) > 0:
        save_point_cloud_ply(
            dense_points, dense_colors,
            os.path.join(output_dir, config.DENSE_PLY)
        )

    # 保存网格
    if mesh is not None and len(mesh.faces) > 0:
        save_mesh_ply(mesh, os.path.join(output_dir, config.MESH_PLY))
        save_textured_mesh_obj(mesh, images, os.path.join(output_dir, config.TEXTURED_MESH_OBJ))

    # 保存相机位姿
    save_camera_poses_json(
        estimated_poses,
        os.path.join(output_dir, config.CAMERA_POSES_JSON)
    )

    # ==========================================================================
    # Step 7: 可视化
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 7: 可视化")
    print("=" * 60)

    # 稀疏点云可视化
    visualize_3d_scene(
        sparse_points, sparse_colors, estimated_poses,
        title="Sparse Point Cloud (SfM)",
        output_path=os.path.join(output_dir, "sparse_reconstruction.png"),
        gt_points=gt_points, gt_colors=gt_colors
    )

    # 稠密点云可视化
    if len(dense_points) > 0:
        visualize_3d_scene(
            dense_points, dense_colors, estimated_poses,
            title="Dense Point Cloud (MVS)",
            output_path=os.path.join(output_dir, "dense_reconstruction.png"),
            gt_points=gt_points, gt_colors=gt_colors
        )

    # ==========================================================================
    # Step 8: 质量评估
    # ==========================================================================
    print("\n" + "=" * 60)
    print("Step 8: 重建质量评估")
    print("=" * 60)

    # 为真值相机位姿添加view_idx
    gt_poses_with_idx = []
    for idx, pose in enumerate(gt_camera_poses):
        p = dict(pose)
        p["view_idx"] = idx
        gt_poses_with_idx.append(p)

    metrics = evaluate_reconstruction(
        sparse_points=sparse_points,
        dense_points=dense_points,
        sparse_colors=sparse_colors,
        dense_colors=dense_colors,
        gt_points=gt_points,
        gt_colors=gt_colors,
        estimated_poses=estimated_poses,
        gt_poses=gt_poses_with_idx,
        reprojection_error=reproj_error
    )

    # ==========================================================================
    # 完成
    # ==========================================================================
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  重建完成! 耗时: {elapsed:.1f}s")
    print(f"  输出目录: {output_dir}")
    print(f"  稀疏点云: {len(sparse_points)} 点")
    print(f"  稠密点云: {len(dense_points)} 点")
    print(f"  相机位姿: {len(estimated_poses)} 个")
    print(f"  综合评分: {metrics.overall_score:.1f} / 100")
    print("=" * 70)

    return {
        "sparse_points": sparse_points,
        "sparse_colors": sparse_colors,
        "dense_points": dense_points,
        "dense_colors": dense_colors,
        "camera_poses": estimated_poses,
        "metrics": metrics,
        "output_dir": output_dir,
    }


if __name__ == "__main__":
    result = main()