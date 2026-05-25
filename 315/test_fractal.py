import time
import os
import sys
import numpy as np

print("=== 分形生成器完整测试 ===")
print()

# 1. 测试核心算法模块
print("1. 测试核心算法模块...")
from fractal_core import mandelbrot_set, julia_set, burning_ship_set

start = time.perf_counter()
data = mandelbrot_set(-2.0, 1.0, -1.5, 1.5, 400, 300, 100)
elapsed = (time.perf_counter() - start) * 1000
print(f"   Mandelbrot集: {elapsed:.1f}ms, 形状: {data.shape}")

start = time.perf_counter()
data = julia_set(-2.0, 2.0, -1.5, 1.5, 400, 300, -0.7, 0.27015, 100)
elapsed = (time.perf_counter() - start) * 1000
print(f"   Julia集: {elapsed:.1f}ms, 形状: {data.shape}")

start = time.perf_counter()
data = burning_ship_set(-2.0, 1.0, -2.0, 1.0, 400, 300, 100)
elapsed = (time.perf_counter() - start) * 1000
print(f"   Burning Ship: {elapsed:.1f}ms, 形状: {data.shape}")
print("   ✓ 核心算法模块测试通过")
print()

# 2. 测试几何分形模块
print("2. 测试几何分形模块...")
from geometric_fractals import (
    koch_snowflake, koch_curve, sierpinski_carpet,
    sierpinski_triangle, dragon_curve, hilbert_curve
)

start = time.perf_counter()
x, y = koch_snowflake(5, scale=10.0)
elapsed = (time.perf_counter() - start) * 1000
print(f"   科赫雪花: {elapsed:.1f}ms, 点数: {len(x)}")

start = time.perf_counter()
carpet = sierpinski_carpet(4, 243)
elapsed = (time.perf_counter() - start) * 1000
print(f"   谢尔宾斯基地毯: {elapsed:.1f}ms, 形状: {carpet.shape}")

start = time.perf_counter()
x, y = dragon_curve(12, scale=10.0)
elapsed = (time.perf_counter() - start) * 1000
print(f"   龙形曲线: {elapsed:.1f}ms, 点数: {len(x)}")

start = time.perf_counter()
x, y = hilbert_curve(5, scale=10.0)
elapsed = (time.perf_counter() - start) * 1000
print(f"   希尔伯特曲线: {elapsed:.1f}ms, 点数: {len(x)}")
print("   ✓ 几何分形模块测试通过")
print()

# 3. 测试高精度模块
print("3. 测试高精度模块...")
from high_precision import (
    compute_view_range, adaptive_max_iter,
    HighPrecisionCalculator, get_mandelbrot_interesting_points,
    get_julia_classic_sets
)

xmin, xmax, ymin, ymax = compute_view_range(-0.5, 0.0, 100.0, 800, 600)
print(f"   视图范围计算: X=[{xmin:.6f}, {xmax:.6f}], Y=[{ymin:.6f}, {ymax:.6f}]")

print(f"   自适应迭代: 1x={adaptive_max_iter(1, 100)}, 1000x={adaptive_max_iter(1000, 100)}")

hp_calc = HighPrecisionCalculator()
print(f"   mpmath可用: {hp_calc._mpmath_available}")

mandel_points = get_mandelbrot_interesting_points()
julia_sets = get_julia_classic_sets()
print(f"   预设位置: Mandelbrot={len(mandel_points)}个, Julia={len(julia_sets)}个")
print("   ✓ 高精度模块测试通过")
print()

# 4. 测试颜色映射模块
print("4. 测试颜色映射模块...")
from color_maps import (
    apply_fractal_colors, get_available_colormaps,
    create_hsv_colormap, create_psychedelic_colormap
)

cmaps = get_available_colormaps()
print(f"   可用颜色映射: {len(cmaps)}个")

data = np.random.rand(100, 100) * 100
start = time.perf_counter()
colored = apply_fractal_colors(data, 'inferno', gamma=1.0, invert=False, log_scale=False)
elapsed = (time.perf_counter() - start) * 1000
print(f"   颜色映射应用: {elapsed:.1f}ms, 输出形状: {colored.shape}")

start = time.perf_counter()
hsv_colored = create_hsv_colormap(data, 100)
elapsed = (time.perf_counter() - start) * 1000
print(f"   HSV着色: {elapsed:.1f}ms")

start = time.perf_counter()
psy_colored = create_psychedelic_colormap(data, 100)
elapsed = (time.perf_counter() - start) * 1000
print(f"   迷幻风格: {elapsed:.1f}ms")
print("   ✓ 颜色映射模块测试通过")
print()

# 5. 测试绘图模块
print("5. 测试绘图模块...")
from fractal_plotter import FractalPlotter

plotter = FractalPlotter(parent=None, width=600, height=450)
print(f"   Plotter创建成功: 分形类型={plotter.fractal_type}")

test_fractals = ['mandelbrot', 'julia', 'burning_ship', 'koch_snowflake', 'sierpinski_carpet']
for fractal_type in test_fractals:
    plotter.set_fractal_type(fractal_type)
    start = time.perf_counter()
    plotter.render()
    elapsed = (time.perf_counter() - start) * 1000
    status = plotter.get_status_info()
    print(f"   {fractal_type}: {elapsed:.1f}ms, 迭代={status['max_iter']}")

status = plotter.get_status_info()
print(f"   状态信息: 缩放={status['zoom']:.2e}x, 中心=({status['center_x']:.6f}, {status['center_y']:.6f})")
print("   ✓ 绘图模块测试通过")
print()

# 6. 显示项目结构
print("6. 项目文件结构:")
total_size = 0
for root, dirs, files in os.walk('.'):
    for file in sorted(files):
        if file.endswith('.py') or file.endswith('.txt') or file.endswith('.md'):
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            total_size += size
            print(f"   {file:<25} ({size:>6} bytes)")
print(f"   {'-'*40}")
print(f"   {'总计':<25} ({total_size:>6} bytes)")
print()

print("=" * 50)
print("所有测试通过！分形生成器已准备就绪。")
print("=" * 50)
print()
print("运行方式:")
print("  python main.py")
print()
print("依赖库:")
print("  numpy, numba, matplotlib, mpmath")
print()
print("操作说明:")
print("  - 左键拖拽: 框选区域缩放")
print("  - 滚轮: 以鼠标位置为中心缩放")
print("  - 右键拖拽: 平移视图")
print("  - R键: 重置视图")
print("  - 空格键: 重新渲染")
print("  - S键: 保存图像")
