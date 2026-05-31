import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const routingAPI = {
  createWeightRouting: (data: any) =>
    apiClient.post('/routing/weight', data),

  createHeaderRouting: (data: any) =>
    apiClient.post('/routing/header', data),

  createTrafficMirror: (data: any) =>
    apiClient.post('/routing/mirror', data),

  createFaultInjection: (data: any) =>
    apiClient.post('/routing/fault', data),

  getRoutingRules: (namespace: string = 'default') =>
    apiClient.get(`/routing/rules?namespace=${namespace}`),

  deleteRoutingRule: (namespace: string, id: string) =>
    apiClient.delete(`/routing/rules/${namespace}/${id}`),
};

export const istioAPI = {
  getVirtualServices: (namespace: string = 'default') =>
    apiClient.get(`/istio/virtualservices?namespace=${namespace}`),

  getDestinationRules: (namespace: string = 'default') =>
    apiClient.get(`/istio/destinationrules?namespace=${namespace}`),
};

export const topologyAPI = {
  getTopology: (namespace: string = 'default') =>
    apiClient.get(`/topology?namespace=${namespace}`),
};

export const metricsAPI = {
  getMetrics: (namespace: string = 'default', serviceName?: string) => {
    let url = `/metrics?namespace=${namespace}`;
    if (serviceName) {
      url += `&service=${serviceName}`;
    }
    return apiClient.get(url);
  },
};

export const reportsAPI = {
  generateReport: (data: any) =>
    apiClient.post('/reports', data),

  getReport: (id: string) =>
    apiClient.get(`/reports/${id}`),
};

export const healthAPI = {
  check: () => apiClient.get('/health'),
};

export const blueGreenAPI = {
  createDeployment: (data: any) =>
    apiClient.post('/bluegreen', data),

  listDeployments: (namespace?: string) => {
    let url = '/bluegreen';
    if (namespace) {
      url += `?namespace=${namespace}`;
    }
    return apiClient.get(url);
  },

  getDeployment: (id: string) =>
    apiClient.get(`/bluegreen/${id}`),

  startDeployment: (id: string) =>
    apiClient.post(`/bluegreen/${id}/start`),

  pauseDeployment: (id: string) =>
    apiClient.post(`/bluegreen/${id}/pause`),

  rollbackDeployment: (id: string) =>
    apiClient.post(`/bluegreen/${id}/rollback`),

  completeDeployment: (id: string) =>
    apiClient.post(`/bluegreen/${id}/complete`),
};

export const accessControlAPI = {
  createRule: (data: any) =>
    apiClient.post('/access-control', data),

  listRules: (namespace?: string, serviceName?: string) => {
    let url = '/access-control';
    const params = [];
    if (namespace) params.push(`namespace=${namespace}`);
    if (serviceName) params.push(`service=${serviceName}`);
    if (params.length > 0) url += `?${params.join('&')}`;
    return apiClient.get(url);
  },

  getRule: (id: string) =>
    apiClient.get(`/access-control/${id}`),

  updateRule: (id: string, data: any) =>
    apiClient.put(`/access-control/${id}`, data),

  deleteRule: (id: string) =>
    apiClient.delete(`/access-control/${id}`),

  checkAccess: (data: any) =>
    apiClient.post('/access-control/check', data),
};

export const costAPI = {
  estimateCost: (data: any) =>
    apiClient.post('/cost/estimate', data),

  getProviders: () =>
    apiClient.get('/cost/providers'),

  getRegions: (provider: string) =>
    apiClient.get(`/cost/regions?provider=${provider}`),

  getConfig: (provider: string) =>
    apiClient.get(`/cost/config/${provider}`),

  monthlyReport: (data: any) =>
    apiClient.post('/cost/monthly-report', data),

  compareProviders: (data: any) =>
    apiClient.post('/cost/compare', data),
};

export default apiClient;
