import { create } from 'zustand';
import type { ThresholdRule, AlertRecord, MetricData, AlertHistoryQuery, ThresholdRecommendation, MetricCorrelation, AlertFeedback, FeedbackStats } from '@/types';
import * as api from '@/utils/api';

interface AlertStore {
  rules: ThresholdRule[];
  alerts: AlertRecord[];
  alertsTotal: number;
  alertsPage: number;
  alertsPageSize: number;
  realtimeAlerts: AlertRecord[];
  metrics: Record<string, MetricData[]>;
  wsConnected: boolean;
  alertPanelOpen: boolean;
  activeAlertMetric: string | null;
  thresholdRecommendations: ThresholdRecommendation | null;
  correlations: Record<string, MetricCorrelation[]>;
  feedbacks: Record<string, AlertFeedback[]>;
  feedbackStats: Record<string, FeedbackStats>;

  setRules: (rules: ThresholdRule[]) => void;
  addRule: (rule: ThresholdRule) => void;
  updateRule: (rule: ThresholdRule) => void;
  deleteRule: (id: string) => void;

  setAlerts: (alerts: AlertRecord[], total: number, page: number, pageSize: number) => void;

  addRealtimeAlert: (alert: AlertRecord) => void;
  clearRealtimeAlerts: () => void;

  addMetricData: (data: MetricData) => void;

  setWsConnected: (connected: boolean) => void;
  setAlertPanelOpen: (open: boolean) => void;
  setActiveAlertMetric: (metric: string | null) => void;

  fetchRules: () => Promise<void>;
  fetchAlerts: (query: AlertHistoryQuery) => Promise<void>;
  createRule: (rule: Omit<ThresholdRule, 'id' | 'createdAt' | 'updatedAt'>) => Promise<ThresholdRule>;
  updateRuleApi: (id: string, rule: Partial<ThresholdRule>) => Promise<ThresholdRule>;
  deleteRuleApi: (id: string) => Promise<void>;
  acknowledgeAlert: (id: string) => Promise<void>;
  fetchSmartThreshold: (metric: string, method: 'zscore' | 'percentile' | 'iqr', sensitivity: 'low' | 'medium' | 'high') => Promise<ThresholdRecommendation>;
  fetchRelatedMetrics: (metric: string) => Promise<MetricCorrelation[]>;
  submitFeedback: (alertId: string, type: 'false_positive' | 'true_positive' | 'needs_adjustment', comment?: string) => Promise<void>;
  fetchFeedbackStats: (ruleId: string) => Promise<FeedbackStats>;
}

const MAX_REALTIME_ALERTS = 50;
const MAX_METRIC_POINTS = 30;

export const useAlertStore = create<AlertStore>((set, get) => ({
  rules: [],
  alerts: [],
  alertsTotal: 0,
  alertsPage: 1,
  alertsPageSize: 20,
  realtimeAlerts: [],
  metrics: {},
  wsConnected: false,
  alertPanelOpen: false,
  activeAlertMetric: null,
  thresholdRecommendations: null,
  correlations: {},
  feedbacks: {},
  feedbackStats: {},

  setRules: (rules) => set({ rules }),

  addRule: (rule) => set((s) => ({ rules: [...s.rules, rule] })),

  updateRule: (rule) => set((s) => ({
    rules: s.rules.map(r => r.id === rule.id ? rule : r),
  })),

  deleteRule: (id) => set((s) => ({
    rules: s.rules.filter(r => r.id !== id),
  })),

  setAlerts: (alerts, total, page, pageSize) => set({
    alerts, alertsTotal: total, alertsPage: page, alertsPageSize: pageSize,
  }),

  addRealtimeAlert: (alert) => set((s) => ({
    realtimeAlerts: [alert, ...s.realtimeAlerts].slice(0, MAX_REALTIME_ALERTS),
  })),

  clearRealtimeAlerts: () => set({ realtimeAlerts: [] }),

  addMetricData: (data) => set((s) => {
    const existing = s.metrics[data.metric] || [];
    const updated = [...existing, data].slice(-MAX_METRIC_POINTS);
    return { metrics: { ...s.metrics, [data.metric]: updated } };
  }),

  setWsConnected: (connected) => set({ wsConnected: connected }),
  setAlertPanelOpen: (open) => set({ alertPanelOpen: open }),
  setActiveAlertMetric: (metric) => set({ activeAlertMetric: metric }),

  fetchRules: async () => {
    const rules = await api.fetchRules();
    set({ rules });
  },

  fetchAlerts: async (query) => {
    const result = await api.fetchAlerts(query);
    set({
      alerts: result.items,
      alertsTotal: result.total,
      alertsPage: result.page,
      alertsPageSize: result.pageSize,
    });
  },

  createRule: async (rule) => {
    const created = await api.createRule(rule);
    set((s) => ({ rules: [...s.rules, created] }));
    return created;
  },

  updateRuleApi: async (id, rule) => {
    const updated = await api.updateRule(id, rule);
    set((s) => ({ rules: s.rules.map(r => r.id === id ? updated : r) }));
    return updated;
  },

  deleteRuleApi: async (id) => {
    await api.deleteRule(id);
    set((s) => ({ rules: s.rules.filter(r => r.id !== id) }));
  },

  acknowledgeAlert: async (id) => {
    await api.acknowledgeAlert(id);
    set((s) => ({
      alerts: s.alerts.map(a => a.id === id ? { ...a, acknowledged: true } : a),
      realtimeAlerts: s.realtimeAlerts.map(a => a.id === id ? { ...a, acknowledged: true } : a),
    }));
  },

  fetchSmartThreshold: async (metric, method, sensitivity) => {
    const recommendation = await api.fetchSmartThreshold(metric, method, sensitivity);
    set({ thresholdRecommendations: recommendation });
    return recommendation;
  },

  fetchRelatedMetrics: async (metric) => {
    const correlations = await api.fetchRelatedMetrics(metric);
    set((s) => ({ correlations: { ...s.correlations, [metric]: correlations } }));
    return correlations;
  },

  submitFeedback: async (alertId, type, comment) => {
    await api.submitAlertFeedback(alertId, type, comment);
    set((s) => {
      const alert = s.alerts.find(a => a.id === alertId);
      const realtimeAlert = s.realtimeAlerts.find(a => a.id === alertId);
      return {
        alerts: s.alerts.map(a => a.id === alertId ? { ...a, feedbackType: type, hasFeedback: true } : a),
        realtimeAlerts: s.realtimeAlerts.map(a => a.id === alertId ? { ...a, feedbackType: type, hasFeedback: true } : a),
      };
    });
  },

  fetchFeedbackStats: async (ruleId) => {
    const stats = await api.fetchFeedbackStats(ruleId);
    set((s) => ({ feedbackStats: { ...s.feedbackStats, [ruleId]: stats } }));
    return stats;
  },
}));
