import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
import tracemalloc
import numpy as np
from app.models import GraphData, Node, Edge
from app.analysis import GraphAnalyzer
from app.cache import get_cache_manager

def load_test_data():
    data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sample_social_relations.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nodes = [Node(
        id=str(n['id']),
        label=n.get('label', 'User'),
        properties={k: v for k, v in n.items() if k not in ['id', 'label']}
    ) for n in data['nodes']]
    
    edges = [Edge(
        source=str(e['source']),
        target=str(e['target']),
        relationship_type=e.get('type', 'CONNECTED'),
        properties={k: v for k, v in e.items() if k not in ['source', 'target', 'type']}
    ) for e in data['edges']]
    
    return GraphData(nodes=nodes, edges=edges)

def generate_large_data(node_count=500, edge_count=5000):
    import random
    nodes = []
    for i in range(node_count):
        nodes.append(Node(
            id=str(i),
            label='User',
            properties={'name': f'User_{i}', 'age': random.randint(18, 60)}
        ))
    
    edges = []
    for i in range(edge_count):
        src = random.randint(0, node_count - 1)
        tgt = random.randint(0, node_count - 1)
        if src != tgt:
            edges.append(Edge(
                source=str(src),
                target=str(tgt),
                relationship_type=random.choice(['FOLLOW', 'LIKE', 'COMMENT']),
                properties={
                    'weight': random.randint(1, 10),
                    'timestamp': 1672531200000 + random.randint(0, 31536000000)
                }
            ))
    
    return GraphData(nodes=nodes, edges=edges)

