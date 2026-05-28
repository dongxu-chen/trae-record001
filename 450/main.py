import argparse
import os
import sys
import cv2
import numpy as np

from config import Config
from core import ReflectionRemover, Evaluator
from utils import BatchProcessor, Visualizer
from data import get_data_loader, PolarizationProcessor


def parse_args():
    parser = argparse.ArgumentParser(description='Image Reflection Removal System')
    
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    infer_parser = subparsers.add_parser('infer', help='Inference on single image')
    infer_parser.add_argument('--input', '-i', type=str, required=True, help='Input image path')
    infer_parser.add_argument('--output', '-o', type=str, default='output', help='Output directory')
    infer_parser.add_argument('--model', '-m', type=str, default=None, help='Model checkpoint path')
    infer_parser.add_argument('--polarization', '-p', type=str, default=None, help='Polarization image path')
    infer_parser.add_argument('--ground-truth', '-gt', type=str, default=None, help='Ground truth image path')
    infer_parser.add_argument('--visualize', action='store_true', help='Generate visualization')
    
    batch_parser = subparsers.add_parser('batch', help='Batch processing')
    batch_parser.add_argument('--input-dir', type=str, required=True, help='Input directory')
    batch_parser.add_argument('--output-dir', type=str, default='output', help='Output directory')
    batch_parser.add_argument('--model', '-m', type=str, default=None, help='Model checkpoint path')
    batch_parser.add_argument('--polarization-dir', type=str, default=None, help='Polarization images directory')
    batch_parser.add_argument('--ground-truth-dir', type=str, default=None, help='Ground truth directory')
    batch_parser.add_argument('--save-all', action='store_true', help='Save all outputs (input, transmission, reflection, alpha)')
    
    train_parser = subparsers.add_parser('train', help='Train the model')
    train_parser.add_argument('--epochs', type=int, default=None, help='Number of epochs')
    train_parser.add_argument('--batch-size', type=int, default=None, help='Batch size')
    train_parser.add_argument('--lr', type=float, default=None, help='Learning rate')
    train_parser.add_argument('--resume', type=str, default=None, help='Resume from checkpoint')
    
    eval_parser = subparsers.add_parser('eval', help='Evaluate model performance')
    eval_parser.add_argument('--input-dir', type=str, required=True, help='Input directory')
    eval_parser.add_argument('--ground-truth-dir', type=str, required=True, help='Ground truth directory')
    eval_parser.add_argument('--model', '-m', type=str, default=None, help='Model checkpoint path')
    eval_parser.add_argument('--output-dir', type=str, default='output/eval', help='Output directory')
    
    vis_parser = subparsers.add_parser('vis', help='Visualize results')
    vis_parser.add_argument('--input', type=str, required=True, help='Input image')
    vis_parser.add_argument('--restored', type=str, required=True, help='Restored image')
    vis_parser.add_argument('--ground-truth', type=str, default=None, help='Ground truth image')
    vis_parser.add_argument('--output', type=str, default='output/vis.png', help='Output visualization path')
    
    return parser.parse_args()


def inference_mode(args, config):
    print(f"Running inference on: {args.input}")
    
    remover = ReflectionRemover(config, args.model)
    
    image = cv2.imread(args.input, cv2.IMREAD_COLOR)
    if image is None:
        print(f"Error: Could not load image {args.input}")
        sys.exit(1)
    
    pol_image = None
    if args.polarization and os.path.exists(args.polarization):
        pol_image = cv2.imread(args.polarization, cv2.IMREAD_COLOR)
        print("Using polarization information")
    
    results = remover.remove_reflection(image, pol_image)
    
    os.makedirs(args.output, exist_ok=True)
    basename = os.path.splitext(os.path.basename(args.input))[0]
    
    cv2.imwrite(
        os.path.join(args.output, f"{basename}_transmission.png"),
        cv2.cvtColor(results['transmission'], cv2.COLOR_RGB2BGR)
    )
    
    if args.visualize:
        visualizer = Visualizer()
        metrics = None
        
        if args.ground_truth and os.path.exists(args.ground_truth):
            gt = cv2.imread(args.ground_truth, cv2.IMREAD_COLOR)
            gt = cv2.cvtColor(gt, cv2.COLOR_BGR2RGB)
            evaluator = Evaluator(config)
            metrics = evaluator.evaluate(results['transmission'], gt, results['input'])
            evaluator.print_metrics(metrics)
        
        visualizer.visualize_comparison(
            results['input'],
            results['transmission'],
            ground_truth=cv2.cvtColor(cv2.imread(args.ground_truth, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB) if args.ground_truth else None,
            reflection=results['reflection'],
            metrics=metrics,
            save_path=os.path.join(args.output, f"{basename}_comparison.png"),
            show=False
        )
        
        visualizer.visualize_results(
            results,
            save_path=os.path.join(args.output, f"{basename}_all.png"),
            show=False,
            title="Reflection Separation Results"
        )
    
    print(f"Results saved to {args.output}")
    return results


def batch_mode(args, config):
    print(f"Batch processing: {args.input_dir}")
    
    config.inference.save_all_outputs = args.save_all
    
    processor = BatchProcessor(config, args.model)
    
    results = processor.process_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        polarization_dir=args.polarization_dir,
        ground_truth_dir=args.ground_truth_dir
    )
    
    print(f"\nProcessing complete!")
    print(f"Total processed: {results['total_processed']}")
    print(f"Total failed: {results['total_failed']}")
    
    if results['summary']:
        print("\n" + "="*50)
        print("Metrics Summary")
        print("="*50)
        for metric, stats in results['summary'].items():
            print(f"\n{metric.upper()}:")
            print(f"  Mean:   {stats['mean']:.4f}")
            print(f"  Std:    {stats['std']:.4f}")
            print(f"  Min:    {stats['min']:.4f}")
            print(f"  Max:    {stats['max']:.4f}")
            print(f"  Median: {stats['median']:.4f}")
        print("="*50)
    
    return results


