import numpy as np
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from models import CircuitBreakerConfig, SimulationParams, MetricData
from circuit_breaker import CircuitBreaker


@dataclass
class SimulationEvent:
    timestamp: float
    event_type: str
    latency: float
    success: bool
    allowed: bool
    state: str
    retry_attempt: int = 0
    is_retry_storm: bool = False


@dataclass
class SimulationResult:
    events: List[SimulationEvent] = field(default_factory=list)
    metrics: List[MetricData] = field(default_factory=list)
    final_stats: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class SimulationEngine:
    def __init__(self, config: CircuitBreakerConfig, params: SimulationParams, 
                 endpoint: str = "api/test"):
        self.config = config
        self.params = params
        self.endpoint = endpoint
        self.circuit_breaker = CircuitBreaker(config, endpoint)
        self.rng = np.random.RandomState(42)
        self.retry_storm_active = False
        self.retry_storm_start_time = 0.0
        self.retry_storm_duration = 0.0
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0
    
    def _check_retry_storm(self, t: float, recent_error_rate: float) -> bool:
        if not self.params.retry_storm.enabled:
            return False
        
        threshold = self.params.retry_storm.retry_storm_trigger_threshold
        
        if not self.retry_storm_active and recent_error_rate >= threshold:
            self.retry_storm_active = True
            self.retry_storm_start_time = t
            return True
        
        if self.retry_storm_active and recent_error_rate < threshold * 0.5:
            self.retry_storm_active = False
            self.retry_storm_duration += (t - self.retry_storm_start_time)
        
        return self.retry_storm_active
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        rs = self.params.retry_storm
        base_delay = rs.retry_delay_base * (rs.retry_backoff_multiplier ** attempt)
        jitter = base_delay * rs.retry_jitter * (self.rng.rand() * 2 - 1)
        return max(0.001, base_delay + jitter)
    
    def _generate_traffic_rate(self, t: float) -> float:
        base_rate = 10.0 * self.params.traffic_multiplier
        
        if self.params.traffic_pattern == "steady":
            rate = base_rate
        elif self.params.traffic_pattern == "spike":
            spike_times = self.params.failure_spike_times or [100.0, 200.0]
            rate = base_rate
            for spike_t in spike_times:
                if abs(t - spike_t) < 20.0:
                    rate = base_rate * 3.0
                    break
        elif self.params.traffic_pattern == "periodic":
            rate = base_rate * (0.5 + 0.5 * np.sin(2 * np.pi * t / 60.0))
        else:
            rate = base_rate
        
        if self.params.retry_storm.enabled and self.retry_storm_active:
            rate *= self.params.retry_storm.retry_amplification_factor
        
        return rate
    
    def _generate_error_rate(self, t: float) -> float:
        base_error = self.params.base_error_rate
        
        spike_times = self.params.failure_spike_times or [100.0, 200.0]
        for spike_t in spike_times:
            if abs(t - spike_t) < 15.0:
                return 0.8
        
        return base_error
    
    def _generate_latency(self, t: float, error: bool, retry_attempt: int = 0) -> float:
        base_latency = self.params.base_latency
        
        if error:
            latency = base_latency * 2.0 + self.rng.exponential(base_latency)
        else:
            latency = base_latency * (0.5 + self.rng.rand())
        
        latency *= (1.0 + retry_attempt * 0.1)
        
        spike_times = self.params.failure_spike_times or [100.0, 200.0]
        for spike_t in spike_times:
            if abs(t - spike_t) < 30.0:
                latency *= 1.5
        
        return min(latency, self.config.timeout * 2)
    
    def _check_timeout(self, latency: float) -> bool:
        return latency > self.config.timeout
    
    def _execute_request(self, t: float, error_rate: float, retry_attempt: int = 0) -> Tuple[bool, float, str, bool]:
        is_error = self.rng.rand() < error_rate
        latency = self._generate_latency(t, is_error, retry_attempt)
        is_timeout = self._check_timeout(latency)
        success = not (is_error or is_timeout)
        
        event_type = "success" if success else ("timeout" if is_timeout else "error")
        if retry_attempt > 0:
            event_type = f"retry_{event_type}"
        
        return success, latency, event_type, is_error
    
    def run(self) -> SimulationResult:
        result = SimulationResult()
        t = 0.0
        metric_interval = 10.0
        next_metric_time = metric_interval
        
        window_events: List[SimulationEvent] = []
        recent_window_events: List[SimulationEvent] = []
        
        while t < self.params.duration:
            if len(recent_window_events) >= 50:
                recent_window_events = recent_window_events[-50:]
            recent_errors = sum(1 for e in recent_window_events if not e.success and e.allowed)
            recent_total = sum(1 for e in recent_window_events if e.allowed)
            recent_error_rate = recent_errors / recent_total if recent_total > 0 else 0.0
            
            self._check_retry_storm(t, recent_error_rate)
            
            rate = self._generate_traffic_rate(t)
            if rate <= 0:
                t += 0.1
                continue
            
            inter_arrival = self.rng.exponential(1.0 / rate)
            t += inter_arrival
            
            if t >= self.params.duration:
                break
            
            current_time = t
            error_rate = self._generate_error_rate(current_time)
            
            allowed = self.circuit_breaker.allow_request(current_time)
            
            if not allowed:
                event = SimulationEvent(
                    timestamp=current_time,
                    event_type="rejected",
                    latency=0.0,
                    success=False,
                    allowed=False,
                    state=self.circuit_breaker.state.value,
                    retry_attempt=0,
                    is_retry_storm=self.retry_storm_active
                )
                result.events.append(event)
                window_events.append(event)
                recent_window_events.append(event)
                
                if self.params.retry_storm.enabled and self.retry_storm_active:
                    for retry_attempt in range(1, self.params.retry_storm.max_retries + 1):
                        retry_delay = self._calculate_retry_delay(retry_attempt)
                        retry_time = current_time + retry_delay
                        
                        if retry_time >= self.params.duration:
                            break
                        
                        retry_allowed = self.circuit_breaker.allow_request(retry_time)
                        self.total_retries += 1
                        
                        if not retry_allowed:
                            retry_event = SimulationEvent(
                                timestamp=retry_time,
                                event_type="retry_rejected",
                                latency=0.0,
                                success=False,
                                allowed=False,
                                state=self.circuit_breaker.state.value,
                                retry_attempt=retry_attempt,
                                is_retry_storm=True
                            )
                            result.events.append(retry_event)
                            window_events.append(retry_event)
                            self.failed_retries += 1
                        else:
                            success, latency, event_type, _ = self._execute_request(
                                retry_time, error_rate, retry_attempt
                            )
                            self.circuit_breaker.record_result(success, latency, retry_time)
                            
                            retry_event = SimulationEvent(
                                timestamp=retry_time,
                                event_type=event_type,
                                latency=latency,
                                success=success,
                                allowed=True,
                                state=self.circuit_breaker.state.value,
                                retry_attempt=retry_attempt,
                                is_retry_storm=True
                            )
                            result.events.append(retry_event)
                            window_events.append(retry_event)
                            recent_window_events.append(retry_event)
                            
                            if success:
                                self.successful_retries += 1
                                break
                            else:
                                self.failed_retries += 1
                continue
            
            success, latency, event_type, _ = self._execute_request(current_time, error_rate, 0)
            self.circuit_breaker.record_result(success, latency, current_time)
            
            event = SimulationEvent(
                timestamp=current_time,
                event_type=event_type,
                latency=latency,
                success=success,
                allowed=True,
                state=self.circuit_breaker.state.value,
                retry_attempt=0,
                is_retry_storm=self.retry_storm_active
            )
            result.events.append(event)
            window_events.append(event)
            recent_window_events.append(event)
            
            if not success and self.params.retry_storm.enabled:
                for retry_attempt in range(1, self.params.retry_storm.max_retries + 1):
                    retry_delay = self._calculate_retry_delay(retry_attempt)
                    retry_time = current_time + retry_delay
                    
                    if retry_time >= self.params.duration:
                        break
                    
                    retry_allowed = self.circuit_breaker.allow_request(retry_time)
                    self.total_retries += 1
                    
                    if not retry_allowed:
                        retry_event = SimulationEvent(
                            timestamp=retry_time,
                            event_type="retry_rejected",
                            latency=0.0,
                            success=False,
                            allowed=False,
                            state=self.circuit_breaker.state.value,
                            retry_attempt=retry_attempt,
                            is_retry_storm=self.retry_storm_active
                        )
                        result.events.append(retry_event)
                        window_events.append(retry_event)
                        self.failed_retries += 1
                    else:
                        retry_success, retry_latency, retry_event_type, _ = self._execute_request(
                            retry_time, error_rate, retry_attempt
                        )
                        self.circuit_breaker.record_result(retry_success, retry_latency, retry_time)
                        
                        retry_event = SimulationEvent(
                            timestamp=retry_time,
                            event_type=retry_event_type,
                            latency=retry_latency,
                            success=retry_success,
                            allowed=True,
                            state=self.circuit_breaker.state.value,
                            retry_attempt=retry_attempt,
                            is_retry_storm=self.retry_storm_active
                        )
                        result.events.append(retry_event)
                        window_events.append(retry_event)
                        recent_window_events.append(retry_event)
                        
                        if retry_success:
                            self.successful_retries += 1
                            break
                        else:
                            self.failed_retries += 1
            
            if t >= next_metric_time:
                metric = self._calculate_metric(window_events, next_metric_time - metric_interval, 
                                               next_metric_time)
                result.metrics.append(metric)
                window_events = []
                next_metric_time += metric_interval
        
        if window_events:
            metric = self._calculate_metric(window_events, 
                                           next_metric_time - metric_interval,
                                           self.params.duration)
            result.metrics.append(metric)
        
        if self.retry_storm_active:
            self.retry_storm_duration += (self.params.duration - self.retry_storm_start_time)
        
        result.final_stats = self._calculate_final_stats(result)
        result.score = self._calculate_score(result.final_stats)
        
        return result
    
    def _calculate_metric(self, events: List[SimulationEvent], 
                         start: float, end: float) -> MetricData:
        if not events:
            return MetricData(
                endpoint=self.endpoint,
                throughput=0.0,
                error_rate=0.0,
                avg_latency=0.0
            )
        
        total = len(events)
        successes = sum(1 for e in events if e.success)
        failures = total - successes
        latencies = [e.latency for e in events if e.allowed]
        
        if latencies:
            avg_lat = np.mean(latencies)
            p50 = np.percentile(latencies, 50)
            p95 = np.percentile(latencies, 95)
            p99 = np.percentile(latencies, 99)
        else:
            avg_lat = p50 = p95 = p99 = 0.0
        
        duration = end - start
        throughput = total / duration if duration > 0 else 0.0
        error_rate = failures / total if total > 0 else 0.0
        
        return MetricData(
            endpoint=self.endpoint,
            success_count=successes,
            failure_count=failures,
            total_requests=total,
            avg_latency=avg_lat,
            p50_latency=p50,
            p95_latency=p95,
            p99_latency=p99,
            error_rate=error_rate,
            throughput=throughput
        )
    
    def _calculate_final_stats(self, result: SimulationResult) -> Dict[str, Any]:
        events = result.events
        cb_metrics = self.circuit_breaker.get_metrics()
        
        if not events:
            return {**cb_metrics, "score": 0.0}
        
        total = len(events)
        successes = sum(1 for e in events if e.success)
        failures = total - successes
        rejected = sum(1 for e in events if not e.allowed)
        latencies = [e.latency for e in events if e.allowed and e.latency > 0]
        
        retry_events = [e for e in events if e.retry_attempt > 0]
        retry_successes = sum(1 for e in retry_events if e.success)
        retry_failures = len(retry_events) - retry_successes
        retry_storm_events = [e for e in events if e.is_retry_storm]
        
        recovery_times = []
        last_open_time = None
        for i, event in enumerate(events):
            if event.state == "OPEN" and last_open_time is None:
                last_open_time = event.timestamp
            elif event.state == "CLOSED" and last_open_time is not None:
                recovery_times.append(event.timestamp - last_open_time)
                last_open_time = None
        
        if last_open_time is not None:
            recovery_times.append(self.params.duration - last_open_time)
        
        state_changes = sum(
            1 for i in range(1, len(events)) 
            if events[i].state != events[i-1].state
        )
        
        open_time = sum(
            events[i+1].timestamp - events[i].timestamp
            for i in range(len(events) - 1)
            if events[i].state == "OPEN"
        )
        open_ratio = open_time / self.params.duration if self.params.duration > 0 else 0.0
        
        error_rate = failures / total if total > 0 else 0.0
        success_rate = successes / total if total > 0 else 0.0
        reject_rate = rejected / total if total > 0 else 0.0
        
        original_requests = sum(1 for e in events if e.retry_attempt == 0)
        retry_rate = (total - original_requests) / original_requests if original_requests > 0 else 0.0
        
        avg_lat = np.mean(latencies) if latencies else 0.0
        p95_lat = np.percentile(latencies, 95) if latencies else 0.0
        
        effective_successes = sum(1 for e in events if e.success and e.retry_attempt == 0)
        effective_throughput = effective_successes / self.params.duration
        
        return {
            **cb_metrics,
            "total_requests": total,
            "original_requests": original_requests,
            "successful_requests": successes,
            "failed_requests": failures,
            "rejected_requests": rejected,
            "error_rate": error_rate,
            "success_rate": success_rate,
            "reject_rate": reject_rate,
            "avg_latency": avg_lat,
            "p95_latency": p95_lat,
            "state_changes": state_changes,
            "open_ratio": open_ratio,
            "effective_throughput": effective_throughput,
            "simulation_duration": self.params.duration,
            "retry_storm_enabled": self.params.retry_storm.enabled,
            "retry_storm_duration": self.retry_storm_duration,
            "retry_storm_ratio": self.retry_storm_duration / self.params.duration if self.params.duration > 0 else 0.0,
            "total_retries": self.total_retries,
            "successful_retries": self.successful_retries,
            "failed_retries": self.failed_retries,
            "retry_success_rate": self.successful_retries / self.total_retries if self.total_retries > 0 else 0.0,
            "retry_rate": retry_rate,
            "recovery_times": recovery_times,
            "avg_recovery_time": np.mean(recovery_times) if recovery_times else 0.0,
            "max_recovery_time": max(recovery_times) if recovery_times else 0.0,
            "retry_storm_event_count": len(retry_storm_events),
            "retry_storm_traffic_amplification": len(events) / original_requests if original_requests > 0 else 1.0
        }
    
    def _calculate_score(self, stats: Dict[str, Any]) -> float:
        success_rate = stats.get("success_rate", 0.0)
        reject_rate = stats.get("reject_rate", 0.0)
        avg_latency = stats.get("avg_latency", 0.0)
        p95_latency = stats.get("p95_latency", 0.0)
        state_changes = stats.get("state_changes", 0)
        open_ratio = stats.get("open_ratio", 0.0)
        effective_throughput = stats.get("effective_throughput", 0.0)
        avg_recovery_time = stats.get("avg_recovery_time", 0.0)
        retry_success_rate = stats.get("retry_success_rate", 0.0)
        retry_storm_ratio = stats.get("retry_storm_ratio", 0.0)
        
        w_success = 0.25
        w_reject = 0.15
        w_latency = 0.15
        w_stability = 0.15
        w_throughput = 0.10
        w_recovery = 0.10
        w_retry = 0.10
        
        norm_latency = max(0.0, 1.0 - avg_latency / self.config.timeout)
        norm_p95 = max(0.0, 1.0 - p95_latency / (self.config.timeout * 1.5))
        latency_score = 0.6 * norm_latency + 0.4 * norm_p95
        
        max_changes = 20.0
        stability_score = max(0.0, 1.0 - state_changes / max_changes)
        stability_score = 0.7 * stability_score + 0.3 * (1.0 - open_ratio)
        
        max_throughput = 50.0
        throughput_score = min(1.0, effective_throughput / max_throughput)
        
        max_recovery_time = 120.0
        recovery_score = max(0.0, 1.0 - avg_recovery_time / max_recovery_time)
        
        retry_score = retry_success_rate
        
        score = (
            w_success * success_rate +
            w_reject * (1.0 - reject_rate) +
            w_latency * latency_score +
            w_stability * stability_score +
            w_throughput * throughput_score +
            w_recovery * recovery_score +
            w_retry * retry_score
        )
        
        penalty = 0.0
        if reject_rate > 0.5:
            penalty += (reject_rate - 0.5) * 0.5
        if open_ratio > 0.3:
            penalty += (open_ratio - 0.3) * 0.3
        if state_changes > 10:
            penalty += (state_changes - 10) * 0.01
        if avg_recovery_time > 60.0:
            penalty += (avg_recovery_time - 60.0) * 0.005
        if retry_storm_ratio > 0.5:
            penalty += (retry_storm_ratio - 0.5) * 0.2
        
        return max(0.0, score - penalty)


def run_simulation(config: CircuitBreakerConfig, 
                   params: SimulationParams,
                   endpoint: str = "api/test") -> SimulationResult:
    engine = SimulationEngine(config, params, endpoint)
    return engine.run()
