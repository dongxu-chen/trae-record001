import type {
  DashboardOverview,
  MetricsTrendPoint,
  AnomalyHeatmapPoint,
  Alert,
  Rule,
  RuleTemplate,
  TableScore,
  TableScoreDetail,
  LineageNode,
  LineageEdge,
  ImpactAnalysis,
  DynamicThreshold,
  FieldImportance,
  ScoreWeightConfig,
  SqlParseLog,
  SqlParseRequest,
  SqlParseResult,
  AnomalySample,
  AnomalySampleRecord,
  QualityForecast,
  ForecastPoint,
} from '@/types'

const BASE = '/api'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  dashboard: {
    overview: () => fetchJSON<DashboardOverview>('/dashboard/overview'),
    metricsTrend: (params: { tableId?: string; metricType: string; days: number }) => {
      const q = new URLSearchParams()
      if (params.tableId) q.set('tableId', params.tableId)
      q.set('metricType', params.metricType)
      q.set('days', String(params.days))
      return fetchJSON<MetricsTrendPoint[]>(`/dashboard/metrics-trend?${q}`)
    },
    anomalyHeatmap: () => fetchJSON<AnomalyHeatmapPoint[]>('/dashboard/anomaly-heatmap'),
    recentAlerts: (limit = 10) => fetchJSON<Alert[]>(`/dashboard/recent-alerts?limit=${limit}`),
  },
  rules: {
    list: () => fetchJSON<Rule[]>('/rules'),
    get: (id: string) => fetchJSON<Rule>(`/rules/${id}`),
    create: (data: Partial<Rule>) => fetchJSON<Rule>('/rules', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: Partial<Rule>) => fetchJSON<Rule>(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => fetchJSON<void>(`/rules/${id}`, { method: 'DELETE' }),
    toggle: (id: string, enabled: boolean) => fetchJSON<Rule>(`/rules/${id}/toggle`, { method: 'PATCH', body: JSON.stringify({ enabled }) }),
    templates: () => fetchJSON<RuleTemplate[]>('/rules/templates'),
    dynamicThreshold: (params: { tableId: string; metricType: string; fieldImportance: string }) => {
      const q = new URLSearchParams()
      q.set('tableId', params.tableId)
      q.set('metricType', params.metricType)
      q.set('fieldImportance', params.fieldImportance)
      return fetchJSON<DynamicThreshold>(`/rules/dynamic-threshold?${q}`)
    },
    fieldImportance: (tableId: string) => fetchJSON<FieldImportance[]>(`/rules/field-importance/${tableId}`),
    updateFieldImportance: (tableId: string, fields: { field_name: string; importance: string }[]) =>
      fetchJSON<void>(`/rules/field-importance/${tableId}`, { method: 'PUT', body: JSON.stringify({ fields }) }),
  },
  scores: {
    list: () => fetchJSON<TableScore[]>('/scores'),
    get: (tableId: string) => fetchJSON<TableScoreDetail>(`/scores/${tableId}`),
    getWeights: (tableId: string) => fetchJSON<ScoreWeightConfig>(`/scores/weights/${tableId}`),
    updateWeights: (tableId: string, weights: ScoreWeightConfig) =>
      fetchJSON<ScoreWeightConfig>(`/scores/weights/${tableId}`, { method: 'PUT', body: JSON.stringify(weights) }),
  },
  alerts: {
    list: (params?: { severity?: string; status?: string; page?: number; pageSize?: number }) => {
      const q = new URLSearchParams()
      if (params?.severity) q.set('severity', params.severity)
      if (params?.status) q.set('status', params.status)
      if (params?.page) q.set('page', String(params.page))
      if (params?.pageSize) q.set('pageSize', String(params.pageSize))
      return fetchJSON<{ items: Alert[]; total: number }>(`/alerts?${q}`)
    },
    get: (id: string) => fetchJSON<Alert>(`/alerts/${id}`),
    acknowledge: (id: string) => fetchJSON<Alert>(`/alerts/${id}/acknowledge`, { method: 'PATCH', body: JSON.stringify({ acknowledgedBy: 'current_user' }) }),
    resolve: (id: string, resolution: string) => fetchJSON<Alert>(`/alerts/${id}/resolve`, { method: 'PATCH', body: JSON.stringify({ resolvedBy: 'current_user', resolution }) }),
  },
  impact: {
    lineage: () => fetchJSON<{ nodes: LineageNode[]; edges: LineageEdge[] }>('/impact/lineage'),
    analyze: (tableId: string) => fetchJSON<ImpactAnalysis>(`/impact/analyze/${tableId}`),
  },
  lineage: {
    parseSql: (data: SqlParseRequest) => fetchJSON<SqlParseResult>('/lineage/parse-sql', { method: 'POST', body: JSON.stringify(data) }),
    getParseLog: () => fetchJSON<SqlParseLog[]>('/lineage/parse-log'),
    autoDiscover: () => fetchJSON<{ discovered: number }>('/lineage/auto-discover', { method: 'POST' }),
  },
  samples: {
    getByAlert: (alertId: string) => fetchJSON<AnomalySample[]>(`/samples/alert/${alertId}`),
    getByTable: (tableId: string, metricType?: string) => {
      const q = new URLSearchParams()
      if (metricType) q.set('metricType', metricType)
      const query = q.toString()
      return fetchJSON<AnomalySample[]>(`/samples/table/${tableId}${query ? `?${query}` : ''}`)
    },
    generate: (data: { alert_id?: string; table_id: string; metric_type: string; sample_count?: number }) =>
      fetchJSON<AnomalySample>('/samples/generate', { method: 'POST', body: JSON.stringify(data) }),
    generateForActiveAlerts: () => fetchJSON<{ generated: number }>('/samples/generate-for-active-alerts', { method: 'POST' }),
  },
  forecast: {
    overview: () => fetchJSON<QualityForecast>('/forecast/overview'),
    timeseries: (horizon?: number, includeHistory?: boolean) => {
      const q = new URLSearchParams()
      if (horizon !== undefined) q.set('horizon', String(horizon))
      if (includeHistory !== undefined) q.set('includeHistory', String(includeHistory))
      const query = q.toString()
      return fetchJSON<ForecastPoint[]>(`/forecast/timeseries${query ? `?${query}` : ''}`)
    },
    generate: (horizonDays?: number) =>
      fetchJSON<QualityForecast>('/forecast/generate', { method: 'POST', body: JSON.stringify({ horizonDays }) }),
    byTable: (horizon?: number) => {
      const q = new URLSearchParams()
      if (horizon !== undefined) q.set('horizon', String(horizon))
      const query = q.toString()
      return fetchJSON<Record<string, number>>(`/forecast/alerts-by-table${query ? `?${query}` : ''}`)
    },
  },
}
