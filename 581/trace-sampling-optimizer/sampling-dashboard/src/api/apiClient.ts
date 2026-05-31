import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

export interface SamplingRate {
  serviceName: string;
  rate: number;
  previousRate: number;
  reason: string;
  effectiveTime: string;
  isEdgeOptimized: boolean;
  confidenceScore: number;
}

export interface CostSummary {
  dailyBudgetUsd: number;
  currentSpendUsd: number;
  remainingBudget: number;
  utilizationPercent: number;
  overBudget: boolean;
  alertTriggered: boolean;
  serviceBreakdown: Record<string, number>;
}

export interface FeedbackAnalysis {
  serviceName: string;
  totalSignals: number;
  errorRateSignals: number;
  latencySignals: number;
  missingTraceSignals: number;
  costOverrunSignals: number;
  effectiveSignals: number;
  avgSeverity: number;
}

export interface AgentStatus {
  explorationRate: number;
  qTableSizes: Record<string, number>;
}

export interface CpuCostSummary {
  cpuCostPerService: Record<string, number>;
  cpuCostMultiplier: number;
  overallCostEfficiency: number;
  costPerSpanCpu: number;
  cpuCoreCostPerHourUsd: number;
  spansProcessedPerCoreSecond: number;
  samplingCpuOverheadPercent: number;
  totalCpuCost: number;
}

export interface ComprehensiveCostAssessment {
  serviceName: string;
  proposedSamplingRate: number;
  storageCost: number;
  networkCost: number;
  computeCost: number;
  cpuCost: number;
  totalCost: number;
  costSaving: number;
  observabilityGain: number;
  costEfficiency: number;
  observabilityLossRisk: number;
  errorDetectionRisk: number;
  latencyDetectionRisk: number;
  aggregateRisk: number;
  compositeScore: number;
  budgetUtilization: number;
  recommendation: string;
  recommendedRate: number;
}

export interface EdgeAsyncStatus {
  localDecisionsMade: number;
  centralOverridesApplied: number;
  conflictsDetected: number;
  reportsSent: number;
  reportsDropped: number;
  pendingReports: number;
  activeLocalDecisions: number;
  activeCentralDecisions: number;
  localDecisionWeight: number;
}

export interface CentralDecision {
  serviceName: string;
  samplingRate: number;
  effectiveTimeMs: number;
  reason: string;
  confidence: number;
  serviceLevel: string;
}

export interface AgentStatus {
  explorationRate: number;
  useStateReduction: boolean;
  reductionStats: {
    useStateReduction: boolean;
    targetDimensions: number;
    hashBuckets: number;
    uniqueStates: number;
    cacheHits: number;
    cacheMisses: number;
    cacheHitRate: string;
    reducedQTablesCount: number;
    serviceStateCacheSize: number;
  };
  qTableSizes: Record<string, number>;
}

export const fetchSamplingRates = () =>
  api.get<{ rates: Record<string, SamplingRate>; totalServices: number }>('/sampling/rates');

export const updateServiceRate = (serviceName: string, data: Record<string, unknown>) =>
  api.put<SamplingRate>(`/sampling/rates/${serviceName}`, data);

export const triggerOptimization = () =>
  api.post<Record<string, SamplingRate>>('/sampling/optimize');

export const edgeSamplingDecision = (serviceName: string, traceId: string, globalRate: number) =>
  api.get(`/sampling/edge/${serviceName}`, { params: { traceId, globalRate } });

export const fetchCostSummary = () =>
  api.get<CostSummary>('/cost/summary');

export const fetchCostProjections = () =>
  api.get('/cost/projections');

export const fetchBudgetStatus = () =>
  api.get('/cost/budget-status');

export const fetchCpuCostSummary = () =>
  api.get<CpuCostSummary>('/cost/cpu-summary');

export const fetchCostAssessment = (serviceName: string, proposedRate: number) =>
  api.get<ComprehensiveCostAssessment>(`/cost/assessment/${serviceName}`, { params: { proposedRate } });

export const fetchAllCostAssessments = () =>
  api.get<Record<string, ComprehensiveCostAssessment>>('/cost/all-assessments');

export const submitFeedbackSignal = (data: Record<string, unknown>) =>
  api.post('/feedback/signal', data);

export const fetchFeedbackAnalysis = (serviceName: string) =>
  api.get<FeedbackAnalysis>(`/feedback/analysis/${serviceName}`);

export const fetchAgentStatus = () =>
  api.get<AgentStatus>('/feedback/agent-status');

export const fetchEdgeSamplerStatus = () =>
  api.get('/feedback/edge-sampler-status');

export const fetchEdgeAsyncStatus = () =>
  api.get<EdgeAsyncStatus>('/feedback/edge-async-status');

export const fetchCentralDecisions = () =>
  api.get<Record<string, CentralDecision>>('/feedback/central-decisions');

export const pushCentralDecisions = () =>
  api.post('/feedback/push-central-decisions');

export interface AnomalyEnhancementStats {
  totalTracesProcessed: number;
  anomalyTracesDetected: number;
  forceSampledTraces: number;
  activeAnomalyServices: number;
  forceSamplingRate: number;
}

export interface SamplingEffectReport {
  serviceName: string;
  totalProblems: number;
  problemsDetected: number;
  problemsMissed: number;
  detectionRate: number;
  detectionRateChange: number;
  detectionByType: Record<string, number>;
  averageSamplingRate: number;
  costEfficiency: number;
}

export interface HeatTierStats {
  heatTier: string;
  timeSinceLastAccessMs: number;
  recentAccessCount: number;
  totalAccessCount: number;
  adjustedSamplingRate: number;
}

export interface OverallEvaluation {
  overallDetectionRate: number;
  detectionRateByProblemType: Record<string, number>;
  samplingRateDetectionCorrelation: Record<string, number>;
}

export const fetchAnomalyStats = () =>
  api.get<AnomalyEnhancementStats>('/enhancement/anomaly/stats');

export const fetchServiceErrorRate = (serviceName: string) =>
  api.get<number>(`/enhancement/anomaly/service/${serviceName}/error-rate`);

export const fetchBoostedSamplingRate = (serviceName: string) =>
  api.get<number>(`/enhancement/anomaly/service/${serviceName}/boosted-rate`);

export const checkForceSample = (traceId: string, serviceName: string, hasError: boolean, statusCode: number) =>
  api.post<boolean>('/enhancement/anomaly/check-force-sample', null, {
    params: { traceId, serviceName, hasError, statusCode }
  });

export const fetchServiceEvaluation = (serviceName: string) =>
  api.get<SamplingEffectReport>(`/enhancement/evaluation/service/${serviceName}`);

export const fetchAllEvaluations = () =>
  api.get<Record<string, SamplingEffectReport | OverallEvaluation>>('/enhancement/evaluation/all');

export const recordProblem = (problemId: string, serviceName: string, type: string, detected: boolean, samplingRate: number) =>
  api.post('/enhancement/evaluation/record-problem', null, {
    params: { problemId, serviceName, type, detected, samplingRate }
  });

export const fetchHeatTierStats = (serviceName: string) =>
  api.get<HeatTierStats>(`/enhancement/storage/heat-tier/${serviceName}`);

export const fetchAllHeatTiers = () =>
  api.get<Record<string, string>>('/enhancement/storage/heat-tiers');

export const applyHeatTierAdjustment = (serviceName: string, baseRate: number) =>
  api.post<number>('/enhancement/storage/adjust-rate', null, {
    params: { serviceName, baseRate }
  });

export const recordServiceHeat = (serviceName: string) =>
  api.post(`/enhancement/storage/record-heat/${serviceName}`);

export default api;
