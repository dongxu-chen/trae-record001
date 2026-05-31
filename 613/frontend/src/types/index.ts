export interface AlertTag {
  key: string;
  value: string;
}

export interface Alert {
  id: string;
  ruleName: string;
  alarmMessage: string;
  scope: string;
  service: string;
  serviceInstance?: string;
  endpointName?: string;
  startTime: number;
  priority: 'CRITICAL' | 'WARNING' | 'INFO';
  tags: AlertTag[];
}

export interface AlertRule {
  id: number;
  name: string;
  metricsName: string;
  threshold: number | number[];
  op: string;
  period: number;
  count: number;
  silencePeriod: number;
  message: string;
  enabled: boolean;
  priority: string;
}

export interface AlertCluster {
  clusterId: string;
  ruleName: string;
  alertCount: number;
  services: string[];
  timeSpan: { start: number; end: number };
  priorityDistribution: Record<string, number>;
  sampleAlerts: Alert[];
  patternFeatures: Record<string, any>;
}

export interface InefficientRule {
  ruleName: string;
  totalAlerts: number;
  frequencyScore: number;
  criticalityScore: number;
  noiseScore: number;
  inefficiencyScore: number;
  recommendation: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  metricsData: Record<string, any>;
}

export interface OptimizationSuggestion {
  ruleName: string;
  originalConfig: Record<string, any>;
  suggestedConfig: Record<string, any>;
  expectedImprovement: {
    alertReduction: number;
    reductionPercent: number;
    noiseReductionScore: number;
    criticalityPreserved: boolean;
    originalAlertCount: number;
    expectedAlertCount: number;
    optimizationMethod?: string;
    cvScore?: number;
    scoreStability?: number;
    cvDetails?: Record<string, any>;
  };
  confidence: number;
  reasoning: string;
}

export interface EvaluationResult {
  metricName: string;
  originalValue: number;
  optimizedValue: number;
  improvementPercent: number;
}

export interface RuleOptimizationResult {
  ruleName: string;
  optimizationApplied: boolean;
  originalConfig: Record<string, any>;
  optimizedConfig: Record<string, any>;
  evaluation: EvaluationResult[];
  simulationResults: Record<string, any>;
}

export interface ClusterSummary {
  totalClusters: number;
  totalAlertsInClusters: number;
  avgClusterSize: number;
  maxClusterSize: number;
  minClusterSize: number;
  ruleDistribution: Record<string, number>;
  priorityDistribution: Record<string, number>;
  periodicClusters: number;
  periodicPercentage: number;
}

export interface OverallStatistics {
  totalAlerts: number;
  uniqueRules: number;
  uniqueServices: number;
  priorityDistribution: Record<string, number>;
  inefficientRulesCount: number;
  inefficientRulesPercentage: number;
  alertsFromInefficient: number;
  alertsFromInefficientPercentage: number;
  highSeverityCount: number;
  mediumSeverityCount: number;
  avgInefficiencyScore: number;
  potentialAlertReduction: number;
  potentialReductionPercentage: number;
  timeRange: { start: number; end: number };
}

export interface OptimizationSummary {
  totalSuggestions: number;
  totalExpectedReduction: number;
  avgReductionPercent: number;
  avgConfidence: number;
  highConfidenceCount: number;
  mediumConfidenceCount: number;
  thresholdIncreases: number;
  periodIncreases: number;
}

export interface OverallEvaluation {
  totalEvaluations: number;
  successfulEvaluations: number;
  totalOriginalAlerts: number;
  totalOptimizedAlerts: number;
  totalReduction: number;
  overallReductionPercent: number;
  avgImprovementPercent: number;
  avgNoiseReductionPercent: number;
  avgCriticalCoverage: number;
  highImpactOptimizations: number;
  avgF1ScoreOriginal?: number;
  avgF1ScoreOptimized?: number;
  avgPrecisionOriginal?: number;
  avgPrecisionOptimized?: number;
  avgRecallOriginal?: number;
  avgRecallOptimized?: number;
  f1ImprovedCount?: number;
  f1ImprovementRate?: number;
}

export interface AnalysisParams {
  lookbackHours?: number;
  minInefficiencyScore?: number;
  minConfidence?: number;
}

export interface HealthStatus {
  status: string;
  skywalkingConnected: boolean;
  mockMode: boolean;
  timestamp: string;
}

export type RuleGenerationMethod = 'fault_pattern' | 'anomaly_pattern' | 'correlation' | 'frequent_pattern';

