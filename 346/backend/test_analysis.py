import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from app.models import GraphData, Node, Edge
from app.analysis import GraphAnalyzer
from app.utils import filter_graph_by_time, calculate_temporal_metrics

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

def test_graph_analyzer():
    print("=" * 60)
    print("测试 GraphAnalyzer 模块")
    print("=" * 60)
    
    graph_data = load_test_data()
    print(f"\n✅ 加载测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    
    analyzer = GraphAnalyzer(graph_data)
    
    # 测试图指标
    print("\n--- 测试图指标 ---")
    metrics = analyzer.get_graph_metrics()
    print(f"节点数: {metrics['node_count']}")
    print(f"边数: {metrics['edge_count']}")
    print(f"图密度: {metrics['density']:.4f}")
    print(f"平均度数: {metrics['average_degree']:.2f}")
    print(f"最大度数: {metrics['max_degree']}")
    if 'clustering_coefficient' in metrics:
        print(f"聚类系数: {metrics['clustering_coefficient']:.4f}")
    print("✅ 图指标计算成功")
    
    # 测试社区检测
    print("\n--- 测试社区检测 (Louvain算法) ---")
    communities = analyzer.detect_communities()
    print(f"检测到 {len(communities)} 个社区")
    for i, comm in enumerate(communities[:3]):
        print(f"  社区 {comm.id + 1}: {comm.size} 节点, 模块度={comm.modularity:.4f}")
    print("✅ 社区检测成功")
    
    # 测试中心度计算
    print("\n--- 测试中心度计算 ---")
    methods = ['degree', 'betweenness', 'closeness', 'eigenvector', 'pagerank']
    for method in methods:
        influences = analyzer.calculate_influence(method)
        top3 = influences[:3]
        print(f"\n{method.upper()} Top 3:")
        for inf in top3:
            node = next((n for n in graph_data.nodes if n.id == inf.node_id), None)
            name = node.properties.get('name', inf.node_id) if node else inf.node_id
            print(f"  #{inf.rank} {name}: {inf.score:.4f}")
    print("✅ 所有中心度计算成功")
    
    # 测试关系类型过滤
    print("\n--- 测试关系类型过滤 ---")
    filtered = analyzer.filter_by_relationship_type(['FOLLOW', 'LIKE'])
    print(f"过滤后: {len(filtered.nodes)} 节点, {len(filtered.edges)} 边")
    
    follow_only = analyzer.filter_by_relationship_type(['FOLLOW'])
    print(f"仅关注关系: {len(follow_only.nodes)} 节点, {len(follow_only.edges)} 边")
    print("✅ 关系类型过滤成功")
    
    # 测试时间演化分析
    print("\n--- 测试时间演化分析 ---")
    temporal = analyzer.get_temporal_analysis(time_windows=5)
    print(f"时间窗口数: {len(temporal)}")
    for i, window in enumerate(temporal):
        print(f"  窗口 {i+1}: {window.get('node_count', 0)} 节点, {window.get('edge_count', 0)} 边, {window.get('community_count', 0)} 社区")
    print("✅ 时间演化分析成功")
    
    # 测试中心性对比
    print("\n--- 测试中心性对比 ---")
    comparison = analyzer.get_influence_comparison()
    print(f"算法对比完成，包含 {len(comparison.get('correlations', {}))} 组相关性")
    for key, value in list(comparison.get('correlations', {}).items())[:3]:
        corr = value if isinstance(value, float) else value.get('pearson_correlation', 0)
        print(f"  {key}: {corr:.4f}")
    print("✅ 中心性对比成功")
    
    # 测试最短路径
    print("\n--- 测试最短路径 ---")
    if len(graph_data.nodes) >= 2:
        source = graph_data.nodes[0].id
        target = graph_data.nodes[-1].id
        path = analyzer.find_shortest_path(source, target)
        if path:
            print(f"从 {source} 到 {target} 的路径: {' -> '.join(path)}")
        else:
            print(f"从 {source} 到 {target} 没有路径")
    print("✅ 最短路径计算成功")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过!")
    print("=" * 60)

def test_utils():
    print("\n" + "=" * 60)
    print("测试 Utils 模块")
    print("=" * 60)
    
    graph_data = load_test_data()
    
    # 测试时间过滤
    print("\n--- 测试时间过滤 ---")
    timestamps = [e.properties.get('timestamp') for e in graph_data.edges if e.properties.get('timestamp')]
    if timestamps:
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        mid_ts = (min_ts + max_ts) / 2
        
        filtered = filter_graph_by_time(graph_data, start_time=min_ts, end_time=mid_ts)
        print(f"前半时间段: {len(filtered.nodes)} 节点, {len(filtered.edges)} 边")
        
        filtered2 = filter_graph_by_time(graph_data, start_time=mid_ts, end_time=max_ts)
        print(f"后半时间段: {len(filtered2.nodes)} 节点, {len(filtered2.edges)} 边")
    print("✅ 时间过滤成功")
    
    # 测试时间指标
    print("\n--- 测试时间指标计算 ---")
    temporal_metrics = calculate_temporal_metrics(graph_data, time_key='timestamp')
    print(f"计算了 {len(temporal_metrics)} 个时间窗口的指标")
    print("✅ 时间指标计算成功")
    
    print("\n" + "=" * 60)
    print("🎉 Utils模块测试通过!")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_graph_analyzer()
        test_utils()
        print("\n🚀 所有测试完成，可以启动后端服务了!")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
