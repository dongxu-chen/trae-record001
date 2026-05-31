import type {
  DetectRequest,
  DetectResponse,
  BatchDetectRequest,
  Anomaly,
  Alert,
  CorrelationResult,
  TimeSeries,
  RootCauseResult,
  Prediction,
  InjectionResult,
  DrillSummary,
} from '../types';

const BASE_URL = '/api';

async function fetchAPI<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE_URL + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function detectAnomalies(req: DetectRequest): Promise<{
  anomalies: Anomaly[];
  clusters: any[];
  count: number;
}> {
  return fetchAPI('/detect', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function batchDetect(req: BatchDetectRequest): Promise<DetectResponse> {
  return fetchAPI('/detect/batch', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function correlateMetrics(req: BatchDetectRequest): Promise<{
  correlations: CorrelationResult[];
}> {
  return fetchAPI('/correlate', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function getAlerts(showSuppressed = false): Promise<{
  alerts: Alert[];
  count: number;
}> {
  const query = showSuppressed ? '?suppressed=true' : '';
  return fetchAPI(`/alerts${query}`);
}

export async function acknowledgeAlert(alertId: string): Promise<{ status: string }> {
  return fetchAPI('/alerts/acknowledge', {
    method: 'POST',
    body: JSON.stringify({ alert_id: alertId }),
  });
}

export async function queryMetrics(query: string, start?: string, end?: string, step?: string): Promise<{
  series: TimeSeries[];
}> {
  const params = new URLSearchParams({ query });
  if (start) params.set('start', start);
  if (end) params.set('end', end);
  if (step) params.set('step', step);
  return fetchAPI(`/metrics/query?${params}`);
}

export async function demoDetect(): Promise<DetectResponse> {
  return fetchAPI('/demo/detect');
}

export async function demoGetSeries(): Promise<{
  series: TimeSeries[];
}> {
  return fetchAPI('/demo/series');
}

export async function demoGenerate(): Promise<{ status: string }> {
  return fetchAPI('/demo/generate');
}

export async function demoDrill(): Promise<{
  results: InjectionResult[];
  summary: DrillSummary;
  total_tests: number;
}> {
  return fetchAPI('/demo/drill');
}

export async function demoPredict(): Promise<{
  predictions: Prediction[];
  count: number;
  horizon: string;
}> {
  return fetchAPI('/demo/predict');
}
