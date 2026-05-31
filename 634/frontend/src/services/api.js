import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const topicApi = {
  getAllTopics: (params) => api.get('/topics', { params }),
  getTopic: (topicId) => api.get(`/topics/${topicId}`),
  getTopicArticles: (topicId, limit = 20) => 
    api.get(`/topics/${topicId}/articles`, { params: { limit } }),
  getBurstingTopics: () => api.get('/bursting'),
  getPropagation: (topicId) => api.get(`/topics/${topicId}/propagation`),
  getIgnitionPoints: (topicId) => api.get(`/topics/${topicId}/ignition`),
  getSimilarTopics: (topicId, threshold = 0.5) => 
    api.get(`/topics/${topicId}/similar`, { params: { threshold } }),
};

export const warningApi = {
  getActiveWarnings: (minLevel) => api.get('/warnings', { params: { min_level: minLevel } }),
  getWarningHistory: (limit = 20) => api.get('/warnings', { params: { history: true, limit } }),
  acknowledgeWarning: (topicId) => api.post(`/warnings/${topicId}/acknowledge`),
};

export const comparisonApi = {
  getAvailableTopics: () => api.get('/comparison/available'),
  compareTopics: (topicIds, timeRangeHours) => 
    api.post('/comparison', { topic_ids: topicIds, time_range_hours: timeRangeHours }),
};

export const evolutionApi = {
  getGraph: () => api.get('/evolution/graph'),
  getFullGraphWithVersions: () => api.get('/evolution/graph/full'),
  getIncrementalUpdate: () => api.get('/evolution/graph/incremental'),
  getChain: (topicId) => api.get(`/evolution/chain/${topicId}`),
};

export const newsApi = {
  submitNews: (article) => api.post('/news', article),
  generateMock: (count = 1) => api.post('/mock/generate', null, { params: { count } }),
};

export const healthApi = {
  check: () => axios.get('/health'),
};

export default api;
