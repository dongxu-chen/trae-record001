export type IdAlgorithm = 'SNOWFLAKE' | 'SEGMENT' | 'RANDOM';
export type ClockMode = 'NORMAL' | 'CLOCK_DRIFT' | 'CLOCK_BACKWARD' | 'MIXED';

export interface TestConfig {
  algorithm: IdAlgorithm;
  threadCount: number;
  durationSeconds: number;
  idCount?: number;
  snowflakeConfig?: SnowflakeConfig;
  segmentConfig?: SegmentConfig;
  uniquenessConfig?: UniquenessCheckConfig;
}

export interface SnowflakeConfig {
  workerId: number;
  datacenterId: number;
  clockMode: ClockMode;
  clockOffsetMs: number;
  clockBackProbability: number;
}

export interface SegmentConfig {
  segmentSize: number;
}

export interface UniquenessCheckConfig {
  sampleSize: number;
  falsePositiveProbability: number;
}

export interface RealtimeMetrics {
  timestamp: number;
  qps: number;
  avgLatency: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;
  generatedCount: number;
  progress: number;
}

export interface SampledMetrics {
  timestamp: number;
  qps: number;
  avgLatency: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;
  generatedCount: number;
  progress: number;
}

export interface DuplicateDetail {
  id: string;
  count: number;
}

export interface TestReport {
  id: string;
  config: TestConfig;
  startTime: number;
  endTime: number;
  summary: SummaryStats;
  latencyStats: LatencyStats;
  uniquenessCheck: UniquenessCheck;
  clockStats: ClockSimulationStats;
  memoryStats: MemoryUsageStats;
  sampledMetrics: SampledMetrics[];
}

export interface SummaryStats {
  totalGenerated: number;
  successCount: number;
  errorCount: number;
  avgQps: number;
  peakQps: number;
  minQps: number;
  stdDevQps: number;
  durationSeconds: number;
}

export interface LatencyStats {
  avg: number;
  min: number;
  max: number;
  p50: number;
  p90: number;
  p95: number;
  p99: number;
  p999: number;
  stdDev: number;
}

export interface UniquenessCheck {
  isUnique: boolean;
  bloomFilterDuplicates: number;
  sampleDuplicates: number;
  sampleSize: number;
  falsePositives: number;
  estimatedDuplicateRate: number;
  sampleDuplicateRate: number;
  adjustedDuplicateRate: number;
  memoryUsageBytes: number;
  duplicateDetails: DuplicateDetail[];
  sampleIds: string[];
}

export interface ClockSimulationStats {
  enabled: boolean;
  mode: ClockMode;
  clockDriftCount: number;
  clockBackwardCount: number;
  forcedWaitCount: number;
  totalWaitTimeMs: number;
  totalDriftApplied: number;
  totalBackwardApplied: number;
}

export interface MemoryUsageStats {
  peakMemoryBytes: number;
  avgMemoryBytes: number;
  estimatedMemorySavedBytes: number;
}

export interface StabilityTestConfig {
  algorithm: IdAlgorithm;
  threadCount: number;
  durationHours: number;
  checkpointIntervalMinutes: number;
  autoRecovery: boolean;
  qpsDegradationThreshold: number;
  latencySpikeThreshold: number;
  errorRateThreshold: number;
  snowflakeConfig?: { workerId: number; datacenterId: number; clockMode: ClockMode; clockOffsetMs: number; clockBackProbability: number };
  segmentConfig?: { segmentSize: number };
  uniquenessConfig?: UniquenessCheckConfig;
}

export interface StabilityCheckpoint {
  timestamp: number;
  elapsedMs: number;
  generatedCount: number;
  errorCount: number;
  avgQps: number;
  avgLatency: number;
  p99Latency: number;
  isHealthy: boolean;
  healthMessage: string;
}

export interface AnomalyEvent {
  timestamp: number;
  type: string;
  severity: string;
  message: string;
  observedValue: number;
  thresholdValue: number;
}

export interface PerformanceTrend {
  qpsTrendSlope: number;
  latencyTrendSlope: number;
  qpsDegraded: boolean;
  latencyDegraded: boolean;
  qpsVariability: number;
  latencyVariability: number;
}

export interface StabilityTestReport {
  id: string;
  config: StabilityTestConfig;
  startTime: number;
  endTime: number;
  status: string;
  totalDurationMs: number;
  checkpointCount: number;
  totalGenerated: number;
  totalErrors: number;
  overallAvgQps: number;
  overallPeakQps: number;
  overallAvgLatency: number;
  overallP99Latency: number;
  uniquenessPassed: boolean;
  checkpoints: StabilityCheckpoint[];
  anomalies: AnomalyEvent[];
  performanceTrend: PerformanceTrend;
}

export interface PerformanceBaseline {
  id: string;
  algorithm: string;
  threadCount: number;
  createdTime: number;
  isBest: boolean;
  avgQps: number;
  peakQps: number;
  avgLatency: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;
  p999Latency: number;
  errorRate: number;
  totalGenerated: number;
  testDurationSeconds: number;
  testId: string;
}

export interface BaselineComparison {
  reportId: string;
  baselineId: string;
  hasBaseline: boolean;
  baselineAvgQps: number;
  currentAvgQps: number;
  qpsChangePercent: number;
  baselineAvgLatency: number;
  currentAvgLatency: number;
  latencyChangePercent: number;
  baselineP99Latency: number;
  currentP99Latency: number;
  p99ChangePercent: number;
  overallVerdict: string;
}

export interface AutoTuningConfig {
  algorithm: IdAlgorithm;
  maxRounds: number;
  testDurationSeconds: number;
  optimizationTarget: string;
  threadCountRange: ParamRange;
  algorithmParamRanges?: Record<string, ParamRange>;
}

export interface ParamRange {
  min: number;
  max: number;
  step: number;
}

export interface TuningRoundResult {
  round: number;
  config: TestConfig;
  score: number;
  avgQps: number;
  avgLatency: number;
  p99Latency: number;
  errorRate: number;
  uniquenessPassed: boolean;
  totalGenerated: number;
}

export interface TuningResult {
  bestConfig: TestConfig;
  bestScore: number;
  bestAvgQps: number;
  bestAvgLatency: number;
  bestP99Latency: number;
  bestParams: Record<string, unknown>;
}

export interface ParamSuggestion {
  paramName: string;
  recommendedValue: unknown;
  reason: string;
  impact: number;
}

export interface AutoTuningReport {
  id: string;
  config: AutoTuningConfig;
  startTime: number;
  endTime: number;
  status: string;
  completedRounds: number;
  totalRounds: number;
  bestResult: TuningResult | null;
  roundResults: TuningRoundResult[];
  suggestions: ParamSuggestion[];
}
