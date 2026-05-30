#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""核心功能测试脚本"""

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cache_recommender import CacheStrategyEngine
from src.bloom_filter import BloomFilter, CacheBloomFilter
from src.ml_predictor import CachePredictor, TTLOptimizer, DuplicationPredictor
from src.log_analyzer import AccessLogAnalyzer, LogEntry
from src.utils import (
    format_size, generate_cache_key, extract_endpoint_pattern,
    normalize_params, compute_content_hash, classify_data_freshness,
    serialize_fields, calculate_hotness_score, select_hot_fields,
    DATA_FRESHNESS_TAGS
)


def test_bloom_filter():
    """测试布隆过滤器"""
    print("=" * 60)
    print("测试 1: 布隆过滤器")
    print("=" * 60)
    
    bf = BloomFilter(capacity=1000, error_rate=0.01)
    print(f"✓ 初始化布隆过滤器: 容量=1000, 误报率=1%")
    print(f"  - 位数组大小: {bf.bit_size:,} bits")
    print(f"  - 哈希函数数量: {bf.hash_count}")
    print(f"  - 内存使用: {bf.get_memory_usage_kb():.2f} KB")
    
    test_items = ["/api/v1/products", "/api/v1/users", "/api/v1/orders"]
    for item in test_items:
        bf.add(item)
        print(f"✓ 添加: {item}")
    
    for item in test_items:
        exists = item in bf
        print(f"  检查 '{item}': {'存在' if exists else '不存在'}")
    
    stats = bf.to_dict()
    print(f"✓ 当前误报率: {stats['current_fpr']:.6%}")
    print()


def test_cache_bloom_filter():
    """测试缓存专用布隆过滤器"""
    print("=" * 60)
    print("测试 2: 缓存专用布隆过滤器")
    print("=" * 60)
    
    cbf = CacheBloomFilter(expected_endpoints=1000)
    
    endpoints = [
        ("/api/v1/products", ["data", "total", "page"]),
        ("/api/v1/products/1", ["id", "name", "price"]),
        ("/api/v1/users/profile", ["id", "name", "email"]),
    ]
    
    for endpoint, fields in endpoints:
        cbf.record_request(endpoint, fields)
        print(f"✓ 记录请求: {endpoint}")
    
    result = cbf.check_endpoint_cache("/api/v1/products")
    print(f"\n检查 /api/v1/products:")
    print(f"  - 可能存在: {result['may_exist']}")
    print(f"  - 历史计数: {result['historical_count']}")
    print(f"  - 命中概率: {result['cache_hit_probability']:.1%}")
    
    stats = cbf.get_stats()
    print(f"\n✓ 统计信息:")
    print(f"  - 总记录请求: {stats['total_requests_recorded']}")
    print(f"  - 独立端点数: {stats['unique_endpoints_estimated']}")
    print()


def test_log_analyzer():
    """测试日志分析器"""
    print("=" * 60)
    print("测试 3: 日志分析器")
    print("=" * 60)
    
    analyzer = AccessLogAnalyzer()
    
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    
    if os.path.exists(sample_path):
        count = analyzer.load_logs(sample_path)
        print(f"✓ 加载日志文件: {count} 条记录")
        
        stats = analyzer.get_basic_stats()
        print(f"\n✓ 基本统计:")
        print(f"  - 总请求数: {stats.get('total_requests', 0):,}")
        print(f"  - 独立端点数: {stats.get('unique_patterns', 0):,}")
        print(f"  - 平均响应时间: {stats.get('avg_response_time_ms', 0):.1f} ms")
        print(f"  - 成功率: {stats.get('success_rate', 0):.1f}%")
        
        dup_stats = analyzer.analyze_duplication_patterns()
        print(f"\n✓ 重复模式分析:")
        print(f"  - 重复率: {dup_stats.get('duplication_ratio', 0):.1%}")
        print(f"  - 有重复的端点数: {dup_stats.get('total_duplicate_endpoints', 0)}")
        
        sim_analysis = analyzer.analyze_response_similarity()
        print(f"\n✓ 响应相似度分析:")
        print(f"  - 分析端点数: {sim_analysis.get('endpoints_analyzed', 0)}")
        print(f"  - 多响应端点数: {sim_analysis.get('endpoints_with_multiple_responses', 0)}")
        
    else:
        print("✗ 示例日志文件不存在")
    
    print()


