import numpy as np
import cv2
from typing import Dict, Optional, Tuple
from skimage.metrics import structural_similarity as ssim
import json
import os


class Evaluator:
    def __init__(self, config=None):
        self.config = config
    
    def evaluate(
        self,
        restored: np.ndarray,
        ground_truth: np.ndarray,
        input_image: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        metrics = {}
        
        if self.config is None or self.config.eval.compute_psnr:
            metrics['psnr'] = self.compute_psnr(restored, ground_truth)
        
        if self.config is None or self.config.eval.compute_ssim:
            metrics['ssim'] = self.compute_ssim(restored, ground_truth)
        
        metrics['rmse'] = self.compute_rmse(restored, ground_truth)
        metrics['mae'] = self.compute_mae(restored, ground_truth)
        
        if input_image is not None:
            metrics['psnr_improvement'] = metrics['psnr'] - self.compute_psnr(input_image, ground_truth)
            metrics['ssim_improvement'] = metrics['ssim'] - self.compute_ssim(input_image, ground_truth)
            metrics['reflection_suppression'] = self.compute_reflection_suppression(
                input_image, restored, ground_truth
            )
        
        metrics['niqe'] = self.compute_niqe(restored)
        
        return metrics
    
    @staticmethod
    def compute_psnr(img1: np.ndarray, img2: np.ndarray, data_range: float = 255.0) -> float:
        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)
        
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        mse = np.mean((img1 - img2) ** 2)
        
        if mse == 0:
            return float('inf')
        
        return 20 * np.log10(data_range / np.sqrt(mse))
    
    @staticmethod
    def compute_ssim(img1: np.ndarray, img2: np.ndarray, multichannel: bool = True) -> float:
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        img1_gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY) if len(img1.shape) == 3 else img1
        img2_gray = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY) if len(img2.shape) == 3 else img2
        
        if multichannel and len(img1.shape) == 3:
            return ssim(img1, img2, channel_axis=2, data_range=255)
        else:
            return ssim(img1_gray, img2_gray, data_range=255)
    
    @staticmethod
    def compute_rmse(img1: np.ndarray, img2: np.ndarray) -> float:
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        return np.sqrt(np.mean((img1.astype(np.float64) - img2.astype(np.float64)) ** 2))
    
    @staticmethod
    def compute_mae(img1: np.ndarray, img2: np.ndarray) -> float:
        if img1.shape != img2.shape:
            img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
        
        return np.mean(np.abs(img1.astype(np.float64) - img2.astype(np.float64)))
    
    @staticmethod
    def compute_reflection_suppression(
        input_img: np.ndarray,
        restored_img: np.ndarray,
        ground_truth: np.ndarray
    ) -> float:
        if input_img.shape != ground_truth.shape:
            input_img = cv2.resize(input_img, (ground_truth.shape[1], ground_truth.shape[0]))
        if restored_img.shape != ground_truth.shape:
            restored_img = cv2.resize(restored_img, (ground_truth.shape[1], ground_truth.shape[0]))
        
        input_error = np.mean(np.abs(input_img.astype(np.float64) - ground_truth.astype(np.float64)))
        restored_error = np.mean(np.abs(restored_img.astype(np.float64) - ground_truth.astype(np.float64)))
        
        if input_error == 0:
            return 1.0
        
        suppression = max(0, (input_error - restored_error) / input_error)
        return suppression
    
    @staticmethod
    def compute_niqe(img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img
        
        mu = cv2.GaussianBlur(gray.astype(np.float64), (7, 7), 7/6)
        mu_sq = mu * mu
        sigma = cv2.GaussianBlur(gray.astype(np.float64) * gray.astype(np.float64), (7, 7), 7/6) - mu_sq
        sigma = np.sqrt(np.abs(sigma))
        
        structdis = (gray.astype(np.float64) - mu) / (sigma + 1)
        
        features = []
        block_size = 96
        h, w = structdis.shape
        
        for i in range(0, h - block_size + 1, block_size // 2):
            for j in range(0, w - block_size + 1, block_size // 2):
                block = structdis[i:i+block_size, j:j+block_size]
                features.extend([
                    np.mean(block),
                    np.var(block),
                    np.mean(np.abs(block - np.mean(block)))
                ])
        
        if not features:
            return 0.0
        
        features = np.array(features)
        score = np.mean(np.abs(features - np.mean(features)))
        
        return float(score)
    
    @staticmethod
    def compute_edge_preservation(restored: np.ndarray, ground_truth: np.ndarray) -> float:
        restored_gray = cv2.cvtColor(restored, cv2.COLOR_RGB2GRAY) if len(restored.shape) == 3 else restored
        gt_gray = cv2.cvtColor(ground_truth, cv2.COLOR_RGB2GRAY) if len(ground_truth.shape) == 3 else ground_truth
        
        if restored_gray.shape != gt_gray.shape:
            gt_gray = cv2.resize(gt_gray, (restored_gray.shape[1], restored_gray.shape[0]))
        
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
        
        edge_restored_x = cv2.filter2D(restored_gray.astype(np.float64), -1, sobel_x)
        edge_restored_y = cv2.filter2D(restored_gray.astype(np.float64), -1, sobel_y)
        edge_restored = np.sqrt(edge_restored_x**2 + edge_restored_y**2)
        
        edge_gt_x = cv2.filter2D(gt_gray.astype(np.float64), -1, sobel_x)
        edge_gt_y = cv2.filter2D(gt_gray.astype(np.float64), -1, sobel_y)
        edge_gt = np.sqrt(edge_gt_x**2 + edge_gt_y**2)
        
        correlation = np.corrcoef(edge_restored.flatten(), edge_gt.flatten())[0, 1]
        
        return max(0, correlation)
    
    def print_metrics(self, metrics: Dict[str, float]):
        print("\n" + "="*50)
        print("Evaluation Metrics")
        print("="*50)
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{key:30s}: {value:.4f}")
            else:
                print(f"{key:30s}: {value}")
        print("="*50 + "\n")
    
    def save_metrics(self, metrics: Dict[str, float], output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=4)
        print(f"Metrics saved to {output_path}")
