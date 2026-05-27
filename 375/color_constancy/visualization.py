import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
import os
from pathlib import Path


def rgb_to_temperature(rgb):
    """
    Convert RGB illuminant to correlated color temperature (CCT) in Kelvin.
    
    Uses McCamy approximation.
    
    Args:
        rgb: RGB values [R, G, B] or (N, 3)
    
    Returns:
        cct: Color temperature in Kelvin, and duv: Distance from Planckian locus
    """
    rgb = np.asarray(rgb, dtype=np.float32)
    single = (rgb.ndim == 1)
    if single:
        rgb = rgb.reshape(1, 3)
    
    rgb_norm = rgb / (np.sum(rgb, axis=1, keepdims=True) + 1e-8)
    
    M_srgb_to_xyz = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ], dtype=np.float32)
    
    xyz = rgb_norm @ M_srgb_to_xyz.T
    
    sum_xyz = np.sum(xyz, axis=1, keepdims=True) + 1e-8
    x = xyz[:, 0] / sum_xyz[:, 0]
    y = xyz[:, 1] / sum_xyz[:, 0]
    
    n = (x - 0.3320) / (y - 0.1858 + 1e-8)
    
    cct = 449.0 * n ** 3 + 3525.0 * n ** 2 + 6823.3 * n + 5520.33
    
    cct = np.clip(cct, 1000, 25000)
    
    xc = -0.1173 * n ** 2 - 0.23893 * n + 0.10735 * n ** 2 - 0.02953
    duv = y - xc
    
    if single:
        return float(cct[0]), float(duv[0])
    return cct, duv


def temperature_to_rgb(cct):
    """
    Convert color temperature (Kelvin) to approximate RGB color.
    
    Args:
        cct: Color temperature in Kelvin (scalar or array)
    
    Returns:
        rgb: RGB values [R, G, B] normalized
    """
    cct = np.asarray(cct, dtype=np.float32)
    scalar = cct.ndim == 0
    if scalar:
        cct = cct.reshape(1)
    
    temp = cct / 100.0
    
    r = np.where(temp <= 66,
                   255.0,
                   329.698727446 * np.power(np.maximum(temp - 60, 1), -0.1332047592))
    
    g = np.where(temp <= 66,
                   99.4708025861 * np.log(np.maximum(temp, 1)) - 161.1195681661,
                   288.1221695283 * np.power(np.maximum(temp - 60, 1), -0.0755148492))
    
    b = np.where(temp <= 19,
                  0.0,
                  np.where(temp >= 66,
                           255.0,
                           138.5177312231 * np.log(np.maximum(temp - 10, 1)) - 305.0447927307))
    
    rgb = np.stack([r, g, b], axis=-1)
    rgb = np.clip(rgb, 0, 255)
    rgb = rgb / (np.max(rgb, axis=-1, keepdims=True) + 1e-8)
    rgb = rgb / (np.linalg.norm(rgb, axis=-1, keepdims=True) + 1e-8)
    
    if scalar:
        return rgb[0]
    return rgb


def create_color_temperature_bar():
    """
    Create a color temperature gradient bar image.
    
    Returns:
        bar: Gradient bar image (1, 1024, 3) uint8 in RGB
        temps: Array of corresponding temperatures
    """
    temps = np.linspace(2000, 12000, 1024, dtype=np.float32)
    colors = np.zeros((1, 1024, 3), dtype=np.uint8)
    
    for i, t in enumerate(temps):
        rgb = temperature_to_rgb(t)
        colors[0, i] = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    
    return colors, temps


