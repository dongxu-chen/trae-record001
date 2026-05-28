#!/usr/bin/env python3
import argparse
import os
import sys

from flow_interpolation import VideoInterpolator, InterpolationConfig
from flow_interpolation.sr_interpolator import VideoProcessor, SRFrameInterpolator
from flow_interpolation.super_resolution import create_sr_processor
from flow_interpolation.style_transfer import create_style_processor


def parse_args():
    parser = argparse.ArgumentParser(
        description='Optical Flow Guided Video Frame Interpolation using RAFT',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--input', '-i', type=str, required=True,
                        help='Input video path')
    parser.add_argument('--output', '-o', type=str, required=True,
                        help='Output video path')
    
    parser.add_argument('--source-fps', type=float, default=None,
                        help='Source video FPS (default: auto-detect)')
    parser.add_argument('--target-fps', type=int, default=60,
                        help='Target output FPS')
    
    parser.add_argument('--raft-model', type=str, default=None,
                        help='Path to pretrained RAFT model weights')
    parser.add_argument('--raft-iters', type=int, default=12,
                        help='Number of RAFT iterations')
    parser.add_argument('--raft-small', action='store_true',
                        help='Use small RAFT model')
    
    parser.add_argument('--no-gpu', action='store_true',
                        help='Disable GPU acceleration')
    
    parser.add_argument('--no-occlusion', action='store_true',
                        help='Disable occlusion detection')
    parser.add_argument('--occlusion-threshold', type=float, default=0.01,
                        help='Occlusion detection threshold')
    
    parser.add_argument('--no-motion-blur', action='store_true',
                        help='Disable motion blur generation')
    parser.add_argument('--motion-blur-kernel', type=int, default=11,
                        help='Motion blur kernel size')
    parser.add_argument('--motion-blur-strength', type=float, default=1.0,
                        help='Motion blur strength')
    
    parser.add_argument('--no-bidirectional', action='store_true',
                        help='Disable bidirectional flow')
    
    parser.add_argument('--output-resolution', type=int, nargs=2, default=None,
                        metavar=('WIDTH', 'HEIGHT'),
                        help='Output video resolution')
    parser.add_argument('--crf', type=int, default=18,
                        help='Output video CRF quality (lower = better)')
    parser.add_argument('--preset', type=str, default='medium',
                        help='FFmpeg encoder preset')
    
    parser.add_argument('--save-flow', action='store_true',
                        help='Save flow visualization (first 5 frames)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    
    parser.add_argument('--sr', action='store_true',
                        help='Enable super-resolution')
    parser.add_argument('--sr-scale', type=int, default=2,
                        help='Super-resolution scale factor')
    parser.add_argument('--sr-model', type=str, default=None,
                        help='Path to SR model weights')
    parser.add_argument('--sr-no-esrgan', action='store_true',
                        help='Use bilinear upsampling instead of ESRGAN')
    
    parser.add_argument('--smoothness', type=float, default=None,
                        help='Interpolation smoothness (0.0-1.0)')
    parser.add_argument('--sharpness', type=float, default=None,
                        help='Interpolation sharpness (0.0-1.0)')
    parser.add_argument('--preset', type=str, default=None,
                        choices=['smooth', 'balanced', 'sharp', 'cinematic', 'gameplay'],
                        dest='strength_preset',
                        help='Quality preset (smooth/balanced/sharp/cinematic/gameplay)')
    
    parser.add_argument('--style-transfer', action='store_true',
                        help='Enable style transfer')
    parser.add_argument('--style-image', type=str, default=None,
                        help='Path to style reference image')
    parser.add_argument('--style-model', type=str, default=None,
                        help='Path to style transfer model weights')
    parser.add_argument('--style-alpha', type=float, default=1.0,
                        help='Style transfer intensity (0.0-1.0)')
    parser.add_argument('--style-name', type=str, default='custom',
                        help='Style name identifier')
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    if not os.path.exists(args.input):
        print(f'Error: Input file not found: {args.input}', file=sys.stderr)
        sys.exit(1)
    
    config = InterpolationConfig(
        target_fps=args.target_fps,
        source_fps=args.source_fps,
        use_gpu=not args.no_gpu,
        raft_model_path=args.raft_model,
        raft_iters=args.raft_iters,
        raft_small=args.raft_small,
        occlusion_detection=not args.no_occlusion,
        occlusion_threshold=args.occlusion_threshold,
        bidirectional_flow=not args.no_bidirectional,
        motion_blur=not args.no_motion_blur,
        motion_blur_kernel_size=args.motion_blur_kernel,
        motion_blur_strength=args.motion_blur_strength,
        output_resolution=tuple(args.output_resolution) if args.output_resolution else None,
        output_crf=args.crf,
        output_preset=args.preset if args.preset else 'medium',
        save_flow_visualization=args.save_flow,
        verbose=args.verbose,
        enable_sr=args.sr,
        sr_scale=args.sr_scale,
        sr_model_path=args.sr_model,
        sr_use_esrgan=not args.sr_no_esrgan,
        smoothness=args.smoothness if args.smoothness is not None else 0.5,
        sharpness=args.sharpness if args.sharpness is not None else 0.5,
        strength_preset=args.strength_preset,
        enable_style_transfer=args.style_transfer,
        style_model_path=args.style_model,
        style_image_path=args.style_image,
        style_alpha=args.style_alpha,
        style_name=args.style_name
    )
    
    if args.verbose:
        print(f'Configuration:')
        print(f'  Device: {config.device}')
        print(f'  Source FPS: {config.source_fps or "auto"}')
        print(f'  Target FPS: {config.target_fps}')
        print(f'  Super-resolution: {config.enable_sr} (scale={config.sr_scale})')
        print(f'  Style transfer: {config.enable_style_transfer}')
        print(f'  Smoothness: {config.smoothness}, Sharpness: {config.sharpness}')
    
    print('Initializing Video Interpolator...')
    
    if config.enable_sr or config.enable_style_transfer:
        sr_processor = None
        if config.enable_sr:
            print(f'Loading super-resolution processor (scale={config.sr_scale})...')
            sr_processor = create_sr_processor(
                scale=config.sr_scale,
                device=config.device,
                model_path=config.sr_model_path,
                use_esrgan=config.sr_use_esrgan
            )
        
        style_processor = None
        if config.enable_style_transfer:
            print(f'Loading style transfer processor...')
            style_processor = create_style_processor(
                device=config.device,
                model_path=config.style_model_path,
                style_name=config.style_name
            )
            if config.style_image_path:
                style_processor.set_style_from_path(config.style_image_path)
                print(f'  Style image: {config.style_image_path}')
        
        from flow_interpolation.raft import load_raft_model
        raft_model = load_raft_model(
            model_path=config.raft_model_path,
            small=config.raft_small,
            device=config.device
        )
        
        processor = VideoProcessor(config, raft_model, sr_processor, style_processor)
        
        if args.smoothness is not None or args.sharpness is not None or args.strength_preset is not None:
            processor.set_strength(
                smoothness=args.smoothness,
                sharpness=args.sharpness,
                preset=args.strength_preset
            )
        
        print(f'Starting processing: {args.input} -> {args.output}')
        try:
            processor.process_video_sr(
                args.input, args.output,
                sr_scale=config.sr_scale,
                use_sr=config.enable_sr,
                use_style=config.enable_style_transfer,
                style_alpha=config.style_alpha
            )
            print('Done!')
        except KeyboardInterrupt:
            print('\nInterrupted by user.')
            sys.exit(130)
        except Exception as e:
            print(f'Error: {e}', file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        interpolator = VideoInterpolator(config)
        
        print(f'Starting interpolation: {args.input} -> {args.output}')
        try:
            interpolator.process_video(args.input, args.output)
            print('Done!')
        except KeyboardInterrupt:
            print('\nInterrupted by user.')
            sys.exit(130)
        except Exception as e:
            print(f'Error: {e}', file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()
