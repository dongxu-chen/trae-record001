import re
import os
import time
import threading
from datetime import datetime
from collections import defaultdict, deque
from urllib.parse import urlparse
from user_agents import parse
import geoip2.database
import geoip2.errors

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

ACCESS_LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)\s+'
    r'"(?P<referrer>[^"]*)"\s+"(?P<user_agent>[^"]*)"(?:\s+(?P<response_time>\S+))?'
)

ERROR_LOG_PATTERN = re.compile(
    r'^(?P<time>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'\[(?P<level>\w+)\]\s+\d+#\d+:\s+\*(?P<connection_id>\d+)\s+'
    r'(?P<message>.*?),\s+client:\s+(?P<ip>\S+),\s+'
    r'server:\s+(?P<server>\S+),\s+request:\s+"(?P<request>[^"]+)",\s+'
    r'(?:host:\s+"(?P<host>[^"]+)"\s*,?\s*)?'
    r'(?:upstream:\s+"(?P<upstream>[^"]+)"\s*,?\s*)?'
    r'(?:referrer:\s+"(?P<referrer>[^"]+)")?'
)

ERROR_LOG_PATTERN_SIMPLE = re.compile(
    r'^(?P<time>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'\[(?P<level>\w+)\]\s+\d+#\d+:\s+(?P<message>.*)'
)

TIME_FORMAT_ACCESS = '%d/%b/%Y:%H:%M:%S %z'
TIME_FORMAT_ERROR = '%Y/%m/%d %H:%M:%S'


class GeoIPCache:
    def __init__(self, db_path, ttl=3600, cleanup_interval=300):
        self.db_path = db_path
        self.ttl = ttl
        self.cleanup_interval = cleanup_interval
        self._cache = {}
        self._lock = threading.RLock()
        self._reader = None
        self._last_db_check = 0
        self._db_mtime = 0
        self._stop_cleanup = threading.Event()
        self._cleanup_thread = None
        self._init_reader()
        self._start_cleanup_thread()
    
    def _init_reader(self):
        try:
            if os.path.exists(self.db_path):
                self._reader = geoip2.database.Reader(self.db_path)
                self._db_mtime = os.path.getmtime(self.db_path)
                self._last_db_check = time.time()
        except Exception as e:
            print(f"Warning: Failed to load GeoIP database: {e}")
            self._reader = None
    
    def _check_db_update(self):
        if not os.path.exists(self.db_path):
            if self._reader:
                self._reader.close()
                self._reader = None
                with self._lock:
                    self._cache.clear()
            return
        
        current_mtime = os.path.getmtime(self.db_path)
        if current_mtime != self._db_mtime:
            print(f"GeoIP database updated, reloading...")
            if self._reader:
                self._reader.close()
            self._init_reader()
            with self._lock:
                self._cache.clear()
    
    def _start_cleanup_thread(self):
        if self._cleanup_thread is not None:
            return
        
        def cleanup_worker():
            while not self._stop_cleanup.is_set():
                try:
                    time.sleep(self.cleanup_interval)
                    self._check_db_update()
                    self._cleanup_expired()
                except Exception as e:
                    print(f"Error in GeoIP cache cleanup: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_expired(self):
        now = time.time()
        with self._lock:
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if now - timestamp > self.ttl
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def get(self, ip):
        if not self._reader:
            return None
        
        with self._lock:
            if ip in self._cache:
                result, timestamp = self._cache[ip]
                if time.time() - timestamp <= self.ttl:
                    return result
        
        try:
            response = self._reader.city(ip)
            result = {
                'country': response.country.name if response.country.name else 'Unknown',
                'country_code': response.country.iso_code if response.country.iso_code else 'Unknown',
                'city': response.city.name if response.city.name else 'Unknown',
                'latitude': response.location.latitude,
                'longitude': response.location.longitude
            }
            
            with self._lock:
                self._cache[ip] = (result, time.time())
            
            return result
        except (geoip2.errors.AddressNotFoundError, ValueError):
            result = None
            with self._lock:
                self._cache[ip] = (result, time.time())
            return result
    
    def clear(self):
        with self._lock:
            self._cache.clear()
    
    def stop(self):
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1)
        if self._reader:
            self._reader.close()
    
    def __del__(self):
        self.stop()


