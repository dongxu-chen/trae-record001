import os
import sys
import queue
import threading
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable
from datetime import datetime
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class AsyncEvaluationQueue:
    """异步评估队列 - 不阻塞主竞价链路"""
    
    def __init__(self, config_path: str = "configs/config.yaml", 
                 max_queue_size: int = 100000,
                 num_workers: int = 4):
        self.config = load_config(config_path)
        self.logger = setup_logger("AsyncEvaluationQueue", self.config)
        
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        
        self.evaluation_queue = queue.Queue(maxsize=max_queue_size)
        self.result_queue = queue.Queue()
        
        self.workers = []
        self.processors = {}
        self.metrics_callbacks = []
        
        self.running = False
        self.stats = {
            "total_enqueued": 0,
            "total_processed": 0,
            "total_dropped": 0,
            "avg_processing_time_ms": 0
        }
        
        self._lock = threading.Lock()

    def register_processor(self, processor_name: str, processor_func: Callable):
        """注册数据处理器"""
        self.processors[processor_name] = processor_func
        self.logger.info(f"Registered processor: {processor_name}")

    def register_metrics_callback(self, callback: Callable):
        """注册指标回调函数"""
        self.metrics_callbacks.append(callback)

    def enqueue(self, data: Dict, processor_name: str = "default", 
                priority: int = 0, callback: Optional[Callable] = None) -> bool:
        """
        异步入队 - 非阻塞
        
        Args:
            data: 待处理数据
            processor_name: 处理器名称
            priority: 优先级 (0-10)
            callback: 处理完成回调
        
        Returns:
            bool: 是否成功入队
        """
        if self.evaluation_queue.full():
            with self._lock:
                self.stats["total_dropped"] += 1
            self.logger.warning("Evaluation queue is full, dropping data")
            return False

        item = {
            "data": data,
            "processor_name": processor_name,
            "priority": priority,
            "callback": callback,
            "enqueue_time": time.time()
        }

        try:
            self.evaluation_queue.put_nowait(item)
            with self._lock:
                self.stats["total_enqueued"] += 1
            return True
        except queue.Full:
            with self._lock:
                self.stats["total_dropped"] += 1
            return False

    def _worker_loop(self):
        """工作线程主循环"""
        while self.running:
            try:
                item = self.evaluation_queue.get(timeout=1.0)
                start_time = time.time()
                
                try:
                    result = self._process_item(item)
                    
                    process_time = (time.time() - start_time) * 1000
                    with self._lock:
                        self.stats["total_processed"] += 1
                        self.stats["avg_processing_time_ms"] = (
                            0.9 * self.stats["avg_processing_time_ms"] + 
                            0.1 * process_time
                        )
                    
                    if item.get("callback"):
                        item["callback"](result)
                    
                    for cb in self.metrics_callbacks:
                        try:
                            cb(result)
                        except Exception as e:
                            self.logger.error(f"Callback error: {e}")
                            
                except Exception as e:
                    self.logger.error(f"Error processing item: {e}")
                finally:
                    self.evaluation_queue.task_done()
                    
            except queue.Empty:
                continue

    def _process_item(self, item: Dict) -> Dict:
        """处理单个队列项"""
        data = item["data"]
        processor_name = item["processor_name"]
        
        processor = self.processors.get(processor_name)
        if processor:
            result = processor(data)
        else:
            result = {"status": "no_processor", "data": data}
        
        return {
            "result": result,
            "processor": processor_name,
            "process_time_ms": (time.time() - item["enqueue_time"]) * 1000,
            "queue_latency_ms": (time.time() - item["enqueue_time"]) * 1000
        }

    def start(self):
        """启动工作线程"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"Started {self.num_workers} async evaluation workers")

    def stop(self):
        """停止工作线程"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5.0)
        self.workers = []
        self.logger.info("Stopped all async evaluation workers")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.copy()
            stats["queue_size"] = self.evaluation_queue.qsize()
            stats["utilization"] = stats["queue_size"] / max(self.max_queue_size, 1)
        return stats

    def wait_until_empty(self, timeout: float = 60.0):
        """等待队列清空"""
        start_time = time.time()
        while not self.evaluation_queue.empty():
            if time.time() - start_time > timeout:
                self.logger.warning("Timeout waiting for queue to empty")
                break
            time.sleep(0.1)


class PredictionDataProcessor:
    """预测数据处理器 - 用于异步记录预测和标签"""
    
    def __init__(self, output_dir: str = "data/online_predictions"):
        self.output_dir = output_dir
        ensure_dir(output_dir)
        self.buffer = []
        self.buffer_size = 1000
        self.flush_interval = 60
        self.last_flush = time.time()

    def __call__(self, data: Dict) -> Dict:
        """处理预测数据"""
        self.buffer.append({
            "prediction_id": data.get("prediction_id"),
            "user_id": data.get("user_id"),
            "ad_id": data.get("ad_id"),
            "prediction_score": data.get("prediction_score"),
            "model_version": data.get("model_version"),
            "features": data.get("features", {}),
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "ab_group": data.get("ab_group")
        })
        
        if len(self.buffer) >= self.buffer_size or time.time() - self.last_flush > self.flush_interval:
            self.flush()
        
        return {"status": "buffered", "buffer_size": len(self.buffer)}

    def flush(self):
        """刷新缓冲区到磁盘"""
        if not self.buffer:
            return
        
        filename = f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w") as f:
            for item in self.buffer:
                f.write(json.dumps(item) + "\n")
        
        self.buffer = []
        self.last_flush = time.time()


