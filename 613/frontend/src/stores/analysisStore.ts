import { create } from 'zustand';
import {
  Alert,
  AlertRule,
  AlertCluster,
  InefficientRule,
  OptimizationSuggestion,
  RuleOptimizationResult,
  ClusterSummary,
  OverallStatistics,
  OptimizationSummary,
  OverallEvaluation,
  HealthStatus,
} from '@/types';
import { healthApi, alertsApi, rulesApi, analysisApi } from '@/services/api';

interface AnalysisState {
  alerts: Alert[];
  rules: AlertRule[];
  clusters: AlertCluster[];
  clusterSummary: ClusterSummary | null;
  inefficientRules: InefficientRule[];
  overallStatistics: OverallStatistics | null;
  suggestions: OptimizationSuggestion[];
  optimizationSummary: OptimizationSummary | null;
  evaluationResults: RuleOptimizationResult[];
  overallEvaluation: OverallEvaluation | null;
  healthStatus: HealthStatus | null;

  loading: Record<string, boolean>;
  error: string | null;

  filters: {
    lookbackHours: number;
    minInefficiencyScore: number;
    minConfidence: number;
    selectedServices: string[];
    selectedPriorities: string[];
  };

  fetchHealth: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchRules: () => Promise<void>;
  fetchClusters: () => Promise<void>;
  fetchInefficientRules: () => Promise<void>;
  fetchSuggestions: () => Promise<void>;
  fetchEvaluation: () => Promise<void>;
  fetchFullReport: () => Promise<void>;
  setFilters: (filters: Partial<AnalysisState['filters']>) => void;
  resetFilters: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  alerts: [],
  rules: [],
  clusters: [],
  clusterSummary: null,
  inefficientRules: [],
  overallStatistics: null,
  suggestions: [],
  optimizationSummary: null,
  evaluationResults: [],
  overallEvaluation: null,
  healthStatus: null,

  loading: {},
  error: null,

  filters: {
    lookbackHours: 168,
    minInefficiencyScore: 0.3,
    minConfidence: 0.5,
    selectedServices: [],
    selectedPriorities: [],
  },

  fetchHealth: async () => {
    set({ loading: { ...get().loading, health: true } });
    try {
      const data = await healthApi.check();
      set({ healthStatus: data, error: null });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, health: false } });
    }
  },

  fetchAlerts: async () => {
    set({ loading: { ...get().loading, alerts: true } });
    try {
      const { filters } = get();
      const data = await alertsApi.getAlerts({
        lookbackHours: filters.lookbackHours,
      });
      set({ alerts: data, error: null });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, alerts: false } });
    }
  },

  fetchRules: async () => {
    set({ loading: { ...get().loading, rules: true } });
    try {
      const data = await rulesApi.getRules();
      set({ rules: data, error: null });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, rules: false } });
    }
  },

  fetchClusters: async () => {
    set({ loading: { ...get().loading, clusters: true } });
    try {
      const { filters } = get();
      const data = await alertsApi.getClusters({
        lookbackHours: filters.lookbackHours,
      });
      set({
        clusters: data.clusters,
        clusterSummary: data.summary,
        error: null,
      });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, clusters: false } });
    }
  },

  fetchInefficientRules: async () => {
    set({ loading: { ...get().loading, inefficientRules: true } });
    try {
      const { filters } = get();
      const data = await rulesApi.getInefficientRules({
        lookbackHours: filters.lookbackHours,
        minInefficiencyScore: filters.minInefficiencyScore,
      });
      set({
        inefficientRules: data.inefficientRules,
        overallStatistics: data.statistics,
        error: null,
      });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, inefficientRules: false } });
    }
  },

  fetchSuggestions: async () => {
    set({ loading: { ...get().loading, suggestions: true } });
    try {
      const { filters } = get();
      const data = await rulesApi.getOptimizationSuggestions({
        lookbackHours: filters.lookbackHours,
        minConfidence: filters.minConfidence,
      });
      set({
        suggestions: data.suggestions,
        optimizationSummary: data.summary,
        error: null,
      });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, suggestions: false } });
    }
  },

  fetchEvaluation: async () => {
    set({ loading: { ...get().loading, evaluation: true } });
    try {
      const { filters } = get();
      const data = await rulesApi.evaluateOptimizations({
        lookbackHours: filters.lookbackHours,
      });
      set({
        evaluationResults: data.evaluationResults,
        overallEvaluation: data.overallEvaluation,
        error: null,
      });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, evaluation: false } });
    }
  },

  fetchFullReport: async () => {
    set({ loading: { ...get().loading, fullReport: true } });
    try {
      const { filters } = get();
      const data = await analysisApi.getFullReport({
        lookbackHours: filters.lookbackHours,
      });
      set({
        alerts: [],
        clusters: data.clusters,
        clusterSummary: data.clusterSummary,
        inefficientRules: data.inefficientRules,
        suggestions: data.optimizationSuggestions,
        evaluationResults: data.evaluationResults,
        overallStatistics: data.overallSummary,
        optimizationSummary: data.overallSummary.optimization,
        overallEvaluation: data.overallSummary.evaluation,
        error: null,
      });
    } catch (error: any) {
      set({ error: error.message });
    } finally {
      set({ loading: { ...get().loading, fullReport: false } });
    }
  },

  setFilters: (newFilters) => {
    set({
      filters: { ...get().filters, ...newFilters },
    });
  },

  resetFilters: () => {
    set({
      filters: {
        lookbackHours: 168,
        minInefficiencyScore: 0.3,
        minConfidence: 0.5,
        selectedServices: [],
        selectedPriorities: [],
      },
    });
  },
}));
