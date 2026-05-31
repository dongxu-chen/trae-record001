#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from super_resolution_pipeline import SuperResolutionPipeline, get_available_models, get_available_scales


def main():
    parser = argparse.ArgumentParser(description='视频超分辨率重建系统')
    
    parser.add_argument('--input', '-i', type=str, required=True,
                        help='输入视频或图片路径')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='输出路径 (可选)')
    parser.add_argument('--model', '-m', type=str, default='edsr',
                        choices=get_available_models(),
                        help='超分模型选择')
    parser.add_argument('--scale', '-s', type=int, default=4,
                        choices=get_available_scales(),
                        help='超分倍数')
    parser.add_argument('--weights', '-w', type=str, default=None,
                        help='预训练权重路径')
    
    parser.add_argument('--no-denoise', action='store_true',
                        help='禁用多帧融合降噪')
    parser.add_argument('--no-temporal', action='store_true',
                        help='禁用时序一致性')
    parser.add_argument('--no-bitrate', action='store_true',
                        help='禁用码率自适应')
    parser.add_argument('--enable-face', action='store_true',
                        help='启用人脸区域增强')
    parser.add_argument('--enable-subtitle', action='store_true',
                        help='启用字幕清晰化')
    parser.add_argument('--enable-realtime', action='store_true',
                        help='启用实时超分优化')
    parser.add_argument('--half', action='store_true',
                        help='使用半精度推理 (FP16)')
    
    parser.add_argument('--fusion-method', type=str, default='weighted_average',
                        choices=['weighted_average', 'gaussian', 'bilateral', 'adaptive'],
                        help='多帧融合方法')
    parser.add_argument('--temporal-method', type=str, default='optical_flow',
                        choices=['optical_flow', 'simple_average', 'rolling_guidance', 'deep_flow'],
                        help='时序一致性方法')
    parser.add_argument('--quality', type=str, default='high',
                        choices=['low', 'medium', 'high', 'ultra'],
                        help='输出质量')
    
    parser.add_argument('--start-time', type=float, default=None,
                        help='开始时间 (秒)')
    parser.add_argument('--duration', type=float, default=None,
                        help='处理时长 (秒)')
    parser.add_argument('--fps', type=int, default=None,
                        help='目标帧率')
    
    parser.add_argument('--image-mode', action='store_true',
                        help='图片处理模式')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        sys.exit(1)
    
    print("=" * 60)
    print("视频超分辨率重建系统")
    print("=" * 60)
    print(f"模型: {args.model.upper()} x{args.scale}")
    print(f"输入: {args.input}")
    print(f"降噪: {'关闭' if args.no_denoise else '开启'}")
    print(f"时序一致性: {'关闭' if args.no_temporal else '开启'}")
    print(f"码率自适应: {'关闭' if args.no_bitrate else '开启'}")
    print(f"人脸增强: {'开启' if args.enable_face else '关闭'}")
    print(f"字幕清晰化: {'开启' if args.enable_subtitle else '关闭'}")
    print(f"实时超分: {'开启' if args.enable_realtime else '关闭'}")
    print(f"半精度: {'开启' if args.half else '关闭'}")
    print("=" * 60)
    
    pipeline = SuperResolutionPipeline(
        model_name=args.model,
        scale=args.scale,
        weight_path=args.weights,
        enable_denoise=not args.no_denoise,
        enable_temporal=not args.no_temporal,
        enable_bitrate_adapt=not args.no_bitrate,
        enable_face_enhance=args.enable_face,
        enable_subtitle_enhance=args.enable_subtitle,
        enable_realtime=args.enable_realtime,
        half_precision=args.half,
    )
    
    if args.image_mode:
        print("正在处理图片...")
        result = pipeline.process_image(args.input, args.output)
        print(f"\n处理完成!")
        print(f"输出文件: {result['output_path']}")
        print(f"分辨率: {result['original_resolution']} -> {result['resolution']}")
    else:
        print("正在处理视频...")
        
        def progress_cb(current, total):
            percent = current / total * 100
            print(f"\r进度: {current}/{total} 帧 ({percent:.1f}%)", end='')
        
        result = pipeline.process_video(
            input_path=args.input,
            output_path=args.output,
            start_time=args.start_time,
            duration=args.duration,
            target_fps=args.fps,
            target_quality=args.quality,
            progress_callback=progress_cb,
        )
        
        print(f"\n\n处理完成!")
        print(f"输出文件: {result['output_path']}")
        print(f"处理帧数: {result['num_frames']}")
        print(f"帧率: {result['fps']:.1f} FPS")
        print(f"分辨率: {result['original_resolution']} -> {result['resolution']}")
        print(f"音频: {'包含' if result['has_audio'] else '无'}")
        if result.get('face_enhance_enabled'):
            print(f"人脸增强: ✓ 已启用")
        if result.get('subtitle_enhance_enabled'):
            print(f"字幕清晰化: ✓ 已启用")
        if result.get('realtime_stats'):
            rs = result['realtime_stats']
            print(f"实时性能: {rs['fps']:.1f} FPS (目标 {rs['target_fps']} FPS)")
            print(f"缓存命中率: {rs['cache_hit_rate']*100:.1f}%")


if __name__ == '__main__':
    main()