def plot_illuminant_visualization(image, illuminant, save_path=None, 
                                   method_name='Unknown',
                                   original_image=None,
                                   corrected_image=None):
    """
    Visualize illuminant estimation result with color temperature display.
    
    Args:
        image: Input BGR image (H, W, 3)
        illuminant: Estimated illuminant [R, G, B] normalized
        save_path: Optional path to save figure
        method_name: Name of the estimation method
        original_image: Optional original image for comparison
        corrected_image: Optional corrected image for comparison
    
    Returns:
        fig, axes: Figure and axes
    """
    cct, duv = rgb_to_temperature(illuminant)
    
    temp_rgb = temperature_to_rgb(cct)
    
    n_panels = 4
    if original_image is not None:
        n_panels += 1
    if corrected_image is not None:
        n_panels += 1
    
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 6))
    if n_panels == 1:
        axes = [axes]
    
    ax_idx = 0
    
    if original_image is not None:
        axes[ax_idx].imshow(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
        axes[ax_idx].set_title('Original', fontsize=12, fontweight='bold')
        axes[ax_idx].axis('off')
        ax_idx += 1
    
    if corrected_image is not None:
        axes[ax_idx].imshow(cv2.cvtColor(corrected_image, cv2.COLOR_BGR2RGB))
        axes[ax_idx].set_title('Corrected', fontsize=12, fontweight='bold')
        axes[ax_idx].axis('off')
        ax_idx += 1
    
    axes[ax_idx].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    axes[ax_idx].set_title('Analyzed', fontsize=12, fontweight='bold')
    axes[ax_idx].axis('off')
    ax_idx += 1
    
    color_patch = np.ones((200, 200, 3), dtype=np.float32)
    color_patch[:, :] = np.clip(illuminant.astype(np.float32), 0, 1)
    color_patch = (color_patch * 255).astype(np.uint8)
    axes[ax_idx].imshow(color_patch)
    axes[ax_idx].set_title('Estimated\nLight Color', fontsize=12, fontweight='bold')
    axes[ax_idx].axis('off')
    ax_idx += 1
    
    info_text = f'Method: {method_name}\n'
    info_text += f'Illuminant RGB: [{illuminant[0]:.3f}, {illuminant[1]:.3f}, {illuminant[2]:.3f}]\n'
    info_text += f'CCT: {cct:.0f} K\n'
    info_text += f'duv: {duv:.4f}\n'
    
    if cct < 3500:
        temp_label = 'Warm'
    elif cct < 5000:
        temp_label = 'Neutral'
    elif cct < 6500:
        temp_label = 'Cool'
    else:
        temp_label = 'Very Cool'
    
    info_text += f'Classification: {temp_label}'
    
    axes[ax_idx].text(0.1, 0.7, info_text,
                      transform=axes[ax_idx].transAxes,
                      fontsize=10, verticalalignment='top',
                      fontfamily='monospace',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    axes[ax_idx].axis('off')
    axes[ax_idx].set_title('Estimation Info', fontsize=12, fontweight='bold')
    ax_idx += 1
    
    bar, temps = create_color_temperature_bar()
    axes[ax_idx].imshow(bar, aspect='auto', extent=[temps[0], temps[-1], 0, 1])
    axes[ax_idx].axvline(x=cct, color='red', linewidth=3, linestyle='--')
    axes[ax_idx].set_xlabel('Color Temperature (K)')
    axes[ax_idx].set_yticks([])
    axes[ax_idx].set_title('CCT Scale', fontsize=12, fontweight='bold')
    axes[ax_idx].set_xlim(temps[0], temps[-1])
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Illuminant visualization saved to {save_path}")
    
    return fig, axes


def plot_illuminant_comparison_with_temperature(estimates, ground_truths, method_names, 
                                             save_path=None):
    """
    Plot illuminant comparison with color temperature visualization.
    
    Args:
        estimates: Dictionary of method_name -> (N, 3) estimates
        ground_truths: Ground truth illuminants (N, 3)
        method_names: List of method names
        save_path: Optional path to save figure
    
    Returns:
        fig, axes: Figure and axes
    """
    n_methods = len(method_names)
    n_samples = len(ground_truths)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    gt_cct, gt_duv = rgb_to_temperature(np.array(ground_truths))
    
    ax = axes[0, 0]
    bar, temps = create_color_temperature_bar()
    ax.imshow(bar, aspect='auto', extent=[temps[0], temps[-1], 0, n_methods + 1])
    
    for i, method in enumerate(method_names):
        est_cct, _ = rgb_to_temperature(np.array(estimates[method]))
        mean_cct = np.mean(est_cct)
        ax.axhline(y=i + 0.5, color='white', linewidth=0.5, alpha=0.3)
        ax.scatter([mean_cct], [i + 0.5], c='white', s=100, 
                   edgecolors='black', zorder=5, label=f'{method}: {mean_cct:.0f}K')
    
    ax.scatter([np.mean(gt_cct)], [n_methods + 0.5], 
              c='red', marker='*', s=200, 
              edgecolors='black', zorder=5, label=f'GT: {np.mean(gt_cct):.0f}K')
    
    ax.set_yticks(np.arange(0.5, n_methods + 1.5))
    ax.set_yticklabels(method_names + ['Ground Truth'])
    ax.set_xlabel('Color Temperature (K)')
    ax.set_title('Estimated Color Temperature')
    ax.set_xlim(temps[0], temps[-1])
    ax.legend(loc='lower right', fontsize=8)
    ax.grid(True, alpha=0.3, axis='x')
    
    ax = axes[0, 1]
    colors = plt.cm.tab10(np.linspace(0, 1, n_methods))
    
    for i, method in enumerate(method_names):
        est_cct, _ = rgb_to_temperature(np.array(estimates[method]))
        ax.hist(est_cct, bins=20, alpha=0.5, color=colors[i], label=method,
                edgecolor='white')
    
    ax.hist(gt_cct, bins=20, alpha=0.3, color='black', label='Ground Truth',
            edgecolor='white', hatch='//')
    
    ax.set_xlabel('Color Temperature (K)')
    ax.set_ylabel('Frequency')
    ax.set_title('CCT Distribution')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    ax = axes[1, 0]
    gt = np.array(ground_truths)
    sum_gt = np.sum(gt, axis=1, keepdims=True) + 1e-8
    gt_r = gt[:, 0] / sum_gt[:, 0]
    gt_g = gt[:, 1] / sum_gt[:, 0]
    
    ax.scatter(gt_r, gt_g, c='black', marker='x', s=100, label='Ground Truth', zorder=10)
    
    for i, method in enumerate(method_names):
        est = np.array(estimates[method])
        sum_est = np.sum(est, axis=1, keepdims=True) + 1e-8
        est_r = est[:, 0] / sum_est[:, 0]
        est_g = est[:, 1] / sum_est[:, 0]
        
        ax.scatter(est_r, est_g, c=[colors[i]], marker='o', s=40,
                  alpha=0.7, label=method, edgecolors='white', linewidths=0.5)
    
    ax.set_xlabel('r = R/(R+G+B)')
    ax.set_ylabel('g = G/(R+G+B)')
    ax.set_title('Chromaticity Diagram')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.set_xlim(0.2, 0.5)
    ax.set_ylim(0.25, 0.4)
    ax.grid(True, alpha=0.3)
    
    ax = axes[1, 1]
    x = np.arange(n_samples)
    
    for i, method in enumerate(method_names):
        est_cct, _ = rgb_to_temperature(np.array(estimates[method]))
        ax.plot(x, est_cct, 'o-', color=colors[i], label=method, alpha=0.7, markersize=4)
    
    ax.plot(x, gt_cct, 'k-x', label='Ground Truth', linewidth=2, markersize=8)
    
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Color Temperature (K)')
    ax.set_title('CCT per Sample')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Temperature comparison plot saved to {save_path}")
    
    return fig, axes


def plot_illuminant_comparison(estimates, ground_truths, method_names, save_path=None):
    """
    Plot comparison of estimated vs ground truth illuminants in chromaticity space.
    
    Args:
        estimates: Dictionary of method_name -> (N, 3) estimates
        ground_truths: Ground truth illuminants (N, 3)
        method_names: List of method names
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(1, 2, figsize=(14, 6))
    
    gt = np.array(ground_truths)
    sum_gt = np.sum(gt, axis=1, keepdims=True) + 1e-8
    gt_r = gt[:, 0] / sum_gt[:, 0]
    gt_g = gt[:, 1] / sum_gt[:, 0]
    
    ax[0].scatter(gt_r, gt_g, c='black', marker='x', s=100, label='Ground Truth', zorder=10)
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(method_names)))
    
    for i, method in enumerate(method_names):
        est = np.array(estimates[method])
        sum_est = np.sum(est, axis=1, keepdims=True) + 1e-8
        est_r = est[:, 0] / sum_est[:, 0]
        est_g = est[:, 1] / sum_est[:, 0]
        
        ax[0].scatter(est_r, est_g, c=[colors[i]], marker='o', s=40, 
                      alpha=0.7, label=method, edgecolors='white', linewidths=0.5)
    
    for i in range(len(gt_r)):
        for method in method_names:
            est = np.array(estimates[method])
            sum_est = np.sum(est, axis=1, keepdims=True) + 1e-8
            est_r = est[i, 0] / sum_est[i, 0]
            est_g = est[i, 1] / sum_est[i, 0]
            ax[0].plot([gt_r[i], est_r], [gt_g[i], est_g], 'gray', alpha=0.2, linewidth=0.5)
    
    ax[0].set_xlabel('r = R/(R+G+B)')
    ax[0].set_ylabel('g = G/(R+G+B)')
    ax[0].set_title('Illuminant Chromaticity')
    ax[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax[0].set_xlim(0, 1)
    ax[0].set_ylim(0, 1)
    ax[0].grid(True, alpha=0.3)
    
    errors_dict = {}
    for method in method_names:
        from .metrics import angular_error
        errors = angular_error(estimates[method], ground_truths)
        errors_dict[method] = errors
    
    boxplot_data = [errors_dict[m] for m in method_names]
    bp = ax[1].boxplot(boxplot_data, labels=method_names, patch_artist=True)
    
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax[1].set_ylabel('Angular Error (degrees)')
    ax[1].set_title('Angular Error Distribution')
    ax[1].grid(True, alpha=0.3, axis='y')
    plt.setp(ax[1].get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, ax


def plot_method_comparison(metrics_dict, save_path=None):
    """
    Plot comparison of methods across different metrics.
    
    Args:
        metrics_dict: Dictionary of method_name -> metrics dict
        save_path: Optional path to save figure
    """
    method_names = list(metrics_dict.keys())
    metric_names = ['mean', 'median', 'trimean', 'best25', 'worst25']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(metric_names))
    width = 0.15
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(method_names)))
    
    for i, method in enumerate(method_names):
        values = [metrics_dict[method][m] for m in metric_names]
        ax.bar(x + i * width, values, width, label=method, 
               color=colors[i], alpha=0.8, edgecolor='white')
    
    ax.set_xlabel('Metric')
    ax.set_ylabel('Angular Error (degrees)')
    ax.set_title('Method Comparison - Angular Error Metrics')
    ax.set_xticks(x + width * (len(method_names) - 1) / 2)
    ax.set_xticklabels(metric_names)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    
    for i, method in enumerate(method_names):
        for j, m in enumerate(metric_names):
            val = metrics_dict[method][m]
            ax.text(x[j] + i * width, val + 0.05, f'{val:.2f}', 
                    ha='center', va='bottom', fontsize=8, rotation=0)
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, ax


def plot_error_cdf(errors_dict, save_path=None):
    """
    Plot cumulative distribution function of angular errors.
    
    Args:
        errors_dict: Dictionary of method_name -> error array
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(errors_dict)))
    
    for i, (method, errors) in enumerate(errors_dict.items()):
        sorted_errors = np.sort(errors)
        cdf = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors)
        ax.plot(sorted_errors, cdf, label=method, color=colors[i], 
                linewidth=2, alpha=0.8)
    
    ax.set_xlabel('Angular Error (degrees)')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('CDF of Angular Errors')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, None)
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, ax


