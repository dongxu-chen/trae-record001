import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const groupApi = {
  list: () => api.get('/groups'),
  get: (id) => api.get(`/groups/${id}`),
  create: (data) => api.post('/groups', data),
  update: (id, data) => api.put(`/groups/${id}`, data),
  delete: (id) => api.delete(`/groups/${id}`),
}

export const ruleApi = {
  list: (groupId) => api.get('/rules', { params: { group_id: groupId } }),
  get: (id) => api.get(`/rules/${id}`),
  create: (data) => api.post('/rules', data),
  update: (id, data) => api.put(`/rules/${id}`, data),
  delete: (id) => api.delete(`/rules/${id}`),
  listVersions: (id) => api.get(`/rules/${id}/versions`),
  compareVersions: (id, versionId) => api.get(`/rules/${id}/versions/${versionId}/compare`),
  restoreVersion: (id, versionId) => api.post(`/rules/${id}/versions/${versionId}/restore`),
  restoreVersionWithConfirm: (id, versionId, data) => api.post(`/rules/${id}/versions/${versionId}/restore-confirm`, data),
}

export const promqlApi = {
  validate: (expr) => api.post('/promql/validate', { expr }),
  simulate: (expr, forDuration, metrics, timeSeries) => api.post('/promql/simulate', { expr, for: forDuration, metrics, time_series: timeSeries }),
  simulateBatch: (expr, forDuration, testScenarios) => api.post('/promql/simulate/batch', { expr, for: forDuration, test_scenarios: testScenarios }),
  generateTestData: (data) => api.post('/promql/generate-test-data', data),
}

export const ioApi = {
  import: (file, groupId, format = 'yaml') => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/io/import', file, {
      params: { group_id: groupId, format },
      headers: { 'Content-Type': format === 'json' ? 'application/json' : 'application/x-yaml' },
    })
  },
  export: (groupId, format = 'yaml') =>
    api.get('/io/export', {
      params: { group_id: groupId, format },
      responseType: format === 'json' ? 'json' : 'blob',
    }),
}

export const prometheusApi = {
  getRules: () => api.get('/prometheus/rules'),
  getAlerts: () => api.get('/prometheus/alerts'),
  query: (query, time) => api.post('/prometheus/query', { query, time }),
}

export default api
