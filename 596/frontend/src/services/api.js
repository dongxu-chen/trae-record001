import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const scanAPI = {
  startScan: async (config) => {
    const response = await api.post('/api/scan', config);
    return response.data;
  },

  startMultipleScan: async (config, endpoints) => {
    const response = await api.post('/api/scan/multiple', { config, endpoints });
    return response.data;
  },

  getScanTypes: async () => {
    const response = await api.get('/api/scan/types');
    return response.data;
  },

  getAuthTypes: async () => {
    const response = await api.get('/api/auth/types');
    return response.data;
  },

  getPayloads: async (type) => {
    const response = await api.get(`/api/payloads/${type}`);
    return response.data;
  },

  generateHTMLReport: async (result) => {
    const response = await api.post('/api/report/generate/html', result);
    return response.data;
  },

  generateMarkdownReport: async (result) => {
    const response = await api.post('/api/report/generate/markdown', result);
    return response.data;
  },
};

export default api;
