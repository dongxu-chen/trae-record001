import sys
sys.path.insert(0, '.')

import torch
import torch.nn as nn
import numpy as np
from cd_tool.models import UNet, DeepLabV3Plus
from cd_tool.utils import (
    DifferenceCalculator, ChangeSegmenter, Evaluator, PerClassEvaluator,
    MixedPrecisionTrainer, DiceLoss, FocalLoss, CombinedLoss
)
from cd_tool.data import ChangeDetectionDataset, MaskedNormalize, ImagePairLoader, get_transforms


def example1_masked_normalization():
    print("=" * 80)
    print("EXAMPLE 1: Masked Normalization (with Invalid Pixels)")
    print("=" * 80)
    
    dummy_image = torch.randn(3, 256, 256) * 2 + 10
    dummy_image[:, :20, :20] = 0
    
    valid_mask = (dummy_image != 0).any(dim=0, keepdim=True).float()
    
    normalizer = MaskedNormalize(use_masked_stats=True)
    normalized, mask = normalizer(dummy_image, valid_mask)
    
    print(f"Original image range: [{dummy_image.min():.2f}, {dummy_image.max():.2f}]")
    print(f"Normalized image range: [{normalized.min():.2f}, {normalized.max():.2f}]")
    print(f"Valid mask shape: {mask.shape}")
    print(f"Valid pixels: {mask.sum()} / {mask.numel()} ({mask.sum()/mask.numel()*100:.1f}%)")
    print()


