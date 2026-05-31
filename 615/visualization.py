import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch


class RegistrationVisualizer:
    def __init__(self, figsize=(15, 10)):
        self.figsize = figsize

    def plot_registration_result(self, ref_img, target_img, transformed_img, 
                                 translation, rotation, scale, quality_metrics):
        fig, axes = plt.subplots(2, 3, figsize=self.figsize)
        
        axes[0, 0].imshow(ref_img, cmap='gray')
        axes[0, 0].set_title('Reference Image')
        axes[0, 0].axis('off')
        
        axes[0, 1].imshow(target_img, cmap='gray')
        axes[0, 1].set_title('Target Image')
        axes[0, 1].axis('off')
        
        axes[0, 2].imshow(transformed_img, cmap='gray')
        axes[0, 2].set_title('Registered Image')
        axes[0, 2].axis('off')
        
        diff_before = np.abs(ref_img - target_img)
        axes[1, 0].imshow(diff_before, cmap='hot')
        axes[1, 0].set_title('Difference Before Registration')
        axes[1, 0].axis('off')
        
        diff_after = np.abs(ref_img - transformed_img)
        axes[1, 1].imshow(diff_after, cmap='hot')
        axes[1, 1].set_title('Difference After Registration')
        axes[1, 1].axis('off')
        
        axes[1, 2].axis('off')
        info_text = (
            f"Transformation Parameters:\n"
            f"  Translation: ({translation[0]:.3f}, {translation[1]:.3f})\n"
            f"  Rotation: {rotation:.3f}°\n"
            f"  Scale: {scale:.3f}\n\n"
            f"Quality Metrics:\n"
            f"  NCC: {quality_metrics['ncc']:.4f}\n"
            f"  SSIM: {quality_metrics['ssim']:.4f}\n"
            f"  PSNR: {quality_metrics['psnr']:.2f} dB\n"
            f"  MSE: {quality_metrics['mse']:.4f}\n"
            f"  MI: {quality_metrics['mutual_information']:.4f}\n"
            f"  Gradient Sim: {quality_metrics['gradient_similarity']:.4f}"
        )
        axes[1, 2].text(0.05, 0.95, info_text, 
                        transform=axes[1, 2].transAxes,
                        verticalalignment='top',
                        fontsize=10,
                        family='monospace')
        
        plt.tight_layout()
        return fig

    def plot_correlation_peak(self, correlation, dx, dy):
        fig, ax = plt.subplots(1, 2, figsize=(12, 5))
        
        im = ax[0].imshow(correlation, cmap='viridis')
        ax[0].set_title('Phase Correlation Map')
        ax[0].set_xlabel('X')
        ax[0].set_ylabel('Y')
        plt.colorbar(im, ax=ax[0])
        
        center_x = correlation.shape[1] // 2
        center_y = correlation.shape[0] // 2
        peak_x = center_x + dx
        peak_y = center_y + dy
        
        ax[0].plot(peak_x, peak_y, 'ro', markersize=10, label='Peak')
        ax[0].legend()
        
        window_size = 10
        x_start = max(0, int(peak_x) - window_size)
        x_end = min(correlation.shape[1], int(peak_x) + window_size + 1)
        y_start = max(0, int(peak_y) - window_size)
        y_end = min(correlation.shape[0], int(peak_y) + window_size + 1)
        
        zoomed = correlation[y_start:y_end, x_start:x_end]
        im2 = ax[1].imshow(zoomed, cmap='viridis', extent=[x_start, x_end, y_end, y_start])
        ax[1].set_title(f'Peak Detail (dx={dx:.3f}, dy={dy:.3f})')
        ax[1].set_xlabel('X')
        ax[1].set_ylabel('Y')
        plt.colorbar(im2, ax=ax[1])
        
        ax[1].plot(peak_x, peak_y, 'rx', markersize=15, markeredgewidth=2)
        
        plt.tight_layout()
        return fig

    def plot_log_polar_transform(self, ref_lp, target_lp, correlation_lp):
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        im1 = axes[0].imshow(ref_lp, cmap='viridis', aspect='auto')
        axes[0].set_title('Reference Log-Polar')
        axes[0].set_xlabel('Angle')
        axes[0].set_ylabel('Log Radius')
        plt.colorbar(im1, ax=axes[0])
        
        im2 = axes[1].imshow(target_lp, cmap='viridis', aspect='auto')
        axes[1].set_title('Target Log-Polar')
        axes[1].set_xlabel('Angle')
        axes[1].set_ylabel('Log Radius')
        plt.colorbar(im2, ax=axes[1])
        
        im3 = axes[2].imshow(correlation_lp, cmap='viridis', aspect='auto')
        axes[2].set_title('Log-Polar Correlation')
        axes[2].set_xlabel('Angle Offset')
        axes[2].set_ylabel('Scale Offset')
        plt.colorbar(im3, ax=axes[2])
        
        peak = np.unravel_index(np.argmax(correlation_lp), correlation_lp.shape)
        axes[2].plot(peak[1], peak[0], 'ro', markersize=10)
        
        plt.tight_layout()
        return fig

    def plot_quality_comparison(self, batch_results):
        if not batch_results:
            return None
        
        indices = [r['index'] for r in batch_results]
        ncc_values = [r['quality']['ncc'] for r in batch_results]
        ssim_values = [r['quality']['ssim'] for r in batch_results]
        psnr_values = [r['quality']['psnr'] for r in batch_results]
        mse_values = [r['quality']['mse'] for r in batch_results]
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        axes[0, 0].plot(indices, ncc_values, 'b-o', linewidth=2, markersize=6)
        axes[0, 0].set_title('Normalized Cross Correlation')
        axes[0, 0].set_xlabel('Image Index')
        axes[0, 0].set_ylabel('NCC')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].set_ylim([min(0, min(ncc_values) - 0.1), 1.1])
        
        axes[0, 1].plot(indices, ssim_values, 'g-o', linewidth=2, markersize=6)
        axes[0, 1].set_title('Structural Similarity Index')
        axes[0, 1].set_xlabel('Image Index')
        axes[0, 1].set_ylabel('SSIM')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].set_ylim([min(0, min(ssim_values) - 0.1), 1.1])
        
        axes[1, 0].plot(indices, psnr_values, 'r-o', linewidth=2, markersize=6)
        axes[1, 0].set_title('Peak Signal to Noise Ratio')
        axes[1, 0].set_xlabel('Image Index')
        axes[1, 0].set_ylabel('PSNR (dB)')
        axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].plot(indices, mse_values, 'm-o', linewidth=2, markersize=6)
        axes[1, 1].set_title('Mean Squared Error')
        axes[1, 1].set_xlabel('Image Index')
        axes[1, 1].set_ylabel('MSE')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig

    def plot_transformation_parameters(self, batch_results):
        if not batch_results:
            return None
        
        indices = [r['index'] for r in batch_results]
        tx = [r['translation_x'] for r in batch_results]
        ty = [r['translation_y'] for r in batch_results]
        rot = [r['rotation'] for r in batch_results]
        scale = [r['scale'] for r in batch_results]
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        axes[0, 0].plot(indices, tx, 'b-o', linewidth=2, markersize=6, label='X')
        axes[0, 0].plot(indices, ty, 'r-o', linewidth=2, markersize=6, label='Y')
        axes[0, 0].set_title('Translation Parameters')
        axes[0, 0].set_xlabel('Image Index')
        axes[0, 0].set_ylabel('Translation (pixels)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        axes[0, 1].plot(indices, rot, 'g-o', linewidth=2, markersize=6)
        axes[0, 1].set_title('Rotation Angle')
        axes[0, 1].set_xlabel('Image Index')
        axes[0, 1].set_ylabel('Rotation (degrees)')
        axes[0, 1].grid(True, alpha=0.3)
        
        axes[1, 0].plot(indices, scale, 'm-o', linewidth=2, markersize=6)
        axes[1, 0].set_title('Scale Factor')
        axes[1, 0].set_xlabel('Image Index')
        axes[1, 0].set_ylabel('Scale')
        axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].scatter(tx, ty, c=indices, cmap='viridis', s=50)
        axes[1, 1].set_title('Translation Scatter Plot')
        axes[1, 1].set_xlabel('X Translation (pixels)')
        axes[1, 1].set_ylabel('Y Translation (pixels)')
        axes[1, 1].grid(True, alpha=0.3)
        for i, txt in enumerate(indices):
            axes[1, 1].annotate(str(txt), (tx[i], ty[i]), xytext=(5, 5), 
                                 textcoords='offset points')
        
        plt.tight_layout()
        return fig

    def plot_overlay_comparison(self, ref_img, transformed_img, alpha=0.5):
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        
        ref_rgb = np.stack([ref_img] * 3, axis=-1)
        ref_rgb = (ref_rgb - ref_rgb.min()) / (ref_rgb.max() - ref_rgb.min() + 1e-12)
        
        trans_rgb = np.stack([transformed_img] * 3, axis=-1)
        trans_rgb = (trans_rgb - trans_rgb.min()) / (trans_rgb.max() - trans_rgb.min() + 1e-12)
        
        overlay = np.zeros_like(ref_rgb)
        overlay[..., 0] = ref_rgb[..., 0]
        overlay[..., 1] = trans_rgb[..., 1]
        overlay[..., 2] = (ref_rgb[..., 2] + trans_rgb[..., 2]) / 2
        
        ax.imshow(overlay)
        ax.set_title('Overlay Comparison (Red=Ref, Green=Registered)')
        ax.axis('off')
        
        return fig

    def compute_local_error_map(self, ref_img, transformed_img, window_size=11, metric='mse'):
        ref = ref_img.astype(np.float64)
        trans = transformed_img.astype(np.float64)
        
        rows, cols = ref.shape
        pad = window_size // 2
        
        ref_pad = np.pad(ref, pad, mode='reflect')
        trans_pad = np.pad(trans, pad, mode='reflect')
        
        error_map = np.zeros((rows, cols))
        
        for i in range(rows):
            for j in range(cols):
                ref_patch = ref_pad[i:i+window_size, j:j+window_size]
                trans_patch = trans_pad[i:i+window_size, j:j+window_size]
                
                if metric == 'mse':
                    error_map[i, j] = np.mean((ref_patch - trans_patch)**2)
                elif metric == 'ncc':
                    ref_norm = (ref_patch - np.mean(ref_patch)) / (np.std(ref_patch) + 1e-12)
                    trans_norm = (trans_patch - np.mean(trans_patch)) / (np.std(trans_patch) + 1e-12)
                    error_map[i, j] = 1.0 - np.mean(ref_norm * trans_norm)
                elif metric == 'abs':
                    error_map[i, j] = np.mean(np.abs(ref_patch - trans_patch))
                elif metric == 'ssim':
                    error_map[i, j] = 1.0 - self._local_ssim(ref_patch, trans_patch)
        
        return error_map

    def _local_ssim(self, img1, img2):
        K1 = 0.01
        K2 = 0.03
        L = max(img1.max() - img1.min(), img2.max() - img2.min())
        if L == 0:
            L = 1.0
        
        C1 = (K1 * L)**2
        C2 = (K2 * L)**2
        
        mu1 = np.mean(img1)
        mu2 = np.mean(img2)
        sigma1_sq = np.var(img1)
        sigma2_sq = np.var(img2)
        sigma12 = np.mean((img1 - mu1) * (img2 - mu2))
        
        ssim = ((2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2))
        
        return ssim

    def plot_error_heatmap(self, ref_img, target_img, transformed_img, window_size=11):
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        axes[0, 0].imshow(ref_img, cmap='gray')
        axes[0, 0].set_title('Reference Image')
        axes[0, 0].axis('off')
        
        axes[0, 1].imshow(target_img, cmap='gray')
        axes[0, 1].set_title('Target Image')
        axes[0, 1].axis('off')
        
        axes[0, 2].imshow(transformed_img, cmap='gray')
        axes[0, 2].set_title('Registered Image')
        axes[0, 2].axis('off')
        
        mse_map_before = self.compute_local_error_map(ref_img, target_img, window_size, 'mse')
        im1 = axes[1, 0].imshow(mse_map_before, cmap='hot', aspect='auto')
        axes[1, 0].set_title('Local MSE Before Registration')
        axes[1, 0].axis('off')
        plt.colorbar(im1, ax=axes[1, 0], fraction=0.046, pad=0.04)
        
        mse_map_after = self.compute_local_error_map(ref_img, transformed_img, window_size, 'mse')
        im2 = axes[1, 1].imshow(mse_map_after, cmap='hot', aspect='auto')
        axes[1, 1].set_title('Local MSE After Registration')
        axes[1, 1].axis('off')
        plt.colorbar(im2, ax=axes[1, 1], fraction=0.046, pad=0.04)
        
        mse_diff = mse_map_before - mse_map_after
        vmax = np.max(np.abs(mse_diff))
        im3 = axes[1, 2].imshow(mse_diff, cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='auto')
        axes[1, 2].set_title('MSE Improvement (Blue=Better)')
        axes[1, 2].axis('off')
        plt.colorbar(im3, ax=axes[1, 2], fraction=0.046, pad=0.04)
        
        plt.tight_layout()
        return fig

    def plot_detailed_error_analysis(self, ref_img, transformed_img, window_size=11):
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        
        abs_error = np.abs(ref_img - transformed_img)
        im0 = axes[0, 0].imshow(abs_error, cmap='hot', aspect='auto')
        axes[0, 0].set_title('Pixel-wise Absolute Error')
        axes[0, 0].axis('off')
        plt.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)
        
        ncc_map = self.compute_local_error_map(ref_img, transformed_img, window_size, 'ncc')
        im1 = axes[0, 1].imshow(ncc_map, cmap='hot', aspect='auto')
        axes[0, 1].set_title(f'Local 1-NCC (Window={window_size}x{window_size})')
        axes[0, 1].axis('off')
        plt.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)
        
        ssim_map = self.compute_local_error_map(ref_img, transformed_img, window_size, 'ssim')
        im2 = axes[1, 0].imshow(ssim_map, cmap='hot', aspect='auto')
        axes[1, 0].set_title(f'Local 1-SSIM (Window={window_size}x{window_size})')
        axes[1, 0].axis('off')
        plt.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)
        
        grad_y1, grad_x1 = np.gradient(ref_img)
        grad_y2, grad_x2 = np.gradient(transformed_img)
        mag1 = np.sqrt(grad_x1**2 + grad_y1**2)
        mag2 = np.sqrt(grad_x2**2 + grad_y2**2)
        angle1 = np.arctan2(grad_y1, grad_x1)
        angle2 = np.arctan2(grad_y2, grad_x2)
        angle_error = np.abs(np.arctan2(np.sin(angle1 - angle2), np.cos(angle1 - angle2)))
        angle_error = np.degrees(angle_error)
        
        im3 = axes[1, 1].imshow(angle_error, cmap='hot', aspect='auto')
        axes[1, 1].set_title('Gradient Direction Error (degrees)')
        axes[1, 1].axis('off')
        plt.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04)
        
        plt.tight_layout()
        return fig

    def plot_registration_error_histogram(self, ref_img, target_img, transformed_img):
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        error_before = np.abs(ref_img - target_img).flatten()
        error_after = np.abs(ref_img - transformed_img).flatten()
        
        bins = np.linspace(0, min(np.percentile(error_before, 99), 100), 50)
        
        axes[0].hist(error_before, bins=bins, alpha=0.6, label='Before', density=True)
        axes[0].hist(error_after, bins=bins, alpha=0.6, label='After', density=True)
        axes[0].set_title('Error Distribution')
        axes[0].set_xlabel('Absolute Pixel Error')
        axes[0].set_ylabel('Normalized Frequency')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        error_before_log = np.log10(error_before + 1e-10)
        error_after_log = np.log10(error_after + 1e-10)
        
        bins_log = np.linspace(min(error_before_log.min(), error_after_log.min()), 
                               max(error_before_log.max(), error_after_log.max()), 50)
        
        axes[1].hist(error_before_log, bins=bins_log, alpha=0.6, label='Before', density=True)
        axes[1].hist(error_after_log, bins=bins_log, alpha=0.6, label='After', density=True)
        axes[1].set_title('Log-Scaled Error Distribution')
        axes[1].set_xlabel('Log10(Absolute Error)')
        axes[1].set_ylabel('Normalized Frequency')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig

    def save_error_heatmap_data(self, ref_img, transformed_img, output_path, window_size=11):
        abs_error = np.abs(ref_img - transformed_img)
        mse_map = self.compute_local_error_map(ref_img, transformed_img, window_size, 'mse')
        ncc_map = self.compute_local_error_map(ref_img, transformed_img, window_size, 'ncc')
        
        data = {
            'absolute_error': abs_error,
            'local_mse': mse_map,
            'local_ncc': ncc_map,
            'mean_abs_error': np.mean(abs_error),
            'max_abs_error': np.max(abs_error),
            'mean_local_mse': np.mean(mse_map),
            'mean_local_ncc': np.mean(ncc_map)
        }
        
        if output_path.endswith('.npz'):
            np.savez(output_path, **data)
        elif output_path.endswith('.npy'):
            np.save(output_path, data)
        
        return data
