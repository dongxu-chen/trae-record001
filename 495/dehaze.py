import argparse
import os
import sys
import cv2
import numpy as np

from dark_channel_dehazer import DarkChannelDehazer
from utils import (load_image, save_image, batch_dehaze, 
                   batch_dehaze_with_report, visualize_results, 
                   create_synthetic_hazy_image, resize_image, 
                   calculate_psnr, estimate_batch_haze_density,
                   evaluate_dehazing, print_evaluation_report)

try:
    from aod_net import AODNetDehazer
    AOD_NET_AVAILABLE = True
except (ImportError, OSError, Exception):
    AOD_NET_AVAILABLE = False
    AODNetDehazer = None


def get_dehazer(method, **kwargs):
    if method == 'dark_channel':
        return DarkChannelDehazer(
            patch_size=kwargs.get('patch_size', 15),
            omega=kwargs.get('omega', None),
            t_min=kwargs.get('t_min', None),
            sky_detection=kwargs.get('sky_detection', True),
            sky_threshold=kwargs.get('sky_threshold', 0.7),
            dehaze_strength=kwargs.get('strength', None),
            adaptive_params=kwargs.get('adaptive_params', True),
            auto_brightness=kwargs.get('auto_brightness', True),
            enhance_enabled=kwargs.get('enhance_enabled', False),
            enhance_strength=kwargs.get('enhance_strength', 0.5)
        )
    elif method == 'aod_net':
        if not AOD_NET_AVAILABLE:
            raise ImportError("AOD-Net requires PyTorch, which is not available. "
                            "Please install PyTorch or use dark_channel method.")
        model_path = kwargs.get('model_path', None)
        return AODNetDehazer(
            model_path=model_path,
            dehaze_strength=kwargs.get('strength', 1.0)
        )
    else:
        raise ValueError(f"Unknown method: {method}")


def single_image_dehaze(args):
    dehazer = get_dehazer(
        args.method,
        patch_size=args.patch_size,
        omega=args.omega,
        t_min=args.t_min,
        sky_detection=not args.no_sky_detection,
        sky_threshold=args.sky_threshold,
        strength=args.strength,
        model_path=args.model_path,
        adaptive_params=not args.no_adaptive,
        auto_brightness=not args.no_auto_brightness,
        enhance_enabled=args.enhance,
        enhance_strength=args.enhance_strength
    )
    img = load_image(args.input)
    if args.resize:
        img = resize_image(img, args.resize)
    if args.enhance and hasattr(dehazer, 'dehaze_with_info_and_enhance'):
        final, dehazed, info = dehazer.dehaze_with_info_and_enhaze(img)
        print("\n" + "=" * 50)
        print("Dehazing + Enhancement Information:")
        print(f"  Haze Density:     {info['haze_density']:.3f}")
        print(f"  Omega:            {info['omega']:.3f}")
        print(f"  T_min:            {info['t_min']:.3f}")
        print(f"  Strength:         {info['strength']:.3f}")
        print(f"  Sky Region Ratio: {info['sky_ratio']:.3f}")
        print(f"  Enhanced:         {info['enhanced']}")
        if info.get('atmospheric_light') is not None:
            al = info['atmospheric_light']
            print(f"  Atmospheric Light: R={al[0]:.3f}, G={al[1]:.3f}, B={al[2]:.3f}")
        print("=" * 50 + "\n")
    elif hasattr(dehazer, 'dehaze_with_info') and args.show_info:
        dehazed, info = dehazer.dehaze_with_info(img)
        final = dehazed
        print("\n" + "=" * 50)
        print("Dehazing Information:")
        print(f"  Haze Density:     {info['haze_density']:.3f}")
        print(f"  Omega:            {info['omega']:.3f}")
        print(f"  T_min:            {info['t_min']:.3f}")
        print(f"  Strength:         {info['strength']:.3f}")
        print(f"  Sky Region Ratio: {info['sky_ratio']:.3f}")
        if info.get('atmospheric_light') is not None:
            al = info['atmospheric_light']
            print(f"  Atmospheric Light: R={al[0]:.3f}, G={al[1]:.3f}, B={al[2]:.3f}")
        print("=" * 50 + "\n")
    else:
        dehazed = dehazer.dehaze(img)
        final = dehazed
        if hasattr(dehazer, 'last_haze_density') and dehazer.last_haze_density is not None:
            print(f"Estimated haze density: {dehazer.last_haze_density:.3f}")
    if args.evaluate:
        clear_img = None
        if args.reference_image:
            clear_img = load_image(args.reference_image)
            if args.resize:
                clear_img = resize_image(clear_img, args.resize)
        metrics = evaluate_dehazing(img, final, clear_img)
        print_evaluation_report(metrics, "Dehazing Quality Evaluation")
    if args.output:
        save_image(args.output, final)
        print(f"Dehazed image saved to {args.output}")
    if args.visualize:
        transmission = None
        sky_mask = None
        if args.method == 'dark_channel':
            transmission = dehazer.get_transmission_map(img)
            if hasattr(dehazer, 'get_sky_mask') and not args.no_sky_detection:
                sky_mask = dehazer.get_sky_mask(img)
        if sky_mask is not None:
            import matplotlib.pyplot as plt
            original_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            final_rgb = cv2.cvtColor(final, cv2.COLOR_BGR2RGB)
            fig, axes = plt.subplots(1, 4, figsize=(20, 5))
            axes[0].imshow(original_rgb)
            axes[0].set_title('Hazy Image')
            axes[0].axis('off')
            axes[1].imshow(sky_mask, cmap='gray')
            axes[1].set_title('Sky Mask')
            axes[1].axis('off')
            axes[2].imshow(transmission, cmap='gray')
            axes[2].set_title('Transmission Map')
            axes[2].axis('off')
            axes[3].imshow(final_rgb)
            axes[3].set_title('Dehazed + Enhanced' if args.enhance else 'Dehazed Image')
            axes[3].axis('off')
            plt.tight_layout()
            if args.save_visualization:
                plt.savefig(args.save_visualization, dpi=150, bbox_inches='tight')
                print(f"Comparison saved to {args.save_visualization}")
            plt.show()
        else:
            visualize_results(img, final, transmission, 
                             save_path=args.save_visualization)
    return final


