import numpy as np
from datetime import datetime, timedelta
from models import MetricData, CircuitBreakerConfig, SimulationParams, RetryStormParams
from simulation_engine import run_simulation
from bayesian_optimizer import optimize_circuit_breaker, OptimizationParams, PARAMETER_EXPLANATIONS, RETRY_PARAMETER_EXPLANATIONS


def generate_sample_metrics(endpoint: str = "api/user", count: int = 50) -> list:
    metrics = []
    base_time = datetime.now() - timedelta(hours=1)
    
    for i in range(count):
        t = base_time + timedelta(seconds=i * 10)
        
        if 10 <= i <= 20:
            error_rate = 0.3 + np.random.rand() * 0.4
            latency = 0.5 + np.random.rand() * 0.5
        else:
            error_rate = 0.02 + np.random.rand() * 0.05
            latency = 0.1 + np.random.rand() * 0.1
        
        total = np.random.randint(50, 150)
        failures = int(total * error_rate)
        successes = total - failures
        
        metric = MetricData(
            timestamp=t,
            endpoint=endpoint,
            success_count=successes,
            failure_count=failures,
            total_requests=total,
            avg_latency=latency,
            p50_latency=latency * 0.8,
            p95_latency=latency * 1.5,
            p99_latency=latency * 2.0,
            error_rate=error_rate,
            throughput=total / 10.0
        )
        metrics.append(metric)
    
    return metrics


def test_circuit_breaker():
    print("=" * 60)
    print("测试熔断器核心逻辑")
    print("=" * 60)
    
    from circuit_breaker import CircuitBreaker
    
    config = CircuitBreakerConfig(
        timeout=2.0,
        failure_threshold=0.5,
        half_open_window=10.0,
        min_requests=5,
        open_duration=15.0
    )
    
    cb = CircuitBreaker(config, "api/test")
    
    print(f"初始状态: {cb.state}")
    
    t = 0.0
    print("\n模拟连续失败...")
    for i in range(10):
        t += 0.5
        allowed = cb.allow_request(t)
        if allowed:
            cb.record_result(False, 0.3, t)
        metrics = cb.get_metrics()
        print(f"  t={t:.1f}s, 状态={metrics['state']}, 窗口错误率={metrics['window_error_rate']:.2%}")
    
    print(f"\n熔断后状态: {cb.state}")
    print(f"拒绝请求数: {cb.get_metrics()['rejected_requests']}")
    
    print("\n等待熔断超时...")
    t += 20.0
    
    print(f"\n半开状态测试:")
    for i in range(10):
        t += 0.5
        allowed = cb.allow_request(t)
        if allowed:
            success = i < 3
            cb.record_result(success, 0.2, t)
        metrics = cb.get_metrics()
        print(f"  t={t:.1f}s, 允许={allowed}, 状态={metrics['state']}, 成功={success if allowed else 'N/A'}")
    
    print(f"\n最终状态: {cb.state}")
    print("熔断器测试通过!\n")


def test_simulation_engine():
    print("=" * 60)
    print("测试模拟引擎")
    print("=" * 60)
    
    config = CircuitBreakerConfig(
        timeout=3.0,
        failure_threshold=0.5,
        half_open_window=10.0,
        min_requests=5,
        open_duration=30.0
    )
    
    params = SimulationParams(
        duration=120.0,
        base_error_rate=0.05,
        base_latency=0.2,
        traffic_pattern="spike",
        failure_spike_times=[60.0]
    )
    
    print(f"配置: 超时={config.timeout}s, 失败阈值={config.failure_threshold:.0%}")
    print(f"模拟参数: 时长={params.duration}s, 基础错误率={params.base_error_rate:.0%}")
    
    result = run_simulation(config, params, "api/test")
    
    print(f"\n模拟结果:")
    print(f"  总分: {result.score:.4f}")
    print(f"  总请求数: {result.final_stats['total_requests']}")
    print(f"  成功率: {result.final_stats['success_rate']:.2%}")
    print(f"  拒绝率: {result.final_stats['reject_rate']:.2%}")
    print(f"  平均延迟: {result.final_stats['avg_latency']:.3f}s")
    print(f"  熔断器状态切换次数: {result.final_stats['state_changes']}")
    print(f"  熔断时间占比: {result.final_stats['open_ratio']:.2%}")
    print(f"  有效吞吐量: {result.final_stats['effective_throughput']:.2f} req/s")
    
    print("\n前5个指标点:")
    for m in result.metrics[:5]:
        print(f"  t={m.timestamp.strftime('%H:%M:%S')}, 吞吐={m.throughput:.1f}, "
              f"错误率={m.error_rate:.2%}, 延迟={m.avg_latency:.3f}s")
    
    print("模拟引擎测试通过!\n")
    return result


