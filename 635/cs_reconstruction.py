import numpy as np
import cv2
import os
import glob
import time
from cvxopt import matrix, solvers
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

solvers.options['show_progress'] = False


class SamplingPattern(ABC):
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._rng = np.random.RandomState(seed) if seed is not None else np.random

    @abstractmethod
    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        pass

    def reset_seed(self, seed: Optional[int] = None):
        self.seed = seed
        self._rng = np.random.RandomState(seed) if seed is not None else np.random


class RandomSampling(SamplingPattern):
    def __init__(self, seed: Optional[int] = 42):
        super().__init__(seed)

    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        mask = self._rng.random(shape) < ratio
        return mask.astype(np.float64)


class GaussianSampling(SamplingPattern):
    def __init__(self, seed: Optional[int] = 42):
        super().__init__(seed)

    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        h, w = shape
        y, x = np.mgrid[0:h, 0:w]
        cy, cx = h // 2, w // 2
        sigma = max(h, w) * 0.3
        gaussian = np.exp(-((x - cx)**2 + (y - cy)**2) / (2 * sigma**2))
        gaussian = gaussian / gaussian.max()
        noise = self._rng.normal(0, 0.05, gaussian.shape)
        gaussian_noisy = np.clip(gaussian + noise, 0, 1)
        threshold = np.percentile(gaussian_noisy, (1 - ratio) * 100)
        mask = gaussian_noisy > threshold
        return mask.astype(np.float64)


class BlockSampling(SamplingPattern):
    def __init__(self, block_size: int = 8, seed: Optional[int] = 42):
        super().__init__(seed)
        self.block_size = block_size

    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        h, w = shape
        mask = np.zeros(shape, dtype=np.float64)
        bh, bw = h // self.block_size, w // self.block_size
        num_blocks = int(bh * bw * ratio)
        block_indices = self._rng.choice(bh * bw, num_blocks, replace=False)
        for idx in block_indices:
            i, j = idx // bw, idx % bw
            mask[i*self.block_size:(i+1)*self.block_size,
                 j*self.block_size:(j+1)*self.block_size] = 1
        return mask


class VerticalLineSampling(SamplingPattern):
    def __init__(self, seed: Optional[int] = 42):
        super().__init__(seed)

    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        h, w = shape
        num_lines = int(w * ratio)
        selected_cols = self._rng.choice(w, num_lines, replace=False)
        mask = np.zeros(shape, dtype=np.float64)
        mask[:, selected_cols] = 1
        return mask


class HorizontalLineSampling(SamplingPattern):
    def __init__(self, seed: Optional[int] = 42):
        super().__init__(seed)

    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        h, w = shape
        num_lines = int(h * ratio)
        selected_rows = self._rng.choice(h, num_lines, replace=False)
        mask = np.zeros(shape, dtype=np.float64)
        mask[selected_rows, :] = 1
        return mask