def plot_wb_results(original, corrected, ground_truth=None, method_names=None, save_path=None):
    """
    Plot white balance correction results.
    
    Args:
        original: Original image (H, W, 3)
        corrected: Dictionary of method_name -> corrected image
        ground_truth: Optional ground truth image
        method_names: List of method names
        save_path: Optional path to save figure
    """
    if method_names is None:
        method_names = list(corrected.keys())
    
    n_cols = min(len(method_names) + 1 + (1 if ground_truth is not None else 0), 4)
    n_rows = int(np.ceil((len(method_names) + 1 + (1 if ground_truth is not None else 0)) / n_cols))
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 4 * n_rows))
    if n_rows == 1:
        axes = axes.reshape(1, -1)
    
    ax = axes[0, 0]
    ax.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB))
    ax.set_title('Original')
    ax.axis('off')
    
    idx = 1
    if ground_truth is not None:
        ax = axes[0, 1] if n_cols > 1 else axes[0]
        ax.imshow(cv2.cvtColor(ground_truth, cv2.COLOR_BGR2RGB))
        ax.set_title('Ground Truth')
        ax.axis('off')
        idx = 2
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(method_names)))
    
    for i, method in enumerate(method_names):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col] if n_rows > 1 else axes[col]
        
        img = corrected[method]
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        ax.set_title(method, color=colors[i], fontsize=10)
        ax.axis('off')
        
        idx += 1
    
    for i in range(idx, n_rows * n_cols):
        row = i // n_cols
        col = i % n_cols
        axes[row, col].axis('off')
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, axes


