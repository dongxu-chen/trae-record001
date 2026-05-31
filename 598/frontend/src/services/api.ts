import axios from 'axios'
import type {
  DBConfig,
  TableInfo,
  TableStats,
  PartitionRecommendation,
  PartitionPlan,
  PartitionInfo,
  QueryRewriteRequest,
  QueryRewriteResponse,
  PartitionOperationRequest,
  PartitionOperationResponse,
  GrowthPrediction,
  ToolAvailability,
  OnlineDDLRequest,
  OnlineDDLResponse,
  PartitionResizeRequest,
  PartitionMigrationRequest,
  MigrationResult,
  HotColdAnalysis,
  PerformanceComparison,
  PerformanceBenchmarkRequest,
  PartitionResizeResult,
  ApiResponse,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const connectionApi = {
  test: (config: DBConfig): Promise<ApiResponse> =>
    api.post('/connection/test', config),

  connect: (config: DBConfig): Promise<ApiResponse> =>
    api.post('/connection/connect', config),

  getStatus: (): Promise<ApiResponse<{ connected: boolean }>> =>
    api.get('/connection/status'),

  disconnect: (): Promise<ApiResponse> =>
    api.post('/connection/disconnect'),
}

export const tablesApi = {
  getList: (): Promise<ApiResponse<TableInfo[]>> =>
    api.get('/tables'),

  getInfo: (tableName: string): Promise<ApiResponse<TableInfo>> =>
    api.get(`/tables/${tableName}`),

  getStats: (tableName: string): Promise<ApiResponse<TableStats>> =>
    api.get(`/tables/${tableName}/stats`),

  getPrediction: (tableName: string): Promise<ApiResponse<GrowthPrediction>> =>
    api.get(`/tables/${tableName}/prediction`),

  getPartitionInfo: (tableName: string): Promise<ApiResponse<PartitionInfo>> =>
    api.get(`/tables/${tableName}/partition-info`),
}

export const partitionApi = {
  getRecommendation: (tableName: string): Promise<ApiResponse<PartitionRecommendation>> =>
    api.get(`/partition/recommendations/${tableName}`),

  getAllRecommendations: (): Promise<ApiResponse<any[]>> =>
    api.get('/partition/recommendations/all'),

  generatePlan: (tableName: string, method: string, column: string): Promise<ApiResponse<PartitionPlan>> =>
    api.get(`/partition/plan/${tableName}`, {
      params: { method, column },
    }),

  executePlan: (plan: PartitionPlan): Promise<ApiResponse<PartitionOperationResponse>> =>
    api.post('/partition/execute', plan),

  executeOperation: (req: PartitionOperationRequest): Promise<ApiResponse<PartitionOperationResponse>> =>
    api.post('/partition/operation', req),

  autoExtend: (tableName: string): Promise<ApiResponse<{ sqlStatements: string[]; count: number }>> =>
    api.get(`/partition/auto-extend/${tableName}`),

  getToolAvailability: (): Promise<ApiResponse<ToolAvailability>> =>
    api.get('/partition/tool-availability'),

  generatePTOSC: (req: OnlineDDLRequest): Promise<ApiResponse<{ command: string; dryRunCommand: string }>> =>
    api.post('/partition/generate-ptosc', req),

  executeOnlineDDL: (plan: PartitionPlan, useOnlineDDL: boolean = true): Promise<ApiResponse<OnlineDDLResponse>> =>
    api.post('/partition/execute-online-ddl', plan, {
      params: { useOnlineDDL },
    }),

  splitPartition: (tableName: string, partitionName: string, targetRows: number): Promise<ApiResponse<{ sqlStatements: string[] }>> =>
    api.get(`/partition/split/${tableName}`, {
      params: { partitionName, targetRows },
    }),

  mergePartitions: (tableName: string, partitionNames: string[]): Promise<ApiResponse<{ sqlStatements: string[] }>> =>
    api.post('/partition/merge', { tableName, partitionNames }),

  rebalancePartitions: (tableName: string, targetRows: number): Promise<ApiResponse<{ sqlStatements: string[] }>> =>
    api.get(`/partition/rebalance/${tableName}`, {
      params: { targetRows },
    }),

  migratePartition: (req: PartitionMigrationRequest): Promise<ApiResponse<MigrationResult>> =>
    api.post('/partition/migrate', req),

  analyzeHotCold: (tableName: string, thresholdDays: number): Promise<ApiResponse<HotColdAnalysis>> =>
    api.get(`/partition/hot-cold/${tableName}`, {
      params: { thresholdDays },
    }),

  generateHotColdMigration: (tableName: string, coldPartitions: string[], archivePath: string): Promise<ApiResponse<{ sqlStatements: string[] }>> =>
    api.post('/partition/hot-cold/migrate', { tableName, coldPartitions, archivePath }),

  runBenchmark: (req: PerformanceBenchmarkRequest): Promise<ApiResponse<PerformanceComparison>> =>
    api.post('/partition/benchmark', req),

  generateResizePlan: (req: PartitionResizeRequest): Promise<ApiResponse<PartitionResizeResult>> =>
    api.post('/partition/resize', req),
}

export const queryApi = {
  rewrite: (req: QueryRewriteRequest): Promise<ApiResponse<QueryRewriteResponse>> =>
    api.post('/query/rewrite', req),

  analyze: (sql: string, tableName: string): Promise<ApiResponse<any>> =>
    api.get('/query/analyze', {
      params: { sql, tableName },
    }),
}

export default api
