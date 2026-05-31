import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code !== 'ERR_CANCELED') {
      console.error('API Error:', error.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);

export const getStyles = () => api.get('/api/styles');

export const getModels = () => api.get('/api/models');

export const uploadImage = (formData) => api.post('/api/upload', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export const transferStyle = (formData) => api.post('/api/transfer', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export const getPreview = (formData, signal) => api.post('/api/preview', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
  signal,
});

export const cancelPreview = () => api.post('/api/cancel-preview');

export const submitFeedback = (data) => api.post('/api/feedback', data);

export const getPersonalizedModels = (userId) => api.get('/api/personalized-models', {
  params: { user_id: userId }
});

export const trainModel = (data) => api.post('/api/train-model', data);

export const getExtendedStyles = (userId) => api.get('/api/styles/extended', {
  params: { user_id: userId }
});

export const transferMixed = (data) => api.post('/api/transfer-mixed', data);

export const batchTransfer = (data) => api.post('/api/batch-transfer', data);

export const batchTransferMixed = (data) => api.post('/api/batch-transfer-mixed', data);

export default {
  getStyles,
  getModels,
  uploadImage,
  transferStyle,
  getPreview,
  cancelPreview,
  submitFeedback,
  getPersonalizedModels,
  trainModel,
  getExtendedStyles,
  transferMixed,
  batchTransfer,
  batchTransferMixed,
};
