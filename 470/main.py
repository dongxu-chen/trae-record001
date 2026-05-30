import os
import sys
import argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from core import SaliencyInferencer, BatchProcessor

Config.ensure_dirs()


def main():
    parser = argparse.ArgumentParser(description='显著性目标检测系统')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    predict_parser = subparsers.add_parser('predict', help='单图显著性检测')
    predict_parser.add_argument('--input', '-i', required=True, help='输入图像路径')
    predict_parser.add_argument('--output', '-o', default=None, help='输出目录')
    predict_parser.add_argument('--model', '-m', default='basnet', choices=['basnet', 'poolnet'], help='模型选择')
    predict_parser.add_argument('--threshold', '-t', type=float, default=0.5, help='二值化阈值')
    predict_parser.add_argument('--no-refine', action='store_true', help='禁用边缘细化')
    
    batch_parser = subparsers.add_parser('batch', help='批量显著性检测')
    batch_parser.add_argument('--input', '-i', required=True, help='输入目录')
    batch_parser.add_argument('--output', '-o', default=None, help='输出目录')
    batch_parser.add_argument('--model', '-m', default='basnet', choices=['basnet', 'poolnet'], help='模型选择')
    batch_parser.add_argument('--batch-size', '-b', type=int, default=4, help='批量大小')
    batch_parser.add_argument('--threshold', '-t', type=float, default=0.5, help='二值化阈值')
    batch_parser.add_argument('--save-segmented', action='store_true', help='保存分割结果')
    batch_parser.add_argument('--save-overlay', action='store_true', help='保存叠加图')
    
    api_parser = subparsers.add_parser('api', help='启动Flask API服务')
    api_parser.add_argument('--host', default=Config.FLASK_HOST, help='监听地址')
    api_parser.add_argument('--port', type=int, default=Config.FLASK_PORT, help='监听端口')
    
    models_parser = subparsers.add_parser('models', help='列出可用模型')
    
    args = parser.parse_args()
    
    if args.command == 'predict':
        run_single_predict(args)
    elif args.command == 'batch':
        run_batch_process(args)
    elif args.command == 'api':
        run_api_service(args)
    elif args.command == 'models':
        list_available_models()
    else:
        parser.print_help()


def run_single_predict(args):
    print("=" * 60)
    print("单图显著性检测")
    print("=" * 60)
    
    output_dir = args.output or Config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"输入图像: {args.input}")
    print(f"输出目录: {output_dir}")
    print(f"模型: {args.model}")
    print(f"阈值: {args.threshold}")
    print(f"边缘细化: {not args.no_refine}")
    
    inferencer = SaliencyInferencer(model_name=args.model, pretrained=False)
    
    result = inferencer.predict_and_save(
        args.input,
        output_dir=output_dir,
        threshold=args.threshold,
        edge_refinement=not args.no_refine
    )
    
    print(f"\n检测完成!")
    print(f"显著图: {result['saliency_path']}")
    print(f"掩膜图: {result['mask_path']}")
    print(f"平均显著值: {result['saliency_map'].mean():.4f}")


def run_batch_process(args):
    print("=" * 60)
    print("批量显著性检测")
    print("=" * 60)
    
    output_dir = args.output or Config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"输入目录: {args.input}")
    print(f"输出目录: {output_dir}")
    print(f"模型: {args.model}")
    print(f"批量大小: {args.batch_size}")
    print(f"阈值: {args.threshold}")
    
    inferencer = SaliencyInferencer(model_name=args.model, pretrained=False)
    batch_processor = BatchProcessor(inferencer)
    
    result = batch_processor.process_directory(
        input_dir=args.input,
        output_dir=output_dir,
        batch_size=args.batch_size,
        threshold=args.threshold,
        edge_refinement=True,
        save_maps=True,
        save_masks=True,
        save_segmented=args.save_segmented,
        save_overlay=args.save_overlay
    )
    
    print(f"\n批量处理完成!")
    print(f"处理图像数: {result['total_images']}")
    
    print("\n处理结果:")
    for i, item in enumerate(result['results']):
        print(f"  {i+1}. {item['filename']} - 平均显著值: {item['stats']['mean_saliency']:.4f}")


def run_api_service(args):
    from api import create_app
    
    print("=" * 60)
    print("显著性目标检测 API 服务")
    print("=" * 60)
    print(f"服务地址: http://{args.host}:{args.port}")
    print(f"API文档: http://{args.host}:{args.port}/")
    print("=" * 60)
    print()
    
    app = create_app()
    app.run(host=args.host, port=args.port, debug=Config.DEBUG, threaded=True)


def list_available_models():
    from models import list_models
    
    print("=" * 60)
    print("可用模型列表")
    print("=" * 60)
    
    models = list_models()
    for name, desc in models.items():
        print(f"  {name}: {desc}")
    
    print()
    print(f"默认模型: {Config.DEFAULT_MODEL}")


if __name__ == '__main__':
    main()