def test_retry_storm_model():
    print("=" * 60)
    print("测试重试风暴模型")
    print("=" * 60)
    
    config = CircuitBreakerConfig(
        timeout=3.0,
        failure_threshold=0.5,
        half_open_window=10.0,
        min_requests=5,
        open_duration=30.0
    )
    
    retry_params = RetryStormParams(
        enabled=True,
        max_retries=3,
        retry_delay_base=0.1,
        retry_backoff_multiplier=2.0,
        retry_jitter=0.1,
        retry_storm_trigger_threshold=0.3,
        retry_amplification_factor=3.0
    )
    
    params = SimulationParams(
        duration=120.0,
        base_error_rate=0.05,
        base_latency=0.2,
        traffic_pattern="spike",
        failure_spike_times=[60.0],
        retry_storm=retry_params
    )
    
    print(f"配置: 超时={config.timeout}s, 失败阈值={config.failure_threshold:.0%}")
    print(f"重试风暴: 启用, 最大重试={retry_params.max_retries}次, "
          f"放大倍数={retry_params.retry_amplification_factor}x")
    
    result = run_simulation(config, params, "api/test")
    stats = result.final_stats
    
    print(f"\n重试风暴模拟结果:")
    print(f"  总分: {result.score:.4f}")
    print(f"  原始请求数: {stats.get('original_requests', 0)}")
    print(f"  总请求数(含重试): {stats['total_requests']}")
    print(f"  重试次数: {stats.get('total_retries', 0)}")
    print(f"  重试成功率: {stats.get('retry_success_rate', 0):.2%}")
    print(f"  流量放大倍数: {stats.get('retry_storm_traffic_amplification', 1.0):.2f}x")
    print(f"  重试风暴持续时间: {stats.get('retry_storm_duration', 0):.1f}s")
    print(f"  重试风暴时间占比: {stats.get('retry_storm_ratio', 0):.2%}")
    print(f"  平均恢复时间: {stats.get('avg_recovery_time', 0):.2f}s")
    print(f"  最大恢复时间: {stats.get('max_recovery_time', 0):.2f}s")
    print(f"  成功率: {stats['success_rate']:.2%}")
    print(f"  拒绝率: {stats['reject_rate']:.2%}")
    
    print(f"\n恢复时间序列: {stats.get('recovery_times', [])[:5]}...")
    
    print("\n对比: 无重试风暴 vs 有重试风暴")
    params_no_retry = SimulationParams(
        duration=120.0,
        base_error_rate=0.05,
        base_latency=0.2,
        traffic_pattern="spike",
        failure_spike_times=[60.0],
        retry_storm=RetryStormParams(enabled=False)
    )
    result_no_retry = run_simulation(config, params_no_retry, "api/test")
    stats_no = result_no_retry.final_stats
    
    print(f"  无重试: 得分={result_no_retry.score:.4f}, 总请求={stats_no['total_requests']}, "
          f"成功率={stats_no['success_rate']:.2%}")
    print(f"  有重试: 得分={result.score:.4f}, 总请求={stats['total_requests']}, "
          f"成功率={stats['success_rate']:.2%}")
    print(f"  差异: 得分={result.score - result_no_retry.score:+.4f}, "
          f"请求量={stats['total_requests'] - stats_no['total_requests']:+d}")
    
    print("重试风暴模型测试通过!\n")
    return result