class LogFileHandler(FileSystemEventHandler):
    def __init__(self, log_parser, file_path, log_type, debounce=0.5):
        super().__init__()
        self.log_parser = log_parser
        self.file_path = file_path
        self.log_type = log_type
        self.debounce = debounce
        self._last_event = 0
        self._lock = threading.Lock()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if os.path.abspath(event.src_path) != os.path.abspath(self.file_path):
            return
        
        with self._lock:
            now = time.time()
            if now - self._last_event < self.debounce:
                return
            self._last_event = now
        
        print(f"Detected change in {self.log_type} log, reading updates...")
        if self.log_type == 'access':
            new_logs = self.log_parser.read_new_access_logs()
        else:
            new_logs = self.log_parser.read_new_error_logs()
        
        if new_logs:
            print(f"Loaded {len(new_logs)} new {self.log_type} log entries")


class LogFileWatcher:
    def __init__(self, log_parser, config):
        self.log_parser = log_parser
        self.config = config
        self.observer = None
        self._handlers = []
    
    def start(self):
        if not WATCHDOG_AVAILABLE:
            print("Warning: watchdog library not available, falling back to polling")
            return False
        
        if self.observer:
            return True
        
        try:
            self.observer = Observer()
            
            access_path = os.path.abspath(self.config.ACCESS_LOG_PATH)
            if os.path.exists(access_path):
                access_dir = os.path.dirname(access_path)
                access_handler = LogFileHandler(
                    self.log_parser,
                    access_path,
                    'access',
                    self.config.FILE_WATCHER_DEBOUNCE
                )
                self.observer.schedule(access_handler, access_dir, recursive=False)
                self._handlers.append(access_handler)
                print(f"Watching access log: {access_path}")
            
            error_path = os.path.abspath(self.config.ERROR_LOG_PATH)
            if os.path.exists(error_path):
                error_dir = os.path.dirname(error_path)
                error_handler = LogFileHandler(
                    self.log_parser,
                    error_path,
                    'error',
                    self.config.FILE_WATCHER_DEBOUNCE
                )
                self.observer.schedule(error_handler, error_dir, recursive=False)
                self._handlers.append(error_handler)
                print(f"Watching error log: {error_path}")
            
            self.observer.start()
            print("Log file watcher started successfully")
            return True
        except Exception as e:
            print(f"Failed to start log file watcher: {e}")
            self.observer = None
            return False
    
    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
            print("Log file watcher stopped")


class PathAggregator:
    def __init__(self, patterns=None, aggregate_query=True):
        self.patterns = patterns or []
        self.aggregate_query = aggregate_query
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]
    
    def aggregate(self, path):
        if not path:
            return path
        
        if self.aggregate_query:
            parsed = urlparse(path)
            path = parsed.path
        
        for pattern in self._compiled_patterns:
            path = pattern.sub('/{param}', path)
        
        return path


