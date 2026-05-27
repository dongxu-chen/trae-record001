import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 0 && res.code !== undefined) {
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    return Promise.reject(error)
  }
)

export const api = {
  getDashboard: () => request.get('/dashboard'),

  getDomains: (params) => request.get('/domains', { params }),
  createDomain: (data) => request.post('/domains', data),
  updateDomain: (id, data) => request.put(`/domains/${id}`, data),
  deleteDomain: (id) => request.delete(`/domains/${id}`),
  getDomainDetail: (id) => request.get(`/domains/${id}`),
  checkDomain: (id) => request.post(`/domains/${id}/check`),
  toggleDomain: (id) => request.put(`/domains/${id}/toggle`),
  importDomains: (formData) => request.post('/domains/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  batchCreateDomains: (data) => request.post('/domains/batch', data),
  getTags: () => request.get('/tags'),

  getCertRecords: (params) => request.get('/certs', { params }),
  getCertHistory: (domainId, limit) => request.get(`/certs/${domainId}/history`, { params: { limit } }),

  getReport: () => request.get('/report'),
  exportReport: () => {
    window.open('/api/report/export', '_blank')
  },

  getAlertLogs: (params) => request.get('/alerts', { params }),
  sendTestAlert: (data) => request.post('/alerts/test', data),

  getDNSRecords: (params) => request.get('/dns/records', { params }),
  getSubdomains: (params) => request.get('/dns/subdomains', { params }),
  scanDNS: (data) => request.post('/dns/scan', data),
  promoteSubdomain: (id) => request.post(`/dns/subdomains/${id}/promote`),
  deleteSubdomainRecord: (id) => request.post(`/dns/subdomains/${id}`),
  getDNSStats: () => request.get('/dns/stats'),

  getRules: (params) => request.get('/rules', { params }),
  updateRules: () => request.post('/rules/update'),
  getRuleUpdateLogs: (params) => request.get('/rules/logs', { params }),
  addRule: (data) => request.post('/rules', data),
  updateRule: (id, data) => request.put(`/rules/${id}`, data),
  deleteRule: (id) => request.delete(`/rules/${id}`),
  getRuleVersion: () => request.get('/rules/version'),
  exportRules: () => {
    window.open('/api/rules/export', '_blank')
  },
  importRules: (formData) => request.post('/rules/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),

  getScanConfig: () => request.get('/scan/config'),

  getCertChainInfo: (domainId) => request.get(`/certs/${domainId}/chain`),
  compareCertWithPrevious: (domainId) => request.get(`/certs/${domainId}/compare`),
  getCertChanges: (domainId, limit) => request.get(`/certs/${domainId}/changes`, { params: { limit } }),
  getUnloggedCerts: () => request.get('/certs/unlogged'),
  getIncompleteChainCerts: () => request.get('/certs/incomplete-chain'),
}

export default request
