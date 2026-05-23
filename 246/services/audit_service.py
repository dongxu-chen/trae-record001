import io
import uuid
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PIL import Image

from models.content_detector import detector
from cache.redis_cache import cache, CacheHitSource
from mq.rabbitmq_client import mq_client
from review.review_manager import review_manager
from config import config

class AuditService:
    def __init__(self):
        self.detector = detector
        self.cache = cache
        self.mq = mq_client
        self.review_manager = review_manager
    
    def _load_image(self, image_data: bytes) -> Tuple[Image.Image, bytes]:
        image = Image.open(io.BytesIO(image_data))
        return image, image_data
    
    def _load_image_from_base64(self, base64_str: str) -> Tuple[Image.Image, bytes]:
        if base64_str.startswith('data:image'):
            base64_str = base64_str.split(',')[1]
        image_data = base64.b64decode(base64_str)
        return self._load_image(image_data)
    
    def _process_cache_hit(self, result: Dict, cached_result: Dict, md5_hash: str) -> Dict:
        result.update(cached_result)
        result["cached"] = True
        result["cache_md5"] = md5_hash
        
        hit_source = cached_result.get("cache_hit_source", CacheHitSource.NONE)
        result["cache_hit_source"] = hit_source
        
        if hit_source != CacheHitSource.MD5 and hit_source != CacheHitSource.NONE:
            result["from_similar"] = True
            result["hash_distance"] = cached_result.get("hash_distance", 0)
        else:
            result["from_similar"] = False
        
        return result
    
    def audit_image_sync(
        self,
        image_data: bytes,
        enable_cache: bool = True,
        enable_review: bool = True,
        image_id: Optional[str] = None,
        use_multi_hash: bool = True
    ) -> Dict:
        if image_id is None:
            image_id = str(uuid.uuid4())
        
        result = {
            "image_id": image_id,
            "audit_time": datetime.utcnow().isoformat(),
            "cached": False,
            "from_similar": False,
            "cache_hit_source": CacheHitSource.NONE
        }
        
        if enable_cache:
            try:
                image, _ = self._load_image(image_data)
                cached_result, md5_hash = self.cache.get_cached_result(
                    image_data, image, use_multi_hash
                )
                if cached_result:
                    return self._process_cache_hit(result, cached_result, md5_hash)
            except Exception as e:
                print(f"Cache lookup error: {e}")
        
        try:
            image, _ = self._load_image(image_data)
            detect_result = self.detector.detect(image)
            result.update(detect_result)
            
            if enable_cache:
                self.cache.cache_with_multi_hash(image_data, image, detect_result)
            
            if enable_review:
                review_task = self.review_manager.auto_submit_for_review(image_id, detect_result)
                if review_task:
                    result["review_submitted"] = True
                    result["review_id"] = review_task["review_id"]
                    result["review_priority"] = review_task["priority"]
            
            self.mq.publish_result(result)
            
        except Exception as e:
            result["error"] = str(e)
            result["risk_level"] = "unknown"
        
        return result
    
    def audit_image_async(
        self,
        image_data: bytes,
        callback_url: Optional[str] = None,
        enable_cache: bool = True,
        image_id: Optional[str] = None,
        use_multi_hash: bool = True
    ) -> Dict:
        if image_id is None:
            image_id = str(uuid.uuid4())
        
        task_id = str(uuid.uuid4())
        
        if enable_cache:
            try:
                image, _ = self._load_image(image_data)
                cached_result, md5_hash = self.cache.get_cached_result(
                    image_data, image, use_multi_hash
                )
                if cached_result:
                    return {
                        "task_id": task_id,
                        "image_id": image_id,
                        "status": "completed",
                        "cached": True,
                        "cache_hit_source": cached_result.get("cache_hit_source", CacheHitSource.NONE),
                        "result": cached_result
                    }
            except Exception as e:
                print(f"Cache lookup error: {e}")
        
        task_data = {
            "task_id": task_id,
            "image_id": image_id,
            "image_data": base64.b64encode(image_data).decode('utf-8'),
            "callback_url": callback_url,
            "enable_cache": enable_cache,
            "use_multi_hash": use_multi_hash,
            "created_at": datetime.utcnow().isoformat()
        }
        
        success = self.mq.publish_async_task(task_data)
        
        return {
            "task_id": task_id,
            "image_id": image_id,
            "status": "queued" if success else "failed",
            "queue_position": self.mq.get_async_queue_size()
        }
    
    def audit_batch_sync(
        self,
        images_data: List[bytes],
        enable_cache: bool = True,
        enable_review: bool = True,
        use_multi_hash: bool = True
    ) -> List[Dict]:
        if len(images_data) > config.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size exceeds maximum of {config.MAX_BATCH_SIZE}")
        
        results = []
        for idx, image_data in enumerate(images_data):
            image_id = f"batch_{uuid.uuid4()}_{idx}"
            result = self.audit_image_sync(
                image_data,
                enable_cache=enable_cache,
                enable_review=enable_review,
                image_id=image_id,
                use_multi_hash=use_multi_hash
            )
            results.append(result)
        
        return results
    
    def audit_batch_async(
        self,
        images_data: List[bytes],
        callback_url: Optional[str] = None,
        enable_cache: bool = True,
        use_multi_hash: bool = True
    ) -> Dict:
        if len(images_data) > config.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size exceeds maximum of {config.MAX_BATCH_SIZE}")
        
        batch_id = str(uuid.uuid4())
        task_ids = []
        
        for idx, image_data in enumerate(images_data):
            image_id = f"{batch_id}_{idx}"
            async_result = self.audit_image_async(
                image_data,
                callback_url=callback_url,
                enable_cache=enable_cache,
                image_id=image_id,
                use_multi_hash=use_multi_hash
            )
            task_ids.append(async_result["task_id"])
        
        return {
            "batch_id": batch_id,
            "total_count": len(images_data),
            "task_ids": task_ids,
            "status": "queued"
        }
    
    def audit_base64_sync(
        self,
        base64_image: str,
        enable_cache: bool = True,
        enable_review: bool = True,
        use_multi_hash: bool = True
    ) -> Dict:
        image, image_data = self._load_image_from_base64(base64_image)
        return self.audit_image_sync(
            image_data,
            enable_cache=enable_cache,
            enable_review=enable_review,
            use_multi_hash=use_multi_hash
        )
    
    def get_stats(self) -> Dict:
        return {
            "cache": self.cache.get_cache_stats(),
            "review": self.review_manager.get_review_stats(),
            "queue": {
                "async_tasks": self.mq.get_async_queue_size(),
                "review_tasks": self.mq.get_review_queue_size()
            }
        }
    
    def clear_image_cache(self, image_data: bytes) -> bool:
        return self.cache.delete_cache(image_data)
    
    def clear_all_cache(self) -> int:
        return self.cache.clear_all_cache()

audit_service = AuditService()
