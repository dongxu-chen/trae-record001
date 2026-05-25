from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any
import json

from app.database import Neo4jDatabase
from app.analysis import GraphAnalyzer
from app.models import GraphData, Node, Edge
from app.cache import get_cache_manager

bp = Blueprint('api', __name__)

def get_db() -> Neo4jDatabase:
    config = current_app.config
    return Neo4jDatabase(
        config['NEO4J_URI'],
        config['NEO4J_USER'],
        config['NEO4J_PASSWORD']
    )

@bp.route('/health', methods=['GET'])
def health_check():
    db = get_db()
    try:
        db_connected = db.test_connection()
        return jsonify({
            'status': 'healthy',
            'database': db_connected
        })
    finally:
        db.close()

@bp.route('/graph', methods=['GET'])
def get_graph():
    db = get_db()
    try:
        limit = int(request.args.get('limit', 1000))
        graph_data = db.get_all_graph_data(limit)
        
        analyzer = GraphAnalyzer(graph_data)
        metrics = analyzer.get_graph_metrics()
        
        result = graph_data.to_dict()
        result['metrics'] = metrics
        
        return jsonify(result)
    finally:
        db.close()

@bp.route('/graph/communities', methods=['GET'])
def get_communities():
    db = get_db()
    try:
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        communities = analyzer.detect_communities()
        
        return jsonify([{
            'id': c.id,
            'nodes': c.nodes,
            'size': c.size,
            'modularity': c.modularity
        } for c in communities])
    finally:
        db.close()

@bp.route('/graph/influence', methods=['GET'])
def get_influence():
    db = get_db()
    try:
        method = request.args.get('method', 'degree')
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        influences = analyzer.calculate_influence(method)
        
        return jsonify([{
            'node_id': i.node_id,
            'score': i.score,
            'rank': i.rank
        } for i in influences])
    finally:
        db.close()

@bp.route('/graph/metrics', methods=['GET'])
def get_metrics():
    db = get_db()
    try:
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        metrics = analyzer.get_graph_metrics()
        
        return jsonify(metrics)
    finally:
        db.close()

@bp.route('/graph/path', methods=['GET'])
def get_shortest_path():
    db = get_db()
    try:
        source = request.args.get('source')
        target = request.args.get('target')
        
        if not source or not target:
            return jsonify({'error': 'source and target are required'}), 400
        
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        path = analyzer.find_shortest_path(source, target)
        
        if path is None:
            return jsonify({'path': None, 'message': 'No path found'})
        
        subgraph = analyzer.get_subgraph(path)
        
        return jsonify({
            'path': path,
            'graph': subgraph.to_dict()
        })
    finally:
        db.close()

@bp.route('/nodes', methods=['POST'])
def add_node():
    db = get_db()
    try:
        data = request.get_json()
        node = Node(
            id='',
            label=data.get('label', 'Node'),
            properties=data.get('properties', {})
        )
        created = db.create_node(node)
        return jsonify({
            'id': created.id,
            'label': created.label,
            'properties': created.properties
        }), 201
    finally:
        db.close()

