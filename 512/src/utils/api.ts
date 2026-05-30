import type { ThresholdRule, AlertRecord, AlertHistoryQuery, ThresholdRecommendation, MetricCorrelation, FeedbackStats } from '@/types';

const API_BASE = '/api';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || error.error || `API Error: ${res.status}`);
  }
  const json = await res.json();
  if (json.success && json.data !== undefined) return json.data as T;
  if (json.success) return undefined as T;
  return json as T;
}

export async function fetchRules(): Promise<ThresholdRule[]> {
  return apiFetch<ThresholdRule[]>('/rules');
}

export async function createRule(rule: Omit<ThresholdRule, 'id' | 'createdAt' | 'updatedAt'>): Promise<ThresholdRule> {
  return apiFetch<ThresholdRule>('/rules', {
    method: 'POST',
    body: JSON.stringify(rule),
  });
}

export async function updateRule(id: string, rule: Partial<ThresholdRule>): Promise<ThresholdRule> {
  return apiFetch<ThresholdRule>(`/rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(rule),
  });
}

export async function deleteRule(id: string): Promise<void> {
  await apiFetch<void>(`/rules/${id}`, { method: 'DELETE' });
}

export async function fetchAlerts(query: AlertHistoryQuery): Promise<{
  items: AlertRecord[];
  total: number;
  page: number;
  pageSize: number;
}> {
  const params = new URLSearchParams();
  params.set('page', String(query.page));
  params.set('pageSize', String(query.pageSize));
  if (query.level) params.set('level', query.level);
  if (query.metric) params.set('metric', query.metric);
  if (query.startTime) params.set('startTime', query.startTime);
  if (query.endTime) params.set('endTime', query.endTime);
  if (query.acknowledged !== undefined) params.set('acknowledged', String(query.acknowledged));
  const res = await fetch(`${API_BASE}/alerts?${params.toString()}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  const json = await res.json();
  const items: AlertRecord[] = json.data ?? [];
  const pag = json.pagination ?? { total: 0, page: 1, pageSize: 20 };
  return { items, total: pag.total, page: pag.page, pageSize: pag.pageSize };
}

export async function fetchAlertDetail(id: string): Promise<AlertRecord> {
  return apiFetch<AlertRecord>(`/alerts/${id}`);
}

export async function acknowledgeAlert(id: string): Promise<AlertRecord> {
  return apiFetch<AlertRecord>(`/alerts/${id}/acknowledge`, { method: 'PUT' });
}

export async function fetchSmartThreshold(
  metric: string,
  method: 'zscore' | 'percentile' | 'iqr',
  sensitivity: 'low' | 'medium' | 'high'
): Promise<ThresholdRecommendation> {
  const params = new URLSearchParams({ method, sensitivity });
  return apiFetch<ThresholdRecommendation>(`/rules/smart-threshold/${metric}?${params.toString()}`);
}

export async function fetchRelatedMetrics(metric: string): Promise<MetricCorrelation[]> {
  return apiFetch<MetricCorrelation[]>(`/alerts/related/${metric}`);
}

export async function submitAlertFeedback(
  alertId: string,
  type: 'false_positive' | 'true_positive' | 'needs_adjustment',
  comment?: string
): Promise<void> {
  return apiFetch<void>(`/alerts/${alertId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ type, comment }),
  });
}

export async function fetchFeedbackStats(ruleId: string): Promise<FeedbackStats> {
  return apiFetch<FeedbackStats>(`/rules/${ruleId}/feedback-stats`);
}
