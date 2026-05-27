import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
from skopt import gp_minimize, forest_minimize, dummy_minimize
from skopt.space import Real, Integer, Space
from skopt.utils import use_named_args
from skopt.callbacks import VerboseCallback
from models import CircuitBreakerConfig, SimulationParams, OptimizationResult
from simulation_engine import run_simulation


@dataclass
class OptimizationParams:
    n_calls: int = 50
    n_random_starts: int = 15
    acq_func: str = "EI"
    acq_optimizer: str = "sampling"
    n_points: int = 10000
    optimizer: str = "gp"
    random_state: int = 42
    verbose: bool = True
    xi: float = 0.05
    kappa: float = 1.96


PARAMETER_EXPLANATIONS: Dict[str, Dict[str, Any]] = {
    "timeout": {
        "name": "超时时间",
        "unit": "秒",
        "description": "请求超时阈值，超过该时间则判定为超时失败",
        "recommended_range": "1.0 - 5.0",
        "default": 3.0,
        "impact": "设置过小会误杀正常慢请求；设置过大降低熔断敏感度",
        "tradeoff": "低延迟 vs 容错能力"
    },
    "failure_threshold": {
        "name": "失败率阈值",
        "unit": "比例",
        "description": "窗口内错误率达到该阈值时触发熔断",
        "recommended_range": "0.3 - 0.7",
        "default": 0.5,
        "impact": "设置过低会频繁熔断；设置过高降低保护效果",
        "tradeoff": "保护力度 vs 可用性"
    },
    "half_open_window": {
        "name": "半开探测窗口",
        "unit": "秒",
        "description": "统计失败率的时间窗口大小，决定熔断判定的灵敏度",
        "recommended_range": "10.0 - 30.0",
        "default": 10.0,
        "impact": "窗口太小易受波动影响；太大响应不及时",
        "tradeoff": "灵敏度 vs 稳定性"
    },
    "min_requests": {
        "name": "最小请求数",
        "unit": "个",
        "description": "触发熔断所需的最小请求样本数，防止小样本误判",
        "recommended_range": "5 - 20",
        "default": 5,
        "impact": "设置过小容易误熔断；太大需要更多样本才触发",
        "tradeoff": "快速响应 vs 统计显著性"
    },
    "open_duration": {
        "name": "熔断持续时间",
        "unit": "秒",
        "description": "熔断后保持OPEN状态的时长，之后进入半开探测",
        "recommended_range": "15.0 - 60.0",
        "default": 30.0,
        "impact": "设置太短频繁切换状态；太长降低系统可用性",
        "tradeoff": "恢复速度 vs 系统稳定性"
    }
}


RETRY_PARAMETER_EXPLANATIONS: Dict[str, Dict[str, Any]] = {
    "enabled": {
        "name": "重试风暴开关",
        "unit": "布尔",
        "description": "是否启用重试风暴模拟",
        "recommended_range": "True/False",
        "default": False,
        "impact": "启用后会模拟真实世界的重试行为，更贴近生产环境",
        "tradeoff": "真实性 vs 计算复杂度"
    },
    "max_retries": {
        "name": "最大重试次数",
        "unit": "次",
        "description": "单次请求失败后的最大重试次数",
        "recommended_range": "1 - 5",
        "default": 3,
        "impact": "重试次数过多放大流量；次数太少降低成功率",
        "tradeoff": "成功率 vs 系统负载"
    },
    "retry_delay_base": {
        "name": "重试延迟基数",
        "unit": "秒",
        "description": "首次重试的基础延迟时间",
        "recommended_range": "0.05 - 0.5",
        "default": 0.1,
        "impact": "延迟太短易造成瞬时冲击；太长影响用户体验",
        "tradeoff": "响应速度 vs 系统保护"
    },
    "retry_backoff_multiplier": {
        "name": "退避乘数",
        "unit": "倍数",
        "description": "指数退避的乘数，每次重试延迟 = 基数 * 乘数^重试次数",
        "recommended_range": "1.5 - 3.0",
        "default": 2.0,
        "impact": "乘数太大重试间隔增长过快；太小退避效果不足",
        "tradeoff": "退避速度 vs 重试频率"
    },
    "retry_jitter": {
        "name": "抖动比例",
        "unit": "比例",
        "description": "重试延迟的随机抖动范围，避免重试惊群效应",
        "recommended_range": "0.05 - 0.3",
        "default": 0.1,
        "impact": "抖动太小容易产生同步重试；太大延迟不可预测",
        "tradeoff": "避免惊群 vs 延迟确定性"
    },
    "retry_storm_trigger_threshold": {
        "name": "重试风暴触发阈值",
        "unit": "错误率",
        "description": "当错误率超过此阈值时触发重试风暴（流量放大）",
        "recommended_range": "0.2 - 0.5",
        "default": 0.3,
        "impact": "阈值太低容易误触发；太高失去测试意义",
        "tradeoff": "测试敏感度 vs 场景真实性"
    },
    "retry_amplification_factor": {
        "name": "流量放大倍数",
        "unit": "倍数",
        "description": "重试风暴期间的流量放大倍数",
        "recommended_range": "2.0 - 5.0",
        "default": 3.0,
        "impact": "倍数越大系统压力越大；太小测试不够充分",
        "tradeoff": "测试严格度 vs 系统极限"
    }
}


