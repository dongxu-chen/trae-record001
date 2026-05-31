from neo4j import GraphDatabase, Driver, Session
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime
import json

from ..config import settings
from ..models.schemas import Paper, Author, GraphData, GraphNode, GraphEdge, InfluenceMetrics, SourceType

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self.driver: Optional[Driver] = None
        self._connect()
        self._initialize_indexes()

    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            logger.info("Connected to Neo4j successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def _initialize_indexes(self):
        if not self.driver:
            return

        index_queries = [
            "CREATE INDEX paper_doi IF NOT EXISTS FOR (p:Paper) ON (p.doi)",
            "CREATE INDEX paper_title IF NOT EXISTS FOR (p:Paper) ON (p.title)",
            "CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year)",
            "CREATE INDEX author_orcid IF NOT EXISTS FOR (a:Author) ON (a.orcid)",
            "CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.name)",
        ]

        try:
            with self.driver.session(database=settings.neo4j_database) as session:
                for query in index_queries:
                    session.run(query)
            logger.info("Neo4j indexes initialized")
        except Exception as e:
            logger.warning(f"Index initialization error: {e}")

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def _get_session(self) -> Optional[Session]:
        if not self.driver:
            self._connect()
        if self.driver:
            return self.driver.session(database=settings.neo4j_database)
        return None

    def save_paper(self, paper: Paper) -> bool:
        session = self._get_session()
        if not session:
            return False

        try:
            with session:
                paper_props = {
                    'doi': paper.doi,
                    'title': paper.title,
                    'year': paper.year,
                    'venue': paper.venue,
                    'abstract': paper.abstract or '',
                    'citations': paper.citations,
                    'url': paper.url or '',
                    'source': paper.source.value if isinstance(paper.source, SourceType) else str(paper.source),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }

                if paper.keywords:
                    paper_props['keywords'] = json.dumps(paper.keywords)

                query = """
                MERGE (p:Paper {doi: $doi})
                SET p += $props
                WITH p
                OPTIONAL MATCH (p)-[r:AUTHORED_BY]->(:Author)
                DELETE r
                """

                for i, author in enumerate(paper.authors):
                    query += f"""
                    MERGE (a{i}:Author {{name: $author_name_{i}}})
                    SET a{i}.orcid = COALESCE($author_orcid_{i}, a{i}.orcid),
                        a{i}.affiliation = COALESCE($author_affiliation_{i}, a{i}.affiliation)
                    MERGE (p)-[:AUTHORED_BY {{order: {i}}}]->(a{i})
                    """

                params = {'doi': paper.doi, 'props': paper_props}
                for i, author in enumerate(paper.authors):
                    params[f'author_name_{i}'] = author.name
                    params[f'author_orcid_{i}'] = author.orcid
                    params[f'author_affiliation_{i}'] = author.affiliation

                session.run(query, params)
                logger.info(f"Saved paper: {paper.doi}")
                return True

        except Exception as e:
            logger.error(f"Error saving paper {paper.doi}: {e}")
            return False

    def save_papers(self, papers: List[Paper]) -> int:
        count = 0
        for paper in papers:
            if self.save_paper(paper):
                count += 1
        return count

    def save_citation(self, citing_doi: str, cited_doi: str, year: Optional[int] = None) -> bool:
        session = self._get_session()
        if not session:
            return False

        try:
            with session:
                query = """
                MATCH (citing:Paper {doi: $citing_doi})
                MATCH (cited:Paper {doi: $cited_doi})
                MERGE (citing)-[r:CITES]->(cited)
                SET r.year = COALESCE($year, r.year)
                RETURN count(r) as count
                """
                result = session.run(query, {'citing_doi': citing_doi, 'cited_doi': cited_doi, 'year': year})
                return result.single()['count'] > 0
        except Exception as e:
            logger.error(f"Error saving citation {citing_doi} -> {cited_doi}: {e}")
            return False

    def save_graph(self, graph_data: GraphData) -> bool:
        session = self._get_session()
        if not session:
            return False

        try:
            with session:
                for node in graph_data.nodes:
                    session.run("""
                        MERGE (p:Paper {doi: $doi})
                        SET p.title = $title,
                            p.year = $year,
                            p.citations = $citations,
                            p.pagerank = $pagerank,
                            p.h_index = $h_index,
                            p.community_group = $group
                    """, {
                        'doi': node.id,
                        'title': node.title,
                        'year': node.year,
                        'citations': node.citations,
                        'pagerank': node.pagerank,
                        'h_index': node.h_index,
                        'group': node.group
                    })

                for edge in graph_data.edges:
                    session.run("""
                        MATCH (source:Paper {doi: $source})
                        MATCH (target:Paper {doi: $target})
                        MERGE (source)-[r:CITES]->(target)
                        SET r.weight = $value
                    """, {
                        'source': edge.source,
                        'target': edge.target,
                        'value': edge.value
                    })

                logger.info(f"Saved graph: {len(graph_data.nodes)} nodes, {len(graph_data.edges)} edges")
                return True
        except Exception as e:
            logger.error(f"Error saving graph: {e}")
            return False

    def get_paper(self, doi: str) -> Optional[Dict[str, Any]]:
        session = self._get_session()
        if not session:
            return None

        try:
            with session:
                result = session.run("""
                    MATCH (p:Paper {doi: $doi})
                    OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                    RETURN p, collect(a) as authors
                """, {'doi': doi})

                record = result.single()
                if not record:
                    return None

                paper_node = record['p']
                authors = record['authors']

                paper_data = dict(paper_node.items())
                paper_data['authors'] = [dict(a.items()) for a in authors]

                if 'keywords' in paper_data and isinstance(paper_data['keywords'], str):
                    paper_data['keywords'] = json.loads(paper_data['keywords'])

                return paper_data
        except Exception as e:
            logger.error(f"Error getting paper {doi}: {e}")
            return None

    def get_references(self, doi: str, limit: int = 100) -> List[Dict[str, Any]]:
        session = self._get_session()
        if not session:
            return []

        try:
            with session:
                result = session.run("""
                    MATCH (p:Paper {doi: $doi})-[:CITES]->(ref:Paper)
                    RETURN ref
                    LIMIT $limit
                """, {'doi': doi, 'limit': limit})

                return [dict(record['ref'].items()) for record in result]
        except Exception as e:
            logger.error(f"Error getting references for {doi}: {e}")
            return []

    def get_citations(self, doi: str, limit: int = 100) -> List[Dict[str, Any]]:
        session = self._get_session()
        if not session:
            return []

        try:
            with session:
                result = session.run("""
                    MATCH (cit:Paper)-[:CITES]->(p:Paper {doi: $doi})
                    RETURN cit
                    LIMIT $limit
                """, {'doi': doi, 'limit': limit})

                return [dict(record['cit'].items()) for record in result]
        except Exception as e:
            logger.error(f"Error getting citations for {doi}: {e}")
            return []

    def compute_pagerank_neo4j(self) -> bool:
        session = self._get_session()
        if not session:
            return False

        try:
            with session:
                session.run("""
                    CALL gds.graph.project(
                        'citationGraph',
                        'Paper',
                        'CITES',
                        {
                            relationshipProperties: 'weight'
                        }
                    )
                """)

                session.run("""
                    CALL gds.pageRank.stream('citationGraph', {
                        relationshipWeightProperty: 'weight',
                        dampingFactor: 0.85,
                        maxIterations: 100
                    })
                    YIELD nodeId, score
                    MATCH (p:Paper) WHERE id(p) = nodeId
                    SET p.pagerank = score
                """)

                session.run("CALL gds.graph.drop('citationGraph')")
                return True
        except Exception as e:
            logger.warning(f"Neo4j PageRank computation error: {e}")
            return False

    def get_influence_rankings(
        self,
        metric: str = 'pagerank',
        limit: int = 50
    ) -> List[InfluenceMetrics]:
        session = self._get_session()
        if not session:
            return []

        sort_field = {
            'pagerank': 'p.pagerank',
            'h_index': 'p.h_index',
            'citations': 'p.citations'
        }.get(metric, 'p.pagerank')

        try:
            with session:
                result = session.run(f"""
                    MATCH (p:Paper)
                    WHERE p.{metric} IS NOT NULL
                    RETURN p
                    ORDER BY {sort_field} DESC
                    LIMIT $limit
                """, {'limit': limit})

                rankings = []
                for i, record in enumerate(result):
                    paper = dict(record['p'].items())
                    rankings.append(InfluenceMetrics(
                        doi=paper.get('doi', ''),
                        title=paper.get('title', 'Untitled'),
                        pagerank=paper.get('pagerank', 0.0),
                        pagerank_rank=i + 1,
                        h_index=paper.get('h_index', 0),
                        h_index_rank=i + 1,
                        citations=paper.get('citations', 0),
                        citations_rank=i + 1,
                        is_core=i < int(limit * 0.1),
                        core_reason=f"{metric}排名第{i + 1}" if i < int(limit * 0.1) else None
                    ))

                return rankings
        except Exception as e:
            logger.error(f"Error getting influence rankings: {e}")
            return []

    def search_papers(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        session = self._get_session()
        if not session:
            return []

        try:
            with session:
                result = session.run("""
                    MATCH (p:Paper)
                    WHERE toLower(p.title) CONTAINS toLower($query)
                       OR ANY(kw IN p.keywords WHERE toLower(kw) CONTAINS toLower($query))
                    OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                    RETURN p, collect(a) as authors
                    ORDER BY p.citations DESC
                    LIMIT $limit
                """, {'query': query, 'limit': limit})

                papers = []
                for record in result:
                    paper_data = dict(record['p'].items())
                    paper_data['authors'] = [dict(a.items()) for a in record['authors']]
                    papers.append(paper_data)

                return papers
        except Exception as e:
            logger.error(f"Error searching papers: {e}")
            return []

    def get_trend_data(self, start_year: int = 2010, end_year: int = 2025) -> List[Dict[str, Any]]:
        session = self._get_session()
        if not session:
            return []

        try:
            with session:
                result = session.run("""
                    MATCH (p:Paper)
                    WHERE p.year >= $start_year AND p.year <= $end_year
                    RETURN p.year as year,
                           count(p) as paper_count,
                           sum(p.citations) as citation_count
                    ORDER BY year
                """, {'start_year': start_year, 'end_year': end_year})

                return [dict(record.items()) for record in result]
        except Exception as e:
            logger.error(f"Error getting trend data: {e}")
            return []

    def get_subgraph(self, center_doi: str, depth: int = 2, max_nodes: int = 200) -> Optional[GraphData]:
        session = self._get_session()
        if not session:
            return None

        try:
            with session:
                result = session.run("""
                    MATCH path = (center:Paper {doi: $doi})-[:CITES*1..$depth]-(connected:Paper)
                    WITH DISTINCT center, connected, path
                    LIMIT $max_nodes
                    WITH collect(DISTINCT center) + collect(DISTINCT connected) as nodes
                    UNWIND nodes as n
                    WITH DISTINCT n
                    OPTIONAL MATCH (n)-[r:CITES]->(m)
                    WHERE (n)-[:CITES*0..$depth]-(:Paper {doi: $doi})
                      AND (m)-[:CITES*0..$depth]-(:Paper {doi: $doi})
                    RETURN collect(DISTINCT n) as node_list,
                           collect(DISTINCT {source: n.doi, target: m.doi, weight: r.weight}) as edge_list
                """, {'doi': center_doi, 'depth': depth, 'max_nodes': max_nodes})

                record = result.single()
                if not record:
                    return None

                nodes = []
                for node in record['node_list']:
                    data = dict(node.items())
                    nodes.append(GraphNode(
                        id=data.get('doi', ''),
                        label=data.get('title', '')[:50],
                        title=data.get('title', 'Untitled'),
                        year=data.get('year', 2020),
                        citations=data.get('citations', 0),
                        pagerank=data.get('pagerank', 0.0),
                        h_index=data.get('h_index', 0),
                        group=data.get('community_group', 0)
                    ))

                edges = []
                for edge in record['edge_list']:
                    if edge['source'] and edge['target']:
                        edges.append(GraphEdge(
                            source=edge['source'],
                            target=edge['target'],
                            value=edge.get('weight', 1.0)
                        ))

                return GraphData(
                    nodes=nodes,
                    edges=edges,
                    stats=GraphStats(
                        total_nodes=len(nodes),
                        total_edges=len(edges),
                        avg_degree=(2 * len(edges)) / max(1, len(nodes)),
                        density=len(edges) / max(1, len(nodes) * (len(nodes) - 1)),
                        communities=len(set(n.group for n in nodes))
                    )
                )
        except Exception as e:
            logger.error(f"Error getting subgraph: {e}")
            return None

    def clear_database(self) -> bool:
        session = self._get_session()
        if not session:
            return False

        try:
            with session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Database cleared")
                return True
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            return False
