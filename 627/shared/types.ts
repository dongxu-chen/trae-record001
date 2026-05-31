export type RuleType = 'null_check' | 'uniqueness' | 'value_range' | 'dependency';

export interface RuleConfig {
  nullCheck?: {
    allowNull: boolean;
  };
  uniqueness?: {
    columns: string[];
  };
  valueRange?: {
    min?: number;
    max?: number;
    allowedValues?: string[];
    pattern?: string;
  };
  dependency?: {
    sourceColumn: string;
    targetTable: string;
    targetColumn: string;
    sampleRate?: number;
  };
}

export interface DataQualityRule {
  id: string;
  name: string;
  description: string;
  type: RuleType;
  dataSource: string;
  tableName: string;
  columnName: string;
  config: RuleConfig;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface RuleTemplate {
  id: string;
  name: string;
  description: string;
  type: RuleType;
  defaultConfig: RuleConfig;
}

export interface ScheduledTask {
  id: string;
  name: string;
  ruleIds: string[];
  cronExpression: string;
  enabled: boolean;
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface TaskExecution {
  id: string;
  taskId: string;
  taskName: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  startTime: string;
  endTime?: string;
  totalRecords: number;
  failedRecords: number;
  qualityScore: number;
}

export interface QualityIssue {
  id: string;
  executionId: string;
  ruleId: string;
  ruleName: string;
  tableName: string;
  columnName: string;
  rowIdentifier: string;
  issueType: string;
  description: string;
  status: 'open' | 'in_progress' | 'resolved';
  assignee?: string;
  priority: 'low' | 'medium' | 'high';
  createdAt: string;
  resolvedAt?: string;
}

export interface TrendDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface DynamicThreshold {
  upper: number;
  lower: number;
  baseline: number;
}

export interface TrendDataWithThreshold {
  date: string;
  value: number;
  upper: number;
  lower: number;
  baseline: number;
  isAnomaly: boolean;
  label?: string;
}

export interface UserRole {
  id: string;
  name: string;
  role: 'admin' | 'engineer' | 'analyst';
}

export interface OverviewStats {
  totalRules: number;
  activeRules: number;
  totalTasks: number;
  totalExecutions: number;
  openIssues: number;
  avgQualityScore: number;
}

export interface RuleExecutionResult {
  ruleId: string;
  ruleName: string;
  success: boolean;
  totalRecords: number;
  failedRecords: number;
  issues: Omit<QualityIssue, 'id' | 'executionId' | 'status' | 'assignee' | 'priority' | 'createdAt' | 'resolvedAt'>[];
}

export interface RuleScoreDetail {
  ruleId: string;
  ruleName: string;
  ruleType: RuleType;
  tableName: string;
  columnName: string;
  score: number;
  totalRecords: number;
  failedRecords: number;
  weight: number;
}

export interface HealthScore {
  overall: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  ruleScores: RuleScoreDetail[];
  dimensionScores: {
    completeness: number;
    uniqueness: number;
    validity: number;
    consistency: number;
  };
  timestamp: string;
}

export interface AutoFixResult {
  issueId: string;
  issueType: string;
  tableName: string;
  columnName: string;
  rowIdentifier: string;
  fixStrategy: string;
  oldValue: string;
  newValue: string;
  fixed: boolean;
  message: string;
}

export interface AutoFixPreview {
  totalFixable: number;
  fixes: AutoFixResult[];
}

export interface BoardMetrics {
  healthScore: HealthScore;
  totalRules: number;
  activeRules: number;
  openIssues: number;
  totalRecords: number;
  failedRecords: number;
  recentScores: TrendDataPoint[];
  issueDistribution: { type: string; count: number; label: string }[];
  lastUpdated: string;
}