def plot_illuminant_3d(estimates, ground_truths, method_names, save_path=None):
    """
    Plot illuminants in 3D RGB space.
    
    Args:
        estimates: Dictionary of method_name -> (N, 3) estimates
        ground_truths: Ground truth illuminants (N, 3)
        method_names: List of method names
        save_path: Optional path to save figure
    """
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    gt = np.array(ground_truths)
    ax.scatter(gt[:, 0], gt[:, 1], gt[:, 2], c='black', marker='x', 
               s=100, label='Ground Truth', zorder=10)
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(method_names)))
    
    for i, method in enumerate(method_names):
        est = np.array(estimates[method])
        ax.scatter(est[:, 0], est[:, 1], est[:, 2], c=[colors[i]], 
                   marker='o', s=50, alpha=0.7, label=method)
    
    ax.set_xlabel('R')
    ax.set_ylabel('G')
    ax.set_zlabel('B')
    ax.set_title('Illuminant Estimates in RGB Space')
    ax.legend()
    
    max_val = np.max([np.max(gt), np.max([np.max(e) for e in estimates.values()])])
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_zlim(0, max_val)
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, ax


def plot_metrics_radar(metrics_dict, save_path=None):
    """
    Plot method comparison using radar chart.
    
    Args:
        metrics_dict: Dictionary of method_name -> metrics dict
        save_path: Optional path to save figure
    """
    method_names = list(metrics_dict.keys())
    metric_names = ['mean', 'median', 'trimean', 'best25', 'worst25']
    
    angles = np.linspace(0, 2 * np.pi, len(metric_names), endpoint=False)
    angles = np.concatenate((angles, [angles[0]]))
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(method_names)))
    
    max_val = max([max([metrics_dict[m][metric] for metric in metric_names]) 
                   for m in method_names])
    
    for i, method in enumerate(method_names):
        values = [metrics_dict[method][m] for m in metric_names]
        values = np.concatenate((values, [values[0]]))
        
        values_norm = [v / max_val for v in values]
        
        ax.plot(angles, values_norm, label=method, color=colors[i], 
                linewidth=2, alpha=0.8)
        ax.fill(angles, values_norm, color=colors[i], alpha=0.15)
    
    metric_labels = metric_names + [metric_names[0]]
    ax.set_xticks(angles)
    ax.set_xticklabels(metric_labels)
    ax.set_ylim(0, 1)
    ax.set_title('Method Comparison - Radar Chart')
    ax.legend(bbox_to_anchor=(1.3, 0.5), loc='center left')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to {save_path}")
    
    return fig, ax


