import networkx as nx
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import logging
import uuid

from ..models.schemas import (
    Paper, GraphNode, GraphEdge, GraphData, GraphStats,
    InfluenceMetrics, TrendData, KeywordTrend,
    MultiGranularClusters, SubGraphData, HierarchicalGraphData
)
from .graph_optimizer import (
    SparsePageRank, MultiGranularCommunityDetector, SubGraphExplorer
)

logger = logging.getLogger(__name__)


class GraphAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.papers: Dict[str, Paper] = {}

    def build_graph(self, papers: List[Paper], edges: List[Tuple[str, str]]) -> nx.DiGraph:
        self.graph.clear()
        self.papers = {p.doi: p for p in papers}

        for paper in papers:
            self.graph.add_node(
                paper.doi,
                title=paper.title,
                year=paper.year,
                citations=paper.citations,
                venue=paper.venue,
                authors=[a.name for a in paper.authors]
            )

        for source, target in edges:
            if source in self.papers and target in self.papers:
                self.graph.add_edge(source, target, weight=1.0)

        logger.info(f"Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        return self.graph

    def compute_pagerank(
        self,
        alpha: float = 0.85,
        max_iter: int = 100,
        use_sparse: bool = True
    ) -> Dict[str, float]:
        if self.graph.number_of_nodes() == 0:
            return {}

        if use_sparse:
            sparse_pr = SparsePageRank(alpha=alpha, max_iter=max_iter)
            pagerank_scores = sparse_pr.compute_from_graph(self.graph)
        else:
            pagerank_scores = nx.pagerank(
                self.graph,
                alpha=alpha,
                max_iter=max_iter,
                weight='weight'
            )

        for node, score in pagerank_scores.items():
            if node in self.graph.nodes:
                self.graph.nodes[node]['pagerank'] = score

        logger.info(f"PageRank computed for {len(pagerank_scores)} nodes (sparse={use_sparse})")
        return pagerank_scores

    def detect_hierarchical_communities(self, num_levels: int = 3) -> MultiGranularClusters:
        if self.graph.number_of_nodes() == 0:
            return MultiGranularClusters(
                levels=[],
                communities={},
                node_community_map={}
            )

        undirected = self.graph.to_undirected()
        detector = MultiGranularCommunityDetector(undirected)
        hierarchy = detector.detect_hierarchical(num_levels=num_levels)

        for level in hierarchy.levels:
            for node, comm_map in hierarchy.node_community_map.items():
                if node in self.graph.nodes:
                    self.graph.nodes[node][f'community_level_{level}'] = comm_map.get(level, 0)

        logger.info(f"Hierarchical communities detected: {hierarchy.levels} levels")
        return hierarchy

    def get_subgraph(
        self,
        node_id: str,
        max_depth: int = 2,
        max_nodes: int = 50
    ) -> SubGraphData:
        explorer = SubGraphExplorer(self.graph, self.papers)
        return explorer.get_neighborhood(node_id, max_depth=max_depth, max_nodes=max_nodes)

    def get_core_papers_by_community(
        self,
        hierarchy: MultiGranularClusters,
        level: int = 0,
        limit_per_community: int = 5
    ) -> Dict[int, List[InfluenceMetrics]]:
        rankings = self.compute_influence_rankings()
        result = {}

        if level not in hierarchy.levels:
            return result

        communities = hierarchy.communities.get(level, {})
        for comm_id, community in communities.items():
            comm_papers = [
                r for r in rankings if r.doi in community.nodes
            ]
            comm_papers.sort(key=lambda x: x.pagerank_rank)
            result[comm_id] = comm_papers[:limit_per_community]

        return result

    def compute_h_index(self) -> Dict[str, int]:
        h_indices = {}

        for node in self.graph.nodes():
            in_degree = self.graph.in_degree(node, weight='weight') or 0
            citations_list = []

            for predecessor in self.graph.predecessors(node):
                pred_citations = self.graph.nodes[predecessor].get('citations', 0)
                citations_list.append(pred_citations)

            paper_citations = self.graph.nodes[node].get('citations', in_degree)
            citations_list.append(paper_citations)

            citations_list.sort(reverse=True)
            h_index = 0
            for i, c in enumerate(citations_list, 1):
                if c >= i:
                    h_index = i
                else:
                    break

            h_indices[node] = h_index
            self.graph.nodes[node]['h_index'] = h_index

        return h_indices

    def compute_centrality(self) -> Dict[str, Dict[str, float]]:
        centralities = {}

        if self.graph.number_of_nodes() < 2:
            return centralities

        try:
            betweenness = nx.betweenness_centrality(self.graph, k=min(50, self.graph.number_of_nodes()))
            closeness = nx.closeness_centrality(self.graph)

            for node in self.graph.nodes():
                centralities[node] = {
                    'betweenness': betweenness.get(node, 0.0),
                    'closeness': closeness.get(node, 0.0)
                }
                self.graph.nodes[node]['betweenness'] = betweenness.get(node, 0.0)
                self.graph.nodes[node]['closeness'] = closeness.get(node, 0.0)
        except Exception as e:
            logger.warning(f"Centrality computation error: {e}")

        return centralities

    def detect_communities(self) -> Dict[str, int]:
        try:
            undirected = self.graph.to_undirected()
            communities = nx.algorithms.community.greedy_modularity_communities(undirected)

            community_map = {}
            for i, community in enumerate(communities):
                for node in community:
                    community_map[node] = i
                    self.graph.nodes[node]['group'] = i

            logger.info(f"Detected {len(communities)} communities")
            return community_map
        except Exception as e:
            logger.warning(f"Community detection error: {e}")
            return {node: 0 for node in self.graph.nodes()}

    def compute_influence_rankings(self) -> List[InfluenceMetrics]:
        pagerank = self.compute_pagerank()
        h_index = self.compute_h_index()
        centrality = self.compute_centrality()

        nodes = list(self.graph.nodes())

        pagerank_sorted = sorted(nodes, key=lambda n: pagerank.get(n, 0), reverse=True)
        h_index_sorted = sorted(nodes, key=lambda n: h_index.get(n, 0), reverse=True)
        citations_sorted = sorted(nodes, key=lambda n: self.graph.nodes[n].get('citations', 0), reverse=True)

        pagerank_ranks = {n: i + 1 for i, n in enumerate(pagerank_sorted)}
        h_index_ranks = {n: i + 1 for i, n in enumerate(h_index_sorted)}
        citations_ranks = {n: i + 1 for i, n in enumerate(citations_sorted)}

        rankings = []
        for node in nodes:
            node_data = self.graph.nodes[node]
            paper = self.papers.get(node)

            pr = pagerank.get(node, 0.0)
            hi = h_index.get(node, 0)
            cit = node_data.get('citations', 0)

            pr_rank = pagerank_ranks.get(node, len(nodes))
            hi_rank = h_index_ranks.get(node, len(nodes))
            cit_rank = citations_ranks.get(node, len(nodes))

            cent = centrality.get(node, {})

            is_core, reason = self._is_core_paper(node, pr, hi, cit, pr_rank, hi_rank, cit_rank)

            rankings.append(InfluenceMetrics(
                doi=node,
                title=node_data.get('title', 'Untitled'),
                pagerank=pr,
                pagerank_rank=pr_rank,
                h_index=hi,
                h_index_rank=hi_rank,
                citations=cit,
                citations_rank=cit_rank,
                betweenness_centrality=cent.get('betweenness'),
                closeness_centrality=cent.get('closeness'),
                is_core=is_core,
                core_reason=reason
            ))

        return sorted(rankings, key=lambda x: x.pagerank_rank)

    def _is_core_paper(
        self,
        node: str,
        pagerank: float,
        h_index: int,
        citations: int,
        pr_rank: int,
        hi_rank: int,
        cit_rank: int,
        threshold: float = 0.1
    ) -> Tuple[bool, Optional[str]]:
        total_nodes = self.graph.number_of_nodes()
        if total_nodes == 0:
            return False, None

        reasons = []

        if pr_rank <= max(1, int(total_nodes * threshold)):
            reasons.append(f"PageRank排名前{int(threshold * 100)}%")

        if hi_rank <= max(1, int(total_nodes * threshold)):
            reasons.append(f"H指数排名前{int(threshold * 100)}%")

        if cit_rank <= max(1, int(total_nodes * threshold)):
            reasons.append(f"引用量排名前{int(threshold * 100)}%")

        in_degree = self.graph.in_degree(node)
        out_degree = self.graph.out_degree(node)
        if in_degree > total_nodes * 0.1 or out_degree > total_nodes * 0.1:
            reasons.append("高连接度节点")

        is_core = len(reasons) >= 2
        reason = "; ".join(reasons) if reasons else None

        return is_core, reason

    def get_core_papers(self, method: str = 'pagerank', limit: int = 20) -> List[InfluenceMetrics]:
        rankings = self.compute_influence_rankings()
        core_papers = [r for r in rankings if r.is_core]

        if method == 'pagerank':
            core_papers.sort(key=lambda x: x.pagerank_rank)
        elif method == 'h_index':
            core_papers.sort(key=lambda x: x.h_index_rank)
        elif method == 'citations':
            core_papers.sort(key=lambda x: x.citations_rank)
        elif method == 'community':
            communities = self.detect_communities()
            community_core = {}
            for r in rankings:
                comm = communities.get(r.doi, 0)
                if comm not in community_core or r.pagerank > community_core[comm].pagerank:
                    community_core[comm] = r
            core_papers = list(community_core.values())
            core_papers.sort(key=lambda x: x.pagerank_rank)

        return core_papers[:limit]

    def get_graph_stats(self) -> GraphStats:
        G = self.graph
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()

        if total_nodes > 1:
            avg_degree = (2 * total_edges) / total_nodes
            density = nx.density(G)
        else:
            avg_degree = 0.0
            density = 0.0

        try:
            communities = len(set(nx.algorithms.community.greedy_modularity_communities(G.to_undirected())))
        except:
            communities = 1

        return GraphStats(
            total_nodes=total_nodes,
            total_edges=total_edges,
            avg_degree=avg_degree,
            density=density,
            communities=communities
        )

    def export_graph_data(self, include_hierarchy: bool = True) -> HierarchicalGraphData:
        self.compute_pagerank(use_sparse=True)
        self.compute_h_index()
        self.detect_communities()

        hierarchy = None
        if include_hierarchy:
            hierarchy = self.detect_hierarchical_communities(num_levels=3)

        nodes = []
        for node, data in self.graph.nodes(data=True):
            label = data.get('title', node)
            if len(label) > 50:
                label = label[:47] + "..."

            nodes.append(GraphNode(
                id=node,
                label=label,
                title=data.get('title', 'Untitled'),
                year=data.get('year', 2020),
                citations=data.get('citations', 0),
                pagerank=data.get('pagerank', 0.0),
                h_index=data.get('h_index', 0),
                group=data.get('group', 0)
            ))

        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append(GraphEdge(
                source=source,
                target=target,
                value=data.get('weight', 1.0)
            ))

        stats = self.get_graph_stats()

        layer_info = {}
        if hierarchy:
            for level in hierarchy.levels:
                communities = hierarchy.communities.get(level, {})
                layer_info[level] = sorted(communities.keys())

        return HierarchicalGraphData(
            nodes=nodes,
            edges=edges,
            stats=stats,
            graph_id=str(uuid.uuid4()),
            hierarchy=hierarchy,
            layer_info=layer_info
        )

    def analyze_trends(self, start_year: int = 2010, end_year: int = 2025) -> List[TrendData]:
        year_data = defaultdict(lambda: {'paper_count': 0, 'citation_count': 0})

        for node, data in self.graph.nodes(data=True):
            year = data.get('year')
            if year and start_year <= year <= end_year:
                year_data[year]['paper_count'] += 1
                year_data[year]['citation_count'] += data.get('citations', 0)

        trends = []
        for year in range(start_year, end_year + 1):
            data = year_data.get(year, {'paper_count': 0, 'citation_count': 0})
            avg_cit = data['citation_count'] / data['paper_count'] if data['paper_count'] > 0 else 0
            trends.append(TrendData(
                year=year,
                paper_count=data['paper_count'],
                citation_count=data['citation_count'],
                avg_citations=avg_cit
            ))

        return trends

    def extract_keyword_trends(self, limit: int = 30) -> List[KeywordTrend]:
        all_keywords = []

        for paper in self.papers.values():
            if paper.keywords:
                all_keywords.extend(paper.keywords)
            if paper.title:
                words = paper.title.lower().split()
                all_keywords.extend([w for w in words if len(w) > 3])

        keyword_counts = defaultdict(int)
        for kw in all_keywords:
            kw_clean = kw.strip().lower()
            if len(kw_clean) > 2:
                keyword_counts[kw_clean] += 1

        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        recent_year = max(p.year for p in self.papers.values()) if self.papers else 2025
        older_year = recent_year - 5

        recent_counts = defaultdict(int)
        older_counts = defaultdict(int)

        for paper in self.papers.values():
            kws = []
            if paper.keywords:
                kws.extend([k.lower() for k in paper.keywords])
            if paper.title:
                kws.extend([w.lower() for w in paper.title.split() if len(w) > 3])

            for kw in kws:
                kw_clean = kw.strip().lower()
                if paper.year >= recent_year - 2:
                    recent_counts[kw_clean] += 1
                elif paper.year <= older_year:
                    older_counts[kw_clean] += 1

        trends = []
        for kw, count in sorted_keywords:
            recent = recent_counts.get(kw, 0)
            older = older_counts.get(kw, 1)
            growth_rate = (recent - older) / older if older > 0 else float('inf')

            if growth_rate > 0.2:
                trend = 'rising'
            elif growth_rate < -0.2:
                trend = 'declining'
            else:
                trend = 'stable'

            trends.append(KeywordTrend(
                keyword=kw,
                count=count,
                trend=trend,
                growth_rate=growth_rate
            ))

        return trends

    def get_paper_references(self, doi: str) -> List[str]:
        if doi not in self.graph:
            return []
        return list(self.graph.successors(doi))

    def get_paper_citations(self, doi: str) -> List[str]:
        if doi not in self.graph:
            return []
        return list(self.graph.predecessors(doi))
