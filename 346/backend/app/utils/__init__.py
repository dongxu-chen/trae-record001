import json
from typing import Dict, Any, List, Optional
from app.models import GraphData, Node, Edge
import pandas as pd

def load_json_file(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(filepath: str, data: Dict[str, Any]):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def graph_data_from_json(data: Dict[str, Any]) -> GraphData:
    nodes = [Node(
        id=str(n.get('id', '')),
        label=n.get('label', 'Node'),
        properties={k: v for k, v in n.items() if k not in ['id', 'label']}
    ) for n in data.get('nodes', [])]
    
    edges = [Edge(
        source=str(e.get('source', '')),
        target=str(e.get('target', '')),
        relationship_type=e.get('type', 'CONNECTED'),
        properties={k: v for k, v in e.items() if k not in ['source', 'target', 'type']}
    ) for e in data.get('edges', [])]
    
    return GraphData(nodes=nodes, edges=edges)

def graph_data_from_dataframes(nodes_df: pd.DataFrame, edges_df: pd.DataFrame,
                              id_col: str = 'id', label_col: str = 'label',
                              source_col: str = 'source', target_col: str = 'target',
                              type_col: str = 'type') -> GraphData:
    nodes = []
    for _, row in nodes_df.iterrows():
        props = row.drop([id_col, label_col]).to_dict()
        nodes.append(Node(
            id=str(row[id_col]),
            label=str(row[label_col]) if label_col in row else 'Node',
            properties=props
        ))
    
    edges = []
    for _, row in edges_df.iterrows():
        props = row.drop([source_col, target_col, type_col]).to_dict()
        edges.append(Edge(
            source=str(row[source_col]),
            target=str(row[target_col]),
            relationship_type=str(row[type_col]) if type_col in row else 'CONNECTED',
            properties=props
        ))
    
    return GraphData(nodes=nodes, edges=edges)

def filter_graph_by_time(graph_data: GraphData, start_time: Optional[float] = None,
                         end_time: Optional[float] = None, time_key: str = 'timestamp') -> GraphData:
    filtered_edges = []
    for edge in graph_data.edges:
        timestamp = edge.properties.get(time_key)
        if timestamp is None:
            filtered_edges.append(edge)
            continue
        if (start_time is None or timestamp >= start_time) and \
           (end_time is None or timestamp <= end_time):
            filtered_edges.append(edge)
    
    connected_node_ids = set()
    for edge in filtered_edges:
        connected_node_ids.add(edge.source)
        connected_node_ids.add(edge.target)
    
    filtered_nodes = [n for n in graph_data.nodes if n.id in connected_node_ids]
    
    return GraphData(nodes=filtered_nodes, edges=filtered_edges)

def calculate_temporal_metrics(graph_data: GraphData, 
                               time_key: str = 'timestamp') -> List[Dict[str, Any]]:
    timestamps = []
    for edge in graph_data.edges:
        ts = edge.properties.get(time_key)
        if ts is not None:
            timestamps.append(ts)
    
    if not timestamps:
        return []
    
    timestamps.sort()
    time_points = []
    
    num_windows = 10
    if len(timestamps) > num_windows:
        step = len(timestamps) // num_windows
        time_points = [timestamps[i * step] for i in range(num_windows)] + [timestamps[-1]]
    else:
        time_points = timestamps
    
    metrics_over_time = []
    for i in range(1, len(time_points)):
        start_ts = time_points[i-1]
        end_ts = time_points[i]
        
        subgraph = filter_graph_by_time(graph_data, start_ts, end_ts, time_key)
        
        if subgraph.nodes:
            from app.analysis import GraphAnalyzer
            analyzer = GraphAnalyzer(subgraph)
            metrics = analyzer.get_graph_metrics()
            metrics['start_time'] = start_ts
            metrics['end_time'] = end_ts
            metrics_over_time.append(metrics)
    
    return metrics_over_time

def validate_graph_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    if 'nodes' not in data:
        return False, 'Missing "nodes" field'
    
    if 'edges' not in data:
        return False, 'Missing "edges" field'
    
    node_ids = set()
    for i, node in enumerate(data['nodes']):
        if 'id' not in node:
            return False, f'Node at index {i} missing "id" field'
        if node['id'] in node_ids:
            return False, f'Duplicate node id: {node["id"]}'
        node_ids.add(str(node['id']))
    
    for i, edge in enumerate(data['edges']):
        if 'source' not in edge:
            return False, f'Edge at index {i} missing "source" field'
        if 'target' not in edge:
            return False, f'Edge at index {i} missing "target" field'
        if str(edge['source']) not in node_ids:
            return False, f'Edge at index {i} has unknown source: {edge["source"]}'
        if str(edge['target']) not in node_ids:
            return False, f'Edge at index {i} has unknown target: {edge["target"]}'
    
    return True, None
