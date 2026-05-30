import { create } from 'zustand'
import type { DashboardOverview, Alert, Rule, TableScore, LineageNode, LineageEdge, ImpactAnalysis, FieldImportance, DynamicThreshold, ScoreWeightConfig, SqlParseLog, AnomalySample, QualityForecast, ForecastPoint, SqlParseRequest } from '@/types'
import { api } from '@/utils/api'

interface AppState {
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  dashboardOverview: DashboardOverview | null
  dashboardLoading: boolean
  fetchDashboardOverview: () => Promise<void>

  recentAlerts: Alert[]
  fetchRecentAlerts: (limit?: number) => Promise<void>

  rules: Rule[]
  rulesLoading: boolean
  fetchRules: () => Promise<void>
  toggleRule: (id: string, enabled: boolean) => Promise<void>
  deleteRule: (id: string) => Promise<void>

  scores: TableScore[]
  scoresLoading: boolean
  fetchScores: () => Promise<void>

  alerts: Alert[]
  alertsTotal: number
  alertsLoading: boolean
  alertsPage: number
  alertsSeverity: string
  alertsStatus: string
  fetchAlerts: () => Promise<void>
  setAlertsPage: (page: number) => void
  setAlertsFilter: (severity: string, status: string) => void
  acknowledgeAlert: (id: string) => Promise<void>
  resolveAlert: (id: string, resolution: string) => Promise<void>

  lineageNodes: LineageNode[]
  lineageEdges: LineageEdge[]
  lineageLoading: boolean
  selectedTableId: string | null
  impactAnalysis: ImpactAnalysis | null
  fetchLineage: () => Promise<void>
  selectTable: (tableId: string | null) => Promise<void>

  fieldImportanceMap: Record<string, FieldImportance[]>
  fetchFieldImportance: (tableId: string) => Promise<void>

  dynamicThreshold: DynamicThreshold | null
  fetchDynamicThreshold: (tableId: string, metricType: string, importance: string) => Promise<void>

  weightConfigs: Record<string, ScoreWeightConfig>
  fetchWeightConfig: (tableId: string) => Promise<void>
  updateWeightConfig: (tableId: string, weights: ScoreWeightConfig) => Promise<void>

  parseLogs: SqlParseLog[]
  parseLogsLoading: boolean
  fetchParseLogs: () => Promise<void>
  parseSql: (data: SqlParseRequest) => Promise<void>
  autoDiscoverLineage: () => Promise<void>

  anomalySamples: Record<string, AnomalySample[]>
  fetchSamplesByAlert: (alertId: string) => Promise<void>
  fetchSamplesByTable: (tableId: string, metricType?: string) => Promise<void>
  generateSamples: (data: any) => Promise<void>
  generateSamplesForActiveAlerts: () => Promise<void>

  forecastOverview: QualityForecast | null
  forecastTimeseries: ForecastPoint[]
  forecastLoading: boolean
  fetchForecastOverview: () => Promise<void>
  fetchForecastTimeseries: (horizon?: number) => Promise<void>
  generateForecast: (horizonDays?: number) => Promise<void>
}

