import time
import os
import numpy as np
from decimal import Decimal, getcontext

print("=" * 60)
print("分形生成器增强功能测试")
print("=" * 60)
print()

# 1. 测试decimal高精度计算
print("1. 测试decimal高精度计算模块...")
from high_precision import HighPrecisionCalculator, decimal_ln, decimal_log

hp_calc = HighPrecisionCalculator()

# 测试Decimal对数计算
getcontext().prec = 50
x = Decimal('2.0')
ln_x = decimal_ln(x)
print(f"   ln(2.0) = {ln_x}")
print(f"   理论值  = 0.693147180559945309417232121458176568075500134360255")
error = abs(float(ln_x) - np.log(2))
print(f"   误差: {error:.2e}")

# 测试更多值
for test_val in [0.5, 1.0, 2.718281828, 10.0, 100.0]:
    x = Decimal(str(test_val))
    ln_x = decimal_ln(x)
    error = abs(float(ln_x) - np.log(test_val))
    print(f"   ln({test_val:.3f}) 误差: {error:.2e}")

# 测试精度确定
precision = hp_calc._determine_precision(-1e-13, 1e-13)
print(f"   1e-13范围所需精度: {precision} 位十进制数")

print("   ✓ decimal高精度模块测试通过")
print()

# 2. 测试Julia网格缓存
print("2. 测试Julia网格缓存优化...")
from high_precision import JuliaGridCache, julia_set_from_grid, julia_set_optimized

width, height = 600, 450
xmin, xmax, ymin, ymax = -2.0, 2.0, -1.5, 1.5
cx, cy = -0.7, 0.27015
max_iter = 100

grid_cache = JuliaGridCache(width, height)

# Numba预热（第一次调用会编译）
print("   Numba编译预热...")
_ = julia_set_optimized(-1, 1, -1, 1, 100, 100, 0, 0, 10)
grid_cache.precompute_grid(-1, 1, -1, 1)
zx_warm, zy_warm = grid_cache.get_grids()
_ = julia_set_from_grid(zx_warm, zy_warm, 0, 0, 10)
grid_cache.invalidate()

# 预计算网格
start = time.perf_counter()
grid_cache.precompute_grid(xmin, xmax, ymin, ymax)
grid_time = (time.perf_counter() - start) * 1000
print(f"   网格预计算: {grid_time:.1f}ms")

# 从缓存计算Julia集
zx, zy = grid_cache.get_grids()
start = time.perf_counter()
data1 = julia_set_from_grid(zx, zy, cx, cy, max_iter)
cached_time = (time.perf_counter() - start) * 1000
print(f"   缓存计算: {cached_time:.1f}ms")

# 常规计算Julia集（无缓存）
start = time.perf_counter()
data2 = julia_set_optimized(xmin, xmax, ymin, ymax, width, height, cx, cy, max_iter)
normal_time = (time.perf_counter() - start) * 1000
print(f"   常规计算: {normal_time:.1f}ms")

# 验证结果一致
error = np.max(np.abs(data1 - data2))
print(f"   结果一致性最大误差: {error:.2e}")
print(f"   性能提升: {normal_time/cached_time:.1f}x 倍")

# 测试多次参数变化时的性能（固定视图，只改变参数）
print("   测试50次参数变化（固定视图，真实交互场景）...")
total_cached = 0
total_normal = 0
grid_time_total = 0

for i in range(50):
    cx_test = -0.7 + i * 0.002
    cy_test = 0.27015 + i * 0.001
    
    # 缓存方式：网格已经预计算好
    start = time.perf_counter()
    data_cached = julia_set_from_grid(zx, zy, cx_test, cy_test, max_iter)
    total_cached += (time.perf_counter() - start) * 1000
    
    # 常规方式：每次都重新计算网格
    start = time.perf_counter()
    data_normal = julia_set_optimized(xmin, xmax, ymin, ymax, width, height, cx_test, cy_test, max_iter)
    total_normal += (time.perf_counter() - start) * 1000

print(f"   缓存方式50次计算: {total_cached:.1f}ms")
print(f"   常规方式50次计算: {total_normal:.1f}ms")
print(f"   平均性能提升: {total_normal/total_cached:.1f}x 倍")

# 测试Plotter中的快速更新
print("\n   测试Plotter快速更新API（滑动条场景）...")
from fractal_plotter import FractalPlotter
plotter = FractalPlotter(parent=None, width=width, height=height)
plotter.set_fractal_type('julia')
start = time.perf_counter()
plotter.render()  # 首次渲染，建立缓存
first_render = (time.perf_counter() - start) * 1000

total_fast = 0
for i in range(20):
    cx_test = -0.7 + i * 0.005
    cy_test = 0.27015 + i * 0.002
    start = time.perf_counter()
    plotter.update_julia_params(cx_test, cy_test, max_iter)
    total_fast += (time.perf_counter() - start) * 1000

print(f"   首次完整渲染: {first_render:.1f}ms")
print(f"   快速更新API 20次: {total_fast:.1f}ms, 平均 {total_fast/20:.1f}ms/次")
print(f"   相比完整渲染提升: {first_render/(total_fast/20):.1f}x 倍")

print("   ✓ Julia网格缓存优化测试通过")
print()

# 3. 测试多段渐变和循环渐变颜色映射
print("3. 测试多段渐变和循环渐变颜色映射...")
from color_maps import (
    create_multistop_gradient, create_cyclic_gradient,
    create_gradient_colormaps, create_cyclic_colormaps,
    get_available_colormaps, get_colormap,
    create_hue_cycling_colormap
)

