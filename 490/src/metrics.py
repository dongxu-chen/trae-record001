import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from skimage.metrics import structural_similarity as ssim
from typing import Dict, Tuple, List, Optional
import warnings


class MultiScaleLPIPS:
    def __init__(self, device='cpu', backbones=['vgg', 'alex']):
        self.device = device
        self.models = {}
        
        for net_type in backbones:
            try:
                import lpips
                self.models[net_type] = lpips.LPIPS(net=net_type).to(device)
                self.models[net_type].eval()
            except (ImportError, Exception) as e:
                warnings.warn(f"LPIPS with backbone '{net_type}' not available: {e}")
        
    def _prepare_tensors(self, img1, img2):
        if not isinstance(img1, torch.Tensor):
            img1 = torch.from_numpy(img1).float()
        if not isinstance(img2, torch.Tensor):
            img2 = torch.from_numpy(img2).float()
        
        if img1.ndim == 3:
            img1 = img1.unsqueeze(0)
        if img2.ndim == 3:
            img2 = img2.unsqueeze(0)
        
        if img1.shape[1] != 3:
            if img1.ndim == 4 and img1.shape[3] == 3:
                img1 = img1.permute(0, 3, 1, 2)
        if img2.shape[1] != 3:
            if img2.ndim == 4 and img2.shape[3] == 3:
                img2 = img2.permute(0, 3, 1, 2)
        
        img1 = img1.to(self.device)
        img2 = img2.to(self.device)
        
        return img1, img2
    
    def compute_single_scale(self, img1, img2, backbone='vgg'):
        if backbone not in self.models:
            return None
        
        img1, img2 = self._prepare_tensors(img1, img2)
        
        with torch.no_grad():
            value = self.models[backbone](img1, img2)
        
        return value.item()
    
    def compute_multi_scale(self, img1, img2, scales=[1.0, 0.5, 0.25], backbone='vgg'):
        if backbone not in self.models:
            return None
        
        img1, img2 = self._prepare_tensors(img1, img2)
        
        scale_values = []
        for scale in scales:
            if scale != 1.0:
                h, w = img1.shape[2], img1.shape[3]
                new_h, new_w = int(h * scale), int(w * scale)
                
                if new_h < 16 or new_w < 16:
                    continue
                
                s1 = F.interpolate(img1, size=(new_h, new_w), mode='bilinear', align_corners=False)
                s2 = F.interpolate(img2, size=(new_h, new_w), mode='bilinear', align_corners=False)
            else:
                s1, s2 = img1, img2
            
            with torch.no_grad():
                val = self.models[backbone](s1, s2)
            scale_values.append(val.item())
        
        if not scale_values:
            return None
        
        weights = [1.0, 0.6, 0.3][:len(scale_values)]
        total_weight = sum(weights)
        weighted_sum = sum(v * w for v, w in zip(scale_values, weights))
        
        return weighted_sum / total_weight
    
    def compute_ensemble(self, img1, img2, scales=[1.0, 0.5, 0.25]):
        results = {}
        ensemble_values = []
        ensemble_weights = []
        
        backbone_weights = {'vgg': 0.5, 'alex': 0.3, 'squeeze': 0.2}
        
        for backbone in self.models.keys():
            ms_value = self.compute_multi_scale(img1, img2, scales=scales, backbone=backbone)
            if ms_value is not None:
                results[f'lpips_ms_{backbone}'] = ms_value
                ensemble_values.append(ms_value)
                ensemble_weights.append(backbone_weights.get(backbone, 0.25))
        
        if ensemble_values:
            total_w = sum(ensemble_weights)
            results['lpips_ensemble'] = sum(v * w for v, w in zip(ensemble_values, ensemble_weights)) / total_w
        
        return results


