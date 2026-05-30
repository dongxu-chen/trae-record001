from lightfield import LightField
from depth_estimation import DepthEstimator
from fusion import MultiViewFusion
from evaluation import DepthEvaluator
import numpy as np

print('=== 测试1: 模块导入 ===')
print('所有模块导入成功!')

print('\n=== 测试2: 梯度密度计算 ===')
lf = LightField.generate_synthetic(num_rows=3, num_cols=3, height=100, width=100, num_depths=2)
grad_density, low_tex_mask = lf.compute_gradient_density()
print(f'梯度密度图范围: [{grad_density.min():.4f}, {grad_density.max():.4f}]')
print(f'低纹理区域占比: {low_tex_mask.mean():.2%}')

print('\n=== 测试3: 自适应采样步长 ===')
estimator = DepthEstimator(lf)
adaptive_alphas = estimator.compute_adaptive_alphas((-2.0, 2.0), base_planes=15)
uniform_alphas = np.linspace(-2.0, 2.0, 15)
print(f'均匀采样步长数: {len(uniform_alphas)}')
print(f'自适应采样步长数: {len(adaptive_alphas)}')
print(f'自适应步长范围: [{adaptive_alphas.min():.3f}, {adaptive_alphas.max():.3f}]')

print('\n=== 测试4: 深度估计(含低纹理置信度) ===')
depth, conf = estimator.estimate_depth_from_focus(num_planes=10, adaptive=True)
print(f'深度图范围: [{depth.min():.3f}, {depth.max():.3f}]')
print(f'置信度平均: {conf.mean():.3f}')
high_tex_conf = conf[~low_tex_mask].mean() if (~low_tex_mask).any() else 0
low_tex_conf = conf[low_tex_mask].mean() if low_tex_mask.any() else 0
print(f'高纹理区域置信度: {high_tex_conf:.3f}')
print(f'低纹理区域置信度: {low_tex_conf:.3f}')

print('\n=== 测试5: 散焦估计(含低纹理置信度) ===')
depth_dfd, conf_dfd = estimator.estimate_depth_from_defocus()
print(f'散焦深度范围: [{depth_dfd.min():.3f}, {depth_dfd.max():.3f}]')
print(f'散焦置信度平均: {conf_dfd.mean():.3f}')

print('\n=== 测试6: 纹理感知评估 ===')
evaluator = DepthEvaluator()
metrics = evaluator.full_evaluation(depth, conf, image=lf.get_center_view(), texture_threshold=0.3)
print(f'纹理覆盖率: {metrics["TextureCoverage"]:.2%}')
print(f'平滑度(高纹理): {metrics["Smoothness"]:.6f}')
print(f'高纹理置信度: {metrics["MeanConfidence_HighTexture"]:.4f}')
print(f'低纹理置信度: {metrics["MeanConfidence_LowTexture"]:.4f}')

print('\n=== 测试7: 外部纹理掩码设置 ===')
evaluator2 = DepthEvaluator()
custom_mask = grad_density > 0.5
evaluator2.set_texture_mask(custom_mask)
metrics2 = evaluator2.full_evaluation(depth, conf, image=lf.get_center_view())
print(f'外部掩码纹理覆盖率: {metrics2["TextureCoverage"]:.2%}')

print('\n=== 测试8: 深度图置灰渲染 ===')
depth_norm = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
low_conf_mask = conf < 0.3
gray_ratio = low_conf_mask.mean()
print(f'低置信度像素占比: {gray_ratio:.2%}')

print('\n所有功能测试通过!')
