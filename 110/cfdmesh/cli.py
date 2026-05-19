import argparse
import sys
from pathlib import Path
import meshio

from .mesh_reader import MeshReader
from .mesh_quality import MeshQuality
from .mesh_converter import MeshConverter
from .quality_report import QualityReport
from .mesh_optimizer import MeshOptimizer
from .mesh_visualization import MeshVisualizer


def cmd_check(args):
    print(f"\n正在检查网格文件: {args.input}")
    print("-" * 50)

    try:
        reader = MeshReader()
        reader.read(args.input)
        mesh_info = reader.get_mesh_info()

        print(f"\n网格信息:")
        print(f"  节点数: {mesh_info['num_points']}")
        print(f"  单元数: {mesh_info['total_cells']}")
        print(f"  单元类型:")
        for cell_type, count in mesh_info["cell_types"].items():
            print(f"    - {cell_type}: {count}")

        print(f"\n正在计算网格质量指标...")
        quality = MeshQuality(reader.get_points(), reader.get_cells())
        metrics = quality.compute_all_metrics()
        stats = quality.get_statistics()
        histograms = quality.get_all_histograms(bins=10)
        is_2d = quality.is_2d

        if not stats:
            print("警告: 没有计算出质量指标（可能不支持当前单元类型）")
            return

        report = QualityReport(mesh_info, metrics, stats, histograms, is_2d)
        report_text = report.generate_text_report()

        if args.output:
            report.save_report(args.output)
            print(f"\n报告已保存到: {args.output}")
        else:
            print("\n")
            print(report_text)

        if args.csv:
            report.export_csv(args.csv)
            print(f"\nCSV数据已导出到: {args.csv}")

    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_convert(args):
    print(f"\n正在转换网格文件...")
    print(f"  输入: {args.input}")
    print(f"  输出: {args.output}")
    print("-" * 50)

    try:
        converter = MeshConverter()
        output_path = converter.convert(args.input, args.output)
        print(f"\n转换成功! 输出文件: {output_path}")

        reader = MeshReader()
        reader.read(output_path)
        info = reader.get_mesh_info()
        print(f"  节点数: {info['num_points']}")
        print(f"  单元数: {info['total_cells']}")

    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    print(f"\n网格文件信息: {args.input}")
    print("-" * 50)

    try:
        reader = MeshReader()
        reader.read(args.input)
        info = reader.get_mesh_info()

        print(f"\n基本信息:")
        print(f"  文件路径: {info['file_path']}")
        print(f"  节点数量: {info['num_points']}")
        print(f"  单元总数: {info['total_cells']}")

        print(f"\n单元统计:")
        for cell_type, count in info["cell_types"].items():
            print(f"  {cell_type}: {count} 个")

        points = reader.get_points()
        print(f"\n边界框:")
        print(f"  X范围: [{points[:, 0].min():.6f}, {points[:, 0].max():.6f}]")
        if points.shape[1] > 1:
            print(f"  Y范围: [{points[:, 1].min():.6f}, {points[:, 1].max():.6f}]")
        if points.shape[1] > 2:
            print(f"  Z范围: [{points[:, 2].min():.6f}, {points[:, 2].max():.6f}]")

    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_optimize(args):
    print(f"\n正在优化网格文件: {args.input}")
    print("-" * 50)

    try:
        reader = MeshReader()
        reader.read(args.input)
        mesh = reader.mesh

        print(f"\n网格信息:")
        print(f"  节点数: {len(mesh.points)}")
        print(f"  单元数: {sum(len(cb.data) for cb in mesh.cells)}")

        optimizer = MeshOptimizer(mesh)

        if args.method == 'smooth':
            print(f"\n执行 Laplacian 平滑...")
            print(f"  迭代次数: {args.iterations}")
            print(f"  松弛因子: {args.relaxation}")
            optimized_mesh = optimizer.laplacian_smooth(
                iterations=args.iterations,
                relaxation=args.relaxation,
                fixed_boundary=not args.free_boundary
            )
            result = {
                'before': optimizer._compute_quality_summary(),
                'after': optimizer._compute_quality_summary(),
                'mesh': optimized_mesh
            }
        else:
            print(f"\n执行完整优化...")
            print(f"  平滑迭代: {args.iterations}")
            print(f"  加密方法: {args.refine_method}")
            print(f"  最大加密层级: {args.max_refine}")

            refinement_threshold = None
            if args.threshold is not None:
                refinement_threshold = float(args.threshold)
                print(f"  加密阈值: {refinement_threshold}")

            result = optimizer.optimize_mesh(
                smooth_iterations=args.iterations,
                refinement_method=args.refine_method,
                refinement_threshold=refinement_threshold,
                max_refinement_level=args.max_refine
            )

        print("\n优化完成!")
        print(f"  节点数变化: {result['before']['num_points']} -> {result['after']['num_points']}")
        print(f"  单元数变化: {result['before']['num_cells']} -> {result['after']['num_cells']}")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            meshio.write(output_path, result['mesh'])
            print(f"\n优化后网格已保存到: {output_path}")

        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            visualizer = MeshVisualizer(
                mesh.points, mesh.cells,
                result['mesh'].points, result['mesh'].cells
            )

            report_text = visualizer.generate_text_summary(result['before'], result['after'])
            report_path.write_text(report_text, encoding='utf-8')
            print(f"优化报告已保存到: {report_path}")

            try:
                img_path = report_path.with_suffix('.png')
                visualizer.generate_comparison_report(
                    str(img_path), result['before'], result['after']
                )
                print(f"可视化报告已保存到: {img_path}")
            except Exception as e:
                print(f"可视化生成跳过: {e}")

        if args.quality:
            quality = MeshQuality(result['mesh'].points, result['mesh'].cells)
            metrics = quality.compute_all_metrics()
            stats = quality.get_statistics()
            histograms = quality.get_all_histograms()

            report = QualityReport(reader.get_mesh_info(), metrics, stats,
                                 histograms, quality.is_2d)
            print("\n" + report.generate_text_report())

    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="CFD 网格前处理工具 - meshio + NumPy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例命令:
  cfdmesh info mesh.msh                    显示网格基本信息
  cfdmesh check mesh.vtk -o report.txt     检查网格质量并保存报告
  cfdmesh optimize mesh.vtk -o opt.vtk    优化网格质量
  cfdmesh optimize mesh.vtk --method smooth 仅执行平滑
  cfdmesh convert input.msh output.vtk     转换网格格式
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    info_parser = subparsers.add_parser("info", help="显示网格基本信息")
    info_parser.add_argument("input", help="输入网格文件路径")

    check_parser = subparsers.add_parser("check", help="检查网格质量")
    check_parser.add_argument("input", help="输入网格文件路径")
    check_parser.add_argument("-o", "--output", help="输出报告文件路径")
    check_parser.add_argument("--csv", help="导出CSV数据文件路径")

    optimize_parser = subparsers.add_parser("optimize", help="优化网格质量")
    optimize_parser.add_argument("input", help="输入网格文件路径")
    optimize_parser.add_argument("-o", "--output", help="输出优化后网格文件")
    optimize_parser.add_argument("--method", default="full",
                               choices=["full", "smooth"],
                               help="优化方法: full(完整优化), smooth(仅平滑)")
    optimize_parser.add_argument("-i", "--iterations", type=int, default=20,
                               help="Laplacian平滑迭代次数 (默认: 20)")
    optimize_parser.add_argument("-r", "--relaxation", type=float, default=0.5,
                               help="松弛因子 (默认: 0.5)")
    optimize_parser.add_argument("--free-boundary", action="store_true",
                               help="允许边界移动 (默认: 固定边界)")
    optimize_parser.add_argument("--refine-method", default="quality",
                               choices=["quality", "curvature"],
                               help="网格加密方法 (默认: quality)")
    optimize_parser.add_argument("--max-refine", type=int, default=0,
                               help="最大加密层级 (默认: 0, 不加密)")
    optimize_parser.add_argument("--threshold", type=float, default=None,
                               help="加密阈值")
    optimize_parser.add_argument("--report", help="输出优化报告文件路径")
    optimize_parser.add_argument("--quality", action="store_true",
                               help="显示优化后质量报告")

    convert_parser = subparsers.add_parser("convert", help="转换网格格式")
    convert_parser.add_argument("input", help="输入网格文件路径")
    convert_parser.add_argument("output", help="输出网格文件路径")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "info":
        cmd_info(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "optimize":
        cmd_optimize(args)
    elif args.command == "convert":
        cmd_convert(args)


if __name__ == "__main__":
    main()