class PoissonDiskSampling(SamplingPattern):
    def __init__(self, min_dist: float = 5, seed: Optional[int] = 42):
        super().__init__(seed)
        self.min_dist = min_dist

    def generate_mask(self, shape: Tuple[int, int], ratio: float) -> np.ndarray:
        h, w = shape
        mask = np.zeros(shape, dtype=np.float64)
        num_samples = int(h * w * ratio)
        samples = []
        grid_size = self.min_dist / np.sqrt(2)
        grid_h, grid_w = int(np.ceil(h / grid_size)), int(np.ceil(w / grid_size))
        grid = -np.ones((grid_h, grid_w), dtype=int)

        def get_grid_coords(y, x):
            return int(y // grid_size), int(x // grid_size)

        def is_valid(y, x):
            if y < 0 or y >= h or x < 0 or x >= w:
                return False
            gy, gx = get_grid_coords(y, x)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ngy, ngx = gy + dy, gx + dx
                    if 0 <= ngy < grid_h and 0 <= ngx < grid_w and grid[ngy, ngx] >= 0:
                        sy, sx = samples[grid[ngy, ngx]]
                        if (y - sy)**2 + (x - sx)**2 < self.min_dist**2:
                            return False
            return True

        first_y = self._rng.randint(0, h)
        first_x = self._rng.randint(0, w)
        samples.append((first_y, first_x))
        gy, gx = get_grid_coords(first_y, first_x)
        grid[gy, gx] = 0

        active = [0]
        while active and len(samples) < num_samples:
            idx = self._rng.randint(0, len(active))
            sample_idx = active[idx]
            sy, sx = samples[sample_idx]
            found = False
            for _ in range(30):
                angle = 2 * np.pi * self._rng.random()
                radius = self.min_dist * (1 + self._rng.random())
                ny, nx = sy + radius * np.sin(angle), sx + radius * np.cos(angle)
                ny, nx = int(ny), int(nx)
                if is_valid(ny, nx):
                    samples.append((ny, nx))
                    gy, gx = get_grid_coords(ny, nx)
                    grid[gy, gx] = len(samples) - 1
                    active.append(len(samples) - 1)
                    found = True
                    break
            if not found:
                active.pop(idx)

        for y, x in samples:
            if 0 <= y < h and 0 <= x < w:
                mask[y, x] = 1
        return mask


def _tv_gradient(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    grad_y = np.zeros_like(x)
    grad_x = np.zeros_like(x)
    grad_y[:-1, :] = x[1:, :] - x[:-1, :]
    grad_x[:, :-1] = x[:, 1:] - x[:, :-1]
    return grad_y, grad_x


def _tv_divergence(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    div = np.zeros_like(p)
    div[1:, :] += p[1:, :] - p[:-1, :]
    div[:, 1:] += q[:, 1:] - q[:, :-1]
    div[0, :] += p[0, :]
    div[:, 0] += q[:, 0]
    div[-1, :] -= p[-2, :]
    div[:, -1] -= q[:, -2]
    return div


def _soft_threshold(v: np.ndarray, threshold: float) -> np.ndarray:
    return np.sign(v) * np.maximum(np.abs(v) - threshold, 0)


class FISTAReconstructor:
    def __init__(self, tv_weight: float = 0.5, max_iter: int = 200, 
                 tol: float = 1e-5, time_limit: float = 10.0,
                 verbose: bool = False):
        self.tv_weight = tv_weight
        self.max_iter = max_iter
        self.tol = tol
        self.time_limit = time_limit
        self.verbose = verbose

    def _objective(self, x: np.ndarray, y: np.ndarray, mask: np.ndarray) -> float:
        data_term = 0.5 * np.sum(mask * (x - y)**2)
        tv_term = self.tv_weight * (np.sum(np.abs(np.diff(x, axis=0))) + 
                                    np.sum(np.abs(np.diff(x, axis=1))))
        return data_term + tv_term

    def _tv_denoise_chambolle_pock(self, x: np.ndarray, lambda_tv: float, 
                                    max_iter: int = 30) -> np.ndarray:
        h, w = x.shape
        p = np.zeros((h, w, 2))
        tau = 0.125
        sigma = 0.125
        theta = 1.0
        u = x.copy()
        u_bar = x.copy()
        
        for _ in range(max_iter):
            grad_u = np.zeros((h, w, 2))
            grad_u[:-1, :, 0] = u_bar[1:, :] - u_bar[:-1, :]
            grad_u[:, :-1, 1] = u_bar[:, 1:] - u_bar[:, :-1]
            
            p_new = p + sigma * grad_u
            norm_p = np.sqrt(p_new[:, :, 0]**2 + p_new[:, :, 1]**2)
            norm_p = np.maximum(norm_p, 1e-8)
            p = p_new / np.maximum(norm_p / lambda_tv, 1.0)[:, :, np.newaxis]
            
            div_p = np.zeros((h, w))
            div_p[1:, :] += p[1:, :, 0] - p[:-1, :, 0]
            div_p[:, 1:] += p[:, 1:, 1] - p[:, :-1, 1]
            div_p[0, :] += p[0, :, 0]
            div_p[:, 0] += p[:, 0, 1]
            div_p[-1, :] -= p[-2, :, 0]
            div_p[:, -1] -= p[:, -2, 1]
            
            u_new = (u + tau * div_p + tau * x) / (1 + tau)
            
            u_bar = u_new + theta * (u_new - u)
            u = u_new
        
        return u

    def _gradient_step(self, x: np.ndarray, y: np.ndarray, mask: np.ndarray, 
                      lipschitz: float) -> np.ndarray:
        grad = mask * (x - y)
        x_grad = x - grad / lipschitz
        x_prox = self._tv_denoise_chambolle_pock(x_grad, self.tv_weight / lipschitz)
        x_proj = y * mask + x_prox * (1 - mask)
        return np.clip(x_proj, 0, 255)

    def _estimate_lipschitz(self, y: np.ndarray, mask: np.ndarray) -> float:
        return float(np.max(mask) + 4 * self.tv_weight * 2)

    def reconstruct(self, measurements: np.ndarray, mask: np.ndarray,
                   x0: Optional[np.ndarray] = None) -> np.ndarray:
        start_time = time.time()
        h, w = measurements.shape
        y = measurements.astype(np.float64)
        
        if x0 is None:
            x = y.copy()
        else:
            x = x0.astype(np.float64)
        
        lipschitz = self._estimate_lipschitz(y, mask)
        
        x_prev = x.copy()
        t = 1.0
        best_x = x.copy()
        best_obj = self._objective(x, y, mask)
        
        for iteration in range(self.max_iter):
            elapsed = time.time() - start_time
            if elapsed > self.time_limit:
                if self.verbose:
                    print(f"Time limit reached at iteration {iteration}")
                break
            
            y_fista = x + (t - 1) / t * (x - x_prev)
            x_new = self._gradient_step(y_fista, y, mask, lipschitz)
            
            obj_new = self._objective(x_new, y, mask)
            
            if obj_new > best_obj:
                lipschitz *= 1.5
                x_new = self._gradient_step(x, y, mask, lipschitz)
                obj_new = self._objective(x_new, y, mask)
                t = 1.0
            
            if obj_new < best_obj:
                best_obj = obj_new
                best_x = x_new.copy()
            
            if iteration > 0:
                rel_change = np.linalg.norm(x_new - x) / (np.linalg.norm(x) + 1e-8)
                if rel_change < self.tol:
                    if self.verbose:
                        print(f"Converged at iteration {iteration}, rel_change = {rel_change:.6f}")
                    break
            
            t_next = (1 + np.sqrt(1 + 4 * t**2)) / 2
            x_prev = x.copy()
            x = x_new.copy()
            t = t_next
            
            if self.verbose and iteration % 20 == 0:
                elapsed = time.time() - start_time
                print(f"Iter {iteration:4d}: obj = {obj_new:.2f}, L = {lipschitz:.2f}, time = {elapsed:.2f}s")
        
        if self.verbose:
            total_time = time.time() - start_time
            print(f"FISTA completed: {iteration+1} iterations, {total_time:.2f}s, "
                  f"best_obj = {best_obj:.2f}")
        
        return best_x.astype(np.uint8)


class CSReconstructor:
    def __init__(self, tv_weight: float = 1e-2, max_iter: int = 100):
        self.tv_weight = tv_weight
        self.max_iter = max_iter

    def _tv_gradient(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        return _tv_gradient(x)

    def _tv_solve(self, y: np.ndarray, mask: np.ndarray, x0: Optional[np.ndarray] = None) -> np.ndarray:
        h, w = y.shape
        n = h * w
        if x0 is None:
            x0 = y.copy()
        x = x0.copy().flatten()
        y_flat = y.flatten()
        mask_flat = mask.flatten()
        known_indices = np.where(mask_flat > 0)[0]
        A = np.zeros((len(known_indices), n))
        for i, idx in enumerate(known_indices):
            A[i, idx] = 1
        P = matrix(np.eye(n) * 0.1)
        q = matrix(np.zeros(n))
        G_list = []
        h_list = []
        for i in range(h - 1):
            for j in range(w):
                idx = i * w + j
                idx_below = (i + 1) * w + j
                row = np.zeros(n)
                row[idx] = -1
                row[idx_below] = 1
                G_list.append(row)
                G_list.append(-row)
                h_list.append(self.tv_weight)
                h_list.append(self.tv_weight)
        for i in range(h):
            for j in range(w - 1):
                idx = i * w + j
                idx_right = i * w + j + 1
                row = np.zeros(n)
                row[idx] = -1
                row[idx_right] = 1
                G_list.append(row)
                G_list.append(-row)
                h_list.append(self.tv_weight)
                h_list.append(self.tv_weight)
        G = matrix(np.array(G_list))
        h_cvx = matrix(np.array(h_list))
        A_cvx = matrix(A)
        b_cvx = matrix(y_flat[known_indices])
        try:
            sol = solvers.qp(P, q, G, h_cvx, A_cvx, b_cvx)
            x_opt = np.array(sol['x']).flatten()
            return x_opt.reshape(h, w)
        except Exception as e:
            print(f"Optimization failed: {e}")
            return y

    def reconstruct(self, measurements: np.ndarray, mask: np.ndarray, 
                   x0: Optional[np.ndarray] = None) -> np.ndarray:
        h, w = measurements.shape
        if h > 128 or w > 128:
            print(f"Warning: Image size ({h}x{w}) may be too large for CVXOPT. Consider resizing.")
        result = self._tv_solve(measurements, mask, x0)
        result = np.clip(result, 0, 255)
        return result.astype(np.uint8)


class FFTReconstructor(CSReconstructor):
    def __init__(self, tv_weight: float = 1e-2, max_iter: int = 50):
        super().__init__(tv_weight, max_iter)

    def reconstruct(self, measurements: np.ndarray, mask: np.ndarray,
                   x0: Optional[np.ndarray] = None) -> np.ndarray:
        h, w = measurements.shape
        if x0 is None:
            x0 = measurements.copy()
        x = x0.copy().astype(np.float64)
        for _ in range(self.max_iter):
            x_known = measurements * mask + x * (1 - mask)
            grad_y, grad_x = self._tv_gradient(x)
            tv_norm = np.sqrt(grad_y**2 + grad_x**2 + 1e-8)
            div_y = np.zeros_like(grad_y)
            div_x = np.zeros_like(grad_x)
            div_y[1:, :] = grad_y[:-1, :] / tv_norm[:-1, :]
            div_x[:, 1:] = grad_x[:, :-1] / tv_norm[:, :-1]
            tv_grad = div_y + div_x
            x = x_known - self.tv_weight * tv_grad
            x = np.clip(x, 0, 255)
        return x.astype(np.uint8)


class QualityEvaluator:
    @staticmethod
    def psnr(original: np.ndarray, reconstructed: np.ndarray) -> float:
        mse = np.mean((original.astype(np.float64) - reconstructed.astype(np.float64))**2)
        if mse == 0:
            return float('inf')
        max_pixel = 255.0
        return 20 * np.log10(max_pixel / np.sqrt(mse))

    @staticmethod
    def ssim(original: np.ndarray, reconstructed: np.ndarray) -> float:
        C1 = (0.01 * 255)**2
        C2 = (0.03 * 255)**2
        img1 = original.astype(np.float64)
        img2 = reconstructed.astype(np.float64)
        kernel = cv2.getGaussianKernel(11, 1.5)
        window = np.outer(kernel, kernel.transpose())
        mu1 = cv2.filter2D(img1, -1, window)
        mu2 = cv2.filter2D(img2, -1, window)
        mu1_sq = mu1**2
        mu2_sq = mu2**2
        mu1_mu2 = mu1 * mu2
        sigma1_sq = cv2.filter2D(img1**2, -1, window) - mu1_sq
        sigma2_sq = cv2.filter2D(img2**2, -1, window) - mu2_sq
        sigma12 = cv2.filter2D(img1 * img2, -1, window) - mu1_mu2
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        return float(np.mean(ssim_map))

    @staticmethod
    def msssim(original: np.ndarray, reconstructed: np.ndarray, 
              levels: int = 5) -> float:
        img1 = original.astype(np.float64)
        img2 = reconstructed.astype(np.float64)
        weights = np.array([0.0448, 0.2856, 0.3001, 0.2363, 0.1333])
        if levels > len(weights):
            weights = np.concatenate([weights, [weights[-1]] * (levels - len(weights))])
        weights = weights[:levels] / np.sum(weights[:levels])
        
        msssim_values = []
        for level in range(levels):
            if level > 0:
                img1 = cv2.pyrDown(img1)
                img2 = cv2.pyrDown(img2)
            ssim_val = QualityEvaluator.ssim(
                img1.astype(np.uint8), 
                img2.astype(np.uint8)
            )
            msssim_values.append(ssim_val)
        
        msssim_values = np.array(msssim_values)
        return float(np.prod(msssim_values ** weights))

    @staticmethod
    def mae(original: np.ndarray, reconstructed: np.ndarray) -> float:
        return float(np.mean(np.abs(original.astype(np.float64) - 
                                   reconstructed.astype(np.float64))))

    @staticmethod
    def rmse(original: np.ndarray, reconstructed: np.ndarray) -> float:
        return float(np.sqrt(np.mean((original.astype(np.float64) - 
                                      reconstructed.astype(np.float64))**2)))

    @staticmethod
    def evaluate(original: np.ndarray, reconstructed: np.ndarray) -> Dict[str, float]:
        return {
            'PSNR': QualityEvaluator.psnr(original, reconstructed),
            'SSIM': QualityEvaluator.ssim(original, reconstructed),
            'MS_SSIM': QualityEvaluator.msssim(original, reconstructed),
            'MAE': QualityEvaluator.mae(original, reconstructed),
            'RMSE': QualityEvaluator.rmse(original, reconstructed)
        }

    @staticmethod
    def print_evaluation(metrics: Dict[str, float]):
        print("\n" + "=" * 50)
        print("  图像质量综合评估")
        print("=" * 50)
        print(f"  PSNR:      {metrics['PSNR']:.2f} dB")
        print(f"  SSIM:      {metrics['SSIM']:.4f}")
        print(f"  MS-SSIM:   {metrics['MS_SSIM']:.4f}")
        print(f"  MAE:       {metrics['MAE']:.4f}")
        print(f"  RMSE:      {metrics['RMSE']:.4f}")
        print("=" * 50 + "\n")


class ImageHandler:
    @staticmethod
    def load_image(path: str, grayscale: bool = True, 
                   target_size: Optional[Tuple[int, int]] = None) -> np.ndarray:
        if grayscale:
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        else:
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if img is None:
            raise ValueError(f"Could not load image from {path}")
        if target_size is not None:
            img = cv2.resize(img, target_size)
        return img

    @staticmethod
    def save_image(path: str, image: np.ndarray):
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(path, image)

    @staticmethod
    def normalize(image: np.ndarray) -> np.ndarray:
        return image.astype(np.float64) / 255.0

    @staticmethod
    def denormalize(image: np.ndarray) -> np.ndarray:
        return (np.clip(image, 0, 1) * 255).astype(np.uint8)


class CSImageProcessor:
    def __init__(self, sampling_pattern: SamplingPattern, 
                 reconstructor):
        self.sampling_pattern = sampling_pattern
        self.reconstructor = reconstructor

    def process_image(self, image: np.ndarray, sampling_ratio: float,
                     mask: Optional[np.ndarray] = None,
                     measure_time: bool = True) -> Dict:
        if measure_time:
            start_time = time.time()
        
        if mask is None:
            mask = self.sampling_pattern.generate_mask(image.shape[:2], sampling_ratio)
        
        if len(image.shape) == 3:
            measurements = np.zeros_like(image, dtype=np.float64)
            reconstructed = np.zeros_like(image)
            for c in range(image.shape[2]):
                measurements[:, :, c] = image[:, :, c] * mask
                reconstructed[:, :, c] = self.reconstructor.reconstruct(
                    measurements[:, :, c], mask)
        else:
            measurements = image * mask
            reconstructed = self.reconstructor.reconstruct(measurements, mask)
        
        quality = QualityEvaluator.evaluate(image, reconstructed)
        
        result = {
            'original': image,
            'mask': mask,
            'measurements': measurements,
            'reconstructed': reconstructed,
            'quality': quality,
            'sampling_ratio': sampling_ratio
        }
        
        if measure_time:
            result['processing_time'] = time.time() - start_time
        
        return result


class BatchProcessor:
    def __init__(self, input_dir: str, output_dir: str,
                 processor: CSImageProcessor):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.processor = processor
        os.makedirs(output_dir, exist_ok=True)

    def process_batch(self, sampling_ratios: List[float],
                     patterns: Optional[List[SamplingPattern]] = None,
                     file_pattern: str = '*.png') -> List[Dict]:
        if patterns is None:
            patterns = [self.processor.sampling_pattern]
        image_files = glob.glob(os.path.join(self.input_dir, file_pattern))
        image_files += glob.glob(os.path.join(self.input_dir, '*.jpg'))
        image_files += glob.glob(os.path.join(self.input_dir, '*.jpeg'))
        results = []
        for img_path in image_files:
            try:
                image = ImageHandler.load_image(img_path, grayscale=True)
                img_name = os.path.splitext(os.path.basename(img_path))[0]
                for pattern in patterns:
                    self.processor.sampling_pattern = pattern
                    pattern_name = pattern.__class__.__name__
                    for ratio in sampling_ratios:
                        result = self.processor.process_image(image, ratio)
                        result['image_name'] = img_name
                        result['pattern_name'] = pattern_name
                        out_name = f"{img_name}_{pattern_name}_ratio{ratio:.2f}.png"
                        out_path = os.path.join(self.output_dir, out_name)
                        ImageHandler.save_image(out_path, result['reconstructed'])
                        results.append(result)
                        proc_time = result.get('processing_time', 0)
                        print(f"Processed {img_name} with {pattern_name}, ratio={ratio:.2f}, "
                              f"PSNR={result['quality']['PSNR']:.2f}dB, "
                              f"SSIM={result['quality']['SSIM']:.4f}, "
                              f"time={proc_time:.2f}s")
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
        return results


class ResultVisualizer:
    @staticmethod
    def plot_single_result(result: Dict, save_path: Optional[str] = None):
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes[0, 0].imshow(result['original'], cmap='gray')
        axes[0, 0].set_title('Original Image')
        axes[0, 0].axis('off')
        axes[0, 1].imshow(result['mask'], cmap='gray')
        axes[0, 1].set_title(f"Sampling Mask (Ratio: {result['sampling_ratio']:.2%})")
        axes[0, 1].axis('off')
        axes[1, 0].imshow(result['measurements'], cmap='gray')
        axes[1, 0].set_title('Measurements')
        axes[1, 0].axis('off')
        axes[1, 1].imshow(result['reconstructed'], cmap='gray')
        q = result['quality']
        quality_text = (f"PSNR: {q['PSNR']:.2f}dB\n"
                       f"SSIM: {q['SSIM']:.4f}\n"
                       f"MS-SSIM: {q['MS_SSIM']:.4f}")
        if 'processing_time' in result:
            quality_text += f"\nTime: {result['processing_time']:.2f}s"
        axes[1, 1].set_title(f"Reconstructed\n{quality_text}")
        axes[1, 1].axis('off')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

    @staticmethod
    def plot_comparison(results: List[Dict], titles: List[str],
                       save_path: Optional[str] = None):
        n = len(results)
        fig, axes = plt.subplots(n, 4, figsize=(16, 4 * n))
        if n == 1:
            axes = axes.reshape(1, -1)
        for i, (result, title) in enumerate(zip(results, titles)):
            axes[i, 0].imshow(result['original'], cmap='gray')
            axes[i, 0].set_title(f'{title}\nOriginal')
            axes[i, 0].axis('off')
            axes[i, 1].imshow(result['mask'], cmap='gray')
            axes[i, 1].set_title(f"Mask ({result['sampling_ratio']:.2%})")
            axes[i, 1].axis('off')
            axes[i, 2].imshow(result['measurements'], cmap='gray')
            axes[i, 2].set_title('Measurements')
            axes[i, 2].axis('off')
            axes[i, 3].imshow(result['reconstructed'], cmap='gray')
            q = result['quality']
            quality_text = (f"PSNR: {q['PSNR']:.2f}dB\n"
                           f"SSIM: {q['SSIM']:.4f}\n"
                           f"MS-SSIM: {q['MS_SSIM']:.4f}")
            if 'processing_time' in result:
                quality_text += f"\nTime: {result['processing_time']:.2f}s"
            axes[i, 3].set_title(f"Reconstructed\n{quality_text}")
            axes[i, 3].axis('off')
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

    @staticmethod
    def plot_quality_comparison(results: List[Dict], save_path: Optional[str] = None):
        ratios = []
        psnrs = []
        ssims = []
        msssims = []
        times = []
        pattern_names = []
        for result in results:
            ratios.append(result['sampling_ratio'])
            psnrs.append(result['quality']['PSNR'])
            ssims.append(result['quality']['SSIM'])
            msssims.append(result['quality']['MS_SSIM'])
            times.append(result.get('processing_time', 0))
            pattern_names.append(result.get('pattern_name', 'Unknown'))
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        unique_patterns = list(set(pattern_names))
        for pattern in unique_patterns:
            pattern_indices = [i for i, p in enumerate(pattern_names) if p == pattern]
            pattern_ratios = [ratios[i] for i in pattern_indices]
            pattern_psnrs = [psnrs[i] for i in pattern_indices]
            pattern_ssims = [ssims[i] for i in pattern_indices]
            pattern_msssims = [msssims[i] for i in pattern_indices]
            pattern_times = [times[i] for i in pattern_indices]
            sorted_indices = np.argsort(pattern_ratios)
            axes[0, 0].plot([pattern_ratios[i] for i in sorted_indices],
                          [pattern_psnrs[i] for i in sorted_indices],
                          'o-', label=pattern, markersize=6)
            axes[0, 1].plot([pattern_ratios[i] for i in sorted_indices],
                          [pattern_ssims[i] for i in sorted_indices],
                          'o-', label=pattern, markersize=6)
            axes[1, 0].plot([pattern_ratios[i] for i in sorted_indices],
                          [pattern_msssims[i] for i in sorted_indices],
                          'o-', label=pattern, markersize=6)
            axes[1, 1].plot([pattern_ratios[i] for i in sorted_indices],
                          [pattern_times[i] for i in sorted_indices],
                          'o-', label=pattern, markersize=6)
        axes[0, 0].set_xlabel('Sampling Ratio')
        axes[0, 0].set_ylabel('PSNR (dB)')
        axes[0, 0].set_title('PSNR vs Sampling Ratio')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].legend()
        axes[0, 1].set_xlabel('Sampling Ratio')
        axes[0, 1].set_ylabel('SSIM')
        axes[0, 1].set_title('SSIM vs Sampling Ratio')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].legend()
        axes[1, 0].set_xlabel('Sampling Ratio')
        axes[1, 0].set_ylabel('MS-SSIM')
        axes[1, 0].set_title('MS-SSIM vs Sampling Ratio')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].legend()
        axes[1, 1].set_xlabel('Sampling Ratio')
        axes[1, 1].set_ylabel('Processing Time (s)')
        axes[1, 1].set_title('Processing Time vs Sampling Ratio')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].legend()
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

    @staticmethod
    def plot_ssim_map(original: np.ndarray, reconstructed: np.ndarray,
                     save_path: Optional[str] = None):
        C1 = (0.01 * 255)**2
        C2 = (0.03 * 255)**2
        img1 = original.astype(np.float64)
        img2 = reconstructed.astype(np.float64)
        kernel = cv2.getGaussianKernel(11, 1.5)
        window = np.outer(kernel, kernel.transpose())
        mu1 = cv2.filter2D(img1, -1, window)
        mu2 = cv2.filter2D(img2, -1, window)
        mu1_sq = mu1**2
        mu2_sq = mu2**2
        mu1_mu2 = mu1 * mu2
        sigma1_sq = cv2.filter2D(img1**2, -1, window) - mu1_sq
        sigma2_sq = cv2.filter2D(img2**2, -1, window) - mu2_sq
        sigma12 = cv2.filter2D(img1 * img2, -1, window) - mu1_mu2
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        axes[0].imshow(original, cmap='gray')
        axes[0].set_title('Original')
        axes[0].axis('off')
        axes[1].imshow(reconstructed, cmap='gray')
        axes[1].set_title('Reconstructed')
        axes[1].axis('off')
        im = axes[2].imshow(ssim_map, cmap='jet', vmin=0, vmax=1)
        axes[2].set_title(f'SSIM Map (Mean: {np.mean(ssim_map):.4f})')
        axes[2].axis('off')
        plt.colorbar(im, ax=axes[2], fraction=0.046, pad=0.04)
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()


