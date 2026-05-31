import type {
  Paper,
  GraphData,
  HierarchicalGraphData,
  GraphNode,
  GraphEdge,
  InfluenceMetrics,
  TrendData,
  KeywordTrend,
  MultiGranularClusters,
  HierarchicalCommunity,
  ApiResponse,
  PaperRecommendations,
  RecommendedPaper,
  CollaborationNetwork,
  CollaboratorInfo,
  CitationPrediction,
} from '@/types';

const mockAuthors = [
  { name: 'Alice Johnson', orcid: '0000-0001-2345-6789', affiliation: 'Stanford University' },
  { name: 'Bob Smith', orcid: '0000-0002-3456-7890', affiliation: 'MIT' },
  { name: 'Carol Williams', orcid: '0000-0003-4567-8901', affiliation: 'Harvard University' },
  { name: 'David Brown', orcid: '0000-0004-5678-9012', affiliation: 'UC Berkeley' },
  { name: 'Eva Martinez', orcid: '0000-0005-6789-0123', affiliation: 'CMU' },
  { name: 'Frank Lee', orcid: '0000-0006-7890-1234', affiliation: 'Oxford University' },
  { name: 'Grace Kim', orcid: '0000-0007-8901-2345', affiliation: 'Cambridge University' },
  { name: 'Henry Chen', orcid: '0000-0008-9012-3456', affiliation: 'Tsinghua University' },
];

const mockTitles = [
  'Deep Learning for Natural Language Processing: A Comprehensive Survey',
  'Attention Is All You Need: Transformer Architectures',
  'Graph Neural Networks: A Review of Methods and Applications',
  'BERT: Pre-training of Deep Bidirectional Transformers',
  'Generative Adversarial Networks: An Overview',
  'Reinforcement Learning in Robotics: A Survey',
  'Federated Learning: Challenges, Methods, and Future Directions',
  'Knowledge Graphs: Opportunities and Challenges',
  'Explainable Artificial Intelligence (XAI): Concepts, Taxonomies',
  'Large Language Models: A Survey and Taxonomy',
  'Self-Supervised Learning: A New Paradigm in Computer Vision',
  'Multi-Modal Learning: Fusion Strategies and Applications',
  'Efficient Transformers: A Survey',
  'Prompt Engineering for Large Language Models',
  'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks',
];

const mockVenues = [
  'Nature',
  'Science',
  'NeurIPS',
  'ICML',
  'ACL',
  'CVPR',
  'ICLR',
  'KDD',
  'WWW',
  'AAAI',
  'IEEE TPAMI',
  'ACM Computing Surveys',
];

const mockKeywords = [
  'deep learning',
  'neural networks',
  'natural language processing',
  'computer vision',
  'transformer',
  'graph neural networks',
  'reinforcement learning',
  'federated learning',
  'knowledge graph',
  'explainable AI',
  'large language models',
  'self-supervised learning',
  'multi-modal learning',
  'prompt engineering',
  'retrieval-augmented generation',
  'machine learning',
  'artificial intelligence',
  'data mining',
  'computer science',
  'algorithm',
];

function generateDOI(index: number): string {
  return `10.1234/mock.${index.toString().padStart(5, '0')}`;
}

