import axios from 'axios';
import { mockApi } from './mockData';
import type {
  Paper,
  GraphData,
  HierarchicalGraphData,
  InfluenceMetrics,
  TrendData,
  KeywordTrend,
  ApiResponse,
  GraphBuildRequest,
  SubGraphRequest,
  SubGraphData,
  MultiGranularClusters,
  SourceType,
  RankingMetric,
  PaperRecommendations,
  CollaborationNetwork,
  CitationPrediction,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

async function withFallback<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  fallback: () => Promise<ApiResponse<T>>,
  useMock: boolean = USE_MOCK
): Promise<ApiResponse<T>> {
  if (useMock) {
    return fallback();
  }
  
  try {
    return await apiCall();
  } catch (error) {
    console.warn('API call failed, falling back to mock data:', error);
    return fallback();
  }
}

export const api = {
  async searchPapers(
    query: string,
    source: SourceType = 'crossref',
    limit: number = 20
  ): Promise<ApiResponse<Paper[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/search', {
          params: { q: query, source, limit },
        });
        return response.data;
      },
      () => mockApi.searchPapers()
    );
  },

  async getPaper(doi: string): Promise<ApiResponse<Paper>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/paper/${encodeURIComponent(doi)}`);
        return response.data;
      },
      async () => {
        const papers = await mockApi.searchPapers();
        return {
          success: true,
          data: papers.data?.[0] || null as any,
        };
      }
    );
  },

  async getPaperReferences(doi: string): Promise<ApiResponse<Paper[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/paper/${encodeURIComponent(doi)}/references`);
        return response.data;
      },
      () => mockApi.searchPapers()
    );
  },

  async getPaperCitations(doi: string): Promise<ApiResponse<Paper[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/paper/${encodeURIComponent(doi)}/citations`);
        return response.data;
      },
      () => mockApi.searchPapers()
    );
  },

  async buildGraph(request: GraphBuildRequest): Promise<ApiResponse<GraphData>> {
    return withFallback(
      async () => {
        const response = await apiClient.post('/api/graph/build', request);
        return response.data;
      },
      () => mockApi.buildGraph()
    );
  },

  async getGraph(graphId: string): Promise<ApiResponse<GraphData>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/graph/${graphId}`);
        return response.data;
      },
      () => mockApi.buildGraph()
    );
  },

  async getInfluenceRanking(
    metric: RankingMetric = 'pagerank',
    limit: number = 50
  ): Promise<ApiResponse<InfluenceMetrics[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/influence/ranking', {
          params: { metric, limit },
        });
        return response.data;
      },
      () => mockApi.getInfluenceRanking()
    );
  },

  async getCorePapers(
    method: string = 'pagerank',
    threshold: number = 0.1,
    limit: number = 20
  ): Promise<ApiResponse<InfluenceMetrics[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/influence/core-papers', {
          params: { method, threshold, limit },
        });
        return response.data;
      },
      () => mockApi.getCorePapers()
    );
  },

  async getTrendsOverTime(
    keywords?: string,
    startYear: number = 2010,
    endYear: number = 2025
  ): Promise<ApiResponse<TrendData[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/trends/over-time', {
          params: { keywords, start_year: startYear, end_year: endYear },
        });
        return response.data;
      },
      () => mockApi.getTrendsOverTime()
    );
  },

  async getKeywordTrends(limit: number = 30): Promise<ApiResponse<KeywordTrend[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/trends/keywords', {
          params: { limit },
        });
        return response.data;
      },
      () => mockApi.getKeywordTrends()
    );
  },

  async getSubGraph(request: SubGraphRequest): Promise<ApiResponse<SubGraphData>> {
    return withFallback(
      async () => {
        const response = await apiClient.post('/api/graph/subgraph', request);
        return response.data;
      },
      async () => {
        const data = await mockApi.buildGraph();
        return {
          success: true,
          data: {
            center_node: request.node_id,
            nodes: data.data?.nodes.slice(0, 20) || [],
            edges: data.data?.edges.slice(0, 50) || [],
            depth_reached: request.max_depth || 2,
          },
        };
      }
    );
  },

  async getHierarchicalGraph(includeHierarchy: boolean = true): Promise<ApiResponse<HierarchicalGraphData>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/graph/hierarchical', {
          params: { include_hierarchy: includeHierarchy },
        });
        return response.data;
      },
      () => mockApi.buildHierarchicalGraph()
    );
  },

  async getClusters(numLevels: number = 3): Promise<ApiResponse<MultiGranularClusters>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/graph/clusters', {
          params: { num_levels: numLevels },
        });
        return response.data;
      },
      () => mockApi.getClusters()
    );
  },

  async getClusterPapers(
    level: number,
    clusterId: number,
    limit: number = 20
  ): Promise<ApiResponse<InfluenceMetrics[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/graph/cluster/${level}/${clusterId}/papers`, {
          params: { limit },
        });
        return response.data;
      },
      () => mockApi.getClusterPapers(level, clusterId, limit)
    );
  },

  async getRecommendations(
    doi: string,
    limit: number = 20,
    method: string = 'hybrid'
  ): Promise<ApiResponse<PaperRecommendations>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/recommendations/${encodeURIComponent(doi)}`, {
          params: { limit, method },
        });
        return response.data;
      },
      () => mockApi.getRecommendations(doi, limit)
    );
  },

  async getCollaborators(
    authorName: string,
    limit: number = 20
  ): Promise<ApiResponse<CollaborationNetwork>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/collaborators/${encodeURIComponent(authorName)}`, {
          params: { limit },
        });
        return response.data;
      },
      () => mockApi.getCollaborators(authorName, limit)
    );
  },

  async getCitationPrediction(doi: string): Promise<ApiResponse<CitationPrediction>> {
    return withFallback(
      async () => {
        const response = await apiClient.get(`/api/prediction/citations/${encodeURIComponent(doi)}`);
        return response.data;
      },
      () => mockApi.getCitationPrediction(doi)
    );
  },

  async getBatchCitationPrediction(dois: string[]): Promise<ApiResponse<{ predictions: CitationPrediction[]; model_version: string; prediction_date: string }>> {
    return withFallback(
      async () => {
        const response = await apiClient.post('/api/prediction/citations/batch', { dois });
        return response.data;
      },
      () => mockApi.getBatchCitationPrediction(dois)
    );
  },

  async getTrendingPapers(limit: number = 20): Promise<ApiResponse<CitationPrediction[]>> {
    return withFallback(
      async () => {
        const response = await apiClient.get('/api/prediction/trending', {
          params: { limit },
        });
        return response.data;
      },
      () => mockApi.getTrendingPapers(limit)
    );
  },

  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    try {
      const response = await apiClient.get('/api/health');
      return response.data;
    } catch (error) {
      return {
        success: false,
        data: { status: 'offline' },
        error: 'Backend service unavailable',
      };
    }
  },
};

export default api;
