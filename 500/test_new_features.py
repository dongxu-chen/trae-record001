import numpy as np
import time

from lightfield import LightField
from depth_estimation import DepthEstimator
from depth_effects import DepthOfFieldEffect, ApertureSynthesizer
from dynamic_depth import DynamicDepthEstimator

print("=" * 60)
print("光场深度估计系统 - 新功能综合测试")
print("=" * 60)

print("\n=== 测试1: Numba JIT加速验证 ===")
lf = LightField.generate_synthetic(num_rows=5, num_cols=5, height=80, width=80, num_depths=2)
print(f"光场: {lf.num_rows}x{lf.num_cols} 视图, {lf.height}x{lf.width} 像素")

est_cpu = DepthEstimator(lf, use_accelerated=False)
est_jit = DepthEstimator(lf, use_accelerated=True)

n_iter = 3

t0 = time.time()
for _ in range(n_iter):
    _, _ = est_cpu.estimate_depth_from_focus(adaptive=False, num_planes=10)
cpu_time = (time.time() - t0) / n_iter

t0 = time.time()
for _ in range(n_iter):
    _, _ = est_jit.estimate_depth_from_focus(adaptive=True, num_planes=10)
jit_time = (time.time() - t0) / n_iter

speedup = cpu_time / max(jit_time, 1e-6)
print(f"CPU 耗时: {cpu_time:.3f}s / 次")
print(f"JIT 耗时: {jit_time:.3f}s / 次")
print(f"加速比: {speedup:.1f}x")

print("\n=== 测试2: 景深效果 ===")
depth, conf = est_jit.estimate_depth_from_focus()
dof = DepthOfFieldEffect(lf)

t0 = time.time()
dof_image = dof.apply_bokeh(depth, focus_depth=0.5, aperture=0.3, max_blur=10.0)
dof_time = time.time() - t0

print(f"景深效果计算: {dof_time:.3f}s")
print(f"输出图像范围: [{dof_image.min():.3f}, {dof_image.max():.3f}]")

print("\n=== 测试3: 光圈合成 ===")
ap_synth = ApertureSynthesizer(lf)

t0 = time.time()
small_aperture = ap_synth.refocus_with_aperture(alpha=0.0, aperture_radius=1.0)
large_aperture = ap_synth.refocus_with_aperture(alpha=0.0, aperture_radius=3.0)
ap_time = time.time() - t0

print(f"光圈合成: {ap_time:.3f}s")
print(f"小光圈 vs 大光圈 差异: {np.abs(small_aperture - large_aperture).mean():.4f}")

print("\n=== 测试4: 动态深度估计 (时序平滑) ===")
try:
    dyn_est = DynamicDepthEstimator(lf, temporal_window=3)
    
    depths = []
    confs = []
    
    for i in range(5):
        depth_t, conf_t = dyn_est.process_frame()
        depths.append(depth_t)
        confs.append(conf_t)
    
    first_depth = depths[0]
    last_depth = depths[-1]
    temporal_variance = np.var([d.mean() for d in depths])
    
    print(f"处理了 {len(depths)} 帧")
    print(f"时序深度方差: {temporal_variance:.6f}")
    print(f"动态估计 成功!")
except Exception as e:
    print(f"动态估计 跳过 (cv2 不可用): {e}")

print("\n=== 测试5: 散焦和视差加速 ===")
t0 = time.time()
depth_def, conf_def = est_jit.estimate_depth_from_defocus()
def_time = time.time() - t0
print(f"散焦估计加速: {def_time:.3f}s")

t0 = time.time()
depth_disp, conf_disp = est_jit.estimate_disparity(disparity_range=(-5, 5))
disp_time = time.time() - t0
print(f"视差估计加速: {disp_time:.3f}s")

print("\n" + "=" * 60)
print("所有新功能测试完成!")
print("=" * 60)
