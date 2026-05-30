import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional

from .models import (PartialConvUNet, EdgeConnect, DiversePartialConvUNet,
                      StochasticInpainter, load_pretrained_model)
from .utils import (load_image, save_image, img2tensor, tensor2img,
                    create_directory, poisson_blend)
from .metrics import QualityEvaluator
from .mask_generator import MaskGenerator


class DiverseInpainter:
    def __init__(self, device: str = None,
                 image_size: Tuple[int, int] = (256, 256),
                 poisson_blend_method: str = 'mixed'):
        
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.device = device
        self.image_size = image_size
        self.poisson_blend_method = poisson_blend_method
        self.evaluator = QualityEvaluator(device=device)
        
        self.models = {}
        self._load_all_models()
    
    def _load_all_models(self):
        model_names = ['partialconv', 'edgeconnect', 'stochastic']
        for name in model_names:
            try:
                self.models[name] = load_pretrained_model(name, self.device)
                print(f"Loaded {name} model")
            except Exception as e:
                print(f"Could not load {name}: {e}")
    
    def generate_diverse_results(self,
                                  image: np.ndarray,
                                  mask: np.ndarray,
                                  num_variants: int = 5,
                                  methods: List[str] = None,
                                  blend: bool = True) -> List[Dict]:
        
        if isinstance(image, str):
            image = load_image(image, size=self.image_size, normalize=True)
        
        if mask.ndim == 2:
            mask = mask[:, :, np.newaxis]
        
        img_tensor = img2tensor(image, device=self.device)
        mask_tensor = img2tensor(mask, device=self.device)
        if mask_tensor.shape[1] == 3:
            mask_tensor = mask_tensor[:, :1, :, :]
        
        if methods is None:
            methods = ['partialconv', 'edgeconnect', 'stochastic',
                        'partialconv_blended', 'stochastic_diverse']
        
        results = []
        
        for method in methods:
            try:
                variant = self._generate_single(
                    image, mask, img_tensor, mask_tensor,
                    method, num_variants, blend
                )
                if variant is not None:
                    results.extend(variant)
            except Exception as e:
                print(f"Method {method} failed: {e}")
                continue
        
        for result in results:
            if 'metrics' not in result:
                result['metrics'] = self.evaluator.evaluate_all(
                    image, result['image'], mask[:, :, 0] if mask.ndim == 3 else mask,
                    only_masked_region=True, detailed=True
                )
        
        results.sort(key=lambda x: x['metrics'].get('perceptual_score',
                       x['metrics'].get('psnr', 0)), reverse=True)
        
        for i, result in enumerate(results):
            result['rank'] = i + 1
        
        return results
    
    def _generate_single(self, image, mask, img_tensor, mask_tensor,
                          method, num_variants, blend):
        results = []
        
        if method == 'partialconv':
            model = self.models.get('partialconv')
            if model is None:
                return None
            model.eval()
            with torch.no_grad():
                output = model(img_tensor, mask_tensor)
            output = output * mask_tensor + img_tensor * (1 - mask_tensor)
            output_np = tensor2img(output)
            
            if blend:
                mask_2d = mask[:, :, 0] if mask.ndim == 3 else mask
                try:
                    output_np = poisson_blend(output_np, image, mask_2d,
                                               method=self.poisson_blend_method)
                except Exception:
                    pass
            
            results.append({
                'method': 'partialconv',
                'variant': 0,
                'image': output_np,
                'metrics': self.evaluator.evaluate_all(
                    image, output_np, mask[:, :, 0] if mask.ndim == 3 else mask,
                    only_masked_region=True, detailed=True
                )
            })
        
        elif method == 'edgeconnect':
            model = self.models.get('edgeconnect')
            if model is None:
                return None
            model.eval()
            with torch.no_grad():
                output, edge = model(img_tensor, mask_tensor)
            output = output * mask_tensor + img_tensor * (1 - mask_tensor)
            output_np = tensor2img(output)
            
            if blend:
                mask_2d = mask[:, :, 0] if mask.ndim == 3 else mask
                try:
                    output_np = poisson_blend(output_np, image, mask_2d,
                                               method=self.poisson_blend_method)
                except Exception:
                    pass
            
            results.append({
                'method': 'edgeconnect',
                'variant': 0,
                'image': output_np,
                'metrics': self.evaluator.evaluate_all(
                    image, output_np, mask[:, :, 0] if mask.ndim == 3 else mask,
                    only_masked_region=True, detailed=True
                )
            })
        
        elif method == 'partialconv_blended':
            model = self.models.get('partialconv')
            if model is None:
                return None
            model.eval()
            
            blend_methods = ['seamless_normal', 'seamless_mixed', 'feathered', 'gradient', 'multi_pass']
            mask_2d = mask[:, :, 0] if mask.ndim == 3 else mask
            
            with torch.no_grad():
                raw_output = model(img_tensor, mask_tensor)
            raw_output = raw_output * mask_tensor + img_tensor * (1 - mask_tensor)
            raw_np = tensor2img(raw_output)
            
            for bi, bm in enumerate(blend_methods[:num_variants]):
                try:
                    blended = poisson_blend(raw_np, image, mask_2d, method=bm)
                    results.append({
                        'method': f'partialconv_{bm}',
                        'variant': bi,
                        'image': blended,
                    })
                except Exception:
                    continue
        
        elif method == 'stochastic':
            model = self.models.get('stochastic')
            if model is None:
                return None
            model.eval()
            
            with torch.no_grad():
                diverse_outputs = model(img_tensor, mask_tensor,
                                        num_samples=min(num_variants, 5), temperature=0.8)
            
            if not isinstance(diverse_outputs, list):
                diverse_outputs = [diverse_outputs]
            
            for i, output in enumerate(diverse_outputs):
                output_np = tensor2img(output)
                if blend:
                    mask_2d = mask[:, :, 0] if mask.ndim == 3 else mask
                    try:
                        output_np = poisson_blend(output_np, image, mask_2d,
                                                   method=self.poisson_blend_method)
                    except Exception:
                        pass
                
                results.append({
                    'method': 'stochastic',
                    'variant': i,
                    'image': output_np,
                })
        
        elif method == 'stochastic_diverse':
            model = self.models.get('stochastic')
            if model is None:
                return None
            model.eval()
            
            temperatures = [0.5, 0.8, 1.0, 1.2, 1.5]
            mask_2d = mask[:, :, 0] if mask.ndim == 3 else mask
            
            for i, temp in enumerate(temperatures[:num_variants]):
                with torch.no_grad():
                    output = model(img_tensor, mask_tensor,
                                    num_samples=1, temperature=temp)
                
                output_np = tensor2img(output)
                if blend:
                    try:
                        output_np = poisson_blend(output_np, image, mask_2d,
                                                   method=self.poisson_blend_method)
                    except Exception:
                        pass
                
                results.append({
                    'method': f'stochastic_t{temp}',
                    'variant': i,
                    'image': output_np,
                })
        
        return results if results else None
    
    def visualize_variants(self, image, mask, results, save_path=None, max_display=6):
        if isinstance(image, torch.Tensor):
            image = tensor2img(image)
        if isinstance(mask, torch.Tensor):
            mask = tensor2img(mask)
        
        n = min(len(results), max_display)
        cols = n + 1
        rows = 1
        
        fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 5))
        
        if cols == 1:
            axes = [axes]
        
        axes[0].imshow(image)
        mask_disp = mask[:, :, 0] if mask.ndim == 3 and mask.shape[2] == 1 else mask
        axes[0].set_title('Original', fontsize=10)
        axes[0].axis('off')
        
        for i in range(n):
            result = results[i]
            axes[i + 1].imshow(result['image'])
            
            rank = result.get('rank', '?')
            method = result.get('method', '?')
            psnr = result['metrics'].get('psnr', 0) if 'metrics' in result else 0
            score = result['metrics'].get('perceptual_score', 0) if 'metrics' in result else 0
            
            title = f"#{rank} {method[:15]}\nPSNR:{psnr:.1f} Score:{score:.0f}"
            axes[i + 1].set_title(title, fontsize=8)
            axes[i + 1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    
    def inpaint_diverse(self, image_path: str,
                         mask_type: str = 'watermark',
                         num_variants: int = 5,
                         output_dir: str = 'diverse_results',
                         save_all: bool = True) -> Dict:
        
        create_directory(output_dir)
        
        image = load_image(image_path, size=self.image_size, normalize=True)
        h, w = image.shape[:2]
        
        mask_gen = MaskGenerator(height=h, width=w)
        mask = mask_gen.generate_mask(mask_type)
        
        print(f"Generating {num_variants} diverse inpainting results...")
        
        results = self.generate_diverse_results(image, mask, num_variants=num_variants)
        
        if save_all:
            for result in results:
                rank = result.get('rank', 0)
                method = result.get('method', 'unknown')
                filename = f"rank{rank}_{method}.png"
                save_path = os.path.join(output_dir, filename)
                save_image(result['image'], save_path)
            
            viz_path = os.path.join(output_dir, 'all_variants.png')
            self.visualize_variants(image, mask, results, save_path=viz_path)
        
        if results:
            best = results[0]
            best_path = os.path.join(output_dir, 'best_result.png')
            save_image(best['image'], best_path)
            print(f"\nBest result (rank #1): {best['method']}")
            if 'metrics' in best:
                self.evaluator.print_results(best['metrics'])
        
        return {
            'num_variants': len(results),
            'results': results,
            'best': results[0] if results else None
        }
    
    def select_best(self, results: List[Dict],
                     criterion: str = 'perceptual_score') -> Dict:
        valid_results = [r for r in results if 'metrics' in r and criterion in r['metrics']]
        
        if not valid_results:
            return results[0] if results else None
        
        if criterion in ('psnr', 'ssim', 'perceptual_score'):
            best = max(valid_results, key=lambda x: x['metrics'][criterion])
        elif criterion in ('lpips_vgg', 'lpips_ensemble', 'mae', 'mse'):
            best = min(valid_results, key=lambda x: x['metrics'][criterion])
        else:
            best = max(valid_results, key=lambda x: x['metrics'].get('perceptual_score', 0))
        
        return best
