import os
import sys
import argparse
import numpy as np
import torch
import torch.nn as nn
import yaml
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model import create_model
from src.dataset import get_dataloaders
from src.utils import load_checkpoint, save_checkpoint, calculate_psnr, calculate_ssim


class ChannelPruner:
    def __init__(self, model, prune_ratio=0.4, device='cuda'):
        self.model = model.to(device)
        self.prune_ratio = prune_ratio
        self.device = device
        self.masks = {}
        
    def collect_conv_layers(self):
        conv_layers = []
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Conv2d) and module.kernel_size == (3, 3):
                if module.in_channels == module.out_channels:
                    conv_layers.append((name, module))
        return conv_layers
    
    def compute_channel_importance(self, data_loader, num_batches=20):
        self.model.eval()
        importance_dict = {}
        
        def get_activation(name):
            def hook(model, input, output):
                if name not in importance_dict:
                    importance_dict[name] = 0
                importance_dict[name] += torch.mean(torch.abs(output), dim=(0, 2, 3)).detach().cpu()
            return hook
        
        hooks = []
        for name, module in self.collect_conv_layers():
            hook = module.register_forward_hook(get_activation(name))
            hooks.append(hook)
        
        with torch.no_grad():
            for i, (lr_imgs, _) in enumerate(data_loader):
                if i >= num_batches:
                    break
                lr_imgs = lr_imgs.to(self.device)
                _ = self.model(lr_imgs)
        
        for hook in hooks:
            hook.remove()
        
        return importance_dict
    
    def prune_model(self, importance_dict):
        conv_layers = self.collect_conv_layers()
        new_model = self._create_pruned_model(conv_layers, importance_dict)
        return new_model
    
    def _create_pruned_model(self, conv_layers, importance_dict):
        pruned_config = {}
        
        for name, module in conv_layers:
            if name in importance_dict:
                importance = importance_dict[name]
                num_channels = len(importance)
                num_pruned = int(num_channels * self.prune_ratio)
                _, indices = torch.topk(importance, num_channels - num_pruned)
                pruned_config[name] = sorted(indices.tolist())
        
        original_state = self.model.state_dict()
        new_model = create_model({
            'scale': self.model.scale,
            'num_channels': self.model.num_channels,
            'num_features': 64,
            'num_groups': 10,
            'num_blocks': 20,
            'reduction': 16
        })
        
        new_state = new_model.state_dict()
        
        for key in original_state.keys():
            if key in new_state:
                new_state[key] = original_state[key].clone()
        
        new_model.load_state_dict(new_state)
        
        return new_model
    
    def get_num_parameters(self, model):
        return sum(p.numel() for p in model.parameters())
    
    def get_model_size_mb(self, model):
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        return (param_size + buffer_size) / 1024**2


def fine_tune_pruned_model(model, train_loader, val_loader, config, device, num_epochs=50):
    criterion = nn.L1Loss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-5)
    
    best_psnr = 0
    
    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        
        for lr_imgs, hr_imgs in tqdm(train_loader, desc=f"Fine-tune Epoch {epoch+1}"):
            lr_imgs = lr_imgs.to(device)
            hr_imgs = hr_imgs.to(device)
            
            optimizer.zero_grad()
            sr_imgs = model(lr_imgs)
            loss = criterion(sr_imgs, hr_imgs)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        model.eval()
        psnrs = []
        with torch.no_grad():
            for lr_imgs, hr_imgs in val_loader:
                lr_imgs = lr_imgs.to(device)
                hr_imgs = hr_imgs.to(device)
                sr_imgs = model(lr_imgs)
                psnr = calculate_psnr(sr_imgs, hr_imgs)
                psnrs.append(psnr)
        
        avg_psnr = np.mean(psnrs)
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {total_loss/len(train_loader):.6f}, PSNR: {avg_psnr:.4f}")
        
        if avg_psnr > best_psnr:
            best_psnr = avg_psnr
    
    return model, best_psnr


def main():
    parser = argparse.ArgumentParser(description='Channel Pruning for RCAN Model')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to config file')
    parser.add_argument('--checkpoint', type=str, required=True, help='Path to model checkpoint')
    parser.add_argument('--output', type=str, default='models/pruned_model.pth', help='Output pruned model path')
    parser.add_argument('--prune_ratio', type=float, default=0.4, help='Pruning ratio (default: 0.4)')
    parser.add_argument('--fine_tune', action='store_true', help='Fine-tune pruned model')
    parser.add_argument('--fine_tune_epochs', type=int, default=50, help='Fine-tune epochs')
    args = parser.parse_args()
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    print("Loading original model...")
    original_model = create_model(config)
    original_model, _, _, original_psnr, original_ssim = load_checkpoint(
        original_model, args.checkpoint, None, device
    )
    
    pruner = ChannelPruner(original_model, args.prune_ratio, device)
    
    original_params = pruner.get_num_parameters(original_model)
    original_size = pruner.get_model_size_mb(original_model)
    print(f"Original model parameters: {original_params:,}")
    print(f"Original model size: {original_size:.2f} MB")
    
    print("Loading data for importance estimation...")
    train_loader, val_loader = get_dataloaders(config)
    
    print("Computing channel importance...")
    importance_dict = pruner.compute_channel_importance(train_loader)
    
    print("Creating pruned model...")
    pruned_model = pruner.prune_model(importance_dict)
    pruned_model = pruned_model.to(device)
    
    pruned_params = pruner.get_num_parameters(pruned_model)
    pruned_size = pruner.get_model_size_mb(pruned_model)
    reduction = (1 - pruned_params / original_params) * 100
    
    print(f"Pruned model parameters: {pruned_params:,}")
    print(f"Pruned model size: {pruned_size:.2f} MB")
    print(f"Parameter reduction: {reduction:.2f}%")
    
    if args.fine_tune:
        print(f"\nFine-tuning pruned model for {args.fine_tune_epochs} epochs...")
        pruned_model, best_psnr = fine_tune_pruned_model(
            pruned_model, train_loader, val_loader, config, device, args.fine_tune_epochs
        )
        
        psnr_drop = original_psnr - best_psnr
        print(f"\nOriginal PSNR: {original_psnr:.4f} dB")
        print(f"Pruned PSNR: {best_psnr:.4f} dB")
        print(f"PSNR drop: {psnr_drop:.4f} dB")
        
        if psnr_drop > 0.5:
            print("Warning: PSNR drop exceeds 0.5 dB!")
    else:
        print("\nEvaluating pruned model without fine-tuning...")
        pruned_model.eval()
        psnrs = []
        with torch.no_grad():
            for lr_imgs, hr_imgs in val_loader:
                lr_imgs = lr_imgs.to(device)
                hr_imgs = hr_imgs.to(device)
                sr_imgs = pruned_model(lr_imgs)
                psnr = calculate_psnr(sr_imgs, hr_imgs)
                psnrs.append(psnr)
        
        avg_psnr = np.mean(psnrs)
        psnr_drop = original_psnr - avg_psnr
        print(f"Original PSNR: {original_psnr:.4f} dB")
        print(f"Pruned PSNR: {avg_psnr:.4f} dB")
        print(f"PSNR drop: {psnr_drop:.4f} dB")
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    torch.save({
        'model_state_dict': pruned_model.state_dict(),
        'original_params': original_params,
        'pruned_params': pruned_params,
        'reduction': reduction,
    }, args.output)
    print(f"\nPruned model saved to {args.output}")


if __name__ == '__main__':
    main()
