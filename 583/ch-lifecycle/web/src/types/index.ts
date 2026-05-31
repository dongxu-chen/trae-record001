export type ActionType = 'move_to_disk' | 'drop' | 'freeze' | 'optimize';

export interface TTLPolicy {
  id: string;
  name: string;
  database: string;
  table: string;
  description: string;
  enabled: boolean;
  rules: TTLRule[];
  created_at: string;
  updated_at: string;
}

export interface TTLRule {
  id: string;
  age_days: number;
  action: ActionType;
  target_disk?: string;
  target_policy?: string;
  description?: string;
  priority: number;
}

export interface ShadowMoveStep {
  step: string;
  database: string;
  table: string;
  partition: string;
  target_disk?: string;
  status: string;
  error?: string;
}

export interface PartitionAction {
  database: string;
  table: string;
  partition: string;
  action: ActionType;
  target_disk?: string;
  reason: string;
  age_days: number;
  size_bytes: number;
  rows: number;
  shadow_move: boolean;
  steps?: ShadowMoveStep[];
}

export interface ActionError {
  partition: string;
  action: string;
  error: string;
}

export interface ExecutionResult {
  total_evaluated: number;
  actions: PartitionAction[];
  errors?: ActionError[];
  duration: number;
}

export interface TierStatus {
  name: string;
  type: string;
  path: string;
  priority: number;
  free_space: number;
  total_space: number;
  used_percent: number;
}

export interface MigrationPlan {
  database: string;
  table: string;
  partition: string;
  from_disk: string;
  to_disk: string;
  age_days: number;
  size_bytes: number;
  reason: string;
}

export interface MigrationResult {
  planned: number;
  executed: number;
  errors?: MigrationError[];
  duration: number;
}

export interface MigrationError {
  partition: string;
  from_disk: string;
  to_disk: string;
  error: string;
}

export type JobType = 'ttl_check' | 'tiering' | 'cleanup' | 'optimize';

export interface JobStatus {
  type: JobType;
  status: string;
  last_run?: string;
  next_run?: string;
  duration?: number;
  error?: string;
  result?: unknown;
}

export type PartitionGranularity = 'daily' | 'monthly' | 'yearly';

export interface PartitionPattern {
  granularity: PartitionGranularity;
  count: number;
  avg_size_bytes: number;
  avg_rows: number;
  time_span_days: number;
  confidence: number;
}

export interface RecommendedGranularity {
  current: PartitionGranularity;
  recommended: PartitionGranularity;
  reason: string;
  estimated_part_count: number;
  sql_template: string;
}

export interface TableAnalysis {
  database: string;
  table: string;
  engine: string;
  total_rows: number;
  total_bytes: number;
  partition_count: number;
  avg_partition_size: number;
  skew_ratio: number;
  fragmentation: number;
  suggestions: OptimizationSuggestion[];
  pattern?: PartitionPattern;
  granularity_recommendation?: RecommendedGranularity;
}

export interface OptimizationSuggestion {
  database: string;
  table: string;
  partition?: string;
  type: string;
  severity: string;
  description: string;
  action: string;
  impact: string;
}

export interface PartitionInfo {
  database: string;
  table: string;
  partition: string;
  name: string;
  active: number;
  rows: number;
  bytes_on_disk: number;
  modification: string;
  min_date: string;
  max_date: string;
  level: number;
  path: string;
}

export interface TableInfo {
  database: string;
  name: string;
  engine: string;
  total_rows: number;
  total_bytes: number;
  partition_key: string;
  sorting_key: string;
  primary_key: string;
  storage_policy: string;
}

export interface DiskInfo {
  name: string;
  path: string;
  type: string;
  free_space: number;
  total_space: number;
}

export interface StoragePolicyInfo {
  name: string;
  disks: string;
  volumes: string;
  move_factor: number;
}

export interface ClusterSnapshot {
  timestamp: string;
  disks: DiskSnapshot[];
  tables: TableSnapshot[];
}

export interface DiskSnapshot {
  name: string;
  type: string;
  free_space: number;
  total_space: number;
  used_pct: number;
}

export interface TableSnapshot {
  database: string;
  table: string;
  total_rows: number;
  total_bytes: number;
  partition_count: number;
}

export type ArchiveStatus = 'pending' | 'running' | 'completed' | 'failed' | 'deleted';

export interface ArchiveConfig {
  enabled: boolean;
  endpoint: string;
  bucket: string;
  export_format: string;
}

export interface CreateArchiveRequest {
  database: string;
  table: string;
  partition: string;
}

export interface ArchiveJob {
  id: string;
  database: string;
  table: string;
  partition: string;
  status: ArchiveStatus;
  object_path: string;
  size_bytes: number;
  rows: number;
  export_sql: string;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export type QuerySource = 'hot' | 'cold' | 'auto';

export interface CreateRoutingRuleRequest {
  database: string;
  table: string;
  pattern: string;
  min_age_days: number;
  target_source: QuerySource;
  priority: number;
}

export interface QueryInfo {
  sql: string;
  database: string;
  table: string;
  start_time: string;
  end_time: string;
  table_names: string[];
}

export interface RouteResult {
  source: QuerySource;
  reason: string;
  target_host: string;
  estimated_rows: number;
}

export interface RoutingRule {
  id: string;
  database: string;
  table: string;
  pattern: string;
  min_age_days: number;
  target_source: QuerySource;
  priority: number;
}

export interface RoutingConfig {
  enable_smart_routing: boolean;
  default_source: QuerySource;
  hot_host: string;
  cold_host: string;
  rules: RoutingRule[];
}

export interface SimulationConfig {
  days_to_simulate: number;
  daily_growth_rate: number;
  compression_ratio: number;
  tz: string;
}

export interface PartitionProjection {
  partition: string;
  current_size: number;
  projected_size: number;
  age_days: number;
  action: string;
  target_disk?: string;
  dropped: boolean;
  timestamp: string;
}

export interface StorageProjection {
  disk_name: string;
  current_used: number;
  projected_used: number[];
  projected_free: number[];
  timestamps: string[];
}

export interface DailyStat {
  date: string;
  hot_size: number;
  cold_size: number;
  archived_size: number;
  dropped_size: number;
  new_partitions: number;
  dropped_partitions: number;
}

export interface SavingsMetric {
  total_savings_bytes: number;
  drop_savings: number;
  archive_savings: number;
  tier_savings: number;
  savings_percent: number;
  projected_without_policies: number;
  projected_with_policies: number;
}

export interface ChartData {
  storage_timeline: unknown;
  action_breakdown: unknown;
  daily_growth: unknown;
  tier_distribution: unknown;
}

export interface SimulationResult {
  config: SimulationConfig;
  start_date: string;
  end_date: string;
  partitions: PartitionProjection[];
  storage: StorageProjection[];
  total_dropped_size: number;
  total_archived_size: number;
  total_moved_size: number;
  daily_stats: DailyStat[];
}
