#!/usr/bin/env python
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import create_directory


def main():
    parser = argparse.ArgumentParser(description='Deep Learning Image Inpainting Tool v3.0')
    parser.add_argument('--mode', type=str, default='single', 
                        choices=['single', 'batch', 'demo', 'compare', 'compare_blend',
                                  'video', 'interactive', 'diverse'],
                        help='Operation mode')
    parser.add_argument('--input', type=str, help='Input image/video path or directory')
    parser.add_argument('--output', type=str, default='output', help='Output path/directory')
    parser.add_argument('--mask', type=str, default=None, help='Mask image path or directory')
    parser.add_argument('--model', type=str, default='partialconv', 
                        choices=['partialconv', 'edgeconnect', 'diverse_partialconv', 'stochastic'],
                        help='Model type')
    parser.add_argument('--mask_type', type=str, default='random',
                        choices=['random', 'stroke', 'bbox', 'watermark', 'text', 'scratch', 'irregular'],
                        help='Mask type for auto-generated masks')
    parser.add_argument('--image_size', type=int, default=256, help='Image size')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate inpainting quality')
    parser.add_argument('--save_viz', action='store_true', help='Save visualization images')
    parser.add_argument('--checkpoint', type=str, default=None, help='Path to model checkpoint')
    parser.add_argument('--blend_method', type=str, default='mixed',
                        choices=['seamless_normal', 'seamless_mixed', 'feathered', 'gradient', 'multi_pass'],
                        help='Poisson blending method')
    parser.add_argument('--feather_radius', type=int, default=5, help='Feather blending radius')
    parser.add_argument('--no_blend', action='store_true', help='Disable Poisson blending')
    parser.add_argument('--dynamic_batch', action='store_true', default=True, help='Enable dynamic batching')
    parser.add_argument('--max_batch_size', type=int, default=32, help='Maximum batch size')
    parser.add_argument('--detailed_eval', action='store_true', help='Detailed evaluation with perceptual metrics')
    
    parser.add_argument('--start_frame', type=int, default=0, help='Video start frame')
    parser.add_argument('--end_frame', type=int, default=-1, help='Video end frame (-1=all)')
    parser.add_argument('--temporal_weight', type=float, default=0.6, help='Temporal consistency weight')
    parser.add_argument('--no_temporal', action='store_true', help='Disable temporal consistency for video')
    parser.add_argument('--fps', type=int, default=None, help='Output video FPS')
    
    parser.add_argument('--num_variants', type=int, default=5, help='Number of diverse results')
    
    args = parser.parse_args()
    
    create_directory(args.output)
    
    if args.mode == 'single':
        from src.inpainter import ImageInpainter
        from src.utils import save_image, visualize_results
        
        if not args.input or not os.path.exists(args.input):
            print("Error: --input is required and must exist for single mode")
            return
        
        print(f"Processing single image: {args.input}")
        inpainter = ImageInpainter(
            model_name=args.model,
            image_size=(args.image_size, args.image_size),
            poisson_blend_method=args.blend_method,
            feather_radius=args.feather_radius,
            enable_poisson_blend=not args.no_blend
        )
        
        if args.checkpoint:
            inpainter.load_checkpoint(args.checkpoint)
        
        image, mask, result = inpainter.inpaint_with_auto_mask(
            args.input, mask_type=args.mask_type
        )
        
        output_path = os.path.join(args.output, 'result.png')
        save_image(result, output_path)
        
        if args.save_viz:
            viz_path = os.path.join(args.output, 'visualization.png')
            visualize_results(image, mask, result, save_path=viz_path)
        
        if args.evaluate:
            metrics = inpainter.evaluate_inpainting(
                image, result, mask, only_masked_region=True, detailed=args.detailed_eval
            )
            inpainter.print_evaluation(metrics)
        
        print(f"\nResult saved to: {output_path}")
    
    elif args.mode == 'batch':
        from src.inpainter import ImageInpainter
        
        if not args.input or not os.path.isdir(args.input):
            print("Error: --input directory is required for batch mode")
            return
        
        print(f"Processing batch from: {args.input}")
        inpainter = ImageInpainter(
            model_name=args.model,
            image_size=(args.image_size, args.image_size),
            poisson_blend_method=args.blend_method,
            feather_radius=args.feather_radius,
            enable_poisson_blend=not args.no_blend
        )
        
        if args.checkpoint:
            inpainter.load_checkpoint(args.checkpoint)
        
        results = inpainter.batch_inpaint(
            input_dir=args.input,
            output_dir=args.output,
            mask_dir=args.mask,
            mask_type=args.mask_type,
            save_visualization=args.save_viz,
            evaluate=args.evaluate,
            dynamic_batch=args.dynamic_batch,
            max_batch_size=args.max_batch_size
        )
        
        print(f"\nProcessed {results['num_processed']} images")
    
    elif args.mode == 'video':
        from src.video_inpainter import VideoInpainter
        
        if not args.input:
            print("Error: --input video path is required for video mode")
            return
        
        print(f"Processing video: {args.input}")
        video_inpainter = VideoInpainter(
            model_name=args.model,
            image_size=(args.image_size, args.image_size),
            poisson_blend_method=args.blend_method,
            temporal_weight=args.temporal_weight,
            use_temporal=not args.no_temporal
        )
        
        if args.output.endswith(('.mp4', '.avi', '.mov')):
            output_path = args.output
        else:
            create_directory(args.output)
            output_path = os.path.join(args.output, 'inpainted_video.mp4')
        
        results = video_inpainter.inpaint_video(
            video_path=args.input,
            output_path=output_path,
            mask_path=args.mask,
            mask_type=args.mask_type,
            start_frame=args.start_frame,
            end_frame=args.end_frame,
            use_temporal=not args.no_temporal,
            output_fps=args.fps
        )
        
        print(f"\nVideo saved to: {output_path}")
    
    elif args.mode == 'interactive':
        from src.interactive_inpainter import InteractiveInpainter
        
        if not args.input or not os.path.exists(args.input):
            print("Error: --input image path is required for interactive mode")
            return
        
        print(f"Interactive inpainting: {args.input}")
        interactor = InteractiveInpainter(
            model_name=args.model,
            image_size=(args.image_size, args.image_size),
            poisson_blend_method=args.blend_method
        )
        
        output_path = os.path.join(args.output, 'interactive_result.png') if args.output else None
        image, mask, result = interactor.inpaint_interactive(args.input, output_path=output_path)
    
    elif args.mode == 'diverse':
        from src.diverse_inpainter import DiverseInpainter
        
        if not args.input or not os.path.exists(args.input):
            print("Error: --input image path is required for diverse mode")
            return
        
        print(f"Generating {args.num_variants} diverse inpainting results...")
        diverse = DiverseInpainter(
            image_size=(args.image_size, args.image_size),
            poisson_blend_method=args.blend_method
        )
        
        results = diverse.inpaint_diverse(
            image_path=args.input,
            mask_type=args.mask_type,
            num_variants=args.num_variants,
            output_dir=args.output
        )
        
        print(f"\nGenerated {results['num_variants']} variants")
        print(f"Best result: {results['best']['method'] if results['best'] else 'N/A'}")
    
    elif args.mode == 'demo':
        from src.inpainter import InpaintingDemo
        from src.utils import save_image
        
        import numpy as np
        
        print("Running inpainting demo...")
        test_img = np.ones((256, 256, 3), dtype=np.float32)
        test_img[:, :, 0] = np.linspace(0.3, 0.9, 256).reshape(1, -1)
        test_img[:, :, 1] = np.linspace(0.5, 0.2, 256).reshape(-1, 1)
        test_img[:, :, 2] = 0.4
        
        test_img_path = os.path.join(args.output, 'test_image.png')
        save_image(test_img, test_img_path)
        
        InpaintingDemo.run_single_image_demo(
            image_path=test_img_path,
            model_name=args.model,
            mask_type=args.mask_type,
            output_path=os.path.join(args.output, 'demo_result.png'),
            blend_method=args.blend_method
        )
        print("Demo completed!")
    
    elif args.mode == 'compare':
        from src.inpainter import InpaintingDemo
        
        if not args.input or not os.path.exists(args.input):
            print("Error: --input is required for compare mode")
            return
        
        InpaintingDemo.compare_models(
            image_path=args.input,
            mask_type=args.mask_type,
            output_dir=args.output
        )
    
    elif args.mode == 'compare_blend':
        from src.inpainter import InpaintingDemo
        
        if not args.input or not os.path.exists(args.input):
            print("Error: --input is required for compare_blend mode")
            return
        
        InpaintingDemo.compare_blend_methods(
            image_path=args.input,
            mask_type=args.mask_type,
            output_dir=args.output
        )


if __name__ == '__main__':
    main()
