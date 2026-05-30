export interface EventImpact {
  factor: number
  active_events: Array<{ id: number; title: string; type: string; factor: number }>
}

export interface ZoneReading {
  zone_id: string
  total_spots: number
  occupied_spots: number
  available_spots: number
  occupancy_rate: number
  timestamp: string
  event_impact?: EventImpact
}

export interface PredictionPoint {
  timestamp: string
  available_spots: number
  confidence: number
  event_impact?: number
}

export interface PredictionResult {
  zone_id: string
  predictions: PredictionPoint[]
  model_type: string
  accuracy_metrics: {
    mae: number
    rmse: number
  }
  active_events: Array<{ id: number; title: string; type: string; factor: number }>
}

export interface AlternativeZone {
  zone_id: string
  score: number
  utility_score: number
  reason: string
}

export interface GuidanceResult {
  recommended_zone: string
  estimated_wait_minutes: number
  confidence: number
  walking_distance: number
  reason: string
  alternatives: AlternativeZone[]
  utility_score: number
  q_values: Record<string, number>
}

export interface SimulationResult {
  zone_id: string
  entrance: string
  driving_time_minutes: number
  walking_time_minutes: number
  walking_distance: number
  current_available: number
  arrival_probability: number
}

export interface StrategyStats {
  zone_distribution: Record<string, number>
  success_rate: number
  total_guidance: number
  avg_walking_distances: Record<string, number>
}

export interface OccupancyRecord {
  timestamp: string
  occupied: number
  available: number
}

export interface EventInfo {
  id: number
  event_type: string
  title: string
  event_date: string
  start_hour: number
  end_hour: number
  impact_zone_ids: string
  impact_factor: number
  description?: string
  created_at: string
}

export interface EventCreate {
  event_type: string
  title: string
  event_date: string
  start_hour: number
  end_hour: number
  impact_zone_ids: string
  impact_factor?: number
  description?: string
}

export interface ProcessedZonesResponse {
  data: ZoneReading[]
  event_impacts: Record<string, number>
  active_events: EventInfo[]
  processed: boolean
  timestamp: string
  cached?: boolean
  cache_age_ms?: number
}

export interface EdgeSummary {
  total_available: number
  total_spots: number
  occupancy_rate: number
  best_zone: string
  worst_zone: string
  zone_statuses: Record<string, string>
  has_active_events: boolean
  event_count: number
  processing_latency_ms?: number
  timestamp: string
}

export interface ReservationInfo {
  id: number
  zone_id: string
  vehicle_plate: string
  reserved_spot: number
  arrival_time: string
  duration_hours: number
  status: string
  price: number
  created_at: string
}

export interface ReservationCreate {
  zone_id: string
  vehicle_plate: string
  arrival_time: string
  duration_hours: number
}

export interface ZonePricing {
  zone_id: string
  base_price: number
  current_price: number
  surge_factor: number
  demand_level: string
  hourly_rate: number
  base_hourly: number
  updated_at: string
}

export interface NavigationStep {
  instruction: string
  distance: number
  icon: string
}

export interface NavigationRoute {
  zone_id: string
  entrance: string
  driving_distance: number
  driving_time_minutes: number
  walking_distance: number
  walking_time_minutes: number
  turn_by_turn: NavigationStep[]
  estimated_arrival: string
  has_reservation: boolean
  push_status: string
  push_target: string
}

export interface NavigationPushResult {
  success: boolean
  target: string
  route_data: NavigationRoute
  push_time: string
  message_type: string
  protocol: string
  message: string
}

export type ZoneId = 'A' | 'B' | 'C' | 'D' | 'E'

export const ZONE_NAMES: Record<ZoneId, string> = {
  A: 'A区-地面层',
  B: 'B区-地面层',
  C: 'C区-地下一层',
  D: 'D区-地下一层',
  E: 'E区-地下二层',
}

export const ZONE_COLORS: Record<ZoneId, string> = {
  A: '#06D6A0',
  B: '#3B82F6',
  C: '#8B5CF6',
  D: '#F59E0B',
  E: '#EC4899',
}

export const EVENT_TYPES: Record<string, { label: string; color: string; icon: string }> = {
  concert: { label: '演唱会', color: '#EC4899', icon: '🎵' },
  sports: { label: '体育比赛', color: '#3B82F6', icon: '⚽' },
  exhibition: { label: '展览', color: '#8B5CF6', icon: '🎨' },
  conference: { label: '会议', color: '#06D6A0', icon: '📋' },
  festival: { label: '节日活动', color: '#F59E0B', icon: '🎉' },
}