def get_sampling_patterns(seed: int = 42) -> Dict[str, SamplingPattern]:
    return {
        'random': RandomSampling(seed=seed),
        'gaussian': GaussianSampling(seed=seed),
        'block': BlockSampling(block_size=8, seed=seed),
        'vertical': VerticalLineSampling(seed=seed),
        'horizontal': HorizontalLineSampling(seed=seed),
        'poisson': PoissonDiskSampling(min_dist=4, seed=seed)
    }


# ============================================================================
# 深度压缩感知 (Deep Compressed Sensing)
# ============================================================================

class ReLULayer:
    def __init__(self):
        pass

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.output = np.maximum(0, x)
        return self.output

    def backward(self, grad_output: np.ndarray) -> np.ndarray:
        return grad_output * (self.output > 0)


class Conv2DLayer:
    def __init__(self, in_channels: int, out_channels: int, 
                 kernel_size: int = 3, stride: int = 1, padding: int = 1):
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.stride = stride
        self.padding = padding
        scale = np.sqrt(2.0 / (in_channels * kernel_size * kernel_size))
        self.weights = np.random.randn(out_channels, in_channels, kernel_size, kernel_size) * scale
        self.bias = np.zeros(out_channels)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.input = x
        batch_size, in_channels, h, w = x.shape
        out_h = (h + 2 * self.padding - self.kernel_size) // self.stride + 1
        out_w = (w + 2 * self.padding - self.kernel_size) // self.stride + 1
        
        x_pad = np.pad(x, ((0, 0), (0, 0), (self.padding, self.padding), 
                         (self.padding, self.padding)), mode='reflect')
        
        output = np.zeros((batch_size, self.out_channels, out_h, out_w))
        for i in range(out_h):
            for j in range(out_w):
                x_slice = x_pad[:, :, i*self.stride:i*self.stride+self.kernel_size,
                               j*self.stride:j*self.stride+self.kernel_size]
                for k in range(self.out_channels):
                    output[:, k, i, j] = np.sum(x_slice * self.weights[k], axis=(1, 2, 3))
        return output + self.bias[np.newaxis, :, np.newaxis, np.newaxis]

    def backward(self, grad_output: np.ndarray) -> np.ndarray:
        batch_size, _, out_h, out_w = grad_output.shape
        grad_input = np.zeros_like(self.input)
        grad_weights = np.zeros_like(self.weights)
        grad_bias = np.sum(grad_output, axis=(0, 2, 3))
        
        x_pad = np.pad(self.input, ((0, 0), (0, 0), (self.padding, self.padding),
                             (self.padding, self.padding)), mode='reflect')
        grad_input_pad = np.zeros_like(x_pad)
        
        for i in range(out_h):
            for j in range(out_w):
                x_slice = x_pad[:, :, i*self.stride:i*self.stride+self.kernel_size,
                               j*self.stride:j*self.stride+self.kernel_size]
                for k in range(self.out_channels):
                    grad = grad_output[:, k, i, j][:, np.newaxis, np.newaxis, np.newaxis]
                    grad_weights[k] += np.sum(x_slice * grad, axis=0)
                    grad_input_pad[:, :, i*self.stride:i*self.stride+self.kernel_size,
                                  j*self.stride:j*self.stride+self.kernel_size] += \
                        self.weights[k] * grad
        
        if self.padding > 0:
            grad_input = grad_input_pad[:, :, self.padding:-self.padding, self.padding:-self.padding]
        else:
            grad_input = grad_input_pad
        
        self.grad_weights = grad_weights
        self.grad_bias = grad_bias
        return grad_input


