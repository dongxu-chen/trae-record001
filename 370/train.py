"""
训练模块
训练U-Net变化检测模型
支持加权交叉熵损失、类别频率统计等
"""

import os
import time
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import confusion_matrix, cohen_kappa_score
from collections import Counter
from tqdm import tqdm

from models.unet import UNet, ChangeDetectionLoss
from data_loader import ChangeDetectionDataset
from config import MODEL_CONFIG, TRAIN_CONFIG, CHECKPOINT_DIR, CLASS_NAMES


def compute_class_weights_from_dataset(dataset, num_classes):
    print("计算类别权重...")
    class_counts = Counter()

    for i in tqdm(range(min(len(dataset), 1000)), desc='统计类别频率'):
        _, _, label = dataset[i]
        if isinstance(label, torch.Tensor):
            label = label.numpy()
        unique, counts = np.unique(label, return_counts=True)
        for u, c in zip(unique, counts):
            class_counts[int(u)] += c

    total = sum(class_counts.values())
    weights = np.ones(num_classes)

    if total > 0:
        for c in range(num_classes):
            if c in class_counts and class_counts[c] > 0:
                weights[c] = total / (num_classes * class_counts[c])
            else:
                weights[c] = 10.0

        weights = np.clip(weights, 0.1, 10.0)
        weights = weights / weights.sum() * num_classes

    print("类别权重:")
    for i, name in enumerate(CLASS_NAMES[:num_classes]):
        count = class_counts.get(i, 0)
        print(f"  {name}: 权重={weights[i]:.3f}, 样本数={count}")

    return torch.tensor(weights, dtype=torch.float32), class_counts


def train(model, train_loader, val_loader, criterion, optimizer, scheduler, num_epochs, device):
    best_val_loss = float('inf')
    train_losses = []
    val_losses = []
    train_ious = []
    val_ious = []

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        train_iou = 0.0
        num_batches = 0

        pbar = tqdm(train_loader, desc=f'Epoch {epoch + 1}/{num_epochs} [Train]')
        for img1, img2, labels in pbar:
            img1, img2, labels = img1.to(device), img2.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(img1, img2)
            loss = criterion(outputs, labels)
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

            optimizer.step()

            running_loss += loss.item()
            preds = torch.argmax(outputs, dim=1)
            iou = compute_batch_iou(preds, labels, MODEL_CONFIG['out_channels'])
            train_iou += iou
            num_batches += 1

            pbar.set_postfix({'loss': f'{loss.item():.4f}', 'iou': f'{iou:.4f}'})

        avg_train_loss = running_loss / num_batches
        avg_train_iou = train_iou / num_batches
        train_losses.append(avg_train_loss)
        train_ious.append(avg_train_iou)

        if val_loader is not None:
            val_loss, val_iou = validate(model, val_loader, criterion, device)
            val_losses.append(val_loss)
            val_ious.append(val_iou)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                save_checkpoint(model, optimizer, epoch, val_loss, 'best_model.pth')

            print(f'Epoch {epoch + 1}/{num_epochs} - '
                  f'Train Loss: {avg_train_loss:.4f}, Train IoU: {avg_train_iou:.4f}, '
                  f'Val Loss: {val_loss:.4f}, Val IoU: {val_iou:.4f}')
        else:
            print(f'Epoch {epoch + 1}/{num_epochs} - '
                  f'Train Loss: {avg_train_loss:.4f}, Train IoU: {avg_train_iou:.4f}')
            save_checkpoint(model, optimizer, epoch, avg_train_loss, 'best_model.pth')

        if scheduler is not None:
            scheduler.step()

        class_weights = criterion.get_class_weights()
        if class_weights is not None and (epoch + 1) % 10 == 0:
            print(f"  当前类别权重: {class_weights}")

    save_checkpoint(model, optimizer, num_epochs - 1, train_losses[-1], 'final_model.pth')

    return {
        'train_losses': train_losses,
        'val_losses': val_losses,
        'train_ious': train_ious,
        'val_ious': val_ious
    }


