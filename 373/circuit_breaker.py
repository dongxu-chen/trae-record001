import time
import threading
from collections import deque
from typing import Deque, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from models import CircuitState, CircuitBreakerConfig


@dataclass
class RequestRecord:
    timestamp: float
    success: bool
    latency: float


@dataclass
class CircuitBreakerStats:
    state: CircuitState
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    total_latency: float = 0.0
    state_transitions: int = 0
    current_window_requests: int = 0
    current_window_failures: int = 0


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig, endpoint: str = "default"):
        self.config = config
        self.endpoint = endpoint
        self.state = CircuitState.CLOSED
        self.state_changed_at = time.time()
        
        self._requests: Deque[RequestRecord] = deque()
        self._lock = threading.RLock()
        
        self.stats = CircuitBreakerStats(state=self.state)
        self._half_open_attempts = 0
        self._half_open_successes = 0
        self._open_until = 0.0
    
    def _cleanup_old_requests(self, current_time: float):
        cutoff = current_time - self.config.half_open_window
        while self._requests and self._requests[0].timestamp < cutoff:
            self._requests.popleft()
    
    def _calculate_metrics(self, current_time: float) -> Tuple[int, int, float]:
        self._cleanup_old_requests(current_time)
        window_requests = len(self._requests)
        window_failures = sum(1 for r in self._requests if not r.success)
        error_rate = window_failures / window_requests if window_requests > 0 else 0.0
        return window_requests, window_failures, error_rate
    
    def _check_state_transition(self, current_time: float):
        window_requests, window_failures, error_rate = self._calculate_metrics(current_time)
        
        self.stats.current_window_requests = window_requests
        self.stats.current_window_failures = window_failures
        
        if self.state == CircuitState.CLOSED:
            if (window_requests >= self.config.min_requests and 
                error_rate >= self.config.failure_threshold):
                self._transition_to_open(current_time)
        
        elif self.state == CircuitState.OPEN:
            if current_time >= self._open_until:
                self._transition_to_half_open(current_time)
        
        elif self.state == CircuitState.HALF_OPEN:
            if self._half_open_attempts > 0:
                half_open_error_rate = (
                    (self._half_open_attempts - self._half_open_successes) / 
                    self._half_open_attempts
                )
                if half_open_error_rate >= self.config.failure_threshold:
                    self._transition_to_open(current_time)
                elif (self._half_open_attempts >= self.config.min_requests and 
                      half_open_error_rate < self.config.failure_threshold * 0.5):
                    self._transition_to_closed(current_time)
    
    def _transition_to_open(self, current_time: float):
        with self._lock:
            self.state = CircuitState.OPEN
            self.state_changed_at = current_time
            self._open_until = current_time + self.config.open_duration
            self.stats.state = self.state
            self.stats.state_transitions += 1
            self._half_open_attempts = 0
            self._half_open_successes = 0
    
    def _transition_to_half_open(self, current_time: float):
        with self._lock:
            self.state = CircuitState.HALF_OPEN
            self.state_changed_at = current_time
            self.stats.state = self.state
            self.stats.state_transitions += 1
            self._half_open_attempts = 0
            self._half_open_successes = 0
    
    def _transition_to_closed(self, current_time: float):
        with self._lock:
            self.state = CircuitState.CLOSED
            self.state_changed_at = current_time
            self.stats.state = self.state
            self.stats.state_transitions += 1
            self._half_open_attempts = 0
            self._half_open_successes = 0
    
    def allow_request(self, current_time: Optional[float] = None) -> bool:
        with self._lock:
            now = current_time if current_time is not None else time.time()
            self._check_state_transition(now)
            
            if self.state == CircuitState.OPEN:
                self.stats.rejected_requests += 1
                return False
            return True
    
    def record_result(self, success: bool, latency: float, current_time: Optional[float] = None):
        with self._lock:
            now = current_time if current_time is not None else time.time()
            
            self._requests.append(RequestRecord(
                timestamp=now,
                success=success,
                latency=latency
            ))
            
            self.stats.total_requests += 1
            if success:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1
            self.stats.total_latency += latency
            
            if self.state == CircuitState.HALF_OPEN:
                self._half_open_attempts += 1
                if success:
                    self._half_open_successes += 1
            
            self._check_state_transition(now)
    
    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            window_requests, window_failures, error_rate = self._calculate_metrics(now)
            
            avg_latency = (
                self.stats.total_latency / self.stats.total_requests 
                if self.stats.total_requests > 0 else 0.0
            )
            
            return {
                "endpoint": self.endpoint,
                "state": self.state.value,
                "state_duration": now - self.state_changed_at,
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "rejected_requests": self.stats.rejected_requests,
                "overall_success_rate": (
                    self.stats.successful_requests / self.stats.total_requests 
                    if self.stats.total_requests > 0 else 0.0
                ),
                "overall_error_rate": (
                    self.stats.failed_requests / self.stats.total_requests 
                    if self.stats.total_requests > 0 else 0.0
                ),
                "window_requests": window_requests,
                "window_error_rate": error_rate,
                "avg_latency": avg_latency,
                "state_transitions": self.stats.state_transitions,
                "config": self.config.model_dump()
            }
    
    def reset(self):
        with self._lock:
            self.state = CircuitState.CLOSED
            self.state_changed_at = time.time()
            self._requests.clear()
            self.stats = CircuitBreakerStats(state=self.state)
            self._half_open_attempts = 0
            self._half_open_successes = 0
            self._open_until = 0.0
