import os
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from config import Config
from data.transforms import preprocess_image, postprocess_saliency, preprocess_batch, postprocess_batch
from utils.helpers import load_image, save_image
from .post_processing import postprocess_saliency_map
from .dynamic_batch import GPUMemoryMonitor, DynamicBatchProcessor


@dataclass
class InferenceStats:
    preprocess_time: float = 0.0
    inference_time: float = 0.0
    postprocess_time: float = 0.0
    total_time: float = 0.0
    memory_used: float = 0.0


class SaliencyInferencer:
    def __init__(self, model_name=None, pretrained=True, device=None,
                 use_tensorrt=None, use_dynamic_batch=True):
        if model_name is None:
            model_name = Config.DEFAULT_MODEL
        if device is None:
            device = Config.get_device()
        if use_tensorrt is None:
            use_tensorrt = Config.USE_TENSORRT
        
        self.device = device
        self.model_name = model_name.lower()
        self.use_tensorrt = use_tensorrt and device != 'cpu'
        self.use_dynamic_batch = use_dynamic_batch
        
        self._torch_model = None
        self._trt_engine = None
        
        self.memory_monitor = GPUMemoryMonitor()
        self.inference_stats = InferenceStats()
        self._target_time = Config.TARGET_INFERENCE_TIME / 1000.0
        
        self._initialize_model(pretrained)
    
    def _initialize_model(self, pretrained):
        if self.use_tensorrt:
            trt_success = self._try_load_tensorrt()
            if not trt_success:
                print("TensorRT not available, falling back to PyTorch")
                self.use_tensorrt = False
                self._load_torch_model(pretrained)
        else:
            self._load_torch_model(pretrained)
    
    def _load_torch_model(self, pretrained):
        import torch
        from models import get_model
        
        print(f"Loading PyTorch model: {self.model_name}")
        self._torch_model = get_model(self.model_name, pretrained=pretrained, device=self.device)
        self._torch_model.eval()
    
    def _try_load_tensorrt(self) -> bool:
        try:
            from models import load_tensorrt_engine
            
            trt_path = self._get_trt_path()
            if not os.path.exists(trt_path):
                print(f"TensorRT engine not found at {trt_path}")
                print("Use convert_model_to_tensorrt() to create one")
                return False
            
            print(f"Loading TensorRT engine: {trt_path}")
            self._trt_engine = load_tensorrt_engine(trt_path, batch_size=1)
            
            return self._trt_engine is not None
            
        except ImportError as e:
            print(f"TensorRT import failed: {e}")
            return False
        except Exception as e:
            print(f"TensorRT load failed: {e}")
            return False
    
    def _get_trt_path(self) -> str:
        if self.model_name == 'basnet':
            return Config.BASNET_TRT
        elif self.model_name == 'poolnet':
            return Config.POOLNET_TRT
        else:
            return os.path.join(Config.CHECKPOINT_DIR, f'{self.model_name}.trt')
    
    def _get_onnx_path(self) -> str:
        if self.model_name == 'basnet':
            return Config.BASNET_ONNX
        elif self.model_name == 'poolnet':
            return Config.POOLNET_ONNX
        else:
            return os.path.join(Config.CHECKPOINT_DIR, f'{self.model_name}.onnx')
    
    def convert_model_to_tensorrt(self, max_batch_size=8, fp16=True, int8=False, calibration_data=None) -> bool:
        if self._torch_model is None:
            self._load_torch_model(pretrained=False)
        
        trt_path = self._get_trt_path()
        
        print(f"Converting {self.model_name} to TensorRT...")
        
        success = self._torch_model.export_to_tensorrt(
            trt_path,
            input_size=Config.IMAGE_SIZE,
            max_batch_size=max_batch_size,
            fp16=fp16,
            int8=int8,
            calibration_data=calibration_data
        )
        
        if success:
            print(f"TensorRT engine saved to {trt_path}")
            if self._trt_engine is None:
                self._try_load_tensorrt()
                self.use_tensorrt = self._trt_engine is not None
            return True
        else:
            print("TensorRT conversion failed")
            return False
    
    def _inference_torch(self, tensor):
        import torch
        with torch.no_grad():
            output = self._torch_model(tensor)
        return output
    
    def _inference_tensorrt(self, tensor):
        if self._trt_engine is None:
            raise RuntimeError("TensorRT engine not loaded")
        
        import torch
        if isinstance(tensor, torch.Tensor):
            tensor = tensor.detach().cpu().numpy()
        
        if tensor.ndim == 3:
            tensor = np.expand_dims(tensor, axis=0)
        
        output = self._trt_engine.infer_batch(tensor)
        
        output = output.reshape(tensor.shape[0], 1, Config.IMAGE_SIZE, Config.IMAGE_SIZE)
        
        return output
    
    def _inference(self, tensor):
        if self.use_tensorrt and self._trt_engine is not None:
            return self._inference_tensorrt(tensor)
        else:
            return self._inference_torch(tensor)
    
    def predict(self, image, threshold=None, edge_refinement=True, 
                refine_method='guided', measure_time=False) -> Dict[str, Any]:
        start_time = time.time()
        stats = InferenceStats()
        
        if threshold is None:
            threshold = Config.THRESHOLD
        
        if isinstance(image, str):
            image = load_image(image)
        
        preprocess_start = time.time()
        tensor, original_size = preprocess_image(image)
        tensor = tensor.to(self.device)
        stats.preprocess_time = time.time() - preprocess_start
        
        inference_start = time.time()
        self.memory_monitor.reset_peak_memory()
        
        output = self._inference(tensor)
        
        stats.inference_time = time.time() - inference_start
        stats.memory_used = self.memory_monitor.get_peak_memory()
        
        postprocess_start = time.time()
        saliency_map, binary_mask = postprocess_saliency(output, original_size, threshold)
        
        if edge_refinement and Config.EDGE_THINNING:
            saliency_map, binary_mask = postprocess_saliency_map(
                saliency_map, binary_mask, threshold=threshold,
                refine_method=refine_method, original_image=image
            )
        
        stats.postprocess_time = time.time() - postprocess_start
        stats.total_time = time.time() - start_time
        
        if measure_time:
            self.inference_stats = stats
        
        result = {
            'saliency_map': saliency_map,
            'binary_mask': binary_mask,
            'original_image': image,
            'original_size': original_size,
        }
        
        if measure_time:
            result['stats'] = {
                'preprocess_time_ms': stats.preprocess_time * 1000,
                'inference_time_ms': stats.inference_time * 1000,
                'postprocess_time_ms': stats.postprocess_time * 1000,
                'total_time_ms': stats.total_time * 1000,
                'memory_mb': stats.memory_used / (1024 * 1024),
                'target_time_ms': self._target_time * 1000,
                'meets_target': stats.inference_time <= self._target_time
            }
        
        return result
    
    def predict_batch(self, images, threshold=None, edge_refinement=True,
                      refine_method='guided', dynamic_batch=None,
                      measure_time=False) -> List[Dict[str, Any]]:
        if threshold is None:
            threshold = Config.THRESHOLD
        if dynamic_batch is None:
            dynamic_batch = self.use_dynamic_batch
        
        loaded_images = []
        for img in images:
            if isinstance(img, str):
                loaded_images.append(load_image(img))
            else:
                loaded_images.append(img)
        
        if dynamic_batch:
            return self._predict_dynamic_batch(
                loaded_images, threshold, edge_refinement, refine_method, measure_time
            )
        else:
            return self._predict_fixed_batch(
                loaded_images, threshold, edge_refinement, refine_method, measure_time
            )
    
    def _predict_fixed_batch(self, loaded_images, threshold, edge_refinement,
                              refine_method, measure_time) -> List[Dict[str, Any]]:
        batch_tensor, original_sizes = preprocess_batch(loaded_images)
        batch_tensor = batch_tensor.to(self.device)
        
        with torch.no_grad():
            outputs = self._inference(batch_tensor)
        
        results = postprocess_batch(outputs, original_sizes, threshold)
        
        if edge_refinement and Config.EDGE_THINNING:
            for i, result in enumerate(results):
                refined_saliency, refined_mask = postprocess_saliency_map(
                    result['saliency_map'], result['binary_mask'],
                    threshold=threshold, refine_method=refine_method,
                    original_image=loaded_images[i]
                )
                results[i]['saliency_map'] = refined_saliency
                results[i]['binary_mask'] = refined_mask
        
        for i, result in enumerate(results):
            result['original_image'] = loaded_images[i]
            result['original_size'] = original_sizes[i]
        
        return results
    
    def _predict_dynamic_batch(self, loaded_images, threshold, edge_refinement,
                                refine_method, measure_time) -> List[Dict[str, Any]]:
        def process_batch(batch_images):
            return self._predict_fixed_batch(
                batch_images, threshold, edge_refinement,
                refine_method, measure_time=False
            )
        
        processor = DynamicBatchProcessor(
            process_func=process_batch,
            initial_batch_size=Config.BATCH_SIZE,
            min_batch_size=1,
            max_batch_size=Config.MAX_BATCH_SIZE
        )
        
        results = processor.process(loaded_images, show_progress=True)
        
        final_results = []
        for i, batch_results in enumerate(results):
            if batch_results is None:
                final_results.append(None)
            else:
                if isinstance(batch_results, list):
                    final_results.extend(batch_results)
                else:
                    final_results.append(batch_results)
        
        return final_results
    
    def predict_and_save(self, image_path, output_dir=None, threshold=None, 
                         edge_refinement=True, refine_method='guided',
                         measure_time=False):
        if output_dir is None:
            output_dir = Config.OUTPUT_DIR
        
        result = self.predict(image_path, threshold, edge_refinement, 
                              refine_method, measure_time)
        
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        
        saliency_path = os.path.join(output_dir, f'{name}_saliency.png')
        mask_path = os.path.join(output_dir, f'{name}_mask.png')
        
        save_image((result['saliency_map'] * 255).astype(np.uint8), saliency_path)
        save_image((result['binary_mask'] * 255).astype(np.uint8), mask_path)
        
        result['saliency_path'] = saliency_path
        result['mask_path'] = mask_path
        
        return result
    
    def benchmark_inference(self, image, num_runs=100, warmup_runs=10) -> Dict[str, float]:
        if isinstance(image, str):
            image = load_image(image)
        
        tensor, original_size = preprocess_image(image)
        tensor = tensor.to(self.device)
        
        print(f"Benchmarking {self.model_name} inference...")
        print(f"{'=' * 50}")
        
        for _ in range(warmup_runs):
            _ = self._inference(tensor)
        
        times = []
        for i in range(num_runs):
            start = time.time()
            _ = self._inference(tensor)
            elapsed = time.time() - start
            times.append(elapsed * 1000)
        
        times = np.array(times)
        
        stats = {
            'model': self.model_name,
            'engine': 'TensorRT' if self.use_tensorrt else 'PyTorch',
            'mean_ms': float(times.mean()),
            'median_ms': float(np.median(times)),
            'min_ms': float(times.min()),
            'max_ms': float(times.max()),
            'std_ms': float(times.std()),
            'target_ms': self._target_time * 1000,
            'meets_target': float(times.mean()) <= self._target_time * 1000,
            'num_runs': num_runs
        }
        
        print(f"Mean:     {stats['mean_ms']:.2f} ms")
        print(f"Median:   {stats['median_ms']:.2f} ms")
        print(f"Min:      {stats['min_ms']:.2f} ms")
        print(f"Max:      {stats['max_ms']:.2f} ms")
        print(f"Std:      {stats['std_ms']:.2f} ms")
        print(f"Target:   {stats['target_ms']:.1f} ms")
        print(f"Meets target: {stats['meets_target']}")
        print(f"{'=' * 50}")
        
        return stats
    
    def get_model_info(self):
        from models import list_models
        
        return {
            'current_model': self.model_name,
            'available_models': list_models(),
            'device': self.device,
            'use_tensorrt': self.use_tensorrt,
            'engine': 'TensorRT' if self.use_tensorrt else 'PyTorch',
            'target_inference_time_ms': self._target_time * 1000
        }
    
    def switch_model(self, model_name, pretrained=True):
        model_name = model_name.lower()
        if model_name != self.model_name:
            self.model_name = model_name
            self._torch_model = None
            self._trt_engine = None
            self._initialize_model(pretrained)
        return self.get_model_info()
    
    def switch_engine(self, use_tensorrt: bool):
        if use_tensorrt and not self._trt_engine:
            success = self._try_load_tensorrt()
            if not success:
                print("Could not enable TensorRT, keeping current engine")
                return self.use_tensorrt
        
        self.use_tensorrt = use_tensorrt and self._trt_engine is not None
        engine_type = 'TensorRT' if self.use_tensorrt else 'PyTorch'
        print(f"Switched to {engine_type} inference")
        return self.use_tensorrt
    
    def clear_gpu_memory(self):
        try:
            import torch
            torch.cuda.empty_cache()
            print("GPU memory cleared")
        except:
            pass


import torch