class BatchNorm2DLayer:
    def __init__(self, num_channels: int, eps: float = 1e-5):
        self.num_channels = num_channels
        self.eps = eps
        self.gamma = np.ones(num_channels)
        self.beta = np.zeros(num_channels)
        self.running_mean = np.zeros(num_channels)
        self.running_var = np.ones(num_channels)
        self.momentum = 0.1
        self.training = True

    def forward(self, x: np.ndarray) -> np.ndarray:
        self.input = x
        if self.training:
            mean = np.mean(x, axis=(0, 2, 3))
            var = np.var(x, axis=(0, 2, 3))
            self.running_mean = (1 - self.momentum) * self.running_mean + self.momentum * mean
            self.running_var = (1 - self.momentum) * self.running_var + self.momentum * var
            self.mean = mean
            self.var = var
        else:
            mean = self.running_mean
            var = self.running_var
        
        x_norm = (x - mean[np.newaxis, :, np.newaxis, np.newaxis]) / \
                 np.sqrt(var[np.newaxis, :, np.newaxis, np.newaxis] + self.eps)
        self.x_norm = x_norm
        return self.gamma[np.newaxis, :, np.newaxis, np.newaxis] * x_norm + \
               self.beta[np.newaxis, :, np.newaxis, np.newaxis]

    def backward(self, grad_output: np.ndarray) -> np.ndarray:
        batch_size = grad_output.shape[0]
        dgamma = np.sum(grad_output * self.x_norm, axis=(0, 2, 3))
        dbeta = np.sum(grad_output, axis=(0, 2, 3))
        
        dx_norm = grad_output * self.gamma[np.newaxis, :, np.newaxis, np.newaxis]
        dvar = np.sum(dx_norm * (self.input - self.mean[np.newaxis, :, np.newaxis, np.newaxis]),
                      axis=(0, 2, 3)) * -0.5 / np.power(self.var + self.eps, 1.5)
        dmean = np.sum(dx_norm, axis=(0, 2, 3)) * -1.0 / np.sqrt(self.var + self.eps) + \
                dvar * np.mean(-2.0 * (self.input - self.mean[np.newaxis, :, np.newaxis, np.newaxis]),
                              axis=(0, 2, 3))
        dx = dx_norm / np.sqrt(self.var + self.eps)[np.newaxis, :, np.newaxis, np.newaxis] + \
             dvar[np.newaxis, :, np.newaxis, np.newaxis] * 2.0 / batch_size * \
             (self.input - self.mean[np.newaxis, :, np.newaxis, np.newaxis]) + \
             dmean[np.newaxis, :, np.newaxis, np.newaxis] / batch_size
        
        self.grad_gamma = dgamma
        self.grad_beta = dbeta
        return dx


