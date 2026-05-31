import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8080/api/schemas',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const schemaApi = {
  getAllSchemas: () => api.get('/'),
  
  getSchema: (subject) => api.get(`/${subject}`),
  
  createSchema: (data) => api.post('/', data),
  
  deleteSchema: (subject) => api.delete(`/${subject}`),
  
  updateCompatibility: (subject, level) => 
    api.put(`/${subject}/compatibility`, { level }),
  
  getVersions: (subject) => api.get(`/${subject}/versions`),
  
  getVersion: (subject, version) => api.get(`/${subject}/versions/${version}`),
  
  addVersion: (subject, data) => api.post(`/${subject}/versions`, data),
  
  checkCompatibility: (data) => api.post('/compatibility/check', data),
  
  compareVersions: (subject, oldVersion, newVersion) => 
    api.get(`/${subject}/diff`, { params: { oldVersion, newVersion } }),
  
  compareSchemasDirect: (type, oldSchema, newSchema) => 
    api.post('/diff', { oldSchema, newSchema }, { params: { type } }),
  
  getEvolutionRecommendation: (data) => 
    api.post('/evolution/recommendation', data),
  
  previewEvolution: (subject, schema) => 
    api.post(`/${subject}/evolve/preview`, { schema }),
  
  autoEvolveSchema: (subject, schema, username) => 
    api.post(`/${subject}/evolve`, { schema, username }),
  
  generateCode: (subject, version, language, packageName, className) => 
    api.post(`/${subject}/versions/${version}/code`, {}, { params: { language, packageName, className } }),
  
  generateCodeDirect: (type, language, packageName, className, schema) => 
    api.post('/code/generate', { schema }, { params: { type, language, packageName, className } }),
  
  getAuditLogsBySubject: (subject) => 
    api.get(`/${subject}/audit`),
  
  getAuditLogs: (username, action, recentHours) => 
    api.get('/audit', { params: { username, action, recentHours } }),
  
  getAuditLogById: (id) => 
    api.get(`/audit/${id}`),
};

export default schemaApi;
