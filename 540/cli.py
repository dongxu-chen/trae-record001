#!/usr/bin/env python3
import argparse
import os
import sys
from raster_to_vector import RasterToVector
from batch_processor import BatchProcessor
from format_exporter import FormatExporter


def cmd_single(args):
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        return 1

    print(f"正在处理: {args.input}")

    try:
        converter = RasterToVector(args.input)

        output_path = converter.convert(
            output_svg_path=args.output,
            denoise_method=args.denoise if args.denoise != 'none' else 'bilateral',
            n_colors=args.colors,
            edge_method=args.edge_method,
            low_threshold=args.low_threshold,
            high_threshold=args.high_threshold,
            min_contour_area=args.min_area,
            use_curve_fitting=not args.no_curve,
            stroke_width=args.stroke_width,
            denoise_min_area=args.denoise_min_area,
            edge_aware_quant=not args.no_edge_aware,
            smooth_sigma=args.smooth_sigma,
            curve_max_iter=args.curve_iter,
            curve_error_threshold=args.curve_error
        )

        print(f"成功! SVG输出: {output_path}")
        print(f"提取轮廓数: {len(converter.contours)}")

        if args.format and args.format.lower() != 'svg':
            export_path = args.output.rsplit('.', 1)[0] + f'.{args.format}'
            exporter = FormatExporter(output_path)
            exporter.export(export_path, format=args.format)
            print(f"格式转换: {export_path}")

        if args.preview:
            import cv2
            preview = converter.get_preview()
            if preview is not None:
                cv2.imshow('Preview', preview)
                print("按任意键关闭预览窗口...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()

        return 0

    except Exception as e:
        print(f"处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_batch(args):
    if not os.path.isdir(args.input_dir):
        print(f"错误: 输入目录不存在: {args.input_dir}")
        return 1

    convert_kwargs = {
        'denoise_method': args.denoise if args.denoise != 'none' else 'bilateral',
        'n_colors': args.colors,
        'edge_aware_quant': not args.no_edge_aware,
        'smooth_sigma': args.smooth_sigma,
        'use_curve_fitting': not args.no_curve,
        'curve_max_iter': args.curve_iter,
        'curve_error_threshold': args.curve_error,
    }

    processor = BatchProcessor(args.input_dir, args.output_dir, max_workers=args.workers)
    results = processor.run(convert_kwargs=convert_kwargs)

    summary = processor.get_summary()
    print(f"\n批量处理完成:")
    print(f"  总计: {summary['total']}, 成功: {summary['success']}, 失败: {summary['failed']}")
    print(f"  总轮廓数: {summary['total_contours']}")

    if args.format and args.format.lower() != 'svg':
        print(f"\n正在批量转换为 {args.format.upper()} 格式...")
        for result in results:
            if result['success']:
                try:
                    exporter = FormatExporter(result['output'])
                    export_path = result['output'].rsplit('.', 1)[0] + f'.{args.format}'
                    exporter.export(export_path, format=args.format)
                    print(f"  ✓ {os.path.basename(export_path)}")
                except Exception as e:
                    print(f"  ✗ {os.path.basename(result['output'])}: {e}")

    return 0 if summary['failed'] == 0 else 1


def cmd_edit(args):
    if not os.path.exists(args.input):
        print(f"错误: 输入SVG文件不存在: {args.input}")
        return 1

    from vector_editor import VectorEditor

    editor = VectorEditor(args.input)
    info = editor.get_edit_info()
    print(f"已加载: {args.input}")
    print(f"  画布: {info['canvas_size'][0]:.0f}x{info['canvas_size'][1]:.0f}")
    print(f"  路径数: {info['total_paths']}, 锚点数: {info['total_anchors']}")

    if args.list_paths:
        for i, path in enumerate(editor.paths):
            vis = "可见" if path['visible'] else "隐藏"
            print(f"  路径 {i}: {len(path['points'])} 个锚点, 填充={path['fill']}, {vis}")

    if args.smooth is not None:
        for idx in (args.smooth if args.smooth else range(len(editor.paths))):
            editor.smooth_path(idx, iterations=3, factor=0.5)
            print(f"  平滑路径 {idx}")

    if args.simplify is not None:
        for idx in (args.simplify if args.simplify else range(len(editor.paths))):
            editor.simplify_path(idx, tolerance=2.0)
            print(f"  简化路径 {idx}")

    if args.delete_path is not None:
        for idx in sorted(args.delete_path, reverse=True):
            editor.delete_path(idx)
            print(f"  删除路径 {idx}")

    if args.move_anchor:
        parts = args.move_anchor.split(',')
        if len(parts) == 4:
            pi, ai = int(parts[0]), int(parts[1])
            nx, ny = float(parts[2]), float(parts[3])
            editor.move_anchor(pi, ai, nx, ny)
            print(f"  移动锚点: 路径{pi} 锚点{ai} -> ({nx}, {ny})")

    if args.add_anchor:
        parts = args.add_anchor.split(',')
        if len(parts) == 4:
            pi, after_i = int(parts[0]), int(parts[1])
            nx, ny = float(parts[2]), float(parts[3])
            editor.add_anchor(pi, after_i, nx, ny)
            print(f"  添加锚点: 路径{pi} 位置{after_i}后 -> ({nx}, {ny})")

    if args.remove_anchor:
        parts = args.remove_anchor.split(',')
        if len(parts) == 2:
            pi, ai = int(parts[0]), int(parts[1])
            editor.remove_anchor(pi, ai)
            print(f"  删除锚点: 路径{pi} 锚点{ai}")

    if args.transform:
        parts = args.transform.split(',')
        if len(parts) >= 3:
            pi = int(parts[0])
            tx, ty = float(parts[1]), float(parts[2])
            scale = (float(parts[3]), float(parts[4])) if len(parts) >= 5 else (1.0, 1.0)
            rotate = float(parts[5]) if len(parts) >= 6 else 0.0
            editor.transform_path(pi, translate=(tx, ty), scale=scale, rotate=rotate)
            print(f"  变换路径 {pi}")

    if args.color:
        parts = args.color.split(',')
        if len(parts) >= 5:
            pi = int(parts[0])
            r, g, b = int(parts[1]), int(parts[2]), int(parts[3])
            sr, sg, sb = int(parts[4]), int(parts[5]), int(parts[6]) if len(parts) >= 7 else r, g, b
            editor.set_path_color(pi, fill=(r, g, b), stroke=(sr, sg, sb))
            print(f"  修改路径 {pi} 颜色")

    output = args.output or args.input
    editor.save_svg(output)

    if args.format and args.format.lower() != 'svg':
        export_path = output.rsplit('.', 1)[0] + f'.{args.format}'
        exporter = FormatExporter(output)
        exporter.export(export_path, format=args.format)
        print(f"  格式转换: {export_path}")

    print(f"已保存: {output}")
    return 0


def cmd_export(args):
    if not os.path.exists(args.input):
        print(f"错误: 输入SVG文件不存在: {args.input}")
        return 1

    try:
        exporter = FormatExporter(args.input)
        output = args.output or args.input.rsplit('.', 1)[0] + f'.{args.format}'
        exporter.export(output, format=args.format)
        print(f"导出成功: {output}")
        return 0
    except Exception as e:
        print(f"导出失败: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='光栅图像矢量化工具 - 将位图转换为矢量图形',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # ── single ──
    p_single = subparsers.add_parser('single', help='单图矢量化')
    _add_common_args(p_single)
    p_single.add_argument('input', help='输入图像路径')
    p_single.add_argument('output', help='输出SVG路径')
    p_single.add_argument('--format', '-f', choices=['svg', 'pdf', 'eps', 'ai'],
                          help='导出格式 (默认SVG)')
    p_single.add_argument('--preview', action='store_true', help='显示预览')

    # ── batch ──
    p_batch = subparsers.add_parser('batch', help='批量矢量化')
    _add_common_args(p_batch)
    p_batch.add_argument('input_dir', help='输入图像目录')
    p_batch.add_argument('output_dir', help='输出SVG目录')
    p_batch.add_argument('--workers', '-w', type=int, default=None,
                         help='并行工作进程数 (默认CPU核心数)')
    p_batch.add_argument('--format', '-f', choices=['svg', 'pdf', 'eps', 'ai'],
                         help='导出格式 (默认SVG)')

    # ── edit ──
    p_edit = subparsers.add_parser('edit', help='编辑矢量图')
    p_edit.add_argument('input', help='输入SVG路径')
    p_edit.add_argument('--output', '-o', help='输出SVG路径 (默认覆盖原文件)')
    p_edit.add_argument('--list-paths', action='store_true', help='列出所有路径')
    p_edit.add_argument('--smooth', nargs='*', type=int, help='平滑指定路径 (空=全部)')
    p_edit.add_argument('--simplify', nargs='*', type=int, help='简化指定路径 (空=全部)')
    p_edit.add_argument('--delete-path', nargs='*', type=int, help='删除指定路径')
    p_edit.add_argument('--move-anchor', type=str, help='移动锚点: path_idx,anchor_idx,x,y')
    p_edit.add_argument('--add-anchor', type=str, help='添加锚点: path_idx,after_idx,x,y')
    p_edit.add_argument('--remove-anchor', type=str, help='删除锚点: path_idx,anchor_idx')
    p_edit.add_argument('--transform', type=str,
                        help='变换路径: path_idx,tx,ty[,sx,sy[,rotate]]')
    p_edit.add_argument('--color', type=str,
                        help='修改颜色: path_idx,r,g,b[,sr,sg,sb]')
    p_edit.add_argument('--format', '-f', choices=['svg', 'pdf', 'eps', 'ai'],
                        help='导出格式')

    # ── export ──
    p_export = subparsers.add_parser('export', help='格式转换导出')
    p_export.add_argument('input', help='输入SVG路径')
    p_export.add_argument('--output', '-o', help='输出文件路径')
    p_export.add_argument('--format', '-f', choices=['svg', 'pdf', 'eps', 'ai'],
                          required=True, help='目标格式')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    dispatch = {
        'single': cmd_single,
        'batch': cmd_batch,
        'edit': cmd_edit,
        'export': cmd_export,
    }
    return dispatch[args.command](args)


def _add_common_args(parser):
    parser.add_argument('--denoise', '-d',
                        choices=['bilateral', 'gaussian', 'median', 'nl_means', 'area_filter', 'none'],
                        default='bilateral', help='去噪方法')
    parser.add_argument('--denoise-min-area', type=int, default=20,
                        help='去噪最小面积阈值 (默认: 20)')
    parser.add_argument('--colors', '-c', type=int, default=8,
                        help='颜色量化数量 (默认: 8)')
    parser.add_argument('--no-edge-aware', action='store_true',
                        help='禁用边缘感知颜色量化')
    parser.add_argument('--smooth-sigma', type=float, default=1.5,
                        help='边界平滑sigma值 (默认: 1.5)')
    parser.add_argument('--edge-method', '-e',
                        choices=['canny', 'sobel', 'laplacian'],
                        default='canny', help='边缘检测方法')
    parser.add_argument('--low-threshold', type=int, default=50,
                        help='Canny低阈值 (默认: 50)')
    parser.add_argument('--high-threshold', type=int, default=150,
                        help='Canny高阈值 (默认: 150)')
    parser.add_argument('--min-area', type=int, default=10,
                        help='最小轮廓面积 (默认: 10)')
    parser.add_argument('--no-curve', action='store_true',
                        help='禁用曲线拟合')
    parser.add_argument('--curve-iter', type=int, default=5,
                        help='曲线拟合迭代次数 (默认: 5)')
    parser.add_argument('--curve-error', type=float, default=1.0,
                        help='曲线拟合误差阈值 (默认: 1.0)')
    parser.add_argument('--stroke-width', type=float, default=1,
                        help='线条宽度 (默认: 1)')


if __name__ == '__main__':
    exit(main())
