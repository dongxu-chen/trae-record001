import os
import gc
import torch
import numpy as np
from tqdm import tqdm
from typing import List, Tuple, Optional, Dict
import cv2

from .models import PartialConvUNet, EdgeConnect, load_pretrained_model
from .utils import (load_image, save_image, img2tensor, tensor2img, create_directory,
                    get_image_list, poisson_blend, compute_optimal_batch_size,
                    get_available_gpu_memory, estimate_gpu_memory_per_image)
from .mask_generator import MaskGenerator
from .metrics import QualityEvaluator


class GPUMemoryManager:
    def __init__(self, device='cpu', safety_factor=0.8):
        self.device = device
        self.safety_factor = safety_factor
        self._peak_usage = 0
        self._current_batch_size = 1
    
    def get_available_memory(self):
        if self.device == 'cpu' or not torch.cuda.is_available():
            return float('inf')
        return get_available_gpu_memory(self.device)
    
    def compute_batch_size(self, height, width, model_name='partialconv'):
        if self.device == 'cpu' or not torch.cuda.is_available():
            self._current_batch_size = 1
            return 1
        
        batch_size = compute_optimal_batch_size(
            height, width, device=self.device,
            model_name=model_name, safety_factor=self.safety_factor
        )
        
        self._current_batch_size = batch_size
        return batch_size
    
    def adaptive_batch_size(self, height, width, model_name='partialconv'):
        if self.device == 'cpu' or not torch.cuda.is_available():
            return 1
        
        available = self.get_available_memory()
        per_image = estimate_gpu_memory_per_image(height, width, model_name=model_name)
        
        if per_image <= 0:
            return 1
        
        batch_size = int(available * self.safety_factor / per_image)
        batch_size = max(1, min(batch_size, 32))
        
        self._current_batch_size = batch_size
        return batch_size
    
    def release_memory(self):
        if self.device != 'cpu' and torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()
    
    def check_memory_status(self):
        if self.device == 'cpu' or not torch.cuda.is_available():
            return {'status': 'cpu', 'available': 'N/A', 'batch_size': 1}
        
        device_id = 0 if self.device == 'cuda' else int(self.device.split(':')[-1])
        total = torch.cuda.get_device_properties(device_id).total_memory
        allocated = torch.cuda.memory_allocated(device_id)
        available = total - allocated - torch.cuda.memory_reserved(device_id)
        
        return {
            'status': 'gpu',
            'total_mb': total / (1024 * 1024),
            'allocated_mb': allocated / (1024 * 1024),
            'available_mb': available / (1024 * 1024),
            'batch_size': self._current_batch_size,
            'utilization': allocated / total if total > 0 else 0
        }


