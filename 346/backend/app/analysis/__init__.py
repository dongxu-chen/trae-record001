import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from itertools import combinations
import time

try:
    from scipy.sparse import csr_matrix, lil_matrix
    from scipy.sparse.linalg import spsolve
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import leidenalg as la
    import igraph as ig
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False

try:
    import community as community_louvain
except ImportError:
    try:
        from community import community_louvain
    except ImportError:
        community_louvain = None

from app.models import (
    GraphData, Community, InfluenceResult, Node, Edge,
    KeyNode, DiffusionStep, DiffusionResult,
    CommunityEvolutionEvent, CommunityEvolutionFrame, CommunityEvolutionResult
)
from app.cache import get_cache_manager


class GraphAnalyzer:
    def __init__(self, graph_data: GraphData, use_cache: bool = True):
        self.G = nx.Graph()
        self._build_graph(graph_data)
        self._node_list = list(self.G.nodes())
        self._node_to_idx = {node: idx for idx, node in enumerate(self._node_list)}
        self._use_cache = use_cache
        self._cache = get_cache_manager()
        self._graph_hash = self._compute_graph_hash()
    
    def _compute_graph_hash(self) -> str:
        nodes = sorted(self.G.nodes())
        edges = sorted(
            (min(u, v), max(u, v), d.get('weight', 1.0), d.get('relationship_type', ''))
            for u, v, d in self.G.edges(data=True)
        )
        import hashlib
        import json
        raw = json.dumps([nodes, edges], sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()
    
    def _build_graph(self, graph_data: GraphData):
        for node in graph_data.nodes:
            self.G.add_node(node.id, label=node.label, **node.properties)
        
        for edge in graph_data.edges:
            edge_attrs = {
                'relationship_type': edge.relationship_type,
                'weight': edge.properties.get('weight', 1.0)
            }
            edge_attrs.update(edge.properties)
            self.G.add_edge(edge.source, edge.target, **edge_attrs)
    
    def _build_sparse_adjacency_matrix(self, weight: str = 'weight') -> csr_matrix:
        n = len(self._node_list)
        lil = lil_matrix((n, n), dtype=np.float64)
        
        for u, v, data in self.G.edges(data=True):
            i = self._node_to_idx[u]
            j = self._node_to_idx[v]
            w = data.get(weight, 1.0)
            lil[i, j] = w
            lil[j, i] = w
        
        return lil.tocsr()
    
    def _pagerank_sparse(self, alpha: float = 0.85, max_iter: int = 100, 
                         tol: float = 1e-6, weight: str = 'weight') -> Dict[str, float]:
        n = len(self._node_list)
        if n == 0:
            return {}
        
        if not SCIPY_AVAILABLE:
            return nx.pagerank(self.G, alpha=alpha, max_iter=max_iter, tol=tol, weight=weight)
        
        A = self._build_sparse_adjacency_matrix(weight=weight)
        
        row_sums = np.array(A.sum(axis=1)).flatten()
        D_inv = np.where(row_sums > 0, 1.0 / row_sums, 0.0)
        
        M = A.multiply(D_inv[:, np.newaxis]).tocsr()
        
        x = np.ones(n) / n
        teleport = np.ones(n) / n
        
        for i in range(max_iter):
            x_new = alpha * M.T.dot(x) + (1 - alpha) * teleport
            
            err = np.abs(x_new - x).sum()
            x = x_new
            
            if err < n * tol:
                break
        
        return {self._node_list[i]: float(x[i]) for i in range(n)}
    
    def detect_communities(self) -> List[Community]:
        cache_key = self._cache.get_community_key(self._graph_hash)
        
        if self._use_cache:
            cached, hit = self._cache.get(cache_key)
            if hit:
                return [Community(**c) for c in cached]
        
        n = len(self.G.nodes())
        if n == 0:
            return []
        
        start_time = time.time()
        
        if LEIDEN_AVAILABLE:
            try:
                ig_graph = ig.Graph()
                ig_graph.add_vertices(self._node_list)
                
                edges = []
                weights = []
                for u, v, data in self.G.edges(data=True):
                    edges.append((self._node_to_idx[u], self._node_to_idx[v]))
                    weights.append(data.get('weight', 1.0))
                
                ig_graph.add_edges(edges)
                
                partition = la.find_partition(
                    ig_graph,
                    la.ModularityVertexPartition,
                    weights=weights if weights else None,
                    n_iterations=-1
                )
                
                communities: Dict[int, List[str]] = {}
                for idx, comm_id in enumerate(partition.membership):
                    if comm_id not in communities:
                        communities[comm_id] = []
                    communities[comm_id].append(self._node_list[idx])
                
                modularity = partition.quality()
                
            except Exception:
                if community_louvain is not None:
                    try:
                        partition = community_louvain.best_partition(self.G, weight='weight')
                        communities = {}
                        for node_id, comm_id in partition.items():
                            if comm_id not in communities:
                                communities[comm_id] = []
                            communities[comm_id].append(node_id)
                        modularity = community_louvain.modularity(partition, self.G)
                    except Exception:
                        return [Community(id=0, nodes=list(self.G.nodes()), 
                                         size=self.G.number_of_nodes(), modularity=0.0)]
                else:
                    return [Community(id=0, nodes=list(self.G.nodes()), 
                                     size=self.G.number_of_nodes(), modularity=0.0)]
        elif community_louvain is not None:
            try:
                partition = community_louvain.best_partition(self.G, weight='weight')
                communities = {}
                for node_id, comm_id in partition.items():
                    if comm_id not in communities:
                        communities[comm_id] = []
                    communities[comm_id].append(node_id)
                modularity = community_louvain.modularity(partition, self.G)
            except Exception:
                return [Community(id=0, nodes=list(self.G.nodes()), 
                                 size=self.G.number_of_nodes(), modularity=0.0)]
        else:
            return [Community(id=0, nodes=list(self.G.nodes()), 
                             size=self.G.number_of_nodes(), modularity=0.0)]
        
        result = []
        for i, (comm_id, nodes) in enumerate(sorted(communities.items(), key=lambda x: len(x[1]), reverse=True)):
            result.append(Community(
                id=i,
                nodes=nodes,
                size=len(nodes),
                modularity=modularity
            ))
        
        end_time = time.time()
        algorithm = 'leiden' if LEIDEN_AVAILABLE else 'louvain'
        
        if self._use_cache:
            self._cache.set(cache_key, [c.__dict__ for c in result], ttl=3600)
        
        return result
    
    def calculate_influence(self, method: str = 'degree') -> List[InfluenceResult]:
        cache_key = self._cache.get_influence_key(self._graph_hash, method)
        
        if self._use_cache:
            cached, hit = self._cache.get(cache_key)
            if hit:
                return [InfluenceResult(**i) for i in cached]
        
        start_time = time.time()
        
        if method == 'degree':
            scores = dict(self.G.degree(weight='weight'))
        elif method == 'betweenness':
            scores = nx.betweenness_centrality(self.G, weight='weight')
        elif method == 'closeness':
            scores = nx.closeness_centrality(self.G)
        elif method == 'eigenvector':
            scores = nx.eigenvector_centrality(self.G, weight='weight', max_iter=1000)
        elif method == 'pagerank':
            scores = self._pagerank_sparse(alpha=0.85, max_iter=100, tol=1e-6, weight='weight')
        else:
            raise ValueError(f"Unknown method: {method}")
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        result = [
            InfluenceResult(node_id=node_id, score=score, rank=i+1)
            for i, (node_id, score) in enumerate(sorted_scores)
        ]
        
        end_time = time.time()
        
        if self._use_cache:
            self._cache.set(cache_key, [i.__dict__ for i in result], ttl=3600)
        
        return result
    
    def get_graph_metrics(self) -> Dict[str, Any]:
        if self.G.number_of_nodes() == 0:
            return {}
        
        metrics = {
            'node_count': self.G.number_of_nodes(),
            'edge_count': self.G.number_of_edges(),
            'density': nx.density(self.G),
            'average_degree': np.mean([d for n, d in self.G.degree()]),
            'max_degree': max(d for n, d in self.G.degree()),
            'is_connected': nx.is_connected(self.G),
        }
        
        if metrics['is_connected']:
            metrics['average_shortest_path'] = nx.average_shortest_path_length(self.G, weight='weight')
            metrics['diameter'] = nx.diameter(self.G)
        
        try:
            metrics['clustering_coefficient'] = nx.average_clustering(self.G, weight='weight')
        except:
            pass
        
        return metrics
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        try:
            path = nx.shortest_path(self.G, source=source, target=target, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def get_subgraph(self, nodes: List[str]) -> GraphData:
        subgraph = self.G.subgraph(nodes)
        
        sub_nodes = []
        for node_id, data in subgraph.nodes(data=True):
            props = {k: v for k, v in data.items() if k != 'label'}
            sub_nodes.append(Node(
                id=node_id,
                label=data.get('label', ''),
                properties=props
            ))
        
        sub_edges = []
        for u, v, data in subgraph.edges(data=True):
            props = {k: v for k, v in data.items() if k != 'relationship_type'}
            sub_edges.append(Edge(
                source=u,
                target=v,
                relationship_type=data.get('relationship_type', 'CONNECTED'),
                properties=props
            ))
        
        return GraphData(nodes=sub_nodes, edges=sub_edges)
    
    def filter_by_relationship_type(self, relationship_types: List[str]) -> GraphData:
        if not relationship_types:
            raise ValueError("relationship_types list cannot be empty")
        
        relationship_types_set = set(relationship_types)
        
        filtered_edges = []
        for u, v, data in self.G.edges(data=True):
            edge_type = data.get('relationship_type', 'CONNECTED')
            if edge_type in relationship_types_set:
                filtered_edges.append((u, v, data))
        
        connected_nodes = set()
        for u, v, _ in filtered_edges:
            connected_nodes.add(u)
            connected_nodes.add(v)
        
        sub_nodes = []
        for node_id in connected_nodes:
            data = self.G.nodes[node_id]
            props = {k: v for k, v in data.items() if k != 'label'}
            sub_nodes.append(Node(
                id=node_id,
                label=data.get('label', ''),
                properties=props
            ))
        
        sub_edges = []
        for u, v, data in filtered_edges:
            props = {k: v for k, v in data.items() if k != 'relationship_type'}
            sub_edges.append(Edge(
                source=u,
                target=v,
                relationship_type=data.get('relationship_type', 'CONNECTED'),
                properties=props
            ))
        
        return GraphData(nodes=sub_nodes, edges=sub_edges)
    
    def _get_timestamps(self) -> Tuple[List[float], float, float]:
        all_timestamps = []
        for _, _, data in self.G.edges(data=True):
            ts = data.get('timestamp')
            if ts is not None:
                all_timestamps.append(ts)
        
        if not all_timestamps:
            return [], 0, 0
        
        return all_timestamps, min(all_timestamps), max(all_timestamps)
    
    def _precompute_temporal_windows(self, time_windows: int = 10) -> List[Dict[str, Any]]:
        all_timestamps, min_ts, max_ts = self._get_timestamps()
        
        if not all_timestamps:
            return []
        
        window_size = (max_ts - min_ts) / time_windows
        
        window_data = []
        for window_idx in range(time_windows):
            window_start = min_ts + window_idx * window_size
            window_end = min_ts + (window_idx + 1) * window_size
            
            window_edges = []
            for u, v, data in self.G.edges(data=True):
                ts = data.get('timestamp')
                if ts is not None:
                    if window_idx == time_windows - 1:
                        if window_start <= ts <= window_end:
                            window_edges.append((u, v, data))
                    else:
                        if window_start <= ts < window_end:
                            window_edges.append((u, v, data))
            
            window_nodes = set()
            for u, v, _ in window_edges:
                window_nodes.add(u)
                window_nodes.add(v)
            
            window_data.append({
                'window_index': window_idx,
                'start_time': window_start,
                'end_time': window_end,
                'edges': window_edges,
                'nodes': window_nodes
            })
        
        return window_data
    
    def get_temporal_analysis(self, time_windows: int = 10, 
                              relationship_types: Optional[List[str]] = None) -> Dict[str, Any]:
        cache_key = self._cache.get_temporal_key(
            self._graph_hash, time_windows, relationship_types
        )
        
        if self._use_cache:
            cached, hit = self._cache.get(cache_key)
            if hit:
                return {
                    'data': cached,
                    'from_cache': True,
                    'algorithm': 'leiden' if LEIDEN_AVAILABLE else 'louvain',
                    'pagerank_method': 'sparse_matrix' if SCIPY_AVAILABLE else 'networkx'
                }
        
        start_time = time.time()
        
        all_timestamps, min_ts, max_ts = self._get_timestamps()
        
        if not all_timestamps:
            result = []
            for i in range(time_windows):
                result.append({
                    'window_index': i,
                    'start_time': None,
                    'end_time': None,
                    'metrics': {},
                    'community_count': 0,
                    'node_count': 0,
                    'edge_count': 0,
                    'new_nodes': [],
                    'removed_nodes': [],
                    'community_changes': []
                })
            return {
                'data': result,
                'from_cache': False,
                'compute_time_ms': 0,
                'algorithm': 'leiden' if LEIDEN_AVAILABLE else 'louvain',
                'pagerank_method': 'sparse_matrix' if SCIPY_AVAILABLE else 'networkx'
            }
        
        window_data = self._precompute_temporal_windows(time_windows)
        
        result = []
        prev_communities = {}
        prev_nodes = set()
        
        for wd in window_data:
            window_nodes = wd['nodes']
            window_edges = wd['edges']
            window_start = wd['start_time']
            window_end = wd['end_time']
            window_idx = wd['window_index']
            
            if not window_edges:
                result.append({
                    'window_index': window_idx,
                    'start_time': window_start,
                    'end_time': window_end,
                    'metrics': {},
                    'community_count': 0,
                    'node_count': 0,
                    'edge_count': 0,
                    'new_nodes': [],
                    'removed_nodes': [],
                    'community_changes': []
                })
                prev_communities = {}
                prev_nodes = set()
                continue
            
            temp_nodes = [Node(
                id=nid, 
                label=self.G.nodes[nid].get('label', 'Node'),
                properties={k: v for k, v in self.G.nodes[nid].items() if k != 'label'}
            ) for nid in window_nodes]
            
            temp_edges = [Edge(
                source=u, 
                target=v,
                relationship_type=data.get('relationship_type', 'CONNECTED'),
                properties={k: v for k, v in data.items() if k != 'relationship_type'}
            ) for u, v, data in window_edges]
            
            temp_graph_data = GraphData(nodes=temp_nodes, edges=temp_edges)
            temp_analyzer = GraphAnalyzer(temp_graph_data, use_cache=False)
            
            metrics = temp_analyzer.get_graph_metrics()
            
            communities = {}
            if len(window_nodes) > 0:
                try:
                    if LEIDEN_AVAILABLE:
                        ig_graph = ig.Graph()
                        ig_graph.add_vertices(list(window_nodes))
                        edges = []
                        weights = []
                        for u, v, data in window_edges:
                            edges.append((list(window_nodes).index(u), list(window_nodes).index(v)))
                            weights.append(data.get('weight', 1.0))
                        ig_graph.add_edges(edges)
                        partition = la.find_partition(
                            ig_graph,
                            la.ModularityVertexPartition,
                            weights=weights if weights else None,
                            n_iterations=-1
                        )
                        for idx, comm_id in enumerate(partition.membership):
                            if comm_id not in communities:
                                communities[comm_id] = []
                            communities[comm_id].append(list(window_nodes)[idx])
                    elif community_louvain is not None:
                        subgraph = nx.Graph()
                        for node_id in window_nodes:
                            subgraph.add_node(node_id, **self.G.nodes[node_id])
                        for u, v, data in window_edges:
                            subgraph.add_edge(u, v, **data)
                        partition = community_louvain.best_partition(subgraph, weight='weight')
                        for node_id, comm_id in partition.items():
                            if comm_id not in communities:
                                communities[comm_id] = []
                            communities[comm_id].append(node_id)
                except Exception:
                    pass
            
            new_nodes = window_nodes - prev_nodes
            removed_nodes = prev_nodes - window_nodes
            
            community_changes = []
            if prev_communities and communities:
                prev_comm_nodes = {cid: set(nodes) for cid, nodes in prev_communities.items()}
                curr_comm_nodes = {cid: set(nodes) for cid, nodes in communities.items()}
                
                for curr_cid, curr_nodes in curr_comm_nodes.items():
                    max_overlap = 0
                    matched_prev = None
                    for prev_cid, prev_nodes_set in prev_comm_nodes.items():
                        overlap = len(curr_nodes & prev_nodes_set)
                        if overlap > max_overlap:
                            max_overlap = overlap
                            matched_prev = prev_cid
                    
                    if matched_prev is not None:
                        change_ratio = len(curr_nodes ^ prev_comm_nodes[matched_prev]) / max(len(curr_nodes), len(prev_comm_nodes[matched_prev]))
                        community_changes.append({
                            'community_id': curr_cid,
                            'matched_prev_id': matched_prev,
                            'overlap_count': max_overlap,
                            'change_ratio': change_ratio,
                            'is_new': max_overlap == 0
                        })
                    else:
                        community_changes.append({
                            'community_id': curr_cid,
                            'matched_prev_id': None,
                            'overlap_count': 0,
                            'change_ratio': 1.0,
                            'is_new': True
                        })
            
            result.append({
                'window_index': window_idx,
                'start_time': window_start,
                'end_time': window_end,
                'metrics': metrics,
                'community_count': len(communities),
                'node_count': len(window_nodes),
                'edge_count': len(window_edges),
                'new_nodes': list(new_nodes),
                'removed_nodes': list(removed_nodes),
                'community_changes': community_changes
            })
            
            prev_communities = communities
            prev_nodes = window_nodes
        
        end_time = time.time()
        compute_time_ms = (end_time - start_time) * 1000
        
        if self._use_cache:
            self._cache.set(cache_key, result, ttl=3600)
        
        return {
            'data': result,
            'from_cache': False,
            'compute_time_ms': compute_time_ms,
            'algorithm': 'leiden' if LEIDEN_AVAILABLE else 'louvain',
            'pagerank_method': 'sparse_matrix' if SCIPY_AVAILABLE else 'networkx'
        }
    
    def get_influence_comparison(self) -> Dict[str, Any]:
        methods = ['degree', 'betweenness', 'closeness', 'eigenvector', 'pagerank']
        results = {}
        
        for method in methods:
            try:
                influence = self.calculate_influence(method)
                results[method] = {
                    'scores': {i.node_id: i.score for i in influence},
                    'ranks': {i.node_id: i.rank for i in influence}
                }
            except Exception as e:
                results[method] = {
                    'scores': {},
                    'ranks': {},
                    'error': str(e)
                }
        
        node_ids = list(results[methods[0]]['scores'].keys())
        correlations = {}
        for m1, m2 in combinations(methods, 2):
            if len(node_ids) >= 2:
                ranks1 = [results[m1]['ranks'].get(n, 0) for n in node_ids]
                ranks2 = [results[m2]['ranks'].get(n, 0) for n in node_ids]
                
                try:
                    correlation = np.corrcoef(ranks1, ranks2)[0, 1]
                    if np.isnan(correlation):
                        correlation = 0.0
                except Exception:
                    correlation = 0.0
            else:
                correlation = 0.0
            
            correlations[f"{m1}_vs_{m2}"] = {
                'pearson_correlation': correlation,
                'top_10_overlap': len(set(
                    [n for n, r in sorted(results[m1]['ranks'].items(), key=lambda x: x[1])[:10]]
                ) & set(
                    [n for n, r in sorted(results[m2]['ranks'].items(), key=lambda x: x[1])[:10]]
                ))
            }
        
        top_nodes = {}
        for method in methods:
            sorted_nodes = sorted(results[method]['ranks'].items(), key=lambda x: x[1])[:5]
            top_nodes[method] = [
                {'node_id': n, 'rank': r, 'score': results[method]['scores'][n]}
                for n, r in sorted_nodes
            ]
        
        return {
            'methods': methods,
            'node_count': len(node_ids),
            'correlations': correlations,
            'top_nodes': top_nodes,
            'algorithm_info': {
                'community': 'leiden' if LEIDEN_AVAILABLE else 'louvain',
                'pagerank': 'sparse_matrix' if SCIPY_AVAILABLE else 'networkx'
            },
            'all_ranks': {
                node_id: {
                    method: results[method]['ranks'].get(node_id, None)
                    for method in methods
                }
                for node_id in node_ids
            }
        }
    
    def get_performance_info(self) -> Dict[str, Any]:
        return {
            'node_count': self.G.number_of_nodes(),
            'edge_count': self.G.number_of_edges(),
            'scipy_available': SCIPY_AVAILABLE,
            'leiden_available': LEIDEN_AVAILABLE,
            'louvain_available': community_louvain is not None,
            'pagerank_method': 'sparse_matrix' if SCIPY_AVAILABLE else 'networkx',
            'community_algorithm': 'leiden' if LEIDEN_AVAILABLE else 'louvain',
            'cache_enabled': self._use_cache,
            'graph_hash': self._graph_hash
        }

    def identify_key_nodes(self, top_n: int = 10) -> Dict[str, Any]:
        cache_key = self._cache._generate_key('key_nodes', self._graph_hash, top_n=top_n)

        if self._use_cache:
            cached, hit = self._cache.get(cache_key)
            if hit:
                return {
                    'data': cached,
                    'from_cache': True
                }

        start_time = time.time()

        n = len(self.G.nodes())
        if n == 0:
            return {
                'data': {
                    'influence_nodes': [],
                    'bridge_nodes': [],
                    'hub_nodes': [],
                    'all_key_nodes': []
                },
                'from_cache': False,
                'compute_time_ms': 0
            }

        pagerank_scores = self._pagerank_sparse()
        betweenness_scores = nx.betweenness_centrality(self.G, weight='weight')
        degree_scores = dict(self.G.degree(weight='weight'))
        eigenvector_scores = nx.eigenvector_centrality(self.G, weight='weight', max_iter=1000)

        influence_nodes = []
        sorted_pagerank = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (node_id, score) in enumerate(sorted_pagerank[:top_n]):
            influence_nodes.append(KeyNode(
                node_id=node_id,
                node_type='influence',
                score=score,
                rank=i + 1,
                description=f'高影响力节点，PageRank得分 {score:.4f}，在信息传播中起关键作用'
            ))

        bridge_nodes = []
        sorted_betweenness = sorted(betweenness_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (node_id, score) in enumerate(sorted_betweenness[:top_n]):
            bridge_nodes.append(KeyNode(
                node_id=node_id,
                node_type='bridge',
                score=score,
                rank=i + 1,
                description=f'桥接节点，介数中心度 {score:.4f}，连接不同社区的关键枢纽'
            ))

        hub_nodes = []
        sorted_degree = sorted(degree_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (node_id, score) in enumerate(sorted_degree[:top_n]):
            hub_nodes.append(KeyNode(
                node_id=node_id,
                node_type='hub',
                score=float(score),
                rank=i + 1,
                description=f'枢纽节点，加权度 {score:.2f}，连接最多的节点'
            ))

        all_key_nodes = {}
        for node_id in self.G.nodes():
            combined_score = (
                0.4 * pagerank_scores.get(node_id, 0) +
                0.3 * betweenness_scores.get(node_id, 0) +
                0.2 * eigenvector_scores.get(node_id, 0) +
                0.1 * (degree_scores.get(node_id, 0) / max(degree_scores.values()) if degree_scores else 0)
            )
            all_key_nodes[node_id] = {
                'node_id': node_id,
                'pagerank': pagerank_scores.get(node_id, 0),
                'betweenness': betweenness_scores.get(node_id, 0),
                'degree': degree_scores.get(node_id, 0),
                'eigenvector': eigenvector_scores.get(node_id, 0),
                'combined_score': combined_score
            }

        sorted_all = sorted(all_key_nodes.values(), key=lambda x: x['combined_score'], reverse=True)
        for i, item in enumerate(sorted_all):
            item['rank'] = i + 1

        result = {
            'influence_nodes': [kn.__dict__ for kn in influence_nodes],
            'bridge_nodes': [kn.__dict__ for kn in bridge_nodes],
            'hub_nodes': [kn.__dict__ for kn in hub_nodes],
            'all_key_nodes': sorted_all,
            'node_types': {
                'influence': [n.node_id for n in influence_nodes],
                'bridge': [n.node_id for n in bridge_nodes],
                'hub': [n.node_id for n in hub_nodes]
            }
        }

        end_time = time.time()
        compute_time_ms = (end_time - start_time) * 1000

        if self._use_cache:
            self._cache.set(cache_key, result, ttl=3600)

        return {
            'data': result,
            'from_cache': False,
            'compute_time_ms': compute_time_ms
        }

    def simulate_diffusion(self,
                           start_nodes: Optional[List[str]] = None,
                           infection_rate: float = 0.3,
                           recovery_rate: float = 0.1,
                           max_steps: int = 50,
                           model: str = 'SIR') -> Dict[str, Any]:
        cache_key = self._cache._generate_key(
            'diffusion', self._graph_hash,
            start_nodes=sorted(start_nodes) if start_nodes else None,
            infection_rate=infection_rate,
            recovery_rate=recovery_rate,
            max_steps=max_steps,
            model=model
        )

        if self._use_cache:
            cached, hit = self._cache.get(cache_key)
            if hit:
                return {
                    'data': cached,
                    'from_cache': True
                }

        start_time = time.time()

        n = len(self.G.nodes())
        if n == 0:
            return {
                'data': {
                    'steps': [],
                    'total_infected': 0,
                    'total_recovered': 0,
                    'peak_infected': 0,
                    'peak_step': 0,
                    'duration': 0,
                    'infection_tree': {},
                    'affected_nodes': [],
                    'parameters': {}
                },
                'from_cache': False,
                'compute_time_ms': 0
            }

        if start_nodes is None or len(start_nodes) == 0:
            pagerank = self._pagerank_sparse()
            start_nodes = [max(pagerank, key=pagerank.get)]

        for node in start_nodes:
            if node not in self.G.nodes():
                raise ValueError(f"Start node {node} not found in graph")

        susceptible = set(self.G.nodes()) - set(start_nodes)
        infected = set(start_nodes)
        recovered = set()

        infection_tree: Dict[str, List[str]] = {node: [] for node in self.G.nodes()}
        steps = []
        peak_infected = 0
        peak_step = 0

        for step in range(max_steps):
            new_infections: List[str] = []

            infected_list = list(infected)
            np.random.shuffle(infected_list)

            for infected_node in infected_list:
                neighbors = list(self.G.neighbors(infected_node))
                for neighbor in neighbors:
                    if neighbor in susceptible:
                        if np.random.random() < infection_rate:
                            new_infections.append(neighbor)
                            susceptible.remove(neighbor)
                            infection_tree[infected_node].append(neighbor)

            new_recoveries: List[str] = []
            for infected_node in list(infected):
                if np.random.random() < recovery_rate:
                    new_recoveries.append(infected_node)
                    infected.remove(infected_node)
                    recovered.add(infected_node)

            infected.update(new_infections)

            steps.append(DiffusionStep(
                step=step,
                infected=list(infected),
                recovered=list(recovered),
                susceptible=list(susceptible),
                new_infections=new_infections,
                infection_count=len(infected),
                recovery_count=len(recovered)
            ))

            if len(infected) > peak_infected:
                peak_infected = len(infected)
                peak_step = step

            if len(infected) == 0:
                break

        total_infected = len(recovered) + len(infected)
        total_recovered = len(recovered)
        affected_nodes = list(recovered) + list(infected)

        result = DiffusionResult(
            steps=steps,
            total_infected=total_infected,
            total_recovered=total_recovered,
            peak_infected=peak_infected,
            peak_step=peak_step,
            duration=len(steps),
            infection_tree=infection_tree,
            affected_nodes=affected_nodes
        )

        end_time = time.time()
        compute_time_ms = (end_time - start_time) * 1000

        result_dict = {
            'steps': [s.__dict__ for s in result.steps],
            'total_infected': result.total_infected,
            'total_recovered': result.total_recovered,
            'peak_infected': result.peak_infected,
            'peak_step': result.peak_step,
            'duration': result.duration,
            'infection_tree': result.infection_tree,
            'affected_nodes': result.affected_nodes,
            'parameters': {
                'start_nodes': start_nodes,
                'infection_rate': infection_rate,
                'recovery_rate': recovery_rate,
                'max_steps': max_steps,
                'model': model
            },
            'spread_paths': self._extract_spread_paths(start_nodes, infection_tree, affected_nodes)
        }

        if self._use_cache:
            self._cache.set(cache_key, result_dict, ttl=3600)

        return {
            'data': result_dict,
            'from_cache': False,
            'compute_time_ms': compute_time_ms
        }

    def _extract_spread_paths(self, start_nodes: List[str],
                              infection_tree: Dict[str, List[str]],
                              affected_nodes: List[str]) -> List[Dict[str, Any]]:
        paths = []
        visited = set()

        def dfs(node: str, current_path: List[str], depth: int):
            if node in visited:
                return
            visited.add(node)

            children = infection_tree.get(node, [])
            if not children:
                if len(current_path) > 1:
                    paths.append({
                        'path': current_path,
                        'length': len(current_path) - 1,
                        'start_node': current_path[0],
                        'end_node': current_path[-1]
                    })
            else:
                for child in children:
                    dfs(child, current_path + [child], depth + 1)

        for start_node in start_nodes:
            dfs(start_node, [start_node], 0)

        paths.sort(key=lambda x: x['length'], reverse=True)
        return paths[:20]

    def analyze_community_evolution(self, time_windows: int = 10) -> Dict[str, Any]:
        cache_key = self._cache._generate_key(
            'community_evolution', self._graph_hash, time_windows=time_windows
        )

        if self._use_cache:
            cached, hit = self._cache.get(cache_key)
            if hit:
                return {
                    'data': cached,
                    'from_cache': True
                }

        start_time = time.time()

        all_timestamps, min_ts, max_ts = self._get_timestamps()

        if not all_timestamps:
            return {
                'data': {
                    'frames': [],
                    'events': [],
                    'total_merges': 0,
                    'total_splits': 0,
                    'total_new_communities': 0,
                    'total_dissolved_communities': 0,
                    'animation_data': {
                        'frames': [],
                        'total_frames': 0,
                        'event_types': ['initial', 'new', 'merge', 'split', 'expanded', 'contracted', 'dissolved']
                    }
                },
                'from_cache': False,
                'compute_time_ms': 0
            }

        window_data = self._precompute_temporal_windows(time_windows)

        frames: List[CommunityEvolutionFrame] = []
        all_events: List[CommunityEvolutionEvent] = []
        prev_node_community: Dict[str, int] = {}
        prev_communities: Dict[int, set] = {}

        total_merges = 0
        total_splits = 0
        total_new_communities = 0
        total_dissolved_communities = 0

        for wd in window_data:
            window_nodes = wd['nodes']
            window_edges = wd['edges']
            window_start = wd['start_time']
            window_end = wd['end_time']
            window_idx = wd['window_index']

            frame_events: List[CommunityEvolutionEvent] = []

            if not window_edges:
                frames.append(CommunityEvolutionFrame(
                    window_index=window_idx,
                    start_time=window_start,
                    end_time=window_end,
                    communities=[],
                    events=[],
                    node_community_map={}
                ))
                prev_node_community = {}
                prev_communities = {}
                continue

            temp_nodes = [Node(
                id=nid,
                label=self.G.nodes[nid].get('label', 'Node'),
                properties={k: v for k, v in self.G.nodes[nid].items() if k != 'label'}
            ) for nid in window_nodes]

            temp_edges = [Edge(
                source=u,
                target=v,
                relationship_type=data.get('relationship_type', 'CONNECTED'),
                properties={k: v for k, v in data.items() if k != 'relationship_type'}
            ) for u, v, data in window_edges]

            temp_graph_data = GraphData(nodes=temp_nodes, edges=temp_edges)
            temp_analyzer = GraphAnalyzer(temp_graph_data, use_cache=False)

            communities_list = temp_analyzer.detect_communities()

            curr_communities: Dict[int, set] = {}
            curr_node_community: Dict[str, int] = {}

            for comm in communities_list:
                curr_communities[comm.id] = set(comm.nodes)
                for node in comm.nodes:
                    curr_node_community[node] = comm.id

            if prev_communities and curr_communities:
                prev_comm_ids = set(prev_communities.keys())
                curr_comm_ids = set(curr_communities.keys())

                for curr_id in curr_comm_ids:
                    curr_nodes = curr_communities[curr_id]

                    matching_prev = []
                    for prev_id in prev_comm_ids:
                        prev_nodes = prev_communities[prev_id]
                        overlap = len(curr_nodes & prev_nodes)
                        if overlap > 0:
                            matching_prev.append((prev_id, overlap))

                    matching_prev.sort(key=lambda x: x[1], reverse=True)

                    if len(matching_prev) == 0:
                        total_new_communities += 1
                        frame_events.append(CommunityEvolutionEvent(
                            window_index=window_idx,
                            event_type='new',
                            community_id=curr_id,
                            source_communities=[],
                            target_community=curr_id,
                            nodes_involved=list(curr_nodes),
                            description=f'新社区 {curr_id} 形成，包含 {len(curr_nodes)} 个节点'
                        ))
                    elif len(matching_prev) == 1:
                        prev_id, overlap = matching_prev[0]
                        prev_nodes = prev_communities[prev_id]

                        if len(curr_nodes - prev_nodes) > len(prev_nodes) * 0.5:
                            frame_events.append(CommunityEvolutionEvent(
                                window_index=window_idx,
                                event_type='expanded',
                                community_id=curr_id,
                                source_communities=[prev_id],
                                target_community=curr_id,
                                nodes_involved=list(curr_nodes - prev_nodes),
                                description=f'社区 {curr_id} 显著扩张，新增 {len(curr_nodes - prev_nodes)} 个节点'
                            ))
                        elif len(prev_nodes - curr_nodes) > len(prev_nodes) * 0.5:
                            frame_events.append(CommunityEvolutionEvent(
                                window_index=window_idx,
                                event_type='contracted',
                                community_id=curr_id,
                                source_communities=[prev_id],
                                target_community=curr_id,
                                nodes_involved=list(prev_nodes - curr_nodes),
                                description=f'社区 {curr_id} 收缩，失去 {len(prev_nodes - curr_nodes)} 个节点'
                            ))
                    else:
                        total_merges += 1
                        source_ids = [p[0] for p in matching_prev[:3]]
                        merged_nodes = set()
                        for p in matching_prev[:3]:
                            merged_nodes.update(prev_communities[p[0]])
                        frame_events.append(CommunityEvolutionEvent(
                            window_index=window_idx,
                            event_type='merge',
                            community_id=curr_id,
                            source_communities=source_ids,
                            target_community=curr_id,
                            nodes_involved=list(merged_nodes & curr_nodes),
                            description=f'社区 {source_ids} 合并为新社区 {curr_id}，共 {len(curr_nodes)} 个节点'
                        ))

                for prev_id in prev_comm_ids:
                    if prev_id not in [p[0] for m in frame_events if m.event_type == 'merge' for p in
                                       [(x,) for x in m.source_communities]]:
                        prev_nodes = prev_communities[prev_id]
                        matching_curr = []
                        for curr_id in curr_comm_ids:
                            overlap = len(prev_nodes & curr_communities[curr_id])
                            if overlap > 0:
                                matching_curr.append((curr_id, overlap))

                        if len(matching_curr) >= 2:
                            total_splits += 1
                            target_ids = [c[0] for c in matching_curr]
                            frame_events.append(CommunityEvolutionEvent(
                                window_index=window_idx,
                                event_type='split',
                                community_id=prev_id,
                                source_communities=[prev_id],
                                target_community=None,
                                nodes_involved=list(prev_nodes),
                                description=f'社区 {prev_id} 分裂为 {target_ids} 等多个社区'
                            ))
                        elif len(matching_curr) == 0:
                            total_dissolved_communities += 1
                            frame_events.append(CommunityEvolutionEvent(
                                window_index=window_idx,
                                event_type='dissolved',
                                community_id=prev_id,
                                source_communities=[prev_id],
                                target_community=None,
                                nodes_involved=list(prev_nodes),
                                description=f'社区 {prev_id} 解散，{len(prev_nodes)} 个节点分散'
                            ))

            elif not prev_communities and curr_communities:
                for curr_id, curr_nodes in curr_communities.items():
                    total_new_communities += 1
                    frame_events.append(CommunityEvolutionEvent(
                        window_index=window_idx,
                        event_type='initial',
                        community_id=curr_id,
                        source_communities=[],
                        target_community=curr_id,
                        nodes_involved=list(curr_nodes),
                        description=f'初始社区 {curr_id}，包含 {len(curr_nodes)} 个节点'
                    ))

            comm_dicts = []
            for comm in communities_list:
                comm_dicts.append({
                    'id': comm.id,
                    'nodes': comm.nodes,
                    'size': comm.size,
                    'modularity': comm.modularity
                })

            frames.append(CommunityEvolutionFrame(
                window_index=window_idx,
                start_time=window_start,
                end_time=window_end,
                communities=comm_dicts,
                events=frame_events,
                node_community_map=curr_node_community
            ))

            all_events.extend(frame_events)
            prev_communities = curr_communities
            prev_node_community = curr_node_community

        result = CommunityEvolutionResult(
            frames=frames,
            events=all_events,
            total_merges=total_merges,
            total_splits=total_splits,
            total_new_communities=total_new_communities,
            total_dissolved_communities=total_dissolved_communities
        )

        end_time = time.time()
        compute_time_ms = (end_time - start_time) * 1000

        result_dict = {
            'frames': [{
                'window_index': f.window_index,
                'start_time': f.start_time,
                'end_time': f.end_time,
                'communities': f.communities,
                'events': [e.__dict__ for e in f.events],
                'node_community_map': f.node_community_map
            } for f in result.frames],
            'events': [e.__dict__ for e in result.events],
            'total_merges': result.total_merges,
            'total_splits': result.total_splits,
            'total_new_communities': result.total_new_communities,
            'total_dissolved_communities': result.total_dissolved_communities,
            'animation_data': self._prepare_animation_data(result.frames)
        }

        if self._use_cache:
            self._cache.set(cache_key, result_dict, ttl=3600)

        return {
            'data': result_dict,
            'from_cache': False,
            'compute_time_ms': compute_time_ms
        }

    def _prepare_animation_data(self, frames: List[CommunityEvolutionFrame]) -> Dict[str, Any]:
        node_positions = {}
        all_nodes = set()
        for f in frames:
            for node in f.node_community_map.keys():
                all_nodes.add(node)

        for node in all_nodes:
            node_positions[node] = {
                'x': np.random.uniform(-100, 100),
                'y': np.random.uniform(-100, 100)
            }

        animation_frames = []
        for f in frames:
            animation_frames.append({
                'window_index': f.window_index,
                'start_time': f.start_time,
                'end_time': f.end_time,
                'nodes': [{
                    'id': node,
                    'x': node_positions[node]['x'] + np.random.uniform(-5, 5),
                    'y': node_positions[node]['y'] + np.random.uniform(-5, 5),
                    'community': f.node_community_map.get(node, -1)
                } for node in f.node_community_map.keys()],
                'communities': f.communities,
                'events': [e.__dict__ for e in f.events]
            })

        return {
            'frames': animation_frames,
            'total_frames': len(animation_frames),
            'event_types': ['initial', 'new', 'merge', 'split', 'expanded', 'contracted', 'dissolved']
        }
