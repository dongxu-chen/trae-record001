import numpy as np
from scipy.ndimage import sobel, gaussian_filter
from typing import Dict, Optional, Tuple
import json


class DepthEvaluator:
    def __init__(self, ground_truth: Optional[np.ndarray] = None):
        self.ground_truth = ground_truth
        self._texture_mask = None

    def set_texture_mask(self, mask: np.ndarray):
        self._texture_mask = mask

    def _compute_texture_mask(self, image: Optional[np.ndarray],
                               confidence: Optional[np.ndarray],
                               texture_threshold: float = 0.1) -> np.ndarray:
        if self._texture_mask is not None:
            return self._texture_mask

        if confidence is not None:
            return confidence >= texture_threshold

        if image is not None:
            grad_y = sobel(image, axis=0)
            grad_x = sobel(image, axis=1)
            grad_mag = np.sqrt(grad_y ** 2 + grad_x ** 2)
            grad_mag = grad_mag / (grad_mag.max() + 1e-8)
            return grad_mag >= texture_threshold

        return np.ones((1, 1), dtype=bool)
        
    def mae(self, depth: np.ndarray, gt: Optional[np.ndarray] = None,
            texture_mask: Optional[np.ndarray] = None) -> float:
        if gt is None:
            gt = self.ground_truth
        if gt is None:
            raise ValueError("No ground truth provided")
        
        mask = ~np.isnan(gt) & ~np.isnan(depth)
        if texture_mask is not None:
            mask = mask & texture_mask
        return np.mean(np.abs(depth[mask] - gt[mask]))
    
    def rmse(self, depth: np.ndarray, gt: Optional[np.ndarray] = None,
             texture_mask: Optional[np.ndarray] = None) -> float:
        if gt is None:
            gt = self.ground_truth
        if gt is None:
            raise ValueError("No ground truth provided")
        
        mask = ~np.isnan(gt) & ~np.isnan(depth)
        if texture_mask is not None:
            mask = mask & texture_mask
        return np.sqrt(np.mean((depth[mask] - gt[mask]) ** 2))
    
    def bad_pixel_ratio(self, depth: np.ndarray, gt: Optional[np.ndarray] = None, 
                        threshold: float = 0.07,
                        texture_mask: Optional[np.ndarray] = None) -> float:
        if gt is None:
            gt = self.ground_truth
        if gt is None:
            raise ValueError("No ground truth provided")
        
        mask = ~np.isnan(gt) & ~np.isnan(depth)
        if texture_mask is not None:
            mask = mask & texture_mask
        abs_diff = np.abs(depth[mask] - gt[mask])
        bad_ratio = np.mean(abs_diff > threshold)
        return bad_ratio
    
    def si_rmse(self, depth: np.ndarray, gt: Optional[np.ndarray] = None,
                texture_mask: Optional[np.ndarray] = None) -> float:
        if gt is None:
            gt = self.ground_truth
        if gt is None:
            raise ValueError("No ground truth provided")
        
        mask = ~np.isnan(gt) & ~np.isnan(depth)
        if texture_mask is not None:
            mask = mask & texture_mask
        log_depth = np.log(depth[mask] + 1e-8)
        log_gt = np.log(gt[mask] + 1e-8)
        
        log_diff = log_depth - log_gt
        si_rmse = np.sqrt(np.mean(log_diff ** 2) - np.mean(log_diff) ** 2)
        return si_rmse
    
    def absolute_relative_error(self, depth: np.ndarray, 
                                 gt: Optional[np.ndarray] = None,
                                 texture_mask: Optional[np.ndarray] = None) -> float:
        if gt is None:
            gt = self.ground_truth
        if gt is None:
            raise ValueError("No ground truth provided")
        
        mask = ~np.isnan(gt) & ~np.isnan(depth) & (gt > 0)
        if texture_mask is not None:
            mask = mask & texture_mask
        return np.mean(np.abs(depth[mask] - gt[mask]) / gt[mask])
    
    def compute_edge_aware_smoothness(self, depth: np.ndarray, 
                                       image: Optional[np.ndarray] = None,
                                       texture_mask: Optional[np.ndarray] = None) -> float:
        depth_grad_y = sobel(depth, axis=0)
        depth_grad_x = sobel(depth, axis=1)
        
        if image is not None:
            image_grad_y = sobel(image, axis=0)
            image_grad_x = sobel(image, axis=1)
            
            edge_weight = np.exp(-(image_grad_y ** 2 + image_grad_x ** 2) / 0.1)
            
            smoothness_val = edge_weight * (depth_grad_y ** 2 + depth_grad_x ** 2)
        else:
            smoothness_val = depth_grad_y ** 2 + depth_grad_x ** 2
        
        if texture_mask is not None:
            return np.mean(smoothness_val[texture_mask])
        return np.mean(smoothness_val)
    
    def compute_confidence_accuracy(self, depth: np.ndarray, confidence: np.ndarray,
                                     gt: Optional[np.ndarray] = None,
                                     texture_mask: Optional[np.ndarray] = None) -> Dict[str, float]:
        if gt is None:
            gt = self.ground_truth
        if gt is None:
            raise ValueError("No ground truth provided")
        
        mask = ~np.isnan(gt) & ~np.isnan(depth)
        if texture_mask is not None:
            mask = mask & texture_mask
        errors = np.abs(depth - gt)
        errors[~mask] = np.nan
        
        conf_sorted_idx = np.argsort(-confidence.flatten())
        errors_sorted = errors.flatten()[conf_sorted_idx]
        
        cum_error = np.nancumsum(errors_sorted)
        cum_count = np.cumsum(~np.isnan(errors_sorted))
        
        oracle_error = np.nanmean(np.sort(errors.flatten()))
        current_error = cum_error[-1] / cum_count[-1] if cum_count[-1] > 0 else 0
        
        auc = np.trapz(cum_error / (cum_count + 1e-8), dx=1) / len(errors_sorted)
        
        high_conf_mask = confidence > 0.7
        high_conf_error = np.mean(errors[high_conf_mask & mask]) if np.any(high_conf_mask & mask) else 0
        
        low_conf_mask = confidence < 0.3
        low_conf_error = np.mean(errors[low_conf_mask & mask]) if np.any(low_conf_mask & mask) else 0
        
        conf_corr = 0.0
        if np.sum(mask) > 10:
            try:
                conf_corr = np.corrcoef(confidence[mask], -errors[mask])[0, 1]
            except:
                conf_corr = 0.0
        
        return {
            'oracle_ratio': oracle_error / (current_error + 1e-8),
            'auc': auc,
            'high_conf_error': high_conf_error,
            'low_conf_error': low_conf_error,
            'confidence_correlation': conf_corr
        }
    
    def full_evaluation(self, depth: np.ndarray, confidence: np.ndarray,
                        gt: Optional[np.ndarray] = None,
                        image: Optional[np.ndarray] = None,
                        texture_threshold: float = 0.1) -> Dict[str, float]:
        results = {}
        
        texture_mask = self._compute_texture_mask(image, confidence, texture_threshold)
        texture_ratio = np.mean(texture_mask) if texture_mask.size > 1 else 1.0
        results['TextureCoverage'] = texture_ratio
        
        if gt is not None or self.ground_truth is not None:
            results['MAE'] = self.mae(depth, gt, texture_mask)
            results['RMSE'] = self.rmse(depth, gt, texture_mask)
            results['BadPixelRatio_0.07'] = self.bad_pixel_ratio(depth, gt, 0.07, texture_mask)
            results['BadPixelRatio_0.1'] = self.bad_pixel_ratio(depth, gt, 0.1, texture_mask)
            results['SI_RMSE'] = self.si_rmse(depth, gt, texture_mask)
            results['AbsRel'] = self.absolute_relative_error(depth, gt, texture_mask)
            
            conf_acc = self.compute_confidence_accuracy(depth, confidence, gt, texture_mask)
            results.update(conf_acc)
        
        results['Smoothness'] = self.compute_edge_aware_smoothness(depth, image, texture_mask)
        results['MeanConfidence'] = np.mean(confidence)
        results['StdDepth'] = np.std(depth)
        
        if texture_mask.size > 1:
            results['MeanConfidence_HighTexture'] = np.mean(confidence[texture_mask])
            results['MeanConfidence_LowTexture'] = np.mean(confidence[~texture_mask])
        
        return results
    
    def print_report(self, results: Dict[str, float]) -> None:
        print("=" * 50)
        print("深度质量评估报告 (仅高纹理区域)")
        print("=" * 50)
        
        if 'TextureCoverage' in results:
            print(f"纹理覆盖率:             {results['TextureCoverage']:.2%}")
        
        if 'MAE' in results:
            print(f"MAE:                    {results['MAE']:.6f}")
            print(f"RMSE:                   {results['RMSE']:.6f}")
            print(f"Bad Pixel Ratio (0.07): {results['BadPixelRatio_0.07']:.4f}")
            print(f"Bad Pixel Ratio (0.1):  {results['BadPixelRatio_0.1']:.4f}")
            print(f"SI-RMSE:                {results['SI_RMSE']:.6f}")
            print(f"AbsRel:                 {results['AbsRel']:.6f}")
        
        print(f"Smoothness:             {results['Smoothness']:.6f}")
        print(f"Mean Confidence:        {results['MeanConfidence']:.4f}")
        print(f"Std Depth:              {results['StdDepth']:.6f}")
        
        if 'MeanConfidence_HighTexture' in results:
            print(f"高纹理置信度:           {results['MeanConfidence_HighTexture']:.4f}")
            print(f"低纹理置信度:           {results['MeanConfidence_LowTexture']:.4f}")
        
        if 'confidence_correlation' in results:
            print(f"Confidence Correlation: {results['confidence_correlation']:.4f}")
        
        print("=" * 50)
    
    def save_report(self, results: Dict[str, float], filepath: str) -> None:
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=4)