class LogParser:
    def __init__(self, config):
        self.config = config
        self.access_log_path = config.ACCESS_LOG_PATH
        self.error_log_path = config.ERROR_LOG_PATH
        
        self.access_logs = deque(maxlen=config.MAX_LOG_LINES)
        self.error_logs = deque(maxlen=config.MAX_LOG_LINES)
        
        self.access_file_position = 0
        self.error_file_position = 0
        
        self.geoip_cache = GeoIPCache(
            config.GEOIP_DB_PATH,
            config.GEOIP_CACHE_TTL,
            config.GEOIP_CACHE_CLEANUP_INTERVAL
        )
        
        self.path_aggregator = PathAggregator(
            config.AGGREGATE_PATH_PATTERNS,
            config.AGGREGATE_QUERY_PARAMS
        )
        
        self.file_watcher = None
        if config.USE_FILE_WATCHER:
            self.file_watcher = LogFileWatcher(self, config)
    
    def start_watcher(self):
        if self.file_watcher:
            return self.file_watcher.start()
        return False
    
    def stop_watcher(self):
        if self.file_watcher:
            self.file_watcher.stop()
    
    def get_geo_info(self, ip):
        return self.geoip_cache.get(ip)
    
    def aggregate_path(self, path):
        return self.path_aggregator.aggregate(path)
    
    def parse_access_log_line(self, line):
        match = ACCESS_LOG_PATTERN.match(line.strip())
        if not match:
            return None
        
        data = match.groupdict()
        
        try:
            timestamp = datetime.strptime(data['time'], TIME_FORMAT_ACCESS)
        except ValueError:
            return None
        
        response_time = None
        if data.get('response_time') and data['response_time'] != '-':
            try:
                response_time = float(data['response_time'])
            except ValueError:
                pass
        
        ua_string = data['user_agent']
        try:
            user_agent = parse(ua_string)
            os_info = user_agent.os.family if user_agent.os.family else 'Unknown'
            browser = user_agent.browser.family if user_agent.browser.family else 'Unknown'
            is_mobile = user_agent.is_mobile
        except Exception:
            os_info = 'Unknown'
            browser = 'Unknown'
            is_mobile = False
        
        geo_info = self.get_geo_info(data['ip'])
        original_path = data['path']
        aggregated_path = self.aggregate_path(original_path)
        
        return {
            'ip': data['ip'],
            'timestamp': timestamp,
            'time_str': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'method': data['method'],
            'path': original_path,
            'aggregated_path': aggregated_path,
            'protocol': data['protocol'],
            'status': int(data['status']),
            'size': int(data['size']) if data['size'] != '-' else 0,
            'referrer': data['referrer'],
            'user_agent': ua_string,
            'os': os_info,
            'browser': browser,
            'is_mobile': is_mobile,
            'response_time': response_time,
            'geo': geo_info
        }
    
    def parse_error_log_line(self, line):
        match = ERROR_LOG_PATTERN.match(line.strip())
        if not match:
            match = ERROR_LOG_PATTERN_SIMPLE.match(line.strip())
            if not match:
                return None
            data = match.groupdict()
            try:
                timestamp = datetime.strptime(data['time'], TIME_FORMAT_ERROR)
            except ValueError:
                return None
            return {
                'timestamp': timestamp,
                'time_str': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': data['level'],
                'message': data['message'],
                'ip': None,
                'server': None,
                'request': None
            }
        
        data = match.groupdict()
        try:
            timestamp = datetime.strptime(data['time'], TIME_FORMAT_ERROR)
        except ValueError:
            return None
        
        geo_info = self.get_geo_info(data['ip']) if data['ip'] else None
        
        return {
            'timestamp': timestamp,
            'time_str': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': data['level'],
            'connection_id': data.get('connection_id'),
            'message': data['message'],
            'ip': data['ip'],
            'server': data['server'],
            'request': data.get('request'),
            'host': data.get('host'),
            'upstream': data.get('upstream'),
            'referrer': data.get('referrer'),
            'geo': geo_info
        }
    
    def read_new_access_logs(self):
        if not os.path.exists(self.access_log_path):
            return []
        
        new_logs = []
        try:
            file_size = os.path.getsize(self.access_log_path)
            if file_size < self.access_file_position:
                print("Access log file truncated, resetting position")
                self.access_file_position = 0
            
            with open(self.access_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.access_file_position)
                for line in f:
                    parsed = self.parse_access_log_line(line)
                    if parsed:
                        new_logs.append(parsed)
                        self.access_logs.append(parsed)
                self.access_file_position = f.tell()
        except Exception as e:
            print(f"Error reading access log: {e}")
        
        return new_logs
    
    def read_new_error_logs(self):
        if not os.path.exists(self.error_log_path):
            return []
        
        new_logs = []
        try:
            file_size = os.path.getsize(self.error_log_path)
            if file_size < self.error_file_position:
                print("Error log file truncated, resetting position")
                self.error_file_position = 0
            
            with open(self.error_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.error_file_position)
                for line in f:
                    parsed = self.parse_error_log_line(line)
                    if parsed:
                        new_logs.append(parsed)
                        self.error_logs.append(parsed)
                self.error_file_position = f.tell()
        except Exception as e:
            print(f"Error reading error log: {e}")
        
        return new_logs
    
    def refresh(self):
        new_access = self.read_new_access_logs()
        new_error = self.read_new_error_logs()
        return {
            'new_access_count': len(new_access),
            'new_error_count': len(new_error),
            'total_access': len(self.access_logs),
            'total_error': len(self.error_logs),
            'watcher_active': self.file_watcher is not None and self.file_watcher.observer is not None
        }
    
    def filter_logs(self, logs, start_time=None, end_time=None, keyword=None):
        filtered = list(logs)
        
        if start_time:
            filtered = [l for l in filtered if l['timestamp'] >= start_time]
        if end_time:
            filtered = [l for l in filtered if l['timestamp'] <= end_time]
        if keyword:
            keyword = keyword.lower()
            filtered = [
                l for l in filtered
                if keyword in str(l.get('path', '')).lower() or
                   keyword in str(l.get('aggregated_path', '')).lower() or
                   keyword in str(l.get('ip', '')).lower() or
                   keyword in str(l.get('message', '')).lower() or
                   keyword in str(l.get('user_agent', '')).lower()
            ]
        
        return filtered
    
    def get_hourly_stats(self, access_logs):
        hourly = defaultdict(lambda: {'count': 0, 'errors': 0, 'avg_response_time': 0, 'total_time': 0})
        
        for log in access_logs:
            hour_key = log['timestamp'].strftime('%Y-%m-%d %H:00')
            hourly[hour_key]['count'] += 1
            if log['status'] >= 400:
                hourly[hour_key]['errors'] += 1
            if log.get('response_time'):
                hourly[hour_key]['total_time'] += log['response_time']
        
        for hour_key, data in hourly.items():
            if data['count'] > 0 and data['total_time'] > 0:
                data['avg_response_time'] = round(data['total_time'] / data['count'], 3)
        
        return dict(hourly)
    
    def get_status_distribution(self, access_logs):
        status_dist = defaultdict(int)
        for log in access_logs:
            status_group = f"{(log['status'] // 100) * 100}"
            status_dist[status_group] += 1
        return dict(status_dist)
    
    def get_slow_requests(self, access_logs, threshold=1.0, limit=20, aggregate=True):
        slow = [
            log for log in access_logs
            if log.get('response_time') and log['response_time'] >= threshold
        ]
        
        if not aggregate or not self.config.AGGREGATE_SLOW_REQUESTS:
            slow.sort(key=lambda x: x['response_time'], reverse=True)
            return slow[:limit]
        
        aggregated = defaultdict(lambda: {
            'path': '',
            'aggregated_path': '',
            'count': 0,
            'total_time': 0,
            'max_time': 0,
            'min_time': float('inf'),
            'avg_time': 0,
            'status_codes': defaultdict(int),
            'methods': defaultdict(int),
            'sample_logs': []
        })
        
        for log in slow:
            agg_path = log['aggregated_path']
            entry = aggregated[agg_path]
            entry['path'] = log['path']
            entry['aggregated_path'] = agg_path
            entry['count'] += 1
            entry['total_time'] += log['response_time']
            entry['max_time'] = max(entry['max_time'], log['response_time'])
            entry['min_time'] = min(entry['min_time'], log['response_time'])
            entry['status_codes'][str(log['status'])] += 1
            entry['methods'][log['method']] += 1
            
            if len(entry['sample_logs']) < 5:
                entry['sample_logs'].append({
                    'time_str': log['time_str'],
                    'path': log['path'],
                    'response_time': log['response_time'],
                    'status': log['status'],
                    'ip': log['ip']
                })
        
        result = []
        for agg_path, entry in aggregated.items():
            entry['avg_time'] = round(entry['total_time'] / entry['count'], 3)
            if entry['min_time'] == float('inf'):
                entry['min_time'] = 0
            entry['top_status'] = max(entry['status_codes'].items(), key=lambda x: x[1])[0] if entry['status_codes'] else '200'
            entry['top_method'] = max(entry['methods'].items(), key=lambda x: x[1])[0] if entry['methods'] else 'GET'
            result.append(entry)
        
        result.sort(key=lambda x: x['avg_time'], reverse=True)
        return result[:limit]
    
    def get_top_paths(self, access_logs, limit=10, aggregate=True):
        if not aggregate or not self.config.AGGREGATE_SLOW_REQUESTS:
            path_count = defaultdict(int)
            for log in access_logs:
                path_count[log['path']] += 1
            return sorted(path_count.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        path_count = defaultdict(int)
        for log in access_logs:
            path_count[log['aggregated_path']] += 1
        return sorted(path_count.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_top_ips(self, access_logs, limit=10):
        ip_count = defaultdict(int)
        for log in access_logs:
            ip_count[log['ip']] += 1
        return sorted(ip_count.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_geo_distribution(self, access_logs):
        country_count = defaultdict(int)
        city_count = defaultdict(int)
        for log in access_logs:
            if log.get('geo'):
                country = log['geo'].get('country', 'Unknown')
                city = log['geo'].get('city', 'Unknown')
                country_count[country] += 1
                city_count[f"{city}, {country}"] += 1
        
        return {
            'countries': dict(country_count),
            'cities': dict(city_count)
        }
    
    def get_error_level_distribution(self, error_logs):
        level_dist = defaultdict(int)
        for log in error_logs:
            level_dist[log['level']] += 1
        return dict(level_dist)
    
    def get_recent_errors(self, error_logs, limit=20):
        return list(error_logs)[-limit:][::-1]
    
    def get_overview(self, start_time=None, end_time=None, keyword=None):
        if not self.file_watcher or not self.file_watcher.observer:
            self.refresh()
        
        filtered_access = self.filter_logs(self.access_logs, start_time, end_time, keyword)
        filtered_error = self.filter_logs(self.error_logs, start_time, end_time, keyword)
        
        total_requests = len(filtered_access)
        total_errors = len(filtered_error)
        
        total_traffic = sum(log['size'] for log in filtered_access)
        avg_response_time = 0
        response_times = [log['response_time'] for log in filtered_access if log.get('response_time')]
        if response_times:
            avg_response_time = round(sum(response_times) / len(response_times), 3)
        
        error_rate = 0
        if total_requests > 0:
            error_requests = sum(1 for log in filtered_access if log['status'] >= 400)
            error_rate = round((error_requests / total_requests) * 100, 2)
        
        unique_ips = len(set(log['ip'] for log in filtered_access))
        
        return {
            'total_requests': total_requests,
            'total_errors': total_errors,
            'total_traffic': total_traffic,
            'avg_response_time': avg_response_time,
            'error_rate': error_rate,
            'unique_ips': unique_ips,
            'hourly_stats': self.get_hourly_stats(filtered_access),
            'status_distribution': self.get_status_distribution(filtered_access),
            'slow_requests': self.get_slow_requests(
                filtered_access,
                self.config.SLOW_REQUEST_THRESHOLD,
                aggregate=self.config.AGGREGATE_SLOW_REQUESTS
            ),
            'top_paths': self.get_top_paths(filtered_access),
            'top_ips': self.get_top_ips(filtered_access),
            'geo_distribution': self.get_geo_distribution(filtered_access),
            'error_level_distribution': self.get_error_level_distribution(filtered_error),
            'recent_errors': self.get_recent_errors(filtered_error),
            'watcher_active': self.file_watcher is not None and self.file_watcher.observer is not None,
            'geoip_cache_size': len(self.geoip_cache._cache)
        }
    
    def shutdown(self):
        self.stop_watcher()
        self.geoip_cache.stop()
