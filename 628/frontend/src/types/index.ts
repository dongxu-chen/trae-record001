export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface TimeSeries {
  name: string;
  labels: Record<string, string>;
  points: TimeSeriesPoint[];
}

export type AnomalyDirection = 'up' | 'down' | 'both';

export interface Anomaly {
  id: string;
  metric: string;
  labels: Record<string, string>;
  timestamp: string;
  value: number;
  expected: number;
  deviation: number;
  direction: AnomalyDirection;
  score: number;
  cluster_id: number;
}

export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface Alert {
  id: string;
  anomalies: Anomaly[];
  severity: AlertSeverity;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  group_key: string;
  suppressed: boolean;
  acknowledged: boolean;
}

export interface CorrelationResult {
  metric_a: string;
  metric_b: string;
  coefficient: number;
  _p_value?: number;
  significant: boolean;
}

export interface ClusterResult {
  cluster_id: number;
  anomalies: Anomaly[];
  center_time: string;
  size: number;
  severity: AlertSeverity;
}

export interface RootCauseEvidence {
  type: string;
  description: string;
  value: number;
}

export interface RootCause {
  metric: string;
  confidence: number;
  reason: string;
  evidence: RootCauseEvidence[];
  correlation: number;
  lead_time: number;
  anomaly?: Anomaly;
}

export interface RootCauseResult {
  anomaly: Anomaly;
  root_causes: RootCause[];
  top_cause?: RootCause;
  analysis_time: string;
}

export interface Prediction {
  metric: string;
  predicted_time: string;
  direction: AnomalyDirection;
  confidence: number;
  current_value: number;
  threshold: number;
  trend_slope: number;
  reason: string;
}

export interface InjectionConfig {
  metric: string;
  type: 'spike' | 'drop' | 'gradual' | 'oscillation';
  magnitude: number;
  start_index: number;
  duration: number;
}

export interface DetectionDetail {
  index: number;
  detected: boolean;
  expected: number;
  actual: number;
  score: number;
}

export interface InjectionResult {
  injected_metric: string;
  injection_type: string;
  original_series: number[];
  injected_series: number[];
  detected_count: number;
  injected_count: number;
  sensitivity: number;
  detection_delay: number;
  false_positive_rate: number;
  detection_details: DetectionDetail[];
}

export interface DrillSummary {
  total_tests: number;
  detection_rate: number;
  avg_sensitivity: number;
  avg_false_positive_rate: number;
  avg_detection_delay: number;
  grade: string;
  summary: string;
  by_type?: Record<string, {
    count: number;
    avg_sensitivity: number;
    avg_false_positive: number;
    avg_delay: number;
    detection_rate: number;
  }>;
}

export interface DetectResponse {
  anomalies: Anomaly[];
  clusters: ClusterResult[];
  correlations: CorrelationResult[];
  alerts: Alert[];
  root_causes: RootCauseResult[];
  predictions: Prediction[];
  total_anomalies: number;
  total_clusters: number;
  total_root_causes: number;
  total_predictions: number;
  algorithm: Record<string, string>;
}

export interface DetectRequest {
  query: string;
  start?: string;
  end?: string;
  step?: string;
  direction?: AnomalyDirection;
  alpha?: number;
  period?: number;
}

export interface BatchDetectRequest {
  queries: string[];
  start?: string;
  end?: string;
  step?: string;
  direction?: AnomalyDirection;
  alpha?: number;
  period?: number;
}