class PerceptualQualityScorer:
    def __init__(self, device='cpu'):
        self.device = device
    
    def compute_dists_features(self, img1, img2):
        if not isinstance(img1, torch.Tensor):
            img1 = torch.from_numpy(img1).float()
        if not isinstance(img2, torch.Tensor):
            img2 = torch.from_numpy(img2).float()
        
        if img1.ndim == 3:
            img1 = img1.unsqueeze(0)
        if img2.ndim == 3:
            img2 = img2.unsqueeze(0)
        
        if img1.shape[1] != 3 and img1.shape[-1] == 3:
            img1 = img1.permute(0, 3, 1, 2)
        if img2.shape[1] != 3 and img2.shape[-1] == 3:
            img2 = img2.permute(0, 3, 1, 2)
        
        img1 = img1.to(self.device)
        img2 = img2.to(self.device)
        
        diff = (img1 - img2).abs()
        
        structure_loss = diff.mean().item()
        
        mean_diff = diff.mean(dim=1, keepdim=True)
        variance = ((diff - mean_diff) ** 2).mean().item()
        texture_loss = variance
        
        return structure_loss, texture_loss
    
    def compute_boundary_artifact_score(self, original, inpainted, mask):
        if isinstance(original, torch.Tensor):
            original = original.detach().cpu().numpy()
        if isinstance(inpainted, torch.Tensor):
            inpainted = inpainted.detach().cpu().numpy()
        if isinstance(mask, torch.Tensor):
            mask = mask.detach().cpu().numpy()
        
        if mask.ndim == 4:
            mask = mask.squeeze()
        if mask.ndim == 3 and mask.shape[0] == 1:
            mask = mask.squeeze(0)
        if mask.ndim == 3:
            mask = mask[:, :, 0]
        
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        import cv2
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
        boundary = (dilated - mask_uint8).astype(np.float32) / 255.0
        
        if boundary.sum() < 1e-6:
            return 0.0
        
        if original.ndim == 2:
            original = original[:, :, np.newaxis]
        if inpainted.ndim == 2:
            inpainted = inpainted[:, :, np.newaxis]
        
        if boundary.ndim == 2:
            boundary = boundary[:, :, np.newaxis]
        
        boundary_diff = np.abs(original - inpainted) * boundary
        
        artifact_score = boundary_diff.sum() / (boundary.sum() + 1e-8)
        
        return artifact_score
    
    def compute_perceptual_score(self, psnr, ssim_val, lpips_val, 
                                  boundary_artifact=None):
        psnr_norm = min(max((psnr - 15) / 25, 0), 1)
        ssim_norm = min(max(ssim_val, 0), 1)
        
        if lpips_val is not None:
            lpips_norm = max(1 - lpips_val, 0)
        else:
            lpips_norm = 0.5
        
        weights = {
            'psnr': 0.2,
            'ssim': 0.25,
            'lpips': 0.4,
            'boundary': 0.15
        }
        
        if boundary_artifact is not None:
            boundary_norm = max(1 - boundary_artifact * 10, 0)
        else:
            weights['lpips'] += weights['boundary']
            weights['boundary'] = 0
            boundary_norm = 0
        
        total_weight = sum(weights.values())
        score = (
            weights['psnr'] * psnr_norm +
            weights['ssim'] * ssim_norm +
            weights['lpips'] * lpips_norm +
            weights['boundary'] * boundary_norm
        ) / total_weight
        
        return score * 100


