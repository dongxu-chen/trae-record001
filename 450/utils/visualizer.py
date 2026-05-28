import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Dict, List, Optional, Tuple
import cv2


class Visualizer:
    def __init__(self, figsize: Tuple[int, int] = (15, 10), dpi: int = 100):
        self.figsize = figsize
        self.dpi = dpi
        plt.style.use('seaborn-v0_8-whitegrid')
    
    def visualize_results(
        self,
        results: Dict[str, np.ndarray],
        save_path: Optional[str] = None,
        show: bool = False,
        title: Optional[str] = None
    ):
        images = []
        labels = []
        
        for key in ['input', 'transmission', 'reflection', 'alpha']:
            if key in results and results[key] is not None:
                images.append(results[key])
                labels.append(key.capitalize())
        
        num_images = len(images)
        cols = min(4, num_images)
        rows = (num_images + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=self.figsize, dpi=self.dpi)
        if rows == 1:
            axes = axes.reshape(1, -1)
        
        for i, (img, label) in enumerate(zip(images, labels)):
            row = i // cols
            col = i % cols
            ax = axes[row, col]
            
            if label.lower() == 'alpha' and len(img.shape) == 2:
                ax.imshow(img, cmap='jet', vmin=0, vmax=255)
            else:
                if len(img.shape) == 3:
                    ax.imshow(img)
                else:
                    ax.imshow(img, cmap='gray')
            
            ax.set_title(label, fontsize=12, fontweight='bold')
            ax.axis('off')
        
        for i in range(num_images, rows * cols):
            row = i // cols
            col = i % cols
            axes[row, col].axis('off')
        
        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight', dpi=self.dpi)
            print(f"Visualization saved to {save_path}")
        
        if show:
            plt.show()
        
        plt.close()
    
    def visualize_comparison(
        self,
        input_img: np.ndarray,
        restored_img: np.ndarray,
        ground_truth: Optional[np.ndarray] = None,
        reflection: Optional[np.ndarray] = None,
        metrics: Optional[Dict[str, float]] = None,
        save_path: Optional[str] = None,
        show: bool = False
    ):
        images = [input_img, restored_img]
        labels = ['Input Image', 'Restored (Transmission)']
        
        if ground_truth is not None:
            images.append(ground_truth)
            labels.append('Ground Truth')
        
        if reflection is not None:
            images.append(reflection)
            labels.append('Estimated Reflection')
        
        num_images = len(images)
        
        if metrics is not None:
            fig = plt.figure(figsize=(4 * num_images, 8), dpi=self.dpi)
            gs = gridspec.GridSpec(2, num_images, height_ratios=[4, 1], hspace=0.15)
            
            axes = []
            for i in range(num_images):
                ax = fig.add_subplot(gs[0, i])
                axes.append(ax)
            
            ax_metrics = fig.add_subplot(gs[1, :])
        else:
            fig, axes = plt.subplots(1, num_images, figsize=(4 * num_images, 5), dpi=self.dpi)
            if num_images == 1:
                axes = [axes]
        
        for i, (img, label) in enumerate(zip(images, labels)):
            ax = axes[i]
            ax.imshow(img)
            ax.set_title(label, fontsize=12, fontweight='bold')
            ax.axis('off')
            
            if ground_truth is not None and i == 1 and metrics is not None:
                psnr = metrics.get('psnr', 0)
                ssim = metrics.get('ssim', 0)
                ax.set_xlabel(f'PSNR: {psnr:.2f} dB | SSIM: {ssim:.4f}',
                            fontsize=10, fontweight='bold')
        
        if metrics is not None and 'ax_metrics' in locals():
            metric_names = list(metrics.keys())
            metric_values = list(metrics.values())
            
            ax_metrics.bar(range(len(metric_names)), metric_values, color='steelblue', alpha=0.7)
            ax_metrics.set_xticks(range(len(metric_names)))
            ax_metrics.set_xticklabels(metric_names, rotation=45, ha='right', fontsize=9)
            ax_metrics.set_title('Quality Metrics', fontsize=11, fontweight='bold')
            ax_metrics.grid(axis='y', alpha=0.3)
            
            for i, v in enumerate(metric_values):
                ax_metrics.text(i, v + max(metric_values) * 0.01, f'{v:.2f}',
                               ha='center', fontsize=8)
        
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight', dpi=self.dpi)
        
        if show:
            plt.show()
        
        plt.close()
    
    def plot_metrics_comparison(
        self,
        metrics_list: List[Dict[str, float]],
        labels: List[str],
        save_path: Optional[str] = None,
        show: bool = False,
        title: str = "Metrics Comparison"
    ):
        metric_keys = metrics_list[0].keys()
        
        fig, axes = plt.subplots(1, len(metric_keys), figsize=(4 * len(metric_keys), 5), dpi=self.dpi)
        if len(metric_keys) == 1:
            axes = [axes]
        
        for ax, metric in zip(axes, metric_keys):
            values = [m[metric] for m in metrics_list]
            bars = ax.bar(labels, values, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'][:len(labels)], alpha=0.8)
            
            ax.set_title(metric.upper(), fontsize=12, fontweight='bold')
            ax.grid(axis='y', alpha=0.3)
            
            for bar, val in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(values) * 0.01,
                       f'{val:.2f}', ha='center', va='bottom', fontsize=9)
        
        fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight', dpi=self.dpi)
        
        if show:
            plt.show()
        
        plt.close()
    
    def plot_training_curves(
        self,
        train_losses: List[float],
        val_losses: List[float],
        save_path: Optional[str] = None,
        show: bool = False
    ):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=self.dpi)
        
        epochs = range(1, len(train_losses) + 1)
        
        ax1.plot(epochs, train_losses, 'b-', label='Training Loss', linewidth=2)
        ax1.plot(epochs, val_losses, 'r-', label='Validation Loss', linewidth=2)
        ax1.set_xlabel('Epoch', fontsize=12)
        ax1.set_ylabel('Loss', fontsize=12)
        ax1.set_title('Training and Validation Loss', fontsize=13, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(alpha=0.3)
        
        if len(train_losses) > 5:
            ax2.plot(epochs[5:], train_losses[5:], 'b-', label='Training Loss', linewidth=2)
            ax2.plot(epochs[5:], val_losses[5:], 'r-', label='Validation Loss', linewidth=2)
            ax2.set_xlabel('Epoch', fontsize=12)
            ax2.set_ylabel('Loss', fontsize=12)
            ax2.set_title('Loss (Epochs 5+)', fontsize=13, fontweight='bold')
            ax2.legend(fontsize=10)
            ax2.grid(alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight', dpi=self.dpi)
        
        if show:
            plt.show()
        
        plt.close()
    
    def create_mosaic(
        self,
        images: List[np.ndarray],
        rows: int,
        cols: int,
        titles: Optional[List[str]] = None,
        save_path: Optional[str] = None,
        show: bool = False
    ):
        fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows), dpi=self.dpi)
        if rows == 1:
            axes = axes.reshape(1, -1)
        
        for i in range(rows * cols):
            row = i // cols
            col = i % cols
            ax = axes[row, col]
            
            if i < len(images):
                img = images[i]
                if len(img.shape) == 3:
                    ax.imshow(img)
                else:
                    ax.imshow(img, cmap='gray')
                
                if titles and i < len(titles):
                    ax.set_title(titles[i], fontsize=10, fontweight='bold')
            ax.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches='tight', dpi=self.dpi)
        
        if show:
            plt.show()
        
        plt.close()
