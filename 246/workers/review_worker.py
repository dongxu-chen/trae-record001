import os
import sys
import uuid
import time
import signal
import logging
from typing import Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mq.rabbitmq_client import create_mq_client
from review.review_manager import ReviewStatus
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ReviewWorker")

class ReviewWorker:
    def __init__(self, worker_id: str = None, prefetch_count: int = 5):
        self.worker_id = worker_id or f"review_worker_{uuid.uuid4().hex[:8]}"
        self.prefetch_count = prefetch_count
        self.mq_client = create_mq_client(self.worker_id)
        self.processed_count = 0
        self.running = True
        
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        logger.info(f"[{self.worker_id}] Received shutdown signal. Stopping...")
        self.running = False
        self.mq_client.close()
        sys.exit(0)
    
    def _process_review(self, review_data: Dict):
        review_id = review_data.get("review_id")
        image_id = review_data.get("image_id")
        priority = review_data.get("priority", "medium")
        audit_result = review_data.get("audit_result", {})
        
        logger.info(
            f"[{self.worker_id}] Processing review task: {review_id} "
            f"(image: {image_id}, priority: {priority})"
        )
        
        result = {
            "worker_id": self.worker_id,
            "review_id": review_id,
            "image_id": image_id,
            "processed_at": datetime.utcnow().isoformat(),
            "original_risk": audit_result.get("risk_level"),
            "original_content": audit_result.get("main_content"),
            "confidence": audit_result.get("confidence", 0)
        }
        
        self.processed_count += 1
        
        logger.info(
            f"[{self.worker_id}] Completed review {review_id}. "
            f"Total processed: {self.processed_count}"
        )
        
        return result
    
    def start(self):
        logger.info(f"[{self.worker_id}] Review Worker started")
        logger.info(f"[{self.worker_id}] Prefetch count: {self.prefetch_count}")
        logger.info(f"[{self.worker_id}] Waiting for review tasks...")
        
        try:
            self.mq_client.consume_review_tasks(
                callback=self._process_review,
                prefetch_count=self.prefetch_count,
                auto_ack=False
            )
        except Exception as e:
            logger.error(f"[{self.worker_id}] Error: {e}")
            if self.running:
                time.sleep(5)
                self.start()

class MultiWorkerManager:
    def __init__(self, num_workers: int = 3, prefetch_count: int = 5):
        self.num_workers = num_workers
        self.prefetch_count = prefetch_count
        self.workers = []
    
    def start(self):
        logger.info(f"Starting {self.num_workers} review workers...")
        
        import multiprocessing
        
        processes = []
        for i in range(self.num_workers):
            worker_id = f"review_worker_{i+1}"
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
        worker = ReviewWorker(worker_id=worker_id, prefetch_count=prefetch_count)
        worker.start()

def run_single_worker():
    worker = ReviewWorker()
    worker.start()

def run_multiple_workers(num_workers: int = 3, prefetch_count: int = 5):
    manager = MultiWorkerManager(num_workers=num_workers, prefetch_count=prefetch_count)
    manager.start()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Review Worker for Image Audit Service")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--prefetch", type=int, default=5, help="Prefetch count per worker")
    parser.add_argument("--id", type=str, default=None, help="Worker ID (for single worker)")
    
    args = parser.parse_args()
    
    if args.workers > 1:
        run_multiple_workers(num_workers=args.workers, prefetch_count=args.prefetch)
    else:
        worker = ReviewWorker(worker_id=args.id, prefetch_count=args.prefetch)
        worker.start()
