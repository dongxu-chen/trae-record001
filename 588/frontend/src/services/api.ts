import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export interface Overview {
  total_nodes: number
  total_size: number
  max_depth: number
  alert_count: number
  timestamp: string
  status: string
}

export interface Alert {
  type: string
  severity: string
  path: string
  message: string
  value: number
  threshold: number
  timestamp: string
}

export interface PathStat {
  path: string
  node_count: number
  total_data_size: number
  max_depth: number
  avg_data_size: number
  ephemeral_count: number
}

export interface DataPoint {
  timestamp: string
  value: number
}

export interface Prediction {
  metric: string
  historical_data: DataPoint[]
  predicted_data: DataPoint[]
  growth_rate: number
  predicted_value_7d: number
  trend: string
  season_type: string
}

export interface Recommendation {
  category: string
  severity: string
  title: string
  message: string
  action: string
  solutions?: string[]
  scripts?: string[]
  affected_paths?: string[]
  affected_nodes?: string[]
}

export interface TTLInfo {
  path: string
  ttl_seconds: number
  expire_at: string
  created_at: string
  auto_delete: boolean
}

export interface TTLStats {
  total_ttl_nodes: number
  auto_delete_count: number
  expired_count: number
  enabled: boolean
  default_ttl_seconds: number
}

export interface NodeHotness {
  path: string
  read_count: number
  write_count: number
  watch_count: number
  total_access: number
  hotness_score: number
  last_access_time: string
  cold_data: boolean
  days_since_access: number
}

export interface HotnessStats {
  total_tracked_nodes: number
  cold_node_count: number
  hot_node_count: number
  cold_threshold_days: number
  hot_threshold_score: number
}

export interface MigrationSuggestion {
  prefix: string
  cold_node_count: number
  total_data_size: number
  avg_cold_days: number
  suggested_action: string
  recommendations: string[]
}

export interface HealthScore {
  overall_score: number
  grade: string
  last_updated: string
  category_scores: Record<string, number>
  recommendations: string[]
  warnings: string[]
}

export const getOverview = async (): Promise<Overview> => {
  const response = await api.get('/overview')
  return response.data
}

export const getAlerts = async (): Promise<Alert[]> => {
  const response = await api.get('/alerts')
  return response.data
}

export const getTopPaths = async (by: string = 'total_size', limit: number = 20): Promise<PathStat[]> => {
  const response = await api.get(`/paths/top?by=${by}&limit=${limit}`)
  return response.data
}

export const getTimeSeries = async (metric: string, duration: string = '24h'): Promise<DataPoint[]> => {
  const response = await api.get(`/timeseries/${metric}?duration=${duration}`)
  return response.data
}

export const getPredictions = async (): Promise<Record<string, Prediction>> => {
  const response = await api.get('/predictions')
  return response.data
}

export const getRecommendations = async (): Promise<Recommendation[]> => {
  const response = await api.get('/recommendations')
  return response.data
}

export const triggerCollection = async (): Promise<any> => {
  const response = await api.post('/collect')
  return response.data
}

export const getTTLStats = async (): Promise<TTLStats> => {
  const response = await api.get('/ttl/stats')
  return response.data
}

export const getTTLNodes = async (): Promise<TTLInfo[]> => {
  const response = await api.get('/ttl/nodes')
  return response.data
}

export const setTTL = async (path: string, ttlSeconds: number, autoDelete: boolean): Promise<any> => {
  const response = await api.post('/ttl/set', { path, ttl_seconds: ttlSeconds, auto_delete: autoDelete })
  return response.data
}

export const removeTTL = async (path: string): Promise<any> => {
  const response = await api.post('/ttl/remove', { path })
  return response.data
}

export const triggerCleanup = async (): Promise<{ deleted: number }> => {
  const response = await api.post('/ttl/cleanup')
  return response.data
}

export const getHotnessStats = async (): Promise<HotnessStats> => {
  const response = await api.get('/hotness/stats')
  return response.data
}

export const getHotNodes = async (limit: number = 20): Promise<NodeHotness[]> => {
  const response = await api.get(`/hotness/hot?limit=${limit}`)
  return response.data
}

export const getColdNodes = async (threshold: number = 0): Promise<NodeHotness[]> => {
  const response = await api.get(`/hotness/cold?threshold=${threshold}`)
  return response.data
}

export const getMigrationSuggestions = async (): Promise<MigrationSuggestion[]> => {
  const response = await api.get('/hotness/migration')
  return response.data
}

export const getHealthScore = async (): Promise<HealthScore> => {
  const response = await api.get('/health/score')
  return response.data
}

export default api
