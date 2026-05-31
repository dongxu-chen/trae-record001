const BASE = '/api/v1'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || 'Request failed')
  }
  return res.json()
}

export const api = {
  getClusterInfo: () => request('/cluster/info'),
  getClusterNodes: () => request('/cluster/nodes'),
  getClusterStats: () => request('/cluster/stats'),
  getSlotDistribution: () => request('/cluster/slots'),

  getMonitorCurrent: () => request('/monitor/current'),
  getMonitorHistory: () => request('/monitor/history'),
  getMonitorRange: (from, to) => request(`/monitor/range?from=${from}&to=${to}`),

  getScalerEvents: () => request('/scaler/events'),
  addNode: (addr) => request('/scaler/add-node', { method: 'POST', body: JSON.stringify({ addr }) }),
  removeNode: (nodeId) => request('/scaler/remove-node', { method: 'POST', body: JSON.stringify({ node_id: nodeId }) }),

  getMigrationPlan: () => request('/migration/plan'),
  executeMigration: () => request('/migration/execute', { method: 'POST' }),
  evacuateNode: (nodeId) => request(`/migration/evacuate/${nodeId}`, { method: 'POST' }),
  migrateSlots: (fromNodeId, toNodeId, slots) =>
    request('/migration/migrate', {
      method: 'POST',
      body: JSON.stringify({ from_node_id: fromNodeId, to_node_id: toNodeId, slots }),
    }),
  getMigrationTasks: () => request('/migration/tasks'),
  cancelMigration: (taskId) => request(`/migration/cancel/${taskId}`, { method: 'POST' }),

  getBackupList: () => request('/backup/list'),
  createBackup: () => request('/backup/create', { method: 'POST' }),

  getFailoverHealth: () => request('/failover/health'),
  getFailoverEvents: () => request('/failover/events'),
  triggerFailover: (nodeId) => request(`/failover/trigger/${nodeId}`, { method: 'POST' }),

  getCurrentCost: () => request('/cost/current'),
  predictScaleUp: (nodes) => request(`/cost/predict/scaleup?nodes=${nodes || 1}`),
  predictScaleDown: (nodes) => request(`/cost/predict/scaledown?nodes=${nodes || 1}`),
  predictRebalance: () => request('/cost/predict/rebalance'),
  predictAddReplica: (nodes) => request(`/cost/predict/replica?nodes=${nodes || 1}`),

  simulateScaleUp: (nodes) => request('/simulate/scaleup', { method: 'POST', body: JSON.stringify({ nodes: nodes || 1 }) }),
  simulateScaleDown: (nodes) => request('/simulate/scaledown', { method: 'POST', body: JSON.stringify({ nodes: nodes || 1 }) }),
  simulateRebalance: () => request('/simulate/rebalance', { method: 'POST' }),
  simulateFailover: (nodeId) => request(`/simulate/failover/${nodeId}`, { method: 'POST' }),
  getSimulateResults: () => request('/simulate/results'),
}