class QualityEvaluator:
    def __init__(self, device: str = 'cpu', use_lpips: bool = True):
        self.device = device
        self.loss_fn_vgg = None
        self.loss_fn_alex = None
        self.loss_fn_squeeze = None
        self.ms_lpips = None
        self.perceptual_scorer = None
        
        if use_lpips:
            try:
                import lpips
                self.loss_fn_vgg = lpips.LPIPS(net='vgg').to(device)
                self.loss_fn_vgg.eval()
            except (ImportError, Exception) as e:
                warnings.warn(f"LPIPS-VGG not available: {e}")
            
            try:
                import lpips
                self.loss_fn_alex = lpips.LPIPS(net='alex').to(device)
                self.loss_fn_alex.eval()
            except (ImportError, Exception):
                pass
            
            try:
                import lpips
                self.loss_fn_squeeze = lpips.LPIPS(net='squeeze').to(device)
                self.loss_fn_squeeze.eval()
            except (ImportError, Exception):
                pass
        
        self.ms_lpips = MultiScaleLPIPS(device=device)
        self.perceptual_scorer = PerceptualQualityScorer(device=device)

    def calculate_psnr(self, img1: np.ndarray, img2: np.ndarray, 
                        max_pixel: float = 1.0) -> float:
        if isinstance(img1, torch.Tensor):
            img1 = img1.detach().cpu().numpy()
        if isinstance(img2, torch.Tensor):
            img2 = img2.detach().cpu().numpy()
        
        if img1.shape != img2.shape:
            raise ValueError(f"Image shapes do not match: {img1.shape} vs {img2.shape}")
        
        mse = np.mean((img1 - img2) ** 2)
        
        if mse == 0:
            return float('inf')
        
        psnr = 10 * np.log10((max_pixel ** 2) / mse)
        
        return psnr

    def calculate_ssim(self, img1: np.ndarray, img2: np.ndarray,
                    multichannel: bool = True,
                    window_size: int = 7) -> float:
        if isinstance(img1, torch.Tensor):
            img1 = img1.detach().cpu().numpy()
        if isinstance(img2, torch.Tensor):
            img2 = img2.detach().cpu().numpy()
        
        if img1.ndim == 4:
            img1 = img1.squeeze()
        if img2.ndim == 4:
            img2 = img2.squeeze()
        
        if img1.shape != img2.shape:
            raise ValueError(f"Image shapes do not match: {img1.shape} vs {img2.shape}")
        
        img1_gray = img1
        img2_gray = img2
        
        if multichannel and img1.ndim == 3:
            channel_axis = -1
        else:
            channel_axis = None
            if img1.ndim == 3:
                img1_gray = np.mean(img1, axis=-1)
                img2_gray = np.mean(img2, axis=-1)
        
        ssim_value = ssim(img1_gray, img2_gray, 
                           data_range=1.0,
                           channel_axis=channel_axis)
        
        return ssim_value

    def calculate_lpips(self, img1: torch.Tensor, img2: torch.Tensor, 
                         backbone: str = 'vgg') -> float:
        model_map = {
            'vgg': self.loss_fn_vgg,
            'alex': self.loss_fn_alex,
            'squeeze': self.loss_fn_squeeze,
        }
        
        loss_fn = model_map.get(backbone, self.loss_fn_vgg)
        
        if loss_fn is None:
            if backbone != 'vgg':
                return self.calculate_lpips(img1, img2, backbone='vgg')
            warnings.warn("LPIPS not available")
            return 0.0
        
        if not isinstance(img1, torch.Tensor):
            img1 = torch.from_numpy(img1).float()
        if not isinstance(img2, torch.Tensor):
            img2 = torch.from_numpy(img2).float()
        
        if img1.ndim == 3:
            img1 = img1.unsqueeze(0)
        if img2.ndim == 3:
            img2 = img2.unsqueeze(0)
        
        if img1.shape[1] != 3:
            if img1.ndim == 4 and img1.shape[3] == 3:
                img1 = img1.permute(0, 3, 1, 2)
                img2 = img2.permute(0, 3, 1, 2)
        
        img1 = img1.to(self.device)
        img2 = img2.to(self.device)
        
        with torch.no_grad():
            lpips_value = loss_fn(img1, img2)
        
        return lpips_value.item()

    def calculate_multiscale_lpips(self, img1, img2, backbone='vgg'):
        if self.ms_lpips is None:
            return None
        return self.ms_lpips.compute_multi_scale(img1, img2, backbone=backbone)

    def calculate_lpips_ensemble(self, img1, img2):
        if self.ms_lpips is None:
            return {}
        return self.ms_lpips.compute_ensemble(img1, img2)

    def calculate_mae(self, img1: np.ndarray, img2: np.ndarray) -> float:
        if isinstance(img1, torch.Tensor):
            img1 = img1.detach().cpu().numpy()
        if isinstance(img2, torch.Tensor):
            img2 = img2.detach().cpu().numpy()
        
        return np.mean(np.abs(img1 - img2))

    def calculate_mse(self, img1: np.ndarray, img2: np.ndarray) -> float:
        if isinstance(img1, torch.Tensor):
            img1 = img1.detach().cpu().numpy()
        if isinstance(img2, torch.Tensor):
            img2 = img2.detach().cpu().numpy()
        
        return np.mean((img1 - img2) ** 2)

    def evaluate_all(self, original: np.ndarray, 
                       inpainted: np.ndarray,
                       mask: np.ndarray = None,
                       only_masked_region: bool = False,
                       detailed: bool = False) -> Dict[str, float]:
        if only_masked_region and mask is not None:
            if isinstance(mask, torch.Tensor):
                mask = mask.detach().cpu().numpy()
            if mask.ndim == 4:
                mask = mask.squeeze()
            if mask.ndim == 3 and mask.shape[0] == 1:
                mask = mask.squeeze(0)
            if mask.ndim == 3 and mask.shape[2] == 1:
                mask = mask[:, :, 0]
            
            if mask.ndim == 2:
                mask_3d = mask[:, :, np.newaxis]
            else:
                mask_3d = mask
            
            original_masked = original * (1 - mask_3d)
            inpainted_masked = inpainted * (1 - mask_3d)
        else:
            original_masked = original
            inpainted_masked = inpainted
        
        results = {
            'psnr': self.calculate_psnr(original_masked, inpainted_masked),
            'ssim': self.calculate_ssim(original_masked, inpainted_masked),
            'mae': self.calculate_mae(original_masked, inpainted_masked),
            'mse': self.calculate_mse(original_masked, inpainted_masked),
        }
        
        if self.loss_fn_vgg is not None:
            results['lpips_vgg'] = self.calculate_lpips(original_masked, inpainted_masked, backbone='vgg')
        
        if self.loss_fn_alex is not None:
            results['lpips_alex'] = self.calculate_lpips(original_masked, inpainted_masked, backbone='alex')
        
        if self.loss_fn_squeeze is not None:
            results['lpips_squeeze'] = self.calculate_lpips(original_masked, inpainted_masked, backbone='squeeze')
        
        if detailed and self.ms_lpips is not None:
            ensemble_results = self.calculate_lpips_ensemble(original_masked, inpainted_masked)
            results.update(ensemble_results)
            
            ms_vgg = self.calculate_multiscale_lpips(original_masked, inpainted_masked, backbone='vgg')
            if ms_vgg is not None:
                results['lpips_ms_vgg'] = ms_vgg
            
            ms_alex = self.calculate_multiscale_lpips(original_masked, inpainted_masked, backbone='alex')
            if ms_alex is not None:
                results['lpips_ms_alex'] = ms_alex
        
        if detailed and self.perceptual_scorer is not None:
            structure_loss, texture_loss = self.perceptual_scorer.compute_dists_features(
                original_masked, inpainted_masked
            )
            results['structure_loss'] = structure_loss
            results['texture_loss'] = texture_loss
        
        boundary_artifact = None
        if mask is not None and detailed and self.perceptual_scorer is not None:
            try:
                boundary_artifact = self.perceptual_scorer.compute_boundary_artifact_score(
                    original, inpainted, mask
                )
                results['boundary_artifact'] = boundary_artifact
            except Exception:
                pass
        
        if detailed and self.perceptual_scorer is not None:
            lpips_val = results.get('lpips_ensemble', results.get('lpips_vgg', None))
            perceptual_score = self.perceptual_scorer.compute_perceptual_score(
                psnr=results['psnr'],
                ssim_val=results['ssim'],
                lpips_val=lpips_val,
                boundary_artifact=boundary_artifact
            )
            results['perceptual_score'] = perceptual_score
        
        return results

    def evaluate_batch(self, originals, inpainteds, masks=None,
                       only_masked_region=False, detailed=False):
        batch_results = []
        
        for i, (orig, inp) in enumerate(zip(originals, inpainteds)):
            mask = masks[i] if masks is not None else None
            result = self.evaluate_all(orig, inp, mask, only_masked_region, detailed=detailed)
            batch_results.append(result)
        
        avg_results = {}
        for key in batch_results[0].keys():
            values = [r[key] for r in batch_results if r[key] is not None and r[key] != float('inf')]
            if values:
                avg_results[key] = np.mean(values)
        
        return avg_results, batch_results

    def print_results(self, results: Dict[str, float]):
        print("=" * 60)
        print("Quality Evaluation Results:")
        print("=" * 60)
        
        basic_metrics = ['psnr', 'ssim', 'mae', 'mse']
        lpips_metrics = ['lpips_vgg', 'lpips_alex', 'lpips_squeeze']
        advanced_metrics = ['lpips_ms_vgg', 'lpips_ms_alex', 'lpips_ensemble']
        perceptual_metrics = ['structure_loss', 'texture_loss', 'boundary_artifact', 'perceptual_score']
        
        print("\n[Basic Metrics]")
        for metric in basic_metrics:
            if metric in results:
                value = results[metric]
                if metric == 'psnr':
                    print(f"  PSNR:  {value:.2f} dB")
                elif metric == 'ssim':
                    print(f"  SSIM:  {value:.4f}")
                elif metric == 'mae':
                    print(f"  MAE:   {value:.6f}")
                elif metric == 'mse':
                    print(f"  MSE:   {value:.6f}")
        
        print("\n[LPIPS Perceptual Metrics]")
        for metric in lpips_metrics + advanced_metrics:
            if metric in results and results[metric] is not None:
                print(f"  {metric.upper()}: {results[metric]:.4f}")
        
        perceptual_found = any(m in results for m in perceptual_metrics)
        if perceptual_found:
            print("\n[Perceptual Quality]")
            for metric in perceptual_metrics:
                if metric in results and results[metric] is not None:
                    if metric == 'perceptual_score':
                        print(f"  Perceptual Score: {results[metric]:.1f}/100")
                    elif metric == 'boundary_artifact':
                        print(f"  Boundary Artifact: {results[metric]:.6f}")
                    else:
                        print(f"  {metric}: {results[metric]:.6f}")
        
        print("=" * 60)


