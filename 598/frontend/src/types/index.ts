export interface DBConfig {
  host: string
  port: string
  user: string
  password: string
  database: string
}

export interface ColumnInfo {
  columnName: string
  dataType: string
  columnType: string
  isNullable: boolean
  columnKey: string
  columnDefault: string
  extra: string
  comment: string
}

export interface IndexInfo {
  indexName: string
  nonUnique: boolean
  seqInIndex: number
  columnName: string
  indexType: string
  comment: string
}

export interface PartitionDef {
  partitionName: string
  partitionOrdinal: number
  partitionMethod: string
  partitionExpression: string
  partitionDescription: string
  tableRows: number
  dataLength: number
  indexLength: number
  createTime: string
  updateTime: string
  comment: string
}

export interface PartitionInfo {
  partitionMethod: string
  partitionExpr: string
  partitions: PartitionDef[]
}

export interface DataPoint {
  date: string
  value: number
}

export interface TableStats {
  totalRows: number
  totalSizeMB: number
  avgRowSizeKB: number
  minValue: any
  maxValue: any
  valueRange: any
  valueDistinct: number
  growthPerDay: number
  growthPerWeek: number
  growthPerMonth: number
  estimatedDaysToThreshold: number
  dataPoints: DataPoint[]
}

export interface TableInfo {
  tableName: string
  tableRows: number
  dataSize: number
  indexSize: number
  totalSize: number
  createTime: string
  updateTime: string
  engine: string
  tableCollation: string
  comment: string
  columns: ColumnInfo[]
  primaryKeys: string[]
  indexes: IndexInfo[]
  partitionInfo?: PartitionInfo
  stats?: TableStats
}

export interface AlternativeMethod {
  method: string
  reason: string
  confidence: number
}

export interface PartitionRecommendation {
  tableName: string
  recommendedMethod: string
  partitionExpr: string
  partitionColumn: string
  reason: string
  confidence: number
  estimatedPartitions: number
  estimatedPerfGain: string
  samplePartitions: PartitionDef[]
  alternativeMethods: AlternativeMethod[]
}

export interface PartitionPlan {
  tableName: string
  partitionMethod: string
  partitionExpr: string
  partitionColumn: string
  partitions: PartitionDef[]
  sqlStatements: string[]
  estimatedTimeSec: number
}

export interface QueryRewriteRequest {
  originalSql: string
  tableName: string
}

export interface QueryRewriteResponse {
  originalSql: string
  rewrittenSql: string
  appliedRules: string[]
  explanation: string
  performanceHint: string
}

export interface PartitionOperationRequest {
  tableName: string
  operation: string
  partitionNames: string[]
  newPartitions: PartitionDef[]
}

export interface PartitionOperationResponse {
  success: boolean
  message: string
  sqlExecuted: string[]
  warnings: string[]
}

export interface GrowthPrediction {
  tableName: string
  currentRows: number
  predicted30Days: number
  predicted90Days: number
  predicted365Days: number
  growthRate: number
  shouldPartition: boolean
  recommendedAction: string
}

export interface ToolAvailability {
  ptoscAvailable: boolean
  ptocsAvailable: boolean
  path: string
  version: string
}

export interface OnlineDDLRequest {
  tableName: string
  alterStatement?: string
  partitionMethod?: string
  partitionExpr?: string
  partitions?: PartitionDef[]
}

export interface OnlineDDLResponse {
  success: boolean
  command: string
  output: string
  errorOutput: string
  executionTime: number
  warnings: string[]
}

export interface PartitionPruningAnalysis {
  canPrune: boolean
  partitionsToScan: string[]
  partitionsToPrune: string[]
  totalPartitions: number
  pruningEfficiency: number
  pruningMethod: string
  confidence: number
}

export interface QueryOptimizationReport {
  originalQuery: string
  optimizedQuery: string
  partitionAnalysis: PartitionPruningAnalysis
  appliedRules: string[]
  antiPatterns: string[]
  suggestions: string[]
  estimatedCostReduction: number
}

export interface PartitionResizeRequest {
  tableName: string
  partitionNames: string[]
  targetRowCount: number
  operation: 'SPLIT' | 'MERGE' | 'REBALANCE'
  newPartitionDefs?: PartitionDef[]
}

export interface PartitionMigrationRequest {
  tableName: string
  sourcePartition: string
  targetPartition: string
  whereCondition: string
  batchSize: number
  verifyData: boolean
}

export interface MigrationResult {
  success: boolean
  migratedRows: number
  verifiedRows: number
  executionTime: number
  sourceEmpty: boolean
  sqlStatements: string[]
}

export interface HotColdAnalysis {
  tableName: string
  totalRows: number
  hotRows: number
  coldRows: number
  hotPartitions: PartitionDef[]
  coldPartitions: PartitionDef[]
  hotSizeMB: number
  coldSizeMB: number
  recommendedAction: string
  hotThresholdDays?: number
}

export interface PerformanceMetric {
  query: string
  avgTimeMs: number
  minTimeMs: number
  maxTimeMs: number
  rowsExamined: number
  partitionsScan: number
  partitionPruned: number
  executionPlan: string
}

export interface PerformanceComparison {
  tableName: string
  beforeMetrics: PerformanceMetric[]
  afterMetrics: PerformanceMetric[]
  improvements: Record<string, number>
  overallGain: number
}

export interface PerformanceBenchmarkRequest {
  tableName: string
  queries: string[]
  beforePartition: boolean
  afterPartition: boolean
  runCount: number
}

export interface PartitionResizeResult {
  success: boolean
  sqlStatements: string[]
  oldPartitions: string[]
  newPartitions: PartitionDef[]
  migratedRows: number
  executionTime: number
  warnings: string[]
}

export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message: string
  error: string
}
