import numpy as np
import sys

print("=" * 60)
print("光场相机重聚焦系统 - 基本功能测试")
print("=" * 60)

try:
    from lf_decoder import create_gradient_lightfield
    print("✓ lf_decoder.py 导入成功")
except Exception as e:
    print(f"✗ lf_decoder.py 导入失败: {e}")
    sys.exit(1)

try:
    from lf_refocus import LightFieldRefocus, evaluate_sharpness
    print("✓ lf_refocus.py 导入成功")
except Exception as e:
    print(f"✗ lf_refocus.py 导入失败: {e}")
    sys.exit(1)

try:
    from depth_estimation import DepthEstimator
    print("✓ depth_estimation.py 导入成功")
except Exception as e:
    print(f"✗ depth_estimation.py 导入失败: {e}")
    sys.exit(1)

try:
    from gpu_accelerator import check_gpu_available
    print("✓ gpu_accelerator.py 导入成功")
except Exception as e:
    print(f"✗ gpu_accelerator.py 导入失败: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("生成测试光场数据...")
print("=" * 60)

lf_data = create_gradient_lightfield(size=(128, 128), num_views=7, num_lenses=16)
print(f"光场数据维度: {lf_data.shape}")
print(f"  - 视角数量 (y): {lf_data.shape[0]}")
print(f"  - 视角数量 (x): {lf_data.shape[1]}")
print(f"  - 图像高度: {lf_data.shape[2]}")
print(f"  - 图像宽度: {lf_data.shape[3]}")
print(f"  - 颜色通道: {lf_data.shape[4]}")

print("\n" + "=" * 60)
print("测试重聚焦算法...")
print("=" * 60)

refocus = LightFieldRefocus(lf_data, focal_depth_range=(-3.0, 3.0))

for alpha in [-2.0, 0.0, 2.0]:
    result = refocus.refocus_fast(alpha, aperture_size=0.8)
    sharpness = evaluate_sharpness(result)
    print(f"  α = {alpha:+.1f}: 清晰度 = {sharpness:.1f}")

print("✓ 重聚焦算法测试通过")

print("\n" + "=" * 60)
print("测试全焦合成...")
print("=" * 60)

all_focus, depth_map = refocus.all_in_focus(num_planes=7)
print(f"全焦图像尺寸: {all_focus.shape}")
print(f"深度图尺寸: {depth_map.shape}")
print(f"深度范围: [{depth_map.min():.3f}, {depth_map.max():.3f}]")
print("✓ 全焦合成测试通过")

print("\n" + "=" * 60)
print("测试深度估计...")
print("=" * 60)

depth_estimator = DepthEstimator(lf_data)
depth = depth_estimator.estimate_depth_stereo(method='bm')
print(f"立体匹配深度图尺寸: {depth.shape}")
print("✓ 深度估计测试通过")

print("\n" + "=" * 60)
print("检查GPU加速能力...")
print("=" * 60)

gpu_info = check_gpu_available()
print(f"CuPy可用: {gpu_info['cupy_available']}")
print(f"Numba可用: {gpu_info['numba_available']}")
if 'cuda_available' in gpu_info:
    print(f"CUDA可用: {gpu_info['cuda_available']}")
if 'gpu_count' in gpu_info and gpu_info['gpu_count'] > 0:
    print(f"检测到 {gpu_info['gpu_count']} 个GPU设备")

print("\n" + "=" * 60)
print("所有测试通过！系统已就绪。")
print("=" * 60)
print("\n运行以下命令启动GUI:")
print("  python main.py --mode gui")
print("\n运行以下命令查看演示:")
print("  python main.py --mode demo")
print("\n运行以下命令测试GPU:")
print("  python main.py --mode gpu")
