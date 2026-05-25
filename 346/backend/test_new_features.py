import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
from app.analysis import GraphAnalyzer
from app.models import GraphData, Node, Edge
from app.database import DatabaseManager

def load_sample_data():
    with open('../data/sample_social_relations.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def create_graph_from_data(data):
    nodes = []
    edges = []
    
    for n in data.get('nodes', []):
        nodes.append(Node(
            id=str(n['id']),
            label=n.get('name', n.get('label', 'User')),
            properties={k: v for k, v in n.items() if k not in ['id', 'label', 'name']}
        ))
    
    for e in data.get('edges', []):
        edges.append(Edge(
            source=str(e['source']),
            target=str(e['target']),
            relationship_type=e.get('type', 'CONNECTED'),
            properties={
                'weight': e.get('weight', 1.0),
                'timestamp': e.get('timestamp', time.time())
            }
        ))
    
    return GraphData(nodes=nodes, edges=edges)

def test_key_nodes_identification():
    print("=" * 70)
    print("📊 测试 1: 关键节点识别")
    print("=" * 70)
    
    data = load_sample_data()
    graph_data = create_graph_from_data(data)
    analyzer = GraphAnalyzer(graph_data, use_cache=False)
    
    print(f"\n测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    print("-" * 50)
    
    start_time = time.time()
    result = analyzer.identify_key_nodes(top_n=5)
    elapsed = (time.time() - start_time) * 1000
    
    key_data = result['data']
    
    print(f"\n✅ 计算耗时: {elapsed:.2f} ms")
    print(f"   缓存命中: {result.get('from_cache', False)}")
    
    print("\n🎯 影响力节点 Top 5 (PageRank):")
    for node in key_data['influence_nodes']:
        print(f"   {node['rank']}. 节点 {node['node_id']}: 分数 {node['score']:.4f}")
        print(f"      {node['description']}")
    
    print("\n🌉 桥接节点 Top 5 (Betweenness):")
    for node in key_data['bridge_nodes']:
        print(f"   {node['rank']}. 节点 {node['node_id']}: 分数 {node['score']:.4f}")
        print(f"      {node['description']}")
    
    print("\n⭐ 枢纽节点 Top 5 (Degree):")
    for node in key_data['hub_nodes']:
        print(f"   {node['rank']}. 节点 {node['node_id']}: 分数 {node['score']:.2f}")
        print(f"      {node['description']}")
    
    print(f"\n📈 综合评分 Top 3:")
    for node in key_data['all_key_nodes'][:3]:
        print(f"   {node['rank']}. 节点 {node['node_id']}: 综合分 {node['combined_score']:.4f}")
        print(f"      PageRank: {node['pagerank']:.4f}, 介数: {node['betweenness']:.4f}, "
              f"度数: {node['degree']:.0f}, 特征向量: {node['eigenvector']:.4f}")
    
    print("\n✅ 关键节点识别测试通过!")
    return True

def test_diffusion_simulation():
    print("\n" + "=" * 70)
    print("🦠 测试 2: 病毒式传播扩散模拟 (SIR模型)")
    print("=" * 70)
    
    data = load_sample_data()
    graph_data = create_graph_from_data(data)
    analyzer = GraphAnalyzer(graph_data, use_cache=False)
    
    print(f"\n测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    print("-" * 50)
    
    start_time = time.time()
    result = analyzer.simulate_diffusion(
        start_nodes=['11'],
        infection_rate=0.3,
        recovery_rate=0.1,
        max_steps=30,
        model='SIR'
    )
    elapsed = (time.time() - start_time) * 1000
    
    diff_data = result['data']
    
    print(f"\n✅ 计算耗时: {elapsed:.2f} ms")
    print(f"   缓存命中: {result.get('from_cache', False)}")
    
    params = diff_data['parameters']
    print(f"\n📋 模拟参数:")
    print(f"   起始节点: {params['start_nodes']}")
    print(f"   感染率: {params['infection_rate']}")
    print(f"   恢复率: {params['recovery_rate']}")
    print(f"   最大步数: {params['max_steps']}")
    
    print(f"\n📊 模拟结果:")
    print(f"   总感染数: {diff_data['total_infected']}/{len(graph_data.nodes)} ({diff_data['total_infected']/len(graph_data.nodes)*100:.1f}%)")
    print(f"   总恢复数: {diff_data['total_recovered']}")
    print(f"   峰值感染: {diff_data['peak_infected']} (第 {diff_data['peak_step']} 步)")
    print(f"   持续时间: {diff_data['duration']} 步")
    print(f"   影响节点数: {len(diff_data['affected_nodes'])}")
    
    print(f"\n📈 传播步骤概览 (前10步):")
    for step in diff_data['steps'][:10]:
        status = []
        if step['new_infections']:
            status.append(f"新增{len(step['new_infections'])}")
        if step['infection_count'] > 0:
            status.append(f"感染中{step['infection_count']}")
        if step['recovery_count'] > 0:
            status.append(f"已恢复{step['recovery_count']}")
        print(f"   步骤 {step['step']:2d}: {', '.join(status)}")
    
    print(f"\n🌳 最长传播路径 Top 5:")
    for i, path in enumerate(diff_data['spread_paths'][:5]):
        print(f"   {i+1}. 路径长度 {path['length']}: {' → '.join(path['path'])}")
    
    print(f"\n🔗 感染树 (前5个传播者):")
    spreaders = sorted(diff_data['infection_tree'].items(), key=lambda x: len(x[1]), reverse=True)[:5]
    for node, infected in spreaders:
        if infected:
            print(f"   节点 {node} 传播给: {', '.join(infected)}")
    
    print("\n✅ 扩散模拟测试通过!")
    return True

def test_community_evolution():
    print("\n" + "=" * 70)
    print("🌱 测试 3: 社群演化分析")
    print("=" * 70)
    
    data = load_sample_data()
    graph_data = create_graph_from_data(data)
    analyzer = GraphAnalyzer(graph_data, use_cache=False)
    
    print(f"\n测试数据: {len(graph_data.nodes)} 节点, {len(graph_data.edges)} 边")
    print("-" * 50)
    
    start_time = time.time()
    result = analyzer.analyze_community_evolution(time_windows=10)
    elapsed = (time.time() - start_time) * 1000
    
    evo_data = result['data']
    
    print(f"\n✅ 计算耗时: {elapsed:.2f} ms")
    print(f"   缓存命中: {result.get('from_cache', False)}")
    
    print(f"\n📊 演化统计:")
    print(f"   时间窗口数: {len(evo_data['frames'])}")
    print(f"   总合并数: {evo_data['total_merges']}")
    print(f"   总分裂数: {evo_data['total_splits']}")
    print(f"   新增社区数: {evo_data['total_new_communities']}")
    print(f"   解散社区数: {evo_data['total_dissolved_communities']}")
    print(f"   总事件数: {len(evo_data['events'])}")
    
    print(f"\n📋 时间窗口概览:")
    for frame in evo_data['frames']:
        comm_count = len(frame['communities'])
        node_count = len(frame['node_community_map'])
        event_count = len(frame['events'])
        events_desc = ', '.join([e['event_type'] for e in frame['events'][:3]])
        if len(frame['events']) > 3:
            events_desc += f"...(+{len(frame['events'])-3})"
        print(f"   窗口 {frame['window_index']:2d}: {comm_count} 社区, {node_count} 节点, "
              f"{event_count} 事件 [{events_desc or '无'}]")
    
    print(f"\n⚡ 关键事件时间线:")
    event_types = ['merge', 'split', 'dissolved', 'new']
    important_events = [e for e in evo_data['events'] if e['event_type'] in event_types]
    for event in important_events[:10]:
        icon_map = {
            'merge': '🔗', 'split': '💔', 'dissolved': '💨', 'new': '🌟',
            'initial': '🎬', 'expanded': '📈', 'contracted': '📉'
        }
        icon = icon_map.get(event['event_type'], '📌')
        print(f"   {icon} 窗口 {event['window_index']:2d} - {event['description']}")
    
    if 'animation_data' in evo_data:
        anim = evo_data['animation_data']
        print(f"\n🎬 动画数据:")
        print(f"   总帧数: {anim['total_frames']}")
        print(f"   事件类型: {', '.join(anim['event_types'])}")
        if anim['frames']:
            frame0 = anim['frames'][0]
            print(f"   首帧节点数: {len(frame0['nodes'])}")
            print(f"   首帧社区数: {len(frame0['communities'])}")
    
    print("\n✅ 社群演化分析测试通过!")
    return True

def test_api_endpoints():
    print("\n" + "=" * 70)
    print("🌐 测试 4: API 接口可用性")
    print("=" * 70)
    
    try:
        from app import create_app
        app = create_app()
        client = app.test_client()
        
        db = DatabaseManager()
        db.clear_database()
        
        data = load_sample_data()
        for n in data.get('nodes', []):
            db.create_node(str(n['id']), n.get('name', n.get('label', 'User')),
                          {k: v for k, v in n.items() if k not in ['id', 'label', 'name']})
        
        for e in data.get('edges', []):
            db.create_edge(
                str(e['source']),
                str(e['target']),
                e.get('type', 'CONNECTED'),
                {
                    'weight': e.get('weight', 1.0),
                    'timestamp': e.get('timestamp', time.time())
                }
            )
        
        print("\n📋 测试关键节点 API: GET /api/graph/key-nodes")
        response = client.get('/api/graph/key-nodes?top_n=5')
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.get_json()
        assert 'data' in data, "缺少 data 字段"
        assert 'influence_nodes' in data['data'], "缺少 influence_nodes"
        assert 'bridge_nodes' in data['data'], "缺少 bridge_nodes"
        assert 'hub_nodes' in data['data'], "缺少 hub_nodes"
        print(f"   ✅ 正常返回, {len(data['data']['influence_nodes'])} 个影响力节点")
        
        print("\n📋 测试扩散模拟 API: POST /api/graph/diffusion")
        response = client.post('/api/graph/diffusion', json={
            'start_nodes': ['11'],
            'infection_rate': 0.3,
            'recovery_rate': 0.1,
            'max_steps': 30
        })
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.get_json()
        assert 'data' in data, "缺少 data 字段"
        assert 'steps' in data['data'], "缺少 steps"
        assert 'total_infected' in data['data'], "缺少 total_infected"
        print(f"   ✅ 正常返回, {data['data']['total_infected']} 个节点被感染, "
              f"{len(data['data']['steps'])} 步")
        
        print("\n📋 测试社群演化 API: GET /api/graph/community-evolution")
        response = client.get('/api/graph/community-evolution?time_windows=10')
        assert response.status_code == 200, f"状态码错误: {response.status_code}"
        data = response.get_json()
        assert 'data' in data, "缺少 data 字段"
        assert 'frames' in data['data'], "缺少 frames"
        assert 'events' in data['data'], "缺少 events"
        print(f"   ✅ 正常返回, {len(data['data']['frames'])} 个时间窗口, "
              f"{len(data['data']['events'])} 个事件")
        
        db.close()
        print("\n✅ 所有 API 接口测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ API 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("🚀 社交关系图分析平台 - 新功能测试")
    print("=" * 70)
    
    tests = [
        ('关键节点识别', test_key_nodes_identification),
        ('扩散模拟', test_diffusion_simulation),
        ('社群演化分析', test_community_evolution),
        ('API接口', test_api_endpoints)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)
    
    if failed == 0:
        print("🎉 所有新功能测试通过!")
        return 0
    else:
        print("⚠️  部分测试失败, 请检查")
        return 1

if __name__ == '__main__':
    sys.exit(main())