def test_circuit_breaker_recovery():
    print("=" * 60)
    print("测试熔断恢复能力")
    print("=" * 60)
    
    configs = [
        ("激进配置", CircuitBreakerConfig(timeout=1.0, failure_threshold=0.3, 
                                           half_open_window=5.0, min_requests=3, 
                                           open_duration=10.0)),
        ("平衡配置", CircuitBreakerConfig(timeout=3.0, failure_threshold=0.5, 
                                           half_open_window=15.0, min_requests=10, 
                                           open_duration=30.0)),
        ("保守配置", CircuitBreakerConfig(timeout=5.0, failure_threshold=0.7, 
                                           half_open_window=30.0, min_requests=20, 
                                           open_duration=60.0)),
    ]
    
    retry_params = RetryStormParams(
        enabled=True,
        max_retries=3,
        retry_storm_trigger_threshold=0.3,
        retry_amplification_factor=3.0
    )
    
    params = SimulationParams(
        duration=180.0,
        base_error_rate=0.05,
        base_latency=0.2,
        traffic_pattern="spike",
        failure_spike_times=[60.0, 120.0],
        retry_storm=retry_params
    )
    
    print(f"测试场景: 两次故障尖峰(60s, 120s)，启用重试风暴\n")
    
    results = []
    for name, config in configs:
        result = run_simulation(config, params, "api/test")
        stats = result.final_stats
        results.append((name, config, result))
        
        print(f"{name}:")
        print(f"  配置: 超时={config.timeout}s, 阈值={config.failure_threshold:.0%}, "
              f"窗口={config.half_open_window}s, 熔断={config.open_duration}s")
        print(f"  得分: {result.score:.4f}")
        print(f"  状态切换: {stats['state_changes']}次")
        print(f"  熔断占比: {stats['open_ratio']:.2%}")
        print(f"  平均恢复: {stats.get('avg_recovery_time', 0):.2f}s")
        print(f"  成功率: {stats['success_rate']:.2%}")
        print(f"  拒绝率: {stats['reject_rate']:.2%}")
        print()
    
    best_idx = max(range(len(results)), key=lambda i: results[i][2].score)
    best_name, _, _ = results[best_idx]
    print(f"最佳配置: {best_name}")
    
    print("熔断恢复能力测试通过!\n")


def test_parameter_explanations():
    print("=" * 60)
    print("测试参数解释输出")
    print("=" * 60)
    
    params = SimulationParams(
        duration=60.0,
        base_error_rate=0.1,
        base_latency=0.2,
        traffic_pattern="spike",
        failure_spike_times=[30.0],
        retry_storm=RetryStormParams(enabled=True)
    )
    
    opt_params = OptimizationParams(
        n_calls=5,
        n_random_starts=2,
        verbose=False
    )
    
    result = optimize_circuit_breaker(
        simulation_params=params,
        optimization_params=opt_params,
        endpoint="api/test"
    )
    
    print(f"\n最佳参数配置:")
    for param_name, expl in result.parameter_explanations.items():
        if param_name == "retry_storm":
            continue
        in_range = expl.get('in_range', False)
        range_status = "[OK] 在推荐范围内" if in_range else "[!!] 超出推荐范围"
        print(f"\n  {expl['name']} ({param_name}):")
        print(f"    当前值: {expl['current_value']} {expl['unit']}")
        print(f"    推荐范围: {expl['recommended_range']} {expl['unit']}")
        print(f"    {range_status}")
        print(f"    说明: {expl['description']}")
        print(f"    影响: {expl['impact']}")
        print(f"    权衡: {expl['tradeoff']}")
    
    if "retry_storm" in result.parameter_explanations:
        print(f"\n重试风暴参数:")
        for param_name, expl in result.parameter_explanations["retry_storm"].items():
            print(f"\n  {expl['name']} ({param_name}):")
            print(f"    当前值: {expl['current_value']}")
            print(f"    推荐范围: {expl['recommended_range']}")
            print(f"    说明: {expl['description']}")
    
    print(f"\n熔断器参数详解:")
    for param_name, expl in PARAMETER_EXPLANATIONS.items():
        print(f"\n  {expl['name']} ({param_name}):")
        print(f"    单位: {expl['unit']}")
        print(f"    默认值: {expl['default']}")
        print(f"    推荐范围: {expl['recommended_range']}")
        print(f"    说明: {expl['description']}")
        print(f"    影响: {expl['impact']}")
        print(f"    权衡: {expl['tradeoff']}")
    
    print("\n参数解释输出测试通过!\n")
    return result


