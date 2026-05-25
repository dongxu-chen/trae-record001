import sys
sys.path.insert(0, '.')
import json
import time
from app.analysis import GraphAnalyzer
from app.models import GraphData, Node, Edge

with open('../data/sample_social_relations.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Sample data keys:', list(data.keys()))
print('Users count:', len(data.get('users', [])))
print('Relationships count:', len(data.get('relationships', [])))
print('First user:', data['users'][0])
print('First rel:', data['relationships'][0])

nodes = []
edges = []
for user in data.get('users', []):
    nodes.append(Node(id=str(user['id']), label=user.get('name', 'User_' + str(user['id']))))
for rel in data.get('relationships', []):
    edges.append(Edge(
        source=str(rel['source']),
        target=str(rel['target']),
        relationship_type=rel.get('type', 'CONNECTED'),
        properties={'weight': rel.get('weight', 1.0), 'timestamp': rel.get('timestamp', time.time())}
    ))

print()
print('Nodes created:', len(nodes))
print('Edges created:', len(edges))
print('First node id:', nodes[0].id)
print('First edge:', edges[0].source, '->', edges[0].target)

graph_data = GraphData(nodes=nodes, edges=edges)
analyzer = GraphAnalyzer(graph_data, use_cache=False)

print()
print('Graph analyzer created')
print('Graph nodes:', analyzer.G.number_of_nodes())
print('Graph edges:', analyzer.G.number_of_edges())
print('Node list:', analyzer._node_list[:5])

print()
print('Testing pagerank...')
pr = analyzer._pagerank_sparse()
print('Pagerank result count:', len(pr))
print('Pagerank first 3:', list(pr.items())[:3])

print()
print('Testing betweenness...')
import networkx as nx
bt = nx.betweenness_centrality(analyzer.G, weight='weight')
print('Betweenness count:', len(bt))
print('Betweenness first 3:', list(bt.items())[:3])

print()
print('Testing degree...')
deg = dict(analyzer.G.degree(weight='weight'))
print('Degree count:', len(deg))
print('Degree first 3:', list(deg.items())[:3])

print()
print('Testing identify_key_nodes...')
result = analyzer.identify_key_nodes(top_n=3)
print('Result keys:', list(result.keys()))
print('Data keys:', list(result['data'].keys()))
print('Influence nodes:', result['data']['influence_nodes'])
print('Bridge nodes:', result['data']['bridge_nodes'])
print('Hub nodes:', result['data']['hub_nodes'])