class ResidualBlock:
    def __init__(self, channels: int, kernel_size: int = 3):
        self.conv1 = Conv2DLayer(channels, channels, kernel_size, padding=1)
        self.bn1 = BatchNorm2DLayer(channels)
        self.relu1 = ReLULayer()
        self.conv2 = Conv2DLayer(channels, channels, kernel_size, padding=1)
        self.bn2 = BatchNorm2DLayer(channels)
        self.relu2 = ReLULayer()

    def train(self):
        self.bn1.training = True
        self.bn2.training = True

    def eval(self):
        self.bn1.training = False
        self.bn2.training = False

    def forward(self, x: np.ndarray) -> np.ndarray:
        residual = x
        out = self.conv1.forward(x)
        out = self.bn1.forward(out)
        out = self.relu1.forward(out)
        out = self.conv2.forward(out)
        out = self.bn2.forward(out)
        out += residual
        out = self.relu2.forward(out)
        return out

    def backward(self, grad_output: np.ndarray) -> np.ndarray:
        grad = self.relu2.backward(grad_output)
        grad_residual = grad.copy()
        grad = self.bn2.backward(grad)
        grad = self.conv2.backward(grad)
        grad = self.relu1.backward(grad)
        grad = self.bn1.backward(grad)
        grad = self.conv1.backward(grad)
        grad += grad_residual
        return grad


