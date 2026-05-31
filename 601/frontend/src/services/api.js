import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
});

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const checkApi = {
  createTask: (task) => api.post('/check/task', task),
  startTask: (taskId) => api.post(`/check/task/${taskId}/start`),
  executeTask: (task) => api.post('/check/task/execute', task),
  cancelTask: (taskId) => api.post(`/check/task/${taskId}/cancel`),
  getTask: (taskId) => api.get(`/check/task/${taskId}`),
  getTasks: (params) => api.get('/check/tasks', { params }),
  getResult: (taskId) => api.get(`/check/task/${taskId}/result`),
  getRecentResults: () => api.get('/check/results'),
  getRunningTasks: () => api.get('/check/running'),
  getDiffs: (params) => api.get('/check/diffs', { params }),
  getDiff: (diffId) => api.get(`/check/diff/${diffId}`),
  triggerRepair: (diffId, taskId) =>
    api.post(`/check/repair/${diffId}?taskId=${taskId}`),
  getDataSources: () => api.get('/check/datasources'),
  getTables: (type) => api.get(`/check/datasource/${type}/tables`),
  getColumns: (type, tableName) =>
    api.get(`/check/datasource/${type}/table/${tableName}/columns`),
  getStatistics: () => api.get('/check/statistics'),

  generateReport: (taskId) => api.post(`/check/report/${taskId}`),
  getLatestReport: () => api.get('/check/report/latest'),
  getAllReports: () => api.get('/check/reports'),
  getReport: (reportId) => api.get(`/check/report/${reportId}`),

  createGrayConfig: (config) => api.post('/check/gray', config),
  getAllGrayConfigs: () => api.get('/check/gray'),
  getGrayConfig: (configId) => api.get(`/check/gray/${configId}`),
  executeGrayCheck: (configId, baseTask) =>
    api.post(`/check/gray/${configId}/execute`, baseTask),
  advanceGrayPhase: (configId) => api.post(`/check/gray/${configId}/advance`),
  pauseGrayRelease: (configId) => api.post(`/check/gray/${configId}/pause`),
  resumeGrayRelease: (configId) => api.post(`/check/gray/${configId}/resume`),

  getAllPredictions: () => api.get('/check/predictions'),
  getPrediction: (tableName) => api.get(`/check/prediction/${tableName}`),
  getTrendData: (tableName) => api.get(`/check/prediction/${tableName}/trend`)
};

export default api;