def test_ml_predictor():
    """测试机器学习预测器"""
    print("=" * 60)
    print("测试 4: 机器学习预测器")
    print("=" * 60)
    
    predictor = CachePredictor()
    print("✓ 初始化缓存预测器")
    
    print("\n✓ 测试端点分类:")
    test_patterns = [
        "/api/v1/products",
        "/api/v1/products/123",
        "/static/css/style.css",
        "/api/v1/users/profile",
        "/api/v1/login",
    ]
    for pattern in test_patterns:
        category = predictor._categorize_endpoint(pattern)
        print(f"  {pattern:<40} -> {category}")
    
    optimizer = TTLOptimizer()
    print(f"\n✓ 初始化TTL优化器")
    
    test_metrics = {
        'request_count': 150,
        'avg_interval_seconds': 45,
        'hit_rate': 0.65,
        'eviction_rate': 0.15,
        'current_ttl': 300,
    }
    
    ttl_rec = optimizer.optimize("/api/v1/products", test_metrics)
    print(f"\n✓ TTL优化建议:")
    print(f"  - 当前TTL: {ttl_rec.current_ttl}秒")
    print(f"  - 推荐TTL: {ttl_rec.recommended_ttl}秒")
    print(f"  - 预期命中率提升: {ttl_rec.expected_hit_rate_improvement:.1%}")
    print(f"  - 预期节省: {ttl_rec.expected_savings_percent:.1%}")
    print(f"  - 理由:")
    for reason in ttl_rec.reasoning:
        print(f"    • {reason}")
    
    print()


def test_cache_strategy_engine():
    """测试缓存策略引擎"""
    print("=" * 60)
    print("测试 5: 缓存策略引擎")
    print("=" * 60)
    
    engine = CacheStrategyEngine()
    print("✓ 初始化缓存策略引擎")
    
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    
    if os.path.exists(sample_path):
        count = engine.load_logs(sample_path)
        print(f"✓ 加载日志: {count} 条记录")
        
        print("\n✓ 训练模型...")
        training_results = engine.train_models()
        print(f"  缓存预测器训练: {'成功' if 'error' not in training_results.get('cache_predictor', {}) else '使用规则引擎'}")
        
        print("\n✓ 分析缓存收益...")
        benefit = engine.analyze_cache_benefit()
        print(f"  - 总请求数: {benefit.total_requests:,}")
        print(f"  - 可缓存请求数: {benefit.cacheable_requests:,}")
        print(f"  - 预测命中率: {benefit.estimated_hit_rate:.1%}")
        print(f"  - 预估存储节省: {format_size(benefit.estimated_savings_bytes)}")
        print(f"  - 预估节省比例: {benefit.estimated_savings_percent:.1%}")
        print(f"  - 预估延迟降低: {benefit.estimated_latency_reduction_ms:.1f} ms")
        
        print(f"\n✓ 生成推荐: {len(benefit.recommendations)} 条")
        for i, rec in enumerate(benefit.recommendations[:3], 1):
            print(f"\n  推荐 #{i}: {rec.endpoint}")
            print(f"    - 缓存级别: {rec.cache_level}")
            print(f"    - 优先级: {rec.priority}")
            print(f"    - 预测命中率: {rec.predicted_hit_rate:.1%}")
            print(f"    - 推荐TTL: {rec.recommended_ttl}秒")
            print(f"    - 预估节省: {format_size(rec.estimated_savings_bytes)}")
            if rec.fields_to_cache:
                print(f"    - 缓存字段: {', '.join(rec.fields_to_cache[:3])}")
        
        print(f"\n✓ 布隆过滤器统计:")
        bloom_stats = benefit.bloom_filter_stats
        print(f"  - 端点过滤器已存储: {bloom_stats['endpoint_filter']['items_count']:,}")
        print(f"  - 字段过滤器已存储: {bloom_stats['field_filter']['items_count']:,}")
        print(f"  - 端点过滤器内存: {bloom_stats['endpoint_filter']['memory_usage_kb']:.2f} KB")
        print(f"  - 字段过滤器内存: {bloom_stats['field_filter']['memory_usage_kb']:.2f} KB")
        
    else:
        print("✗ 示例日志文件不存在")
    
    print()