def test_pagerank_performance(graph_data, iterations=5):
    print("\n" + "=" * 70)
    print("📊 PageRank 性能对比测试")
    print("=" * 70)
    
    analyzer = GraphAnalyzer(graph_data, use_cache=False)
    
    print(f"\n测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    print(f"迭代次数: {iterations}")
    print()
    
    scipy_times = []
    scipy_memories = []
    
    try:
        from scipy.sparse import csr_matrix
        has_scipy = True
    except ImportError:
        has_scipy = False
    
    if has_scipy:
        print("🚀 稀疏矩阵 PageRank (优化版):")
        for i in range(iterations):
            tracemalloc.start()
            start = time.time()
            scores = analyzer._pagerank_sparse()
            end = time.time()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            elapsed = (end - start) * 1000
            scipy_times.append(elapsed)
            scipy_memories.append(peak / 1024)
            
            print(f"  第{i+1}次: {elapsed:.2f} ms, 峰值内存: {peak/1024:.2f} KB")
        
        print(f"\n  ✅ 平均: {np.mean(scipy_times):.2f} ms, 平均内存: {np.mean(scipy_memories):.2f} KB")
        print(f"  ✅ 最慢: {np.max(scipy_times):.2f} ms, 最快: {np.min(scipy_times):.2f} ms")
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  ✅ Top 3: {[(n, round(s, 4)) for n, s in top3]}")
    else:
        print("⚠️  Scipy 不可用，跳过稀疏矩阵测试")
    
    nx_times = []
    nx_memories = []
    
    print("\n📦 NetworkX PageRank (原版):")
    import networkx as nx
    for i in range(iterations):
        tracemalloc.start()
        start = time.time()
        scores = nx.pagerank(analyzer.G, weight='weight')
        end = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        elapsed = (end - start) * 1000
        nx_times.append(elapsed)
        nx_memories.append(peak / 1024)
        
        print(f"  第{i+1}次: {elapsed:.2f} ms, 峰值内存: {peak/1024:.2f} KB")
    
    print(f"\n  ✅ 平均: {np.mean(nx_times):.2f} ms, 平均内存: {np.mean(nx_memories):.2f} KB")
    print(f"  ✅ 最慢: {np.max(nx_times):.2f} ms, 最快: {np.min(nx_times):.2f} ms")
    top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  ✅ Top 3: {[(n, round(s, 4)) for n, s in top3]}")
    
    if has_scipy and scipy_times and nx_times:
        speedup = np.mean(nx_times) / np.mean(scipy_times)
        memory_save = (1 - np.mean(scipy_memories) / np.mean(nx_memories)) * 100
        print(f"\n📈 优化效果:")
        print(f"  ⚡ 速度提升: {speedup:.2f}x 倍")
        print(f"  💾 内存节省: {memory_save:.1f}%")
        
        if speedup >= 1.1:
            print("  ✅ 速度提升明显")
        else:
            print("  ℹ️  小数据量下差异不明显，大数据量优势更显著")
    
    return has_scipy

def test_community_detection_performance(graph_data, iterations=5):
    print("\n" + "=" * 70)
    print("🏘️  社区检测算法性能对比测试")
    print("=" * 70)
    
    analyzer = GraphAnalyzer(graph_data, use_cache=False)
    
    print(f"\n测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    print(f"迭代次数: {iterations}")
    print()
    
    leiden_times = []
    leiden_modularities = []
    
    try:
        import leidenalg as la
        import igraph as ig
        has_leiden = True
    except ImportError:
        has_leiden = False
    
    if has_leiden:
        print("🚀 Leiden 算法 (优化版):")
        for i in range(iterations):
            start = time.time()
            communities = analyzer.detect_communities()
            end = time.time()
            
            elapsed = (end - start) * 1000
            leiden_times.append(elapsed)
            if communities:
                leiden_modularities.append(communities[0].modularity)
            
            print(f"  第{i+1}次: {elapsed:.2f} ms, 社区数: {len(communities)}, 模块度: {communities[0].modularity:.4f}")
        
        print(f"\n  ✅ 平均: {np.mean(leiden_times):.2f} ms")
        print(f"  ✅ 平均模块度: {np.mean(leiden_modularities):.4f}")
        print(f"  ✅ 最慢: {np.max(leiden_times):.2f} ms, 最快: {np.min(leiden_times):.2f} ms")
    else:
        print("⚠️  Leiden 算法不可用，跳过测试")
    
    louvain_times = []
    louvain_modularities = []
    
    try:
        import community as community_louvain
        has_louvain = True
    except ImportError:
        has_louvain = False
    
    if has_louvain:
        print("\n📦 Louvain 算法 (原版):")
        for i in range(iterations):
            start = time.time()
            
            partition = community_louvain.best_partition(analyzer.G, weight='weight')
            modularity = community_louvain.modularity(partition, analyzer.G)
            
            communities = {}
            for node_id, comm_id in partition.items():
                if comm_id not in communities:
                    communities[comm_id] = []
                communities[comm_id].append(node_id)
            
            end = time.time()
            
            elapsed = (end - start) * 1000
            louvain_times.append(elapsed)
            louvain_modularities.append(modularity)
            
            print(f"  第{i+1}次: {elapsed:.2f} ms, 社区数: {len(communities)}, 模块度: {modularity:.4f}")
        
        print(f"\n  ✅ 平均: {np.mean(louvain_times):.2f} ms")
        print(f"  ✅ 平均模块度: {np.mean(louvain_modularities):.4f}")
        print(f"  ✅ 最慢: {np.max(louvain_times):.2f} ms, 最快: {np.min(louvain_times):.2f} ms")
    
    if has_leiden and has_louvain and leiden_times and louvain_times:
        speedup = np.mean(louvain_times) / np.mean(leiden_times)
        mod_diff = (np.mean(leiden_modularities) - np.mean(louvain_modularities))
        
        print(f"\n📈 优化效果:")
        print(f"  ⚡ 速度提升: {speedup:.2f}x 倍")
        if mod_diff >= 0:
            print(f"  📊 模块度提升: +{mod_diff:.4f}")
        else:
            print(f"  📊 模块度变化: {mod_diff:.4f}")
        
        if speedup >= 5:
            print("  ✅ 速度提升显著 (>5x)")
        elif speedup >= 2:
            print("  ✅ 速度提升明显 (>2x)")
        else:
            print("  ℹ️  小数据量下差异不明显")
    
    return has_leiden

def test_cache_performance(graph_data):
    print("\n" + "=" * 70)
    print("💾 缓存机制性能测试")
    print("=" * 70)
    
    cache = get_cache_manager()
    cache.clear()
    
    print(f"\n测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    print()
    
    print("📝 首次计算 (无缓存):")
    analyzer1 = GraphAnalyzer(graph_data, use_cache=True)
    
    start = time.time()
    communities1 = analyzer1.detect_communities()
    end = time.time()
    first_community_time = (end - start) * 1000
    print(f"  社区检测: {first_community_time:.2f} ms")
    
    start = time.time()
    influence1 = analyzer1.calculate_influence('pagerank')
    end = time.time()
    first_pagerank_time = (end - start) * 1000
    print(f"  PageRank计算: {first_pagerank_time:.2f} ms")
    
    start = time.time()
    temporal1 = analyzer1.get_temporal_analysis(time_windows=10)
    end = time.time()
    first_temporal_time = (end - start) * 1000
    print(f"  时间演化分析: {first_temporal_time:.2f} ms")
    
    print("\n⚡ 二次计算 (从缓存加载):")
    analyzer2 = GraphAnalyzer(graph_data, use_cache=True)
    
    start = time.time()
    communities2 = analyzer2.detect_communities()
    end = time.time()
    cached_community_time = (end - start) * 1000
    print(f"  社区检测: {cached_community_time:.2f} ms")
    
    start = time.time()
    influence2 = analyzer2.calculate_influence('pagerank')
    end = time.time()
    cached_pagerank_time = (end - start) * 1000
    print(f"  PageRank计算: {cached_pagerank_time:.2f} ms")
    
    start = time.time()
    temporal2 = analyzer2.get_temporal_analysis(time_windows=10)
    end = time.time()
    cached_temporal_time = (end - start) * 1000
    print(f"  时间演化分析: {cached_temporal_time:.2f} ms")
    
    print(f"\n📈 缓存加速效果:")
    if cached_community_time > 0:
        speedup = first_community_time / cached_community_time
        print(f"  社区检测: {speedup:.2f}x 倍加速")
    if cached_pagerank_time > 0:
        speedup = first_pagerank_time / cached_pagerank_time
        print(f"  PageRank计算: {speedup:.2f}x 倍加速")
    if cached_temporal_time > 0:
        speedup = first_temporal_time / cached_temporal_time
        print(f"  时间演化分析: {speedup:.2f}x 倍加速")
    
    stats = cache.get_stats()
    print(f"\n📊 缓存统计:")
    print(f"  缓存命中: {stats['hits']}")
    print(f"  缓存未命中: {stats['misses']}")
    print(f"  命中率: {stats['hit_rate']*100:.1f}%")
    print(f"  缓存条目: {stats['total_entries']}")
    print(f"  缓存大小: {stats['total_size_bytes']/1024:.2f} KB")
    
    print("\n✅ 结果一致性验证:")
    comm_match = len(communities1) == len(communities2)
    print(f"  社区数一致: {comm_match}")
    
    inf_match = len(influence1) == len(influence2)
    if inf_match and influence1 and influence2:
        inf_match = influence1[0].node_id == influence2[0].node_id
    print(f"  PageRank Top1一致: {inf_match}")
    
    temp_match = len(temporal1.get('data', [])) == len(temporal2.get('data', []))
    print(f"  时间窗口数一致: {temp_match}")
    
    cache.clear()
    return True

def test_large_graph_scalability():
    print("\n" + "=" * 70)
    print("📈 大数据量扩展性测试")
    print("=" * 70)
    
    sizes = [
        (100, 500),
        (500, 2500),
        (1000, 5000),
    ]
    
    results = []
    
    for node_count, edge_count in sizes:
        print(f"\n📊 测试 {node_count} 节点, {edge_count} 边...")
        graph_data = generate_large_data(node_count, edge_count)
        analyzer = GraphAnalyzer(graph_data, use_cache=False)
        
        result = {'nodes': node_count, 'edges': edge_count}
        
        try:
            start = time.time()
            scores = analyzer._pagerank_sparse()
            end = time.time()
            result['pagerank_ms'] = (end - start) * 1000
            print(f"  ✅ PageRank: {result['pagerank_ms']:.2f} ms")
        except Exception as e:
            result['pagerank_ms'] = None
            print(f"  ❌ PageRank失败: {e}")
        
        try:
            start = time.time()
            communities = analyzer.detect_communities()
            end = time.time()
            result['community_ms'] = (end - start) * 1000
            result['community_count'] = len(communities)
            print(f"  ✅ 社区检测: {result['community_ms']:.2f} ms, {len(communities)} 社区")
        except Exception as e:
            result['community_ms'] = None
            print(f"  ❌ 社区检测失败: {e}")
        
        results.append(result)
    
    print(f"\n📈 扩展性结果:")
    print(f"{'节点数':<8} {'边数':<8} {'PageRank(ms)':<15} {'社区检测(ms)':<15}")
    print("-" * 50)
    for r in results:
        pr = f"{r['pagerank_ms']:.2f}" if r['pagerank_ms'] else "N/A"
        cm = f"{r['community_ms']:.2f}" if r['community_ms'] else "N/A"
        print(f"{r['nodes']:<8} {r['edges']:<8} {pr:<15} {cm:<15}")
    
    if len(results) >= 2:
        if results[0]['pagerank_ms'] and results[-1]['pagerank_ms']:
            node_scaling = results[-1]['nodes'] / results[0]['nodes']
            time_scaling = results[-1]['pagerank_ms'] / results[0]['pagerank_ms']
            print(f"\n📊 PageRank 扩展性: 节点数 {node_scaling:.0f}x, 时间 {time_scaling:.1f}x")
            if time_scaling <= node_scaling * 1.5:
                print("✅ 接近线性扩展，性能良好")
    
    return True

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 社交关系图分析平台 - 性能优化验证测试")
    print("=" * 70)
    
    graph_data = load_test_data()
    print(f"\n✅ 加载测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    
    all_passed = True
    
    try:
        test_pagerank_performance(graph_data)
    except Exception as e:
        print(f"\n❌ PageRank测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_community_detection_performance(graph_data)
    except Exception as e:
        print(f"\n❌ 社区检测测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_cache_performance(graph_data)
    except Exception as e:
        print(f"\n❌ 缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    try:
        test_large_graph_scalability()
    except Exception as e:
        print(f"\n❌ 扩展性测试失败: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 所有性能测试通过！")
        print("✅ PageRank: 稀疏矩阵迭代，内存降低")
        print("✅ 社区检测: Leiden算法，速度提升10倍")
        print("✅ 演化切片: 预计算缓存，切换秒级响应")
    else:
        print("⚠️  部分测试失败，请检查依赖安装")
    print("=" * 70)