class DeepCSReconstructor:
    def __init__(self, in_channels: int = 1, base_channels: int = 32, 
                 num_res_blocks: int = 4, learning_rate: float = 1e-4):
        self.in_channels = in_channels
        self.base_channels = base_channels
        self.num_res_blocks = num_res_blocks
        self.learning_rate = learning_rate
        self.training = True
        
        self.conv_in = Conv2DLayer(in_channels, base_channels, kernel_size=3, padding=1)
        self.bn_in = BatchNorm2DLayer(base_channels)
        self.relu_in = ReLULayer()
        
        self.res_blocks = []
        for _ in range(num_res_blocks):
            self.res_blocks.append(ResidualBlock(base_channels))
        
        self.conv_out = Conv2DLayer(base_channels, in_channels, kernel_size=3, padding=1)

    def train(self):
        self.training = True
        self.bn_in.training = True
        for block in self.res_blocks:
            block.train()

    def eval(self):
        self.training = False
        self.bn_in.training = False
        for block in self.res_blocks:
            block.eval()

    def forward(self, x: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
        if x.ndim == 2:
            x = x[np.newaxis, np.newaxis, :, :]
        elif x.ndim == 3:
            x = x.transpose(2, 0, 1)[np.newaxis, :, :, :]
        
        x = x.astype(np.float64) / 255.0
        
        out = self.conv_in.forward(x)
        out = self.bn_in.forward(out)
        out = self.relu_in.forward(out)
        
        for block in self.res_blocks:
            out = block.forward(out)
        
        out = self.conv_out.forward(out)
        
        if mask is not None:
            if mask.ndim == 2:
                mask = mask[np.newaxis, np.newaxis, :, :]
            out = x * mask + out * (1 - mask)
        
        out = np.clip(out, 0, 1) * 255.0
        return out.astype(np.uint8)

    def train_step(self, x: np.ndarray, y: np.ndarray, mask: np.ndarray) -> float:
        if x.ndim == 2:
            x = x[np.newaxis, np.newaxis, :, :]
            y = y[np.newaxis, np.newaxis, :, :]
            mask = mask[np.newaxis, np.newaxis, :, :]
        
        x = x.astype(np.float64) / 255.0
        y = y.astype(np.float64) / 255.0
        
        out = self.conv_in.forward(x)
        out = self.bn_in.forward(out)
        out = self.relu_in.forward(out)
        
        for block in self.res_blocks:
            out = block.forward(out)
        
        out = self.conv_out.forward(out)
        out = x * mask + out * (1 - mask)
        out = np.clip(out, 0, 1)
        
        loss = 0.5 * np.mean((out - y)**2)
        grad_output = (out - y) / out.size
        
        grad_output = grad_output * (1 - mask)
        
        grad = self.conv_out.backward(grad_output)
        
        for block in reversed(self.res_blocks):
            grad = block.backward(grad)
        
        grad = self.relu_in.backward(grad)
        grad = self.bn_in.backward(grad)
        grad = self.conv_in.backward(grad)
        
        self._update_weights()
        
        return loss

    def _update_weights(self):
        self.conv_in.weights -= self.learning_rate * self.conv_in.grad_weights
        self.conv_in.bias -= self.learning_rate * self.conv_in.grad_bias
        self.bn_in.gamma -= self.learning_rate * self.bn_in.grad_gamma
        self.bn_in.beta -= self.learning_rate * self.bn_in.grad_beta
        
        for block in self.res_blocks:
            block.conv1.weights -= self.learning_rate * block.conv1.grad_weights
            block.conv1.bias -= self.learning_rate * block.conv1.grad_bias
            block.bn1.gamma -= self.learning_rate * block.bn1.grad_gamma
            block.bn1.beta -= self.learning_rate * block.bn1.grad_beta
            block.conv2.weights -= self.learning_rate * block.conv2.grad_weights
            block.conv2.bias -= self.learning_rate * block.conv2.grad_bias
            block.bn2.gamma -= self.learning_rate * block.bn2.grad_gamma
            block.bn2.beta -= self.learning_rate * block.bn2.grad_beta

    def reconstruct(self, measurements: np.ndarray, mask: np.ndarray,
                   x0: Optional[np.ndarray] = None,
                   fista_init: bool = True,
                   fista_iter: int = 20) -> np.ndarray:
        if fista_init and x0 is None:
            fista = FISTAReconstructor(tv_weight=0.5, max_iter=fista_iter, time_limit=2.0)
            x0 = fista.reconstruct(measurements, mask)
        
        if x0 is not None:
            x0 = x0.astype(np.float64)
            x0 = x0[np.newaxis, np.newaxis, :, :] if x0.ndim == 2 else x0
        
        self.eval()
        result = self.forward(measurements, mask)
        
        if result.shape[0] == 1:
            result = result[0]
        if result.shape[0] == 1:
            result = result[0]
        elif result.shape[-1] not in [1, 3]:
            result = result.transpose(1, 2, 0)
        
        return result.astype(np.uint8)


class DeepCSProcessor:
    def __init__(self, in_channels: int = 1, base_channels: int = 32,
                 num_res_blocks: int = 4, learning_rate: float = 1e-4):
        self.model = DeepCSReconstructor(in_channels, base_channels, 
                                        num_res_blocks, learning_rate)
        self.fista = FISTAReconstructor(tv_weight=0.5, max_iter=50, time_limit=10.0)
        self.is_trained = False

    def pretrain(self, images: List[np.ndarray], masks: List[np.ndarray],
                 num_epochs: int = 10, verbose: bool = True) -> List[float]:
        self.model.train()
        losses = []
        
        for epoch in range(num_epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            for img, mask in zip(images, masks):
                measurements = img * mask
                loss = self.model.train_step(measurements, img, mask)
                epoch_loss += loss
                num_batches += 1
            
            avg_loss = epoch_loss / max(num_batches, 1)
            losses.append(avg_loss)
            
            if verbose and (epoch + 1) % 5 == 0:
                print(f"Epoch {epoch+1}/{num_epochs}, Avg Loss: {avg_loss:.6f}")
        
        self.is_trained = True
        self.model.eval()
        return losses

    def process(self, image: np.ndarray, sampling_ratio: float,
                pattern: SamplingPattern,
                use_fista_init: bool = True) -> Dict:
        mask = pattern.generate_mask(image.shape[:2], sampling_ratio)
        measurements = image * mask
        
        start_time = time.time()
        reconstructed = self.model.reconstruct(measurements, mask, 
                                              fista_init=use_fista_init)
        proc_time = time.time() - start_time
        
        quality = QualityEvaluator.evaluate(image, reconstructed)
        
        return {
            'original': image,
            'mask': mask,
            'measurements': measurements,
            'reconstructed': reconstructed,
            'quality': quality,
            'sampling_ratio': sampling_ratio,
            'processing_time': proc_time,
            'method': 'DeepCS'
        }

    def process_with_fista(self, image: np.ndarray, sampling_ratio: float,
                          pattern: SamplingPattern) -> Dict:
        mask = pattern.generate_mask(image.shape[:2], sampling_ratio)
        measurements = image * mask
        
        start_time = time.time()
        reconstructed = self.fista.reconstruct(measurements, mask)
        proc_time = time.time() - start_time
        
        quality = QualityEvaluator.evaluate(image, reconstructed)
        
        return {
            'original': image,
            'mask': mask,
            'measurements': measurements,
            'reconstructed': reconstructed,
            'quality': quality,
            'sampling_ratio': sampling_ratio,
            'processing_time': proc_time,
            'method': 'FISTA'
        }


# ============================================================================
# 视频压缩感知 (Video Compressed Sensing)
# ============================================================================

class VideoCSReconstructor:
    def __init__(self, tv_weight: float = 0.5, temporal_weight: float = 0.3,
                 max_iter: int = 100, time_limit: float = 10.0,
                 motion_estimation: bool = True):
        self.tv_weight = tv_weight
        self.temporal_weight = temporal_weight
        self.max_iter = max_iter
        self.time_limit = time_limit
        self.motion_estimation = motion_estimation

    def _estimate_motion(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
        if not self.motion_estimation:
            return prev_frame
        
        prev = prev_frame.astype(np.float32)
        curr = curr_frame.astype(np.float32)
        
        flow = cv2.calcOpticalFlowFarneback(
            prev, curr, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        h, w = prev.shape
        y, x = np.mgrid[0:h, 0:w]
        new_x = (x + flow[:, :, 0]).astype(np.float32)
        new_y = (y + flow[:, :, 1]).astype(np.float32)
        
        predicted = cv2.remap(prev, new_x, new_y, cv2.INTER_LINEAR)
        return predicted.astype(np.float64)

    def _temporal_gradient(self, x: np.ndarray, prev_pred: np.ndarray,
                          motion_mask: np.ndarray) -> np.ndarray:
        if prev_pred is None:
            return np.zeros_like(x)
        return self.temporal_weight * (x - prev_pred) * motion_mask

    def reconstruct_frame(self, measurements: np.ndarray, mask: np.ndarray,
                         prev_frame: Optional[np.ndarray] = None,
                         x0: Optional[np.ndarray] = None) -> Dict:
        start_time = time.time()
        h, w = measurements.shape
        y = measurements.astype(np.float64)
        
        if x0 is None:
            if prev_frame is not None:
                x = self._estimate_motion(prev_frame, y)
            else:
                x = y.copy()
        else:
            x = x0.astype(np.float64)
        
        if prev_frame is not None:
            prev_pred = self._estimate_motion(prev_frame, x)
            diff = np.abs(x - prev_pred)
            motion_mask = (diff > np.percentile(diff, 70)).astype(np.float64)
        else:
            prev_pred = None
            motion_mask = np.ones_like(x)
        
        x_prev = x.copy()
        t = 1.0
        best_x = x.copy()
        best_obj = float('inf')
        lipschitz = 1.0 + self.temporal_weight
        
        obj_history = []
        
        for iteration in range(self.max_iter):
            elapsed = time.time() - start_time
            if elapsed > self.time_limit:
                break
            
            y_fista = x + (t - 1) / t * (x - x_prev)
            
            grad_data = mask * (y_fista - y)
            grad_temp = self._temporal_gradient(y_fista, prev_pred, motion_mask)
            grad = grad_data + grad_temp
            
            x_grad = y_fista - grad / lipschitz
            
            grad_y, grad_x = _tv_gradient(x_grad)
            tv_norm = np.sqrt(grad_y**2 + grad_x**2 + 1e-8)
            div_y = np.zeros_like(grad_y)
            div_x = np.zeros_like(grad_x)
            div_y[1:, :] = grad_y[:-1, :] / tv_norm[:-1, :]
            div_x[:, 1:] = grad_x[:, :-1] / tv_norm[:, :-1]
            tv_grad = div_y + div_x
            
            x_prox = x_grad - self.tv_weight * tv_grad / lipschitz
            
            x_proj = y * mask + x_prox * (1 - mask)
            x_new = np.clip(x_proj, 0, 255)
            
            obj = 0.5 * np.sum(mask * (x_new - y)**2) + \
                  self.tv_weight * (np.sum(np.abs(np.diff(x_new, axis=0))) +
                                    np.sum(np.abs(np.diff(x_new, axis=1))))
            if prev_pred is not None:
                obj += 0.5 * self.temporal_weight * \
                       np.sum(motion_mask * (x_new - prev_pred)**2)
            
            obj_history.append(obj)
            
            if obj < best_obj:
                best_obj = obj
                best_x = x_new.copy()
            
            if iteration > 0 and abs(obj_history[-2] - obj) < 1e-4 * abs(obj_history[-2]):
                break
            
            t_next = (1 + np.sqrt(1 + 4 * t**2)) / 2
            x_prev = x.copy()
            x = x_new.copy()
            t = t_next
        
        total_time = time.time() - start_time
        
        quality = None
        if prev_frame is not None:
            quality = QualityEvaluator.evaluate(prev_frame, best_x.astype(np.uint8))
        
        return {
            'reconstructed': best_x.astype(np.uint8),
            'predicted_from_prev': prev_pred.astype(np.uint8) if prev_pred is not None else None,
            'motion_mask': motion_mask,
            'processing_time': total_time,
            'iterations': iteration + 1,
            'final_objective': best_obj,
            'quality': quality
        }


class VideoCSProcessor:
    def __init__(self, tv_weight: float = 0.5, temporal_weight: float = 0.3,
                 max_iter: int = 100, time_limit: float = 10.0):
        self.reconstructor = VideoCSReconstructor(
            tv_weight, temporal_weight, max_iter, time_limit)
        self.frames = []
        self.results = []

    def load_video(self, video_path: str, max_frames: int = 10,
                   target_size: Optional[Tuple[int, int]] = None,
                   grayscale: bool = True) -> List[np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        frames = []
        frame_count = 0
        
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if grayscale:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            if target_size is not None:
                frame = cv2.resize(frame, target_size)
            
            frames.append(frame)
            frame_count += 1
        
        cap.release()
        self.frames = frames
        return frames

    def generate_synthetic_video(self, num_frames: int = 10,
                                 size: Tuple[int, int] = (64, 64),
                                 motion_type: str = 'translation') -> List[np.ndarray]:
        frames = []
        h, w = size
        
        base_frame = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(base_frame, (w//4, h//2), min(w, h)//8, 200, -1)
        cv2.rectangle(base_frame, (w//2, h//4), (3*w//4, 3*h//4), 150, -1)
        base_frame = cv2.GaussianBlur(base_frame.astype(np.float32), (5, 5), 1.0).astype(np.uint8)
        
        for i in range(num_frames):
            frame = base_frame.copy()
            
            if motion_type == 'translation':
                offset_x = int(10 * np.sin(2 * np.pi * i / num_frames))
                offset_y = int(5 * np.cos(2 * np.pi * i / num_frames))
                M = np.float32([[1, 0, offset_x], [0, 1, offset_y]])
                frame = cv2.warpAffine(frame, M, (w, h))
            elif motion_type == 'scaling':
                scale = 1.0 + 0.2 * np.sin(2 * np.pi * i / num_frames)
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, 0, scale)
                frame = cv2.warpAffine(frame, M, (w, h))
            elif motion_type == 'rotation':
                angle = 360 * i / num_frames
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                frame = cv2.warpAffine(frame, M, (w, h))
            
            frames.append(frame)
        
        self.frames = frames
        return frames

    def process_video(self, frames: List[np.ndarray], sampling_ratio: float,
                     pattern: SamplingPattern) -> List[Dict]:
        results = []
        prev_reconstructed = None
        
        for idx, frame in enumerate(frames):
            mask = pattern.generate_mask(frame.shape[:2], sampling_ratio)
            measurements = frame * mask
            
            if idx == 0:
                result = self.reconstructor.reconstruct_frame(
                    measurements, mask, prev_frame=None)
                result['frame_index'] = idx
                result['original'] = frame
                result['mask'] = mask
                result['measurements'] = measurements
                result['sampling_ratio'] = sampling_ratio
                result['quality'] = QualityEvaluator.evaluate(frame, result['reconstructed'])
                prev_reconstructed = result['reconstructed']
            else:
                result = self.reconstructor.reconstruct_frame(
                    measurements, mask, prev_frame=prev_reconstructed)
                result['frame_index'] = idx
                result['original'] = frame
                result['mask'] = mask
                result['measurements'] = measurements
                result['sampling_ratio'] = sampling_ratio
                result['quality'] = QualityEvaluator.evaluate(frame, result['reconstructed'])
                prev_reconstructed = result['reconstructed']
            
            results.append(result)
            
            if idx % 5 == 0 or idx == len(frames) - 1:
                q = result['quality']
                print(f"Frame {idx}: PSNR={q['PSNR']:.2f}dB, SSIM={q['SSIM']:.4f}, "
                      f"time={result['processing_time']:.2f}s")
        
        self.results = results
        return results

    def visualize_video_results(self, results: List[Dict], 
                                save_path: Optional[str] = None,
                                max_frames: int = 5):
        num_display = min(max_frames, len(results))
        fig, axes = plt.subplots(num_display, 5, figsize=(20, 4 * num_display))
        
        if num_display == 1:
            axes = axes.reshape(1, -1)
        
        for i in range(num_display):
            result = results[i]
            axes[i, 0].imshow(result['original'], cmap='gray')
            axes[i, 0].set_title(f'Frame {i} - Original')
            axes[i, 0].axis('off')
            
            axes[i, 1].imshow(result['measurements'], cmap='gray')
            axes[i, 1].set_title(f'Measurements ({result["sampling_ratio"]:.0%})')
            axes[i, 1].axis('off')
            
            axes[i, 2].imshow(result['reconstructed'], cmap='gray')
            q = result['quality']
            axes[i, 2].set_title(f'Reconstructed\nPSNR={q["PSNR"]:.1f}dB, SSIM={q["SSIM"]:.3f}')
            axes[i, 2].axis('off')
            
            if result['predicted_from_prev'] is not None:
                axes[i, 3].imshow(result['predicted_from_prev'], cmap='gray')
                axes[i, 3].set_title('Motion Prediction')
            else:
                axes[i, 3].text(0.5, 0.5, 'First Frame\nNo Prediction', 
                               ha='center', va='center', transform=axes[i, 3].transAxes)
            axes[i, 3].axis('off')
            
            axes[i, 4].imshow(result['motion_mask'], cmap='hot')
            axes[i, 4].set_title('Motion Mask')
            axes[i, 4].axis('off')
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

    def plot_video_quality(self, results: List[Dict],
                          save_path: Optional[str] = None):
        frames = [r['frame_index'] for r in results]
        psnrs = [r['quality']['PSNR'] for r in results]
        ssims = [r['quality']['SSIM'] for r in results]
        msssims = [r['quality']['MS_SSIM'] for r in results]
        times = [r['processing_time'] for r in results]
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        axes[0, 0].plot(frames, psnrs, 'o-', linewidth=2, markersize=6)
        axes[0, 0].set_xlabel('Frame Index')
        axes[0, 0].set_ylabel('PSNR (dB)')
        axes[0, 0].set_title('PSNR across Frames')
        axes[0, 0].grid(True, alpha=0.3)
        
        axes[0, 1].plot(frames, ssims, 'o-', linewidth=2, markersize=6, color='orange')
        axes[0, 1].set_xlabel('Frame Index')
        axes[0, 1].set_ylabel('SSIM')
        axes[0, 1].set_title('SSIM across Frames')
        axes[0, 1].grid(True, alpha=0.3)
        
        axes[1, 0].plot(frames, msssims, 'o-', linewidth=2, markersize=6, color='green')
        axes[1, 0].set_xlabel('Frame Index')
        axes[1, 0].set_ylabel('MS-SSIM')
        axes[1, 0].set_title('MS-SSIM across Frames')
        axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].plot(frames, times, 'o-', linewidth=2, markersize=6, color='red')
        axes[1, 1].set_xlabel('Frame Index')
        axes[1, 1].set_ylabel('Processing Time (s)')
        axes[1, 1].set_title('Processing Time per Frame')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()


# ============================================================================
# 自适应采样率 (Adaptive Sampling Rate)
# ============================================================================

class TextureAnalyzer:
    @staticmethod
    def compute_laplacian_variance(image: np.ndarray) -> np.ndarray:
        laplacian = cv2.Laplacian(image.astype(np.float32), cv2.CV_32F)
        return np.abs(laplacian)

    @staticmethod
    def compute_sobel_magnitude(image: np.ndarray) -> np.ndarray:
        sobel_x = cv2.Sobel(image.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(image.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
        return np.sqrt(sobel_x**2 + sobel_y**2)

    @staticmethod
    def compute_local_variance(image: np.ndarray, kernel_size: int = 11) -> np.ndarray:
        img = image.astype(np.float32)
        mean = cv2.blur(img, (kernel_size, kernel_size))
        mean_sq = cv2.blur(img**2, (kernel_size, kernel_size))
        variance = mean_sq - mean**2
        return np.maximum(variance, 0)

    @staticmethod
    def compute_texture_map(image: np.ndarray, 
                           alpha: float = 0.5, beta: float = 0.5) -> np.ndarray:
        laplacian = TextureAnalyzer.compute_laplacian_variance(image)
        sobel = TextureAnalyzer.compute_sobel_magnitude(image)
        variance = TextureAnalyzer.compute_local_variance(image)
        
        texture = alpha * laplacian + beta * sobel + (1 - alpha - beta) * variance
        texture = (texture - texture.min()) / (texture.max() - texture.min() + 1e-8)
        return texture


class AdaptiveSampling(SamplingPattern):
    def __init__(self, base_ratio: float = 0.3, 
                 min_ratio: float = 0.05, max_ratio: float = 0.8,
                 block_size: int = 8, seed: Optional[int] = 42):
        super().__init__(seed)
        self.base_ratio = base_ratio
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.block_size = block_size

    def _compute_adaptive_ratios(self, image: np.ndarray) -> np.ndarray:
        texture_map = TextureAnalyzer.compute_texture_map(image)
        
        h, w = image.shape
        bh, bw = h // self.block_size, w // self.block_size
        block_ratios = np.zeros((bh, bw))
        
        for i in range(bh):
            for j in range(bw):
                block_texture = texture_map[i*self.block_size:(i+1)*self.block_size,
                                           j*self.block_size:(j+1)*self.block_size]
                avg_texture = np.mean(block_texture)
                ratio = self.min_ratio + (self.max_ratio - self.min_ratio) * avg_texture
                block_ratios[i, j] = ratio
        
        total_samples = np.sum(block_ratios) * self.block_size**2
        target_samples = self.base_ratio * h * w
        scale_factor = target_samples / (total_samples + 1e-8)
        block_ratios = np.clip(block_ratios * scale_factor, 
                              self.min_ratio, self.max_ratio)
        
        return block_ratios

    def generate_mask(self, shape: Tuple[int, int], ratio: float,
                     image: Optional[np.ndarray] = None) -> np.ndarray:
        h, w = shape
        mask = np.zeros((h, w), dtype=np.float64)
        
        if image is None:
            return super().generate_mask(shape, ratio)
        
        if image.shape[:2] != shape:
            image = cv2.resize(image, (w, h))
        
        if image.ndim == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        block_ratios = self._compute_adaptive_ratios(image)
        bh, bw = block_ratios.shape
        
        for i in range(bh):
            for j in range(bw):
                block_ratio = block_ratios[i, j]
                block_mask = self._rng.random((self.block_size, self.block_size)) < block_ratio
                mask[i*self.block_size:(i+1)*self.block_size,
                     j*self.block_size:(j+1)*self.block_size] = block_mask
        
        actual_ratio = np.mean(mask)
        if abs(actual_ratio - self.base_ratio) > 0.05:
            scale = self.base_ratio / (actual_ratio + 1e-8)
            mask = (self._rng.random(mask.shape) < scale * mask).astype(np.float64)
        
        return mask.astype(np.float64)

    def get_sampling_heatmap(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        block_ratios = self._compute_adaptive_ratios(image)
        heatmap = cv2.resize(block_ratios, (w, h), interpolation=cv2.INTER_NEAREST)
        return heatmap


class AdaptiveCSProcessor:
    def __init__(self, base_ratio: float = 0.3, min_ratio: float = 0.05,
                 max_ratio: float = 0.8, block_size: int = 8,
                 seed: int = 42):
        self.adaptive_sampling = AdaptiveSampling(base_ratio, min_ratio, 
                                                max_ratio, block_size, seed)
        self.reconstructor = FISTAReconstructor(tv_weight=0.5, max_iter=100, time_limit=10.0)
        self.uniform_sampling = RandomSampling(seed=seed)

    def process_adaptive(self, image: np.ndarray, base_ratio: float) -> Dict:
        start_time = time.time()
        
        mask = self.adaptive_sampling.generate_mask(image.shape[:2], base_ratio, image)
        measurements = image * mask
        reconstructed = self.reconstructor.reconstruct(measurements, mask)
        
        quality = QualityEvaluator.evaluate(image, reconstructed)
        actual_ratio = np.mean(mask)
        texture_map = TextureAnalyzer.compute_texture_map(image)
        sampling_heatmap = self.adaptive_sampling.get_sampling_heatmap(image)
        
        processing_time = time.time() - start_time
        
        return {
            'original': image,
            'mask': mask,
            'measurements': measurements,
            'reconstructed': reconstructed,
            'quality': quality,
            'sampling_ratio': actual_ratio,
            'base_ratio': base_ratio,
            'texture_map': texture_map,
            'sampling_heatmap': sampling_heatmap,
            'processing_time': processing_time,
            'method': 'Adaptive'
        }

    def process_uniform(self, image: np.ndarray, ratio: float) -> Dict:
        start_time = time.time()
        
        mask = self.uniform_sampling.generate_mask(image.shape[:2], ratio)
        measurements = image * mask
        reconstructed = self.reconstructor.reconstruct(measurements, mask)
        
        quality = QualityEvaluator.evaluate(image, reconstructed)
        processing_time = time.time() - start_time
        
        return {
            'original': image,
            'mask': mask,
            'measurements': measurements,
            'reconstructed': reconstructed,
            'quality': quality,
            'sampling_ratio': ratio,
            'processing_time': processing_time,
            'method': 'Uniform'
        }

    def compare_sampling(self, image: np.ndarray, base_ratio: float) -> Dict:
        adaptive_result = self.process_adaptive(image, base_ratio)
        uniform_result = self.process_uniform(image, base_ratio)
        
        return {
            'adaptive': adaptive_result,
            'uniform': uniform_result,
            'base_ratio': base_ratio
        }


def visualize_adaptive_sampling(comparison: Dict, save_path: Optional[str] = None):
    adaptive = comparison['adaptive']
    uniform = comparison['uniform']
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    
    axes[0, 0].imshow(adaptive['original'], cmap='gray')
    axes[0, 0].set_title('Original Image')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(adaptive['texture_map'], cmap='hot')
    axes[0, 1].set_title('Texture Map')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(adaptive['sampling_heatmap'], cmap='jet', vmin=0, vmax=1)
    axes[0, 2].set_title('Adaptive Sampling Rate')
    axes[0, 2].axis('off')
    
    axes[0, 3].imshow(adaptive['mask'], cmap='gray')
    axes[0, 3].set_title(f"Adaptive Mask ({adaptive['sampling_ratio']:.1%})")
    axes[0, 3].axis('off')
    
    axes[1, 0].imshow(uniform['mask'], cmap='gray')
    axes[1, 0].set_title(f"Uniform Mask ({uniform['sampling_ratio']:.1%})")
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(adaptive['reconstructed'], cmap='gray')
    q = adaptive['quality']
    axes[1, 1].set_title(f"Adaptive Reconstructed\nPSNR={q['PSNR']:.1f}dB, SSIM={q['SSIM']:.3f}")
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(uniform['reconstructed'], cmap='gray')
    q2 = uniform['quality']
    axes[1, 2].set_title(f"Uniform Reconstructed\nPSNR={q2['PSNR']:.1f}dB, SSIM={q2['SSIM']:.3f}")
    axes[1, 2].axis('off')
    
    diff = np.abs(adaptive['reconstructed'].astype(np.int32) - 
                  uniform['reconstructed'].astype(np.int32))
    im = axes[1, 3].imshow(diff, cmap='hot', vmin=0, vmax=50)
    axes[1, 3].set_title('Difference (Adaptive - Uniform)')
    axes[1, 3].axis('off')
    plt.colorbar(im, ax=axes[1, 3], fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def get_all_sampling_patterns(seed: int = 42) -> Dict[str, SamplingPattern]:
    patterns = get_sampling_patterns(seed)
    patterns['adaptive'] = AdaptiveSampling(base_ratio=0.3, seed=seed)
    return patterns

