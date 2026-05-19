#!/usr/bin/env python3
"""
生成测试用的网格文件
"""

import numpy as np
import meshio
from pathlib import Path


def generate_2d_structured_grid(nx=20, ny=15, output="test_2d_grid.vtk"):
    """生成带畸变的二维结构化网格"""
    print(f"生成二维结构化网格: {nx} x {ny}")

    points = []
    for j in range(ny):
        for i in range(nx):
            x = i / (nx - 1)
            y = j / (ny - 1)

            x += 0.05 * np.sin(3 * np.pi * x) * np.sin(2 * np.pi * y)
            y += 0.05 * np.sin(2 * np.pi * x) * np.sin(3 * np.pi * y)

            points.append([x, y, 0.0])

    points = np.array(points)

    cells = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            idx0 = j * nx + i
            idx1 = j * nx + i + 1
            idx2 = (j + 1) * nx + i + 1
            idx3 = (j + 1) * nx + i
            cells.append([idx0, idx1, idx2, idx3])

    cells = np.array(cells)

    mesh = meshio.Mesh(points, [meshio.CellBlock('quad', cells)])
    mesh.write(output)
    print(f"  已保存到: {output}")
    print(f"  节点数: {len(points)}, 单元数: {len(cells)}")
    return output


def generate_3d_structured_grid(nx=8, ny=6, nz=5, output="test_3d_grid.vtk"):
    """生成三维结构化网格"""
    print(f"\n生成三维结构化网格: {nx} x {ny} x {nz}")

    points = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                x = i / (nx - 1)
                y = j / (ny - 1)
                z = k / (nz - 1)

                x += 0.03 * np.sin(2 * np.pi * y) * np.sin(2 * np.pi * z)
                y += 0.03 * np.sin(2 * np.pi * x) * np.sin(2 * np.pi * z)
                z += 0.03 * np.sin(2 * np.pi * x) * np.sin(2 * np.pi * y)

                points.append([x, y, z])

    points = np.array(points)

    cells = []
    for k in range(nz - 1):
        for j in range(ny - 1):
            for i in range(nx - 1):
                idx0 = k * nx * ny + j * nx + i
                idx1 = k * nx * ny + j * nx + i + 1
                idx2 = k * nx * ny + (j + 1) * nx + i + 1
                idx3 = k * nx * ny + (j + 1) * nx + i
                idx4 = (k + 1) * nx * ny + j * nx + i
                idx5 = (k + 1) * nx * ny + j * nx + i + 1
                idx6 = (k + 1) * nx * ny + (j + 1) * nx + i + 1
                idx7 = (k + 1) * nx * ny + (j + 1) * nx + i
                cells.append([idx0, idx1, idx2, idx3, idx4, idx5, idx6, idx7])

    cells = np.array(cells)

    mesh = meshio.Mesh(points, [meshio.CellBlock('hexahedron', cells)])
    mesh.write(output)
    print(f"  已保存到: {output}")
    print(f"  节点数: {len(points)}, 单元数: {len(cells)}")
    return output


def generate_annulus_grid(n_radial=6, n_angular=16, output="test_annulus.vtk"):
    """生成环形二维网格"""
    print(f"\n生成环形网格: {n_radial} x {n_angular}")

    r_inner = 1.0
    r_outer = 3.0

    points = []
    for j in range(n_radial):
        r = r_inner + (r_outer - r_inner) * j / (n_radial - 1)
        for i in range(n_angular):
            theta = 2 * np.pi * i / n_angular
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            points.append([x, y, 0.0])

    points = np.array(points)

    cells = []
    for j in range(n_radial - 1):
        for i in range(n_angular):
            i_next = (i + 1) % n_angular
            idx0 = j * n_angular + i
            idx1 = j * n_angular + i_next
            idx2 = (j + 1) * n_angular + i_next
            idx3 = (j + 1) * n_angular + i
            cells.append([idx0, idx1, idx2, idx3])

    cells = np.array(cells)

    mesh = meshio.Mesh(points, [meshio.CellBlock('quad', cells)])
    mesh.write(output)
    print(f"  已保存到: {output}")
    print(f"  节点数: {len(points)}, 单元数: {len(cells)}")
    return output


def main():
    print("=" * 60)
    print("  生成测试网格文件")
    print("=" * 60)

    output_dir = Path("test_meshes")
    output_dir.mkdir(exist_ok=True)

    files = []

    files.append(generate_2d_structured_grid(20, 15, str(output_dir / "grid_2d.vtk")))
    files.append(generate_3d_structured_grid(6, 5, 4, str(output_dir / "grid_3d.vtk")))
    files.append(generate_annulus_grid(8, 24, str(output_dir / "grid_annulus.vtk")))

    print("\n" + "=" * 60)
    print("  所有网格生成完成!")
    print("=" * 60)
    print(f"\n生成的文件位于: {output_dir.absolute()}")
    print("\n可以运行以下命令启动GUI并加载测试文件:")
    print("  python run_gui.py")
    print()


if __name__ == "__main__":
    main()