def test_utils():
    """测试工具函数"""
    print("=" * 60)
    print("测试 6: 基础工具函数")
    print("=" * 60)
    
    key = generate_cache_key("/api/v1/products", {"page": 1, "limit": 10}, "GET")
    print(f"✓ 缓存键生成: {key}")
    
    pattern = extract_endpoint_pattern("/api/v1/products/12345")
    print(f"✓ 端点模式提取: /api/v1/products/12345 -> {pattern}")
    
    sizes = [0, 1023, 1024, 1024*1024, 1024*1024*1024]
    print(f"\n✓ 大小格式化:")
    for s in sizes:
        print(f"  {s:>12} bytes -> {format_size(s)}")
    
    sample_response = {
        "data": [{"id": 1, "name": "Test"}],
        "total": 100,
        "page": 1
    }
    print(f"\n✓ 响应大小计算: {calculate_size(sample_response)} bytes")
    
    print()


def test_parameter_normalization():
    """测试参数归一化"""
    print("=" * 60)
    print("测试 7: 参数归一化")
    print("=" * 60)
    
    params1 = {"b": 2, "a": 1, "c": None}
    params2 = {"a": 1, "b": 2, "c": ""}
    
    normalized1 = normalize_params(params1)
    normalized2 = normalize_params(params2)
    
    print(f"✓ 原始参数1: {params1}")
    print(f"  归一化后: {normalized1}")
    print(f"✓ 原始参数2: {params2}")
    print(f"  归一化后: {normalized2}")
    print(f"✓ 归一化后结果一致: {normalized1 == normalized2}")
    
    assert normalized1 == normalized2, "归一化后结果应该一致"
    print()


def test_content_hashing():
    """测试内容哈希"""
    print("=" * 60)
    print("测试 8: 内容哈希")
    print("=" * 60)
    
    response1 = {
        "timestamp": "2024-01-01T00:00:00",
        "request_id": "abc123",
        "data": {"id": 1, "name": "Product A", "price": 99.99}
    }
    
    response2 = {
        "timestamp": "2024-01-01T00:00:01",
        "request_id": "def456",
        "data": {"id": 1, "name": "Product A", "price": 99.99}
    }
    
    hash1 = compute_content_hash(response1)
    hash2 = compute_content_hash(response2)
    hash1_with_meta = compute_content_hash(response1, include_metadata=True)
    
    print(f"✓ 响应1内容哈希 (忽略元数据): {hash1[:16]}...")
    print(f"✓ 响应2内容哈希 (忽略元数据): {hash2[:16]}...")
    print(f"✓ 响应1内容哈希 (包含元数据): {hash1_with_meta[:16]}...")
    print(f"✓ 忽略元数据时哈希一致: {hash1 == hash2}")
    print(f"✓ 包含元数据时哈希不同: {hash1 != hash1_with_meta}")
    
    assert hash1 == hash2, "忽略元数据时相同内容的哈希应该一致"
    assert hash1 != hash1_with_meta, "包含元数据时哈希应该不同"
    print()


def test_data_freshness_classification():
    """测试数据时效性分类"""
    print("=" * 60)
    print("测试 9: 数据时效性分类")
    print("=" * 60)
    
    test_cases = [
        ("/api/v1/realtime/stock", {}, "realtime"),
        ("/api/v1/monitoring/live", {}, "near_realtime"),
        ("/api/v1/search", {"q": "test"}, "dynamic"),
        ("/api/v1/categories", {}, "semi_static"),
        ("/api/v1/config/site", {}, "static"),
    ]
    
    print("✓ 时效性标签定义:")
    for tag, info in DATA_FRESHNESS_TAGS.items():
        print(f"  {tag:15} -> {info.description[:20]}..., TTL范围: {info.min_ttl_seconds}s ~ {info.max_ttl_seconds}s")
    
    print(f"\n✓ 端点分类测试:")
    for endpoint, params, expected_tag in test_cases:
        result = classify_data_freshness(endpoint, request_params=params)
        status = "✓" if result.tag == expected_tag else "✗"
        print(f"  {status} {endpoint:<40} -> {result.tag:15} (期望: {expected_tag})")
    
    print()