class ImageInpainter:
    def __init__(self, 
                 model_name: str = 'partialconv',
                 device: str = None,
                 image_size: Tuple[int, int] = (256, 256),
                 poisson_blend_method: str = 'mixed',
                 feather_radius: int = 5,
                 enable_poisson_blend: bool = True):
        
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.device = device
        self.image_size = image_size
        self.model_name = model_name
        self.poisson_blend_method = poisson_blend_method
        self.feather_radius = feather_radius
        self.enable_poisson_blend = enable_poisson_blend
        
        self.model = load_pretrained_model(model_name, device)
        self.mask_generator = MaskGenerator(height=image_size[0], width=image_size[1])
        self.evaluator = QualityEvaluator(device=device)
        self.memory_manager = GPUMemoryManager(device=device)
        
        print(f"Loaded {model_name} model on {device}")
        if enable_poisson_blend:
            print(f"Poisson blending enabled: method={poisson_blend_method}")
    
    def load_checkpoint(self, checkpoint_path: str):
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        if 'model_state_dict' in checkpoint:
            self.model.load_state_dict(checkpoint['model_state_dict'])
        else:
            self.model.load_state_dict(checkpoint)
        
        print(f"Loaded checkpoint from {checkpoint_path}")
    
    def inpaint(self, 
                image, 
                mask,
                return_numpy: bool = True,
                blend_method: str = None,
                feather_radius: int = None) -> np.ndarray:
        if isinstance(image, str):
            image = load_image(image, size=self.image_size, normalize=True)
        
        if isinstance(mask, str):
            mask = self.mask_generator.load_mask_from_file(mask)
        
        if isinstance(mask, np.ndarray) and len(mask.shape) == 2:
            mask = mask[:, :, np.newaxis]
        
        img_tensor = img2tensor(image, device=self.device)
        mask_tensor = img2tensor(mask, device=self.device) if isinstance(mask, np.ndarray) else mask.to(self.device)
        
        if mask_tensor.shape[1] == 3:
            mask_tensor = mask_tensor[:, :1, :, :]
        
        original_img = image.copy() if isinstance(image, np.ndarray) else image
        
        self.model.eval()
        with torch.no_grad():
            if self.model_name == 'edgeconnect':
                output, _ = self.model(img_tensor, mask_tensor)
            else:
                output = self.model(img_tensor, mask_tensor)
        
        output = output * mask_tensor + img_tensor * (1 - mask_tensor)
        
        if return_numpy:
            output = tensor2img(output)
        
        use_blend = self.enable_poisson_blend
        method = blend_method if blend_method is not None else self.poisson_blend_method
        radius = feather_radius if feather_radius is not None else self.feather_radius
        
        if use_blend and isinstance(output, np.ndarray):
            try:
                mask_2d = mask[:, :, 0] if mask.ndim == 3 else mask
                output = poisson_blend(
                    output, original_img, mask_2d,
                    method=method, feather_radius=radius
                )
            except (cv2.error, Exception) as e:
                import warnings
                warnings.warn(f"Poisson blending failed, using raw output: {e}")
        
        return output
    
    def inpaint_batch_tensor(self, images_tensor, masks_tensor, blend=True):
        batch_size = images_tensor.shape[0]
        
        self.model.eval()
        with torch.no_grad():
            if self.model_name == 'edgeconnect':
                outputs, _ = self.model(images_tensor, masks_tensor)
            else:
                outputs = self.model(images_tensor, masks_tensor)
        
        outputs = outputs * masks_tensor + images_tensor * (1 - masks_tensor)
        
        results = []
        for i in range(batch_size):
            output = tensor2img(outputs[i:i+1])
            
            if blend and self.enable_poisson_blend:
                original = tensor2img(images_tensor[i:i+1])
                mask = tensor2img(masks_tensor[i:i+1])
                
                if mask.ndim == 3 and mask.shape[2] == 1:
                    mask_2d = mask[:, :, 0]
                elif mask.ndim == 2:
                    mask_2d = mask
                else:
                    mask_2d = mask[:, :, 0]
                
                try:
                    output = poisson_blend(
                        output, original, mask_2d,
                        method=self.poisson_blend_method,
                        feather_radius=self.feather_radius
                    )
                except (cv2.error, Exception):
                    pass
            
            results.append(output)
        
        return results
    
    def inpaint_with_auto_mask(self, 
                                image_path: str,
                                mask_type: str = 'random',
                                **mask_kwargs):
        image = load_image(image_path, size=self.image_size, normalize=True)
        
        h, w = image.shape[:2]
        if (h, w) != self.image_size:
            self.mask_generator.resize(h, w)
        
        mask = self.mask_generator.generate_mask(mask_type, **mask_kwargs)
        
        result = self.inpaint(image, mask)
        
        return image, mask, result
    
    def batch_inpaint(self,
                     input_dir: str,
                     output_dir: str,
                     mask_dir: Optional[str] = None,
                     mask_type: str = 'random',
                     save_visualization: bool = True,
                     evaluate: bool = False,
                     dynamic_batch: bool = True,
                     max_batch_size: int = 32,
                     **mask_kwargs) -> Dict:
        create_directory(output_dir)
        
        if save_visualization:
            viz_dir = os.path.join(output_dir, 'visualizations')
            create_directory(viz_dir)
        
        image_paths = get_image_list(input_dir)
        
        if len(image_paths) == 0:
            raise ValueError(f"No images found in {input_dir}")
        
        print(f"Found {len(image_paths)} images to process")
        
        if dynamic_batch and self.device != 'cpu' and torch.cuda.is_available():
            h, w = self.image_size
            batch_size = self.memory_manager.adaptive_batch_size(h, w, self.model_name)
            batch_size = min(batch_size, max_batch_size)
            
            mem_status = self.memory_manager.check_memory_status()
            print(f"Dynamic batching: batch_size={batch_size}")
            if isinstance(mem_status.get('available_mb'), (int, float)):
                print(f"  GPU memory: {mem_status['available_mb']:.0f}MB available / {mem_status['total_mb']:.0f}MB total")
        else:
            batch_size = 1
        
        results = []
        all_originals = []
        all_inpainteds = []
        all_masks = []
        
        if batch_size > 1:
            results, all_originals, all_inpainteds, all_masks = self._batch_process(
                image_paths, output_dir, viz_dir, mask_dir, mask_type,
                save_visualization, evaluate, batch_size, **mask_kwargs
            )
        else:
            results, all_originals, all_inpainteds, all_masks = self._sequential_process(
                image_paths, output_dir, viz_dir, mask_dir, mask_type,
                save_visualization, evaluate, **mask_kwargs
            )
        
        evaluation_results = None
        if evaluate and len(all_originals) > 0:
            avg_results, individual_results = self.evaluator.evaluate_batch(
                all_originals, all_inpainteds, all_masks, only_masked_region=True
            )
            
            for i, res in enumerate(results):
                if i < len(individual_results):
                    res['metrics'] = individual_results[i]
            
            evaluation_results = avg_results
            print("\nBatch Evaluation Results:")
            self.evaluator.print_results(avg_results)
        
        return {
            'num_processed': len(results),
            'results': results,
            'evaluation': evaluation_results
        }
    
    def _batch_process(self, image_paths, output_dir, viz_dir, mask_dir,
                        mask_type, save_visualization, evaluate, batch_size, **mask_kwargs):
        results = []
        all_originals = []
        all_inpainteds = []
        all_masks = []
        
        batch_images = []
        batch_masks = []
        batch_info = []
        
        for idx, img_path in enumerate(tqdm(image_paths, desc=f"Inpainting (batch={batch_size})")):
            img_name = os.path.basename(img_path)
            name, ext = os.path.splitext(img_name)
            
            image = load_image(img_path, size=self.image_size, normalize=True)
            
            if mask_dir is not None:
                mask_path = os.path.join(mask_dir, f"{name}.png")
                if os.path.exists(mask_path):
                    mask = self.mask_generator.load_mask_from_file(mask_path)
                else:
                    h, w = image.shape[:2]
                    self.mask_generator.resize(h, w)
                    mask = self.mask_generator.generate_mask(mask_type, **mask_kwargs)
            else:
                h, w = image.shape[:2]
                self.mask_generator.resize(h, w)
                mask = self.mask_generator.generate_mask(mask_type, **mask_kwargs)
            
            if mask.ndim == 2:
                mask = mask[:, :, np.newaxis]
            
            img_tensor = img2tensor(image, device=self.device)
            mask_tensor = img2tensor(mask, device=self.device)
            if mask_tensor.shape[1] == 3:
                mask_tensor = mask_tensor[:, :1, :, :]
            
            batch_images.append(img_tensor)
            batch_masks.append(mask_tensor)
            batch_info.append({
                'image_path': img_path,
                'name': name,
                'ext': ext,
                'original': image,
                'mask': mask
            })
            
            if len(batch_images) == batch_size or idx == len(image_paths) - 1:
                images_batch = torch.cat(batch_images, dim=0)
                masks_batch = torch.cat(batch_masks, dim=0)
                
                try:
                    batch_results = self.inpaint_batch_tensor(images_batch, masks_batch, blend=True)
                except RuntimeError as e:
                    if 'out of memory' in str(e):
                        print(f"\n  OOM at batch_size={len(batch_images)}, falling back to sequential")
                        self.memory_manager.release_memory()
                        
                        for j, info in enumerate(batch_info):
                            single_result = self.inpaint(info['original'], info['mask'])
                            batch_results_data = batch_results if 'batch_results' in dir() else [None] * len(batch_info)
                            
                            output_path = os.path.join(output_dir, f"{info['name']}_inpainted{info['ext']}")
                            save_image(single_result, output_path)
                            
                            results.append({
                                'image_path': info['image_path'],
                                'output_path': output_path,
                                'mask_type': mask_type,
                                'batch_mode': 'sequential_fallback'
                            })
                            
                            if evaluate:
                                all_originals.append(info['original'])
                                all_inpainteds.append(single_result)
                                all_masks.append(info['mask'])
                        
                        batch_images = []
                        batch_masks = []
                        batch_info = []
                        continue
                    else:
                        raise e
                
                for j, (result, info) in enumerate(zip(batch_results, batch_info)):
                    output_path = os.path.join(output_dir, f"{info['name']}_inpainted{info['ext']}")
                    save_image(result, output_path)
                    
                    if save_visualization:
                        self._save_visualization(info['original'], info['mask'], result, viz_dir, info['name'])
                    
                    if evaluate:
                        all_originals.append(info['original'])
                        all_inpainteds.append(result)
                        all_masks.append(info['mask'])
                    
                    results.append({
                        'image_path': info['image_path'],
                        'output_path': output_path,
                        'mask_type': mask_type,
                        'batch_mode': 'dynamic'
                    })
                
                batch_images = []
                batch_masks = []
                batch_info = []
                
                if idx % (batch_size * 4) == 0 and idx > 0:
                    self.memory_manager.release_memory()
        
        return results, all_originals, all_inpainteds, all_masks
    
    def _sequential_process(self, image_paths, output_dir, viz_dir, mask_dir,
                             mask_type, save_visualization, evaluate, **mask_kwargs):
        results = []
        all_originals = []
        all_inpainteds = []
        all_masks = []
        
        for img_path in tqdm(image_paths, desc="Inpainting"):
            img_name = os.path.basename(img_path)
            name, ext = os.path.splitext(img_name)
            
            image = load_image(img_path, size=self.image_size, normalize=True)
            
            if mask_dir is not None:
                mask_path = os.path.join(mask_dir, f"{name}.png")
                if os.path.exists(mask_path):
                    mask = self.mask_generator.load_mask_from_file(mask_path)
                else:
                    h, w = image.shape[:2]
                    self.mask_generator.resize(h, w)
                    mask = self.mask_generator.generate_mask(mask_type, **mask_kwargs)
            else:
                h, w = image.shape[:2]
                self.mask_generator.resize(h, w)
                mask = self.mask_generator.generate_mask(mask_type, **mask_kwargs)
            
            result = self.inpaint(image, mask)
            
            output_path = os.path.join(output_dir, f"{name}_inpainted{ext}")
            save_image(result, output_path)
            
            if save_visualization:
                self._save_visualization(image, mask, result, viz_dir, name)
            
            if evaluate:
                all_originals.append(image)
                all_inpainteds.append(result)
                all_masks.append(mask)
            
            results.append({
                'image_path': img_path,
                'output_path': output_path,
                'mask_type': mask_type,
                'batch_mode': 'sequential'
            })
        
        return results, all_originals, all_inpainteds, all_masks
    
    def _save_visualization(self, image, mask, result, viz_dir, name):
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        axes[0].imshow(image)
        axes[0].set_title('Original')
        axes[0].axis('off')
        
        if mask.ndim == 2:
            mask_3d = mask[:, :, np.newaxis]
        else:
            mask_3d = mask
        
        masked_img = image * (1 - mask_3d) + mask_3d
        axes[1].imshow(masked_img)
        axes[1].set_title('Masked')
        axes[1].axis('off')
        
        axes[2].imshow(result)
        axes[2].set_title('Inpainted (Poisson Blended)')
        axes[2].axis('off')
        
        plt.tight_layout()
        plt.savefig(os.path.join(viz_dir, f"{name}_viz.png"), dpi=100, bbox_inches='tight')
        plt.close()
    
    def inpaint_watermark(self, 
                          image_path: str,
                          text: str = None,
                          font_scale: float = None,
                          thickness: int = None,
                          rotation: int = None):
        return self.inpaint_with_auto_mask(
            image_path, 
            mask_type='watermark',
            text=text,
            font_scale=font_scale,
            thickness=thickness,
            rotation=rotation
        )
    
    def inpaint_scratch(self,
                         image_path: str,
                         num_scratches: int = None):
        return self.inpaint_with_auto_mask(
            image_path,
            mask_type='scratch',
            num_scratches=num_scratches
        )
    
    def inpaint_text(self,
                      image_path: str,
                      text: str = None):
        return self.inpaint_with_auto_mask(
            image_path,
            mask_type='text',
            text=text
        )
    
    def evaluate_inpainting(self,
                            original: np.ndarray,
                            inpainted: np.ndarray,
                            mask: Optional[np.ndarray] = None,
                            only_masked_region: bool = False,
                            detailed: bool = False) -> Dict:
        return self.evaluator.evaluate_all(
            original, inpainted, mask, only_masked_region, detailed=detailed
        )
    
    def print_evaluation(self, results: Dict):
        self.evaluator.print_results(results)
    
    def set_image_size(self, height: int, width: int):
        self.image_size = (height, width)
        self.mask_generator.resize(height, width)
    
    def set_blend_method(self, method: str, feather_radius: int = 5):
        self.poisson_blend_method = method
        self.feather_radius = feather_radius
    
    def to(self, device: str):
        self.device = device
        self.model = self.model.to(device)
        self.evaluator.device = device
        if self.evaluator.loss_fn_vgg is not None:
            self.evaluator.loss_fn_vgg = self.evaluator.loss_fn_vgg.to(device)
        if self.evaluator.loss_fn_alex is not None:
            self.evaluator.loss_fn_alex = self.evaluator.loss_fn_alex.to(device)
        if self.evaluator.loss_fn_squeeze is not None:
            self.evaluator.loss_fn_squeeze = self.evaluator.loss_fn_squeeze.to(device)
        self.memory_manager.device = device


