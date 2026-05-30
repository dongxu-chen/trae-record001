import os
import time
import numpy as np
from typing import List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field


@dataclass
class MemoryInfo:
    total: int = 0
    available: int = 0
    used: int = 0
    reserved: int = 0
    utilization: float = 0.0


@dataclass
class BatchConfig:
    current_batch_size: int = 4
    min_batch_size: int = 1
    max_batch_size: int = 8
    target_memory_usage: float = 0.85
    safe_margin: float = 0.1
    last_memory_usage: float = 0.0
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3


@dataclass
class ProcessingStats:
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    total_time: float = 0.0
    avg_time_per_item: float = 0.0
    memory_peak: float = 0.0
    batch_size_history: List[int] = field(default_factory=list)


class GPUMemoryMonitor:
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self._cuda_available = self._check_cuda()
    
    def _check_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def get_memory_info(self) -> MemoryInfo:
        if not self._cuda_available:
            return self._get_cpu_memory_info()
        
        try:
            import torch
            if not torch.cuda.is_available():
                return self._get_cpu_memory_info()
            
            torch.cuda.synchronize()
            
            total = torch.cuda.get_device_properties(self.device_id).total_memory
            reserved = torch.cuda.memory_reserved(self.device_id)
            allocated = torch.cuda.memory_allocated(self.device_id)
            available = total - allocated
            
            free = total - reserved
            
            info = MemoryInfo(
                total=total,
                available=available,
                used=allocated,
                reserved=reserved,
                utilization=allocated / total if total > 0 else 0.0
            )
            
            return info
            
        except Exception as e:
            print(f"Warning: Failed to get GPU memory info: {e}")
            return self._get_cpu_memory_info()
    
    def _get_cpu_memory_info(self) -> MemoryInfo:
        try:
            import psutil
            mem = psutil.virtual_memory()
            return MemoryInfo(
                total=mem.total,
                available=mem.available,
                used=mem.used,
                reserved=0,
                utilization=mem.percent / 100.0
            )
        except ImportError:
            return MemoryInfo(
                total=0,
                available=0,
                used=0,
                reserved=0,
                utilization=0.0
            )
    
    def estimate_batch_memory(self, batch_size: int, per_item_mb: float) -> float:
        return batch_size * per_item_mb * 1024 * 1024
    
    def can_allocate(self, bytes_needed: float) -> bool:
        mem_info = self.get_memory_info()
        safe_available = mem_info.available * (1 - 0.1)
        return bytes_needed < safe_available
    
    def reset_peak_memory(self):
        if self._cuda_available:
            try:
                import torch
                torch.cuda.reset_peak_memory_stats(self.device_id)
            except:
                pass
    
    def get_peak_memory(self) -> float:
        if self._cuda_available:
            try:
                import torch
                return torch.cuda.max_memory_allocated(self.device_id)
            except:
                return 0.0
        return 0.0


