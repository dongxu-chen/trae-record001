import os
import time
import numpy as np
from typing import Optional, Dict, Tuple, List
from pathlib import Path
from collections import OrderedDict

try:
    import torch
    from segment_anything import sam_model_registry, SamPredictor
    SAM_AVAILABLE = True
except ImportError:
    SAM_AVAILABLE = False
    torch = None

import cv2
from PIL import Image

from schemas import Point, SAMResponse


class LRUCache:
    def __init__(self, max_size: int = 100):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional:
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def set(self, key: str, value) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        self.cache.clear()

    def __len__(self) -> int:
        return len(self.cache)


class SAMModelService:
    _instance = None
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
        self.predictor: Optional[SamPredictor] = None
        self.model_loaded = False
        self.model_type = "vit_b"
        self.device = "cpu"
        self.use_half_precision = False
        
        if SAM_AVAILABLE and torch is not None:
            try:
                if torch.cuda.is_available():
                    self.device = "cuda"
                    self.use_half_precision = True
                    gpu_name = torch.cuda.get_device_name(0)
                    gpu_memory = torch.cuda.get_device_properties(0).total_mem / 1024**3
                    print(f"GPU detected: {gpu_name} ({gpu_memory:.1f} GB)")
                else:
                    self.device = "cpu"
                    print("CUDA not available, using CPU")
            except Exception as e:
                print(f"Error detecting GPU: {e}")
                self.device = "cpu"
        
        self.image_embeddings_cache: Dict[str, torch.Tensor] = {}
        self.prediction_cache = LRUCache(max_size=1000)
        self.current_image_id: Optional[str] = None
        self.current_image: Optional[np.ndarray] = None
        
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_predictions": 0,
            "avg_prediction_time": 0.0,
            "total_time": 0.0,
        }
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_model_path(self) -> Path:
        model_filenames = {
            "vit_h": "sam_vit_h_4b8939.pth",
            "vit_l": "sam_vit_l_0b3195.pth",
            "vit_b": "sam_vit_b_01ec64.pth",
        }
        return self.models_dir / model_filenames.get(self.model_type, "sam_vit_b_01ec64.pth")
    
    def is_model_available(self) -> bool:
        if not SAM_AVAILABLE:
            return False
        return self.get_model_path().exists()
    
    def load_model(self, model_type: str = "vit_b", use_gpu: bool = True) -> bool:
        if not SAM_AVAILABLE or torch is None:
            print("SAM model not available. Please install segment-anything and torch.")
            return False
            
        try:
            self.model_type = model_type
            model_path = self.get_model_path()
            
            if not model_path.exists():
                print(f"Model file not found: {model_path}")
                print(f"Please download the model weights and place them in {self.models_dir}")
                print("Download from: https://dl.fbaipublicfiles.com/segment_anything/")
                return False
            
            if use_gpu and self.device == "cuda":
                print(f"Loading SAM model ({self.model_type}) on GPU with half precision...")
            else:
                self.device = "cpu"
                self.use_half_precision = False
                print(f"Loading SAM model ({self.model_type}) on CPU...")
            
            sam = sam_model_registry[self.model_type](checkpoint=str(model_path))
            sam.to(device=self.device)
            
            if self.use_half_precision and self.device == "cuda":
                sam = sam.half()
            
            self.predictor = SamPredictor(sam)
            self.model_loaded = True
            print(f"SAM model loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            print(f"Error loading SAM model: {e}")
            self.model_loaded = False
            return False
    
    def set_image(self, image_id: str, image: np.ndarray) -> None:
        if not self.model_loaded or self.predictor is None:
            return
            
        if image_id in self.image_embeddings_cache:
            cached_embedding = self.image_embeddings_cache[image_id]
            self.predictor.features = cached_embedding
            self.predictor.original_size = image.shape[:2]
            self.predictor.is_image_set = True
        else:
            with torch.no_grad():
                if self.use_half_precision and self.device == "cuda":
                    input_image = torch.from_numpy(image).permute(2, 0, 1).float().unsqueeze(0)
                    input_image = input_image.to(device=self.device).half()
                    self.predictor.set_image(input_image)
                else:
                    self.predictor.set_image(image)
            
            self.image_embeddings_cache[image_id] = self.predictor.features
            
        self.current_image_id = image_id
        self.current_image = image
    
    def predict(
        self,
        image_id: str,
        point: Point,
        image: Optional[np.ndarray] = None,
        multimask_output: bool = True,
        use_cache: bool = True
    ) -> Optional[SAMResponse]:
        if not self.model_loaded or self.predictor is None:
            return None
            
        start_time = time.time()
        
        cache_key = f"{image_id}_{point.x:.1f}_{point.y:.1f}"
        
        if use_cache:
            cached_result = self.prediction_cache.get(cache_key)
            if cached_result is not None:
                self._stats["cache_hits"] += 1
                return cached_result
        
        self._stats["cache_misses"] += 1
        self._stats["total_predictions"] += 1
            
        try:
            if image_id != self.current_image_id:
                if image is not None:
                    self.set_image(image_id, image)
                elif image_id in self.image_embeddings_cache:
                    self.current_image_id = image_id
                    if self.predictor is not None:
                        self.predictor.features = self.image_embeddings_cache[image_id]
                        self.predictor.original_size = self.current_image.shape[:2] if self.current_image else None
                        self.predictor.is_image_set = True
                else:
                    return None
            
            input_point = np.array([[point.x, point.y]])
            input_label = np.array([1])
            
            with torch.no_grad():
                masks, scores, logits = self.predictor.predict(
                    point_coords=input_point,
                    point_labels=input_label,
                    multimask_output=multimask_output,
                )
            
            best_idx = np.argmax(scores)
            best_mask = masks[best_idx]
            best_score = float(scores[best_idx])
            
            best_mask = self._smooth_mask(best_mask)
            
            mask_uint8 = (best_mask.astype(np.uint8) * 255).flatten().tolist()
            
            result = SAMResponse(
                mask=mask_uint8,
                width=best_mask.shape[1],
                height=best_mask.shape[0],
                confidence=best_score
            )
            
            if use_cache:
                self.prediction_cache.set(cache_key, result)
            
            elapsed = time.time() - start_time
            self._stats["total_time"] += elapsed
            self._stats["avg_prediction_time"] = self._stats["total_time"] / self._stats["total_predictions"]
            
            return result
            
        except Exception as e:
            print(f"Error during SAM prediction: {e}")
            return None
    
    def _smooth_mask(self, mask: np.ndarray) -> np.ndarray:
        mask_uint8 = (mask * 255).astype(np.uint8)
        
        kernel_size = 3
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel, iterations=1)
        mask_uint8 = cv2.GaussianBlur(mask_uint8, (5, 5), 0)
        
        mask_uint8 = cv2.medianBlur(mask_uint8, 5)
        
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            epsilon = 0.001 * cv2.arcLength(contours[0], True)
            approx = cv2.approxPolyDP(contours[0], epsilon, True)
            mask_smoothed = np.zeros_like(mask_uint8)
            cv2.fillPoly(mask_smoothed, [approx], 255)
        else:
            mask_smoothed = mask_uint8
        
        return mask_smoothed > 127
    
    def batch_predict(
        self,
        image_id: str,
        points: List[Point],
        image: Optional[np.ndarray] = None,
        use_cache: bool = True
    ) -> List[SAMResponse]:
        results = []
        for point in points:
            result = self.predict(image_id, point, image, use_cache=use_cache)
            if result:
                results.append(result)
        return results
    
    def reset_image(self, image_id: str) -> None:
        if image_id in self.image_embeddings_cache:
            del self.image_embeddings_cache[image_id]
        
        keys_to_delete = [k for k in self.prediction_cache.cache.keys() if k.startswith(image_id)]
        for key in keys_to_delete:
            del self.prediction_cache.cache[key]
            
        if self.current_image_id == image_id:
            self.current_image_id = None
            self.current_image = None
            if self.predictor is not None:
                self.predictor.reset_image()
    
    def clear_cache(self) -> None:
        self.image_embeddings_cache.clear()
        self.prediction_cache.clear()
        self.current_image_id = None
        self.current_image = None
        if self.predictor is not None:
            self.predictor.reset_image()
        self._reset_stats()
    
    def _reset_stats(self) -> None:
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_predictions": 0,
            "avg_prediction_time": 0.0,
            "total_time": 0.0,
        }
    
    def get_status(self) -> dict:
        cache_hit_rate = 0.0
        total_requests = self._stats["cache_hits"] + self._stats["cache_misses"]
        if total_requests > 0:
            cache_hit_rate = (self._stats["cache_hits"] / total_requests) * 100
            
        return {
            "loaded": self.model_loaded,
            "modelType": self.model_type,
            "device": self.device,
            "useHalfPrecision": self.use_half_precision,
            "embeddingCacheSize": len(self.image_embeddings_cache),
            "predictionCacheSize": len(self.prediction_cache),
            "predictionCacheMax": self.prediction_cache.max_size,
            "samAvailable": SAM_AVAILABLE,
            "modelPath": str(self.get_model_path()) if self.is_model_available() else None,
            "gpuAvailable": SAM_AVAILABLE and torch is not None and torch.cuda.is_available(),
            "stats": {
                "cacheHits": self._stats["cache_hits"],
                "cacheMisses": self._stats["cache_misses"],
                "cacheHitRate": f"{cache_hit_rate:.1f}%",
                "totalPredictions": self._stats["total_predictions"],
                "avgPredictionTime": f"{self._stats['avg_prediction_time']*1000:.2f}ms",
                "totalTime": f"{self._stats['total_time']:.2f}s"
            }
        }


sam_service = SAMModelService.get_instance()
