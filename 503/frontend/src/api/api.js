import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const slowLogAPI = {
  getSlowLogs: (count = 100) => api.get(`/slowlogs?count=${count}`),
  getConfig: () => api.get('/slowlogs/config'),
  getCommandAnalysis: (count = 1000, normalize = true) =>
    api.get(`/analysis/commands?count=${count}&normalize=${normalize}`),
  getHotKeys: (count = 1000, top_n = 20) => api.get(`/analysis/hotkeys?count=${count}&top_n=${top_n}`),
  getLargeKeys: (size_threshold = 10240, element_threshold = null, composite = true) => {
    let url = `/analysis/largekeys?size_threshold=${size_threshold}&composite=${composite}`;
    if (element_threshold !== null) {
      url += `&element_threshold=${element_threshold}`;
    }
    return api.get(url);
  },
  getSlowQueriesRanking: (count = 1000, top_n = 20, sort_by = 'duration') =>
    api.get(`/analysis/ranking?count=${count}&top_n=${top_n}&sort_by=${sort_by}`),
  getOptimizations: (count = 1000, size_threshold = 10240) =>
    api.get(`/optimizations?count=${count}&size_threshold=${size_threshold}`),
  getFullAnalysis: (log_count = 1000, size_threshold = 10240) =>
    api.get(`/full?log_count=${log_count}&size_threshold=${size_threshold}`),
  getAutoOptimizationCommands: (params = {}) => {
    const { log_count = 1000, size_threshold = 10240, element_threshold, composite = true } = params;
    let url = `/optimizations/auto-commands?log_count=${log_count}&size_threshold=${size_threshold}&composite=${composite}`;
    if (element_threshold) {
      url += `&element_threshold=${element_threshold}`;
    }
    return api.get(url);
  },
  getOptimizationScripts: (type = 'all') =>
    api.get(`/optimizations/scripts?type=${type}`),
};

export const monitorAPI = {
  getMetrics: () => api.get('/monitor/metrics'),
  getHistory: (count = null) => api.get(`/monitor/history${count ? `?count=${count}` : ''}`),
  getAggregated: (count = null) => api.get(`/monitor/aggregated${count ? `?count=${count}` : ''}`),
  getAggregatedMetrics: (count = null) => api.get(`/monitor/aggregated${count ? `?count=${count}` : ''}`),
  startMonitor: (interval = 1) => api.post('/monitor/start', { interval }),
  stopMonitor: () => api.post('/monitor/stop'),
  startStreamMonitor: (stream_interval_ms = 100, aggregate_interval_ms = 1000) =>
    api.post('/monitor/stream/start', { stream_interval_ms, aggregate_interval_ms }),
  stopStreamMonitor: () => api.post('/monitor/stream/stop'),
  startStream: (stream_interval_ms = 100, aggregate_interval_ms = 1000) =>
    api.post('/monitor/stream/start', { stream_interval_ms, aggregate_interval_ms }),
  stopStream: () => api.post('/monitor/stream/stop'),
  getStreamSlowLogs: () => api.get('/monitor/stream/slowlogs'),
  getNewSlowLogs: (last_id = -1) => api.get(`/monitor/slowlogs/new?last_id=${last_id}`),
  getDatabaseStats: () => api.get('/monitor/databases'),
  getCommandStats: () => api.get('/monitor/commands'),
};

export const predictionAPI = {
  getTrend: (hours_ahead = 24, hours = 24) =>
    api.get(`/prediction/trend?hours_ahead=${hours_ahead}&hours=${hours}`),
  getHotCommands: (top_n = 10, hours = 24) =>
    api.get(`/prediction/hot-commands?top_n=${top_n}&hours=${hours}`),
  getRisk: (hours = 24) =>
    api.get(`/prediction/risk?hours=${hours}`),
  getSummary: (hours = 24) =>
    api.get(`/prediction/summary?hours=${hours}`),
};

export const auditAPI = {
  getLogs: (action_type = null, status = null, limit = 100) => {
    let url = `/audit/logs?limit=${limit}`;
    if (action_type) url += `&action_type=${action_type}`;
    if (status) url += `&status=${status}`;
    return api.get(url);
  },
  getStatistics: () => api.get('/audit/statistics'),
  getPending: () => api.get('/audit/pending'),
  createLog: (data) => api.post('/audit/log', data),
  executeLog: (entry_id, result) =>
    api.post(`/audit/log/${entry_id}/execute`, { result }),
  failLog: (entry_id, error_message) =>
    api.post(`/audit/log/${entry_id}/fail`, { error_message }),
  clearLogs: (days = 30) => api.post('/audit/clear', { days }),
};

export default api;
