import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

export const clusterApi = {
  list: () => api.get('/clusters'),
  get: (id) => api.get(`/clusters/${id}`),
  getStatus: (id) => api.get(`/clusters/${id}/status`),
  create: (data) => api.post('/clusters', data),
  update: (id, data) => api.put(`/clusters/${id}`, data),
  delete: (id) => api.delete(`/clusters/${id}`)
}

export const backupApi = {
  list: (clusterId) => api.get('/backups', { params: { clusterId } }),
  get: (id) => api.get(`/backups/${id}`),
  createFull: (clusterId) => api.post('/backups/full', { clusterId }),
  createIncremental: (clusterId, parentBackupId) =>
    api.post('/backups/incremental', { clusterId, parentBackupId }),
  verify: (id) => api.post(`/backups/${id}/verify`),
  dryRun: (id) => api.post(`/backups/${id}/dryrun`),
  listTimePoints: (clusterId) => api.get(`/backups/timepoints/${clusterId}`)
}

export const restoreApi = {
  list: (clusterId) => api.get('/restores', { params: { clusterId } }),
  get: (id) => api.get(`/restores/${id}`),
  create: (backupId, targetClusterId, pointInTime) =>
    api.post('/restores', { backupId, targetClusterId, pointInTime }),
  restoreByWALIndex: (backupId, targetClusterId, walIndex) =>
    api.post('/restores/wal-index', { backupId, targetClusterId, walIndex })
}

export const scheduleApi = {
  list: (clusterId) => api.get('/schedules', { params: { clusterId } }),
  get: (id) => api.get(`/schedules/${id}`),
  create: (data) => api.post('/schedules', data),
  update: (id, data) => api.put(`/schedules/${id}`, data),
  delete: (id) => api.delete(`/schedules/${id}`)
}

export const kmsApi = {
  status: () => api.get('/kms/status'),
  rotate: () => api.post('/kms/rotate')
}

export const replicationApi = {
  list: (clusterId) => api.get('/replication', { params: { clusterId } }),
  get: (id) => api.get(`/replication/${id}`),
  create: (data) => api.post('/replication', data),
  update: (id, data) => api.put(`/replication/${id}`, data),
  delete: (id) => api.delete(`/replication/${id}`),
  replicate: (id, backupId) => api.post(`/replication/${id}/replicate`, { backupId }),
  replicateLatest: (id) => api.post(`/replication/${id}/replicate-latest`),
  checkHealth: (id) => api.get(`/replication/${id}/health`),
  getLag: (id) => api.get(`/replication/${id}/lag`),
  listTasks: (configId) => api.get('/replication/tasks', { params: { configId } })
}

export const drillApi = {
  list: (clusterId) => api.get('/drills', { params: { clusterId } }),
  get: (id) => api.get(`/drills/${id}`),
  create: (data) => api.post('/drills', data),
  update: (id, data) => api.put(`/drills/${id}`, data),
  delete: (id) => api.delete(`/drills/${id}`),
  runNow: (id) => api.post(`/drills/${id}/run`),
  listResults: (clusterId) => api.get('/drills/results', { params: { clusterId } }),
  getResult: (id) => api.get(`/drills/results/${id}`),
  getStats: (clusterId) => api.get('/drills/stats', { params: { clusterId } })
}

export const costApi = {
  getAnalysis: (clusterId, period) => api.get(`/cost/analysis/${clusterId}`, { params: { period } }),
  getRestoreTime: (backupId) => api.get(`/cost/restore-time/${backupId}`)
}

export default api