@bp.route('/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    db = get_db()
    try:
        db.delete_node(node_id)
        return jsonify({'message': 'Node deleted successfully'})
    finally:
        db.close()

@bp.route('/edges', methods=['POST'])
def add_edge():
    db = get_db()
    try:
        data = request.get_json()
        edge = Edge(
            source=data['source'],
            target=data['target'],
            relationship_type=data.get('type', 'CONNECTED'),
            properties=data.get('properties', {})
        )
        created = db.create_edge(edge)
        return jsonify({
            'source': created.source,
            'target': created.target,
            'type': created.relationship_type,
            'properties': created.properties
        }), 201
    finally:
        db.close()

@bp.route('/import', methods=['POST'])
def import_data():
    db = get_db()
    try:
        data = request.get_json()
        
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
        
        graph_data = GraphData(nodes=nodes, edges=edges)
        db.import_data(graph_data)
        
        return jsonify({
            'message': 'Data imported successfully',
            'node_count': len(nodes),
            'edge_count': len(edges)
        }), 201
    finally:
        db.close()

@bp.route('/clear', methods=['DELETE'])
def clear_database():
    db = get_db()
    try:
        db.clear_database()
        return jsonify({'message': 'Database cleared successfully'})
    finally:
        db.close()

@bp.route('/nodes/<node_id>/neighbors', methods=['GET'])
def get_neighbors(node_id):
    db = get_db()
    try:
        neighbors = db.get_neighbors(node_id)
        return jsonify([{
            'id': n.id,
            'label': n.label,
            'properties': n.properties
        } for n in neighbors])
    finally:
        db.close()

@bp.route('/graph/temporal', methods=['GET'])
def get_temporal_analysis():
    db = get_db()
    try:
        start_time = request.args.get('start_time', type=float)
        end_time = request.args.get('end_time', type=float)
        time_windows = request.args.get('time_windows', default=10, type=int)
        
        if time_windows < 2:
            return jsonify({'error': 'time_windows must be at least 2'}), 400
        
        graph_data = db.get_graph_data_with_filters(
            start_time=start_time,
            end_time=end_time
        )
        
        analyzer = GraphAnalyzer(graph_data)
        temporal_data = analyzer.get_temporal_analysis(time_windows=time_windows)
        
        return jsonify({
            'time_windows': time_windows,
            'start_time': start_time,
            'end_time': end_time,
            'windows': temporal_data
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/filtered', methods=['GET'])
def get_filtered_graph():
    db = get_db()
    try:
        relationship_types = request.args.getlist('relationship_types')
        start_time = request.args.get('start_time', type=float)
        end_time = request.args.get('end_time', type=float)
        limit = request.args.get('limit', default=1000, type=int)
        
        graph_data = db.get_graph_data_with_filters(
            relationship_types=relationship_types if relationship_types else None,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        analyzer = GraphAnalyzer(graph_data)
        metrics = analyzer.get_graph_metrics()
        
        result = graph_data.to_dict()
        result['metrics'] = metrics
        result['filters'] = {
            'relationship_types': relationship_types,
            'start_time': start_time,
            'end_time': end_time
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/influence/comparison', methods=['GET'])
def get_influence_comparison():
    db = get_db()
    try:
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        comparison = analyzer.get_influence_comparison()
        
        return jsonify(comparison)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/relationship-types', methods=['GET'])
def get_relationship_types():
    db = get_db()
    try:
        types = db.get_all_relationship_types()
        return jsonify({
            'relationship_types': types,
            'count': len(types)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/cache/status', methods=['GET'])
def get_cache_status():
    try:
        cache = get_cache_manager()
        stats = cache.get_stats()
        return jsonify({
            'hits': stats['hits'],
            'misses': stats['misses'],
            'evictions': stats['evictions'],
            'hit_rate': stats['hit_rate'],
            'total_entries': stats['total_entries'],
            'total_size_bytes': stats['total_size_bytes'],
            'total_size_mb': stats['total_size_bytes'] / (1024 * 1024),
            'entries': stats['entries']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/cache/clear', methods=['POST', 'DELETE'])
def clear_cache():
    try:
        cache = get_cache_manager()
        count = cache.clear()
        return jsonify({
            'message': f'Cache cleared successfully',
            'cleared_entries': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/cache/refresh', methods=['POST'])
def refresh_cache():
    db = get_db()
    try:
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data, use_cache=False)
        
        cache = get_cache_manager()
        cache.clear()
        
        communities = analyzer.detect_communities()
        for method in ['degree', 'betweenness', 'closeness', 'eigenvector', 'pagerank']:
            analyzer.calculate_influence(method)
        for time_windows in [5, 10, 15]:
            analyzer.get_temporal_analysis(time_windows=time_windows)
        
        stats = cache.get_stats()
        
        return jsonify({
            'message': 'Cache refreshed successfully',
            'entries_cached': stats['total_entries'],
            'total_size_mb': stats['total_size_bytes'] / (1024 * 1024)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/performance', methods=['GET'])
def get_performance_info():
    db = get_db()
    try:
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        perf_info = analyzer.get_performance_info()

        cache = get_cache_manager()
        cache_stats = cache.get_stats()

        return jsonify({
            'graph': perf_info,
            'cache': {
                'hits': cache_stats['hits'],
                'misses': cache_stats['misses'],
                'hit_rate': cache_stats['hit_rate'],
                'total_entries': cache_stats['total_entries'],
                'total_size_mb': cache_stats['total_size_bytes'] / (1024 * 1024)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/key-nodes', methods=['GET'])
def get_key_nodes():
    db = get_db()
    try:
        top_n = int(request.args.get('top_n', 10))
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        result = analyzer.identify_key_nodes(top_n=top_n)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/diffusion', methods=['POST'])
def simulate_diffusion():
    db = get_db()
    try:
        data = request.get_json() or {}
        start_nodes = data.get('start_nodes')
        infection_rate = float(data.get('infection_rate', 0.3))
        recovery_rate = float(data.get('recovery_rate', 0.1))
        max_steps = int(data.get('max_steps', 50))
        model = data.get('model', 'SIR')

        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        result = analyzer.simulate_diffusion(
            start_nodes=start_nodes,
            infection_rate=infection_rate,
            recovery_rate=recovery_rate,
            max_steps=max_steps,
            model=model
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@bp.route('/graph/community-evolution', methods=['GET'])
def get_community_evolution():
    db = get_db()
    try:
        time_windows = int(request.args.get('time_windows', 10))
        graph_data = db.get_all_graph_data()
        analyzer = GraphAnalyzer(graph_data)
        result = analyzer.analyze_community_evolution(time_windows=time_windows)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()