def batch_process(args):
    dehazer = get_dehazer(
        args.method,
        patch_size=args.patch_size,
        omega=args.omega,
        t_min=args.t_min,
        sky_detection=not args.no_sky_detection,
        sky_threshold=args.sky_threshold,
        strength=args.strength,
        model_path=args.model_path,
        adaptive_params=not args.no_adaptive,
        auto_brightness=not args.no_auto_brightness,
        enhance_enabled=args.enhance,
        enhance_strength=args.enhance_strength
    )
    if args.estimate_only:
        print("Running haze density estimation only...")
        haze_densities = estimate_batch_haze_density(dehazer, args.input_dir)
        return haze_densities
    elif args.with_report:
        print("Running batch dehazing with detailed report...")
        report = batch_dehaze_with_report(dehazer, args.input_dir, args.output_dir)
        if args.save_report:
            import json
            with open(args.save_report, 'w', encoding='utf-8') as f:
                def convert_to_serializable(obj):
                    if isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, np.integer):
                        return int(obj)
                    return obj
                json.dump(report, f, indent=2, ensure_ascii=False, default=convert_to_serializable)
            print(f"Report saved to {args.save_report}")
        return report
    else:
        processed = batch_dehaze(dehazer, args.input_dir, args.output_dir,
                                pre_estimate_haze=not args.no_pre_estimate)
        return processed


