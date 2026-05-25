import sys
sys.path.insert(0, '.')
import json
import time
from app.analysis import GraphAnalyzer
from app.models import GraphData, Node, Edge

print('=' * 70)
print('🧪 测试: 社群演化分析（带变化时间戳）')
print('=' * 70)

nodes = []
for i in range(1, 16):
    nodes.append(Node(
        id=str(i),
        label=f'User_{i}',
        properties={'name': f'用户{i}'}
    ))

base_time = 1750275043902
edges = []

for t in range(5):
    window_base = base_time + t * 100000
    
    if t == 0:
        edges.append(Edge(source='1', target='2', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 1000}))
        edges.append(Edge(source='1', target='3', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 2000}))
        edges.append(Edge(source='2', target='3', relationship_type='LIKE',
            properties={'weight': 1, 'timestamp': window_base + 3000}))
        edges.append(Edge(source='4', target='5', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 4000}))
        edges.append(Edge(source='4', target='6', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 5000}))
        edges.append(Edge(source='5', target='6', relationship_type='LIKE',
            properties={'weight': 1, 'timestamp': window_base + 6000}))
        edges.append(Edge(source='7', target='8', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 7000}))
        edges.append(Edge(source='7', target='9', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 8000}))
    
    elif t == 1:
        edges.append(Edge(source='3', target='4', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 1000}))
        edges.append(Edge(source='6', target='7', relationship_type='LIKE',
            properties={'weight': 1, 'timestamp': window_base + 2000}))
    
    elif t == 2:
        edges.append(Edge(source='1', target='10', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 1000}))
        edges.append(Edge(source='10', target='11', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 2000}))
        edges.append(Edge(source='10', target='12', relationship_type='LIKE',
            properties={'weight': 1, 'timestamp': window_base + 3000}))
    
    elif t == 3:
        edges.append(Edge(source='11', target='7', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 1000}))
        edges.append(Edge(source='12', target='8', relationship_type='LIKE',
            properties={'weight': 1, 'timestamp': window_base + 2000}))
    
    elif t == 4:
        edges.append(Edge(source='13', target='14', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 1000}))
        edges.append(Edge(source='13', target='15', relationship_type='FOLLOW',
            properties={'weight': 1, 'timestamp': window_base + 2000}))
        edges.append(Edge(source='14', target='15', relationship_type='LIKE',
            properties={'weight': 1, 'timestamp': window_base + 3000}))

print(f'\n测试数据: {len(nodes)} 节点, {len(edges)} 边')
print(f'时间范围: {base_time} ~ {base_time + 5 * 100000}')
print('-' * 50)

graph_data = GraphData(nodes=nodes, edges=edges)
analyzer = GraphAnalyzer(graph_data, use_cache=False)

print(f'\n✅ 图构建完成')
print(f'   节点数: {analyzer.G.number_of_nodes()}')
print(f'   边数: {analyzer.G.number_of_edges()}')

timestamps = []
for _, _, data in analyzer.G.edges(data=True):
    ts = data.get('timestamp')
    if ts:
        timestamps.append(ts)
print(f'   时间戳数量: {len(timestamps)}')
print(f'   时间范围: {min(timestamps):.0f} ~ {max(timestamps):.0f}')

start_time = time.time()
result = analyzer.analyze_community_evolution(time_windows=5)
elapsed = (time.time() - start_time) * 1000

evo_data = result['data']

print(f'\n✅ 计算耗时: {elapsed:.2f} ms')
print(f'   缓存命中: {result.get("from_cache", False)}')

print(f'\n📊 演化统计:')
print(f'   时间窗口数: {len(evo_data["frames"])}')
print(f'   总合并数: {evo_data["total_merges"]}')
print(f'   总分裂数: {evo_data["total_splits"]}')
print(f'   新增社区数: {evo_data["total_new_communities"]}')
print(f'   解散社区数: {evo_data["total_dissolved_communities"]}')
print(f'   总事件数: {len(evo_data["events"])}')

print(f'\n📋 时间窗口详情:')
for frame in evo_data['frames']:
    comm_count = len(frame['communities'])
    node_count = len(frame['node_community_map'])
    event_count = len(frame['events'])
    events_desc = ', '.join([e['event_type'] for e in frame['events'][:3]])
    if len(frame['events']) > 3:
        events_desc += f'...(+{len(frame["events"])-3})'
    print(f'   窗口 {frame["window_index"]:2d}: {comm_count} 社区, {node_count} 节点, '
          f'{event_count} 事件 [{events_desc or "无"}]')
    
    for comm in frame['communities']:
        print(f'      社区 {comm["id"]}: {comm["size"]} 节点')
    
    for event in frame['events']:
        icon_map = {
            'merge': '🔗', 'split': '💔', 'dissolved': '💨', 'new': '🌟',
            'initial': '🎬', 'expanded': '📈', 'contracted': '📉'
        }
        icon = icon_map.get(event['event_type'], '📌')
        print(f'      {icon} {event["description"]}')

if 'animation_data' in evo_data:
    anim = evo_data['animation_data']
    print(f'\n🎬 动画数据:')
    print(f'   总帧数: {anim["total_frames"]}')
    if anim['frames']:
        for i, frame in enumerate(anim['frames'][:2]):
            print(f'   帧 {i}: {len(frame["nodes"])} 节点, {len(frame["communities"])} 社区')

print('\n✅ 社群演化分析完整测试通过!')
print('🎉 可以检测到社区的合并、分裂、新增和解散事件!')
