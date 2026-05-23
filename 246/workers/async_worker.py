import os
import sys
import uuid
import base64
import signal
import logging
import requests
from typing import Dict
from datetime import datetime
from PIL import Image
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mq.rabbitmq_client import create_mq_client
from models.content_detector import detector
from cache.redis_cache import cache, CacheHitSource
from review.review_manager import review_manager
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AsyncAuditWorker")

class AsyncAuditWorker:
    def __init__(self, worker_id: str = None, prefetch_count: int = 3):
        self.worker_id = worker_id or f"audit_worker_{uuid.uuid4().hex[:8]}"
        self.prefetch_count = prefetch_count
        self.detector = detector
        self.cache = cache
        self.review_manager = review_manager
        self.mq = create_mq_client(self.worker_id)
        self.processed_count = 0
        self.running = True
        
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        logger.info(f"[{self.worker_id}] Received shutdown signal. Stopping...")
        self.running = False
        self.mq.close()
        sys.exit(0)
    
    def _send_callback(self, callback_url: str, result: Dict):
        if not callback_url:
            return
        
        try:
            requests.post(
                callback_url,
                json=result,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            logger.warning(f"[{self.worker_id}] Callback failed: {e}")
    
    def _process_cache_hit(self, result: Dict, cached_result: Dict, hit_source: str) -> Dict:
        result.update(cached_result)
        result["cached"] = True
        result["cache_hit_source"] = hit_source
        
        if hit_source != CacheHitSource.MD5:
            result["from_similar"] = True
            result["hash_distance"] = cached_result.get("hash_distance", 0)
        else:
            result["from_similar"] = False
        
        return result
    
    def _process_task(self, task_data: Dict) -> Dict:
        task_id = task_data.get("task_id")
        image_id = task_data.get("image_id")
        image_base64 = task_data.get("image_data")
        enable_cache = task_data.get("enable_cache", True)
        use_multi_hash = task_data.get("use_multi_hash", True)
        callback_url = task_data.get("callback_url")
        
        logger.info(
            f"[{self.worker_id}] Processing task: {task_id} (image: {image_id})"
        )
        
        result = {
            "task_id": task_id,
            "image_id": image_id,
            "worker_id": self.worker_id,
            "processed_at": datetime.utcnow().isoformat(),
            "cached": False,
            "from_similar": False,
            "cache_hit_source": CacheHitSource.NONE
        }
        
        try:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            if enable_cache:
                cached_result, md5_hash = self.cache.get_cached_result(
                    image_data, image, use_multi_hash
                )
                if cached_result:
                    hit_source = cached_result.get("cache_hit_source", CacheHitSource.NONE)
                    result = self._process_cache_hit(result, cached_result, hit_source)
                    self._send_callback(callback_url, result)
                    self.processed_count += 1
                    logger.info(
                        f"[{self.worker_id}] Task {task_id} completed from cache "
                        f"(source: {hit_source}). Total: {self.processed_count}"
                    )
                    return result
            
            detect_result = self.detector.detect(image)
            result.update(detect_result)
            
            if enable_cache:
                self.cache.cache_with_multi_hash(image_data, image, detect_result)
            
            review_task = self.review_manager.auto_submit_for_review(image_id, detect_result)
            if review_task:
                result["review_submitted"] = True
                result["review_id"] = review_task["review_id"]
                result["review_priority"] = review_task["priority"]
            
            self._send_callback(callback_url, result)
            self.mq.publish_result(result)
            
            self.processed_count += 1
            logger.info(
                f"[{self.worker_id}] Task {task_id} completed. "
                f"Risk: {result.get('risk_level')}. Total: {self.processed_count}"
            )
            
        except Exception as e:
            logger.error(f"[{self.worker_id}] Task {task_id} failed: {e}")
            result["error"] = str(e)
            result["risk_level"] = "unknown"
            self._send_callback(callback_url, result)
        
        return result
    
    def start(self):
        logger.info(f"[{self.worker_id}] Async Audit Worker started")
        logger.info(f"[{self.worker_id}] Prefetch count: {self.prefetch_count}")
        logger.info(f"[{self.worker_id}] Waiting for audit tasks...")
        
        try:
            self.mq.consume_async_tasks(
                callback=self._process_task,
                prefetch_count=self.prefetch_count,
                auto_ack=False
            )
        except Exception as e:
            logger.error(f"[{self.worker_id}] Consumer error: {e}")
            if self.running:
                import time
                time.sleep(5)
                self.start()

class MultiAuditWorkerManager:
    def __init__(self, num_workers: int = 3, prefetch_count: int = 3):
        self.num_workers = num_workers
        self.prefetch_count = prefetch_count
    
    def start(self):
        logger.info(f"Starting {self.num_workers} async audit workers...")
        
        import multiprocessing
        
        processes = []
        for i in range(self.num_workers):
            worker_id = f"audit_worker_{i+1}"
            process = multiprocessing.Process(
                target=self._run_worker,
                args=(worker_id, self.prefetch_count)
            )
            processes.append(process)
            process.start()
            logger.info(f"Started worker {worker_id} (PID: {process.pid})")
        
        for process in processes:
            process.join()
    
    @staticmethod
    def _run_worker(worker_id: str, prefetch_count: int):
        worker = AsyncAuditWorker(worker_id=worker_id, prefetch_count=prefetch_count)
        worker.start()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Async Audit Worker for Image Audit Service")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--prefetch", type=int, default=3, help="Prefetch count per worker")
    parser.add_argument("--id", type=str, default=None, help="Worker ID (for single worker)")
    
    args = parser.parse_args()
    
    if args.workers > 1:
        manager = MultiAuditWorkerManager(
            num_workers=args.workers,
            prefetch_count=args.prefetch
        )
        manager.start()
    else:
        worker = AsyncAuditWorker(worker_id=args.id, prefetch_count=args.prefetch)
        worker.start()
