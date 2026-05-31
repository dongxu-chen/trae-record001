from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    CROSSREF = "crossref"
    DBLP = "dblp"


class Author(BaseModel):
    name: str
    orcid: Optional[str] = None
    affiliation: Optional[str] = None


class Paper(BaseModel):
    doi: str
    title: str
    authors: List[Author]
    year: int
    venue: str
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    references: List[str] = Field(default_factory=list)
    citations: int = 0
    url: Optional[str] = None
    source: SourceType
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GraphNode(BaseModel):
    id: str
    label: str
    title: str
    year: int
    citations: int
    pagerank: float = 0.0
    h_index: int = 0
    group: int = 0
    x: Optional[float] = None
    y: Optional[float] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    value: float = 1.0


class GraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    avg_degree: float
    density: float
    communities: int


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: GraphStats
    graph_id: Optional[str] = None


class InfluenceMetrics(BaseModel):
    doi: str
    title: str
    pagerank: float
    pagerank_rank: int
    h_index: int
    h_index_rank: int
    citations: int
    citations_rank: int
    betweenness_centrality: Optional[float] = None
    closeness_centrality: Optional[float] = None
    is_core: bool = False
    core_reason: Optional[str] = None


class TrendData(BaseModel):
    year: int
    paper_count: int
    citation_count: int
    avg_citations: float


class KeywordTrend(BaseModel):
    keyword: str
    count: int
    trend: str
    growth_rate: float


class ApiResponse[T](BaseModel):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None


class GraphBuildRequest(BaseModel):
    dois: List[str]
    depth: int = Field(default=2, ge=1, le=5)
    max_nodes: int = Field(default=200, ge=10, le=1000)


class SearchRequest(BaseModel):
    q: str
    source: SourceType = SourceType.CROSSREF
    limit: int = Field(default=20, ge=1, le=100)


class RankingMetric(str, Enum):
    PAGERANK = "pagerank"
    H_INDEX = "h_index"
    CITATIONS = "citations"


class HierarchicalCommunity(BaseModel):
    level: int
    community_id: int
    parent_id: Optional[int] = None
    nodes: List[str] = Field(default_factory=list)
    children: List[int] = Field(default_factory=list)
    name: Optional[str] = None
    size: int = 0
    keywords: List[str] = Field(default_factory=list)


class MultiGranularClusters(BaseModel):
    levels: List[int] = Field(default_factory=list)
    communities: Dict[int, Dict[int, HierarchicalCommunity]] = Field(default_factory=dict)
    node_community_map: Dict[str, Dict[int, int]] = Field(default_factory=dict)

    def get_community(self, level: int, community_id: int) -> Optional[HierarchicalCommunity]:
        return self.communities.get(level, {}).get(community_id)

    def get_node_communities(self, node_id: str) -> Dict[int, int]:
        return self.node_community_map.get(node_id, {})


class GraphLayer(BaseModel):
    level: int
    nodes: List[str] = Field(default_factory=list)
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    is_expanded: bool = False


class SubGraphRequest(BaseModel):
    node_id: str
    max_depth: int = Field(default=2, ge=1, le=3)
    max_nodes: int = Field(default=50, ge=10, le=200)


class SubGraphData(BaseModel):
    center_node: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    depth_reached: int = 0


class HierarchicalGraphData(GraphData):
    hierarchy: Optional[MultiGranularClusters] = None
    layer_info: Dict[int, List[int]] = Field(default_factory=dict)


class RecommendedPaper(BaseModel):
    doi: str
    title: str
    authors: List[Author]
    year: int
    venue: str
    score: float
    reason: str
    similarity: float
    common_references: List[str] = Field(default_factory=list)
    common_citations: List[str] = Field(default_factory=list)


class PaperRecommendations(BaseModel):
    target_doi: str
    recommendations: List[RecommendedPaper]
    algorithm: str


class CollaboratorInfo(BaseModel):
    name: str
    orcid: Optional[str] = None
    affiliation: Optional[str] = None
    paper_count: int
    collaboration_score: float
    common_papers: List[str] = Field(default_factory=list)
    research_overlap: List[str] = Field(default_factory=list)
    potential_impact: float
    match_reason: str


class CollaborationNetwork(BaseModel):
    target_author: str
    existing_collaborators: List[CollaboratorInfo]
    potential_collaborators: List[CollaboratorInfo]


class CitationPrediction(BaseModel):
    doi: str
    title: str
    current_citations: int
    age_years: float
    predicted_citations_1y: int
    predicted_citations_3y: int
    predicted_citations_5y: int
    confidence_score: float
    growth_rate: float
    key_factors: List[str] = Field(default_factory=list)


class BatchCitationPrediction(BaseModel):
    predictions: List[CitationPrediction]
    model_version: str
    prediction_date: str
