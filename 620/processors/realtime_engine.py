import numpy as np
import cv2
import time
import threading
from collections import deque
from queue import Queue
from config import REALTIME_CONFIG


class RealtimeSuperResolution:
    def __init__(self, sr_model, config=None, device=None):
        self.config = config or REALTIME_CONFIG
        self.enable = self.config.get('enable', False)
        self.target_fps = self.config.get('target_fps', 30)
        self.batch_size = self.config.get('batch_size', 4)
        self.prefetch_frames = self.config.get('prefetch_frames', 10)
        self.use_tensorrt = self.config.get('use_tensorrt', False)
        self.use_cuda_graph = self.config.get('use_cuda_graph', False)
        self.frame_skip = self.config.get('frame_skip', False)
        self.max_resolution = self.config.get('max_resolution', (1920, 1080))
        self.async_transfer = self.config.get('async_transfer', True)
        self.pipeline_depth = self.config.get('pipeline_depth', 3)
        
        self.sr_model = sr_model
        self.device = device
        
        self.input_queue = Queue(maxsize=self.prefetch_frames * 2)
        self.output_queue = Queue(maxsize=self.prefetch_frames * 2)
        self.batch_queue = Queue(maxsize=self.pipeline_depth)
        
        self.is_running = False
        self.process_thread = None
        self.batch_thread = None
        
        self.frame_count = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.fps_history = deque(maxlen=30)
        self.last_time = time.time()
        
        self.frame_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        self.pipeline_stages = [
            {'name': 'preprocess', 'time': 0, 'count': 0},
            {'name': 'transfer', 'time': 0, 'count': 0},
            {'name': 'inference', 'time': 0, 'count': 0},
            {'name': 'postprocess', 'time': 0, 'count': 0},
        ]

    def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        self.frame_count = 0
        self.processed_count = 0
        self.skipped_count = 0
        self.last_time = time.time()
        
        self.batch_thread = threading.Thread(target=self._batch_collector)
        self.batch_thread.daemon = True
        self.batch_thread.start()
        
        self.process_thread = threading.Thread(target=self._process_worker)
        self.process_thread.daemon = True
        self.process_thread.start()

    def stop(self):
        self.is_running = False
        
        if self.batch_thread:
            self.batch_thread.join(timeout=1.0)
        
        if self.process_thread:
            self.process_thread.join(timeout=1.0)

    def reset(self):
        self.frame_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.fps_history.clear()
        while not self.input_queue.empty():
            self.input_queue.get()
        while not self.output_queue.empty():
            self.output_queue.get()
        while not self.batch_queue.empty():
            self.batch_queue.get()

    def _get_frame_hash(self, frame):
        resized = cv2.resize(frame, (64, 64))
        hashed = hash(resized.tobytes())
        return hashed

    def _preprocess_frame(self, frame):
        t0 = time.time()
        
        h, w = frame.shape[:2]
        max_w, max_h = self.max_resolution
        
        if w > max_w or h > max_h:
            scale = min(max_w / w, max_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        if frame.dtype != np.float32:
            frame = frame.astype(np.float32) / 255.0
        
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        t1 = time.time()
        self._update_stage_time('preprocess', t1 - t0)
        
        return frame

    def _postprocess_frame(self, frame):
        t0 = time.time()
        
        frame = np.clip(frame, 0, 1)
        
        t1 = time.time()
        self._update_stage_time('postprocess', t1 - t0)
        
        return frame

    def _update_stage_time(self, stage_name, elapsed):
        for stage in self.pipeline_stages:
            if stage['name'] == stage_name:
                stage['time'] += elapsed
                stage['count'] += 1
                break

    def _should_skip_frame(self):
        if not self.frame_skip:
            return False
        
        current_fps = self._get_current_fps()
        if current_fps < self.target_fps * 0.7:
            self.skipped_count += 1
            return True
        
        return False

    def _get_current_fps(self):
        if len(self.fps_history) == 0:
            return self.target_fps
        return np.mean(self.fps_history)

    def _check_cache(self, frame):
        frame_hash = self._get_frame_hash(frame)
        
        if frame_hash in self.frame_cache:
            self.cache_hits += 1
            return self.frame_cache[frame_hash]
        
        self.cache_misses += 1
        return None

    def _update_cache(self, frame, result):
        if len(self.frame_cache) > 100:
            oldest_key = next(iter(self.frame_cache))
            del self.frame_cache[oldest_key]
        
        frame_hash = self._get_frame_hash(frame)
        self.frame_cache[frame_hash] = result

    def enqueue_frame(self, frame, frame_id=None):
        if not self.is_running:
            self.start()
        
        if frame_id is None:
            frame_id = self.frame_count
            self.frame_count += 1
        
        if self._should_skip_frame():
            return None
        
        cached = self._check_cache(frame)
        if cached is not None:
            self.output_queue.put((frame_id, cached))
            return frame_id
        
        preprocessed = self._preprocess_frame(frame)
        self.input_queue.put((frame_id, preprocessed))
        
        return frame_id

    def _batch_collector(self):
        while self.is_running:
            batch = []
            batch_ids = []
            
            try:
                while len(batch) < self.batch_size:
                    if not self.input_queue.empty():
                        frame_id, frame = self.input_queue.get(timeout=0.01)
                        batch.append(frame)
                        batch_ids.append(frame_id)
                    else:
                        time.sleep(0.001)
                    
                    if len(batch) > 0 and time.time() - self.last_time > 1.0 / self.target_fps:
                        break
                
                if len(batch) > 0:
                    self.batch_queue.put((batch_ids, batch))
                    
            except:
                time.sleep(0.001)
                continue

    def _process_worker(self):
        while self.is_running:
            try:
                if self.batch_queue.empty():
                    time.sleep(0.001)
                    continue
                
                batch_ids, batch = self.batch_queue.get(timeout=0.1)
                
                t0 = time.time()
                batch_tensor = self._batch_to_tensor(batch)
                t1 = time.time()
                self._update_stage_time('transfer', t1 - t0)
                
                t0 = time.time()
                sr_batch = self._run_inference(batch_tensor)
                t1 = time.time()
                self._update_stage_time('inference', t1 - t0)
                
                for frame_id, sr_frame in zip(batch_ids, sr_batch):
                    sr_frame = self._postprocess_frame(sr_frame)
                    self._update_cache(batch[batch_ids.index(frame_id)], sr_frame)
                    self.output_queue.put((frame_id, sr_frame))
                    self.processed_count += 1
                
                current_time = time.time()
                elapsed = current_time - self.last_time
                if elapsed > 0:
                    fps = len(batch) / elapsed
                    self.fps_history.append(fps)
                self.last_time = current_time
                
            except Exception as e:
                time.sleep(0.001)
                continue

    def _batch_to_tensor(self, batch):
        try:
            import torch
            batch_np = np.stack(batch, axis=0)
            batch_np = np.transpose(batch_np, (0, 3, 1, 2))
            tensor = torch.from_numpy(batch_np)
            
            if self.device and 'cuda' in str(self.device):
                if self.async_transfer:
                    tensor = tensor.to(self.device, non_blocking=True)
                else:
                    tensor = tensor.to(self.device)
            
            return tensor
        except ImportError:
            return np.stack(batch, axis=0)

    def _run_inference(self, batch_tensor):
        try:
            import torch
            if self.sr_model is not None and hasattr(self.sr_model, '__call__'):
                with torch.no_grad() if 'torch' in str(type(batch_tensor)) else nullcontext():
                    if hasattr(self.sr_model, 'enhance'):
                        results = []
                        for i in range(batch_tensor.shape[0]):
                            frame = batch_tensor[i]
                            if hasattr(frame, 'cpu'):
                                frame = frame.cpu().numpy()
                            if len(frame.shape) == 4:
                                frame = frame[0]
                            if frame.shape[0] == 3:
                                frame = np.transpose(frame, (1, 2, 0))
                            result = self.sr_model.enhance(frame)
                            results.append(result)
                        return results
                    else:
                        output = self.sr_model(batch_tensor)
                        if hasattr(output, 'cpu'):
                            output = output.cpu().numpy()
                        output = np.transpose(output, (0, 2, 3, 1))
                        return [output[i] for i in range(output.shape[0])]
            else:
                return [self._bilinear_upscale(frame) for frame in batch_tensor]
        except Exception as e:
            return [self._bilinear_upscale(frame) for frame in batch_tensor]

    def _bilinear_upscale(self, frame, scale=4):
        if hasattr(frame, 'cpu'):
            frame = frame.cpu().numpy()
        if len(frame.shape) == 4:
            frame = frame[0]
        if frame.shape[0] == 3:
            frame = np.transpose(frame, (1, 2, 0))
        
        h, w = frame.shape[:2]
        new_size = (w * scale, h * scale)
        return cv2.resize(frame, new_size, interpolation=cv2.INTER_LINEAR)

    def get_result(self, timeout=0.1):
        try:
            frame_id, sr_frame = self.output_queue.get(timeout=timeout)
            return frame_id, sr_frame
        except:
            return None, None

    def get_all_results(self):
        results = []
        while not self.output_queue.empty():
            try:
                frame_id, sr_frame = self.output_queue.get_nowait()
                results.append((frame_id, sr_frame))
            except:
                break
        return sorted(results, key=lambda x: x[0])

    def process_frame_sync(self, frame):
        t0 = time.time()
        
        preprocessed = self._preprocess_frame(frame)
        
        cached = self._check_cache(frame)
        if cached is not None:
            return cached
        
        t1 = time.time()
        if self.sr_model and hasattr(self.sr_model, 'enhance'):
            sr_frame = self.sr_model.enhance(preprocessed)
        else:
            sr_frame = self._bilinear_upscale(preprocessed)
        
        t2 = time.time()
        sr_frame = self._postprocess_frame(sr_frame)
        self._update_cache(preprocessed, sr_frame)
        
        self.processed_count += 1
        self._update_stage_time('inference', t2 - t1)
        
        current_time = time.time()
        elapsed = current_time - self.last_time
        if elapsed > 0:
            self.fps_history.append(1.0 / elapsed)
        self.last_time = current_time
        
        return sr_frame

    def get_stats(self):
        total_time = sum(s['time'] for s in self.pipeline_stages)
        stats = {
            'fps': self._get_current_fps(),
            'target_fps': self.target_fps,
            'processed_frames': self.processed_count,
            'skipped_frames': self.skipped_count,
            'total_frames': self.frame_count,
            'cache_hit_rate': self.cache_hits / max(1, self.cache_hits + self.cache_misses),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'queue_size': self.input_queue.qsize() + self.output_queue.qsize(),
            'pipeline_times': {}
        }
        
        for stage in self.pipeline_stages:
            if stage['count'] > 0:
                avg_time = stage['time'] / stage['count'] * 1000
                percentage = (stage['time'] / total_time * 100) if total_time > 0 else 0
                stats['pipeline_times'][stage['name']] = {
                    'avg_ms': avg_time,
                    'percentage': percentage,
                    'count': stage['count']
                }
        
        return stats


class FrameBuffer:
    def __init__(self, size=5):
        self.size = size
        self.buffer = deque(maxlen=size)
        self.timestamps = deque(maxlen=size)
    
    def add(self, frame, timestamp=None):
        self.buffer.append(frame)
        if timestamp is None:
            timestamp = time.time()
        self.timestamps.append(timestamp)
    
    def get_latest(self):
        if len(self.buffer) > 0:
            return self.buffer[-1]
        return None
    
    def get_all(self):
        return list(self.buffer)
    
    def get_average(self):
        if len(self.buffer) == 0:
            return None
        return np.mean(np.stack(self.buffer), axis=0)
    
    def is_full(self):
        return len(self.buffer) == self.size
    
    def clear(self):
        self.buffer.clear()
        self.timestamps.clear()


class nullcontext:
    def __enter__(self):
        return None
    def __exit__(self, *args):
        return False


def optimize_model_for_inference(model, device='cuda', use_fp16=True, use_tensorrt=False):
    try:
        import torch
        
        model.eval()
        
        if use_fp16 and 'cuda' in str(device):
            model = model.half()
        
        if use_tensorrt and 'cuda' in str(device):
            try:
                import torch_tensorrt
                example_input = torch.randn((1, 3, 224, 224)).to(device)
                if use_fp16:
                    example_input = example_input.half()
                model = torch_tensorrt.compile(
                    model,
                    inputs=[example_input],
                    enabled_precisions={torch.half} if use_fp16 else {torch.float}
                )
            except ImportError:
                pass
        
        if 'cuda' in str(device):
            model = model.to(device)
        
        return model
    except ImportError:
        return model


def get_gpu_info():
    try:
        import torch
        if torch.cuda.is_available():
            return {
                'available': True,
                'device_count': torch.cuda.device_count(),
                'current_device': torch.cuda.current_device(),
                'device_name': torch.cuda.get_device_name(0),
                'memory_allocated': torch.cuda.memory_allocated(0) / 1024**3,
                'memory_cached': torch.cuda.memory_reserved(0) / 1024**3,
            }
    except ImportError:
        pass
    return {'available': False}
