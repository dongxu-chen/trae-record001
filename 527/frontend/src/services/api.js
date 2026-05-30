import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const taskApi = {
  getAll: () => api.get('/tasks'),
  getById: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post('/tasks', data),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
};

export const documentApi = {
  getByTask: (taskId, params = {}) => 
    api.get(`/documents/task/${taskId}`, { params }),
  getById: (id) => api.get(`/documents/${id}`),
  getNext: (taskId, currentId = '') => 
    api.get(`/documents/next/${taskId}/${currentId}`),
  create: (data) => api.post('/documents', data),
  bulkCreate: (taskId, documents) => 
    api.post('/documents/bulk', { taskId, documents }),
  update: (id, data) => api.put(`/documents/${id}`, data),
  delete: (id) => api.delete(`/documents/${id}`),
};

export const annotationApi = {
  getByDocument: (documentId, taskId) => 
    api.get(`/annotations/document/${documentId}`, { params: { taskId } }),
  getByTask: (taskId) => api.get(`/annotations/task/${taskId}`),
  save: (documentId, data) => 
    api.post(`/annotations/document/${documentId}`, data),
  delete: (documentId) => api.delete(`/annotations/document/${documentId}`),
};

export const exportApi = {
  exportJSON: (taskId, format = 'flat') => 
    api.get(`/export/json/${taskId}`, { 
      params: { format },
      responseType: 'blob' 
    }),
  exportCoNLL: (taskId) => 
    api.get(`/export/conll/${taskId}`, { responseType: 'blob' }),
  getStats: (taskId) => api.get(`/export/stats/${taskId}`),
};

export const preAnnotateApi = {
  preAnnotateDocument: (documentId, options = {}) => 
    api.post(`/preannotate/document/${documentId}`, options),
  checkConsistency: (taskId, params = {}) => 
    api.get(`/preannotate/consistency/${taskId}`, { params }),
  fineTune: (taskId) => 
    api.post(`/preannotate/finetune/${taskId}`),
  getNextUncertainDocument: (taskId, params = {}) => 
    api.get(`/preannotate/next-uncertain/${taskId}`, { params }),
  getModelInfo: (taskId) => 
    api.get(`/preannotate/model-info/${taskId}`),
};

export const templateApi = {
  getAll: (params = {}) => api.get('/templates', { params }),
  getById: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates', data),
  update: (id, data) => api.put(`/templates/${id}`, data),
  delete: (id) => api.delete(`/templates/${id}`),
  apply: (templateId, taskId) => 
    api.post(`/templates/apply/${templateId}/${taskId}`),
  rate: (id, rating) => 
    api.post(`/templates/rate/${id}`, { rating }),
  getSuggestions: (taskId) => 
    api.get(`/templates/suggestions/${taskId}`),
};

export const qualityApi = {
  getAll: (params = {}) => api.get('/quality', { params }),
  getPersonal: (annotator, taskId) => 
    api.get('/quality/personal', { params: { annotator, taskId } }),
  update: (data) => api.post('/quality/update', data),
  getRankings: (taskId, params = {}) => 
    api.get('/quality/rankings', { params: { taskId, ...params } }),
  getTrends: (annotator, taskId, type = 'daily') => 
    api.get('/quality/trends', { params: { annotator, taskId, type } }),
};

export const achievementApi = {
  getAll: (params = {}) => api.get('/achievements', { params }),
  getUserAchievements: (annotator, taskId) => 
    api.get('/achievements/user', { params: { annotator, taskId } }),
  updateProgress: (data) => 
    api.post('/achievements/progress', data),
  getLeaderboard: (taskId, params = {}) => 
    api.get('/achievements/leaderboard', { params: { taskId, ...params } }),
  getSummary: (annotator, taskId) => 
    api.get('/achievements/summary', { params: { annotator, taskId } }),
};

export default api;
