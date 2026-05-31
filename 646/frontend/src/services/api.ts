import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8080/api',
  timeout: 30000,
});

export interface DataSource {
  id: string;
  name: string;
  type: 'mysql' | 'postgresql' | 'mongodb' | 's3' | 'kafka' | 'rabbitmq';
  config: Record<string, any>;
  status: 'active' | 'inactive' | 'testing';
  createdAt: string;
  updatedAt: string;
}

export interface MigrationTask {
  id: string;
  name: string;
  sourceId: string;
  targetId: string;
  mode: 'full' | 'incremental';
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'rollback' | 'rollback_completed';
  config: TaskConfig;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

export interface TaskConfig {
  tableName?: string;
  targetTableName?: string;
  primaryKey?: string;
  batchSize?: number;
  rateLimit?: number;
  enableBackup?: boolean;
  autoRollback?: boolean;
  rollbackStrategy?: 'table_restore' | 'truncate_and_restore';
  maskingRules?: MaskingRule[];
  transformRules?: TransformRule[];
}

export interface MaskingRule {
  fieldName: string;
  strategyType: 'phone' | 'email' | 'idcard' | 'full';
}

export interface TransformRule {
  sourceField: string;
  targetField?: string;
  transformType: 'uppercase' | 'lowercase' | 'trim' | 'substring' | 'tostring';
  start?: number;
  end?: number;
}

export interface TaskStatus {
  id: string;
  name: string;
  status: string;
  progress: number;
  processedRecords: number;
  totalRecords: number;
  errorRecords: number;
  throughput?: number;
  batchSize?: number;
  rateLimit?: number;
  positionType?: string;
  positionValue?: string;
  liveProgress?: number;
  liveProcessedRecords?: number;
  liveThroughput?: number;
  livePositionType?: string;
  livePositionValue?: string;
  liveBatchSize?: number;
  liveRateLimit?: number;
  rollbackStatus?: RollbackStatus;
}

export interface PositionInfo {
  success: boolean;
  progress: number;
  processedRecords: number;
  totalRecords: number;
  throughput: number;
  batchSize: number;
  rateLimit?: number;
  positionType: string;
  positionValue: string;
  message?: string;
}

export interface CheckpointRecord {
  id: number;
  taskId: number;
  tableName: string;
  positionType: string;
  positionValue: string;
  processedRecords: number;
  createdAt: string;
  updatedAt: string;
}

export interface TaskLog {
  id: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  createdAt: string;
}

export interface ValidationItem {
  key: string;
  name: string;
  passed: boolean;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  summary: string;
  validatedAt: string;
  items: ValidationItem[];
}

export interface RollbackStatus {
  success: boolean;
  taskId: number;
  rollbackStatus: 'BACKING_UP' | 'BACKUP_COMPLETED' | 'BACKUP_FAILED' | 'ROLLING_BACK' | 'ROLLBACK_COMPLETED' | 'ROLLBACK_FAILED';
  backupTableName: string;
  backupRecords: number;
  rollbackStrategy: string;
  errorMessage?: string;
  updatedAt: string;
}

export const dataSourceApi = {
  list: (params: { page?: number; size?: number; type?: string } = {}) =>
    api.get('/datasources', { params }),
  get: (id: string) => api.get(`/datasources/${id}`),
  create: (data: Partial<DataSource>) => api.post('/datasources', data),
  update: (id: string, data: Partial<DataSource>) => api.put(`/datasources/${id}`, data),
  delete: (id: string) => api.delete(`/datasources/${id}`),
  test: (id: string) => api.post(`/datasources/${id}/test`),
  listTables: (id: string) => api.get(`/datasources/${id}/tables`),
  getTableSchema: (id: string, tableName: string) =>
    api.get(`/datasources/${id}/tables/${tableName}/schema`),
};

export const taskApi = {
  list: (params: { page?: number; size?: number; status?: string } = {}) =>
    api.get('/tasks', { params }),
  get: (id: string) => api.get(`/tasks/${id}`),
  create: (data: Partial<MigrationTask>) => api.post('/tasks', data),
  update: (id: string, data: Partial<MigrationTask>) => api.put(`/tasks/${id}`, data),
  delete: (id: string) => api.delete(`/tasks/${id}`),
  preValidate: (id: string) => api.post(`/tasks/${id}/prevalidate`),
  start: (id: string) => api.post(`/tasks/${id}/start`),
  pause: (id: string) => api.post(`/tasks/${id}/pause`),
  rollback: (id: string) => api.post(`/tasks/${id}/rollback`),
  getRollbackStatus: (id: string) => api.get(`/tasks/${id}/rollback/status`),
  getStatus: (id: string) => api.get(`/tasks/${id}/status`),
  getRealtimePosition: (id: string) => api.get(`/tasks/${id}/position`),
  getCheckpointHistory: (id: string, limit?: number) =>
    api.get(`/tasks/${id}/checkpoints`, { params: { limit } }),
  getLogs: (id: string, limit?: number) =>
    api.get(`/tasks/${id}/logs`, { params: { limit } }),
  getDashboardStats: () => api.get('/tasks/dashboard/stats'),
};

export default api;