def demo_synthetic(args):
    if args.clear_image:
        clear_img = load_image(args.clear_image)
    else:
        clear_img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        clear_img = cv2.imread('test.jpg') if os.path.exists('test.jpg') else clear_img
    clear_img = resize_image(clear_img, 800)
    hazy_img = create_synthetic_hazy_image(clear_img, haze_level=args.haze_level)
    dehazer = get_dehazer(
        args.method,
        patch_size=args.patch_size,
        omega=args.omega,
        t_min=args.t_min,
        sky_detection=not args.no_sky_detection,
        sky_threshold=args.sky_threshold,
        strength=args.strength,
        adaptive_params=not args.no_adaptive,
        auto_brightness=not args.no_auto_brightness,
        enhance_enabled=args.enhance,
        enhance_strength=args.enhance_strength
    )
    if args.enhance and hasattr(dehazer, 'dehaze_with_info_and_enhance'):
        final_img, dehazed_img, info = dehazer.dehaze_with_info_and_enhance(hazy_img)
        print("\nAdaptive Parameters (with Enhancement):")
    elif hasattr(dehazer, 'dehaze_with_info'):
        dehazed_img, info = dehazer.dehaze_with_info(hazy_img)
        final_img = dehazed_img
        print("\nAdaptive Parameters:")
    else:
        dehazed_img = dehazer.dehaze(hazy_img)
        final_img = dehazed_img
        info = None
    if info:
        print(f"  Synthetic Haze Level: {args.haze_level:.3f}")
        print(f"  Estimated Haze Density: {info['haze_density']:.3f}")
        print(f"  Omega: {info['omega']:.3f}, T_min: {info['t_min']:.3f}, Strength: {info['strength']:.3f}")
        if info.get('enhanced'):
            print(f"  Enhanced: Yes")
    psnr = calculate_psnr(clear_img, final_img)
    print(f"PSNR: {psnr:.2f} dB")
    if args.output:
        save_image(args.output, dehazed_img)
        save_image(args.output.replace('.', '_hazy.'), hazy_img)
    visualize_results(hazy_img, dehazed_img, 
                     save_path=args.save_visualization)


