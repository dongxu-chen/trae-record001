export type TransactionMode = 'TCC' | 'SAGA' | 'AT' | 'XA';
export type TransactionStatus = 'BEGIN' | 'COMMITTING' | 'COMMITTED' | 'ROLLBACKING' | 'ROLLEDBACK' | 'TIMEOUT' | 'FAILED' | 'UNKNOWN';
export type AlertLevel = 'INFO' | 'WARNING' | 'CRITICAL' | 'EMERGENCY';
export type DiagnosisSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface GlobalTransaction {
  xid: string;
  applicationId: string;
  transactionServiceGroup: string;
  mode: TransactionMode;
  status: TransactionStatus;
  beginTime: string;
  endTime: string | null;
  timeoutMs: number | null;
  traceId: string | null;
  remark: string | null;
  rollbackReason: string | null;
  trafficColor: string | null;
  businessType: string | null;
  tags: Record<string, string>;
  createdAt: string;
  updatedAt: string;
}

export interface CompensationStrategy {
  type: 'RETRY' | 'MANUAL' | 'DEGRADE' | 'RECONCILE';
  name: string;
  description: string;
  priority: number;
  estimatedTime: string;
  successRate: number;
}

export interface CompensationRecommendation {
  xid: string;
  failureReason: string;
  errorType: string;
  strategies: CompensationStrategy[];
  recommendedStrategy: CompensationStrategy;
  analysisDetail: string;
}

export interface PressureTestConfig {
  mode: TransactionMode;
  concurrency: number;
  durationSeconds: number;
  failureRate: number;
  networkDelayMs: number;
  businessType: string;
}

export interface PressureTestMetrics {
  totalRequests: number;
  successCount: number;
  failureCount: number;
  timeoutCount: number;
  avgResponseTimeMs: number;
  p95ResponseTimeMs: number;
  p99ResponseTimeMs: number;
  tps: number;
  rollbackCount: number;
  timestamp: string;
}

export interface PressureTestResult {
  testId: string;
  config: PressureTestConfig;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  startTime: string;
  endTime: string | null;
  metrics: PressureTestMetrics[];
  summary: PressureTestMetrics | null;
}

export interface BranchTransaction {
  id: number;
  branchId: string;
  xid: string;
  resourceId: string;
  lockKey: string | null;
  status: string;
  mode: string;
  applicationId: string;
  beginTime: string;
  endTime: string | null;
  traceId: string | null;
  spanId: string | null;
  errorMessage: string | null;
}

export interface TransactionEvent {
  id: number;
  xid: string;
  branchId: string | null;
  eventType: string;
  phase: string;
  traceId: string | null;
  spanId: string | null;
  applicationId: string | null;
  payload: string | null;
  errorMessage: string | null;
  eventTime: string;
}

export interface AlertRecord {
  id: number;
  alertName: string;
  xid: string;
  branchId: string | null;
  level: AlertLevel;
  alertRule: string;
  message: string;
  acknowledged: boolean;
  acknowledgedBy: string | null;
  acknowledgedAt: string | null;
  triggeredAt: string;
}

export interface AlertRule {
  name: string;
  description: string;
  level: string;
  condition: string;
  thresholdMs: number;
  enabled: boolean;
}

export interface DiagnosisReport {
  xid: string;
  severity: DiagnosisSeverity;
  rootCause: string;
  suggestion: string;
  items: DiagnosisItem[];
  relatedTransactions: string[];
  rollbackLog: RollbackLogAnalysis | null;
}

export interface DiagnosisItem {
  category: string;
  description: string;
  detail: string;
  severity: DiagnosisSeverity;
}

export interface RollbackLogAnalysis {
  triggerBranchId: string | null;
  triggerReason: string;
  cascadeDirection: string;
  logChain: RollbackLogEntry[];
  rootBranchId: string | null;
  rootErrorType: string;
  timelineSummary: string;
}

export interface RollbackLogEntry {
  sequence: number;
  branchId: string | null;
  action: string;
  phase: string;
  errorMessage: string | null;
  eventTime: string | null;
  isRootCause: boolean;
}

export interface TraceSpan {
  traceId: string;
  spanId: string;
  parentSpanId: string | null;
  name: string;
  serviceName: string;
  startMicros: number;
  endMicros: number;
  durationMicros: number;
  kind: string;
  tags: { key: string; value: string }[];
}

export interface TraceDagNode {
  id: string;
  name: string;
  serviceName: string;
  durationMs: number;
  status: string;
  transactionMode?: string;
  branchId?: string;
  depth?: number;
}

export interface TraceDagEdge {
  source: string;
  target: string;
  label: string;
}

export interface TraceDag {
  traceId: string;
  nodes: TraceDagNode[];
  edges: TraceDagEdge[];
}

export interface TransactionStats {
  byStatus: Record<string, number>;
  byMode: Record<string, number>;
  activeCount: number;
  lastHourCount: number;
}

export interface PageResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  number: number;
  size: number;
}
