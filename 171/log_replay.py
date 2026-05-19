import time
import threading
import queue
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from collections import defaultdict


class ReplaySession:
    def __init__(self, session_id: str, logs: List[Dict[str, Any]], speed: float = 1.0):
        self.id = session_id
        self.logs = sorted(logs, key=lambda x: x['timestamp'])
        self.speed = max(0.1, min(speed, 10.0))
        self.status = 'ready'  # ready, running, paused, stopped, completed
        self.current_index = 0
        self.replayed_count = 0
        self.start_time = None
        self.pause_time = None
        self.total_duration = 0
        self.elapsed_time = 0
        self.event_queue = queue.Queue()
        self.callbacks = {
            'on_log': None,
            'on_complete': None,
            'on_status_change': None
        }
        
        if self.logs:
            self.start_log_time = self.logs[0]['timestamp']
            self.end_log_time = self.logs[-1]['timestamp']
            self.total_duration = (self.end_log_time - self.start_log_time).total_seconds()
        else:
            self.start_log_time = None
            self.end_log_time = None
            self.total_duration = 0

    def set_callback(self, event: str, callback: Callable):
        if event in self.callbacks:
            self.callbacks[event] = callback

    def _notify(self, event: str, *args, **kwargs):
        if self.callbacks.get(event):
            try:
                self.callbacks[event](*args, **kwargs)
            except Exception as e:
                print(f"Error in {event} callback: {e}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'status': self.status,
            'speed': self.speed,
            'current_index': self.current_index,
            'replayed_count': self.replayed_count,
            'total_count': len(self.logs),
            'progress': (self.current_index / len(self.logs) * 100) if self.logs else 0,
            'total_duration': self.total_duration,
            'elapsed_time': self.elapsed_time,
            'start_log_time': self.start_log_time.isoformat() if self.start_log_time else None,
            'end_log_time': self.end_log_time.isoformat() if self.end_log_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None
        }