def calculate_fid(real_images, fake_images, device='cpu'):
    try:
        from scipy import linalg
    except ImportError:
        warnings.warn("scipy not available for FID calculation")
        return None
    
    def calculate_activation_statistics(images, model, device):
        batch = images.to(device)
        with torch.no_grad():
            pred = model(batch)[0]
        
        pred = pred.squeeze(3).squeeze(2).cpu().numpy()
        
        mu = np.mean(pred, axis=0)
        sigma = np.cov(pred, rowvar=False)
        
        return mu, sigma
    
    def calculate_frechet_distance(mu1, sigma1, mu2, sigma2, eps=1e-6):
        mu1 = np.atleast_1d(mu1)
        mu2 = np.atleast_1d(mu2)
        
        sigma1 = np.atleast_2d(sigma1)
        sigma2 = np.atleast_2d(sigma2)
        
        diff = mu1 - mu2
        
        covmean, _ = linalg.sqrtm(sigma1.dot(sigma2), disp=False)
        
        if not np.isfinite(covmean).all():
            offset = np.eye(sigma1.shape[0]) * eps
            covmean = linalg.sqrtm((sigma1 + offset).dot(sigma2 + offset))
        
        if np.iscomplexobj(covmean):
            covmean = covmean.real
        
        fid = diff.dot(diff) + np.trace(sigma1) + np.trace(sigma2) - 2 * np.trace(covmean)
        
        return fid
    
    try:
        import torchvision.models as models
        inception_model = models.inception_v3(pretrained=True, transform_input=False)
        inception_model = inception_model.to(device)
        inception_model.eval()
        
        mu1, sigma1 = calculate_activation_statistics(real_images, inception_model, device)
        mu2, sigma2 = calculate_activation_statistics(fake_images, inception_model, device)
        
        fid_value = calculate_frechet_distance(mu1, sigma1, mu2, sigma2)
        
        return fid_value
    except Exception as e:
        warnings.warn(f"FID calculation failed: {e}")
        return None
