#!/usr/bin/env python3
"""
启动交互式CFD网格前处理工具

使用方法:
    python run_gui.py
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("  CFD 网格前处理工具 - 交互式GUI版")
print("  基于 PyVista + Numba + PyQt5 构建")
print("=" * 60)
print()
print("功能特性:")
print("  ✓ 3D 交互式网格可视化")
print("  ✓ Numba JIT 加速质量计算")
print("  ✓ 拖拽式文件加载")
print("  ✓ Laplacian 平滑参数实时调节")
print("  ✓ 实时质量直方图统计")
print("  ✓ 按质量指标着色")
print()
print("支持格式: .vtk, .vtu, .stl, .msh, .obj, .ply")
print()

try:
    from cfdmesh import launch_gui
    launch_gui()
except ImportError as e:
    print(f"错误: 缺少依赖库 - {e}")
    print()
    print("请运行以下命令安装依赖:")
    print("  pip install numpy meshio matplotlib pyvista pyvistaqt numba PyQt5")
    sys.exit(1)
