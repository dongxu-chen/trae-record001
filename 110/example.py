#!/usr/bin/env python3
"""
CFD 网格前处理工具使用示例 - 完整版
"""

import numpy as np
import meshio
from pathlib import Path

from cfdmesh import (
    MeshReader, MeshQuality, MeshConverter,
    QualityReport, MeshOptimizer, MeshVisualizer
)


def create_sample_2d_mesh(output_path: str = "sample_2d.vtk"):
    """创建带有一些低质量单元的二维示例网格"""
    print(f"\n创建二维示例网格: {output_path}")

    nx, ny = 10, 8
    points = []
    for j in range(ny):
        for i in range(nx):
            x = i * 1.0
            y = j * 1.0
            if 3 < i < 7 and 2 < j < 5:
                x += 0.3 * np.sin(i * 0.5)
                y += 0.3 * np.cos(j * 0.5)
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
    mesh.write(output_path)
    print(f"  创建完成: {len(points)} 个节点, {len(cells)} 个单元")
    return output_path


def create_sample_curved_mesh(output_path: str = "sample_curved.vtk"):
    """创建带有曲率变化的二维网格"""
    print(f"\n创建带曲率示例网格: {output_path}")

    n_angular = 16
    n_radial = 5
    r_inner, r_outer = 1.0, 3.0

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
    mesh.write(output_path)
    print(f"  创建完成: {len(points)} 个节点, {len(cells)} 个单元")
    return output_path


def example_1_laplacian_smoothing():
    print("\n" + "=" * 70)
    print("示例 1: Laplacian 网格平滑")
    print("=" * 70)

    mesh_path = create_sample_2d_mesh()

    reader = MeshReader()
    reader.read(mesh_path)
    mesh = reader.mesh

    quality_before = MeshQuality(mesh.points, mesh.cells)
    metrics_before = quality_before.compute_all_metrics()
    stats_before = quality_before.get_statistics()

    print(f"\n平滑前质量统计:")
    for cell_type, stats in stats_before.items():
        print(f"  {cell_type}:")
        print(f"    平均非正交度: {stats['non_orthogonality']['mean']:.4f}")
        print(f"    平均歪斜度: {stats['skewness']['mean']:.4f}")

    optimizer = MeshOptimizer(mesh)

    print(f"\n执行 Laplacian 平滑 (20次迭代)...")
    optimized_mesh = optimizer.laplacian_smooth(
        iterations=20,
        relaxation=0.5,
        fixed_boundary=True
    )

    quality_after = MeshQuality(optimized_mesh.points, optimized_mesh.cells)
    metrics_after = quality_after.compute_all_metrics()
    stats_after = quality_after.get_statistics()

    print(f"\n平滑后质量统计:")
    for cell_type, stats in stats_after.items():
        print(f"  {cell_type}:")
        print(f"    平均非正交度: {stats['non_orthogonality']['mean']:.4f}")
        print(f"    平均歪斜度: {stats['skewness']['mean']:.4f}")

        improvement = (stats_before[cell_type]['non_orthogonality']['mean'] -
                      stats['non_orthogonality']['mean']) / stats_before[cell_type]['non_orthogonality']['mean'] * 100
        print(f"    非正交度改进: {improvement:+.2f}%")

    return mesh, optimized_mesh, quality_before, quality_after


def example_2_curvature_based_refinement():
    print("\n" + "=" * 70)
    print("示例 2: 基于曲率的自适应网格加密")
    print("=" * 70)

    mesh_path = create_sample_curved_mesh()

    reader = MeshReader()
    reader.read(mesh_path)
    mesh = reader.mesh

    optimizer = MeshOptimizer(mesh)

    curvature = optimizer.compute_curvature()
    print(f"\n曲率统计:")
    print(f"  最小曲率: {curvature.min():.4f}")
    print(f"  最大曲率: {curvature.max():.4f}")
    print(f"  平均曲率: {curvature.mean():.4f}")

    threshold = np.percentile(curvature, 70)
    print(f"\n执行曲率自适应加密 (阈值: {threshold:.4f})...")

    refined_mesh = optimizer.adaptive_refine(
        method='curvature',
        threshold=threshold,
        max_level=1
    )

    print(f"\n加密前后对比:")
    print(f"  原始节点数: {len(mesh.points)}")
    print(f"  加密后节点数: {len(refined_mesh.points)}")
    print(f"  原始单元数: {sum(len(cb.data) for cb in mesh.cells)}")
    print(f"  加密后单元数: {sum(len(cb.data) for cb in refined_mesh.cells)}")

    return mesh, refined_mesh


