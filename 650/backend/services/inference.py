import numpy as np
import threading
import queue
import time
from typing import Optional, Dict, Tuple, Any
from collections import deque

import torch


class InferenceService:
    def __init__(
        self,
        model=None,
        max_queue_size: int = 10,
        num_classes: int = 8,
        confidence_threshold: float = 0.5,
    ):
        self._model = model
        self._num_classes = num_classes
        self._confidence_threshold = confidence_threshold
        self._is_running: bool = False
        self._inference_thread: Optional[threading.Thread] = None
        self._input_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._result_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._lock = threading.Lock()

        self._total_inferences: int = 0
        self._total_latency: float = 0.0
        self._recent_latencies: deque = deque(maxlen=100)
        self._fps_window: deque = deque(maxlen=100)
        self._last_inference_time: float = 0.0

    @property
    def confidence_threshold(self) -> float:
        with self._lock:
            return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        with self._lock:
            self._confidence_threshold = value
            if self._model is not None:
                self._model.confidence_threshold = value

    def load_model(self, model) -> None:
        try:
            self._model = model
            if hasattr(model, '_num_classes'):
                self._num_classes = model._num_classes
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def start(self) -> None:
        with self._lock:
            if self._is_running:
                raise RuntimeError("Inference service is already running")

            if self._model is None:
                raise RuntimeError("Model not loaded")

            self._is_running = True
            self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
            self._inference_thread.start()

    def _inference_loop(self) -> None:
        while self._is_running:
            try:
                item = self._input_queue.get(timeout=1.0)
                if item is None:
                    break

                clip_tensor, timestamps, metadata = item

                start_time = time.time()
                predictions, all_probs = self.run_inference_with_probs(clip_tensor)
                latency = time.time() - start_time

                with self._lock:
                    self._total_inferences += 1
                    self._total_latency += latency
                    self._recent_latencies.append(latency)
                    self._last_inference_time = time.time()
                    self._fps_window.append(time.time())

                result = {
                    "prediction": predictions,
                    "all_probabilities": all_probs,
                    "timestamps": timestamps,
                    "latency": latency,
                    "metadata": metadata
                }

                if not self._result_queue.full():
                    self._result_queue.put(result)
                else:
                    try:
                        self._result_queue.get_nowait()
                        self._result_queue.put(result)
                    except queue.Empty:
                        pass

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in inference loop: {e}")
                time.sleep(0.1)

    def run_inference(self, clip_tensor: np.ndarray) -> list:
        try:
            if self._model is None:
                raise RuntimeError("Model not loaded")

            if isinstance(clip_tensor, np.ndarray):
                clip_tensor = torch.from_numpy(clip_tensor).float()

            if clip_tensor.ndim == 4:
                clip_tensor = clip_tensor.unsqueeze(0)

            with torch.no_grad():
                predictions = self._model.predict(clip_tensor)

            return predictions
        except Exception as e:
            print(f"Error during inference: {e}")
            raise

    def run_inference_with_probs(self, clip_tensor: np.ndarray) -> Tuple[list, np.ndarray]:
        try:
            if self._model is None:
                raise RuntimeError("Model not loaded")

            if isinstance(clip_tensor, np.ndarray):
                clip_tensor = torch.from_numpy(clip_tensor).float()

            if clip_tensor.ndim == 4:
                clip_tensor = clip_tensor.unsqueeze(0)

            if hasattr(self._model, 'predict_with_probs'):
                with torch.no_grad():
                    predictions, all_probs = self._model.predict_with_probs(clip_tensor)
            else:
                with torch.no_grad():
                    predictions = self._model.predict(clip_tensor)
                    logits = self._model.model(clip_tensor) if hasattr(self._model, 'model') else None
                    if logits is not None:
                        all_probs = self._model.get_all_probabilities(logits)
                    else:
                        all_probs = np.zeros(self._num_classes, dtype=np.float32)

            return predictions, all_probs
        except Exception as e:
            print(f"Error during inference with probs: {e}")
            raise

    def submit_clip(self, clip_tensor: np.ndarray, timestamps: list, metadata: Optional[Dict] = None) -> bool:
        try:
            if not self._input_queue.full():
                self._input_queue.put((clip_tensor, timestamps, metadata or {}))
                return True
            return False
        except Exception as e:
            print(f"Error submitting clip: {e}")
            return False

    def get_result(self, timeout: float = 1.0) -> Optional[Dict]:
        try:
            return self._result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        with self._lock:
            self._is_running = False

        if not self._input_queue.full():
            try:
                self._input_queue.put_nowait(None)
            except queue.Full:
                pass

        if self._inference_thread:
            self._inference_thread.join(timeout=2.0)

        with self._lock:
            while not self._input_queue.empty():
                try:
                    self._input_queue.get_nowait()
                except queue.Empty:
                    break
            while not self._result_queue.empty():
                try:
                    self._result_queue.get_nowait()
                except queue.Empty:
                    break

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_latency = np.mean(self._recent_latencies) if self._recent_latencies else 0.0
            current_fps = len(self._fps_window) / (self._fps_window[-1] - self._fps_window[0]) \
                if len(self._fps_window) >= 2 and (self._fps_window[-1] - self._fps_window[0]) > 0 else 0.0

            return {
                "total_inferences": self._total_inferences,
                "avg_latency": avg_latency,
                "current_fps": current_fps,
                "input_queue_size": self._input_queue.qsize(),
                "result_queue_size": self._result_queue.qsize(),
                "is_running": self._is_running
            }
