import os
import sys
import argparse
from pathlib import Path
import yaml
from ultralytics import YOLO
import torch

sys.path.append(str(Path(__file__).parent))
from image_enhancer import ImageEnhancer


def parse_args():
    parser = argparse.ArgumentParser(description='Train YOLOv8 for X-ray defect detection')
    parser.add_argument('--data', type=str, default='../configs/dataset.yaml', help='dataset config path')
    parser.add_argument('--weights', type=str, default='yolov8n.pt', help='initial weights path')
    parser.add_argument('--epochs', type=int, default=100, help='number of epochs')
    parser.add_argument('--imgsz', type=int, default=640, help='image size')
    parser.add_argument('--batch', type=int, default=16, help='batch size')
    parser.add_argument('--device', type=str, default='0', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--project', type=str, default='../models', help='save to project/name')
    parser.add_argument('--name', type=str, default='xray_defect', help='save to project/name')
    parser.add_argument('--hyp', type=str, default='../configs/hyp.yaml', help='hyperparameters path')
    parser.add_argument('--optimizer', type=str, default='auto', help='optimizer')
    parser.add_argument('--lr0', type=float, default=0.01, help='initial learning rate')
    parser.add_argument('--lrf', type=float, default=0.01, help='final learning rate')
    parser.add_argument('--patience', type=int, default=50, help='early stopping patience')
    parser.add_argument('--cos_lr', action='store_true', help='use cosine LR scheduler')
    parser.add_argument('--close_mosaic', type=int, default=10, help='close mosaic augmentation last N epochs')
    parser.add_argument('--use_pretrained', action='store_true', help='use pretrained weights')
    parser.add_argument('--resume', action='store_true', help='resume training')
    parser.add_argument('--half', action='store_true', help='use half precision training')
    return parser.parse_args()


def check_cuda():
    if torch.cuda.is_available():
        print(f"CUDA is available! Device count: {torch.cuda.device_count()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")
        return True
    else:
        print("CUDA is not available. Using CPU.")
        return False


def load_hyperparameters(hyp_path):
    if os.path.exists(hyp_path):
        with open(hyp_path, 'r') as f:
            hyp = yaml.safe_load(f)
        print(f"Loaded hyperparameters from {hyp_path}")
        return hyp
    else:
        print(f"Warning: Hyperparameter file {hyp_path} not found. Using defaults.")
        return {}


def main():
    args = parse_args()
    
    os.chdir(Path(__file__).parent)
    
    check_cuda()
    
    hyp = load_hyperparameters(args.hyp)
    
    model_path = args.weights
    if not os.path.exists(model_path) and args.weights.startswith('yolov8'):
        print(f"Downloading pretrained weights: {model_path}")
    
    model = YOLO(model_path)
    
    if args.use_pretrained and not args.weights.startswith('yolov8'):
        print(f"Loading pretrained weights from: {args.weights}")
        model = YOLO(args.weights)
    
    if args.resume:
        last_weights = os.path.join(args.project, args.name, 'weights', 'last.pt')
        if os.path.exists(last_weights):
            print(f"Resuming training from: {last_weights}")
            model = YOLO(last_weights)
        else:
            print(f"Warning: No checkpoint found at {last_weights}. Starting from scratch.")
    
    train_kwargs = {
        'data': args.data,
        'epochs': args.epochs,
        'imgsz': args.imgsz,
        'batch': args.batch,
        'device': args.device,
        'project': args.project,
        'name': args.name,
        'optimizer': args.optimizer,
        'lr0': args.lr0,
        'lrf': args.lrf,
        'patience': args.patience,
        'cos_lr': args.cos_lr,
        'close_mosaic': args.close_mosaic,
        'resume': args.resume,
        'half': args.half,
        'exist_ok': True,
        'save': True,
        'save_period': 10,
        'plots': True,
        'verbose': True,
        'seed': 42,
        'deterministic': True,
        'workers': 8,
        'multi_scale': False,
        'overlap_mask': True,
        'mask_ratio': 4,
        'dropout': 0.0,
        'val': True,
        'split': 'val',
        'save_json': False,
        'save_hybrid': False,
        'conf': 0.001,
        'iou': 0.7,
        'max_det': 300,
        'half': args.half,
        'dnn': False,
        'plots': True,
        'rect': False,
        'criterion': None,
    }
    
    train_kwargs.update(hyp)
    
    print("\n" + "=" * 50)
    print("Starting Training...")
    print("=" * 50)
    print(f"Dataset: {args.data}")
    print(f"Model: {model_path}")
    print(f"Epochs: {args.epochs}")
    print(f"Image size: {args.imgsz}")
    print(f"Batch size: {args.batch}")
    print(f"Device: {args.device}")
    print(f"Output directory: {os.path.join(args.project, args.name)}")
    print("=" * 50 + "\n")
    
    results = model.train(**train_kwargs)
    
    print("\n" + "=" * 50)
    print("Training Complete!")
    print("=" * 50)
    print(f"Best model saved at: {os.path.join(args.project, args.name, 'weights', 'best.pt')}")
    print(f"Last model saved at: {os.path.join(args.project, args.name, 'weights', 'last.pt')}")
    print("\nResults:")
    for key, value in results.results_dict.items():
        print(f"  {key}: {value}")
    print("=" * 50 + "\n")
    
    return model


if __name__ == '__main__':
    main()
