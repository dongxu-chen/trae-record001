import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const ruleApi = {
  getAll: () => api.get('/rules'),
  getEnabled: () => api.get('/rules/enabled'),
  getByCode: (code) => api.get(`/rules/code/${code}`),
  getByScene: (scene) => api.get(`/rules/scene/${scene}`),
  create: (data) => api.post('/rules', data),
  update: (id, data) => api.put(`/rules/${id}`, data),
  delete: (id) => api.delete(`/rules/${id}`),
  getVersions: (id) => api.get(`/rules/${id}/versions`),
  rollback: (id, version) => api.post(`/rules/${id}/rollback/${version}`),
  hotReload: () => api.post('/rules/hot-reload'),
  validateDrl: (drl) => api.post('/rules/validate/drl', { drl }),
  validateGroovy: (script) => api.post('/rules/validate/groovy', { script }),
  simulate: (data) => api.post('/rules/simulate', data),
}

export const statsApi = {
  getHitStats: () => api.get('/stats/hit'),
  getActionCounts: () => api.get('/stats/actions'),
  getDashboard: () => api.get('/stats/dashboard'),
  getHitStatsByGranularity: (granularity, ruleCodes) => {
    const url = ruleCodes
      ? `/stats/hit/granularity/${granularity}?ruleCodes=${ruleCodes.join(',')}`
      : `/stats/hit/granularity/${granularity}`
    return api.get(url)
  },
  getActionCountsByGranularity: (granularity) => api.get(`/stats/actions/granularity/${granularity}`),
}

export const eventApi = {
  evaluate: (data) => api.post('/events/evaluate', data),
}

export const conflictApi = {
  detect: () => api.get('/conflicts/detect'),
}

export const abtestApi = {
  getAll: () => api.get('/abtest'),
  get: (id) => api.get(`/abtest/${id}`),
  create: (data) => api.post('/abtest', data),
  start: (id) => api.post(`/abtest/${id}/start`),
  stop: (id) => api.post(`/abtest/${id}/stop`),
  delete: (id) => api.delete(`/abtest/${id}`),
  getStats: (id) => api.get(`/abtest/${id}/stats`),
}

export const evaluationApi = {
  evaluateRule: (ruleCode, beforeHours = 24, afterHours = 24) =>
    api.get(`/evaluation/rule/${ruleCode}?beforeHours=${beforeHours}&afterHours=${afterHours}`),
  evaluateAll: (beforeHours = 24, afterHours = 24) =>
    api.get(`/evaluation/all?beforeHours=${beforeHours}&afterHours=${afterHours}`),
}

export default api