export const useStore = create<AppState>((set, get) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set(s => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  dashboardOverview: null,
  dashboardLoading: false,
  fetchDashboardOverview: async () => {
    set({ dashboardLoading: true })
    try {
      const data = await api.dashboard.overview()
      set({ dashboardOverview: data, dashboardLoading: false })
    } catch {
      set({ dashboardLoading: false })
    }
  },

  recentAlerts: [],
  fetchRecentAlerts: async (limit = 10) => {
    try {
      const data = await api.dashboard.recentAlerts(limit)
      set({ recentAlerts: data })
    } catch { /* ignore */ }
  },

  rules: [],
  rulesLoading: false,
  fetchRules: async () => {
    set({ rulesLoading: true })
    try {
      const data = await api.rules.list()
      set({ rules: data, rulesLoading: false })
    } catch {
      set({ rulesLoading: false })
    }
  },
  toggleRule: async (id, enabled) => {
    await api.rules.toggle(id, enabled)
    set(s => ({ rules: s.rules.map(r => r.id === id ? { ...r, enabled } : r) }))
  },
  deleteRule: async (id) => {
    await api.rules.delete(id)
    set(s => ({ rules: s.rules.filter(r => r.id !== id) }))
  },

  scores: [],
  scoresLoading: false,
  fetchScores: async () => {
    set({ scoresLoading: true })
    try {
      const data = await api.scores.list()
      set({ scores: data, scoresLoading: false })
    } catch {
      set({ scoresLoading: false })
    }
  },

  alerts: [],
  alertsTotal: 0,
  alertsLoading: false,
  alertsPage: 1,
  alertsSeverity: '',
  alertsStatus: '',
  fetchAlerts: async () => {
    set({ alertsLoading: true })
    const { alertsPage, alertsSeverity, alertsStatus } = get()
    try {
      const data = await api.alerts.list({
        page: alertsPage,
        pageSize: 10,
        severity: alertsSeverity || undefined,
        status: alertsStatus || undefined,
      })
      set({ alerts: data.items, alertsTotal: data.total, alertsLoading: false })
    } catch {
      set({ alertsLoading: false })
    }
  },
  setAlertsPage: (page) => { set({ alertsPage: page }); get().fetchAlerts() },
  setAlertsFilter: (severity, status) => { set({ alertsSeverity: severity, alertsStatus: status, alertsPage: 1 }); get().fetchAlerts() },
  acknowledgeAlert: async (id) => {
    await api.alerts.acknowledge(id)
    get().fetchAlerts()
  },
  resolveAlert: async (id, resolution) => {
    await api.alerts.resolve(id, resolution)
    get().fetchAlerts()
  },

  lineageNodes: [],
  lineageEdges: [],
  lineageLoading: false,
  selectedTableId: null,
  impactAnalysis: null,
  fetchLineage: async () => {
    set({ lineageLoading: true })
    try {
      const data = await api.impact.lineage()
      set({ lineageNodes: data.nodes, lineageEdges: data.edges, lineageLoading: false })
    } catch {
      set({ lineageLoading: false })
    }
  },
  selectTable: async (tableId) => {
    set({ selectedTableId: tableId })
    if (tableId) {
      try {
        const data = await api.impact.analyze(tableId)
        set({ impactAnalysis: data })
      } catch { /* ignore */ }
    } else {
      set({ impactAnalysis: null })
    }
  },

  fieldImportanceMap: {},
  fetchFieldImportance: async (tableId) => {
    try {
      const data = await api.rules.fieldImportance(tableId)
      set(s => ({ fieldImportanceMap: { ...s.fieldImportanceMap, [tableId]: data } }))
    } catch { /* ignore */ }
  },

  dynamicThreshold: null,
  fetchDynamicThreshold: async (tableId, metricType, importance) => {
    try {
      const data = await api.rules.dynamicThreshold({ tableId, metricType, fieldImportance: importance })
      set({ dynamicThreshold: data })
    } catch { /* ignore */ }
  },

  weightConfigs: {},
  fetchWeightConfig: async (tableId) => {
    try {
      const data = await api.scores.getWeights(tableId)
      set(s => ({ weightConfigs: { ...s.weightConfigs, [tableId]: data } }))
    } catch { /* ignore */ }
  },
  updateWeightConfig: async (tableId, weights) => {
    try {
      const data = await api.scores.updateWeights(tableId, weights)
      set(s => ({ weightConfigs: { ...s.weightConfigs, [tableId]: data } }))
    } catch { /* ignore */ }
  },

  parseLogs: [],
  parseLogsLoading: false,
  fetchParseLogs: async () => {
    set({ parseLogsLoading: true })
    try {
      const data = await api.lineage.getParseLog()
      set({ parseLogs: data, parseLogsLoading: false })
    } catch {
      set({ parseLogsLoading: false })
    }
  },
  parseSql: async (data) => {
    try {
      await api.lineage.parseSql(data)
      get().fetchParseLogs()
    } catch { /* ignore */ }
  },
  autoDiscoverLineage: async () => {
    try {
      await api.lineage.autoDiscover()
      get().fetchParseLogs()
    } catch { /* ignore */ }
  },

  anomalySamples: {},
  fetchSamplesByAlert: async (alertId) => {
    try {
      const data = await api.samples.getByAlert(alertId)
      set(s => ({ anomalySamples: { ...s.anomalySamples, [alertId]: data } }))
    } catch { /* ignore */ }
  },
  fetchSamplesByTable: async (tableId, metricType) => {
    try {
      const data = await api.samples.getByTable(tableId, metricType)
      const key = metricType ? `${tableId}_${metricType}` : tableId
      set(s => ({ anomalySamples: { ...s.anomalySamples, [key]: data } }))
    } catch { /* ignore */ }
  },
  generateSamples: async (data) => {
    try {
      await api.samples.generate(data)
      if (data.alert_id) {
        get().fetchSamplesByAlert(data.alert_id)
      }
      if (data.table_id) {
        get().fetchSamplesByTable(data.table_id, data.metric_type)
      }
    } catch { /* ignore */ }
  },
  generateSamplesForActiveAlerts: async () => {
    try {
      await api.samples.generateForActiveAlerts()
    } catch { /* ignore */ }
  },

  forecastOverview: null,
  forecastTimeseries: [],
  forecastLoading: false,
  fetchForecastOverview: async () => {
    set({ forecastLoading: true })
    try {
      const data = await api.forecast.overview()
      set({ forecastOverview: data, forecastLoading: false })
    } catch {
      set({ forecastLoading: false })
    }
  },
  fetchForecastTimeseries: async (horizon) => {
    try {
      const data = await api.forecast.timeseries(horizon)
      set({ forecastTimeseries: data })
    } catch { /* ignore */ }
  },
  generateForecast: async (horizonDays) => {
    try {
      await api.forecast.generate(horizonDays)
      get().fetchForecastOverview()
      get().fetchForecastTimeseries(horizonDays)
    } catch { /* ignore */ }
  },
}))
