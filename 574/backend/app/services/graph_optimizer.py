import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
import networkx as nx
import logging

from ..models.schemas import (
    Paper, GraphNode, GraphEdge, GraphData, GraphStats,
    HierarchicalCommunity, MultiGranularClusters, SubGraphData
)

logger = logging.getLogger(__name__)


class SparsePageRank:
    def __init__(self, alpha: float = 0.85, tol: float = 1e-8, max_iter: int = 100):
        self.alpha = alpha
        self.tol = tol
        self.max_iter = max_iter

    def compute(self, adjacency: csr_matrix) -> np.ndarray:
        n = adjacency.shape[0]
        if n == 0:
            return np.array([])

        out_degree = np.array(adjacency.sum(axis=1)).flatten()
        out_degree[out_degree == 0] = 1

        P = adjacency.multiply(1.0 / out_degree[:, np.newaxis])
        P = P.tocsr()

        x = np.ones(n) / n
        teleport = np.ones(n) / n

        for i in range(self.max_iter):
            x_new = self.alpha * P.T.dot(x) + (1 - self.alpha) * teleport

            dangling = out_degree == 0
            if np.any(dangling):
                dangling_contrib = self.alpha * np.sum(x[dangling]) / n
                x_new += dangling_contrib

            delta = np.abs(x_new - x).sum()
            x = x_new

            if delta < self.tol:
                logger.debug(f"PageRank converged in {i + 1} iterations")
                break

        return x

    def compute_from_graph(self, graph: nx.DiGraph) -> Dict[str, float]:
        nodes = list(graph.nodes())
        n = len(nodes)
        if n == 0:
            return {}

        node_to_idx = {node: i for i, node in enumerate(nodes)}

        adj_data = lil_matrix((n, n))
        for source, target in graph.edges():
            si = node_to_idx[source]
            ti = node_to_idx[target]
            adj_data[si, ti] = graph[source][target].get('weight', 1.0)

        adjacency = adj_data.tocsr()

        scores = self.compute(adjacency)

        return {nodes[i]: float(scores[i]) for i in range(n)}


class MultiGranularCommunityDetector:
    def __init__(self, graph: nx.Graph):
        self.graph = graph
        self.levels: List[int] = []
        self.communities: Dict[int, Dict[int, Set[str]]] = {}
        self.node_community_map: Dict[str, Dict[int, int]] = defaultdict(dict)

    def detect_hierarchical(self, num_levels: int = 3) -> MultiGranularClusters:
        logger.info(f"Detecting {num_levels} levels of hierarchical communities")

        if self.graph.number_of_nodes() < 5:
            return self._create_single_cluster()

        try:
            communities_l0 = nx.algorithms.community.greedy_modularity_communities(
                self.graph, resolution=0.5
            )
            self._store_level(0, communities_l0)

            communities_l1 = nx.algorithms.community.greedy_modularity_communities(
                self.graph, resolution=1.0
            )
            self._store_level(1, communities_l1)

            communities_l2 = nx.algorithms.community.greedy_modularity_communities(
                self.graph, resolution=2.0
            )
            self._store_level(2, communities_l2)

            return self._build_result()

        except Exception as e:
            logger.warning(f"Hierarchical community detection failed: {e}")
            return self._create_single_cluster()

    def _store_level(self, level: int, communities: List[Set[str]]):
        self.levels.append(level)
        self.communities[level] = {}

        for i, comm in enumerate(communities):
            self.communities[level][i] = comm
            for node in comm:
                self.node_community_map[node][level] = i

    def _create_single_cluster(self) -> MultiGranularClusters:
        nodes = set(self.graph.nodes())
        self.levels = [0]
        self.communities[0] = {0: nodes}
        for node in nodes:
            self.node_community_map[node][0] = 0
        return self._build_result()

    def _build_result(self) -> MultiGranularClusters:
        hierarchical_communities = {}

        for level in self.levels:
            hierarchical_communities[level] = {}
            for comm_id, nodes in self.communities.get(level, {}).items():
                keywords = self._extract_keywords(list(nodes))
                name = f"Cluster L{level}-{comm_id}"

                parent_id = None
                if level > 0 and level - 1 in self.levels:
                    sample_node = next(iter(nodes), None)
                    if sample_node and level - 1 in self.node_community_map.get(sample_node, {}):
                        parent_id = self.node_community_map[sample_node][level - 1]

                hierarchical_communities[level][comm_id] = HierarchicalCommunity(
                    level=level,
                    community_id=comm_id,
                    parent_id=parent_id,
                    nodes=list(nodes),
                    children=self._find_children(level, comm_id),
                    name=name,
                    size=len(nodes),
                    keywords=keywords
                )

        node_comm_map = {
            node: dict(comms) for node, comms in self.node_community_map.items()
        }

        return MultiGranularClusters(
            levels=self.levels,
            communities=hierarchical_communities,
            node_community_map=node_comm_map
        )

    def _find_children(self, level: int, comm_id: int) -> List[int]:
        if level >= max(self.levels, default=level):
            return []

        child_level = level + 1
        if child_level not in self.levels:
            return []

        children = set()
        for node in self.communities.get(level, {}).get(comm_id, set()):
            if child_level in self.node_community_map.get(node, {}):
                children.add(self.node_community_map[node][child_level])

        return sorted(children)

    def _extract_keywords(self, nodes: List[str]) -> List[str]:
        all_words = []
        for node in nodes:
            if node in self.graph.nodes:
                title = self.graph.nodes[node].get('title', '')
                words = title.lower().split()
                all_words.extend([w for w in words if len(w) > 3])

        word_counts = defaultdict(int)
        for w in all_words:
            word_counts[w] += 1

        return sorted(word_counts.keys(), key=lambda x: word_counts[x], reverse=True)[:5]