export interface GeneratedRule {
  ruleName: string;
  metricsName: string;
  threshold: number;
  op: string;
  period: number;
  count: number;
  silencePeriod: number;
  message: string;
  priority: string;
  enabled: boolean;
  generationMethod: RuleGenerationMethod;
  confidence: number;
  support: number;
  faultAssociationScore: number;
  sourceFaultEvents: string[];
  reasoning: string;
  service?: string;
  endpoint?: string;
  instance?: string;
}

export interface FaultEvent {
  startTime: number;
  endTime: number;
  duration: number;
  alertCount: number;
  services: string[];
  rules: string[];
  hasCritical: boolean;
  representativeMessage: string;
}

export interface RuleGenerationStatistics {
  totalGenerated: number;
  byMethod: Record<string, number>;
  faultEventsIdentified: number;
  avgConfidence: number;
  avgSupport: number;
  servicesCovered: number;
}

export type SuppressionType = 'dependency' | 'storm' | 'redundant' | 'topological';

export interface SuppressionRule {
  suppressionId: string;
  suppressionType: SuppressionType;
  triggerRule: string;
  suppressedRules: string[];
  triggerService?: string;
  suppressedServices: string[];
  timeWindow: number;
  confidence: number;
  support: number;
  expectedReduction: number;
  reasoning: string;
  severity: string;
  enabled: boolean;
}

export interface StormPattern {
  patternId: string;
  startTime: number;
  endTime: number;
  alertCount: number;
  ruleCount: number;
  serviceCount: number;
  rules: string[];
  services: string[];
  rootCauseCandidates: Array<{
    ruleName: string;
    score: number;
    firstTime: number;
    alertCount: number;
    isEarliest: boolean;
  }>;
  severity: string;
}

export interface DependencyGraph {
  nodes: string[];
  edges: Array<{
    from: string;
    to: string;
    weight: number;
    confidence: number;
    avgTime: number;
  }>;
}

export interface SuppressionStatistics {
  totalSuppressions: number;
  byType: Record<string, number>;
  stormPatternsDetected: number;
  totalExpectedReduction: number;
  reductionPercentage: number;
  avgConfidence: number;
  highSeverityCount: number;
  rulesSuppressed: number;
}

export interface SuppressionSimulationResult {
  originalCount: number;
  suppressedCount: number;
  remainingCount: number;
  reductionPercent: number;
  suppressionDetails: Array<{
    suppressionId: string;
    suppressionType: string;
    triggerRule: string;
    suppressedCount: number;
    suppressedAlerts: Array<{
      alertId: string;
      ruleName: string;
      service: string;
      time: number;
      triggerTime: number;
      delayMs: number;
    }>;
  }>;
}

export type ReviewGranularity = 'hourly' | 'daily' | 'custom';

export interface TimeSeriesDataPoint {
  timestamp: number;
  datetime: string;
  originalCount: number;
  optimizedCount: number;
  reductionCount: number;
  reductionPercent: number;
}

export interface RuleComparison {
  ruleName: string;
  originalCount: number;
  optimizedCount: number;
  reductionCount: number;
  reductionPercent: number;
  priority: string;
  service: string;
  thresholdChanged: boolean;
  originalThreshold?: number;
  optimizedThreshold?: number;
}

export interface ServiceComparison {
  serviceName: string;
  originalCount: number;
  optimizedCount: number;
  reductionCount: number;
  reductionPercent: number;
  rulesAffected: number;
  topRules: string[];
}

export interface PriorityComparison {
  priority: string;
  originalCount: number;
  optimizedCount: number;
  reductionCount: number;
  reductionPercent: number;
}

export interface ReviewSummary {
  totalOriginal: number;
  totalOptimized: number;
  totalReduction: number;
  totalReductionPercent: number;
  peakReductionPercent: number;
  avgReductionPercent: number;
  rulesAnalyzed: number;
  rulesImproved: number;
  rulesWorsened: number;
  servicesAffected: number;
  granularity: string;
  periodStart: number;
  periodEnd: number;
  periodHours: number;
}

export interface AlertReviewReport {
  reviewPeriod: { start: number; end: number };
  timeSeries: TimeSeriesDataPoint[];
  byRule: RuleComparison[];
  byService: ServiceComparison[];
  byPriority: PriorityComparison[];
  summary: ReviewSummary;
  recommendations: string[];
}
