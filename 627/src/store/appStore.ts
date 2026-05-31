import { create } from 'zustand';
import type {
  DataQualityRule,
  ScheduledTask,
  TaskExecution,
  QualityIssue,
  OverviewStats,
  TrendDataPoint,
  TrendDataWithThreshold,
  HealthScore,
  AutoFixPreview,
  BoardMetrics,
} from '../../shared/types.js';
import { rulesApi, tasksApi, issuesApi, statsApi, healthApi, autofixApi } from '@/lib/api';

interface AppState {
  rules: DataQualityRule[];
  tasks: ScheduledTask[];
  executions: TaskExecution[];
  issues: QualityIssue[];
  overviewStats: OverviewStats | null;
  qualityTrend: TrendDataPoint[];
  issuesTrend: TrendDataPoint[];
  qualityTrendWithThreshold: TrendDataWithThreshold[];
  issuesTrendWithThreshold: TrendDataWithThreshold[];
  healthScore: HealthScore | null;
  autoFixPreview: AutoFixPreview | null;
  boardMetrics: BoardMetrics | null;
  loading: boolean;
  error: string | null;

  fetchRules: () => Promise<void>;
  fetchTasks: () => Promise<void>;
  fetchExecutions: () => Promise<void>;
  fetchIssues: (status?: string) => Promise<void>;
  fetchOverviewStats: () => Promise<void>;
  fetchQualityTrend: (days?: number) => Promise<void>;
  fetchIssuesTrend: (days?: number) => Promise<void>;
  fetchQualityTrendWithThreshold: (days?: number) => Promise<void>;
  fetchIssuesTrendWithThreshold: (days?: number) => Promise<void>;
  fetchHealthScore: () => Promise<void>;
  fetchAutoFixPreview: () => Promise<void>;
  executeAutoFix: (issueIds: string[]) => Promise<number>;
  fetchBoardMetrics: () => Promise<void>;
  fetchAll: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  rules: [],
  tasks: [],
  executions: [],
  issues: [],
  overviewStats: null,
  qualityTrend: [],
  issuesTrend: [],
  qualityTrendWithThreshold: [],
  issuesTrendWithThreshold: [],
  healthScore: null,
  autoFixPreview: null,
  boardMetrics: null,
  loading: false,
  error: null,

  fetchRules: async () => {
    set({ loading: true, error: null });
    try {
      const rules = await rulesApi.getAll();
      set({ rules });
    } catch (error) {
      set({ error: 'Failed to fetch rules' });
    } finally {
      set({ loading: false });
    }
  },

  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const tasks = await tasksApi.getAll();
      set({ tasks });
    } catch (error) {
      set({ error: 'Failed to fetch tasks' });
    } finally {
      set({ loading: false });
    }
  },

  fetchExecutions: async () => {
    set({ loading: true, error: null });
    try {
      const executions = await tasksApi.getExecutions();
      set({ executions });
    } catch (error) {
      set({ error: 'Failed to fetch executions' });
    } finally {
      set({ loading: false });
    }
  },

  fetchIssues: async (status?: string) => {
    set({ loading: true, error: null });
    try {
      const issues = await issuesApi.getAll(status);
      set({ issues });
    } catch (error) {
      set({ error: 'Failed to fetch issues' });
    } finally {
      set({ loading: false });
    }
  },

  fetchOverviewStats: async () => {
    set({ loading: true, error: null });
    try {
      const stats = await statsApi.getOverview();
      set({ overviewStats: stats });
    } catch (error) {
      set({ error: 'Failed to fetch overview stats' });
    } finally {
      set({ loading: false });
    }
  },

  fetchQualityTrend: async (days = 7) => {
    set({ loading: true, error: null });
    try {
      const trend = await statsApi.getQualityTrend(days);
      set({ qualityTrend: trend });
    } catch (error) {
      set({ error: 'Failed to fetch quality trend' });
    } finally {
      set({ loading: false });
    }
  },

  fetchIssuesTrend: async (days = 7) => {
    set({ loading: true, error: null });
    try {
      const trend = await statsApi.getIssuesTrend(days);
      set({ issuesTrend: trend });
    } catch (error) {
      set({ error: 'Failed to fetch issues trend' });
    } finally {
      set({ loading: false });
    }
  },

  fetchQualityTrendWithThreshold: async (days = 7) => {
    set({ loading: true, error: null });
    try {
      const trend = await statsApi.getQualityTrendWithThreshold(days);
      set({ qualityTrendWithThreshold: trend });
    } catch (error) {
      set({ error: 'Failed to fetch quality trend with threshold' });
    } finally {
      set({ loading: false });
    }
  },

  fetchIssuesTrendWithThreshold: async (days = 7) => {
    set({ loading: true, error: null });
    try {
      const trend = await statsApi.getIssuesTrendWithThreshold(days);
      set({ issuesTrendWithThreshold: trend });
    } catch (error) {
      set({ error: 'Failed to fetch issues trend with threshold' });
    } finally {
      set({ loading: false });
    }
  },

  fetchHealthScore: async () => {
    set({ loading: true, error: null });
    try {
      const healthScore = await healthApi.getScore();
      set({ healthScore });
    } catch (error) {
      set({ error: 'Failed to fetch health score' });
    } finally {
      set({ loading: false });
    }
  },

  fetchAutoFixPreview: async () => {
    set({ loading: true, error: null });
    try {
      const autoFixPreview = await autofixApi.preview();
      set({ autoFixPreview });
    } catch (error) {
      set({ error: 'Failed to fetch auto-fix preview' });
    } finally {
      set({ loading: false });
    }
  },

  executeAutoFix: async (issueIds: string[]) => {
    set({ loading: true, error: null });
    try {
      const result = await autofixApi.execute(issueIds);
      return result.fixedCount;
    } catch (error) {
      set({ error: 'Failed to execute auto-fix' });
      return 0;
    } finally {
      set({ loading: false });
    }
  },

  fetchBoardMetrics: async () => {
    try {
      const boardMetrics = await statsApi.getBoard();
      set({ boardMetrics });
    } catch (error) {
      set({ error: 'Failed to fetch board metrics' });
    }
  },

  fetchAll: async () => {
    set({ loading: true, error: null });
    try {
      const [rules, tasks, executions, issues, stats, qualityTrend, issuesTrend, qualityTrendWithThreshold, issuesTrendWithThreshold, healthScore] = await Promise.all([
        rulesApi.getAll(),
        tasksApi.getAll(),
        tasksApi.getExecutions(),
        issuesApi.getAll(),
        statsApi.getOverview(),
        statsApi.getQualityTrend(7),
        statsApi.getIssuesTrend(7),
        statsApi.getQualityTrendWithThreshold(7),
        statsApi.getIssuesTrendWithThreshold(7),
        healthApi.getScore(),
      ]);
      set({ rules, tasks, executions, issues, overviewStats: stats, qualityTrend, issuesTrend, qualityTrendWithThreshold, issuesTrendWithThreshold, healthScore });
    } catch (error) {
      set({ error: 'Failed to fetch data' });
    } finally {
      set({ loading: false });
    }
  },
}));