class SubGraphExplorer:
    def __init__(self, graph: nx.DiGraph, papers: Dict[str, Paper]):
        self.graph = graph
        self.papers = papers

    def get_neighborhood(
        self,
        center_node: str,
        max_depth: int = 2,
        max_nodes: int = 50
    ) -> SubGraphData:
        if center_node not in self.graph:
            return SubGraphData(center_node=center_node, nodes=[], edges=[], depth_reached=0)

        visited = {center_node: 0}
        queue = deque([(center_node, 0)])
        nodes = [center_node]
        edges = []

        depth_reached = 0

        while queue and len(nodes) < max_nodes:
            current, depth = queue.popleft()
            depth_reached = max(depth_reached, depth)

            if depth >= max_depth:
                continue

            for neighbor in self.graph.neighbors(current):
                if neighbor not in visited and len(nodes) < max_nodes:
                    visited[neighbor] = depth + 1
                    nodes.append(neighbor)
                    queue.append((neighbor, depth + 1))
                    edges.append((current, neighbor))
                elif neighbor in visited:
                    edges.append((current, neighbor))

            for predecessor in self.graph.predecessors(current):
                if predecessor not in visited and len(nodes) < max_nodes:
                    visited[predecessor] = depth + 1
                    nodes.append(predecessor)
                    queue.append((predecessor, depth + 1))
                    edges.append((predecessor, current))
                elif predecessor in visited:
                    edges.append((predecessor, current))

        graph_nodes = []
        for node_id in nodes:
            node_data = self.graph.nodes.get(node_id, {})
            graph_nodes.append(GraphNode(
                id=node_id,
                label=node_data.get('title', node_id)[:30] + '...',
                title=node_data.get('title', 'Untitled'),
                year=node_data.get('year', 2020),
                citations=node_data.get('citations', 0),
                pagerank=node_data.get('pagerank', 0.0),
                h_index=node_data.get('h_index', 0),
                group=node_data.get('group', 0)
            ))

        graph_edges = []
        for source, target in set(edges):
            graph_edges.append(GraphEdge(
                source=source,
                target=target,
                value=1.0
            ))

        return SubGraphData(
            center_node=center_node,
            nodes=graph_nodes,
            edges=graph_edges,
            depth_reached=depth_reached
        )


class LayeredGraphRenderer:
    def __init__(self, graph: nx.DiGraph, hierarchy: MultiGranularClusters):
        self.graph = graph
        self.hierarchy = hierarchy
        self.expanded_clusters: Set[Tuple[int, int]] = set()

    def get_layered_view(self, level: int) -> Tuple[List[str], List[Tuple[str, str]]]:
        if level not in self.hierarchy.levels:
            return list(self.graph.nodes()), list(self.graph.edges())

        communities = self.hierarchy.communities.get(level, {})

        visible_nodes = set()
        visible_edges = set()

        for comm_id, community in communities.items():
            cluster_key = (level, comm_id)

            if cluster_key in self.expanded_clusters:
                visible_nodes.update(community.nodes)
                for node in community.nodes:
                    for neighbor in self.graph.neighbors(node):
                        if neighbor in visible_nodes:
                            visible_edges.add((node, neighbor))
            else:
                cluster_rep = f"L{level}-C{comm_id}"
                visible_nodes.add(cluster_rep)

        for (src, tgt) in self.graph.edges():
            src_comm = self.hierarchy.node_community_map.get(src, {}).get(level)
            tgt_comm = self.hierarchy.node_community_map.get(tgt, {}).get(level)

            if src_comm is not None and tgt_comm is not None and src_comm != tgt_comm:
                src_cluster = f"L{level}-C{src_comm}"
                tgt_cluster = f"L{level}-C{tgt_comm}"
                if (level, src_comm) not in self.expanded_clusters and \
                   (level, tgt_comm) not in self.expanded_clusters:
                    visible_edges.add((src_cluster, tgt_cluster))

        return list(visible_nodes), list(visible_edges)

    def expand_cluster(self, level: int, cluster_id: int):
        self.expanded_clusters.add((level, cluster_id))

    def collapse_cluster(self, level: int, cluster_id: int):
        self.expanded_clusters.discard((level, cluster_id))