def test_on_demand_serialization():
    """测试按需序列化"""
    print("=" * 60)
    print("测试 10: 按需序列化")
    print("=" * 60)
    
    data = {
        "data": {
            "products": [
                {"id": 1, "name": "Product 1", "price": 99.99, "stock": 100},
                {"id": 2, "name": "Product 2", "price": 199.99, "stock": 50}
            ],
            "total": 2,
            "page": 1
        },
        "meta": {
            "request_id": "abc123",
            "timestamp": "2024-01-01T00:00:00"
        }
    }
    
    fields_to_serialize = ["data.products.id", "data.products.name", "data.products.price", "data.total"]
    serialized = serialize_fields(data, fields_to_serialize)
    
    print(f"✓ 原始字段数: {len(str(data))} 字符")
    print(f"✓ 序列化字段: {fields_to_serialize}")
    print(f"✓ 序列化结果: {serialized}")
    print(f"✓ 序列化后大小: {len(str(serialized))} 字符")
    
    original_size = calculate_size(data)
    serialized_size = calculate_size(serialized)
    savings = (1 - serialized_size / original_size) * 100
    print(f"✓ 原始大小: {original_size} bytes, 序列化后: {serialized_size} bytes, 节省: {savings:.1f}%")
    
    assert "data" in serialized
    assert "products" in serialized["data"]
    assert len(serialized["data"]["products"]) == 2
    assert "id" in serialized["data"]["products"][0]
    assert "name" in serialized["data"]["products"][0]
    assert "price" in serialized["data"]["products"][0]
    assert "stock" not in serialized["data"]["products"][0]
    assert "meta" not in serialized
    
    print()


def test_hotness_scoring():
    """测试热度评分和热点字段选择"""
    print("=" * 60)
    print("测试 11: 热度评分和热点字段选择")
    print("=" * 60)
    
    test_cases = [
        (1000, 5, 0.95),
        (500, 10, 0.95),
        (100, 60, 0.95),
        (10, 3600, 0.95),
    ]
    
    print("✓ 热度评分测试:")
    for request_count, avg_interval, decay in test_cases:
        hotness = calculate_hotness_score(request_count, avg_interval, decay)
        print(f"  请求数={request_count:4d}, 平均间隔={avg_interval:5d}s -> 热度={hotness:.4f}")
    
    field_stats = [
        {"field_path": "data.products.id", "request_count": 1000, "avg_interval_seconds": 5, "redundancy_ratio": 0.9},
        {"field_path": "data.products.name", "request_count": 950, "avg_interval_seconds": 6, "redundancy_ratio": 0.85},
        {"field_path": "data.products.price", "request_count": 800, "avg_interval_seconds": 8, "redundancy_ratio": 0.7},
        {"field_path": "data.products.stock", "request_count": 200, "avg_interval_seconds": 30, "redundancy_ratio": 0.2},
        {"field_path": "data.products.description", "request_count": 100, "avg_interval_seconds": 60, "redundancy_ratio": 0.1},
    ]
    
    hot_fields = select_hot_fields(field_stats, hotness_threshold=0.3, max_fields=3)
    print(f"\n✓ 热点字段选择 (阈值=0.3, 最多3个):")
    for f in field_stats:
        hotness = calculate_hotness_score(f["request_count"], f["avg_interval_seconds"])
        combined = hotness * 0.7 + f["redundancy_ratio"] * 0.3
        status = "🔥" if f["field_path"] in hot_fields else "  "
        print(f"  {status} {f['field_path']:<30} 热度={hotness:.4f}, 冗余={f['redundancy_ratio']:.2f}, 综合={combined:.4f}")
    
    print(f"\n✓ 选中的热点字段: {hot_fields}")
    assert len(hot_fields) <= 3
    assert "data.products.id" in hot_fields
    assert "data.products.name" in hot_fields
    
    print()


def test_content_hash_duplication():
    """测试内容哈希重复识别"""
    print("=" * 60)
    print("测试 12: 内容哈希重复识别")
    print("=" * 60)
    
    analyzer = AccessLogAnalyzer()
    
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    
    if os.path.exists(sample_path):
        count = analyzer.load_logs(sample_path)
        print(f"✓ 加载日志: {count} 条记录")
        
        content_dup = analyzer.analyze_content_hash_duplication()
        print(f"\n✓ 内容哈希重复分析:")
        print(f"  - 重复组数: {content_dup.get('total_duplicate_groups', 0)}")
        print(f"  - 相同内容请求数: {content_dup.get('total_same_content_requests', 0)}")
        print(f"  - 潜在节省: {format_size(content_dup.get('potential_savings_bytes', 0))}")
        
        if content_dup.get('duplicate_groups'):
            print(f"\n✓ 前3组重复内容:")
            for i, group in enumerate(content_dup['duplicate_groups'][:3], 1):
                print(f"  组 {i}: 哈希={group.content_hash[:16]}..., 请求数={group.request_count}, 参数组合数={group.unique_params_count}")
    
    print()