function randomChoice<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomFloat(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

export function generateMockPapers(count: number = 20): Paper[] {
  const papers: Paper[] = [];
  
  for (let i = 0; i < count; i++) {
    const numAuthors = randomInt(2, 4);
    const authors = [];
    for (let j = 0; j < numAuthors; j++) {
      authors.push(mockAuthors[(i + j) % mockAuthors.length]);
    }

    const numKeywords = randomInt(3, 6);
    const keywords = [];
    for (let j = 0; j < numKeywords; j++) {
      keywords.push(mockKeywords[(i * 3 + j) % mockKeywords.length]);
    }

    const numReferences = randomInt(5, 15);
    const references = [];
    for (let j = 0; j < numReferences; j++) {
      const refIdx = (i * 2 + j) % count;
      if (refIdx !== i) {
        references.push(generateDOI(refIdx));
      }
    }

    papers.push({
      doi: generateDOI(i),
      title: mockTitles[i % mockTitles.length],
      authors,
      year: randomInt(2018, 2024),
      venue: randomChoice(mockVenues),
      abstract: `This paper presents a comprehensive study on ${keywords[0]} and ${keywords[1]}. We propose a novel approach that combines ${keywords[2]} with ${keywords[3]} to achieve state-of-the-art performance. Our method is evaluated on multiple benchmark datasets and demonstrates significant improvements over existing techniques.`,
      keywords,
      references,
      citations: randomInt(10, 500),
      url: `https://doi.org/${generateDOI(i)}`,
      source: randomChoice(['crossref', 'dblp']),
    });
  }

  return papers;
}

export function generateMockGraphData(nodeCount: number = 50): GraphData {
  const papers = generateMockPapers(nodeCount);
  
  const nodes: GraphNode[] = papers.map((paper, index) => {
    const pagerank = randomFloat(0.001, 0.05);
    const h_index = randomInt(5, 100);
    
    return {
      id: paper.doi,
      label: paper.title.substring(0, 30) + '...',
      title: paper.title,
      year: paper.year,
      citations: paper.citations,
      pagerank,
      h_index,
      group: randomInt(1, 5),
    };
  });

  const edges: GraphEdge[] = [];
  const edgeSet = new Set<string>();

  for (let i = 0; i < nodeCount; i++) {
    const numEdges = randomInt(2, 8);
    for (let j = 0; j < numEdges; j++) {
      const target = randomInt(0, nodeCount - 1);
      if (target !== i) {
        const edgeKey = `${i}-${target}`;
        if (!edgeSet.has(edgeKey)) {
          edgeSet.add(edgeKey);
          edges.push({
            source: nodes[i].id,
            target: nodes[target].id,
            value: randomFloat(0.5, 2.0),
          });
        }
      }
    }
  }

  const totalEdges = edges.length;
  const avgDegree = (2 * totalEdges) / nodeCount;
  const maxPossibleEdges = nodeCount * (nodeCount - 1);
  const density = totalEdges / maxPossibleEdges;
  const communities = new Set(nodes.map((n) => n.group)).size;

  return {
    nodes,
    edges,
    stats: {
      total_nodes: nodeCount,
      total_edges: totalEdges,
      avg_degree: avgDegree,
      density: density,
      communities: communities,
    },
    graph_id: 'mock-graph-' + Date.now(),
  };
}

export function generateMockInfluenceRanking(count: number = 30): InfluenceMetrics[] {
  const rankings: InfluenceMetrics[] = [];
  
  for (let i = 0; i < count; i++) {
    const pagerank = randomFloat(0.01, 0.1);
    const h_index = randomInt(20, 150);
    const citations = randomInt(100, 5000);
    const isCore = i < Math.floor(count * 0.2);

    const coreReasons = [
      '高PageRank值，领域权威论文',
      '高H指数，作者学术影响力强',
      '高引用量，被广泛认可',
      '中介中心性高，连接不同研究领域',
    ];

    rankings.push({
      doi: generateDOI(i),
      title: mockTitles[i % mockTitles.length],
      pagerank: pagerank,
      pagerank_rank: i + 1,
      h_index: h_index,
      h_index_rank: randomInt(1, count),
      citations: citations,
      citations_rank: randomInt(1, count),
      betweenness_centrality: randomFloat(0, 0.5),
      closeness_centrality: randomFloat(0.3, 0.8),
      is_core: isCore,
      core_reason: isCore ? randomChoice(coreReasons) : undefined,
    });
  }

  return rankings.sort((a, b) => b.pagerank - a.pagerank);
}

export function generateMockTrendData(startYear: number = 2010, endYear: number = 2024): TrendData[] {
  const trends: TrendData[] = [];
  
  for (let year = startYear; year <= endYear; year++) {
    const yearFactor = (year - startYear) / (endYear - startYear);
    const baseCount = 100 + yearFactor * 500;
    
    trends.push({
      year,
      paper_count: Math.floor(baseCount + randomFloat(-50, 50)),
      citation_count: Math.floor(baseCount * 10 + randomFloat(-200, 200)),
      avg_citations: parseFloat((10 + yearFactor * 5 + randomFloat(-1, 2)).toFixed(2)),
    });
  }

  return trends;
}

export function generateMockKeywordTrends(count: number = 20): KeywordTrend[] {
  const trends: KeywordTrend[] = [];
  const trendTypes: Array<'rising' | 'stable' | 'declining'> = ['rising', 'stable', 'declining'];

  for (let i = 0; i < count; i++) {
    const trend = i < count * 0.4 ? 'rising' : i < count * 0.7 ? 'stable' : 'declining';
    
    trends.push({
      keyword: mockKeywords[i % mockKeywords.length],
      count: randomInt(50, 500),
      trend: trend,
      growth_rate: trend === 'rising' 
        ? parseFloat(randomFloat(10, 50).toFixed(1))
        : trend === 'stable'
        ? parseFloat(randomFloat(-5, 5).toFixed(1))
        : parseFloat(randomFloat(-30, -10).toFixed(1)),
    });
  }

  return trends.sort((a, b) => b.count - a.count);
}

export function generateMockClusters(): MultiGranularClusters {
  const levels = [0, 1, 2];
  const communities: Record<number, Record<number, HierarchicalCommunity>> = {};
  const nodeCommunityMap: Record<string, Record<number, number>> = {};

  const clusterCounts = { 0: 3, 1: 6, 2: 12 };
  const clusterKeywords = [
    ['deep learning', 'neural networks', 'transformer'],
    ['nlp', 'language model', 'bert'],
    ['computer vision', 'image classification', 'cnn'],
    ['reinforcement learning', 'q-learning', 'policy gradient'],
    ['graph neural networks', 'gcn', 'gat'],
    ['federated learning', 'privacy', 'distributed'],
  ];

  for (const level of levels) {
    communities[level] = {};
    const numClusters = clusterCounts[level as keyof typeof clusterCounts];

    for (let i = 0; i < numClusters; i++) {
      const size = Math.max(5, Math.floor(60 / numClusters));
      const nodes: string[] = [];

      for (let j = 0; j < size; j++) {
        const nodeIdx = i * size + j;
        if (nodeIdx < 60) {
          const nodeId = `10.1234/mock.${nodeIdx.toString().padStart(5, '0')}`;
          nodes.push(nodeId);

          if (!nodeCommunityMap[nodeId]) {
            nodeCommunityMap[nodeId] = {};
          }
          nodeCommunityMap[nodeId][level] = i;
        }
      }

      const parentId = level > 0 ? Math.floor(i / 2) : undefined;
      const children = level < 2 ? [i * 2, i * 2 + 1] : [];

      communities[level][i] = {
        level,
        community_id: i,
        parent_id: parentId,
        nodes,
        children: children.filter((c) => c < (level === 0 ? 6 : level === 1 ? 12 : 0)),
        name: `L${level} Cluster ${i}`,
        size: nodes.length,
        keywords: clusterKeywords[i % clusterKeywords.length],
      };
    }
  }

  return {
    levels,
    communities,
    node_community_map: nodeCommunityMap,
  };
}

export function generateMockHierarchicalGraph(): HierarchicalGraphData {
  const baseGraph = generateMockGraphData(60);
  const hierarchy = generateMockClusters();

  return {
    ...baseGraph,
    hierarchy,
    layer_info: {
      0: [0, 1, 2],
      1: [0, 1, 2, 3, 4, 5],
      2: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    },
  };
}

export const mockApi = {
  async searchPapers(): Promise<ApiResponse<Paper[]>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return {
      success: true,
      data: generateMockPapers(30),
    };
  },

  async buildGraph(): Promise<ApiResponse<GraphData>> {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return {
      success: true,
      data: generateMockGraphData(60),
    };
  },

  async buildHierarchicalGraph(): Promise<ApiResponse<HierarchicalGraphData>> {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    return {
      success: true,
      data: generateMockHierarchicalGraph(),
    };
  },

  async getClusters(): Promise<ApiResponse<MultiGranularClusters>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return {
      success: true,
      data: generateMockClusters(),
    };
  },

  async getClusterPapers(
    level: number,
    clusterId: number,
    limit: number = 20
  ): Promise<ApiResponse<InfluenceMetrics[]>> {
    await new Promise((resolve) => setTimeout(resolve, 400));
    const all = generateMockInfluenceRanking(50);
    const startIdx = clusterId * Math.floor(limit / 2);
    return {
      success: true,
      data: all.slice(startIdx, startIdx + limit),
    };
  },

  async getInfluenceRanking(): Promise<ApiResponse<InfluenceMetrics[]>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return {
      success: true,
      data: generateMockInfluenceRanking(50),
    };
  },

  async getCorePapers(): Promise<ApiResponse<InfluenceMetrics[]>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    const all = generateMockInfluenceRanking(50);
    return {
      success: true,
      data: all.filter((p) => p.is_core),
    };
  },

  async getTrendsOverTime(): Promise<ApiResponse<TrendData[]>> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    return {
      success: true,
      data: generateMockTrendData(),
    };
  },

  async getKeywordTrends(): Promise<ApiResponse<KeywordTrend[]>> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    return {
      success: true,
      data: generateMockKeywordTrends(),
    };
  },

  async getRecommendations(doi: string, limit: number = 20): Promise<ApiResponse<PaperRecommendations>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    const papers = generateMockPapers(limit);
    const reasons = [
      '高参考文献重叠',
      '共同引用关系',
      '直接引用',
      '关键词高度匹配',
      '相同发表期刊',
      '基于内容相似性',
      '综合推荐',
    ];
    
    const recommendations: RecommendedPaper[] = papers.map((paper, index) => ({
      doi: paper.doi,
      title: paper.title,
      authors: paper.authors,
      year: paper.year,
      venue: paper.venue,
      score: randomFloat(0.5, 0.95),
      reason: randomChoice(reasons),
      similarity: randomFloat(0.3, 0.8),
      common_references: generateMockPapers(3).map(p => p.doi),
      common_citations: generateMockPapers(2).map(p => p.doi),
    }));
    
    return {
      success: true,
      data: {
        target_doi: doi,
        recommendations,
        algorithm: 'hybrid',
      },
    };
  },

  async getCollaborators(authorName: string, limit: number = 20): Promise<ApiResponse<CollaborationNetwork>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    const existingCount = randomInt(3, 8);
    const potentialCount = randomInt(10, limit);
    
    const existing_collaborators: CollaboratorInfo[] = Array.from({ length: existingCount }, (_, i) => {
      const author = randomChoice(mockAuthors);
      return {
        name: author.name,
        orcid: author.orcid,
        affiliation: author.affiliation,
        paper_count: randomInt(2, 15),
        collaboration_score: randomFloat(0.6, 0.95),
        common_papers: Array.from({ length: randomInt(2, 5) }, (_, j) => generateDOI(i * 100 + j)),
        research_overlap: Array.from({ length: 3 }, () => randomChoice(mockKeywords)),
        potential_impact: randomFloat(5, 15),
        match_reason: '已共同发表多篇论文',
      };
    });
    
    const potential_collaborators: CollaboratorInfo[] = Array.from({ length: potentialCount }, (_, i) => {
      const author = mockAuthors[(i + existingCount) % mockAuthors.length];
      const reasons = [
        `${randomInt(3, 10)} 篇共同参考文献`,
        `${randomInt(2, 8)} 个共同引用`,
        `${randomInt(2, 5)} 个研究主题重叠`,
        '基于研究相似性',
      ];
      return {
        name: author.name,
        orcid: author.orcid,
        affiliation: author.affiliation,
        paper_count: randomInt(5, 50),
        collaboration_score: randomFloat(0.3, 0.75),
        common_papers: Array.from({ length: randomInt(1, 3) }, (_, j) => generateDOI(i * 50 + j)),
        research_overlap: Array.from({ length: randomInt(2, 4) }, () => randomChoice(mockKeywords)),
        potential_impact: randomFloat(3, 10),
        match_reason: randomChoice(reasons),
      };
    });
    
    return {
      success: true,
      data: {
        target_author: authorName,
        existing_collaborators,
        potential_collaborators,
      },
    };
  },

  async getCitationPrediction(doi: string): Promise<ApiResponse<CitationPrediction>> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    
    const papers = generateMockPapers(1);
    const paper = papers[0];
    const currentCitations = paper.citations;
    const age = randomFloat(0.5, 10);
    
    const growthFactors = [
      '发表于顶级期刊/会议',
      '引用增长速度快',
      '近期影响力上升趋势明显',
      '参考文献质量高',
      '作者团队影响力高',
    ];
    
    return {
      success: true,
      data: {
        doi,
        title: paper.title,
        current_citations: currentCitations,
        age_years: age,
        predicted_citations_1y: Math.round(currentCitations * randomFloat(1.2, 1.5)),
        predicted_citations_3y: Math.round(currentCitations * randomFloat(1.6, 2.5)),
        predicted_citations_5y: Math.round(currentCitations * randomFloat(2.0, 4.0)),
        confidence_score: randomFloat(0.5, 0.9),
        growth_rate: randomFloat(0.1, 0.5),
        key_factors: Array.from({ length: randomInt(2, 4) }, () => randomChoice(growthFactors)),
      },
    };
  },

  async getBatchCitationPrediction(dois: string[]): Promise<ApiResponse<{ predictions: CitationPrediction[]; model_version: string; prediction_date: string }>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    const predictions: CitationPrediction[] = dois.map((doi) => {
      const paper = generateMockPapers(1)[0];
      const currentCitations = paper.citations;
      const age = randomFloat(0.5, 10);
      
      const growthFactors = [
        '发表于顶级期刊/会议',
        '引用增长速度快',
        '近期影响力上升趋势明显',
        '参考文献质量高',
        '作者团队影响力高',
      ];
      
      return {
        doi,
        title: paper.title,
        current_citations: currentCitations,
        age_years: age,
        predicted_citations_1y: Math.round(currentCitations * randomFloat(1.2, 1.5)),
        predicted_citations_3y: Math.round(currentCitations * randomFloat(1.6, 2.5)),
        predicted_citations_5y: Math.round(currentCitations * randomFloat(2.0, 4.0)),
        confidence_score: randomFloat(0.5, 0.9),
        growth_rate: randomFloat(0.1, 0.5),
        key_factors: Array.from({ length: randomInt(2, 4) }, () => randomChoice(growthFactors)),
      };
    });
    
    return {
      success: true,
      data: {
        predictions,
        model_version: '1.0.0',
        prediction_date: new Date().toISOString(),
      },
    };
  },

  async getTrendingPapers(limit: number = 20): Promise<ApiResponse<CitationPrediction[]>> {
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    const papers = generateMockPapers(limit);
    const predictions: CitationPrediction[] = papers.map((paper) => {
      const currentCitations = paper.citations;
      const age = randomFloat(0.5, 5);
      
      const growthFactors = [
        '发表于顶级期刊/会议',
        '引用增长速度快',
        '近期影响力上升趋势明显',
        '参考文献质量高',
        '作者团队影响力高',
      ];
      
      return {
        doi: paper.doi,
        title: paper.title,
        current_citations: currentCitations,
        age_years: age,
        predicted_citations_1y: Math.round(currentCitations * randomFloat(1.5, 2.0)),
        predicted_citations_3y: Math.round(currentCitations * randomFloat(2.0, 3.5)),
        predicted_citations_5y: Math.round(currentCitations * randomFloat(2.5, 5.0)),
        confidence_score: randomFloat(0.6, 0.95),
        growth_rate: randomFloat(0.3, 0.8),
        key_factors: Array.from({ length: randomInt(2, 4) }, () => randomChoice(growthFactors)),
      };
    });
    
    predictions.sort((a, b) => b.growth_rate - a.growth_rate);
    
    return {
      success: true,
      data: predictions,
    };
  },
};