class InpaintingDemo:
    @staticmethod
    def run_single_image_demo(image_path: str, 
                               model_name: str = 'partialconv',
                               mask_type: str = 'random',
                               output_path: str = None,
                               blend_method: str = 'mixed'):
        inpainter = ImageInpainter(model_name=model_name, poisson_blend_method=blend_method)
        
        image, mask, result = inpainter.inpaint_with_auto_mask(
            image_path, mask_type=mask_type
        )
        
        metrics = inpainter.evaluate_inpainting(image, result, mask, only_masked_region=True, detailed=True)
        
        print("\nInpainting Results:")
        inpainter.print_evaluation(metrics)
        
        if output_path:
            save_image(result, output_path)
            print(f"\nResult saved to: {output_path}")
        
        return image, mask, result, metrics
    
    @staticmethod
    def compare_blend_methods(image_path: str,
                               mask_type: str = 'watermark',
                               output_dir: str = 'blend_comparison'):
        create_directory(output_dir)
        
        blend_methods = ['seamless_normal', 'seamless_mixed', 'feathered', 'gradient', 'multi_pass']
        
        inpainter = ImageInpainter(model_name='partialconv', enable_poisson_blend=False)
        
        image = load_image(image_path, size=inpainter.image_size, normalize=True)
        mask_gen = MaskGenerator(inpainter.image_size[0], inpainter.image_size[1])
        mask = mask_gen.generate_mask(mask_type)
        
        raw_result = inpainter.inpaint(image, mask)
        
        results = {'raw': {'result': raw_result, 'metrics': None}}
        
        for method in blend_methods:
            inpainter.set_blend_method(method)
            inpainter.enable_poisson_blend = True
            
            blended = poisson_blend(raw_result, image, mask, method=method)
            
            metrics = inpainter.evaluate_inpainting(image, blended, mask, only_masked_region=True)
            
            results[method] = {'result': blended, 'metrics': metrics}
            
            save_path = os.path.join(output_dir, f"blend_{method}.png")
            save_image(blended, save_path)
        
        print("\n" + "=" * 60)
        print("Blend Method Comparison:")
        print("=" * 60)
        for method, res in results.items():
            if res['metrics']:
                print(f"\n{method.upper()}:")
                for metric, value in res['metrics'].items():
                    print(f"  {metric}: {value:.4f}")
        
        return results
    
    @staticmethod
    def compare_models(image_path: str, 
                        mask_type: str = 'watermark',
                        output_dir: str = 'comparison_results'):
        create_directory(output_dir)
        
        models = ['partialconv', 'edgeconnect']
        results = {}
        
        for model_name in models:
            print(f"\n{'='*50}")
            print(f"Testing {model_name}...")
            print('='*50)
            
            inpainter = ImageInpainter(model_name=model_name)
            
            image, mask, result = inpainter.inpaint_with_auto_mask(
                image_path, mask_type=mask_type
            )
            
            metrics = inpainter.evaluate_inpainting(image, result, mask, only_masked_region=True, detailed=True)
            
            results[model_name] = {
                'image': image,
                'mask': mask,
                'result': result,
                'metrics': metrics
            }
            
            save_path = os.path.join(output_dir, f"{model_name}_result.png")
            save_image(result, save_path)
        
        print("\n" + "="*50)
        print("Model Comparison:")
        print("="*50)
        for model_name, res in results.items():
            print(f"\n{model_name.upper()}:")
            for metric, value in res['metrics'].items():
                print(f"  {metric}: {value:.4f}")
        
        return results
