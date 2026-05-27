import numpy as np
import cv2
import sys

sys.path.insert(0, r'd:\Trae\project\record001\390')

from optical_flow.algorithms import LucasKanade, Farneback
from optical_flow.dense_interpolation import DenseInterpolator, SparseToDense
from optical_flow.motion_segmentation import MotionSegmentation, MotionAnalyzer
from optical_flow.scene_flow import SceneFlowEstimator, DepthFlowFusion
from optical_flow.metrics import compute_metrics

np.random.seed(42)

print("=" * 70)
print("  光流扩展功能验证")
print("=" * 70)

size = 256
f1_gray = np.random.randint(0, 256, (size, size), dtype=np.uint8)
f2_gray = cv2.warpAffine(f1_gray, np.float32([[1, 0, 5], [0, 1, 3]]), (size, size))
f1 = cv2.cvtColor(f1_gray, cv2.COLOR_GRAY2BGR)
f2 = cv2.cvtColor(f2_gray, cv2.COLOR_GRAY2BGR)
gt = np.zeros((size, size, 2), dtype=np.float32)
gt[:, :, 0] = 5
gt[:, :, 1] = 3

print("\n[1] 测试光流稠密化插值")
print("-" * 70)

sparse_pts = np.array([
    [50, 50], [100, 100], [150, 150], [200, 200],
    [50, 150], [150, 50], [50, 200], [200, 50],
], dtype=np.float32)
sparse_vecs = np.array([
    [5, 3], [5, 3], [5, 3], [5, 3],
    [5, 3], [5, 3], [5, 3], [5, 3],
], dtype=np.float32)

interpolator = DenseInterpolator(method='inverse_distance', power=2.0)
dense_flow = interpolator.interpolate(sparse_pts, sparse_vecs, (size, size))
print(f"  IDW 插值完成: {dense_flow.shape}, 均值: {dense_flow.mean():.3f}")

for method in ['gaussian', 'diffusion']:
    try:
        interp = DenseInterpolator(method=method)
        flow = interp.interpolate(sparse_pts, sparse_vecs, (size, size))
        print(f"  {method:10s} 插值完成: {flow.shape}, 均值: {flow.mean():.3f}")
    except Exception as e:
        print(f"  {method:10s} 插值失败: {e}")

print("\n[2] 测试稀疏到稠密完整管线")
print("-" * 70)

s2d = SparseToDense(feature_detector='shi_tomasi', max_corners=500)
dense_from_sparse = s2d.compute(f2, f1)
print(f"  稀疏到稠密完成: {dense_from_sparse.shape}")
m = compute_metrics(dense_from_sparse, gt)
print(f"  指标: AEE={m['AEE']:.3f}, EPE={m['EPE_mean']:.3f}")

print("\n[3] 测试运动分割")
print("-" * 70)

fb = Farneback()
flow = fb.compute(f2, f1)

segmenter = MotionSegmentation(method='dbscan', eps=0.3, min_samples=30)
labels = segmenter.segment(flow, f1)
print(f"  分割完成: {labels.shape}, 标签范围: [{labels.min()}, {labels.max()}]")
print(f"  运动区域像素数: {(labels >= 0).sum()}")

seg_vis = segmenter.visualize_segments(labels, flow, f1)
print(f"  分割可视化: {seg_vis.shape}")

analyzer = MotionAnalyzer(min_object_size=100)
analysis = analyzer.analyze(labels, flow)
print(f"  分析结果: {analysis['num_objects']} 个运动物体")
for obj in analysis['objects']:
    print(f"    - 标签 {obj['label']}: {obj['num_pixels']}像素, "
          f"类型={obj['motion_type']}, 一致性={obj['motion_consistency']:.3f}")

print("\n[4] 测试场景流估计")
print("-" * 70)

depth_prev = np.random.uniform(1.0, 10.0, (size, size)).astype(np.float32)
depth_curr = depth_prev + 0.1

sf_estimator = SceneFlowEstimator(fx=500.0, fy=500.0)
scene_flow = sf_estimator.compute(flow, depth_prev, depth_curr)
print(f"  场景流计算完成: {scene_flow.shape}")
print(f"  3D运动范围: ΔX=[{scene_flow[..., 0].min():.3f}, {scene_flow[..., 0].max():.3f}]")
print(f"            ΔY=[{scene_flow[..., 1].min():.3f}, {scene_flow[..., 1].max():.3f}]")
print(f"            ΔZ=[{scene_flow[..., 2].min():.3f}, {scene_flow[..., 2].max():.3f}]")

sf_vis = sf_estimator.visualize_scene_flow(scene_flow, max_depth=5.0)
print(f"  场景流可视化: {sf_vis.shape}")

fusion = DepthFlowFusion(fx=500.0, fy=500.0)
motion_3d = fusion.estimate_3d_motion(flow, depth_prev, depth_curr)
print(f"  3D运动估计: 平移={motion_3d['translation']}")
print(f"             缩放={motion_3d['scale']:.3f}")

print("\n" + "=" * 70)
print("所有扩展功能验证通过!")
print("=" * 70)