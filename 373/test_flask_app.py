import sys
import json
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, r'd:\Trae\project\record001\373')

from app import app


def test_flask_app():
    print("\n" + "=" * 70)
    print("熔断器配置优化工具 - Flask 应用功能测试")
    print("=" * 70 + "\n")
    
    client = app.test_client()
    client.testing = True
    
    passed = 0
    total = 0
    
    def run_test(name, test_func):
        nonlocal passed, total
        total += 1
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"[OK] {name}: 通过")
            else:
                print(f"[XX] {name}: 失败")
        except Exception as e:
            print(f"[XX] {name}: 异常 - {e}")
            import traceback
            traceback.print_exc()
    
    def test_health():
        r = client.get('/health')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'healthy'
        return True
    
    def generate_metrics(endpoint, count=20):
        metrics = []
        base_time = datetime.now() - timedelta(minutes=20)
        for i in range(count):
            t = base_time + timedelta(seconds=i * 10)
            if 8 <= i <= 14:
                error_rate = 0.2 + np.random.rand() * 0.3
                latency = 0.3 + np.random.rand() * 0.3
            else:
                error_rate = 0.02 + np.random.rand() * 0.04
                latency = 0.1 + np.random.rand() * 0.08
            
            total = np.random.randint(50, 150)
            failures = int(total * error_rate)
            metrics.append({
                "timestamp": t.isoformat(),
                "endpoint": endpoint,
                "success_count": total - failures,
                "failure_count": failures,
                "total_requests": total,
                "avg_latency": latency,
                "p50_latency": latency * 0.8,
                "p95_latency": latency * 1.8,
                "p99_latency": latency * 2.5,
                "error_rate": error_rate,
                "throughput": total / 10.0
            })
        return metrics
    
    def test_ingest_metrics():
        metrics = generate_metrics("api/v1/users", 20)
        r = client.post('/api/metrics', json=metrics)
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'success'
        return True
    
    def test_get_metrics():
        r = client.get('/api/metrics?endpoint=api/v1/users')
        assert r.status_code == 200
        data = r.get_json()
        assert 'count' in data
        assert 'metrics' in data
        return True
    
    def test_aggregate_metrics():
        r = client.get('/api/metrics/aggregate?endpoint=api/v1/users')
        assert r.status_code == 200
        data = r.get_json()
        assert 'endpoint' in data
        return True
    
    def test_simulate():
        payload = {
            "config": {
                "timeout": 3.0,
                "failure_threshold": 0.5,
                "half_open_window": 15.0,
                "min_requests": 10,
                "open_duration": 30.0
            },
            "params": {
                "duration": 60.0,
                "base_error_rate": 0.1,
                "base_latency": 0.2,
                "traffic_pattern": "spike",
                "failure_spike_times": [30.0]
            },
            "endpoint": "api/test"
        }
        r = client.post('/api/simulate', json=payload)
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'success'
        assert 'score' in data
        assert 'final_stats' in data
        return True
    
    def test_simulate_with_retry_storm():
        payload = {
            "config": {
                "timeout": 3.0,
                "failure_threshold": 0.5,
                "half_open_window": 15.0,
                "min_requests": 10,
                "open_duration": 30.0
            },
            "params": {
                "duration": 60.0,
                "base_error_rate": 0.1,
                "base_latency": 0.2,
                "traffic_pattern": "spike",
                "failure_spike_times": [30.0],
                "retry_storm": {
                    "enabled": True,
                    "max_retries": 3,
                    "retry_delay_base": 0.1,
                    "retry_backoff_multiplier": 2.0,
                    "retry_jitter": 0.1,
                    "retry_storm_trigger_threshold": 0.3,
                    "retry_amplification_factor": 3.0
                }
            },
            "endpoint": "api/test"
        }
        r = client.post('/api/simulate', json=payload)
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'success'
        assert 'final_stats' in data
        stats = data['final_stats']
        assert 'retry_storm_enabled' in stats
        assert 'total_retries' in stats
        assert 'avg_recovery_time' in stats
        return True
    
    def test_compare_configs():
        payload = {
            "configs": [
                {"timeout": 1.0, "failure_threshold": 0.3, "half_open_window": 5.0,
                 "min_requests": 3, "open_duration": 10.0},
                {"timeout": 3.0, "failure_threshold": 0.5, "half_open_window": 15.0,
                 "min_requests": 10, "open_duration": 30.0},
                {"timeout": 5.0, "failure_threshold": 0.7, "half_open_window": 30.0,
                 "min_requests": 20, "open_duration": 60.0}
            ],
            "params": {
                "duration": 60.0,
                "base_error_rate": 0.1,
                "base_latency": 0.2,
                "traffic_pattern": "spike",
                "failure_spike_times": [30.0]
            }
        }
        r = client.post('/api/compare', json=payload)
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'success'
        assert len(data['comparison']) == 3
        return True
    
    def test_optimize_async():
        payload = {
            "simulation_params": {
                "duration": 60.0,
                "base_error_rate": 0.1,
                "base_latency": 0.2,
                "traffic_pattern": "spike",
                "failure_spike_times": [30.0]
            },
            "optimization_params": {
                "n_calls": 3,
                "n_random_starts": 2,
                "verbose": False
            },
            "endpoint": "api/test"
        }
        r = client.post('/api/optimize', json=payload)
        assert r.status_code == 202
        data = r.get_json()
        assert data['status'] == 'success'
        assert 'task_id' in data
        return True
    
    def test_optimize_with_retry_storm():
        payload = {
            "simulation_params": {
                "duration": 60.0,
                "base_error_rate": 0.1,
                "base_latency": 0.2,
                "traffic_pattern": "spike",
                "failure_spike_times": [30.0],
                "retry_storm": {
                    "enabled": True,
                    "max_retries": 3,
                    "retry_amplification_factor": 3.0
                }
            },
            "optimization_params": {
                "n_calls": 3,
                "n_random_starts": 2,
                "verbose": False
            },
            "endpoint": "api/test"
        }
        r = client.post('/api/optimize', json=payload)
        assert r.status_code == 202
        data = r.get_json()
        assert data['status'] == 'success'
        assert 'task_id' in data
        return True
    
    def test_circuit_breaker_lifecycle():
        endpoint = "api/realtime"
        
        r = client.post(f'/api/circuit-breaker/{endpoint}', json={
            "timeout": 2.0,
            "failure_threshold": 0.5,
            "half_open_window": 10.0,
            "min_requests": 3,
            "open_duration": 15.0
        })
        assert r.status_code == 200
        
        r = client.get(f'/api/circuit-breaker/{endpoint}/allow')
        assert r.status_code == 200
        data = r.get_json()
        assert 'allowed' in data
        assert 'state' in data
        
        for i in range(10):
            r = client.get(f'/api/circuit-breaker/{endpoint}/allow')
            allow_data = r.get_json()
            if allow_data['allowed']:
                success = i >= 8
                r = client.post(f'/api/circuit-breaker/{endpoint}/record', 
                               json={"success": success, "latency": 0.2})
                assert r.status_code == 200
        
        r = client.get(f'/api/circuit-breaker/{endpoint}')
        assert r.status_code == 200
        data = r.get_json()
        assert 'metrics' in data
        
        r = client.post(f'/api/circuit-breaker/{endpoint}/reset')
        assert r.status_code == 200
        
        r = client.get('/api/circuit-breaker')
        assert r.status_code == 200
        
        return True
    
    def test_list_tasks():
        r = client.get('/api/optimize/tasks')
        assert r.status_code == 200
        data = r.get_json()
        assert 'tasks' in data
        assert 'count' in data
        return True
    
    def test_parameter_explanations_api():
        r = client.get('/api/parameter-explanations')
        assert r.status_code == 200
        data = r.get_json()
        assert 'circuit_breaker_params' in data
        assert 'retry_storm_params' in data
        assert 'timeout' in data['circuit_breaker_params']
        assert 'enabled' in data['retry_storm_params']
        return True
    
    print("运行 Flask 应用测试:\n")
    
    run_test("健康检查接口", test_health)
    run_test("指标数据采集", test_ingest_metrics)
    run_test("指标数据查询", test_get_metrics)
    run_test("聚合指标查询", test_aggregate_metrics)
    run_test("单次模拟接口", test_simulate)
    run_test("重试风暴模拟接口", test_simulate_with_retry_storm)
    run_test("多配置对比接口", test_compare_configs)
    run_test("贝叶斯优化接口(异步)", test_optimize_async)
    run_test("重试风暴优化接口", test_optimize_with_retry_storm)
    run_test("熔断器生命周期API", test_circuit_breaker_lifecycle)
    run_test("优化任务列表", test_list_tasks)
    run_test("参数解释接口", test_parameter_explanations_api)
    run_test("熔断器生命周期API", test_circuit_breaker_lifecycle)
    run_test("优化任务列表", test_list_tasks)
    
    print(f"\n" + "=" * 70)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 70)
    
    if passed == total:
        print("\n所有 Flask 功能测试通过! [OK]")
        return True
    else:
        print(f"\n{total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    success = test_flask_app()
    sys.exit(0 if success else 1)
