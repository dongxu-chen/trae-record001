import hashlib
import time
import threading
from collections import defaultdict


class EventDeduplicator:
    def __init__(self, window_seconds=300, max_size=1000):
        self.window_seconds = window_seconds
        self.max_size = max_size
        self.events = defaultdict(lambda: {'count': 0, 'first_seen': 0, 'last_seen': 0, 'event': None})
        self.lock = threading.Lock()
        self.flush_callback = None
        self.flush_thread = None
        self._running = False

    def _generate_key(self, event):
        obj = event.get('object', {})
        namespace = obj.get('metadata', {}).get('namespace', '')
        name = obj.get('involvedObject', {}).get('name', '')
        if not name:
            name = obj.get('metadata', {}).get('name', '')
        reason = obj.get('reason', '')
        kind = obj.get('involvedObject', {}).get('kind', '')
        
        key_string = f"{namespace}:{kind}:{name}:{reason}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def add_event(self, event):
        key = self._generate_key(event)
        current_time = time.time()
        
        with self.lock:
            if key in self.events:
                self.events[key]['count'] += 1
                self.events[key]['last_seen'] = current_time
                return False, self.events[key]['count']
            else:
                self.events[key] = {
                    'count': 1,
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'event': event
                }
                return True, 1

    def set_flush_callback(self, callback):
        self.flush_callback = callback

    def start_flush_worker(self):
        if self.flush_thread is None:
            self._running = True
            self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
            self.flush_thread.start()

    def _flush_worker(self):
        while self._running:
            time.sleep(10)
            self._flush_old_events()

    def _flush_old_events(self):
        current_time = time.time()
        events_to_flush = []
        
        with self.lock:
            keys_to_remove = []
            for key, data in self.events.items():
                if current_time - data['last_seen'] >= self.window_seconds:
                    events_to_flush.append((data['event'], data['count']))
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.events[key]
        
        for event, count in events_to_flush:
            if self.flush_callback:
                self.flush_callback(event, count)

    def stop(self):
        self._running = False
        if self.flush_thread:
            self.flush_thread.join(timeout=5)

    def clear(self):
        with self.lock:
            self.events.clear()
