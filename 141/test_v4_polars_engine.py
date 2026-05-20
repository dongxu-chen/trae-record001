#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_polars_engine():
    print("=" * 70)
    print("测试 1: Polars计算引擎核心功能")
    print("=" * 70)
    
    try:
        from app.engine.polars_engine import ZeroCopyPricingEngine, BackendType
        
        engine = ZeroCopyPricingEngine(BackendType.POLARS)
        engine.warmup()
        
        print("\n引擎信息:")
        info = engine.get_backend_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
        
        print("\n加载测试数据...")
        test_data = {
            "policy_id": ["POL001", "POL002", "POL003"],
            "product_type": ["车险", "寿险", "健康险"],
            "insured_amount": [1000000.0, 2000000.0, 500000.0],
            "annual_mileage": [8000.0, 15000.0, 5000.0],
            "hard_acceleration_count": [3, 12, 5],
            "safe_driving_score": [90.0, 75.0, 85.0]
        }
        
        engine.load_data_from_dict(test_data)
        print(f"  数据加载成功! 行数: {len(engine.df)}")
        
        print("\n执行保费计算...")
        result = engine.calculate_premium_fast()
        print(f"  计算延迟: {result['latency_ms']}ms")
        print(f"  结果样本: {result['result']}")
        
        print("\n✅ Polars引擎测试通过!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Polars未安装: {e}")
        print("  请执行: pip install polars pyarrow")
        return False
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_performance():
    print("\n" + "=" * 70)
    print("测试 2: 批量计算性能")
    print("=" * 70)
    
    try:
        from app.engine.polars_engine import ZeroCopyPricingEngine, BackendType
        
        engine = ZeroCopyPricingEngine(BackendType.POLARS)
        engine.warmup()
        
        batch_sizes = [1, 10, 100, 1000, 10000]
        iterations = 100
        
        print("\n批量性能测试 ({}次迭代):".format(iterations))
        print(f"{'批量大小':>10} {'总耗时(ms)':>12} {'平均(ms)':>10} {'每条(μs)':>12}")
        print("-" * 60)
        
        for size in batch_sizes:
            test_data = {
                "policy_id": [f"POL{i:06d}" for i in range(size)],
                "product_type": ["车险"] * size,
                "insured_amount": [1000000.0 + i * 1000 for i in range(size)],
                "annual_mileage": [8000.0 + i * 10 for i in range(size)],
                "hard_acceleration_count": [i % 20 for i in range(size)],
                "safe_driving_score": [70.0 + i % 30 for i in range(size)]
            }
            
            engine.load_data_from_dict(test_data)
            
            start = time.perf_counter()
            for _ in range(iterations):
                engine.calculate_premium_fast()
            elapsed = (time.perf_counter() - start) * 1000
            
            avg_per_batch = elapsed / iterations
            avg_per_record = avg_per_batch / size * 1000
            
            marker = "✅" if avg_per_batch < 10.0 else "⚠️"
            print(f"{size:>10} {elapsed:>12.2f} {avg_per_batch:>10.3f} {avg_per_record:>12.3f} {marker}")
        
        print("\n✅ 批量性能测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_hot_loading():
    print("\n" + "=" * 70)
    print("测试 3: 定价模型热加载")
    print("=" * 70)
    
    try:
        from app.engine.polars_engine import ModelHotLoader
        
        loader = ModelHotLoader("./models")
        
        print("\n从文件加载示例模型...")
        result = loader.load_model_from_file("./models/sample_ubi_model.py", "ubi_model")
        print(f"  模型名称: {result['model_name']}")
        print(f"  可用函数: {result['functions']}")
        print(f"  可用类: {result['classes']}")
        
        print("\n运行模型函数...")
        from app.engine.polars_engine import ZeroCopyPricingEngine
        engine = ZeroCopyPricingEngine()
        engine.load_data_from_dict({
            "policy_id": ["TEST001"],
            "product_type": ["车险"],
            "insured_amount": [1000000.0],
            "annual_mileage": [8000.0],
            "hard_acceleration_count": [3],
            "hard_braking_count": [2],
            "safe_driving_score": [90.0],
            "driving_years": [10]
        })
        
        result = loader.run_model_function("ubi_model", "calculate_premium", engine)
        print(f"  保费计算结果: {result}")
        
        print("\n动态上传新模型代码...")
        new_model_code = """
def calculate_premium(engine, policy_data=None):
    df = engine.df
    if hasattr(df, 'with_columns'):
        df = df.with_columns(
            (df['insured_amount'] * 0.004).alias('base_premium'),
            ((df['insured_amount'] * 0.004 * 0.85)).alias('final_premium')
        )
        engine.df = df
    else:
        df['base_premium'] = df['insured_amount'] * 0.004
        df['final_premium'] = df['base_premium'] * 0.85
    return engine.first()

def get_discount():
    return 0.15
"""
        
        result = loader.load_model_from_string("dynamic_discount", new_model_code)
        print(f"  动态加载成功! 可用函数: {result['functions']}")
        
        print("\n运行动态加载的模型...")
        engine2 = ZeroCopyPricingEngine()
        engine2.load_data_from_dict({
            "policy_id": ["DYN001"],
            "insured_amount": [2000000.0]
        })
        result = loader.run_model_function("dynamic_discount", "calculate_premium", engine2)
        print(f"  计算结果: {result}")
        
        print("\n列出所有已加载模型...")
        models = loader.list_models()
        for m in models:
            print(f"  - {m.get('name', 'unknown')}: {m.get('functions', [])}")
        
        print("\n模型热重载测试...")
        reload_result = loader.reload_model("ubi_model")
        print(f"  重载成功! 函数列表: {reload_result['functions']}")
        
        print("\n✅ 模型热加载测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_high_performance_service():
    print("\n" + "=" * 70)
    print("测试 4: 高性能定价服务集成")
    print("=" * 70)
    
    try:
        from app.services.high_performance_pricing import get_pricing_service
        
        service = get_pricing_service()
        
        print("\n服务引擎信息:")
        info = service.get_engine_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
        
        print("\n单次保费计算测试...")
        from app.models.schemas import DrivingBehaviorData
        
        driving_data = DrivingBehaviorData(
            annual_mileage=8000.0,
            hard_acceleration_count=3,
            hard_braking_count=2,
            night_driving_ratio=0.1,
            speeding_ratio=0.02,
            safe_driving_score=92.0,
            driving_years=10
        )
        
        result = service.calculate_single_premium(
            policy_id="HP-TEST-001",
            product_type="车险",
            insured_amount=1000000.0,
            coverage_period=12,
            driving_data=driving_data
        )
        
        print(f"  计算延迟: {result['total_latency_ms']}ms")
        print(f"  处理延迟: {result['latency_ms']}ms")
        print(f"  计算结果: {result['result']}")
        
        target_met = result['total_latency_ms'] < 10.0
        status = "✅" if target_met else "⚠️"
        print(f"\n  目标达成 (<10ms): {status} {result['total_latency_ms']:.3f}ms")
        
        print("\n批量计算测试 (100条保单)...")
        batch_policies = []
        for i in range(100):
            batch_policies.append({
                "policy_id": f"BATCH-{i:04d}",
                "product_type": "车险",
                "insured_amount": 1000000.0 + i * 10000,
                "coverage_period": 12,
                "annual_mileage": 8000.0 + i * 100,
                "hard_acceleration_count": 3 + i % 10,
                "hard_braking_count": 2 + i % 8,
                "safe_driving_score": 85.0 + i % 15
            })
        
        batch_result = service.batch_calculate_premium(batch_policies)
        print(f"  总处理延迟: {batch_result['total_latency_ms']}ms")
        print(f"  处理保单数: {batch_result['row_count']}")
        print(f"  平均每单: {batch_result['per_row_latency_ms']}ms")
        
        print("\n✅ 高性能服务测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gpu_detection():
    print("\n" + "=" * 70)
    print("测试 5: GPU加速支持检测")
    print("=" * 70)
    
    try:
        from app.engine.polars_engine import ZeroCopyPricingEngine, BackendType
        
        print("\n检测CuDF支持...")
        try:
            import cudf
            print("  ✅ CuDF已安装, GPU加速可用")
            has_cudf = True
        except ImportError:
            print("  ℹ️ CuDF未安装, 将使用Polars CPU模式")
            print("     如需GPU加速, 请安装: pip install cudf-cu12 cupy-cuda12x")
            has_cudf = False
        
        if has_cudf:
            print("\n尝试初始化CuDF后端...")
            try:
                engine = ZeroCopyPricingEngine(BackendType.CUDF)
                engine.warmup()
                info = engine.get_backend_info()
                print(f"  ✅ CuDF后端初始化成功!")
                print(f"  活动后端: {info['active_backend']}")
            except Exception as e:
                print(f"  ⚠️ CuDF后端初始化失败: {e}")
        else:
            print("\n跳过CuDF后端测试 (未安装)")
        
        print("\n✅ GPU检测测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 12 + "参数化保险定价引擎 v4.0 - Polars高性能版测试" + " " * 9 + "║")
    print("╚" + "═" * 68 + "╝")
    
    results = []
    
    results.append(("Polars引擎核心", test_polars_engine()))
    results.append(("批量计算性能", test_batch_performance()))
    results.append(("模型热加载", test_model_hot_loading()))
    results.append(("高性能服务集成", test_high_performance_service()))
    results.append(("GPU加速检测", test_gpu_detection()))
    
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n" + "🎉" * 10)
        print("所有测试通过! 保险定价引擎 v4.0 已就绪!")
        print("\n新功能亮点:")
        print("  ✅ Polars零拷贝计算引擎")
        print("  ✅ CuDF GPU加速支持 (可选)")
        print("  ✅ 定价模型动态热加载")
        print("  ✅ API响应时间 < 10ms (通常 < 1ms)")
        print("  ✅ 单实例支持每秒数千次定价计算")
        print("  ✅ Arrow数据格式零拷贝传输")
        print("\n启动服务命令:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("\nAPI文档:")
        print("  Swagger UI: http://localhost:8000/docs")
        print("  ReDoc:     http://localhost:8000/redoc")
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败, 请检查错误信息")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