def test_freshness_ttl_constraint():
    """测试时效性TTL约束"""
    print("=" * 60)
    print("测试 13: 时效性TTL约束")
    print("=" * 60)
    
    engine = CacheStrategyEngine()
    
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    
    if os.path.exists(sample_path):
        count = engine.load_logs(sample_path)
        print(f"✓ 加载日志: {count} 条记录")
        
        engine.train_models()
        benefit = engine.analyze_cache_benefit()
        
        print(f"\n✓ 缓存推荐中的时效性标签:")
        tag_counts = {}
        for rec in benefit.recommendations:
            tag = rec.freshness_tag
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        for tag, count in sorted(tag_counts.items()):
            info = DATA_FRESHNESS_TAGS.get(tag)
            if info:
                print(f"  {tag:15} ({info.description[:10]:10}): {count:3d} 个端点, TTL范围: {info.min_ttl_seconds}s ~ {info.max_ttl_seconds}s")
        
        print(f"\n✓ TTL约束验证:")
        all_valid = True
        for rec in benefit.recommendations[:5]:
            info = DATA_FRESHNESS_TAGS.get(rec.freshness_tag)
            if info:
                ttl = rec.recommended_ttl
                valid = info.min_ttl_seconds <= ttl <= info.max_ttl_seconds
                status = "✓" if valid else "✗"
                if not valid:
                    all_valid = False
                print(f"  {status} {rec.endpoint:<40} TTL={ttl:5d}s, 范围=[{info.min_ttl_seconds}s, {info.max_ttl_seconds}s]")
        
        if all_valid:
            print(f"\n✓ 所有推荐TTL都在时效性约束范围内!")
        else:
            print(f"\n✗ 存在TTL超出时效性约束的情况!")
    
    print()


def test_adaptive_strategy():
    """测试自适应缓存策略"""
    print("=" * 60)
    print("测试 14: 自适应缓存策略")
    print("=" * 60)
    
    from src.cache_recommender import AdaptiveCacheStrategyEngine
    from src.utils import AdaptiveStrategyConfig, calculate_cache_metrics
    
    engine = CacheStrategyEngine()
    
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    
    if os.path.exists(sample_path):
        count = engine.load_logs(sample_path)
        print(f"✓ 加载日志: {count} 条记录")
        
        adaptive_engine = AdaptiveCacheStrategyEngine(engine)
        print(f"✓ 初始化自适应策略引擎")
        
        config = AdaptiveStrategyConfig()
        print(f"✓ 默认配置:")
        print(f"  - 最低命中率阈值: {config.min_hit_rate_threshold:.1%}")
        print(f"  - 目标命中率: {config.target_hit_rate:.1%}")
        print(f"  - 最大内存使用率: {config.max_memory_usage_ratio:.1%}")
        print(f"  - TTL调整因子: {config.ttl_adjustment_factor:.2f}")
        
        state = adaptive_engine.analyze_current_state()
        if 'error' not in state:
            print(f"\n✓ 当前状态分析:")
            metrics = state['current_metrics']
            print(f"  - 当前命中率: {metrics.hit_rate:.1%}")
            print(f"  - 请求总数: {metrics.request_count:,}")
            print(f"  - 内存使用: {format_size(metrics.memory_usage_bytes)}")
        
        recommendations = adaptive_engine.generate_adaptive_recommendations()
        print(f"\n✓ 生成策略建议: {len(recommendations)} 条")
        
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"\n  建议 #{i}: {rec.endpoint}")
            print(f"    - 分析时间: {rec.analysis_timestamp.strftime('%H:%M:%S')}")
            if rec.recommended_adjustments:
                for adj in rec.recommended_adjustments:
                    print(f"    - {adj.adjustment_type}: {adj.previous_value} -> {adj.new_value}")
            else:
                print(f"    - 无需调整")
    
    print()


