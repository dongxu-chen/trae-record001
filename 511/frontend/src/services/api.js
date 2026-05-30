import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const parseSQL = (sql, database, schema) => {
  return api.post('/parse', { sql, database, schema });
};

export const saveLineage = (sql, database, schema) => {
  return api.post('/lineage', { sql, database, schema });
};

export const getTableLineage = (tableName, depth = 3, collapse = true) => {
  return api.get(`/lineage/table/${tableName}?depth=${depth}&collapse=${collapse}`);
};

export const getColumnLineage = (columnName, depth = 3, collapse = true) => {
  return api.get(`/lineage/column/${columnName}?depth=${depth}&collapse=${collapse}`);
};

export const getColumnMappingChains = (columnName) => {
  return api.get(`/lineage/column/${columnName}/mapping-chains`);
};

export const expandAggregatedEdge = (source, target) => {
  return api.post('/lineage/expand', { source, target });
};

export const getAllTables = () => {
  return api.get('/tables');
};

export const getTableColumns = (tableName) => {
  return api.get(`/tables/${tableName}/columns`);
};

export const getFullGraph = (collapse = true) => {
  return api.get(`/graph?collapse=${collapse}`);
};

export const clearDatabase = () => {
  return api.delete('/database');
};

export const healthCheck = () => {
  return api.get('/health');
};

export const analyzeImpact = (tableName, depth = 10) => {
  return api.get(`/impact/${tableName}?depth=${depth}`);
};

export const getDataDictionary = () => {
  return api.get('/data-dictionary');
};

export const getLineageDocument = (title = '数据血缘文档') => {
  return api.get(`/document?title=${encodeURIComponent(title)}`);
};

export const getMarkdownDocument = (title = '数据血缘文档') => {
  return api.get(`/document/markdown?title=${encodeURIComponent(title)}`, {
    responseType: 'text',
  });
};

export const detectAnomalies = () => {
  return api.get('/anomalies');
};

export default api;
