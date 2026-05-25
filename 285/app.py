import os
import sys
import argparse
from edge_detection import EdgeDetection
from deep_edge import DeepEdgeDetector, EdgeGuidedFilter, RealtimeEdgeDetection
from main import EdgeDetectionBenchmark


def process_image(input_path, output_path, method='canny', preprocess='gaussian', 
                  deep_threshold=30, apply_filter=None):
    import cv2
    
    image = cv2.imread(input_path)
    if image is None:
        print(f"无法读取图片: {input_path}")
        return False

    if method in ['hed', 'rcf']:
        detector = DeepEdgeDetector()
        edges = detector.detect(image, method=method, threshold=deep_threshold)
    else:
        detector = EdgeDetection()
        edges = detector.detect_edges(
            image, method=method, preprocess=preprocess
        )

    if edges is None:
        print("边缘检测失败")
        return False

    if apply_filter:
        egf = EdgeGuidedFilter()
        if apply_filter == 'smooth':
            result = egf.edge_guided_smoothing(image, edges)
        elif apply_filter == 'enhance':
            result = egf.edge_enhancement(image, edges)
        elif apply_filter == 'bokeh':
            result = egf.edge_aware_blur(image, edges)
        else:
            result = edges
    else:
        result = edges

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    cv2.imwrite(output_path, result)
    print(f"结果已保存到: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description='边缘检测算法库 - 完整工具包')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    detect_parser = subparsers.add_parser('detect', help='单张图片边缘检测')
    detect_parser.add_argument('input', help='输入图片路径')
    detect_parser.add_argument('output', help='输出图片路径')
    detect_parser.add_argument('--method', '-m', default='canny', 
                              choices=['sobel', 'laplacian', 'canny', 'hed', 'rcf'],
                              help='检测方法')
    detect_parser.add_argument('--preprocess', '-p', default='gaussian',
                              choices=['none', 'gaussian', 'median'],
                              help='预处理方法')
    detect_parser.add_argument('--filter', '-f', choices=['smooth', 'enhance', 'bokeh'],
                              help='边缘导向滤波应用')

    batch_parser = subparsers.add_parser('batch', help='批量处理')
    batch_parser.add_argument('input_dir', help='输入目录')
    batch_parser.add_argument('output_dir', help='输出目录')
    batch_parser.add_argument('--methods', nargs='+', default=['canny'],
                             choices=['sobel', 'laplacian', 'canny', 'hed', 'rcf'])

    bsds_parser = subparsers.add_parser('bsds', help='BSDS500基准测试')
    bsds_parser.add_argument('--split', default='val', choices=['train', 'val', 'test'])
    bsds_parser.add_argument('--max-images', type=int, default=None)

    realtime_parser = subparsers.add_parser('realtime', help='实时摄像头检测')
    realtime_parser.add_argument('--method', '-m', default='canny',
                                choices=['sobel', 'laplacian', 'canny', 'hed', 'rcf'])
    realtime_parser.add_argument('--camera', '-c', type=int, default=0, help='摄像头ID')

    demo_parser = subparsers.add_parser('demo', help='运行演示')
    demo_parser.add_argument('--type', '-t', default='all',
                            choices=['filter', 'compare', 'realtime', 'all'])

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == 'detect':
        process_image(
            args.input, args.output,
            method=args.method,
            preprocess=None if args.preprocess == 'none' else args.preprocess,
            apply_filter=args.filter
        )

    elif args.command == 'batch':
        benchmark = EdgeDetectionBenchmark()
        benchmark.batch_process(
            args.input_dir, args.output_dir,
            methods=[m for m in args.methods if m not in ['hed', 'rcf']],
            preprocess=[None, 'gaussian', 'median']
        )

    elif args.command == 'bsds':
        benchmark = EdgeDetectionBenchmark()
        benchmark.benchmark_bsds500(
            split=args.split,
            max_images=args.max_images
        )

    elif args.command == 'realtime':
        rt = RealtimeEdgeDetection(camera_id=args.camera)
        rt.start(method=args.method)

    elif args.command == 'demo':
        from demo_all import (
            demo_edge_guided_filtering,
            demo_traditional_vs_deep,
            run_realtime_demo
        )
        if args.type == 'filter':
            demo_edge_guided_filtering()
        elif args.type == 'compare':
            demo_traditional_vs_deep()
        elif args.type == 'realtime':
            run_realtime_demo()
        else:
            demo_edge_guided_filtering()
            demo_traditional_vs_deep()
            run_realtime_demo()


if __name__ == "__main__":
    main()
