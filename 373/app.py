from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import uuid
import time
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from models import (
    MetricData, 
    CircuitBreakerConfig, 
    SimulationParams, 
    OptimizationResult,
    CircuitState,
    ConfigPushResult,
    FaultInjectionParams,
    FaultInjectionResult,
    CircuitBreakerEvent,
    FalseTripAnalysis,
    EventAnalysisResult,
    ConfigHistory
)
from simulation_engine import run_simulation, SimulationEngine, SimulationResult
from bayesian_optimizer import (
    optimize_circuit_breaker, 
    BayesianOptimizer, 
    OptimizationParams,
    ParameterBounds,
    PARAMETER_EXPLANATIONS,
    RETRY_PARAMETER_EXPLANATIONS
)
from circuit_breaker import CircuitBreaker


app = Flask(__name__)
CORS(app)


@dataclass
class OptimizationTask:
    task_id: str
    status: str
    result: Optional[OptimizationResult] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class MetricsStore:
    def __init__(self):
        self._metrics: Dict[str, List[MetricData]] = {}
        self._lock = threading.RLock()
    
    def add_metric(self, metric: MetricData):
        with self._lock:
            endpoint = metric.endpoint
            if endpoint not in self._metrics:
                self._metrics[endpoint] = []
            self._metrics[endpoint].append(metric)
            if len(self._metrics[endpoint]) > 10000:
                self._metrics[endpoint] = self._metrics[endpoint][-10000:]
    
    def get_metrics(self, endpoint: Optional[str] = None, 
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[MetricData]:
        with self._lock:
            if endpoint and endpoint in self._metrics:
                metrics = self._metrics[endpoint]
            else:
                metrics = []
                for ep_metrics in self._metrics.values():
                    metrics.extend(ep_metrics)
            
            if start_time:
                metrics = [m for m in metrics if m.timestamp >= start_time]
            if end_time:
                metrics = [m for m in metrics if m.timestamp <= end_time]
            
            return sorted(metrics, key=lambda m: m.timestamp)
    
    def get_endpoints(self) -> List[str]:
        with self._lock:
            return list(self._metrics.keys())
    
    def get_aggregated_metrics(self, endpoint: str) -> Dict[str, Any]:
        with self._lock:
            if endpoint not in self._metrics or not self._metrics[endpoint]:
                return {}
            
            metrics = self._metrics[endpoint]
            total_requests = sum(m.total_requests for m in metrics)
            total_success = sum(m.success_count for m in metrics)
            total_failures = sum(m.failure_count for m in metrics)
            
            return {
                "endpoint": endpoint,
                "total_requests": total_requests,
                "total_success": total_success,
                "total_failures": total_failures,
                "overall_error_rate": total_failures / total_requests if total_requests > 0 else 0,
                "avg_latency": np.mean([m.avg_latency for m in metrics]),
                "avg_throughput": np.mean([m.throughput for m in metrics]),
                "p95_latency": np.mean([m.p95_latency for m in metrics]),
                "metric_count": len(metrics)
            }


metrics_store = MetricsStore()
optimization_tasks: Dict[str, OptimizationTask] = {}
circuit_breakers: Dict[str, CircuitBreaker] = {}


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "endpoints": metrics_store.get_endpoints(),
        "active_optimizations": len([t for t in optimization_tasks.values() if t.status == "running"])
    })