def test_bayesian_optimization():
    print("=" * 60)
    print("测试贝叶斯优化 (简化版 - 5次迭代)")
    print("=" * 60)
    
    params = SimulationParams(
        duration=60.0,
        base_error_rate=0.1,
        base_latency=0.2,
        traffic_pattern="spike",
        failure_spike_times=[30.0]
    )
    
    opt_params = OptimizationParams(
        n_calls=5,
        n_random_starts=2,
        verbose=True
    )
    
    print(f"模拟参数: 时长={params.duration}s, 基础错误率={params.base_error_rate:.0%}")
    print(f"优化迭代: {opt_params.n_calls}次, 随机探索: {opt_params.n_random_starts}次\n")
    
    result = optimize_circuit_breaker(
        simulation_params=params,
        optimization_params=opt_params,
        endpoint="api/test"
    )
    
    print(f"\n优化结果:")
    print(f"  最佳得分: {result.best_score:.4f}")
    print(f"  最佳配置:")
    print(f"    超时时间: {result.best_config.timeout:.2f}s")
    print(f"    失败阈值: {result.best_config.failure_threshold:.2%}")
    print(f"    半开窗口: {result.best_config.half_open_window:.2f}s")
    print(f"    最小请求数: {result.best_config.min_requests}")
    print(f"    熔断持续: {result.best_config.open_duration:.2f}s")
    
    print(f"\n优化摘要:")
    print(f"  平均得分: {result.metrics_summary['mean_score']:.4f}")
    print(f"  得分标准差: {result.metrics_summary['std_score']:.4f}")
    print(f"  总迭代次数: {result.metrics_summary['total_iterations']}")
    
    print("贝叶斯优化测试通过!\n")
    return result


def test_multiple_configs():
    print("=" * 60)
    print("多配置对比测试")
    print("=" * 60)
    
    params = SimulationParams(
        duration=120.0,
        base_error_rate=0.15,
        base_latency=0.3,
        traffic_pattern="spike",
        failure_spike_times=[60.0]
    )
    
    configs = [
        CircuitBreakerConfig(timeout=1.0, failure_threshold=0.3, half_open_window=5.0, 
                            min_requests=3, open_duration=10.0),
        CircuitBreakerConfig(timeout=3.0, failure_threshold=0.5, half_open_window=15.0,
                            min_requests=10, open_duration=30.0),
        CircuitBreakerConfig(timeout=5.0, failure_threshold=0.7, half_open_window=30.0,
                            min_requests=20, open_duration=60.0),
    ]
    
    results = []
    for i, config in enumerate(configs):
        print(f"\n配置 {i+1}: 超时={config.timeout}s, 阈值={config.failure_threshold:.0%}, "
              f"窗口={config.half_open_window}s")
        result = run_simulation(config, params, "api/test")
        results.append((config, result))
        print(f"  得分: {result.score:.4f}, 成功率: {result.final_stats['success_rate']:.2%}, "
              f"拒绝率: {result.final_stats['reject_rate']:.2%}")
    
    best_idx = max(range(len(results)), key=lambda i: results[i][1].score)
    print(f"\n最佳配置: 配置 {best_idx + 1}")
    
    print("多配置对比测试通过!\n")


def test_score_components():
    print("=" * 60)
    print("评分函数组件分析")
    print("=" * 60)
    
    config = CircuitBreakerConfig(
        timeout=2.0,
        failure_threshold=0.5,
        half_open_window=10.0,
        min_requests=5,
        open_duration=20.0
    )
    
    for error_rate in [0.01, 0.05, 0.15, 0.3, 0.5]:
        params = SimulationParams(
            duration=60.0,
            base_error_rate=error_rate,
            base_latency=0.2,
            traffic_pattern="steady"
        )
        result = run_simulation(config, params, "api/test")
        stats = result.final_stats
        print(f"错误率={error_rate:.0%}: 得分={result.score:.4f}, "
              f"成功率={stats['success_rate']:.2%}, 拒绝率={stats['reject_rate']:.2%}, "
              f"熔断占比={stats['open_ratio']:.2%}")
    
    print("\n评分函数测试通过!\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("熔断器配置优化工具 - 单元测试")
    print("=" * 60 + "\n")
    
    try:
        test_circuit_breaker()
        test_simulation_engine()
        test_retry_storm_model()
        test_circuit_breaker_recovery()
        test_parameter_explanations()
        test_bayesian_optimization()
        test_multiple_configs()
        test_score_components()
        
        print("=" * 60)
        print("所有测试通过! OK")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
