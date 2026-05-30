import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.response.use(
  response => {
    if (response.data && response.data.code === 200) {
      return response.data.data;
    }
    throw new Error(response.data?.message || '请求失败');
  },
  error => {
    const message = error.response?.data?.message || error.message || '网络错误';
    console.error('API Error:', message);
    throw error;
  }
);

export const workflowApi = {
  list: () => api.get('/workflows'),
  get: (id) => api.get(`/workflows/${id}`),
  create: (data) => api.post('/workflows', data),
  update: (id, data) => api.put(`/workflows/${id}`, data),
  delete: (id) => api.delete(`/workflows/${id}`),
  publish: (id) => api.post(`/workflows/${id}/publish`),
  trigger: (id) => api.post(`/executions/trigger/${id}`)
};

export const executionApi = {
  list: (workflowId) => api.get('/executions', { params: { workflowId } }),
  get: (executionId) => api.get(`/executions/${executionId}`),
  retry: (executionId) => api.post(`/executions/${executionId}/retry`),
  cancel: (executionId) => api.post(`/executions/${executionId}/cancel`)
};

export const triggerApi = {
  list: (workflowId) => api.get('/triggers', { params: { workflowId } }),
  get: (id) => api.get(`/triggers/${id}`),
  create: (data) => api.post('/triggers', data),
  update: (id, data) => api.put(`/triggers/${id}`, data),
  toggle: (id, enabled) => api.post(`/triggers/${id}/toggle?enabled=${enabled}`),
  delete: (id) => api.delete(`/triggers/${id}`),
  fireEvent: (topic) => api.post(`/triggers/event/${topic}`),
  getWebhookUrl: (webhookPath) => `${window.location.origin}/webhook/${webhookPath}`
};

export const lineageApi = {
  create: (data) => api.post('/lineage', data),
  listBySource: (workflowId) => api.get(`/lineage/source/${workflowId}`),
  listByTarget: (workflowId) => api.get(`/lineage/target/${workflowId}`),
  toggle: (id, enabled) => api.post(`/lineage/${id}/toggle?enabled=${enabled}`),
  delete: (id) => api.delete(`/lineage/${id}`)
};

export default api;