def example_3_quality_based_refinement():
    print("\n" + "=" * 70)
    print("示例 3: 基于质量指标的自适应网格加密")
    print("=" * 70)

    mesh_path = "sample_2d.vtk"

    reader = MeshReader()
    reader.read(mesh_path)
    mesh = reader.mesh

    optimizer = MeshOptimizer(mesh)

    quality = MeshQuality(mesh.points, mesh.cells)
    metrics = quality.compute_all_metrics()

    print(f"\n质量统计 (加密前):")
    for cell_type, cell_metrics in metrics.items():
        if 'non_orthogonality' in cell_metrics:
            values = cell_metrics['non_orthogonality']
            print(f"  {cell_type} 非正交度:")
            print(f"    范围: [{values.min():.2f}, {values.max():.2f}]")
            print(f"    均值: {values.mean():.2f}")

    threshold = np.percentile(metrics['quad']['non_orthogonality'], 70)
    print(f"\n执行质量自适应加密 (非正交度阈值: {threshold:.2f})...")

    refined_mesh = optimizer.adaptive_refine(
        method='quality',
        threshold=threshold,
        max_level=1,
        quality_metric='non_orthogonality'
    )

    print(f"\n加密前后对比:")
    print(f"  原始节点数: {len(mesh.points)}")
    print(f"  加密后节点数: {len(refined_mesh.points)}")
    print(f"  原始单元数: {sum(len(cb.data) for cb in mesh.cells)}")
    print(f"  加密后单元数: {sum(len(cb.data) for cb in refined_mesh.cells)}")

    return mesh, refined_mesh


def example_4_full_optimization_pipeline():
    print("\n" + "=" * 70)
    print("示例 4: 完整优化流程 (平滑 + 加密 + 可视化)")
    print("=" * 70)

    mesh_path = create_sample_2d_mesh("optimization_test.vtk")

    reader = MeshReader()
    reader.read(mesh_path)
    mesh = reader.mesh

    optimizer = MeshOptimizer(mesh)

    print(f"\n执行完整网格优化...")
    print(f"  1. Laplacian 平滑 (15次迭代)")
    print(f"  2. 基于质量的自适应加密 (1层级)")
    print(f"  3. 平滑过渡处理")

    result = optimizer.optimize_mesh(
        smooth_iterations=15,
        refinement_method='quality',
        refinement_threshold=None,
        max_refinement_level=1
    )

    print(f"\n优化结果:")
    print(f"  节点数: {result['before']['num_points']} -> {result['after']['num_points']}")
    print(f"  单元数: {result['before']['num_cells']} -> {result['after']['num_cells']}")

    visualizer = MeshVisualizer(
        mesh.points, mesh.cells,
        result['mesh'].points, result['mesh'].cells
    )

    summary_text = visualizer.generate_text_summary(result['before'], result['after'])
    print("\n" + summary_text)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    report_path = output_dir / "optimization_report.txt"
    report_path.write_text(summary_text, encoding='utf-8')
    print(f"\n优化报告已保存到: {report_path}")

    try:
        img_path = output_dir / "optimization_comparison.png"
        visualizer.generate_comparison_report(
            str(img_path), result['before'], result['after']
        )
        print(f"可视化对比图已保存到: {img_path}")

        heatmap_path = output_dir / "quality_heatmap.png"
        visualizer.generate_quality_heatmap(str(heatmap_path))
        print(f"质量热力图已保存到: {heatmap_path}")
    except Exception as e:
        print(f"可视化生成跳过: {e}")

    optimized_mesh_path = output_dir / "optimized_mesh.vtk"
    meshio.write(optimized_mesh_path, result['mesh'])
    print(f"优化后网格已保存到: {optimized_mesh_path}")

    return result


def example_5_smooth_transition():
    print("\n" + "=" * 70)
    print("示例 5: 加密区域平滑过渡")
    print("=" * 70)

    mesh_path = create_sample_curved_mesh("transition_test.vtk")

    reader = MeshReader()
    reader.read(mesh_path)
    mesh = reader.mesh

    optimizer = MeshOptimizer(mesh)

    print(f"\n步骤 1: 执行自适应加密...")
    curvature = optimizer.compute_curvature()
    threshold = np.percentile(curvature, 60)
    refined_mesh = optimizer.adaptive_refine(
        method='curvature',
        threshold=threshold,
        max_level=1
    )

    print(f"\n步骤 2: 执行平滑过渡处理...")
    optimizer2 = MeshOptimizer(refined_mesh)
    smoothed_mesh = optimizer2.smooth_transition(iterations=5)

    print(f"\n处理完成:")
    print(f"  初始节点数: {len(mesh.points)}")
    print(f"  加密后节点数: {len(refined_mesh.points)}")
    print(f"  平滑后节点数: {len(smoothed_mesh.points)}")

    return mesh, refined_mesh, smoothed_mesh


def main():
    print("\n" + "#" * 70)
    print("#         CFD 网格前处理工具 - 网格优化功能示例")
    print("#" * 70)

    print("\n" + "=" * 70)
    print("功能说明:")
    print("  ✓ Laplacian 网格平滑 - 可调迭代次数和松弛因子")
    print("  ✓ 基于曲率的自适应加密 - 高曲率区域自动细化")
    print("  ✓ 基于质量的自适应加密 - 低质量单元区域自动细化")
    print("  ✓ 平滑过渡处理 - 加密后边界平滑处理")
    print("  ✓ 可视化对比 - 优化前后网格和质量对比图")
    print("=" * 70)

    example_1_laplacian_smoothing()
    example_2_curvature_based_refinement()
    example_3_quality_based_refinement()
    example_4_full_optimization_pipeline()
    example_5_smooth_transition()

    print("\n" + "#" * 70)
    print("#         所有示例执行完成!")
    print("#" * 70 + "\n")


if __name__ == "__main__":
    main()
