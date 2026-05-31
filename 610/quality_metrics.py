import numpy as np
from scipy.ndimage import gaussian_filter, sobel
from collections import namedtuple

QualityMetrics = namedtuple('QualityMetrics', [
    'snr', 'psnr', 'ssim', 'mse',
    'contrast_noise_ratio', 'sharpness',
    'entropy', 'signal_variation'
])


class ImageQualityMetrics:
    @staticmethod
    def calculate_mse(image1, image2):
        return np.mean((image1 - image2) ** 2)

    @staticmethod
    def calculate_psnr(image1, image2, max_val=1.0):
        mse = ImageQualityMetrics.calculate_mse(image1, image2)
        if mse == 0:
            return float('inf')
        return 20 * np.log10(max_val / np.sqrt(mse))

    @staticmethod
    def calculate_snr_estimated(image, signal_mask=None, noise_estimation='local'):
        if signal_mask is None:
            threshold = np.mean(image) + np.std(image) * 0.5
            signal_mask = image > threshold

        signal_pixels = image[signal_mask]
        background_pixels = image[~signal_mask] if np.sum(~signal_mask) > 10 else image

        if noise_estimation == 'local':
            noise_std = ImageQualityMetrics._estimate_noise_local(image)
        else:
            noise_std = np.std(background_pixels)

        signal_mean = np.mean(signal_pixels) if len(signal_pixels) > 0 else np.mean(image)

        if noise_std < 1e-10:
            return 0
        return 20 * np.log10(signal_mean / noise_std)

    @staticmethod
    def _estimate_noise_local(image, patch_size=7):
        h, w = image.shape
        noise_estimates = []
        for y in range(0, h - patch_size, patch_size // 2):
            for x in range(0, w - patch_size, patch_size // 2):
                patch = image[y:y + patch_size, x:x + patch_size]
                local_mean = np.mean(patch)
                local_var = np.var(patch)
                if local_var < 0.5 * np.var(image):
                    noise_estimates.append(np.sqrt(local_var))
        return np.median(noise_estimates) if noise_estimates else np.std(image) * 0.5

    @staticmethod
    def calculate_ssim(image1, image2, window_size=11, k1=0.01, k2=0.03, max_val=1.0):
        c1 = (k1 * max_val) ** 2
        c2 = (k2 * max_val) ** 2

        mu1 = gaussian_filter(image1, sigma=1.5)
        mu2 = gaussian_filter(image2, sigma=1.5)
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = gaussian_filter(image1 ** 2, sigma=1.5) - mu1_sq
        sigma2_sq = gaussian_filter(image2 ** 2, sigma=1.5) - mu2_sq
        sigma12 = gaussian_filter(image1 * image2, sigma=1.5) - mu1_mu2

        ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / \
                   ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
        return np.mean(ssim_map)

    @staticmethod
    def calculate_contrast_noise_ratio(image, signal_mask=None):
        if signal_mask is None:
            threshold = np.mean(image) + np.std(image)
            signal_mask = image > threshold

        signal_region = image[signal_mask]
        background_region = image[~signal_mask] if np.sum(~signal_mask) > 10 else image

        signal_mean = np.mean(signal_region) if len(signal_region) > 0 else np.mean(image)
        bg_std = np.std(background_region)

        if bg_std < 1e-10:
            return 0
        return (signal_mean - np.mean(background_region)) / bg_std

    @staticmethod
    def calculate_sharpness(image):
        grad_y = sobel(image, axis=0)
        grad_x = sobel(image, axis=1)
        gradient_magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
        return np.mean(gradient_magnitude)

    @staticmethod
    def calculate_entropy(image, bins=64):
        hist, _ = np.histogram(image.flatten(), bins=bins, range=(0, 1), density=True)
        hist = hist[hist > 0]
        return -np.sum(hist * np.log2(hist))

    @staticmethod
    def calculate_signal_variation(image, signal_mask=None):
        if signal_mask is None:
            threshold = np.mean(image) + np.std(image) * 0.5
            signal_mask = image > threshold

        signal_region = image[signal_mask]
        if len(signal_region) < 10:
            return 0
        return np.std(signal_region) / (np.mean(signal_region) + 1e-10)

    @staticmethod
    def compute_full_metrics(original, restored, max_val=1.0):
        mse = ImageQualityMetrics.calculate_mse(original, restored)
        psnr = ImageQualityMetrics.calculate_psnr(original, restored, max_val)
        ssim = ImageQualityMetrics.calculate_ssim(original, restored, max_val=max_val)

        snr_orig = ImageQualityMetrics.calculate_snr_estimated(original)
        snr_rest = ImageQualityMetrics.calculate_snr_estimated(restored)

        cnr_orig = ImageQualityMetrics.calculate_contrast_noise_ratio(original)
        cnr_rest = ImageQualityMetrics.calculate_contrast_noise_ratio(restored)

        sharp_orig = ImageQualityMetrics.calculate_sharpness(original)
        sharp_rest = ImageQualityMetrics.calculate_sharpness(restored)

        entropy_orig = ImageQualityMetrics.calculate_entropy(original)
        entropy_rest = ImageQualityMetrics.calculate_entropy(restored)

        return {
            'mse': mse,
            'psnr': psnr,
            'ssim': ssim,
            'snr_original': snr_orig,
            'snr_restored': snr_rest,
            'snr_improvement': snr_rest - snr_orig,
            'cnr_original': cnr_orig,
            'cnr_restored': cnr_rest,
            'cnr_improvement': cnr_rest - cnr_orig,
            'sharpness_original': sharp_orig,
            'sharpness_restored': sharp_rest,
            'sharpness_improvement': (sharp_rest - sharp_orig) / (sharp_orig + 1e-10) * 100,
            'entropy_original': entropy_orig,
            'entropy_restored': entropy_rest,
        }

    @staticmethod
    def compute_blind_metrics(image):
        snr = ImageQualityMetrics.calculate_snr_estimated(image)
        cnr = ImageQualityMetrics.calculate_contrast_noise_ratio(image)
        sharpness = ImageQualityMetrics.calculate_sharpness(image)
        entropy = ImageQualityMetrics.calculate_entropy(image)
        sig_var = ImageQualityMetrics.calculate_signal_variation(image)

        return {
            'estimated_snr': snr,
            'contrast_noise_ratio': cnr,
            'sharpness': sharpness,
            'entropy': entropy,
            'signal_variation': sig_var,
        }


class DeconvolutionQualityReport:
    def __init__(self):
        self.metrics_before = {}
        self.metrics_after = {}
        self.improvements = {}

    def evaluate(self, original_blurred, restored, ground_truth=None):
        self.metrics_before = ImageQualityMetrics.compute_blind_metrics(original_blurred)
        self.metrics_after = ImageQualityMetrics.compute_blind_metrics(restored)

        if ground_truth is not None:
            self.metrics_after.update(ImageQualityMetrics.compute_full_metrics(ground_truth, restored))
            self.metrics_before.update(ImageQualityMetrics.compute_full_metrics(ground_truth, original_blurred))

        self.improvements = {
            'snr_gain_db': self.metrics_after.get('estimated_snr', 0) - self.metrics_before.get('estimated_snr', 0),
            'cnr_gain': self.metrics_after.get('contrast_noise_ratio', 0) - self.metrics_before.get('contrast_noise_ratio', 0),
            'sharpness_gain_pct': ((self.metrics_after.get('sharpness', 0) - self.metrics_before.get('sharpness', 0)) /
                                    max(self.metrics_before.get('sharpness', 1e-10), 1e-10) * 100),
        }

        return self

    def generate_report_text(self):
        lines = ["=" * 50, "去卷积质量评估报告", "=" * 50, ""]

        lines.append("【无参考指标】")
        lines.append(f"  SNR估计:    {self.metrics_before.get('estimated_snr', 0):.2f} dB → "
                     f"{self.metrics_after.get('estimated_snr', 0):.2f} dB "
                     f"(提升 {self.improvements.get('snr_gain_db', 0):+.2f} dB)")
        lines.append(f"  对比度噪声比: {self.metrics_before.get('contrast_noise_ratio', 0):.2f} → "
                     f"{self.metrics_after.get('contrast_noise_ratio', 0):.2f} "
                     f"(提升 {self.improvements.get('cnr_gain', 0):+.2f})")
        lines.append(f"  锐度:       {self.metrics_before.get('sharpness', 0):.4f} → "
                     f"{self.metrics_after.get('sharpness', 0):.4f} "
                     f"(提升 {self.improvements.get('sharpness_gain_pct', 0):+.1f}%)")
        lines.append(f"  信息熵:     {self.metrics_before.get('entropy', 0):.3f} → "
                     f"{self.metrics_after.get('entropy', 0):.3f}")
        lines.append("")

        if 'psnr' in self.metrics_after:
            lines.append("【有参考指标】")
            lines.append(f"  PSNR:       {self.metrics_before.get('psnr', 0):.2f} dB → "
                         f"{self.metrics_after.get('psnr', 0):.2f} dB")
            lines.append(f"  SSIM:       {self.metrics_before.get('ssim', 0):.4f} → "
                         f"{self.metrics_after.get('ssim', 0):.4f}")
            lines.append(f"  MSE:        {self.metrics_before.get('mse', 0):.6f} → "
                         f"{self.metrics_after.get('mse', 0):.6f}")

        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)


def evaluate_3d_volume(volume_before, volume_after, ground_truth=None):
    nz = volume_before.shape[0]
    slice_reports = []

    for z in range(nz):
        report = DeconvolutionQualityReport()
        gt_slice = ground_truth[z] if ground_truth is not None else None
        report.evaluate(volume_before[z], volume_after[z], gt_slice)
        slice_reports.append(report)

    avg_improvements = {
        'snr_gain_db': np.mean([r.improvements['snr_gain_db'] for r in slice_reports]),
        'cnr_gain': np.mean([r.improvements['cnr_gain'] for r in slice_reports]),
        'sharpness_gain_pct': np.mean([r.improvements['sharpness_gain_pct'] for r in slice_reports]),
    }

    return slice_reports, avg_improvements


def evaluate_multichannel(image_before, image_after, ground_truth=None):
    num_channels = image_before.shape[0]
    channel_reports = []

    for c in range(num_channels):
        report = DeconvolutionQualityReport()
        if image_before[c].ndim == 3:
            bl = np.mean(image_before[c], axis=0)
            re = np.mean(image_after[c], axis=0)
            gt = np.mean(ground_truth[c], axis=0) if ground_truth is not None else None
        else:
            bl = image_before[c]
            re = image_after[c]
            gt = ground_truth[c] if ground_truth is not None else None
        report.evaluate(bl, re, gt)
        channel_reports.append(report)

    return channel_reports


if __name__ == '__main__':
    print("Quality metrics module loaded")