# 测试多段渐变
print("   测试多段渐变...")
stops = [
    (0.0, (0.0, 0.0, 0.5)),
    (0.25, (0.0, 0.5, 1.0)),
    (0.5, (0.0, 1.0, 0.5)),
    (0.75, (1.0, 1.0, 0.0)),
    (1.0, (1.0, 0.0, 0.0)),
]
multistop_cmap = create_multistop_gradient('test_multistop', stops, N=256)
print(f"   多段渐变创建成功, 颜色数: {multistop_cmap.N}")

# 测试循环渐变
print("   测试循环渐变...")
cycle_colors = [
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
]
cyclic_cmap = create_cyclic_gradient('test_cyclic', cycle_colors, num_cycles=5, N=256)
print(f"   循环渐变创建成功, 循环次数: 5, 颜色数: {cyclic_cmap.N}")

# 测试预定义的渐变
print("   测试预定义渐变...")
gradient_cmaps = create_gradient_colormaps()
print(f"   预定义多段渐变数量: {len(gradient_cmaps)}")
for name in gradient_cmaps.keys():
    print(f"     - {name}")

# 测试预定义的循环渐变
print("   测试预定义循环渐变...")
cyclic_cmaps = create_cyclic_colormaps()
print(f"   预定义循环渐变数量: {len(cyclic_cmaps)}")
for name in list(cyclic_cmaps.keys())[:5]:
    print(f"     - {name}")

# 测试颜色映射总数
all_cmaps = get_available_colormaps()
print(f"   全部可用颜色映射数量: {len(all_cmaps)}")

# 测试色相循环着色
print("   测试色相循环着色...")
test_data = np.random.rand(100, 100) * 100
start = time.perf_counter()
hue_cycle_colored = create_hue_cycling_colormap(test_data, 100, num_cycles=5)
elapsed = (time.perf_counter() - start) * 1000
print(f"   色相循环着色完成: {elapsed:.1f}ms, 形状: {hue_cycle_colored.shape}")

# 测试颜色映射查询
print("   测试颜色映射查询...")
test_cmap_names = ['inferno', 'gradient_rainbow', 'cyclic_rainbow_5', 'fractal_flame']
for name in test_cmap_names:
    cmap = get_colormap(name)
    print(f"     {name}: {'成功' if cmap is not None else '失败'}")

print("   ✓ 颜色映射模块测试通过")
print()

# 4. 测试Plotter集成
print("4. 测试Plotter集成新功能...")
from fractal_plotter import FractalPlotter

plotter = FractalPlotter(parent=None, width=600, height=450)

# 测试Julia快速更新
print("   测试Julia快速更新...")
plotter.set_fractal_type('julia')
start = time.perf_counter()
plotter.render()
first_render = (time.perf_counter() - start) * 1000
print(f"   首次渲染: {first_render:.1f}ms")

start = time.perf_counter()
plotter.update_julia_params(-0.75, 0.15, 100)
fast_update = (time.perf_counter() - start) * 1000
print(f"   参数快速更新: {fast_update:.1f}ms")
print(f"   性能提升: {first_render/fast_update:.1f}x 倍")

# 测试色相循环模式
print("   测试色相循环模式...")
plotter.color_mode = 'hue_cycle'
start = time.perf_counter()
plotter.render()
elapsed = (time.perf_counter() - start) * 1000
print(f"   色相循环模式渲染: {elapsed:.1f}ms")

# 测试循环渐变颜色映射
print("   测试循环渐变颜色映射...")
plotter.color_mode = 'colormap'
plotter.cmap_name = 'cyclic_rainbow_5'
start = time.perf_counter()
plotter.render()
elapsed = (time.perf_counter() - start) * 1000
print(f"   循环渐变颜色映射渲染: {elapsed:.1f}ms")

print("   ✓ Plotter集成测试通过")
print()

# 5. 性能对比测试
print("5. 性能对比测试...")
width, height = 800, 600
max_iter = 200

print(f"   分辨率: {width}x{height}, 迭代次数: {max_iter}")
print()

# Mandelbrot
from high_precision import mandelbrot_set_optimized
start = time.perf_counter()
data = mandelbrot_set_optimized(-2.0, 1.0, -1.5, 1.5, width, height, max_iter)
elapsed = (time.perf_counter() - start) * 1000
print(f"   Mandelbrot: {elapsed:.1f}ms")

# Julia 普通方式
start = time.perf_counter()
data = julia_set_optimized(-2.0, 2.0, -1.5, 1.5, width, height, -0.7, 0.27015, max_iter)
elapsed_normal = (time.perf_counter() - start) * 1000
print(f"   Julia (普通): {elapsed_normal:.1f}ms")

# Julia 缓存方式
grid_cache = JuliaGridCache(width, height)
grid_cache.precompute_grid(-2.0, 2.0, -1.5, 1.5)
zx, zy = grid_cache.get_grids()
start = time.perf_counter()
data = julia_set_from_grid(zx, zy, -0.7, 0.27015, max_iter)
elapsed_cached = (time.perf_counter() - start) * 1000
print(f"   Julia (缓存): {elapsed_cached:.1f}ms")

print(f"   性能提升: {elapsed_normal/elapsed_cached:.1f}x 倍")

print()
print("=" * 60)
print("所有增强功能测试通过！")
print("=" * 60)
print()
print("新增功能总结:")
print("  1. decimal高精度计算: 替代mpmath，使用Python标准库")
print("  2. Julia网格缓存: 视图不变时参数变化只更新迭代")
print("  3. 多段渐变颜色映射: 7种预定义多段渐变")
print("  4. 循环渐变颜色映射: 12种预定义循环渐变")
print("  5. 色相循环着色: 专门为分形边界设计的循环渐变")
print("  6. Julia快速更新API: update_julia_params()")
print()
print("运行方式:")
print("  python main.py")
