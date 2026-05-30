export interface ThresholdRecommendation {
  metric: string;
  method: 'zscore' | 'percentile' | 'iqr';
  warning: number;
  danger: number;
  critical: number;
  confidence: number;
  sampleSize: number;
  stats: { mean: number; stdDev: number; p95: number };
}

export interface MetricCorrelation {
  metric: string;
  relatedMetric: string;
  strength: number;
  description: string;
}

export interface AlertFeedback {
  id: string;
  alertId: string;
  ruleId: string;
  type: 'false_positive' | 'true_positive' | 'needs_adjustment';
  comment?: string;
  createdAt: string;
}

export interface FeedbackStats {
  ruleId: string;
  truePositive: number;
  falsePositive: number;
  needsAdjustment: number;
  total: number;
}

export interface ThresholdRule {
  id: string;
  name: string;
  metric: string;
  conditions: AlertCondition[];
  level: 'warning' | 'danger' | 'critical';
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AlertCondition {
  id: string;
  field: string;
  operator: '>' | '<' | '>=' | '<=' | '==' | '!=';
  value: number;
  logic?: 'AND' | 'OR';
  groupId?: string;
}

export interface ConditionGroup {
  id: string;
  name?: string;
  logic: 'AND' | 'OR';
}

export interface AlertRecord {
  id: string;
  ruleId: string;
  ruleName: string;
  metric: string;
  level: 'warning' | 'danger' | 'critical';
  triggerValue: number;
  thresholdValue: number;
  expression: string;
  message: string;
  snapshot: ChartSnapshot;
  createdAt: string;
  acknowledged: boolean;
  feedbackType?: 'false_positive' | 'true_positive' | 'needs_adjustment';
  hasFeedback?: boolean;
}

export interface ChartSnapshot {
  seriesData: number[];
  timestamp: string;
  xAxisLabels: string[];
}

export interface MetricData {
  metric: string;
  value: number;
  timestamp: string;
  labels: Record<string, string>;
}

export interface WebSocketMessage {
  type: 'data' | 'alert' | 'config_update';
  payload: any;
}

export interface AlertHistoryQuery {
  page: number;
  pageSize: number;
  level?: 'warning' | 'danger' | 'critical';
  metric?: string;
  startTime?: string;
  endTime?: string;
  acknowledged?: boolean;
}
