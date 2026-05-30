import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export const healthCheck = () => api.get('/health')

export const getCurrentDeadlocks = () => api.get('/deadlocks/current')
export const getDeadlockHistory = () => api.get('/deadlocks/history')
export const getDeadlockDetail = (id) => api.get(`/deadlocks/${id}`)
export const resolveDeadlock = (id, transactionId) => 
  api.post(`/deadlocks/${id}/resolve`, { transaction_id: transactionId })

export const getRules = () => api.get('/rules')
export const createRule = (rule) => api.post('/rules', rule)
export const updateRule = (id, rule) => api.put(`/rules/${id}`, rule)
export const deleteRule = (id) => api.delete(`/rules/${id}`)

export const getConfig = () => api.get('/config')
export const updateConfig = (config) => api.put('/config', config)

export const getStatistics = () => api.get('/statistics')
export const getTransactions = () => api.get('/transactions')

export const getDetectorStatus = () => api.get('/detector/status')
export const startDetector = () => api.post('/detector/start')
export const stopDetector = () => api.post('/detector/stop')

export const getPreventionRecommendations = (limit) => 
  api.get('/prevention/recommendations', { params: { limit } })
export const getPreventionRecommendation = (id) => 
  api.get(`/prevention/recommendations/${id}`)
export const markRecommendationResolved = (id) => 
  api.put(`/prevention/recommendations/${id}/resolve`)
export const getPreventionStatistics = () => 
  api.get('/prevention/statistics')

export const getSandboxScenarios = () => api.get('/sandbox/scenarios')
export const getSandboxScenario = (id) => api.get(`/sandbox/scenarios/${id}`)
export const createSandboxScenario = (scenario) => 
  api.post('/sandbox/scenarios', scenario)
export const deleteSandboxScenario = (id) => 
  api.delete(`/sandbox/scenarios/${id}`)
export const runSimulation = (scenarioId, killStrategy) => 
  api.post('/sandbox/run', { scenario_id: scenarioId, kill_strategy: killStrategy })
export const getSimulationResults = (limit) => 
  api.get('/sandbox/results', { params: { limit } })
export const getSimulationResult = (id) => 
  api.get(`/sandbox/results/${id}`)
export const getSimulationStatus = (id) => 
  api.get(`/sandbox/results/${id}/status`)

export const getAuditLogs = (filters) => 
  api.get('/audit/logs', { params: filters })
export const getAuditLogDetail = (id) => 
  api.get(`/audit/logs/${id}`)
export const getAuditStatistics = () => 
  api.get('/audit/statistics')
export const getAuditTraceByDeadlock = (deadlockId) => 
  api.get(`/audit/trace/${deadlockId}`)

export default api
