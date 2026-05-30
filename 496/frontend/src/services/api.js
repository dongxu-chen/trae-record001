import axios from 'axios';

const API_BASE = '/api';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const topologyAPI = {
  getTopology: () => apiClient.get('/topology'),
  getServices: () => apiClient.get('/topology/services'),
  getService: (serviceId) => apiClient.get(`/topology/services/${serviceId}`),
  getBottlenecks: () => apiClient.get('/topology/bottlenecks'),
};

export const rateLimitAPI = {
  getRecommendation: (serviceId) => apiClient.get(`/ratelimit/recommend/${serviceId}`),
  getAllRecommendations: () => apiClient.get('/ratelimit/recommend/all'),
  applyRecommendation: (recommendation) => apiClient.post('/ratelimit/apply', recommendation),
  getConfig: (serviceId) => apiClient.get(`/ratelimit/config/${serviceId}`),
  getAllConfigs: () => apiClient.get('/ratelimit/configs'),
  updateConfig: (serviceId, config) => apiClient.put(`/ratelimit/config/${serviceId}`, config),
  deleteConfig: (serviceId) => apiClient.delete(`/ratelimit/config/${serviceId}`),
  toggleConfig: (serviceId, enabled) => apiClient.post(`/ratelimit/config/${serviceId}/toggle?enabled=${enabled}`),
  exportConfig: (serviceId) => apiClient.get(`/ratelimit/config/${serviceId}/export`),
};

export const predictionAPI = {
  getTrafficPrediction: (serviceId, horizonMinutes = 60) =>
    apiClient.get(`/prediction/traffic/${serviceId}?horizonMinutes=${horizonMinutes}`),
};

export const simulationAPI = {
  runSimulation: (serviceId, request) => apiClient.post(`/simulation/overload/${serviceId}`, request),
  runProtectedSimulation: (serviceId, request) => apiClient.post(`/simulation/overload/${serviceId}/protected`, request),
  compareSimulation: (serviceId, request) => apiClient.post(`/simulation/overload/${serviceId}/compare`, request),
};

export const realtimeAPI = {
  getStatus: () => apiClient.get('/realtime/status'),
  getWaterLevels: () => apiClient.get('/realtime/water-levels'),
  getCoordinations: () => apiClient.get('/realtime/coordinations'),
  triggerCoordination: (serviceId, waterLevel, reason) =>
    apiClient.post(`/realtime/coordination/trigger/${serviceId}?waterLevel=${waterLevel}&reason=${reason}`),
  releaseCoordination: (coordinationId) =>
    apiClient.post(`/realtime/coordination/release/${coordinationId}`),
  getCoordinationImpact: (coordinationId) =>
    apiClient.get(`/realtime/coordination/${coordinationId}/impact`),
  getTrafficPattern: (serviceId) => apiClient.get(`/realtime/traffic-pattern/${serviceId}`),
  getTrafficPatternSummary: (serviceId) => apiClient.get(`/realtime/traffic-pattern/${serviceId}/summary`),
  getTrafficSeries: (serviceId, minutes) =>
    apiClient.get(`/realtime/traffic-series/${serviceId}?minutes=${minutes}`),
  triggerBurst: (serviceId, intensity, durationMinutes) =>
    apiClient.post(`/realtime/traffic-burst/${serviceId}?intensity=${intensity}&durationMinutes=${durationMinutes}`),
};

export const deployAPI = {
  deployToGateway: (gatewayId, autoApprove) =>
    apiClient.post(`/deploy/gateway/${gatewayId}?autoApprove=${autoApprove}`),
  deployService: (serviceId) => apiClient.post(`/deploy/service/${serviceId}`),
  rollback: (deployId) => apiClient.post(`/deploy/rollback/${deployId}`),
  getHistory: () => apiClient.get('/deploy/history'),
  getResult: (deployId) => apiClient.get(`/deploy/result/${deployId}`),
};

export const evaluationAPI = {
  evaluate: (serviceId, durationMinutes) =>
    apiClient.post(`/evaluation/${serviceId}?durationMinutes=${durationMinutes}`),
  evaluateAll: (durationMinutes) =>
    apiClient.post(`/evaluation/all?durationMinutes=${durationMinutes}`),
  getHistory: () => apiClient.get('/evaluation/history'),
  getEvaluation: (evaluationId) => apiClient.get(`/evaluation/${evaluationId}`),
};

export const drillAPI = {
  startDrill: (serviceId, config) => apiClient.post(`/drill/start/${serviceId}`, config),
  getDefaultConfig: (serviceId) => apiClient.get(`/drill/default-config/${serviceId}`),
  getActiveDrills: () => apiClient.get('/drill/active'),
  getCompletedDrills: () => apiClient.get('/drill/completed'),
  getDrill: (drillId) => apiClient.get(`/drill/${drillId}`),
  abortDrill: (drillId) => apiClient.post(`/drill/abort/${drillId}`),
};

export default apiClient;
