import axios from 'axios';

const POOL_API = '/api/pool-optimizer';
const MONITOR_API = '/api/monitor';

const api = {
  simulate: (config, workload) =>
    axios.post(`${POOL_API}/simulate`, { config, workload }),

  optimize: (request) =>
    axios.post(`${POOL_API}/optimize`, request),

  compare: (request) =>
    axios.post(`${POOL_API}/compare`, request),

  analyzeQueue: (config, workload) =>
    axios.post(`${POOL_API}/analyze-queue`, { config, workload }),

  getPoolTypes: () =>
    axios.get(`${POOL_API}/pool-types`),

  getDefaultConfig: (poolType) =>
    axios.get(`${POOL_API}/default-config/${poolType}`),

  getDefaultWorkload: () =>
    axios.get(`${POOL_API}/default-workload`),

  getDefaultConstraint: () =>
    axios.get(`${POOL_API}/default-database-constraint`),

  startMonitoring: (config, workload) =>
    axios.post(`${MONITOR_API}/start`, { config, workload }),

  stopMonitoring: () =>
    axios.post(`${MONITOR_API}/stop`),

  getMonitorStatus: () =>
    axios.get(`${MONITOR_API}/status`),

  getMonitorStream: () => `${MONITOR_API}/stream`,

  getSnapshots: (count = 60) =>
    axios.get(`${MONITOR_API}/snapshots?count=${count}`),

  getLatestSnapshot: () =>
    axios.get(`${MONITOR_API}/latest`),

  evaluateTuning: () =>
    axios.post(`${MONITOR_API}/tuning/evaluate`),

  applyTuning: (decision) =>
    axios.post(`${MONITOR_API}/tuning/apply`, decision),

  autoTuneStep: () =>
    axios.post(`${MONITOR_API}/tuning/auto-step`),

  getTuningHistory: () =>
    axios.get(`${MONITOR_API}/tuning/history`),

  getTuningPolicy: () =>
    axios.get(`${MONITOR_API}/tuning/policy`),

  updateTuningPolicy: (policy) =>
    axios.put(`${MONITOR_API}/tuning/policy`, policy),

  getSlowSqlRecords: (limit = 50) =>
    axios.get(`${MONITOR_API}/slow-sql?limit=${limit}`),

  analyzeSlowSql: () =>
    axios.get(`${MONITOR_API}/slow-sql/analysis`),

  getAlerts: () =>
    axios.get(`${MONITOR_API}/alerts`),

  acknowledgeAlert: (alertId) =>
    axios.post(`${MONITOR_API}/alerts/${alertId}/acknowledge`),
};

export default api;