@app.route('/api/metrics', methods=['POST'])
def ingest_metrics():
    try:
        data = request.get_json()
        if isinstance(data, list):
            for item in data:
                metric = MetricData(**item)
                metrics_store.add_metric(metric)
        else:
            metric = MetricData(**data)
            metrics_store.add_metric(metric)
        
        return jsonify({
            "status": "success",
            "message": "Metrics ingested successfully",
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    endpoint = request.args.get('endpoint')
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    start_time = datetime.fromisoformat(start_time_str) if start_time_str else None
    end_time = datetime.fromisoformat(end_time_str) if end_time_str else None
    
    metrics = metrics_store.get_metrics(endpoint, start_time, end_time)
    
    return jsonify({
        "count": len(metrics),
        "metrics": [m.model_dump() for m in metrics]
    })


@app.route('/api/metrics/aggregate', methods=['GET'])
def get_aggregated_metrics():
    endpoint = request.args.get('endpoint')
    if not endpoint:
        endpoints = metrics_store.get_endpoints()
        return jsonify({
            "endpoints": [metrics_store.get_aggregated_metrics(ep) for ep in endpoints]
        })
    
    agg = metrics_store.get_aggregated_metrics(endpoint)
    return jsonify(agg)


@app.route('/api/simulate', methods=['POST'])
def simulate():
    try:
        data = request.get_json()
        
        config_data = data.get('config', {})
        params_data = data.get('params', {})
        endpoint = data.get('endpoint', 'api/test')
        
        config = CircuitBreakerConfig(**config_data)
        params = SimulationParams(**params_data)
        
        sim_result = run_simulation(config, params, endpoint)
        
        return jsonify({
            "status": "success",
            "score": sim_result.score,
            "final_stats": sim_result.final_stats,
            "metrics_count": len(sim_result.metrics),
            "events_count": len(sim_result.events),
            "metrics": [m.model_dump() for m in sim_result.metrics[:100]]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/optimize', methods=['POST'])
def start_optimization():
    try:
        data = request.get_json()
        
        params_data = data.get('simulation_params', {})
        opt_params_data = data.get('optimization_params', {})
        bounds_data = data.get('parameter_bounds', {})
        endpoint = data.get('endpoint', 'api/test')
        
        simulation_params = SimulationParams(**params_data)
        optimization_params = OptimizationParams(**opt_params_data) if opt_params_data else None
        
        parameter_bounds = None
        if bounds_data:
            parameter_bounds = ParameterBounds(**bounds_data)
        
        task_id = str(uuid.uuid4())
        task = OptimizationTask(task_id=task_id, status="running")
        optimization_tasks[task_id] = task
        
        def run_optimization():
            try:
                result = optimize_circuit_breaker(
                    simulation_params=simulation_params,
                    optimization_params=optimization_params,
                    parameter_bounds=parameter_bounds,
                    endpoint=endpoint
                )
                task.result = result
                task.status = "completed"
                task.completed_at = datetime.now()
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.completed_at = datetime.now()
        
        thread = threading.Thread(target=run_optimization, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "success",
            "task_id": task_id,
            "message": "Optimization started"
        }), 202
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/optimize/<task_id>', methods=['GET'])
def get_optimization_result(task_id: str):
    task = optimization_tasks.get(task_id)
    if not task:
        return jsonify({
            "status": "error",
            "message": "Task not found"
        }), 404
    
    if task.status == "running":
        return jsonify({
            "task_id": task_id,
            "status": "running",
            "created_at": task.created_at.isoformat(),
            "message": "Optimization in progress"
        })
    
    if task.status == "failed":
        return jsonify({
            "task_id": task_id,
            "status": "failed",
            "error": task.error,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        })
    
    result = task.result
    return jsonify({
        "task_id": task_id,
        "status": "completed",
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "best_config": result.best_config.model_dump(),
        "best_score": result.best_score,
        "metrics_summary": result.metrics_summary,
        "optimization_history": result.optimization_history,
        "all_results_count": len(result.all_results),
        "parameter_explanations": result.parameter_explanations
    })


@app.route('/api/optimize/<task_id>/history', methods=['GET'])
def get_optimization_history(task_id: str):
    task = optimization_tasks.get(task_id)
    if not task:
        return jsonify({
            "status": "error",
            "message": "Task not found"
        }), 404
    
    if not task.result:
        return jsonify({
            "task_id": task_id,
            "status": task.status,
            "history": []
        })
    
    return jsonify({
        "task_id": task_id,
        "status": task.status,
        "history": task.result.optimization_history
    })


@app.route('/api/optimize/tasks', methods=['GET'])
def list_optimization_tasks():
    tasks_list = []
    for task_id, task in optimization_tasks.items():
        task_info = {
            "task_id": task_id,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "best_score": task.result.best_score if task.result else None
        }
        tasks_list.append(task_info)
    
    return jsonify({
        "count": len(tasks_list),
        "tasks": tasks_list
    })


@app.route('/api/circuit-breaker/<path:endpoint>', methods=['POST'])
def create_circuit_breaker(endpoint: str):
    try:
        data = request.get_json() or {}
        config = CircuitBreakerConfig(**data)
        
        cb = CircuitBreaker(config, endpoint)
        circuit_breakers[endpoint] = cb
        
        return jsonify({
            "status": "success",
            "endpoint": endpoint,
            "config": config.model_dump()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/circuit-breaker/<path:endpoint>/allow', methods=['GET'])
def allow_request(endpoint: str):
    cb = circuit_breakers.get(endpoint)
    if not cb:
        return jsonify({
            "status": "error",
            "message": "Circuit breaker not found"
        }), 404
    
    allowed = cb.allow_request()
    return jsonify({
        "endpoint": endpoint,
        "allowed": allowed,
        "state": cb.state.value
    })


@app.route('/api/circuit-breaker/<path:endpoint>/record', methods=['POST'])
def record_request(endpoint: str):
    try:
        cb = circuit_breakers.get(endpoint)
        if not cb:
            return jsonify({
                "status": "error",
                "message": "Circuit breaker not found"
            }), 404
        
        data = request.get_json()
        success = data.get('success', True)
        latency = data.get('latency', 0.0)
        
        cb.record_result(success, latency)
        
        return jsonify({
            "status": "success",
            "metrics": cb.get_metrics()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/circuit-breaker/<path:endpoint>', methods=['GET'])
def get_circuit_breaker(endpoint: str):
    cb = circuit_breakers.get(endpoint)
    if not cb:
        return jsonify({
            "status": "error",
            "message": "Circuit breaker not found"
        }), 404
    
    return jsonify({
        "endpoint": endpoint,
        "metrics": cb.get_metrics()
    })


@app.route('/api/circuit-breaker/<path:endpoint>/reset', methods=['POST'])
def reset_circuit_breaker(endpoint: str):
    cb = circuit_breakers.get(endpoint)
    if not cb:
        return jsonify({
            "status": "error",
            "message": "Circuit breaker not found"
        }), 404
    
    cb.reset()
    return jsonify({
        "status": "success",
        "message": "Circuit breaker reset",
        "metrics": cb.get_metrics()
    })


@app.route('/api/circuit-breaker', methods=['GET'])
def list_circuit_breakers():
    return jsonify({
        "endpoints": list(circuit_breakers.keys()),
        "count": len(circuit_breakers)
    })


@app.route('/api/recommend', methods=['POST'])
def recommend_config():
    try:
        data = request.get_json()
        endpoint = data.get('endpoint', 'api/test')
        
        agg_metrics = metrics_store.get_aggregated_metrics(endpoint)
        
        base_error_rate = agg_metrics.get('overall_error_rate', 0.05)
        base_latency = agg_metrics.get('avg_latency', 0.2)
        
        simulation_params = SimulationParams(
            duration=300.0,
            base_error_rate=max(0.01, min(base_error_rate, 0.8)),
            base_latency=max(0.05, min(base_latency, 2.0)),
            traffic_pattern="spike",
            failure_spike_times=[100.0, 200.0]
        )
        
        optimization_params = OptimizationParams(
            n_calls=20,
            n_random_starts=5,
            verbose=False
        )
        
        task_id = str(uuid.uuid4())
        task = OptimizationTask(task_id=task_id, status="running")
        optimization_tasks[task_id] = task
        
        def run_recommendation():
            try:
                result = optimize_circuit_breaker(
                    simulation_params=simulation_params,
                    optimization_params=optimization_params,
                    endpoint=endpoint
                )
                task.result = result
                task.status = "completed"
                task.completed_at = datetime.now()
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.completed_at = datetime.now()
        
        thread = threading.Thread(target=run_recommendation, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "success",
            "task_id": task_id,
            "message": "Recommendation optimization started",
            "observed_metrics": {
                "error_rate": base_error_rate,
                "avg_latency": base_latency
            }
        }), 202
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/parameter-explanations', methods=['GET'])
def get_parameter_explanations():
    return jsonify({
        "status": "success",
        "circuit_breaker_params": PARAMETER_EXPLANATIONS,
        "retry_storm_params": RETRY_PARAMETER_EXPLANATIONS,
        "optimization_params": {
            "n_calls": {
                "name": "贝叶斯优化迭代次数",
                "description": "贝叶斯优化的总迭代次数，次数越多找到最优解的概率越高，但计算时间越长",
                "recommended_range": "30 - 100",
                "default": 50,
                "impact": "次数太少可能收敛到局部最优；次数太多计算成本过高"
            },
            "n_random_starts": {
                "name": "随机探索次数",
                "description": "初始随机采样的次数，用于探索参数空间，避免过早陷入局部最优",
                "recommended_range": "10 - 30",
                "default": 15,
                "impact": "随机探索比例建议占总迭代的20%-30%，平衡探索与利用"
            },
            "acq_func": {
                "name": "采集函数",
                "description": "贝叶斯优化中用于选择下一个采样点的策略",
                "recommended_range": "EI, PI, LCB",
                "default": "EI",
                "impact": "EI(期望改进)平衡探索和利用；PI(概率改进)更保守；LCB(置信下界)更偏向探索"
            }
        }
    })


@app.route('/api/compare', methods=['POST'])
def compare_configs():
    try:
        data = request.get_json()
        configs_data = data.get('configs', [])
        params_data = data.get('params', {})
        endpoint = data.get('endpoint', 'api/test')
        
        if len(configs_data) < 2:
            return jsonify({
                "status": "error",
                "message": "At least 2 configurations required for comparison"
            }), 400
        
        params = SimulationParams(**params_data)
        results = []
        
        for config_data in configs_data:
            config = CircuitBreakerConfig(**config_data)
            sim_result = run_simulation(config, params, endpoint)
            results.append({
                "config": config.model_dump(),
                "score": sim_result.score,
                "stats": sim_result.final_stats
            })
        
        results.sort(key=lambda r: r['score'], reverse=True)
        
        return jsonify({
            "status": "success",
            "count": len(results),
            "best_config": results[0]['config'],
            "best_score": results[0]['score'],
            "comparison": results
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


class ConfigPushManager:
    def __init__(self):
        self._config_history: Dict[str, ConfigHistory] = {}
        self._current_version: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def push_config(self, endpoint: str, new_config: CircuitBreakerConfig) -> ConfigPushResult:
        with self._lock:
            old_config_dict = None
            if endpoint in circuit_breakers:
                old_cb = circuit_breakers[endpoint]
                old_config_dict = old_cb.config.model_dump()
            
            cb = CircuitBreaker(new_config, endpoint)
            circuit_breakers[endpoint] = cb
            
            version = f"v{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            if endpoint not in self._config_history:
                self._config_history[endpoint] = ConfigHistory(endpoint=endpoint)
            
            self._config_history[endpoint].configs.append(new_config.model_dump())
            self._config_history[endpoint].timestamps.append(datetime.now())
            self._config_history[endpoint].versions.append(version)
            self._current_version[endpoint] = version
            
            return ConfigPushResult(
                status="success",
                endpoint=endpoint,
                old_config=old_config_dict,
                new_config=new_config.model_dump(),
                pushed_at=datetime.now(),
                version=version
            )
    
    def get_config_history(self, endpoint: str) -> Optional[ConfigHistory]:
        with self._lock:
            return self._config_history.get(endpoint)
    
    def get_current_version(self, endpoint: str) -> str:
        with self._lock:
            return self._current_version.get(endpoint, "unknown")
    
    def rollback(self, endpoint: str, version: str) -> Optional[ConfigPushResult]:
        with self._lock:
            history = self._config_history.get(endpoint)
            if not history:
                return None
            
            if version not in history.versions:
                return None
            
            idx = history.versions.index(version)
            config_data = history.configs[idx]
            new_config = CircuitBreakerConfig(**config_data)
            
            return self.push_config(endpoint, new_config)


class FaultInjectionManager:
    def __init__(self):
        self._injection_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def inject_fault(self, params: FaultInjectionParams) -> FaultInjectionResult:
        task_id = str(uuid.uuid4())
        
        result = FaultInjectionResult(
            status="running",
            task_id=task_id,
            endpoint=params.endpoint,
            injection_type=params.injection_type,
            intensity=params.intensity,
            duration=params.duration
        )
        
        with self._lock:
            self._injection_tasks[task_id] = {
                "status": "running",
                "params": params,
                "result": result
            }
        
        def run_injection():
            try:
                cb = circuit_breakers.get(params.endpoint)
                if not cb:
                    cb = CircuitBreaker(CircuitBreakerConfig(), params.endpoint)
                    circuit_breakers[params.endpoint] = cb
                
                events_before = []
                events_during = []
                events_after = []
                
                t = 0.0
                current_time = time.time()
                
                start_time = current_time + params.start_delay
                end_time = start_time + params.duration
                
                while t < params.start_delay + params.duration + 10.0:
                    current_t = time.time()
                    
                    if current_t < start_time:
                        allowed = cb.allow_request(current_t)
                        if allowed:
                            success = np.random.rand() > 0.1
                            latency = 0.1 + np.random.rand() * 0.1
                            cb.record_result(success, latency, current_t)
                        events_before.append({
                            "time": t,
                            "state": cb.state.value,
                            "allowed": allowed
                        })
                    
                    elif start_time <= current_t < end_time:
                        allowed = cb.allow_request(current_t)
                        if allowed:
                            if params.injection_type == "error":
                                success = np.random.rand() > params.intensity
                            elif params.injection_type == "latency":
                                success = True
                                latency = params.target_latency or (0.5 + np.random.rand())
                            else:
                                success = np.random.rand() > 0.1
                                latency = 0.1 + np.random.rand() * 0.1
                            
                            if params.injection_type == "latency":
                                latency = params.target_latency or (0.5 + np.random.rand())
                            else:
                                latency = 0.2 + np.random.rand() * 0.1
                            
                            cb.record_result(success, latency, current_t)
                        
                        if cb.state == CircuitState.OPEN and not result.circuit_breaker_triggered:
                            result.circuit_breaker_triggered = True
                            result.trigger_time = t - params.start_delay
                        
                        events_during.append({
                            "time": t,
                            "state": cb.state.value,
                            "allowed": allowed
                        })
                    
                    else:
                        allowed = cb.allow_request(current_t)
                        if allowed:
                            success = np.random.rand() > 0.1
                            latency = 0.1 + np.random.rand() * 0.1
                            cb.record_result(success, latency, current_t)
                        
                        if cb.state == CircuitState.CLOSED and result.circuit_breaker_triggered and result.recovery_time is None:
                            result.recovery_time = t - params.start_delay - params.duration
                        
                        events_after.append({
                            "time": t,
                            "state": cb.state.value,
                            "allowed": allowed
                        })
                    
                    t += 0.1
                    time.sleep(0.01)
                
                if events_before:
                    result.success_rate_before = sum(
                        1 for e in events_before if e['allowed']
                    ) / len(events_before) if events_before else 0
                
                if events_during:
                    result.success_rate_during = sum(
                        1 for e in events_during if e['allowed']
                    ) / len(events_during) if events_during else 0
                
                if events_after:
                    result.success_rate_after = sum(
                        1 for e in events_after if e['allowed']
                    ) / len(events_after) if events_after else 0
                
                result.events_before = events_before[:100]
                result.events_during = events_during[:100]
                result.events_after = events_after[:100]
                result.status = "completed"
                
                with self._lock:
                    self._injection_tasks[task_id]["status"] = "completed"
                    self._injection_tasks[task_id]["result"] = result
                    
            except Exception as e:
                result.status = "failed"
                with self._lock:
                    self._injection_tasks[task_id]["status"] = "failed"
                    self._injection_tasks[task_id]["error"] = str(e)
        
        thread = threading.Thread(target=run_injection, daemon=True)
        thread.start()
        
        return result
    
    def get_injection_result(self, task_id: str) -> Optional[FaultInjectionResult]:
        with self._lock:
            task = self._injection_tasks.get(task_id)
            if task:
                return task.get("result")
            return None


class EventAnalyzer:
    def __init__(self):
        self._events: Dict[str, List[CircuitBreakerEvent]] = {}
        self._lock = threading.RLock()
    
    def record_event(self, event: CircuitBreakerEvent):
        with self._lock:
            endpoint = event.endpoint
            if endpoint not in self._events:
                self._events[endpoint] = []
            self._events[endpoint].append(event)
            if len(self._events[endpoint]) > 10000:
                self._events[endpoint] = self._events[endpoint][-10000:]
    
    def analyze_events(self, endpoint: str) -> EventAnalysisResult:
        with self._lock:
            events = self._events.get(endpoint, [])
        
        cb = circuit_breakers.get(endpoint)
        cb_metrics = cb.get_metrics() if cb else {}
        
        state_changes = [e for e in events if e.event_type == "state_change"]
        open_events = [e for e in events if e.new_state == "OPEN"]
        reject_events = [e for e in events if e.event_type == "reject"]
        
        potential_false_trips = 0
        if len(open_events) >= 2:
            for i in range(1, len(open_events)):
                time_between = (open_events[i].timestamp - open_events[i-1].timestamp).total_seconds()
                if time_between < 30.0:
                    potential_false_trips += 1
        
        false_trip_rate = potential_false_trips / max(1, len(open_events))
        
        times_between = []
        for i in range(1, len(open_events)):
            times_between.append(
                (open_events[i].timestamp - open_events[i-1].timestamp).total_seconds()
            )
        
        avg_time_between = np.mean(times_between) if times_between else 0
        
        recommendations = []
        if false_trip_rate > 0.3:
            recommendations.append("检测到频繁的熔断触发，建议增加 failure_threshold 或 half_open_window")
        if avg_time_between < 60.0 and len(open_events) > 3:
            recommendations.append("熔断触发过于频繁，建议增加 open_duration 或 min_requests")
        if cb_metrics.get("reject_rate", 0) > 0.3:
            recommendations.append("拒绝率过高，建议调整 failure_threshold 或 timeout")
        
        false_trip_analysis = FalseTripAnalysis(
            endpoint=endpoint,
            event_count=len(events),
            potential_false_trips=potential_false_trips,
            false_trip_rate=false_trip_rate,
            avg_time_between_trips=avg_time_between,
            min_requests_before_trip=cb_metrics.get("current_window_requests", 0),
            avg_error_rate_before_trip=cb_metrics.get("window_error_rate", 0),
            recommendations=recommendations
        )
        
        general_recommendations = list(recommendations)
        if not recommendations:
            general_recommendations.append("当前配置运行良好，无明显问题")
        
        return EventAnalysisResult(
            endpoint=endpoint,
            total_events=len(events),
            state_changes=len(state_changes),
            open_events=[{
                "timestamp": e.timestamp.isoformat(),
                "old_state": e.old_state,
                "new_state": e.new_state,
                "details": e.details
            } for e in open_events[-20:]],
            reject_events=[{
                "timestamp": e.timestamp.isoformat(),
                "details": e.details
            } for e in reject_events[-20:]],
            false_trip_analysis=false_trip_analysis,
            recommendations=general_recommendations
        )


config_push_manager = ConfigPushManager()
fault_injection_manager = FaultInjectionManager()
event_analyzer = EventAnalyzer()


@app.route('/api/config/push', methods=['POST'])
def push_config():
    try:
        data = request.get_json()
        endpoint = data.get('endpoint', 'api/default')
        config_data = data.get('config', {})
        
        new_config = CircuitBreakerConfig(**config_data)
        result = config_push_manager.push_config(endpoint, new_config)
        
        return jsonify(result.model_dump())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/config/history/<path:endpoint>', methods=['GET'])
def get_config_history(endpoint: str):
    try:
        history = config_push_manager.get_config_history(endpoint)
        if not history:
            return jsonify({
                "status": "error",
                "message": "No config history found"
            }), 404
        
        return jsonify({
            "endpoint": endpoint,
            "current_version": config_push_manager.get_current_version(endpoint),
            "history": [{
                "version": history.versions[i],
                "config": history.configs[i],
                "timestamp": history.timestamps[i].isoformat()
            } for i in range(len(history.versions))]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/config/rollback/<path:endpoint>', methods=['POST'])
def rollback_config(endpoint: str):
    try:
        data = request.get_json() or {}
        version = data.get('version')
        
        if not version:
            return jsonify({
                "status": "error",
                "message": "Version is required"
            }), 400
        
        result = config_push_manager.rollback(endpoint, version)
        if not result:
            return jsonify({
                "status": "error",
                "message": "Rollback failed"
            }), 400
        
        return jsonify(result.model_dump())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/fault/inject', methods=['POST'])
def inject_fault():
    try:
        data = request.get_json()
        params = FaultInjectionParams(**data)
        
        result = fault_injection_manager.inject_fault(params)
        
        return jsonify({
            "status": "success",
            "task_id": result.task_id,
            "message": "Fault injection started"
        }), 202
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/fault/result/<task_id>', methods=['GET'])
def get_fault_result(task_id: str):
    try:
        result = fault_injection_manager.get_injection_result(task_id)
        if not result:
            return jsonify({
                "status": "error",
                "message": "Task not found"
            }), 404
        
        return jsonify(result.model_dump())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/events/record', methods=['POST'])
def record_event():
    try:
        data = request.get_json()
        event = CircuitBreakerEvent(**data)
        event_analyzer.record_event(event)
        
        return jsonify({
            "status": "success",
            "message": "Event recorded"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/events/analyze/<path:endpoint>', methods=['GET'])
def analyze_events(endpoint: str):
    try:
        result = event_analyzer.analyze_events(endpoint)
        return jsonify(result.model_dump())
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/events/analyze/<path:endpoint>/optimize', methods=['POST'])
def optimize_based_on_analysis(endpoint: str):
    try:
        analysis = event_analyzer.analyze_events(endpoint)
        
        current_config = circuit_breakers.get(endpoint)
        if current_config:
            current_cb_config = current_config.config
        else:
            current_cb_config = CircuitBreakerConfig()
        
        recommendations = analysis.recommendations
        
        params = SimulationParams(
            duration=120.0,
            base_error_rate=0.1,
            base_latency=0.2,
            traffic_pattern="spike",
            failure_spike_times=[60.0]
        )
        
        opt_params = OptimizationParams(
            n_calls=20,
            n_random_starts=5,
            verbose=False
        )
        
        result = optimize_circuit_breaker(
            simulation_params=params,
            optimization_params=opt_params,
            endpoint=endpoint
        )
        
        push_result = config_push_manager.push_config(endpoint, result.best_config)
        
        return jsonify({
            "status": "success",
            "analysis": analysis.model_dump(),
            "optimization_result": {
                "best_config": result.best_config.model_dump(),
                "best_score": result.best_score,
                "parameter_explanations": result.parameter_explanations
            },
            "push_result": push_result.model_dump(),
            "recommendations": recommendations
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


@app.route('/api/fault/drill', methods=['POST'])
def run_drill():
    try:
        data = request.get_json() or {}
        endpoint = data.get('endpoint', 'api/test')
        drill_type = data.get('drill_type', 'full')
        
        base_config = CircuitBreakerConfig()
        
        if drill_type == 'full':
            fault_configs = [
                {"type": "error", "intensity": 0.3, "duration": 10.0},
                {"type": "error", "intensity": 0.5, "duration": 15.0},
                {"type": "error", "intensity": 0.7, "duration": 20.0},
                {"type": "latency", "intensity": 0.5, "duration": 10.0, "target_latency": 1.0},
                {"type": "traffic", "intensity": 0.5, "duration": 15.0}
            ]
        else:
            fault_configs = [{"type": "error", "intensity": 0.5, "duration": 10.0}]
        
        results = []
        for fc in fault_configs:
            params = FaultInjectionParams(
                endpoint=endpoint,
                injection_type=fc['type'],
                intensity=fc['intensity'],
                duration=fc['duration'],
                start_delay=1.0,
                target_latency=fc.get('target_latency')
            )
            result = fault_injection_manager.inject_fault(params)
            results.append({
                "task_id": result.task_id,
                "config": fc
            })
        
        return jsonify({
            "status": "success",
            "message": f"Started {len(results)} fault injection drills",
            "drill_tasks": results
        }), 202
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
