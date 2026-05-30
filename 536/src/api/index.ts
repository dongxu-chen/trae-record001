import type {
  GlobalTransaction,
  BranchTransaction,
  TransactionEvent,
  AlertRecord,
  AlertRule,
  DiagnosisReport,
  TraceSpan,
  TraceDag,
  TransactionStats,
  TransactionMode,
  TransactionStatus,
  PageResponse,
  CompensationRecommendation,
  PressureTestConfig,
  PressureTestResult,
} from '@/types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function postJSON<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function putJSON<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function deleteJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as T;
}

export const api = {
  transactions: {
    search: (params: {
      mode?: TransactionMode;
      status?: TransactionStatus;
      applicationId?: string;
      trafficColor?: string;
      businessType?: string;
      startTime?: string;
      endTime?: string;
      page?: number;
      size?: number;
    }) => {
      const query = new URLSearchParams();
      if (params.mode) query.set('mode', params.mode);
      if (params.status) query.set('status', params.status);
      if (params.applicationId) query.set('applicationId', params.applicationId);
      if (params.trafficColor) query.set('trafficColor', params.trafficColor);
      if (params.businessType) query.set('businessType', params.businessType);
      if (params.startTime) query.set('startTime', params.startTime);
      if (params.endTime) query.set('endTime', params.endTime);
      if (params.page !== undefined) query.set('page', String(params.page));
      if (params.size !== undefined) query.set('size', String(params.size));
      return fetchJSON<PageResponse<GlobalTransaction>>(`/transactions?${query.toString()}`);
    },
    getById: (xid: string) => fetchJSON<GlobalTransaction>(`/transactions/${encodeURIComponent(xid)}`),
    getBranches: (xid: string) => fetchJSON<BranchTransaction[]>(`/transactions/${encodeURIComponent(xid)}/branches`),
    getEvents: (xid: string) => fetchJSON<TransactionEvent[]>(`/transactions/${encodeURIComponent(xid)}/events`),
    getStats: () => fetchJSON<TransactionStats>('/transactions/stats'),
    getTrafficColors: () => fetchJSON<string[]>('/transactions/traffic-colors'),
    getBusinessTypes: () => fetchJSON<string[]>('/transactions/business-types'),
    updateTrafficInfo: (xid: string, data: { trafficColor?: string; businessType?: string; tags?: Record<string, string> }) =>
      putJSON<GlobalTransaction>(`/transactions/${encodeURIComponent(xid)}/traffic-info`, data),
  },
  compensation: {
    getRecommendation: (xid: string) => fetchJSON<CompensationRecommendation>(`/compensation/${encodeURIComponent(xid)}`),
    executeStrategy: (xid: string, strategyType: string) => postJSON<{ success: boolean; message: string }>(`/compensation/${encodeURIComponent(xid)}/execute?strategyType=${strategyType}`),
  },
  pressureTest: {
    list: () => fetchJSON<PressureTestResult[]>('/pressure-test'),
    get: (testId: string) => fetchJSON<PressureTestResult>(`/pressure-test/${encodeURIComponent(testId)}`),
    start: (config: PressureTestConfig) => postJSON<PressureTestResult>('/pressure-test/start', config),
    stop: (testId: string) => postJSON<PressureTestResult>(`/pressure-test/${encodeURIComponent(testId)}/stop`),
  },
  alerts: {
    getUnacknowledged: (page = 0, size = 20) =>
      fetchJSON<PageResponse<AlertRecord>>(`/alerts?page=${page}&size=${size}`),
    getByXid: (xid: string, page = 0, size = 20) =>
      fetchJSON<PageResponse<AlertRecord>>(`/alerts/transaction/${encodeURIComponent(xid)}?page=${page}&size=${size}`),
    countUnacknowledged: () => fetchJSON<number>('/alerts/count'),
    acknowledge: (id: number, acknowledgedBy: string) =>
      putJSON<AlertRecord>(`/alerts/${id}/acknowledge?acknowledgedBy=${encodeURIComponent(acknowledgedBy)}`),
  },
  alertRules: {
    getAll: () => fetchJSON<AlertRule[]>('/alert-rules'),
    add: (rule: AlertRule) => postJSON<void>('/alert-rules', rule),
    remove: (ruleName: string) => deleteJSON<void>(`/alert-rules/${encodeURIComponent(ruleName)}`),
    updateTimeoutThreshold: (thresholdMs: number) =>
      putJSON<void>(`/alert-rules/timeout-threshold?thresholdMs=${thresholdMs}`),
  },
  diagnosis: {
    diagnose: (xid: string) => postJSON<DiagnosisReport>(`/diagnosis/${encodeURIComponent(xid)}`),
  },
  trace: {
    getSpans: (traceId: string) => fetchJSON<TraceSpan[]>(`/trace/${encodeURIComponent(traceId)}/spans`),
    getDag: (traceId: string) => fetchJSON<TraceDag>(`/trace/${encodeURIComponent(traceId)}/dag`),
  },
};
