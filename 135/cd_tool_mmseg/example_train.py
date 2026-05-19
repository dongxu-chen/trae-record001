#!/usr/bin/env python
"""
基于 MMSegmentation 风格的变化检测训练示例
"""

import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
from PIL import Image

# 导入新框架模块
from cd_tool_mmseg.models.builder import build_segmentor, build_loss
from cd_tool_mmseg.engine.trainer import Trainer


class SimpleChangeDataset(Dataset):
    """简单的变化检测数据集示例"""
    
    def __init__(self, img_dir1, img_dir2, mask_dir, img_size=256, transform=None):
        self.img_dir1 = img_dir1
        self.img_dir2 = img_dir2
        self.mask_dir = mask_dir
        self.img_size = img_size
        self.transform = transform
        
        self.images = [f for f in os.listdir(img_dir1) if f.endswith(('.png', '.jpg'))]
        
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        filename = self.images[idx]
        
        img1 = Image.open(os.path.join(self.img_dir1, filename)).convert('RGB')
        img2 = Image.open(os.path.join(self.img_dir2, filename)).convert('RGB')
        mask = Image.open(os.path.join(self.mask_dir, filename)).convert('L')
        
        img1 = img1.resize((self.img_size, self.img_size), Image.BILINEAR)
        img2 = img2.resize((self.img_size, self.img_size), Image.BILINEAR)
        mask = mask.resize((self.img_size, self.img_size), Image.NEAREST)
        
        img1 = np.array(img1, dtype=np.float32).transpose(2, 0, 1) / 255.0
        img2 = np.array(img2, dtype=np.float32).transpose(2, 0, 1) / 255.0
        mask = np.array(mask, dtype=np.float32) / 255.0
        
        img1 = torch.from_numpy(img1)
        img2 = torch.from_numpy(img2)
        mask = torch.from_numpy(mask).unsqueeze(0)
        
        return {'img1': img1, 'img2': img2, 'mask': mask, 'filename': filename}


def iou_metric(pred, target):
    """计算IoU"""
    intersection = (pred & target).float().sum((1, 2, 3))
    union = (pred | target).float().sum((1, 2, 3))
    iou = (intersection + 1e-6) / (union + 1e-6)
    return iou.mean().item()


def f1_metric(pred, target):
    """计算F1分数"""
    pred = pred.float()
    target = target.float()
    
    tp = (pred * target).sum((1, 2, 3))
    fp = (pred * (1 - target)).sum((1, 2, 3))
    fn = ((1 - pred) * target).sum((1, 2, 3))
    
    precision = (tp + 1e-6) / (tp + fp + 1e-6)
    recall = (tp + 1e-6) / (tp + fn + 1e-6)
    f1 = 2 * precision * recall / (precision + recall + 1e-6)
    
    return f1.mean().item()


def main():
    # 配置
    config = {
        'model': {
            'type': 'ChangeDetector',
            'backbone': {
                'type': 'UNetBackbone',
                'in_channels': 3,
                'base_channels': 64,
                'num_stages': 4,
                'out_indices': (0, 1, 2, 3),
            },
            'decode_head': {
                'type': 'FCNHead',
                'in_channels': 192,
                'channels': 64,
                'num_classes': 1,
                'dropout_ratio': 0.1,
            },
            'loss_decode': {
                'type': 'DiceLoss',
                'smooth': 1.0,
                'exponent': 2,
                'reduction': 'mean',
                'loss_weight': 1.0,
            },
        },
        'optimizer': {
            'type': 'AdamW',
            'lr': 0.0001,
            'weight_decay': 0.0001,
        },
        'training': {
            'batch_size': 4,
            'num_epochs': 50,
            'use_amp': True,
            'grad_accum_steps': 2,
            'max_grad_norm': 1.0,
        },
        'data': {
            'img_size': 256,
            'num_workers': 4,
        },
    }
    
    # 构建模型
    model = build_segmentor(config['model'])
    
    # 构建损失函数
    loss_cfg = config['model']['loss_decode'].copy()
    loss_fn = build_loss(loss_cfg)
    
    # 优化器
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config['optimizer']['lr'],
        weight_decay=config['optimizer']['weight_decay'],
    )
    
    # 学习率调度器
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config['training']['num_epochs'],
        eta_min=1e-6,
    )
    
    # 数据集（这里使用模拟数据，实际使用时替换为真实数据路径）
    print("创建数据集...")
    
    # 创建模拟数据集目录
    os.makedirs('demo_data/train/img1', exist_ok=True)
    os.makedirs('demo_data/train/img2', exist_ok=True)
    os.makedirs('demo_data/train/mask', exist_ok=True)
    os.makedirs('demo_data/val/img1', exist_ok=True)
    os.makedirs('demo_data/val/img2', exist_ok=True)
    os.makedirs('demo_data/val/mask', exist_ok=True)
    
    # 生成模拟数据
    print("生成模拟数据...")
    for i in range(100):
        img1 = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        img2 = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        mask = np.random.randint(0, 2, (256, 256), dtype=np.uint8) * 255
        
        Image.fromarray(img1).save(f'demo_data/train/img1/{i:04d}.png')
        Image.fromarray(img2).save(f'demo_data/train/img2/{i:04d}.png')
        Image.fromarray(mask).save(f'demo_data/train/mask/{i:04d}.png')
    
    for i in range(20):
        img1 = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        img2 = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        mask = np.random.randint(0, 2, (256, 256), dtype=np.uint8) * 255
        
        Image.fromarray(img1).save(f'demo_data/val/img1/{i:04d}.png')
        Image.fromarray(img2).save(f'demo_data/val/img2/{i:04d}.png')
        Image.fromarray(mask).save(f'demo_data/val/mask/{i:04d}.png')
    
    # 创建数据集
    train_dataset = SimpleChangeDataset(
        'demo_data/train/img1',
        'demo_data/train/img2',
        'demo_data/train/mask',
        img_size=config['data']['img_size'],
    )
    
    val_dataset = SimpleChangeDataset(
        'demo_data/val/img1',
        'demo_data/val/img2',
        'demo_data/val/mask',
        img_size=config['data']['img_size'],
    )
    
    # 创建数据加载器
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,
        num_workers=config['data']['num_workers'],
        pin_memory=True,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=config['data']['num_workers'],
        pin_memory=True,
    )
    
    # 创建训练器
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"使用设备: {device}")
    
    model = model.to(device)
    
    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        lr_scheduler=lr_scheduler,
        loss_fn=loss_fn,
        device=device,
        use_amp=config['training']['use_amp'],
        grad_accum_steps=config['training']['grad_accum_steps'],
        max_grad_norm=config['training']['max_grad_norm'],
        work_dir='./work_dirs/demo_experiment',
    )
    
    # 训练模型
    print("开始训练...")
    metrics = {
        'IoU': iou_metric,
        'F1': f1_metric,
    }
    
    trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=config['training']['num_epochs'],
        val_interval=5,
        save_interval=10,
        metrics=metrics,
    )
    
    print("训练完成！")


if __name__ == '__main__':
    main()