def main():
    parser = argparse.ArgumentParser(description='Image Dehazing Tool with Adaptive Parameters')
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    single_parser = subparsers.add_parser('single', help='Single image dehazing')
    single_parser.add_argument('-i', '--input', required=True, help='Input image path')
    single_parser.add_argument('-o', '--output', help='Output image path')
    single_parser.add_argument('-m', '--method', default='dark_channel',
                              choices=['dark_channel', 'aod_net'], help='Dehazing method')
    single_parser.add_argument('-s', '--strength', type=float, default=None,
                              help='Dehaze strength (0.0-2.0), default: auto/adaptive')
    single_parser.add_argument('--patch-size', type=int, default=15,
                              help='Patch size for dark channel')
    single_parser.add_argument('--omega', type=float, default=None,
                              help='Omega value for haze removal, default: auto/adaptive')
    single_parser.add_argument('--t-min', type=float, default=None,
                              help='Minimum transmission value, default: auto/adaptive')
    single_parser.add_argument('--no-sky-detection', action='store_true',
                              help='Disable sky region detection')
    single_parser.add_argument('--sky-threshold', type=float, default=0.7,
                              help='Sky detection threshold')
    single_parser.add_argument('--model-path', help='Path to AOD-Net model weights')
    single_parser.add_argument('--visualize', action='store_true',
                              help='Visualize results')
    single_parser.add_argument('--save-visualization', help='Path to save visualization')
    single_parser.add_argument('--resize', type=int, help='Resize max dimension')
    single_parser.add_argument('--no-adaptive', action='store_true',
                              help='Disable adaptive parameter adjustment')
    single_parser.add_argument('--no-auto-brightness', action='store_true',
                              help='Disable automatic brightness adjustment')
    single_parser.add_argument('--show-info', action='store_true', default=True,
                              help='Show detailed dehazing information')
    single_parser.add_argument('--enhance', action='store_true',
                              help='Enable contrast enhancement after dehazing')
    single_parser.add_argument('--enhance-strength', type=float, default=0.5,
                              help='Enhancement strength (0.0-2.0)')
    single_parser.add_argument('--evaluate', action='store_true',
                              help='Evaluate dehazing quality')
    single_parser.add_argument('--reference-image', help='Reference clear image for evaluation')
    batch_parser = subparsers.add_parser('batch', help='Batch image dehazing')
    batch_parser.add_argument('-i', '--input-dir', required=True, help='Input directory')
    batch_parser.add_argument('-o', '--output-dir', required=True, help='Output directory')
    batch_parser.add_argument('-m', '--method', default='dark_channel',
                             choices=['dark_channel', 'aod_net'], help='Dehazing method')
    batch_parser.add_argument('-s', '--strength', type=float, default=None,
                             help='Dehaze strength (0.0-2.0), default: auto/adaptive')
    batch_parser.add_argument('--patch-size', type=int, default=15,
                             help='Patch size for dark channel')
    batch_parser.add_argument('--omega', type=float, default=None,
                             help='Omega value for haze removal, default: auto/adaptive')
    batch_parser.add_argument('--t-min', type=float, default=None,
                             help='Minimum transmission value, default: auto/adaptive')
    batch_parser.add_argument('--no-sky-detection', action='store_true',
                             help='Disable sky region detection')
    batch_parser.add_argument('--sky-threshold', type=float, default=0.7,
                             help='Sky detection threshold')
    batch_parser.add_argument('--model-path', help='Path to AOD-Net model weights')
    batch_parser.add_argument('--no-adaptive', action='store_true',
                              help='Disable adaptive parameter adjustment')
    batch_parser.add_argument('--no-auto-brightness', action='store_true',
                              help='Disable automatic brightness adjustment')
    batch_parser.add_argument('--no-pre-estimate', action='store_true',
                              help='Disable haze density pre-estimation')
    batch_parser.add_argument('--estimate-only', action='store_true',
                              help='Only estimate haze density without dehazing')
    batch_parser.add_argument('--with-report', action='store_true',
                              help='Generate detailed processing report')
    batch_parser.add_argument('--save-report', help='Path to save JSON report')
    batch_parser.add_argument('--enhance', action='store_true',
                              help='Enable contrast enhancement after dehazing')
    batch_parser.add_argument('--enhance-strength', type=float, default=0.5,
                              help='Enhancement strength (0.0-2.0)')
    video_parser = subparsers.add_parser('video', help='Video dehazing')
    video_parser.add_argument('-i', '--input', required=True, help='Input video path')
    video_parser.add_argument('-o', '--output', required=True, help='Output video path')
    video_parser.add_argument('-m', '--method', default='dark_channel',
                             choices=['dark_channel', 'aod_net'], help='Dehazing method')
    video_parser.add_argument('-s', '--strength', type=float, default=None,
                             help='Dehaze strength (0.0-2.0), default: auto/adaptive')
    video_parser.add_argument('--patch-size', type=int, default=15,
                             help='Patch size for dark channel')
    video_parser.add_argument('--omega', type=float, default=None,
                             help='Omega value for haze removal, default: auto/adaptive')
    video_parser.add_argument('--t-min', type=float, default=None,
                             help='Minimum transmission value, default: auto/adaptive')
    video_parser.add_argument('--no-sky-detection', action='store_true',
                              help='Disable sky region detection')
    video_parser.add_argument('--sky-threshold', type=float, default=0.7,
                              help='Sky detection threshold')
    video_parser.add_argument('--model-path', help='Path to AOD-Net model weights')
    video_parser.add_argument('--no-adaptive', action='store_true',
                              help='Disable adaptive parameter adjustment')
    video_parser.add_argument('--no-auto-brightness', action='store_true',
                              help='Disable automatic brightness adjustment')
    video_parser.add_argument('--no-temporal-smooth', action='store_true',
                              help='Disable temporal smoothing')
    video_parser.add_argument('--smooth-window', type=int, default=5,
                              help='Temporal smoothing window size')
    video_parser.add_argument('--enhance', action='store_true',
                              help='Enable contrast enhancement after dehazing')
    video_parser.add_argument('--enhance-strength', type=float, default=0.5,
                              help='Enhancement strength (0.0-2.0)')
    video_parser.add_argument('--start-frame', type=int, default=0,
                              help='Start frame index')
    video_parser.add_argument('--max-frames', type=int,
                              help='Maximum number of frames to process')
    video_parser.add_argument('--preview', action='store_true',
                              help='Preview mode (press q to quit)')
    video_parser.add_argument('--evaluate', action='store_true',
                              help='Evaluate dehazing quality')
    evaluate_parser = subparsers.add_parser('evaluate', help='Evaluate dehazing quality')
    evaluate_parser.add_argument('--hazy', required=True, help='Hazy image/video path')
    evaluate_parser.add_argument('--dehazed', required=True, help='Dehazed image/video path')
    evaluate_parser.add_argument('--reference', help='Reference clear image/video path')
    evaluate_parser.add_argument('--video', action='store_true',
                              help='Evaluate video instead of image')
    evaluate_parser.add_argument('--sample-interval', type=int, default=30,
                              help='Sample interval for video evaluation')
    demo_parser = subparsers.add_parser('demo', help='Demo with synthetic hazy image')
    demo_parser.add_argument('-c', '--clear-image', help='Clear image path')
    demo_parser.add_argument('-o', '--output', help='Output image path')
    demo_parser.add_argument('-m', '--method', default='dark_channel',
                            choices=['dark_channel', 'aod_net'], help='Dehazing method')
    demo_parser.add_argument('--haze-level', type=float, default=0.6,
                            help='Synthetic haze level (0.0-1.0)')
    demo_parser.add_argument('-s', '--strength', type=float, default=None,
                            help='Dehaze strength (0.0-2.0), default: auto/adaptive')
    demo_parser.add_argument('--patch-size', type=int, default=15,
                            help='Patch size for dark channel')
    demo_parser.add_argument('--omega', type=float, default=None,
                            help='Omega value for haze removal, default: auto/adaptive')
    demo_parser.add_argument('--t-min', type=float, default=None,
                            help='Minimum transmission value, default: auto/adaptive')
    demo_parser.add_argument('--no-sky-detection', action='store_true',
                            help='Disable sky region detection')
    demo_parser.add_argument('--sky-threshold', type=float, default=0.7,
                            help='Sky detection threshold')
    demo_parser.add_argument('--save-visualization', help='Path to save visualization')
    demo_parser.add_argument('--no-adaptive', action='store_true',
                              help='Disable adaptive parameter adjustment')
    demo_parser.add_argument('--no-auto-brightness', action='store_true',
                              help='Disable automatic brightness adjustment')
    args = parser.parse_args()
    if args.mode is None:
        parser.print_help()
        sys.exit(1)
    if args.mode == 'single':
        single_image_dehaze(args)
    elif args.mode == 'batch':
        batch_process(args)
    elif args.mode == 'demo':
        demo_synthetic(args)
    elif args.mode == 'video':
        video_dehaze(args)
    elif args.mode == 'evaluate':
        evaluate_mode(args)


