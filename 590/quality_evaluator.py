import cv2
import numpy as np
from typing import Tuple, Dict, List
from scipy import ndimage
import math


class QualityMetrics:
    @staticmethod
    def psnr(original: np.ndarray, enhanced: np.ndarray, max_pixel: float = 255.0) -> float:
        if original.shape != enhanced.shape:
            enhanced = cv2.resize(enhanced, (original.shape[1], original.shape[0]))
        
        mse = np.mean((original.astype(np.float64) - enhanced.astype(np.float64)) ** 2)
        if mse == 0:
            return float('inf')
        return 20 * math.log10(max_pixel / math.sqrt(mse))
    
    @staticmethod
    def mse(original: np.ndarray, enhanced: np.ndarray) -> float:
        if original.shape != enhanced.shape:
            enhanced = cv2.resize(enhanced, (original.shape[1], original.shape[0]))
        return np.mean((original.astype(np.float64) - enhanced.astype(np.float64)) ** 2)
    
    @staticmethod
    def ssim(original: np.ndarray, enhanced: np.ndarray, 
             window_size: int = 11, sigma: float = 1.5,
             K1: float = 0.01, K2: float = 0.03, max_pixel: float = 255.0) -> float:
        if original.shape != enhanced.shape:
            enhanced = cv2.resize(enhanced, (original.shape[1], original.shape[0]))
        
        if len(original.shape) == 3:
            original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
        
        original = original.astype(np.float64)
        enhanced = enhanced.astype(np.float64)
        
        C1 = (K1 * max_pixel) ** 2
        C2 = (K2 * max_pixel) ** 2
        
        kernel = cv2.getGaussianKernel(window_size, sigma)
        kernel = kernel @ kernel.T
        
        mu1 = cv2.filter2D(original, -1, kernel)
        mu2 = cv2.filter2D(enhanced, -1, kernel)
        
        mu1_sq = mu1 ** 2
        mu2_sq = mu2 ** 2
        mu1_mu2 = mu1 * mu2
        
        sigma1_sq = cv2.filter2D(original ** 2, -1, kernel) - mu1_sq
        sigma2_sq = cv2.filter2D(enhanced ** 2, -1, kernel) - mu2_sq
        sigma12 = cv2.filter2D(original * enhanced, -1, kernel) - mu1_mu2
        
        ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
                   ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
        
        return np.mean(ssim_map)


class NoReferenceMetrics:
    @staticmethod
    def brisque(img: np.ndarray) -> float:
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            features = []
            
            for scale in range(2):
                if scale > 0:
                    gray = cv2.pyrDown(gray)
                
                mu = cv2.GaussianBlur(gray, (7, 7), 7/6)
                sigma = cv2.GaussianBlur((gray - mu) ** 2, (7, 7), 7/6)
                sigma = np.sqrt(sigma)
                
                struct_dis = (gray - mu) / (sigma + 1)
                
                features.append(np.mean(struct_dis))
                features.append(np.var(struct_dis))
                features.append(np.mean(np.abs(struct_dis - np.mean(struct_dis))))
            
            score = np.mean(np.abs(features)) * 10
            return min(score, 100)
        except:
            return 50.0
    
    @staticmethod
    def contrast_score(img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return np.std(gray) / 128.0
    
    @staticmethod
    def sharpness_score(img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return np.var(laplacian) / 1000.0
    
    @staticmethod
    def color_cast_score(img: np.ndarray) -> float:
        avg_r = np.mean(img[:, :, 2])
        avg_g = np.mean(img[:, :, 1])
        avg_b = np.mean(img[:, :, 0])
        
        avg_gray = (avg_r + avg_g + avg_b) / 3.0
        
        r_deviation = abs(avg_r - avg_gray) / avg_gray
        g_deviation = abs(avg_g - avg_gray) / avg_gray
        b_deviation = abs(avg_b - avg_gray) / avg_gray
        
        total_deviation = (r_deviation + g_deviation + b_deviation) / 3.0
        return 1.0 - min(total_deviation, 1.0)
    
    @staticmethod
    def underwater_quality_score(img: np.ndarray) -> Dict[str, float]:
        contrast = NoReferenceMetrics.contrast_score(img)
        sharpness = NoReferenceMetrics.sharpness_score(img)
        color_cast = NoReferenceMetrics.color_cast_score(img)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray) / 255.0
        
        edges = cv2.Canny(img, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1]) * 100
        
        overall = (contrast * 0.25 + 
                   min(sharpness, 1.0) * 0.25 + 
                   color_cast * 0.25 + 
                   min(edge_density / 10, 1.0) * 0.25)
        
        return {
            'contrast': min(contrast, 1.0),
            'sharpness': min(sharpness, 1.0),
            'color_fidelity': color_cast,
            'brightness': brightness,
            'edge_density': edge_density,
            'overall_quality': overall
        }


class FullReferenceEvaluator:
    def __init__(self, original: np.ndarray):
        self.original = original
    
    def evaluate(self, enhanced: np.ndarray) -> Dict[str, float]:
        return {
            'psnr': QualityMetrics.psnr(self.original, enhanced),
            'mse': QualityMetrics.mse(self.original, enhanced),
            'ssim': QualityMetrics.ssim(self.original, enhanced)
        }


class NoReferenceEvaluator:
    @staticmethod
    def evaluate(img: np.ndarray) -> Dict[str, float]:
        return NoReferenceMetrics.underwater_quality_score(img)
    
    @staticmethod
    def compare(original: np.ndarray, enhanced: np.ndarray) -> Dict[str, Dict]:
        orig_metrics = NoReferenceEvaluator.evaluate(original)
        enh_metrics = NoReferenceEvaluator.evaluate(enhanced)
        
        improvement = {}
        for key in orig_metrics:
            if key in ['contrast', 'sharpness', 'color_fidelity', 'edge_density', 'overall_quality']:
                improvement[key] = enh_metrics[key] - orig_metrics[key]
        
        return {
            'original': orig_metrics,
            'enhanced': enh_metrics,
            'improvement': improvement
        }


class ComparativeEvaluator:
    def __init__(self):
        self.results = []
    
    def add_result(self, method_name: str, original: np.ndarray, enhanced: np.ndarray):
        nr_metrics = NoReferenceEvaluator.compare(original, enhanced)
        fr_metrics = FullReferenceEvaluator(original).evaluate(enhanced)
        
        self.results.append({
            'method': method_name,
            'no_reference': nr_metrics,
            'full_reference': fr_metrics
        })
    
    def get_summary(self) -> Dict:
        summary = {}
        for result in self.results:
            summary[result['method']] = {
                'overall_quality': result['no_reference']['enhanced']['overall_quality'],
                'quality_improvement': result['no_reference']['improvement']['overall_quality'],
                'psnr': result['full_reference']['psnr'],
                'ssim': result['full_reference']['ssim']
            }
        return summary
    
    def get_best_method(self) -> str:
        if not self.results:
            return None
        
        best = max(self.results, 
                  key=lambda x: x['no_reference']['enhanced']['overall_quality'])
        return best['method']