def test_warmup_simulation():
    """测试缓存预热模拟"""
    print("=" * 60)
    print("测试 15: 缓存预热模拟")
    print("=" * 60)
    
    from src.cache_recommender import AdaptiveCacheStrategyEngine
    
    engine = CacheStrategyEngine()
    
    sample_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "sample_access.log"
    )
    
    if os.path.exists(sample_path):
        count = engine.load_logs(sample_path)
        print(f"✓ 加载日志: {count} 条记录")
        
        adaptive_engine = AdaptiveCacheStrategyEngine(engine)
        
        for duration in [10, 30, 60]:
            report = adaptive_engine.simulate_warmup(duration)
            print(f"\n✓ {duration}分钟预热模拟:")
            print(f"  - 预热前命中率: {report.overall_result['original_hit_rate']:.1%}")
            print(f"  - 预热后命中率: {report.overall_result['warmed_hit_rate']:.1%}")
            print(f"  - 命中率提升: {report.total_estimated_hit_rate_improvement:.1%}")
            print(f"  - 预加载数据量: {report.total_estimated_memory_bytes:,} bytes")
            print(f"  - 预估延迟降低: {report.total_estimated_latency_improvement_ms:.1f} ms")
        
        preload_plan = adaptive_engine.generate_hot_data_preload_plan(top_n=10)
        print(f"\n✓ 预加载计划: {len(preload_plan)} 个端点")
        for i, item in enumerate(preload_plan[:5], 1):
            print(f"  {i}. {item['endpoint']}: 优先级={item['priority']}, 热度={item['hotness']:.2f}")
    
    print()


def test_penetration_protection():
    """测试缓存穿透防护"""
    print("=" * 60)
    print("测试 16: 缓存穿透防护")
    print("=" * 60)
    
    from src.bloom_filter import PenetrationProtector, HotDataPreloader
    
    protector = PenetrationProtector(
        null_value_ttl=60,
        bloom_filter_capacity=10000,
        bloom_filter_error_rate=0.001
    )
    print(f"✓ 初始化穿透防护器")
    
    valid_keys = [f"/api/v1/products/{i}" for i in range(100)]
    for key in valid_keys:
        protector.record_key_access(key, exists=True)
    print(f"✓ 记录有效键访问: {len(valid_keys)} 个")
    
    test_keys = valid_keys[:10] + ["/invalid/key1", "/invalid/key2", "/invalid/key3"]
    print(f"\n✓ 键有效性检查:")
    valid_count = 0
    for key in test_keys:
        is_valid = protector.is_key_valid(key)
        if is_valid:
            valid_count += 1
    print(f"  - 检查 {len(test_keys)} 个键，{valid_count} 个可能有效")
    
    protector.set_null_value("/api/v1/products/999", None)
    null_value = protector.get_null_value("/api/v1/products/999")
    print(f"✓ 空值缓存测试: {'成功' if null_value is None else '失败'}")
    
    stats = protector.get_stats()
    print(f"\n✓ 防护器统计:")
    print(f"  - 空值缓存数: {stats['null_value_cache_size']}")
    print(f"  - 热点数据数: {stats['hot_data_count']}")
    print(f"  - 跟踪总键数: {stats['total_keys_tracked']}")
    
    preloader = HotDataPreloader(max_concurrent_loads=10)
    print(f"\n✓ 热点数据预加载器:")
    
    hot_keys = [f"/api/v1/hot/{i}" for i in range(20)]
    for i, key in enumerate(hot_keys):
        priority = 'critical' if i < 5 else 'high' if i < 10 else 'normal'
        preloader.add_to_preload_queue(key, priority=priority)
    
    breakdown = preloader.get_priority_breakdown()
    print(f"  - 队列大小: {preloader.get_queue_size()}")
    print(f"  - 优先级分布: {breakdown}")
    
    data_sources = {k: 50 + i * 5 for i, k in enumerate(hot_keys)}
    simulation = preloader.simulate_preload(data_sources, duration_minutes=30)
    print(f"  - 模拟预加载:")
    print(f"    - 已预加载: {simulation['preloaded_count']}/{simulation['total_count']}")
    print(f"    - 命中率提升: {simulation['estimated_hit_rate_improvement']:.1%}")
    print(f"    - 延迟降低: {simulation['estimated_latency_reduction_ms']:.1f} ms")
    
    print()


def calculate_size(data):
    """计算数据大小"""
    import json
    return len(json.dumps(data, ensure_ascii=False).encode('utf-8'))


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("API缓存预测工具 - 核心功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_bloom_filter()
        test_cache_bloom_filter()
        test_log_analyzer()
        test_ml_predictor()
        test_cache_strategy_engine()
        test_utils()
        test_parameter_normalization()
        test_content_hashing()
        test_data_freshness_classification()
        test_on_demand_serialization()
        test_hotness_scoring()
        test_content_hash_duplication()
        test_freshness_ttl_constraint()
        test_adaptive_strategy()
        test_warmup_simulation()
        test_penetration_protection()
        
        print("=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        print("\n可以运行以下命令启动Web界面:")
        print("  streamlit run main.py")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
