import axios from 'axios'

const API_BASE_URL = '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const graphApi = {
  health: () => apiClient.get('/health'),

  getGraph: (limit = 1000) => apiClient.get('/graph', { params: { limit } }),

  getCommunities: () => apiClient.get('/graph/communities'),

  getInfluence: (method = 'degree') => apiClient.get('/graph/influence', { params: { method } }),

  getMetrics: () => apiClient.get('/graph/metrics'),

  getShortestPath: (source, target) =>
    apiClient.get('/graph/path', { params: { source, target } }),

  addNode: (nodeData) => apiClient.post('/nodes', nodeData),

  deleteNode: (nodeId) => apiClient.delete(`/nodes/${nodeId}`),

  addEdge: (edgeData) => apiClient.post('/edges', edgeData),

  importData: (data) => apiClient.post('/import', data),

  clearDatabase: () => apiClient.delete('/clear'),

  getNeighbors: (nodeId) => apiClient.get(`/nodes/${nodeId}/neighbors`),

  getTemporalAnalysis: (params) =>
    apiClient.get('/graph/temporal', { params }),

  getFilteredGraph: (params) =>
    apiClient.get('/graph/filtered', { params }),

  getInfluenceComparison: () =>
    apiClient.get('/graph/influence/comparison'),

  getRelationshipTypes: () =>
    apiClient.get('/graph/relationship-types'),

  getCacheStatus: () =>
    apiClient.get('/cache/status'),

  clearCache: () =>
    apiClient.post('/cache/clear'),

  refreshCache: () =>
    apiClient.post('/cache/refresh'),

  getPerformanceInfo: () =>
    apiClient.get('/graph/performance'),

  getKeyNodes: (topN = 10) =>
    apiClient.get('/graph/key-nodes', { params: { top_n: topN } }),

  simulateDiffusion: (params) =>
    apiClient.post('/graph/diffusion', params),

  getCommunityEvolution: (timeWindows = 10) =>
    apiClient.get('/graph/community-evolution', { params: { time_windows: timeWindows } }),
}

export default apiClient