@dataclass
class ParameterBounds:
    timeout: Tuple[float, float] = (0.5, 10.0)
    failure_threshold: Tuple[float, float] = (0.2, 0.9)
    half_open_window: Tuple[float, float] = (5.0, 60.0)
    min_requests: Tuple[int, int] = (3, 50)
    open_duration: Tuple[float, float] = (10.0, 120.0)


class BayesianOptimizer:
    def __init__(self, 
                 simulation_params: SimulationParams,
                 optimization_params: Optional[OptimizationParams] = None,
                 parameter_bounds: Optional[ParameterBounds] = None,
                 endpoint: str = "api/test"):
        self.simulation_params = simulation_params
        self.optimization_params = optimization_params or OptimizationParams()
        self.parameter_bounds = parameter_bounds or ParameterBounds()
        self.endpoint = endpoint
        
        self.optimization_history: List[Dict[str, Any]] = []
        self.all_results: List[Dict[str, Any]] = []
        self._iteration = 0
        
        self.space = self._define_search_space()
    
    def _define_search_space(self) -> Space:
        pb = self.parameter_bounds
        return [
            Real(pb.timeout[0], pb.timeout[1], name="timeout", prior="log-uniform"),
            Real(pb.failure_threshold[0], pb.failure_threshold[1], name="failure_threshold"),
            Real(pb.half_open_window[0], pb.half_open_window[1], name="half_open_window", prior="log-uniform"),
            Integer(pb.min_requests[0], pb.min_requests[1], name="min_requests"),
            Real(pb.open_duration[0], pb.open_duration[1], name="open_duration", prior="log-uniform")
        ]
    
    def _objective(self, params: Dict[str, Any]) -> float:
        config = CircuitBreakerConfig(**params)
        sim_result = run_simulation(config, self.simulation_params, self.endpoint)
        
        result_entry = {
            "iteration": self._iteration,
            "params": params.copy(),
            "score": sim_result.score,
            "stats": sim_result.final_stats
        }
        self.all_results.append(result_entry)
        
        history_entry = {
            "iteration": self._iteration,
            "score": sim_result.score,
            "timeout": params["timeout"],
            "failure_threshold": params["failure_threshold"],
            "half_open_window": params["half_open_window"],
            "min_requests": params["min_requests"],
            "open_duration": params["open_duration"],
            "success_rate": sim_result.final_stats.get("success_rate", 0.0),
            "reject_rate": sim_result.final_stats.get("reject_rate", 0.0),
            "avg_latency": sim_result.final_stats.get("avg_latency", 0.0),
            "error_rate": sim_result.final_stats.get("error_rate", 0.0),
            "avg_recovery_time": sim_result.final_stats.get("avg_recovery_time", 0.0),
            "open_ratio": sim_result.final_stats.get("open_ratio", 0.0),
            "retry_storm_duration": sim_result.final_stats.get("retry_storm_duration", 0.0),
            "total_retries": sim_result.final_stats.get("total_retries", 0),
            "retry_success_rate": sim_result.final_stats.get("retry_success_rate", 0.0)
        }
        self.optimization_history.append(history_entry)
        
        if self.optimization_params.verbose:
            print(f"Iteration {self._iteration}: Score = {sim_result.score:.4f}, "
                  f"Timeout={params['timeout']:.2f}s, "
                  f"Threshold={params['failure_threshold']:.2f}, "
                  f"SuccessRate={sim_result.final_stats.get('success_rate', 0):.2%}")
        
        self._iteration += 1
        
        return -sim_result.score
    
    def optimize(self) -> OptimizationResult:
        self.optimization_history = []
        self.all_results = []
        self._iteration = 0
        
        @use_named_args(self.space)
        def objective(**params):
            return self._objective(params)
        
        callbacks = []
        if self.optimization_params.verbose:
            callbacks.append(VerboseCallback(n_total=self.optimization_params.n_calls))
        
        opt_params = self.optimization_params
        if opt_params.optimizer == "gp":
            result = gp_minimize(
                objective,
                self.space,
                n_calls=opt_params.n_calls,
                n_random_starts=opt_params.n_random_starts,
                acq_func=opt_params.acq_func,
                acq_optimizer=opt_params.acq_optimizer,
                n_points=opt_params.n_points,
                xi=opt_params.xi,
                kappa=opt_params.kappa,
                random_state=opt_params.random_state,
                callback=callbacks,
                verbose=opt_params.verbose
            )
        elif opt_params.optimizer == "forest":
            result = forest_minimize(
                objective,
                self.space,
                n_calls=opt_params.n_calls,
                n_random_starts=opt_params.n_random_starts,
                random_state=opt_params.random_state,
                callback=callbacks,
                verbose=opt_params.verbose
            )
        else:
            result = dummy_minimize(
                objective,
                self.space,
                n_calls=opt_params.n_calls,
                random_state=opt_params.random_state,
                callback=callbacks,
                verbose=opt_params.verbose
            )
        
        best_idx = np.argmin(result.func_vals)
        best_params_dict = {
            "timeout": float(result.x[0]),
            "failure_threshold": float(result.x[1]),
            "half_open_window": float(result.x[2]),
            "min_requests": int(result.x[3]),
            "open_duration": float(result.x[4])
        }
        
        best_config = CircuitBreakerConfig(**best_params_dict)
        best_score = -float(result.fun)
        
        metrics_summary = self._generate_metrics_summary(best_config, best_score)
        
        parameter_explanations = self._generate_parameter_explanations(best_params_dict)
        
        return OptimizationResult(
            best_config=best_config,
            best_score=best_score,
            all_results=self.all_results,
            optimization_history=self.optimization_history,
            metrics_summary=metrics_summary,
            parameter_explanations=parameter_explanations
        )
    
    def _generate_parameter_explanations(self, best_params: Dict[str, Any]) -> Dict[str, Any]:
        explanations = {}
        
        for param_name, param_value in best_params.items():
            if param_name in PARAMETER_EXPLANATIONS:
                expl = PARAMETER_EXPLANATIONS[param_name].copy()
                expl["current_value"] = param_value
                expl["in_range"] = self._check_value_in_range(param_name, param_value, expl["recommended_range"])
                explanations[param_name] = expl
        
        if hasattr(self.simulation_params, 'retry_storm') and self.simulation_params.retry_storm.enabled:
            explanations["retry_storm"] = {}
            retry_params = self.simulation_params.retry_storm.model_dump()
            for param_name, param_value in retry_params.items():
                if param_name in RETRY_PARAMETER_EXPLANATIONS:
                    expl = RETRY_PARAMETER_EXPLANATIONS[param_name].copy()
                    expl["current_value"] = param_value
                    explanations["retry_storm"][param_name] = expl
        
        return explanations
    
    def _check_value_in_range(self, param_name: str, value: Any, range_str: str) -> bool:
        try:
            if range_str == "True/False":
                return isinstance(value, bool)
            
            if " - " in range_str:
                parts = range_str.split(" - ")
                min_val = float(parts[0])
                max_val = float(parts[1])
                return min_val <= float(value) <= max_val
        except:
            pass
        return True
    
    def _generate_metrics_summary(self, best_config: CircuitBreakerConfig, 
                                  best_score: float) -> Dict[str, Any]:
        if not self.all_results:
            return {}
        
        scores = [r["score"] for r in self.all_results]
        success_rates = [r["stats"].get("success_rate", 0) for r in self.all_results]
        reject_rates = [r["stats"].get("reject_rate", 0) for r in self.all_results]
        latencies = [r["stats"].get("avg_latency", 0) for r in self.all_results]
        
        best_result = self.all_results[np.argmax(scores)]
        
        return {
            "best_score": best_score,
            "best_config": best_config.model_dump(),
            "mean_score": float(np.mean(scores)),
            "std_score": float(np.std(scores)),
            "max_score": float(np.max(scores)),
            "min_score": float(np.min(scores)),
            "mean_success_rate": float(np.mean(success_rates)),
            "mean_reject_rate": float(np.mean(reject_rates)),
            "mean_latency": float(np.mean(latencies)),
            "total_iterations": len(self.all_results),
            "best_iteration_metrics": best_result["stats"]
        }
    
    def get_convergence_data(self) -> Dict[str, Any]:
        if not self.optimization_history:
            return {}
        
        iterations = [h["iteration"] for h in self.optimization_history]
        scores = [h["score"] for h in self.optimization_history]
        
        running_max = np.maximum.accumulate(scores)
        
        return {
            "iterations": iterations,
            "scores": scores,
            "running_max": running_max.tolist(),
            "converged": running_max[-1] - running_max[max(0, len(running_max)-5)] < 0.01 if len(running_max) >= 5 else False
        }


def optimize_circuit_breaker(
    simulation_params: SimulationParams,
    optimization_params: Optional[OptimizationParams] = None,
    parameter_bounds: Optional[ParameterBounds] = None,
    endpoint: str = "api/test"
) -> OptimizationResult:
    optimizer = BayesianOptimizer(
        simulation_params=simulation_params,
        optimization_params=optimization_params,
        parameter_bounds=parameter_bounds,
        endpoint=endpoint
    )
    return optimizer.optimize()
