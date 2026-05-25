import threading
import time
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Semaphore
from config import BATCH_CONCURRENCY, HOST_CONCURRENCY


class ConcurrencyController:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or BATCH_CONCURRENCY
        self._semaphores: Dict[str, Semaphore] = {}
        self._global_semaphore = Semaphore(self.max_workers)
        self._lock = threading.Lock()

    def _get_host_semaphore(self, hostname: str) -> Semaphore:
        with self._lock:
            if hostname not in self._semaphores:
                self._semaphores[hostname] = Semaphore(HOST_CONCURRENCY)
            return self._semaphores[hostname]

    def execute_on_hosts(self, hosts: List[Any], 
                        task_func: Callable[[Any], Dict[str, Any]],
                        max_workers: Optional[int] = None,
                        progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        workers = max_workers or self.max_workers
        results = []
        total = len(hosts)
        completed = 0
        result_lock = threading.Lock()

        def wrapped_task(host):
            nonlocal completed
            hostname = host.hostname if hasattr(host, 'hostname') else str(host)
            
            host_sem = self._get_host_semaphore(hostname)
            
            with self._global_semaphore, host_sem:
                try:
                    result = task_func(host)
                except Exception as e:
                    result = {
                        'hostname': hostname,
                        'success': False,
                        'error': str(e)
                    }
                
                with result_lock:
                    nonlocal completed
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, hostname)
                    results.append(result)
                return result

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(wrapped_task, host) for host in hosts]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        return results

    def execute_batches(self, hosts: List[Any],
                       task_func: Callable[[Any], Dict[str, Any]],
                       batch_size: Optional[int] = None,
                       delay_between_batches: float = 0.0,
                       progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[Dict[str, Any]]:
        batch_size = batch_size or self.max_workers
        results = []
        total = len(hosts)
        completed = 0

        for i in range(0, total, batch_size):
            batch = hosts[i:i + batch_size]
            
            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = [executor.submit(task_func, host) for host in batch]
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        completed += 1
                        hostname = result.get('hostname', 'unknown')
                        if progress_callback:
                            progress_callback(completed, total, hostname)
                    except Exception as e:
                        results.append({
                            'success': False,
                            'error': str(e)
                        })
            
            if i + batch_size < total and delay_between_batches > 0:
                time.sleep(delay_between_batches)

        return results


class RateLimiter:
    def __init__(self, max_calls: int, period: float = 1.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self._lock = threading.Lock()

    def __enter__(self):
        with self._lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            
            if len(self.calls) >= self.max_calls:
                sleep_time = self.calls[0] + self.period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.calls = self.calls[1:]
            
            self.calls.append(time.time())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class ThrottledExecutor:
    def __init__(self, max_concurrent: int = 5, rate_limit: int = 10, rate_period: float = 1.0):
        self.max_concurrent = max_concurrent
        self.rate_limiter = RateLimiter(rate_limit, rate_period)
        self.semaphore = Semaphore(max_concurrent)

    def execute(self, func: Callable, *args, **kwargs):
        with self.semaphore, self.rate_limiter:
            return func(*args, **kwargs)

    def map(self, func: Callable, items: List[Any], 
            progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Any]:
        results = []
        total = len(items)
        completed = 0
        result_lock = threading.Lock()

        def wrapped(item):
            nonlocal completed
            result = self.execute(func, item)
            with result_lock:
                nonlocal completed
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
            return result

        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = [executor.submit(wrapped, item) for item in items]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({'success': False, 'error': str(e)})

        return results
