import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const serviceApi = {
  getAll: () => api.get('/services'),
  getActive: () => api.get('/services/active'),
  getByName: (name) => api.get(`/services/${name}`),
  create: (data) => api.post('/services', data),
  update: (name, data) => api.put(`/services/${name}`, data),
  delete: (name) => api.delete(`/services/${name}`),
};

export const metricsApi = {
  getLatest: (serviceName) => api.get(`/metrics/${serviceName}/latest`),
  getHistory: (serviceName, hours = 24, windowType = null) => {
    let url = `/metrics/${serviceName}/history?hours=${hours}`;
    if (windowType) url += `&windowType=${windowType}`;
    return api.get(url);
  },
  getAllWindows: (serviceName) => api.get(`/metrics/${serviceName}/windows`),
  getWindowMetrics: (serviceName, windowType) => 
    api.get(`/metrics/${serviceName}/window/${windowType}`),
  getWindowBounds: (windowType) => api.get(`/metrics/window-bounds/${windowType}`),
  getAvailabilitySummary: (serviceName) => 
    api.get(`/metrics/${serviceName}/availability-summary`),
  compare: (serviceNames, hours = 1) => 
    api.get(`/metrics/compare?serviceNames=${serviceNames.join(',')}&hours=${hours}`),
  getPrediction: (serviceName) => api.get(`/metrics/${serviceName}/prediction`),
  getRootCause: (serviceName) => api.get(`/metrics/${serviceName}/root-cause`),
  simulate: (serviceName, count = 100) => 
    api.post(`/metrics/${serviceName}/simulate?count=${count}`),
  simulateAll: () => api.post('/metrics/simulate-all'),
};

export const alertApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return api.get(`/alerts${query ? `?${query}` : ''}`);
  },
  getActive: () => api.get('/alerts/active'),
  getByService: (serviceName) => api.get(`/alerts/service/${serviceName}`),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge`),
  resolve: (id) => api.post(`/alerts/${id}/resolve`),
};

export const slaTierApi = {
  getAll: (active = null) => {
    const url = active !== null ? `/sla-tiers?active=${active}` : '/sla-tiers';
    return api.get(url);
  },
  getById: (id) => api.get(`/sla-tiers/${id}`),
  getByCode: (code) => api.get(`/sla-tiers/code/${code}`),
  create: (data) => api.post('/sla-tiers', data),
  update: (id, data) => api.put(`/sla-tiers/${id}`, data),
  delete: (id) => api.delete(`/sla-tiers/${id}`),
};

export const rootCauseRuleApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return api.get(`/root-cause-rules${query ? `?${query}` : ''}`);
  },
  getById: (id) => api.get(`/root-cause-rules/${id}`),
  getByCode: (code) => api.get(`/root-cause-rules/code/${code}`),
  match: (availability, latency, errorRate) => 
    api.get(`/root-cause-rules/match?availability=${availability}&latency=${latency}&errorRate=${errorRate}`),
  create: (data) => api.post('/root-cause-rules', data),
  update: (id, data) => api.put(`/root-cause-rules/${id}`, data),
  delete: (id) => api.delete(`/root-cause-rules/${id}`),
  mine: () => api.post('/root-cause-rules/mine'),
  getStatistics: () => api.get('/root-cause-rules/statistics'),
  updateStatistics: () => api.post('/root-cause-rules/update-statistics'),
};

export const compensationApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return api.get(`/compensations${query ? `?${query}` : ''}`);
  },
  getPending: () => api.get('/compensations/pending'),
  getById: (id) => api.get(`/compensations/${id}`),
  check: (serviceName) => api.post(`/compensations/check/${serviceName}`),
  approve: (id, approvedBy = 'system') => api.post(`/compensations/${id}/approve`, { approvedBy }),
  resolve: (id) => api.post(`/compensations/${id}/resolve`),
  createManual: (data) => api.post('/compensations/manual', data),
  getStatistics: () => api.get('/compensations/statistics'),
};

export const capacityApi = {
  getAll: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return api.get(`/capacity${query ? `?${query}` : ''}`);
  },
  getAlerts: () => api.get('/capacity/alerts'),
  getCritical: () => api.get('/capacity/critical'),
  getByService: (serviceName) => api.get(`/capacity/service/${serviceName}`),
  generate: (serviceName) => api.post(`/capacity/generate/${serviceName}`),
  getStatistics: () => api.get('/capacity/statistics'),
  getSummary: () => api.get('/capacity/summary'),
};

export const dependencyApi = {
  getAll: () => api.get('/dependencies'),
  getByService: (serviceName) => api.get(`/dependencies/service/${serviceName}`),
  getUpstream: (serviceName) => api.get(`/dependencies/upstream/${serviceName}`),
  getDownstream: (serviceName) => api.get(`/dependencies/downstream/${serviceName}`),
  add: (dependency) => api.post('/dependencies', dependency),
  remove: (id) => api.delete(`/dependencies/${id}`),
  analyze: (serviceName) => api.get(`/dependencies/analyze/${serviceName}`),
  getGraph: () => api.get('/dependencies/graph'),
  getRiskAnalysis: () => api.get('/dependencies/risk-analysis'),
};

export default api;
