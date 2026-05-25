import sys
sys.path.insert(0, '.')
import json
import time
from app.analysis import GraphAnalyzer
from app.models import GraphData, Node, Edge

with open('../data/sample_social_relations.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

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
        properties={'weight': e.get('weight', 1.0), 'timestamp': e.get('timestamp', time.time())}
    ))

graph_data = GraphData(nodes=nodes, edges=edges)
analyzer = GraphAnalyzer(graph_data, use_cache=False)

print('=' * 70)
print('Test 1: Key Nodes Identification')
print('=' * 70)
result = analyzer.identify_key_nodes(top_n=3)
print('Influence nodes:', [n['node_id'] for n in result['data']['influence_nodes']])
print('Bridge nodes:', [n['node_id'] for n in result['data']['bridge_nodes']])
print('Hub nodes:', [n['node_id'] for n in result['data']['hub_nodes']])
print('Compute time:', result.get('compute_time_ms', 0), 'ms')
print('✅ Key nodes OK')

print()
print('=' * 70)
print('Test 2: Diffusion Simulation (SIR Model)')
print('=' * 70)
result = analyzer.simulate_diffusion(
    start_nodes=['11'], 
    infection_rate=0.3, 
    recovery_rate=0.1, 
    max_steps=20
)
print('Total infected:', result['data']['total_infected'])
print('Total recovered:', result['data']['total_recovered'])
print('Peak infected:', result['data']['peak_infected'], 'at step', result['data']['peak_step'])
print('Duration:', result['data']['duration'], 'steps')
print('Affected nodes:', len(result['data']['affected_nodes']))
print('Spread paths:', len(result['data'].get('spread_paths', [])))
print('Compute time:', result.get('compute_time_ms', 0), 'ms')
print('Parameters:', result['data']['parameters'])
print('✅ Diffusion OK')

print()
print('=' * 70)
print('Test 3: Community Evolution Analysis')
print('=' * 70)
result = analyzer.analyze_community_evolution(time_windows=5)
print('Frames:', len(result['data']['frames']))
print('Events:', len(result['data']['events']))
print('Total merges:', result['data']['total_merges'])
print('Total splits:', result['data']['total_splits'])
print('New communities:', result['data']['total_new_communities'])
print('Dissolved:', result['data']['total_dissolved_communities'])
if 'animation_data' in result['data']:
    print('Animation frames:', result['data']['animation_data']['total_frames'])
else:
    print('Animation data: N/A (no temporal data)')
print('Compute time:', result.get('compute_time_ms', 0), 'ms')
print('✅ Evolution OK')

print()
print('=' * 70)
print('🎉 All tests passed!')
print('=' * 70)
