import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const summarizeText = async (options) => {
  const response = await api.post('/summarize', options);
  return response.data;
};

export const summarizeFile = async (file, options) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const params = new URLSearchParams(options).toString();
  const response = await api.post(`/summarize-file?${params}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const multiDocSummarize = async (options) => {
  const response = await api.post('/multi-doc-summarize', options);
  return response.data;
};

export const multiDocSummarizeFiles = async (files, options) => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });
  
  Object.keys(options).forEach(key => {
    formData.append(key, options[key]);
  });
  
  const response = await api.post('/multi-doc-summarize-files', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const evaluateSummary = async (options) => {
  const response = await api.post('/evaluate', options);
  return response.data;
};

export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
