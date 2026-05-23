import os
import sys
import argparse
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description='RCAN Infrared Image Super-Resolution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train the model
  python main.py --mode train --config config.yaml
  
  # Single image inference
  python main.py --mode infer --checkpoint models/best_model.pth --input test.jpg --output results/
  
  # Batch inference
  python main.py --mode infer --checkpoint models/best_model.pth --input data/test/ --output results/ --batch
  
  # Export model to ONNX
  python main.py --mode export --checkpoint models/best_model.pth --output models/rcan.onnx
  
  # Prune model (40% parameter reduction)
  python main.py --mode prune --checkpoint models/best_model.pth --output models/pruned.pth --fine_tune
  
  # Real-time camera super-resolution
  python main.py --mode camera --checkpoint models/best_model.pth --colormap jet
  
  # Video super-resolution
  python main.py --mode video --checkpoint models/best_model.pth --input video.mp4 --output sr_video.mp4
  
  # Thermal heatmap enhancement
  python main.py --mode heatmap --input sr_image.png --output heatmap.png --colormap jet
        """
    )
    
    parser.add_argument('--mode', type=str, 
                       choices=['train', 'infer', 'export', 'prune', 'camera', 'video', 'heatmap'],
                       required=True, help='Operation mode')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--checkpoint', type=str, help='Path to model checkpoint')
    parser.add_argument('--input', type=str, help='Input image/video path or directory')
    parser.add_argument('--output', type=str, help='Output path or directory')
    parser.add_argument('--batch', action='store_true', help='Batch inference mode')
    parser.add_argument('--hr', type=str, help='HR image path for evaluation')
    parser.add_argument('--onnx', action='store_true', help='Use ONNX model for inference')
    parser.add_argument('--simplify', action='store_true', help='Simplify ONNX model during export')
    parser.add_argument('--prune_ratio', type=float, default=0.4, help='Pruning ratio (default: 0.4)')
    parser.add_argument('--fine_tune', action='store_true', help='Fine-tune pruned model')
    parser.add_argument('--fine_tune_epochs', type=int, default=50, help='Fine-tune epochs')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID')
    parser.add_argument('--colormap', type=str, default='jet', help='Thermal colormap')
    parser.add_argument('--record', action='store_true', help='Record camera output')
    
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if args.mode == 'train':
        from src.train import train
        train(config)
    
    elif args.mode == 'infer':
        if not args.checkpoint:
            parser.error("--checkpoint is required for inference mode")
        if not args.input:
            parser.error("--input is required for inference mode")
        
        from src.inference import SuperResolutionInference
        
        inferencer = SuperResolutionInference(config, args.checkpoint, args.onnx)
        
        if args.batch:
            inferencer.inference_batch(args.input, args.output or 'results', args.hr)
        else:
            sr_img, inference_time, psnr, ssim = inferencer.inference_single(
                args.input,
                os.path.join(args.output, 'sr_result.png') if args.output else None,
                args.hr
            )
            
            print(f"\nInference completed!")
            print(f"Inference time: {inference_time:.4f}s")
            if psnr:
                print(f"PSNR: {psnr:.4f} dB")
            if ssim:
                print(f"SSIM: {ssim:.4f}")
            
            if args.output:
                print(f"Result saved to {os.path.join(args.output, 'sr_result.png')}")
    
    elif args.mode == 'export':
        if not args.checkpoint:
            parser.error("--checkpoint is required for export mode")
        
        from src.export_onnx import export_to_onnx
        
        output_path = args.output or 'models/rcan.onnx'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        export_to_onnx(
            config=config,
            checkpoint_path=args.checkpoint,
            output_path=output_path,
            simplify=args.simplify
        )
    
    elif args.mode == 'prune':
        if not args.checkpoint:
            parser.error("--checkpoint is required for pruning mode")
        
        from src.pruning import ChannelPruner, fine_tune_pruned_model
        from src.model import create_model
        from src.dataset import get_dataloaders
        from src.utils import load_checkpoint
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print("Loading original model...")
        original_model = create_model(config)
        original_model, _, _, original_psnr, _ = load_checkpoint(
            original_model, args.checkpoint, None, device
        )
        
        pruner = ChannelPruner(original_model, args.prune_ratio, device)
        original_params = pruner.get_num_parameters(original_model)
        
        train_loader, val_loader = get_dataloaders(config)
        
        print("Computing channel importance...")
        importance_dict = pruner.compute_channel_importance(train_loader)
        
        print("Creating pruned model...")
        pruned_model = pruner.prune_model(importance_dict)
        pruned_model = pruned_model.to(device)
        
        pruned_params = pruner.get_num_parameters(pruned_model)
        reduction = (1 - pruned_params / original_params) * 100
        
        print(f"Original params: {original_params:,}")
        print(f"Pruned params: {pruned_params:,}")
        print(f"Reduction: {reduction:.2f}%")
        
        if args.fine_tune:
            print(f"\nFine-tuning for {args.fine_tune_epochs} epochs...")
            pruned_model, best_psnr = fine_tune_pruned_model(
                pruned_model, train_loader, val_loader, config, device, args.fine_tune_epochs
            )
            print(f"PSNR drop: {original_psnr - best_psnr:.4f} dB")
        
        output_path = args.output or 'models/pruned_model.pth'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        torch.save({
            'model_state_dict': pruned_model.state_dict(),
            'pruned_params': pruned_params,
            'original_params': original_params,
            'reduction': reduction,
        }, output_path)
        print(f"Pruned model saved to {output_path}")
    
    elif args.mode == 'camera':
        if not args.checkpoint:
            parser.error("--checkpoint is required for camera mode")
        
        from src.realtime import run_realtime_inference
        import torch
        
        run_realtime_inference(
            config=config,
            checkpoint_path=args.checkpoint,
            camera_id=args.camera,
            colormap=args.colormap,
            use_onnx=args.onnx,
            record_video=args.record,
            output_path=args.output or 'results/camera_output.mp4'
        )
    
    elif args.mode == 'video':
        if not args.checkpoint:
            parser.error("--checkpoint is required for video mode")
        if not args.input:
            parser.error("--input is required for video mode")
        
        from src.realtime import process_video_file
        import torch
        
        process_video_file(
            config=config,
            checkpoint_path=args.checkpoint,
            input_path=args.input,
            output_path=args.output or 'results/sr_video.mp4',
            colormap=args.colormap,
            use_onnx=args.onnx
        )
    
    elif args.mode == 'heatmap':
        if not args.input:
            parser.error("--input is required for heatmap mode")
        
        import cv2
        from src.thermal_enhance import ThermalEnhancer
        
        enhancer = ThermalEnhancer(args.colormap)
        img = cv2.imread(args.input, cv2.IMREAD_GRAYSCALE)
        
        heatmap = enhancer.enhance(img, enhance_contrast=True, show_temperature_scale=True)
        
        output_path = args.output or 'results/heatmap.png'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, heatmap)
        print(f"Heatmap saved to {output_path}")


if __name__ == '__main__':
    import torch
    main()
