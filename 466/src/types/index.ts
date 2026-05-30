export type MetricType = 'row_count' | 'null_rate' | 'duplicate_rate' | 'distribution_drift'
export type Severity = 'critical' | 'warning' | 'info'
export type AlertStatus = 'active' | 'acknowledged' | 'resolved'
export type TableStatus = 'healthy' | 'warning' | 'critical'
export type ImportanceLevel = 'critical' | 'high' | 'medium' | 'low'

export interface MonitoredTable {
  id: string
  name: string
  schema_name: string
  description: string
  row_count: number
  null_rate: number
  duplicate_rate: number
  distribution_drift: number
  quality_score: number
  status: TableStatus
  updated_at: string
}

export interface FieldImportance {
  id: string
  table_id: string
  field_name: string
  importance: ImportanceLevel
  updated_at: string
}

export interface Rule {
  id: string
  name: string
  table_id: string
  table_name: string
  metric_type: MetricType
  condition: string
  threshold: number
  schedule: string
  severity: Severity
  enabled: boolean
  field_importance: ImportanceLevel
  created_at: string
  updated_at: string
}

export interface RuleTemplate {
  id: string
  name: string
  metric_type: MetricType
  condition: string
  default_threshold: number
  severity: Severity
  description: string
}

export interface QualityMetric {
  id: string
  table_id: string
  metric_type: MetricType
  value: number
  recorded_at: string
}

export interface Alert {
  id: string
  rule_id: string
  rule_name?: string
  table_id: string
  table_name?: string
  severity: Severity
  status: AlertStatus
  message: string
  actual_value: number
  threshold_value: number
  triggered_at: string
  acknowledged_at?: string
  resolved_at?: string
  resolution?: string
}

export interface DimensionScore {
  dimension: string
  score: number
  weight: number
}

export interface TableScore {
  table_id: string
  table_name: string
  overall_score: number
  dimensions: DimensionScore[]
}

export interface TableScoreDetail {
  table_id: string
  overall_score: number
  dimensions: DimensionScore[]
  history: { date: string; score: number }[]
}

export interface LineageNode {
  id: string
  name: string
  type: 'table' | 'report'
  status: TableStatus
  schema?: string
  description?: string
}

export interface LineageEdge {
  source: string
  target: string
  type: 'data_flow' | 'dependency' | 'dimension' | 'hierarchy' | 'feed'
}

export interface DashboardOverview {
  overallScore: number
  activeAlerts: number
  monitoredTables: number
  totalRules: number
  scoreTrend: { date: string; score: number }[]
  statusBreakdown: { healthy: number; warning: number; critical: number }
}

export interface MetricsTrendPoint {
  date: string
  value: number
  table_name: string
}

export interface AnomalyHeatmapPoint {
  table_name: string
  metric: string
  severity: number
}

export interface AffectedTable {
  table_id: string
  table_name: string
  impact_level: string
  affected_metrics: string[]
}

export interface RootCause {
  table_id: string
  table_name: string
  confidence: number
  reason: string
}

export interface DynamicThreshold {
  base_threshold: number
  importance_multiplier: number
  adjusted_threshold: number
  importance_level: ImportanceLevel
}

export interface ScoreWeightConfig {
  table_id: string
  completeness_weight: number
  consistency_weight: number
  timeliness_weight: number
  accuracy_weight: number
}

export interface AffectedReport {
  report_id: string
  report_name: string
  impact_level: string
  affected_data_sources: string[]
  quality_risk: string
}

export interface ImpactAnalysis {
  source_table: string
  affected_downstream: AffectedTable[]
  affected_reports: AffectedReport[]
  root_cause_candidates: RootCause[]
}

export type ParseStatus = 'pending' | 'success' | 'failed'

export interface SqlParseLog {
  id: string
  target_table_id: string
  sql_content: string
  source_tables?: string
  parse_status: ParseStatus
  new_edges_count: number
  error_message?: string
  parsed_at: string
}

export interface SqlParseRequest {
  target_table_id: string
  sql_content: string
}

export interface SqlParseResult {
  parse_status: ParseStatus
  source_tables: string[]
  new_edges: { source_id: string; target_id: string; type: string }[]
  error_message?: string
}

export interface AnomalySampleRecord {
  id: number | string
  field: string
  value: any
  reason: string
}

export interface AnomalySample {
  id: string
  alert_id?: string
  table_id: string
  metric_type: MetricType
  sample_data: string
  sample_count: number
  generated_at: string
}

export interface QualityForecast {
  id: string
  forecast_date: string
  horizon_days: number
  predicted_alerts: number
  predicted_critical: number
  predicted_warning: number
  trend_direction: 'increasing' | 'stable' | 'decreasing'
  confidence: number
  model_version: string
  generated_at: string
  next_7_days: number
  next_14_days: number
  next_30_days: number
}

export interface ForecastPoint {
  date: string
  predicted_alerts: number
  predicted_critical: number
  predicted_warning: number
  upper_bound: number
  lower_bound: number
}

export interface DashboardOverview {
  overallScore: number
  activeAlerts: number
  monitoredTables: number
  totalRules: number
  scoreTrend: { date: string; score: number }[]
  statusBreakdown: { healthy: number; warning: number; critical: number }
  forecast?: {
    next_7_days: number
    trend_direction: string
    confidence: number
  }
}