class LabelMatcher:
    """标签匹配器 - 异步匹配预测和点击/转化标签"""
    
    def __init__(self, window_seconds: int = 3600):
        self.pending_predictions = {}
        self.window_seconds = window_seconds
        self.matched_labels = []

    def add_prediction(self, prediction_id: str, data: Dict):
        """添加待匹配的预测"""
        self.pending_predictions[prediction_id] = {
            "data": data,
            "timestamp": time.time()
        }

    def add_label(self, prediction_id: str, label_type: str, value: int):
        """添加标签并尝试匹配"""
        if prediction_id in self.pending_predictions:
            pred_data = self.pending_predictions[prediction_id]["data"]
            pred_data[f"{label_type}_label"] = value
            pred_data["matched_at"] = datetime.now().isoformat()
            self.matched_labels.append(pred_data)
            
            del self.pending_predictions[prediction_id]

    def cleanup_expired(self):
        """清理过期的待匹配预测"""
        now = time.time()
        expired = [
            pid for pid, item in self.pending_predictions.items()
            if now - item["timestamp"] > self.window_seconds
        ]
        for pid in expired:
            del self.pending_predictions[pid]

    def get_matched_data(self) -> pd.DataFrame:
        """获取已匹配的数据"""
        return pd.DataFrame(self.matched_labels)


def create_async_evaluation_pipeline(config_path: str = "configs/config.yaml") -> AsyncEvaluationQueue:
    """创建异步评估流水线"""
    async_queue = AsyncEvaluationQueue(config_path=config_path)
    
    prediction_processor = PredictionDataProcessor()
    async_queue.register_processor("prediction", prediction_processor)
    
    def click_processor(data: Dict) -> Dict:
        return {"type": "click", "data": data}
    async_queue.register_processor("click", click_processor)
    
    def impression_processor(data: Dict) -> Dict:
        return {"type": "impression", "data": data}
    async_queue.register_processor("impression", impression_processor)
    
    return async_queue


class BidirectionalStreamProcessor:
    """双向流处理器 - 主竞价链路和评估分流完全分离"""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("BidirectionalStream", self.config)
        
        self.async_queue = AsyncEvaluationQueue(config_path=config_path)
        self.label_matcher = LabelMatcher()
        
        self.bidding_path_latency = []
        self.evaluation_path_latency = []

    def predict_bidding_path(self, features: Dict, model) -> Dict:
        """
        主竞价预测路径 - 低延迟优先
        
        这里只做最小必要的计算，不做任何评估逻辑
        """
        start_time = time.time()
        
        prediction = model(features)
        
        latency = (time.time() - start_time) * 1000
        self.bidding_path_latency.append(latency)
        
        return {
            "prediction_score": float(prediction),
            "latency_ms": latency
        }

    def submit_for_evaluation(self, prediction_id: str, features: Dict, 
                               prediction_score: float, model_version: str,
                               ab_group: str = None):
        """
        提交到评估分流 - 异步非阻塞
        
        主竞价路径只调用这个方法提交，不等待结果
        """
        eval_data = {
            "prediction_id": prediction_id,
            "features": features,
            "prediction_score": prediction_score,
            "model_version": model_version,
            "ab_group": ab_group,
            "timestamp": datetime.now().isoformat()
        }
        
        success = self.async_queue.enqueue(
            eval_data, 
            processor_name="prediction",
            priority=5
        )
        
        if success:
            self.label_matcher.add_prediction(prediction_id, eval_data)

    def report_feedback(self, prediction_id: str, click: bool = False, 
                        conversion: bool = False):
        """
        上报反馈标签 - 异步处理
        """
        if click:
            self.label_matcher.add_label(prediction_id, "click", 1)
            self.async_queue.enqueue(
                {"prediction_id": prediction_id, "click": 1},
                processor_name="click"
            )

    def start(self):
        self.async_queue.start()

    def stop(self):
        self.async_queue.stop()


def main():
    print("Async Evaluator Module")
    print("Provides non-blocking evaluation pipeline for CTR predictions")
    
    queue = create_async_evaluation_pipeline()
    queue.start()
    
    for i in range(100):
        data = {
            "prediction_id": f"pred_{i}",
            "user_id": f"user_{i}",
            "prediction_score": np.random.beta(2, 20)
        }
        queue.enqueue(data, processor_name="prediction")
    
    time.sleep(2)
    print("Stats:", queue.get_stats())
    
    queue.stop()


if __name__ == "__main__":
    main()