class DynamicBatchProcessor:
    def __init__(self, 
                 process_func: Callable[[Any], Any],
                 initial_batch_size: int = 4,
                 min_batch_size: int = 1,
                 max_batch_size: int = 8,
                 target_memory_usage: float = 0.85,
                 device_id: int = 0):
        self.process_func = process_func
        self.memory_monitor = GPUMemoryMonitor(device_id)
        self.config = BatchConfig(
            current_batch_size=initial_batch_size,
            min_batch_size=min_batch_size,
            max_batch_size=max_batch_size,
            target_memory_usage=target_memory_usage
        )
        self.stats = ProcessingStats()
        self._per_item_memory_mb: Optional[float] = None
    
    def _estimate_per_item_memory(self, sample_item: Any) -> float:
        if self._per_item_memory_mb is not None:
            return self._per_item_memory_mb
        
        try:
            self.memory_monitor.reset_peak_memory()
            
            mem_before = self.memory_monitor.get_memory_info()
            
            result = self.process_func([sample_item])
            
            mem_after = self.memory_monitor.get_memory_info()
            peak_memory = self.memory_monitor.get_peak_memory()
            
            used_memory = max(mem_after.used - mem_before.used, peak_memory)
            self._per_item_memory_mb = used_memory / (1024 * 1024)
            
            return self._per_item_memory_mb
            
        except Exception as e:
            print(f"Warning: Failed to estimate memory, using default: {e}")
            self._per_item_memory_mb = 500.0
            return self._per_item_memory_mb
    
    def _adjust_batch_size(self, memory_info: MemoryInfo, success: bool = True):
        if not success:
            self.config.consecutive_failures += 1
            
            if self.config.consecutive_failures >= self.config.max_consecutive_failures:
                new_batch_size = max(self.config.min_batch_size, 
                                   self.config.current_batch_size // 2)
                print(f"Consecutive failures detected, reducing batch size: "
                      f"{self.config.current_batch_size} -> {new_batch_size}")
                self.config.current_batch_size = new_batch_size
                self.config.consecutive_failures = 0
        else:
            self.config.consecutive_failures = 0
            
            if memory_info.utilization < self.config.target_memory_usage * 0.7:
                new_batch_size = min(self.config.max_batch_size,
                                   self.config.current_batch_size * 2)
                if new_batch_size > self.config.current_batch_size:
                    print(f"Memory utilization low, increasing batch size: "
                          f"{self.config.current_batch_size} -> {new_batch_size}")
                    self.config.current_batch_size = new_batch_size
            elif memory_info.utilization > self.config.target_memory_usage * 0.95:
                new_batch_size = max(self.config.min_batch_size,
                                   self.config.current_batch_size - 1)
                if new_batch_size < self.config.current_batch_size:
                    print(f"Memory utilization high, reducing batch size: "
                          f"{self.config.current_batch_size} -> {new_batch_size}")
                    self.config.current_batch_size = new_batch_size
        
        self.config.last_memory_usage = memory_info.utilization
    
    def _process_batch_safe(self, batch: List[Any]) -> Tuple[Optional[List[Any]], bool]:
        try:
            results = self.process_func(batch)
            if not isinstance(results, list):
                results = [results]
            return results, True
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
                print(f"OOM detected for batch size {len(batch)}: {e}")
                if hasattr(self.process_func, '__self__') and hasattr(self.process_func.__self__, 'model'):
                    try:
                        import torch
                        torch.cuda.empty_cache()
                    except:
                        pass
                return None, False
            else:
                raise e
        except Exception as e:
            print(f"Error processing batch: {e}")
            return None, False
    
    def _process_with_split(self, items: List[Any]) -> List[Any]:
        if len(items) == 0:
            return []
        
        if len(items) == 1:
            result, success = self._process_batch_safe(items)
            if success:
                return result
            else:
                print(f"Failed to process even single item")
                self.stats.failed_items += 1
                return [None]
        
        mid = len(items) // 2
        left_items = items[:mid]
        right_items = items[mid:]
        
        print(f"Splitting batch {len(items)} -> {len(left_items)} + {len(right_items)}")
        
        left_results = self._process_with_split(left_items)
        right_results = self._process_with_split(right_items)
        
        return left_results + right_results
    
    def process(self, items: List[Any], show_progress: bool = True) -> List[Any]:
        total_items = len(items)
        self.stats = ProcessingStats(total_items=total_items)
        self.config.batch_size_history.clear()
        
        start_time = time.time()
        
        if total_items > 0 and self._per_item_memory_mb is None:
            self._estimate_per_item_memory(items[0])
        
        results = []
        idx = 0
        
        if show_progress:
            from tqdm import tqdm
            pbar = tqdm(total=total_items, desc="Processing")
        
        while idx < total_items:
            batch_size = min(self.config.current_batch_size, total_items - idx)
            batch = items[idx:idx + batch_size]
            
            self.config.batch_size_history.append(batch_size)
            
            mem_before = self.memory_monitor.get_memory_info()
            
            batch_results, success = self._process_batch_safe(batch)
            
            mem_after = self.memory_monitor.get_memory_info()
            self.stats.memory_peak = max(self.stats.memory_peak, mem_after.utilization)
            
            if success:
                results.extend(batch_results)
                self.stats.processed_items += len(batch)
                idx += batch_size
                
                if show_progress:
                    pbar.update(len(batch))
                
                self._adjust_batch_size(mem_after, success=True)
            else:
                if len(batch) == 1:
                    print(f"Failed to process item at index {idx}")
                    results.append(None)
                    self.stats.failed_items += 1
                    idx += 1
                    
                    if show_progress:
                        pbar.update(1)
                else:
                    print(f"OOM with batch size {batch_size}, splitting...")
                    split_results = self._process_with_split(batch)
                    results.extend(split_results)
                    
                    success_count = sum(1 for r in split_results if r is not None)
                    fail_count = len(split_results) - success_count
                    self.stats.processed_items += success_count
                    self.stats.failed_items += fail_count
                    idx += batch_size
                    
                    if show_progress:
                        pbar.update(len(batch))
                    
                    self.config.current_batch_size = max(
                        self.config.min_batch_size,
                        self.config.current_batch_size // 2
                    )
                    self.config.consecutive_failures += 1
        
        if show_progress:
            pbar.close()
        
        self.stats.total_time = time.time() - start_time
        if self.stats.processed_items > 0:
            self.stats.avg_time_per_item = self.stats.total_time / self.stats.processed_items
        
        return results
    
    def get_stats(self) -> ProcessingStats:
        return self.stats
    
    def get_batch_size_history(self) -> List[int]:
        return self.config.batch_size_history.copy()


def process_with_dynamic_batch(
    items: List[Any],
    process_func: Callable[[Any], Any],
    initial_batch_size: int = 4,
    min_batch_size: int = 1,
    max_batch_size: int = 8,
    show_progress: bool = True
) -> Tuple[List[Any], ProcessingStats]:
    processor = DynamicBatchProcessor(
        process_func=process_func,
        initial_batch_size=initial_batch_size,
        min_batch_size=min_batch_size,
        max_batch_size=max_batch_size
    )
    
    results = processor.process(items, show_progress=show_progress)
    stats = processor.get_stats()
    
    return results, stats


def check_oom_safe(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print(f"OOM Error in {func.__name__}: {e}")
                try:
                    import torch
                    torch.cuda.empty_cache()
                except:
                    pass
                return None
            raise e
    return wrapper