def validate(model, val_loader, criterion, device):
    model.eval()
    running_loss = 0.0
    total_iou = 0.0
    num_batches = 0

    with torch.no_grad():
        for img1, img2, labels in tqdm(val_loader, desc='Validation'):
            img1, img2, labels = img1.to(device), img2.to(device), labels.to(device)
            outputs = model(img1, img2)
            loss = criterion(outputs, labels)
            running_loss += loss.item()

            preds = torch.argmax(outputs, dim=1)
            iou = compute_batch_iou(preds, labels, MODEL_CONFIG['out_channels'])
            total_iou += iou
            num_batches += 1

    return running_loss / num_batches, total_iou / num_batches


def compute_batch_iou(preds, labels, num_classes):
    ious = []
    for cls in range(num_classes):
        pred_mask = (preds == cls)
        label_mask = (labels == cls)
        intersection = (pred_mask & label_mask).sum().float()
        union = (pred_mask | label_mask).sum().float()
        if union > 0:
            ious.append((intersection / union).item())
    return np.mean(ious) if ious else 0.0


def save_checkpoint(model, optimizer, epoch, loss, filename):
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }
    path = os.path.join(CHECKPOINT_DIR, filename)
    torch.save(checkpoint, path)
    print(f'Checkpoint saved: {path}')


def load_checkpoint(model, optimizer, filename, device):
    path = os.path.join(CHECKPOINT_DIR, filename)
    if os.path.exists(path):
        checkpoint = torch.load(path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        if optimizer:
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        print(f'Checkpoint loaded: {path}')
        return model, optimizer, checkpoint['epoch']
    return model, optimizer, 0


def train_main(image1_path, image2_path, label_path, use_registration=False):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Using device: {device}')

    if use_registration:
        try:
            from registration import register_image_pair
            print("执行图像配准...")
            registered_img2_path = image2_path.replace('.tif', '_registered.tif')
            _, reg_status = register_image_pair(
                image1_path, image2_path,
                output_path=registered_img2_path,
                method='SIFT'
            )
            if reg_status.get('status') == 'success':
                image2_path = registered_img2_path
                print(f"配准成功，使用配准后影像: {registered_img2_path}")
            else:
                print(f"配准失败: {reg_status.get('reason', 'unknown')}")
        except Exception as e:
            print(f"配准异常: {e}")

    dataset = ChangeDetectionDataset(
        image1_path, image2_path, label_path,
        patch_size=TRAIN_CONFIG['patch_size'],
        stride=TRAIN_CONFIG['stride']
    )

    train_size = int(len(dataset) * TRAIN_CONFIG['train_ratio'])
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(
        train_dataset,
        batch_size=TRAIN_CONFIG['batch_size'],
        shuffle=True,
        num_workers=TRAIN_CONFIG['num_workers']
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=TRAIN_CONFIG['batch_size'],
        shuffle=False,
        num_workers=TRAIN_CONFIG['num_workers']
    )

    model = UNet(
        in_channels=MODEL_CONFIG['in_channels'],
        out_channels=MODEL_CONFIG['out_channels'],
        bilinear=MODEL_CONFIG['bilinear']
    ).to(device)

    num_classes = MODEL_CONFIG['out_channels']

    class_weights, _ = compute_class_weights_from_dataset(dataset, num_classes)

    criterion = ChangeDetectionLoss(
        num_classes=num_classes,
        class_weights=class_weights,
        use_focal=True,
        use_tversky=True,
        wce_weight=1.0,
        dice_weight=0.5,
        focal_weight=0.3,
        tversky_weight=0.3,
        focal_alpha=0.25,
        focal_gamma=2.0,
        tversky_alpha=0.3,
        tversky_beta=0.7,
    )

    optimizer = optim.AdamW(
        model.parameters(),
        lr=TRAIN_CONFIG['learning_rate'],
        weight_decay=TRAIN_CONFIG['weight_decay']
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=TRAIN_CONFIG['num_epochs'],
        eta_min=1e-6
    )

    print(f'Training samples: {len(train_dataset)}, Validation samples: {len(val_dataset)}')

    history = train(
        model, train_loader, val_loader,
        criterion, optimizer, scheduler,
        TRAIN_CONFIG['num_epochs'], device
    )

    return model, history