def train_mode(args, config):
    print("Starting training...")
    
    if args.epochs:
        config.training.epochs = args.epochs
    if args.batch_size:
        config.training.batch_size = args.batch_size
    if args.lr:
        config.training.learning_rate = args.lr
    
    remover = ReflectionRemover(config, args.resume)
    
    train_loader = get_data_loader(
        image_dir=config.data.train_dir,
        transmission_dir=config.data.train_transmission_dir,
        reflection_dir=config.data.train_reflection_dir,
        batch_size=config.training.batch_size,
        shuffle=True,
        num_workers=config.training.num_workers,
        image_size=config.data.image_size,
        mode='train'
    )
    
    val_loader = get_data_loader(
        image_dir=config.data.val_dir,
        transmission_dir=config.data.val_transmission_dir,
        reflection_dir=config.data.val_reflection_dir,
        batch_size=config.training.batch_size,
        shuffle=False,
        num_workers=config.training.num_workers,
        image_size=config.data.image_size,
        mode='train'
    )
    
    print(f"Training samples: {len(train_loader.dataset)}")
    print(f"Validation samples: {len(val_loader.dataset)}")
    
    remover.train(train_loader, val_loader)
    
    print("Training complete!")


def eval_mode(args, config):
    print(f"Evaluating on: {args.input_dir}")
    
    processor = BatchProcessor(config, args.model)
    
    results = processor.process_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        ground_truth_dir=args.ground_truth_dir
    )
    
    if results['summary']:
        visualizer = Visualizer()
        
        metrics_list = [results['summary']]
        labels = ['Ours']
        
        visualizer.plot_metrics_comparison(
            metrics_list=[{k: v['mean'] for k, v in results['summary'].items()}],
            labels=labels,
            save_path=os.path.join(args.output_dir, 'metrics_comparison.png'),
            show=False,
            title="Evaluation Metrics"
        )
    
    print("Evaluation complete!")
    return results


def visualize_mode(args, config):
    print(f"Generating visualization: {args.input}")
    
    visualizer = Visualizer()
    
    input_img = cv2.cvtColor(cv2.imread(args.input, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    restored_img = cv2.cvtColor(cv2.imread(args.restored, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    
    ground_truth = None
    if args.ground_truth and os.path.exists(args.ground_truth):
        ground_truth = cv2.cvtColor(cv2.imread(args.ground_truth, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    
    metrics = None
    if ground_truth is not None:
        evaluator = Evaluator()
        metrics = evaluator.evaluate(restored_img, ground_truth, input_img)
        evaluator.print_metrics(metrics)
    
    visualizer.visualize_comparison(
        input_img,
        restored_img,
        ground_truth=ground_truth,
        metrics=metrics,
        save_path=args.output,
        show=False
    )
    
    print(f"Visualization saved to {args.output}")


def main():
    args = parse_args()
    config = Config()
    
    if args.mode == 'infer':
        inference_mode(args, config)
    elif args.mode == 'batch':
        batch_mode(args, config)
    elif args.mode == 'train':
        train_mode(args, config)
    elif args.mode == 'eval':
        eval_mode(args, config)
    elif args.mode == 'vis':
        visualize_mode(args, config)
    else:
        print("Please specify a mode: infer, batch, train, eval, or vis")
        print("Use --help for more information")


if __name__ == '__main__':
    main()
