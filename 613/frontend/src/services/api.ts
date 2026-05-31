import axios from 'axios';
import {
  Alert,
  AlertRule,
  AlertCluster,
  InefficientRule,
  OptimizationSuggestion,
  RuleOptimizationResult,
  HealthStatus,
  ClusterSummary,
  OverallStatistics,
  OptimizationSummary,
  OverallEvaluation,
} from '@/types';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const healthApi = {
  check: async (): Promise<HealthStatus> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export const alertsApi = {
  getAlerts: async (params?: {
    lookbackHours?: number;
    ruleName?: string;
    service?: string;
    priority?: string;
  }): Promise<Alert[]> => {
    const response = await api.get('/alerts', { params });
    return response.data;
  },

  getClusters: async (params?: {
    lookbackHours?: number;
    minSamples?: number;
    epsTime?: number;
  }): Promise<{
    clusters: AlertCluster[];
    similarPairs: [string, string, number][];
    summary: ClusterSummary;
    totalAlerts: number;
  }> => {
    const response = await api.get('/alerts/clusters', { params });
    return response.data;
  },
};

export const rulesApi = {
  getRules: async (): Promise<AlertRule[]> => {
    const response = await api.get('/rules');
    return response.data;
  },

  getInefficientRules: async (params?: {
    lookbackHours?: number;
    minInefficiencyScore?: number;
  }): Promise<{
    inefficientRules: InefficientRule[];
    statistics: OverallStatistics;
    totalAlertsAnalyzed: number;
    totalRulesAnalyzed: number;
  }> => {
    const response = await api.get('/rules/inefficient', { params });
    return response.data;
  },

  getOptimizationSuggestions: async (params?: {
    lookbackHours?: number;
    minConfidence?: number;
  }): Promise<{
    suggestions: OptimizationSuggestion[];
    summary: OptimizationSummary;
    totalAlertsAnalyzed: number;
  }> => {
    const response = await api.get('/rules/optimize', { params });
    return response.data;
  },

  evaluateOptimizations: async (params?: {
    lookbackHours?: number;
  }): Promise<{
    evaluationResults: RuleOptimizationResult[];
    overallEvaluation: OverallEvaluation;
    totalEvaluatedRules: number;
  }> => {
    const response = await api.get('/rules/evaluate', { params });
    return response.data;
  },

  compareConfigs: async (
    ruleName: string,
    configs: Record<string, any>[],
    params?: { lookbackHours?: number }
  ): Promise<Record<string, any>[]> => {
    const response = await api.post('/rules/compare-configs', configs, {
      params: { ruleName, ...params },
    });
    return response.data;
  },

  updateRule: async (ruleId: number, config: Record<string, any>): Promise<any> => {
    const response = await api.put(`/rules/${ruleId}`, config);
    return response.data;
  },
};

export const analysisApi = {
  getFullReport: async (params?: {
    lookbackHours?: number;
  }): Promise<{
    analysisPeriod: { start: number; end: number; lookbackHours: number };
    totalAlerts: number;
    uniqueRules: number;
    uniqueServices: number;
    clusters: AlertCluster[];
    clusterSummary: ClusterSummary;
    inefficientRules: InefficientRule[];
    optimizationSuggestions: OptimizationSuggestion[];
    evaluationResults: RuleOptimizationResult[];
    overallSummary: OverallStatistics & {
      optimization: OptimizationSummary;
      evaluation: OverallEvaluation;
      generatedAt: string;
    };
  }> => {
    const response = await api.get('/analysis/report', { params });
    return response.data;
  },
};

export const metricsApi = {
  getMetrics: async (
    metricName: string,
    params?: { service?: string; durationHours?: number }
  ): Promise<{ metricName: string; values: Array<{ time: number; value: number }> }> => {
    const response = await api.get(`/metrics/${metricName}`, { params });
    return response.data;
  },
};

export default api;
