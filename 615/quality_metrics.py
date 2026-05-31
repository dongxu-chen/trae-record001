import numpy as np
from scipy.stats import pearsonr
from skimage.metrics import structural_similarity as ssim


class RegistrationQualityEvaluator:
    def __init__(self):
        pass

    def compute_ncc(self, img1, img2):
        img1_norm = (img1 - np.mean(img1)) / (np.std(img1) + 1e-12)
        img2_norm = (img2 - np.mean(img2)) / (np.std(img2) + 1e-12)
        ncc = np.mean(img1_norm * img2_norm)
        return ncc

    def compute_ssim(self, img1, img2, win_size=7):
        if img1.dtype != np.float64:
            img1 = img1.astype(np.float64)
        if img2.dtype != np.float64:
            img2 = img2.astype(np.float64)
        
        data_range = max(img1.max() - img1.min(), img2.max() - img2.min())
        if data_range == 0:
            data_range = 1.0
        
        return ssim(img1, img2, win_size=win_size, data_range=data_range)

    def compute_mse(self, img1, img2):
        return np.mean((img1 - img2) ** 2)

    def compute_rmse(self, img1, img2):
        return np.sqrt(self.compute_mse(img1, img2))

    def compute_psnr(self, img1, img2):
        mse = self.compute_mse(img1, img2)
        if mse == 0:
            return float('inf')
        max_val = max(img1.max(), img2.max())
        return 20 * np.log10(max_val / np.sqrt(mse))

    def compute_mutual_information(self, img1, img2, bins=256):
        img1_flat = img1.flatten()
        img2_flat = img2.flatten()
        
        hist_2d, _, _ = np.histogram2d(img1_flat, img2_flat, bins=bins)
        pxy = hist_2d / hist_2d.sum()
        
        px = pxy.sum(axis=1)
        py = pxy.sum(axis=0)
        
        px_py = px[:, None] * py[None, :]
        nz = pxy > 0
        
        mi = np.sum(pxy[nz] * np.log(pxy[nz] / px_py[nz]))
        return mi

    def compute_correlation_coefficient(self, img1, img2):
        return pearsonr(img1.flatten(), img2.flatten())[0]

    def compute_gradient_similarity(self, img1, img2):
        grad_y1, grad_x1 = np.gradient(img1)
        grad_y2, grad_x2 = np.gradient(img2)
        
        mag1 = np.sqrt(grad_x1 ** 2 + grad_y1 ** 2)
        mag2 = np.sqrt(grad_x2 ** 2 + grad_y2 ** 2)
        
        mag1_norm = (mag1 - np.mean(mag1)) / (np.std(mag1) + 1e-12)
        mag2_norm = (mag2 - np.mean(mag2)) / (np.std(mag2) + 1e-12)
        
        return np.mean(mag1_norm * mag2_norm)

    def evaluate_all(self, ref_img, transformed_img):
        if len(ref_img.shape) == 3:
            ref_img = np.mean(ref_img, axis=2)
        if len(transformed_img.shape) == 3:
            transformed_img = np.mean(transformed_img, axis=2)
        
        return {
            'ncc': self.compute_ncc(ref_img, transformed_img),
            'ssim': self.compute_ssim(ref_img, transformed_img),
            'mse': self.compute_mse(ref_img, transformed_img),
            'rmse': self.compute_rmse(ref_img, transformed_img),
            'psnr': self.compute_psnr(ref_img, transformed_img),
            'mutual_information': self.compute_mutual_information(ref_img, transformed_img),
            'correlation_coefficient': self.compute_correlation_coefficient(ref_img, transformed_img),
            'gradient_similarity': self.compute_gradient_similarity(ref_img, transformed_img)
        }
