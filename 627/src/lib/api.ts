import type {
  DataQualityRule,
  RuleTemplate,
  ScheduledTask,
  TaskExecution,
  QualityIssue,
  OverviewStats,
  TrendDataPoint,
  TrendDataWithThreshold,
  RuleExecutionResult,
  HealthScore,
  AutoFixPreview,
  AutoFixResult,
  BoardMetrics,
} from '../../shared/types.js';

const API_BASE = '/api';

let currentUser: { id: string; name: string; role: string } = {
  id: 'user_admin',
  name: '管理员',
  role: 'admin',
};

export function setCurrentUser(user: { id: string; name: string; role: string }) {
  currentUser = user;
}

export function getCurrentUser() {
  return currentUser;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'x-current-user': JSON.stringify(currentUser),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(errorBody || `HTTP error! status: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const rulesApi = {
  getTemplates: () => request<RuleTemplate[]>('/rules/templates'),
  getTables: () => request<string[]>('/rules/tables'),
  getTableColumns: (table: string) => request<string[]>(`/rules/tables/${table}/columns`),
  getAll: () => request<DataQualityRule[]>('/rules'),
  getById: (id: string) => request<DataQualityRule>(`/rules/${id}`),
  create: (data: Omit<DataQualityRule, 'id' | 'createdAt' | 'updatedAt'>) =>
    request<DataQualityRule>('/rules', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<DataQualityRule>) =>
    request<DataQualityRule>(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => request(`/rules/${id}`, { method: 'DELETE' }),
  test: (id: string) => request<RuleExecutionResult>(`/rules/${id}/test`, { method: 'POST' }),
};

export const tasksApi = {
  getAll: () => request<ScheduledTask[]>('/tasks'),
  getExecutions: () => request<TaskExecution[]>('/tasks/executions'),
  create: (data: Omit<ScheduledTask, 'id' | 'createdAt' | 'updatedAt'>) =>
    request<ScheduledTask>('/tasks', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<ScheduledTask>) =>
    request<ScheduledTask>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  run: (id: string) => request(`/tasks/${id}/run`, { method: 'POST' }),
  delete: (id: string) => request(`/tasks/${id}`, { method: 'DELETE' }),
};

export const reportsApi = {
  getAll: () => request<TaskExecution[]>('/reports'),
  getById: (id: string) => request<TaskExecution>(`/reports/${id}`),
};

export const issuesApi = {
  getAll: (status?: string) =>
    request<QualityIssue[]>(status ? `/issues?status=${status}` : '/issues'),
  update: (id: string, data: Partial<QualityIssue>) =>
    request(`/issues/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

export const statsApi = {
  getOverview: () => request<OverviewStats>('/stats/overview'),
  getQualityTrend: (days = 7) => request<TrendDataPoint[]>(`/stats/trends/quality?days=${days}`),
  getIssuesTrend: (days = 7) => request<TrendDataPoint[]>(`/stats/trends/issues?days=${days}`),
  getQualityTrendWithThreshold: (days = 7) => request<TrendDataWithThreshold[]>(`/stats/trends/quality-threshold?days=${days}`),
  getIssuesTrendWithThreshold: (days = 7) => request<TrendDataWithThreshold[]>(`/stats/trends/issues-threshold?days=${days}`),
  getBoard: () => request<BoardMetrics>('/stats/board'),
};

export const healthApi = {
  getScore: () => request<HealthScore>('/health/score'),
};

export const autofixApi = {
  preview: () => request<AutoFixPreview>('/autofix/preview', { method: 'POST' }),
  execute: (issueIds: string[]) => request<{ results: AutoFixResult[]; fixedCount: number }>('/autofix/execute', { method: 'POST', body: JSON.stringify({ issueIds }) }),
};
