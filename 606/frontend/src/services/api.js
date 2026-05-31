import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export const drillApi = {
  createTask: (data) => api.post('/drill/tasks', data),
  startTask: (taskId, mode = 'simulator') =>
    api.post(`/drill/tasks/${taskId}/start`, null, { params: { mode } }),
  stopTask: (taskId) => api.post(`/drill/tasks/${taskId}/stop`),
  listTasks: () => api.get('/drill/tasks'),
  getTask: (taskId) => api.get(`/drill/tasks/${taskId}`),
  deleteTask: (taskId) => api.delete(`/drill/tasks/${taskId}`),
};

export const strategyApi = {
  create: (data) => api.post('/strategy', data),
  update: (id, data) => api.put(`/strategy/${id}`, data),
  delete: (id) => api.delete(`/strategy/${id}`),
  list: () => api.get('/strategy'),
  get: (id) => api.get(`/strategy/${id}`),
};

export const reportApi = {
  list: () => api.get('/report'),
  get: (taskId) => api.get(`/report/${taskId}`),
};

export const chaosApi = {
  configure: (enabled, errorRatio = 0, delayMs = 0) =>
    api.post('/drill/chaos', null, { params: { enabled, errorRatio, delayMs } }),
  getMetrics: (strategyId = 'default') =>
    api.get('/drill/metrics', { params: { strategyId } }),
};

export const recommendationApi = {
  getStrategyRecommendation: (targetSystem, includeAlternatives = true) =>
    api.get('/recommendation/strategy', { params: { targetSystem, includeAlternatives } }),
  verifyRecommendation: (data) => api.post('/recommendation/strategy/verify', data),
  getStrategyVariants: (strategyId, count = 5) =>
    api.get('/recommendation/strategy/variants', { params: { strategyId, count } }),
};

export const scheduledApi = {
  listTasks: () => api.get('/scheduled/tasks'),
  getTask: (taskId) => api.get(`/scheduled/tasks/${taskId}`),
  createTask: (data) => api.post('/scheduled/tasks', data),
  updateTask: (taskId, data) => api.put(`/scheduled/tasks/${taskId}`, data),
  deleteTask: (taskId) => api.delete(`/scheduled/tasks/${taskId}`),
  toggleTask: (taskId, enabled) =>
    api.post(`/scheduled/tasks/${taskId}/toggle`, null, { params: { enabled } }),
  triggerTask: (taskId) => api.post(`/scheduled/tasks/${taskId}/trigger`),
  getStats: () => api.get('/scheduled/stats'),
};

export const capacityApi = {
  predictCapacity: (targetSystem, horizonHours = 24) =>
    api.get('/capacity/predict', { params: { targetSystem, horizonHours } }),
  getWatermarks: (safetyFactor = 1.0) =>
    api.get('/capacity/watermarks', { params: { safetyFactor } }),
  getHistory: (targetSystem, hours = 168) =>
    api.get('/capacity/history', { params: { targetSystem, hours } }),
  getTrend: (targetSystem) =>
    api.get('/capacity/trend', { params: { targetSystem } }),
};

export default api;