def video_dehaze(args):
    try:
        from video_dehazer import VideoDehazer
    except ImportError as e:
        print(f"Error importing VideoDehazer: {e}")
        return
    dehazer = get_dehazer(
        args.method,
        patch_size=args.patch_size,
        omega=args.omega,
        t_min=args.t_min,
        sky_detection=not args.no_sky_detection,
        sky_threshold=args.sky_threshold,
        strength=args.strength,
        model_path=args.model_path,
        adaptive_params=not args.no_adaptive,
        auto_brightness=not args.no_auto_brightness,
        enhance_enabled=False,
        enhance_strength=args.enhance_strength
    )
    video_dehazer = VideoDehazer(
        dehazer=dehazer,
        smooth_window=args.smooth_window,
        temporal_smooth=not args.no_temporal_smooth,
        show_progress=True,
        enhance_enabled=args.enhance,
        enhance_strength=args.enhance_strength
    )
    if args.preview:
        result = video_dehazer.process_video_with_preview(
            args.input,
            args.output if args.output else None
        )
    else:
        result = video_dehazer.process_video(
            args.input,
            args.output,
            start_frame=args.start_frame,
            max_frames=args.max_frames
        )
    if args.evaluate:
        try:
            from video_dehazer import evaluate_video_dehazing
            metrics = evaluate_video_dehazing(args.input, args.output)
        except Exception as e:
            print(f"Evaluation error: {e}")
    return result


def evaluate_mode(args):
    if args.video:
        try:
            from video_dehazer import evaluate_video_dehazing
            metrics = evaluate_video_dehazing(
                args.hazy,
                args.dehazed,
                args.sample_interval
            )
        except Exception as e:
            print(f"Video evaluation error: {e}")
            return
    else:
        hazy_img = load_image(args.hazy)
        dehazed_img = load_image(args.dehazed)
        clear_img = None
        if args.reference:
            clear_img = load_image(args.reference)
        metrics = evaluate_dehazing(hazy_img, dehazed_img, clear_img)
        print_evaluation_report(metrics, "Image Dehazing Evaluation")
    return metrics


if __name__ == '__main__':
    main()
