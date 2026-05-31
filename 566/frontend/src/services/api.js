import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const faultApi = {
  list: () => api.get('/faults'),
  get: (id) => api.get(`/faults/${id}`),
  create: (data) => api.post('/faults', data),
  update: (id, data) => api.put(`/faults/${id}`, data),
  delete: (id) => api.delete(`/faults/${id}`),
  start: (id) => api.post(`/faults/${id}/start`),
  stop: (id) => api.post(`/faults/${id}/stop`),
  getMetrics: (id) => api.get(`/metrics/fault/${id}`),
  manualRollbackCheck: (id) => api.post(`/faults/${id}/rollback/check`),
  getRollbackStatus: (id) => api.get(`/faults/${id}/rollback/status`),
};

export const scenarioApi = {
  list: () => api.get('/scenarios'),
  get: (id) => api.get(`/scenarios/${id}`),
  create: (data) => api.post('/scenarios', data),
  update: (id, data) => api.put(`/scenarios/${id}`, data),
  delete: (id) => api.delete(`/scenarios/${id}`),
  execute: (id) => api.post(`/scenarios/${id}/execute`),
};

export const executionApi = {
  list: (scenarioId) => api.get('/executions', { params: { scenario_id: scenarioId } }),
  get: (id) => api.get(`/executions/${id}`),
};

export const serviceApi = {
  list: () => api.get('/services'),
  listDetailed: () => api.get('/services/detailed'),
  getTopology: () => api.get('/services/topology'),
  getMetrics: (name, lookback) => api.get(`/services/${name}/metrics`, { params: { lookback } }),
  getComparison: (name, params) => api.get(`/services/${name}/comparison`, { params }),
  getVersions: (name) => api.get(`/services/${name}/versions`),
  getFaults: (name) => api.get(`/services/${name}/faults`),
};

export const metricsApi = {
  getAlignedComparison: (data) => api.post('/metrics/comparison', data),
};

export const presetApi = {
  list: () => api.get('/presets'),
  listByCategory: (category) => api.get(`/presets/category/${category}`),
  search: (keyword) => api.get('/presets/search', { params: { q: keyword } }),
  get: (id) => api.get(`/presets/${id}`),
  apply: (id, data) => api.post(`/presets/${id}/apply`, data),
};

export const rollbackApi = {
  getActiveMonitors: () => api.get('/rollback/active'),
  getDefaultConfig: () => api.get('/rollback/default-config'),
};

export const resilienceApi = {
  getScore: (faultId, params) => api.get(`/resilience/fault/${faultId}/score`, { params }),
  calculate: (data) => api.post('/resilience/calculate', data),
};

export default api;