def plot_stability_comparison(stability_metrics, save_path=None):
    """
    Plot stability comparison across different methods.
    
    Args:
        stability_metrics: Dictionary of method_name -> stability metrics
        save_path: Optional path to save figure
    
    Returns:
        fig, ax: Figure and axes
    """
    method_names = list(stability_metrics.keys())
    n_methods = len(method_names)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    colors = plt.cm.tab10(np.linspace(0, 1, n_methods))
    
    angular_vars = [stability_metrics[m]['mean_angular_variation_deg'] for m in method_names]
    axes[0].bar(range(n_methods), angular_vars, color=colors, alpha=0.8, edgecolor='white')
    axes[0].set_ylabel('Mean Angular Variation (°)')
    axes[0].set_title('Estimate Variation Under Perturbation')
    axes[0].set_xticks(range(n_methods))
    axes[0].set_xticklabels(method_names, rotation=45, ha='right')
    axes[0].grid(True, alpha=0.3, axis='y')
    
    for i, v in enumerate(angular_vars):
        axes[0].text(i, v + max(angular_vars) * 0.01, f'{v:.4f}', 
                    ha='center', va='bottom', fontsize=8)
    
    overall_stds = [stability_metrics[m]['overall_mean_std'] for m in method_names]
    axes[1].bar(range(n_methods), overall_stds, color=colors, alpha=0.8, edgecolor='white')
    axes[1].set_ylabel('Overall Mean Std')
    axes[1].set_title('Estimate Standard Deviation')
    axes[1].set_xticks(range(n_methods))
    axes[1].set_xticklabels(method_names, rotation=45, ha='right')
    axes[1].grid(True, alpha=0.3, axis='y')
    
    for i, v in enumerate(overall_stds):
        axes[1].text(i, v + max(overall_stds) * 0.01, f'{v:.6f}', 
                    ha='center', va='bottom', fontsize=8)
    
    covs = [stability_metrics[m]['coefficient_of_variation'] for m in method_names]
    axes[2].bar(range(n_methods), covs, color=colors, alpha=0.8, edgecolor='white')
    axes[2].set_ylabel('Coefficient of Variation')
    axes[2].set_title('Normalized Variability (CoV)')
    axes[2].set_xticks(range(n_methods))
    axes[2].set_xticklabels(method_names, rotation=45, ha='right')
    axes[2].grid(True, alpha=0.3, axis='y')
    
    for i, v in enumerate(covs):
        axes[2].text(i, v + max(covs) * 0.01, f'{v:.6f}', 
                    ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Stability comparison plot saved to {save_path}")
    
    return fig, axes


def generate_summary_report(results, output_dir):
    """
    Generate comprehensive summary report of evaluation results.
    
    Args:
        results: Dictionary of evaluation results
        output_dir: Directory to save report
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    method_names = list(results['estimates'].keys())
    
    plot_illuminant_comparison(
        results['estimates'],
        results['ground_truths'],
        method_names,
        save_path=str(output_dir / 'illuminant_comparison.png')
    )
    
    plot_method_comparison(
        results['metrics'],
        save_path=str(output_dir / 'method_comparison.png')
    )
    
    errors_dict = {m: results['metrics'][m]['angular_errors'] for m in method_names}
    plot_error_cdf(
        errors_dict,
        save_path=str(output_dir / 'error_cdf.png')
    )
    
    plot_metrics_radar(
        results['metrics'],
        save_path=str(output_dir / 'radar_chart.png')
    )
    
    if 'sample_results' in results:
        sample = results['sample_results']
        plot_wb_results(
            sample['original'],
            sample['corrected'],
            sample.get('ground_truth'),
            method_names,
            save_path=str(output_dir / 'wb_example.png')
        )
    
    txt_report = output_dir / 'evaluation_summary.txt'
    with open(txt_report, 'w') as f:
        f.write('=' * 60 + '\n')
        f.write('COLOR CONSTANCY EVALUATION SUMMARY\n')
        f.write('=' * 60 + '\n\n')
        
        f.write('Dataset Information:\n')
        f.write(f"  Number of samples: {results['num_samples']}\n\n")
        
        f.write('Angular Error Metrics (degrees):\n')
        f.write('-' * 60 + '\n')
        f.write(f"{'Method':<20} {'Mean':>8} {'Median':>8} {'Trimean':>8} {'Best25':>8} {'Worst25':>8}\n")
        f.write('-' * 60 + '\n')
        
        for method in method_names:
            m = results['metrics'][method]
            f.write(f"{method:<20} {m['mean']:>8.2f} {m['median']:>8.2f} {m['trimean']:>8.2f} "
                   f"{m['best25']:>8.2f} {m['worst25']:>8.2f}\n")
        
        f.write('\n')
        f.write('Image Quality Metrics (if available):\n')
        if 'quality_metrics' in results:
            f.write('-' * 60 + '\n')
            f.write(f"{'Method':<20} {'ΔE':>8} {'PSNR':>8} {'SSIM':>8}\n")
            f.write('-' * 60 + '\n')
            for method in method_names:
                qm = results['quality_metrics'][method]
                f.write(f"{method:<20} {qm['delta_e']['mean']:>8.2f} "
                       f"{qm['psnr']['mean']:>8.2f} {qm['ssim']['mean']:>8.3f}\n")
    
    print(f"Summary report generated in {output_dir}")