class LogReplayEngine:
    def __init__(self, config, log_parser):
        self.config = config
        self.log_parser = log_parser
        self.enabled = config.ENABLE_LOG_REPLAY
        self.max_speed = config.LOG_REPLAY_MAX_SPEED
        self.default_speed = config.LOG_REPLAY_DEFAULT_SPEED
        
        self.sessions: Dict[str, ReplaySession] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def create_session(self, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None,
                      keyword: Optional[str] = None,
                      speed: Optional[float] = None,
                      log_type: str = 'access') -> Optional[ReplaySession]:
        if not self.enabled:
            return None

        if log_type == 'access':
            logs = self.log_parser.filter_logs(
                self.log_parser.access_logs,
                start_time=start_time,
                end_time=end_time,
                keyword=keyword
            )
        elif log_type == 'error':
            logs = self.log_parser.filter_logs(
                self.log_parser.error_logs,
                start_time=start_time,
                end_time=end_time,
                keyword=keyword
            )
        else:
            access_logs = self.log_parser.filter_logs(
                self.log_parser.access_logs,
                start_time=start_time,
                end_time=end_time,
                keyword=keyword
            )
            error_logs = self.log_parser.filter_logs(
                self.log_parser.error_logs,
                start_time=start_time,
                end_time=end_time,
                keyword=keyword
            )
            logs = access_logs + error_logs

        if not logs:
            return None

        session_id = f"replay_{int(time.time() * 1000)}"
        session = ReplaySession(
            session_id,
            logs,
            speed if speed else self.default_speed
        )
        
        with self._lock:
            self.sessions[session_id] = session
        
        return session

    def start_session(self, session_id: str) -> bool:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or session.status in ('running', 'completed', 'stopped'):
                return False

            stop_event = threading.Event()
            self._stop_events[session_id] = stop_event

            session.status = 'running'
            session.start_time = datetime.now()
            if session.pause_time:
                session.elapsed_time += (session.pause_time - session.start_time).total_seconds()
            session.pause_time = None

            thread = threading.Thread(
                target=self._replay_worker,
                args=(session, stop_event),
                daemon=True
            )
            self._threads[session_id] = thread
            thread.start()

            session._notify('on_status_change', 'running')
            return True

    def _replay_worker(self, session: ReplaySession, stop_event: threading.Event):
        if not session.logs:
            session.status = 'completed'
            session._notify('on_status_change', 'completed')
            session._notify('on_complete')
            return

        base_time = session.logs[0]['timestamp']
        start_real_time = time.time()

        while session.current_index < len(session.logs):
            if stop_event.is_set():
                break

            current_log = session.logs[session.current_index]
            log_offset = (current_log['timestamp'] - base_time).total_seconds()
            target_real_time = start_real_time + (log_offset / session.speed)

            wait_time = target_real_time - time.time()
            if wait_time > 0:
                if stop_event.wait(wait_time):
                    break

            if stop_event.is_set():
                break

            session._notify('on_log', current_log, session.current_index)
            session.current_index += 1
            session.replayed_count += 1
            session.elapsed_time = time.time() - start_real_time

        if session.current_index >= len(session.logs):
            session.status = 'completed'
            session._notify('on_status_change', 'completed')
            session._notify('on_complete')

    def pause_session(self, session_id: str) -> bool:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or session.status != 'running':
                return False

            if session_id in self._stop_events:
                self._stop_events[session_id].set()
            
            if session_id in self._threads:
                self._threads[session_id].join(timeout=2)
                del self._threads[session_id]
                del self._stop_events[session_id]

            session.status = 'paused'
            session.pause_time = datetime.now()
            session._notify('on_status_change', 'paused')
            return True

    def resume_session(self, session_id: str) -> bool:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or session.status != 'paused':
                return False
        return self.start_session(session_id)

    def stop_session(self, session_id: str) -> bool:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or session.status in ('stopped', 'completed'):
                return False

            if session_id in self._stop_events:
                self._stop_events[session_id].set()
            
            if session_id in self._threads:
                self._threads[session_id].join(timeout=2)
                del self._threads[session_id]
                del self._stop_events[session_id]

            session.status = 'stopped'
            session._notify('on_status_change', 'stopped')
            return True

    def set_speed(self, session_id: str, speed: float) -> bool:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            speed = max(0.1, min(speed, self.max_speed))
            session.speed = speed
            return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.sessions.get(session_id)
            return session.to_dict() if session else None

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [s.to_dict() for s in self.sessions.values()]

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self.sessions:
                return False

            if session_id in self._stop_events:
                self._stop_events[session_id].set()
            
            if session_id in self._threads:
                self._threads[session_id].join(timeout=2)
                del self._threads[session_id]
                del self._stop_events[session_id]

            del self.sessions[session_id]
            return True

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        with self._lock:
            now = datetime.now()
            expired = []
            for sid, session in self.sessions.items():
                if session.status in ('completed', 'stopped') and session.start_time:
                    age = (now - session.start_time).total_seconds() / 3600
                    if age > max_age_hours:
                        expired.append(sid)
            
            for sid in expired:
                self.delete_session(sid)

    def get_available_time_ranges(self) -> Dict[str, Any]:
        ranges = {}
        
        access_logs = list(self.log_parser.access_logs)
        if access_logs:
            access_sorted = sorted(access_logs, key=lambda x: x['timestamp'])
            ranges['access'] = {
                'min': access_sorted[0]['timestamp'].isoformat(),
                'max': access_sorted[-1]['timestamp'].isoformat(),
                'count': len(access_logs)
            }
        
        error_logs = list(self.log_parser.error_logs)
        if error_logs:
            error_sorted = sorted(error_logs, key=lambda x: x['timestamp'])
            ranges['error'] = {
                'min': error_sorted[0]['timestamp'].isoformat(),
                'max': error_sorted[-1]['timestamp'].isoformat(),
                'count': len(error_logs)
            }
        
        return ranges

    def shutdown(self):
        with self._lock:
            for sid in list(self.sessions.keys()):
                self.stop_session(sid)
        print("Log replay engine shutdown complete")
