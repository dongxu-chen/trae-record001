import time
import threading
import queue
from collections import deque
from datetime import datetime
from app.redis_client import get_redis


class MetricsStream:
    def __init__(self, max_history=1000):
        self.redis = get_redis()
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.raw_metrics_queue = queue.Queue(maxsize=10000)
        self.aggregated_metrics = deque(maxlen=max_history)
        self.monitoring = False
        self.collector_thread = None
        self.aggregator_thread = None
        self.callbacks = []
        self.last_slowlog_id = -1
        self.new_slowlogs_queue = queue.Queue(maxsize=1000)
        self.stream_interval = 0.1
        self.aggregate_interval = 1.0
        self._last_aggregate_time = time.time()
        self._aggregate_buffer = []
        self._lock = threading.Lock()
    
    def _collect_raw_metrics(self):
        try:
            info = self.redis.info()
            slowlog_len = self.redis.execute_command('SLOWLOG LEN')
            
            metric = {
                'timestamp': time.time(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_rss': info.get('used_memory_rss', 0),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'commands_per_second': info.get('instantaneous_ops_per_sec', 0),
                'instantaneous_input_kbps': info.get('instantaneous_input_kbps', 0),
                'instantaneous_output_kbps': info.get('instantaneous_output_kbps', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'total_net_input_bytes': info.get('total_net_input_bytes', 0),
                'total_net_output_bytes': info.get('total_net_output_bytes', 0),
                'slowlog_length': slowlog_len,
                'rejected_connections': info.get('rejected_connections', 0),
                'evicted_keys': info.get('evicted_keys', 0),
                'blocked_clients': info.get('blocked_clients', 0),
                'redis_cpu_sys': info.get('used_cpu_sys', 0),
                'redis_cpu_user': info.get('used_cpu_user', 0),
                'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
                'is_raw': True
            }
            
            return metric
        except Exception as e:
            return {
                'timestamp': time.time(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                'error': str(e),
                'is_raw': True
            }
    
    def _calculate_hit_rate(self, info):
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        if total == 0:
            return 100.0
        return round((hits / total) * 100, 2)
    
    def _collector_loop(self):
        while self.monitoring:
            start_time = time.time()
            
            try:
                metric = self._collect_raw_metrics()
                
                if not self.raw_metrics_queue.full():
                    self.raw_metrics_queue.put(metric)
                
                self._collect_slowlogs()
                
                with self._lock:
                    self.metrics_history.append(metric)
                
                for callback in self.callbacks:
                    try:
                        callback(metric)
                    except Exception:
                        pass
            except Exception:
                pass
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.stream_interval - elapsed)
            time.sleep(sleep_time)
    
    def _collect_slowlogs(self):
        try:
            logs = self.redis.execute_command('SLOWLOG GET', 10)
            
            for log in reversed(logs):
                log_id = log[0]
                if log_id > self.last_slowlog_id:
                    self.last_slowlog_id = log_id
                    timestamp = log[1]
                    duration = log[2]
                    command = log[3] if len(log) > 3 else []
                    client_ip = log[4] if len(log) > 4 else None
                    
                    slowlog_entry = {
                        'id': log_id,
                        'timestamp': timestamp,
                        'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                        'duration_ms': duration / 1000,
                        'command': ' '.join(command) if isinstance(command, list) else str(command),
                        'client_ip': client_ip
                    }
                    
                    if not self.new_slowlogs_queue.full():
                        self.new_slowlogs_queue.put(slowlog_entry)
        except Exception:
            pass
    
    def _aggregator_loop(self):
        while self.monitoring:
            start_time = time.time()
            
            try:
                raw_metrics = []
                while not self.raw_metrics_queue.empty() and len(raw_metrics) < 1000:
                    raw_metrics.append(self.raw_metrics_queue.get())
                
                if raw_metrics:
                    aggregated = self._aggregate_metrics(raw_metrics)
                    
                    with self._lock:
                        self.aggregated_metrics.append(aggregated)
                    
                    self._last_aggregate_time = time.time()
            except Exception:
                pass
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.aggregate_interval - elapsed)
            time.sleep(sleep_time)
    
    def _aggregate_metrics(self, raw_metrics):
        if not raw_metrics:
            return None
        
        timestamps = [m['timestamp'] for m in raw_metrics if 'error' not in m]
        valid_metrics = [m for m in raw_metrics if 'error' not in m]
        
        if not valid_metrics:
            return {
                'timestamp': time.time(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'No valid metrics in window',
                'sample_count': len(raw_metrics)
            }
        
        def avg(key):
            values = [m.get(key, 0) for m in valid_metrics]
            return sum(values) / len(values) if values else 0
        
        def max_val(key):
            values = [m.get(key, 0) for m in valid_metrics]
            return max(values) if values else 0
        
        def min_val(key):
            values = [m.get(key, 0) for m in valid_metrics]
            return min(values) if values else 0
        
        first = valid_metrics[0]
        last = valid_metrics[-1]
        
        return {
            'timestamp': time.time(),
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'window_start': min(timestamps),
            'window_end': max(timestamps),
            'sample_count': len(valid_metrics),
            'connected_clients': {
                'avg': avg('connected_clients'),
                'max': max_val('connected_clients'),
                'min': min_val('connected_clients'),
                'last': last.get('connected_clients', 0)
            },
            'used_memory': {
                'avg': avg('used_memory'),
                'max': max_val('used_memory'),
                'min': min_val('used_memory'),
                'last': last.get('used_memory', 0),
                'human': last.get('used_memory_human', '0B')
            },
            'commands_per_second': {
                'avg': avg('commands_per_second'),
                'max': max_val('commands_per_second'),
                'min': min_val('commands_per_second'),
                'last': last.get('commands_per_second', 0)
            },
            'hit_rate': {
                'avg': avg('hit_rate'),
                'max': max_val('hit_rate'),
                'min': min_val('hit_rate'),
                'last': last.get('hit_rate', 0)
            },
            'network': {
                'input_kbps_avg': avg('instantaneous_input_kbps'),
                'output_kbps_avg': avg('instantaneous_output_kbps'),
                'total_input_bytes': last.get('total_net_input_bytes', 0) - first.get('total_net_input_bytes', 0),
                'total_output_bytes': last.get('total_net_output_bytes', 0) - first.get('total_net_output_bytes', 0)
            },
            'cpu': {
                'sys_avg': avg('redis_cpu_sys'),
                'user_avg': avg('redis_cpu_user')
            },
            'slowlog_length': last.get('slowlog_length', 0),
            'evicted_keys': last.get('evicted_keys', 0),
            'rejected_connections': last.get('rejected_connections', 0),
            'blocked_clients': last.get('blocked_clients', 0),
            'mem_fragmentation_ratio': avg('mem_fragmentation_ratio')
        }
    
    def start_streaming(self, stream_interval_ms=100, aggregate_interval_ms=1000):
        if self.monitoring:
            return
        
        self.stream_interval = stream_interval_ms / 1000.0
        self.aggregate_interval = aggregate_interval_ms / 1000.0
        self.monitoring = True
        
        self.collector_thread = threading.Thread(
            target=self._collector_loop,
            daemon=True
        )
        self.collector_thread.start()
        
        self.aggregator_thread = threading.Thread(
            target=self._aggregator_loop,
            daemon=True
        )
        self.aggregator_thread.start()
    
    def stop_streaming(self):
        self.monitoring = False
        
        if self.collector_thread:
            self.collector_thread.join(timeout=1)
        
        if self.aggregator_thread:
            self.aggregator_thread.join(timeout=1)
    
    def get_latest_metrics(self):
        with self._lock:
            if self.metrics_history:
                return self.metrics_history[-1]
        return self._collect_raw_metrics()
    
    def get_raw_metrics_history(self, count=None):
        with self._lock:
            history = list(self.metrics_history)
            if count:
                return history[-count:]
            return history
    
    def get_aggregated_metrics(self, count=None):
        with self._lock:
            history = list(self.aggregated_metrics)
            if count:
                return history[-count:]
            return history

    def get_latest_aggregated(self):
        with self._lock:
            if self.aggregated_metrics:
                latest = self.aggregated_metrics[-1].copy()
                latest['stream_stats'] = {
                    'is_streaming': self.monitoring,
                    'stream_interval_ms': int(self.stream_interval * 1000),
                    'aggregate_interval_ms': int(self.aggregate_interval * 1000),
                    'queue_size': self.raw_metrics_queue.qsize(),
                    'queue_max': self.raw_metrics_queue.maxsize,
                    'total_collected': len(self.metrics_history),
                    'total_aggregated': len(self.aggregated_metrics),
                    'slowlog_queue_size': self.new_slowlogs_queue.qsize()
                }
                return latest
            return None

    def get_stream_stats(self):
        with self._lock:
            return {
                'is_streaming': self.monitoring,
                'stream_interval_ms': int(self.stream_interval * 1000),
                'aggregate_interval_ms': int(self.aggregate_interval * 1000),
                'queue_size': self.raw_metrics_queue.qsize(),
                'queue_max': self.raw_metrics_queue.maxsize,
                'total_collected': len(self.metrics_history),
                'total_aggregated': len(self.aggregated_metrics),
                'slowlog_queue_size': self.new_slowlogs_queue.qsize(),
                'last_slowlog_id': self.last_slowlog_id
            }
    
    def get_new_slowlogs(self, timeout=0):
        logs = []
        try:
            while True:
                log = self.new_slowlogs_queue.get_nowait()
                logs.append(log)
        except queue.Empty:
            pass
        return logs
    
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    def remove_callback(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def get_instant_metrics(self):
        metric = self._collect_raw_metrics()
        return {
            'timestamp': metric['timestamp'],
            'datetime': metric['datetime'].split('.')[0],
            'connected_clients': metric.get('connected_clients', 0),
            'used_memory': metric.get('used_memory', 0),
            'used_memory_human': metric.get('used_memory_human', '0B'),
            'commands_per_second': metric.get('commands_per_second', 0),
            'keyspace_hits': metric.get('keyspace_hits', 0),
            'keyspace_misses': metric.get('keyspace_misses', 0),
            'hit_rate': metric.get('hit_rate', 100),
            'total_commands_processed': metric.get('total_commands_processed', 0),
            'slowlog_length': metric.get('slowlog_length', 0),
            'rejected_connections': metric.get('rejected_connections', 0),
            'evicted_keys': metric.get('evicted_keys', 0),
            'blocked_clients': metric.get('blocked_clients', 0),
            'is_streaming': self.monitoring,
            'stream_interval_ms': int(self.stream_interval * 1000)
        }
    
    def check_slowlog_new_entries(self, last_id=-1):
        try:
            logs = self.redis.execute_command('SLOWLOG GET', 10)
            new_logs = []
            
            for log in logs:
                log_id = log[0]
                if log_id > last_id:
                    timestamp = log[1]
                    duration = log[2]
                    command = log[3] if len(log) > 3 else []
                    client_ip = log[4] if len(log) > 4 else None
                    
                    new_logs.append({
                        'id': log_id,
                        'timestamp': timestamp,
                        'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                        'duration_ms': duration / 1000,
                        'command': ' '.join(command) if isinstance(command, list) else str(command),
                        'client_ip': client_ip
                    })
                else:
                    break
            
            return new_logs
        except Exception:
            return []
    
    def get_database_stats(self):
        try:
            info = self.redis.info('keyspace')
            db_stats = []
            
            for db_name, stats in info.items():
                if db_name.startswith('db'):
                    db_stats.append({
                        'database': db_name,
                        'keys': stats.get('keys', 0),
                        'expires': stats.get('expires', 0),
                        'avg_ttl': stats.get('avg_ttl', 0)
                    })
            
            return db_stats
        except Exception:
            return []
    
    def get_command_stats(self):
        try:
            info = self.redis.info('commandstats')
            command_stats = []
            
            for cmd, stats in info.items():
                cmd_name = cmd.replace('cmdstat_', '').upper()
                command_stats.append({
                    'command': cmd_name,
                    'calls': stats.get('calls', 0),
                    'usec': stats.get('usec', 0),
                    'usec_per_call': stats.get('usec_per_call', 0)
                })
            
            command_stats.sort(key=lambda x: x['calls'], reverse=True)
            return command_stats[:20]
        except Exception:
            return []


class RealTimeMonitor(MetricsStream):
    pass
