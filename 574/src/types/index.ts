export interface Author {
  name: string;
  orcid?: string;
  affiliation?: string;
}

export interface Paper {
  doi: string;
  title: string;
  authors: Author[];
  year: number;
  venue: string;
  abstract?: string;
  keywords?: string[];
  references: string[];
  citations: number;
  url?: string;
  source: 'crossref' | 'dblp';
}

export interface GraphNode {
  id: string;
  label: string;
  title: string;
  year: number;
  citations: number;
  pagerank: number;
  h_index: number;
  group: number;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  value: number;
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  avg_degree: number;
  density: number;
  communities: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: GraphStats;
  graph_id?: string;
}

export interface InfluenceMetrics {
  doi: string;
  title: string;
  pagerank: number;
  pagerank_rank: number;
  h_index: number;
  h_index_rank: number;
  citations: number;
  citations_rank: number;
  betweenness_centrality?: number;
  closeness_centrality?: number;
  is_core: boolean;
  core_reason?: string;
}

export interface TrendData {
  year: number;
  paper_count: number;
  citation_count: number;
  avg_citations: number;
}

export interface KeywordTrend {
  keyword: string;
  count: number;
  trend: 'rising' | 'stable' | 'declining';
  growth_rate: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface GraphBuildRequest {
  dois: string[];
  depth: number;
  max_nodes: number;
}

export type SourceType = 'crossref' | 'dblp';
export type RankingMetric = 'pagerank' | 'h_index' | 'citations';

export interface SearchState {
  query: string;
  source: SourceType;
  results: Paper[];
  loading: boolean;
  selectedPapers: Paper[];
}

export interface HierarchicalCommunity {
  level: number;
  community_id: number;
  parent_id?: number;
  nodes: string[];
  children: number[];
  name?: string;
  size: number;
  keywords: string[];
}

export interface MultiGranularClusters {
  levels: number[];
  communities: Record<number, Record<number, HierarchicalCommunity>>;
  node_community_map: Record<string, Record<number, number>>;
}

export interface SubGraphRequest {
  node_id: string;
  max_depth?: number;
  max_nodes?: number;
}

export interface SubGraphData {
  center_node: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  depth_reached: number;
}

export interface HierarchicalGraphData extends GraphData {
  hierarchy?: MultiGranularClusters;
  layer_info?: Record<number, number[]>;
}

export interface RecommendedPaper {
  doi: string;
  title: string;
  authors: Author[];
  year: number;
  venue: string;
  score: number;
  reason: string;
  similarity: number;
  common_references: string[];
  common_citations: string[];
}

export interface PaperRecommendations {
  target_doi: string;
  recommendations: RecommendedPaper[];
  algorithm: string;
}

export interface CollaboratorInfo {
  name: string;
  orcid?: string;
  affiliation?: string;
  paper_count: number;
  collaboration_score: number;
  common_papers: string[];
  research_overlap: string[];
  potential_impact: number;
  match_reason: string;
}

export interface CollaborationNetwork {
  target_author: string;
  existing_collaborators: CollaboratorInfo[];
  potential_collaborators: CollaboratorInfo[];
}

export interface CitationPrediction {
  doi: string;
  title: string;
  current_citations: number;
  age_years: number;
  predicted_citations_1y: number;
  predicted_citations_3y: number;
  predicted_citations_5y: number;
  confidence_score: number;
  growth_rate: number;
  key_factors: string[];
}

export interface GraphState {
  graphData: HierarchicalGraphData | null;
  loading: boolean;
  selectedNode: GraphNode | null;
  highlightedNodes: Set<string>;
  expandedCommunities: Set<string>;
  currentLevel: number;
}