def example2_attention_enhanced_unet():
    print("=" * 80)
    print("EXAMPLE 2: Attention-Enhanced UNet")
    print("=" * 80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    model = UNet(
        n_channels=6,
        n_classes=2,
        use_attention=True,
        use_attention_gate=True,
        use_boundary_attention=True
    ).to(device)
    
    x = torch.randn(2, 6, 256, 256).to(device)
    
    with torch.no_grad():
        output, boundary_map = model(x, return_boundary=True)
    
    print(f"UNet with attention")
    print(f"  - CBAM attention in encoder/decoder: Enabled")
    print(f"  - Attention gates in decoder: Enabled")
    print(f"  - Boundary attention: Enabled")
    print(f"Output shape: {output.shape}")
    print(f"Boundary map shape: {boundary_map.shape}")
    print()


def example3_mixed_precision_training():
    print("=" * 80)
    print("EXAMPLE 3: Mixed Precision Training with Gradient Accumulation")
    print("=" * 80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = UNet(n_channels=6, n_classes=1, use_attention=True).to(device)
    
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)
    
    trainer = MixedPrecisionTrainer(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        use_amp=True,
        gradient_accumulation_steps=4,
        max_grad_norm=1.0,
        boundary_loss_weight=0.1,
        num_classes=1
    )
    
    print(f"Trainer configured:")
    print(f"  - Mixed Precision (AMP): {'Enabled' if trainer.use_amp else 'Disabled'}")
    print(f"  - Gradient accumulation steps: {trainer.gradient_accumulation_steps}")
    print(f"  - Gradient clipping: {trainer.max_grad_norm}")
    print(f"  - Boundary loss weight: {trainer.boundary_loss_weight}")
    
    print("\nRunning synthetic training epoch...")
    num_batches = 10
    synthetic_data = []
    for _ in range(num_batches):
        img1 = torch.randn(2, 3, 256, 256)
        img2 = torch.randn(2, 3, 256, 256)
        target = torch.randint(0, 2, (2, 1, 256, 256)).float()
        synthetic_data.append((img1, img2, target))
    
    metrics = trainer.train_epoch(
        dataloader=synthetic_data,
        epoch=1,
        return_boundary=True
    )
    
    print(f"Training epoch 1 completed:")
    print(f"  - Loss: {metrics['loss']:.4f}")
    if 'boundary_loss' in metrics:
        print(f"  - Boundary loss: {metrics['boundary_loss']:.4f}")
    print()


def example4_loss_functions():
    print("=" * 80)
    print("EXAMPLE 4: Loss Functions (Dice, Focal, Combined)")
    print("=" * 80)
    
    inputs = torch.randn(4, 1, 256, 256)
    targets = torch.randint(0, 2, (4, 1, 256, 256)).float()
    
    dice_loss = DiceLoss(smooth=1.0)
    focal_loss = FocalLoss(alpha=0.8, gamma=2.0)
    combined_loss = CombinedLoss(bce_weight=0.5, dice_weight=0.5, focal_weight=0.0)
    
    print(f"Dice Loss: {dice_loss(inputs, targets).item():.4f}")
    print(f"Focal Loss: {focal_loss(inputs, targets).item():.4f}")
    print(f"Combined Loss: {combined_loss(inputs, targets).item():.4f}")
    print()


def example5_per_class_evaluation():
    print("=" * 80)
    print("EXAMPLE 5: Per-Class IoU Evaluation with Poor Class Detection")
    print("=" * 80)
    
    num_classes = 5
    class_names = ['background', 'building', 'road', 'vegetation', 'water']
    
    evaluator = PerClassEvaluator(num_classes=num_classes, class_names=class_names)
    
    batch_size = 8
    for _ in range(10):
        pred = torch.randn(batch_size, num_classes, 128, 128)
        target = torch.randint(0, num_classes, (batch_size, 1, 128, 128))
        
        target[:, :, :20, :20] = 4
        target[:, :, 20:40, 20:40] = 1
        
        evaluator.add_batch(pred, target, image_ids=[f'img_{i}' for i in range(batch_size)])
    
    metrics = evaluator.get_class_metrics()
    
    print(f"Per-class evaluation results:")
    print(f"  mIoU: {metrics['mIoU']:.4f}")
    print(f"  mF1: {metrics['mF1']:.4f}")
    print(f"\n  Worst class: {metrics['worst_class_name']} (IoU: {metrics['worst_class_iou']:.4f})")
    
    print("\nPrinting detailed summary...")
    evaluator.print_summary()
    
    worst_images = evaluator.get_worst_images(top_k=5)
    print(f"\nTop 5 worst performing images:")
    for i, img_stats in enumerate(worst_images):
        print(f"  {i+1}. {img_stats['image_id']}: mIoU = {img_stats['mIoU']:.4f}, "
              f"Worst class: {class_names[img_stats['worst_class_idx']]}")
    print()


def example6_difference_calculation():
    print("=" * 80)
    print("EXAMPLE 6: Multiple Difference Calculation Methods")
    print("=" * 80)
    
    img1 = np.random.rand(256, 256, 3) * 255
    img2 = img1.copy()
    img2[50:100, 50:100] += 50
    img2[150:200, 150:200] -= 30
    
    methods = ['cva', 'diff', 'ratio', 'ndvi']
    results = {}
    
    for method in methods:
        calc = DifferenceCalculator(method=method)
        diff = calc.compute(img1, img2)
        results[method] = diff
        print(f"{method.upper()}: mean={diff.mean():.4f}, std={diff.std():.4f}")
    
    segmenter = ChangeSegmenter(threshold=0.5)
    mask = segmenter.otsu_threshold(results['cva'])
    clean_mask = segmenter.post_process(mask, min_area=100)
    
    print(f"\nChange detection result:")
    print(f"  Changed pixels: {clean_mask.sum()}")
    print(f"  Number of change regions: {len(segmenter.get_change_regions(clean_mask))}")
    print()


def example7_image_pair_loader():
    print("=" * 80)
    print("EXAMPLE 7: Image Pair Loader with Custom Transform")
    print("=" * 80)
    
    loader = ImagePairLoader(img_size=(256, 256))
    
    transform = get_transforms(
        train=True,
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
    
    print("ImagePairLoader configured:")
    print(f"  - Target size: {loader.img_size}")
    print(f"  - Supports masked normalization")
    print(f"  - Can compute dataset statistics")
    print()


def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "REMOTE SENSING CHANGE DETECTION TOOLKIT" + " " * 19 + "║")
    print("║" + " " * 25 + "v0.2.0 - Enhanced Edition" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    example1_masked_normalization()
    example2_attention_enhanced_unet()
    example3_mixed_precision_training()
    example4_loss_functions()
    example5_per_class_evaluation()
    example6_difference_calculation()
    example7_image_pair_loader()
    
    print("=" * 80)
    print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("\nNew features in v0.2.0:")
    print("  ✓ Masked normalization for invalid pixels")
    print("  ✓ Attention modules (CBAM, Spatial, Channel, Boundary, Gates)")
    print("  ✓ Mixed precision training (AMP)")
    print("  ✓ Gradient accumulation")
    print("  ✓ Per-class IoU evaluation")
    print("  ✓ Poor class and image detection")
    print("  ✓ Advanced loss functions (Dice, Focal, Combined)")
    print("\n")


if __name__ == "__main__":
    main()
