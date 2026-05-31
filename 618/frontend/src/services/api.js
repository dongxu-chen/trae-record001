import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.response.use(
  (response) => {
    if (response.data.code === 200) {
      return response.data.data
    }
    return Promise.reject(new Error(response.data.message || '请求失败'))
  },
  (error) => {
    return Promise.reject(error)
  }
)

export const auditApi = {
  getLogs: (params) => api.get('/audit/logs', { params }),
  getLog: (id) => api.get(`/audit/logs/${id}`),
  getDiff: (id) => api.get(`/audit/logs/${id}/diff`),
  getStructDiff: (id) => api.get(`/audit/logs/${id}/struct-diff`),
  rollback: (id, operator) => api.post(`/audit/logs/${id}/rollback`, { operator }),
  recordChange: (data) => api.post('/audit/record', data),
  quickRollback: (data) => api.post('/audit/quick-rollback', data),
}

export const namespaceApi = {
  getNamespaces: () => api.get('/namespaces'),
  getConfigs: () => api.get('/namespaces/configs'),
  saveConfig: (data) => api.post('/namespaces/configs', data),
}

export const complianceApi = {
  getRules: () => api.get('/compliance/rules'),
  saveRule: (data) => api.post('/compliance/rules', data),
  deleteRule: (id) => api.delete(`/compliance/rules/${id}`),
}

export const listenerApi = {
  start: (data) => api.post('/listener/start', data),
  stop: (data) => api.post('/listener/stop', data),
}

export const impactApi = {
  analyze: (params) => api.get('/impact/analyze', { params }),
}

export const serviceApi = {
  getServices: (params) => api.get('/services', { params }),
  createService: (data) => api.post('/services', data),
  updateService: (data) => api.put('/services', data),
  deleteService: (id) => api.delete(`/services/${id}`),
}

export const rollbackPolicyApi = {
  getPolicies: (params) => api.get('/rollback-policies', { params }),
  createPolicy: (data) => api.post('/rollback-policies', data),
  updatePolicy: (data) => api.put('/rollback-policies', data),
  deletePolicy: (id) => api.delete(`/rollback-policies/${id}`),
}

export const dashboardApi = {
  getStats: (days = 30) => api.get('/dashboard', { params: { days } }),
}

export default api
