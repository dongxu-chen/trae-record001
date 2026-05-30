import type {
  ZoneReading,
  PredictionResult,
  GuidanceResult,
  SimulationResult,
  StrategyStats,
  OccupancyRecord,
  EventInfo,
  EventCreate,
  ProcessedZonesResponse,
  EdgeSummary,
  ReservationInfo,
  ReservationCreate,
  ZonePricing,
  NavigationRoute,
  NavigationPushResult,
} from './types'

const BASE = '/api'

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchZones(forceRefresh = false): Promise<ProcessedZonesResponse> {
  const url = forceRefresh ? `${BASE}/zones?force_refresh=true` : `${BASE}/zones`
  return fetchJSON<ProcessedZonesResponse>(url)
}

export async function fetchEdgeSummary(): Promise<EdgeSummary> {
  return fetchJSON<EdgeSummary>(`${BASE}/edge/summary`)
}

export async function fetchZoneHistory(zoneId: string, hours = 24): Promise<ZoneReading[]> {
  return fetchJSON<ZoneReading[]>(`${BASE}/zones/${zoneId}/history?hours=${hours}`)
}

export async function fetchPrediction(zoneId: string, minutes = 30): Promise<PredictionResult> {
  return fetchJSON<PredictionResult>(`${BASE}/predict/${zoneId}?minutes=${minutes}`)
}

export async function fetchAllPredictions(minutes = 30): Promise<Record<string, PredictionResult>> {
  const zoneIds = ['A', 'B', 'C', 'D', 'E']
  const results: Record<string, PredictionResult> = {}
  await Promise.all(
    zoneIds.map(async (id) => {
      results[id] = await fetchPrediction(id, minutes)
    })
  )
  return results
}

export async function fetchGuidance(entrance = 'A'): Promise<GuidanceResult> {
  return fetchJSON<GuidanceResult>(`${BASE}/guide/recommend?entrance=${entrance}`)
}

export async function fetchSimulation(entrance: string, zoneId: string): Promise<SimulationResult> {
  return fetchJSON<SimulationResult>(`${BASE}/guide/simulate?entrance=${entrance}&zone_id=${zoneId}`)
}

export async function submitFeedback(
  recommendedZone: string,
  actualZone: string,
  entrance: string,
  success: boolean,
  walkingDistance: number = 0
): Promise<void> {
  await fetch(`${BASE}/guide/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      recommended_zone: recommendedZone,
      actual_zone: actualZone,
      entrance,
      success,
      walking_distance: walkingDistance,
    }),
  })
}

export async function fetchStrategyStats(): Promise<StrategyStats> {
  return fetchJSON<StrategyStats>(`${BASE}/guide/stats`)
}

export async function fetchOccupancy(hours = 24): Promise<Record<string, OccupancyRecord[]>> {
  return fetchJSON<Record<string, OccupancyRecord[]>>(`${BASE}/analytics/occupancy?hours=${hours}`)
}

export async function trainModel(): Promise<void> {
  await fetch(`${BASE}/predict/train`, { method: 'POST' })
}

export async function fetchEvents(includePast = false): Promise<EventInfo[]> {
  return fetchJSON<EventInfo[]>(`${BASE}/events?include_past=${includePast}`)
}

export async function fetchActiveEvents(): Promise<EventInfo[]> {
  return fetchJSON<EventInfo[]>(`${BASE}/events/active`)
}

export async function createEvent(event: EventCreate): Promise<{ id: number; status: string }> {
  const res = await fetch(`${BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function deleteEvent(eventId: number): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/events/${eventId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchReservations(zoneId?: string, status?: string): Promise<ReservationInfo[]> {
  const params = new URLSearchParams()
  if (zoneId) params.set('zone_id', zoneId)
  if (status) params.set('status', status)
  const query = params.toString() ? `?${params.toString()}` : ''
  return fetchJSON<ReservationInfo[]>(`${BASE}/reservations${query}`)
}

export async function createReservation(data: ReservationCreate): Promise<{ id: number; status: string; zone_id: string; spot_number: number; price: number; message: string }> {
  const res = await fetch(`${BASE}/reservations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function cancelReservation(reservationId: number): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/reservations/${reservationId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function fetchPricing(): Promise<ZonePricing[]> {
  return fetchJSON<ZonePricing[]>(`${BASE}/pricing`)
}

export async function fetchZonePricing(zoneId: string): Promise<ZonePricing> {
  return fetchJSON<ZonePricing>(`${BASE}/pricing/${zoneId}`)
}

export async function createNavigationRoute(zoneId: string, entrance: string = 'A', vehiclePlate?: string): Promise<NavigationRoute> {
  const res = await fetch(`${BASE}/navigation/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone_id: zoneId, entrance, vehicle_plate: vehiclePlate }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function pushNavigationToVehicle(zoneId: string, entrance: string = 'A', vehiclePlate?: string): Promise<NavigationPushResult> {
  const res = await fetch(`${BASE}/navigation/push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ zone_id: zoneId, entrance, vehicle_plate: vehiclePlate }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}
