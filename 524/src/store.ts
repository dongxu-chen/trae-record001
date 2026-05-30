import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  ZoneReading,
  PredictionResult,
  GuidanceResult,
  EventInfo,
  EdgeSummary,
  ReservationInfo,
  ZonePricing,
  NavigationRoute,
} from './types'

interface ParkingState {
  zones: ZoneReading[]
  predictions: Record<string, PredictionResult>
  guidance: GuidanceResult | null
  selectedZone: string | null
  events: EventInfo[]
  activeEvents: EventInfo[]
  edgeSummary: EdgeSummary | null
  eventImpacts: Record<string, number>
  reservations: ReservationInfo[]
  pricing: ZonePricing[]
  navigationRoute: NavigationRoute | null
  loading: boolean
  lastUpdate: string | null
  lastZoneUpdate: string | null

  setZones: (zones: ZoneReading[]) => void
  setPredictions: (predictions: Record<string, PredictionResult>) => void
  setGuidance: (guidance: GuidanceResult) => void
  setSelectedZone: (zone: string | null) => void
  setEvents: (events: EventInfo[]) => void
  setActiveEvents: (events: EventInfo[]) => void
  setEdgeSummary: (summary: EdgeSummary) => void
  setEventImpacts: (impacts: Record<string, number>) => void
  setReservations: (reservations: ReservationInfo[]) => void
  setPricing: (pricing: ZonePricing[]) => void
  setNavigationRoute: (route: NavigationRoute | null) => void
  setLoading: (loading: boolean) => void
  setLastUpdate: (time: string) => void
  setLastZoneUpdate: (time: string) => void
  incrementallyUpdateZones: (newZones: ZoneReading[]) => void
  addEvent: (event: EventInfo) => void
  removeEvent: (eventId: number) => void
}

export const useParkingStore = create<ParkingState>()(
  persist(
    (set) => ({
      zones: [],
      predictions: {},
      guidance: null,
      selectedZone: null,
      events: [],
      activeEvents: [],
      edgeSummary: null,
      eventImpacts: {},
      reservations: [],
      pricing: [],
      navigationRoute: null,
      loading: false,
      lastUpdate: null,
      lastZoneUpdate: null,

      setZones: (zones) =>
        set({
          zones,
          lastUpdate: new Date().toISOString(),
          lastZoneUpdate: new Date().toISOString(),
        }),
      setPredictions: (predictions) => set({ predictions }),
      setGuidance: (guidance) => set({ guidance }),
      setSelectedZone: (zone) => set({ selectedZone: zone }),
      setEvents: (events) => set({ events }),
      setActiveEvents: (events) => set({ activeEvents: events }),
      setEdgeSummary: (summary) => set({ edgeSummary: summary }),
      setEventImpacts: (impacts) => set({ eventImpacts: impacts }),
      setReservations: (reservations) => set({ reservations }),
      setPricing: (pricing) => set({ pricing }),
      setNavigationRoute: (route) => set({ navigationRoute: route }),
      setLoading: (loading) => set({ loading }),
      setLastUpdate: (time) => set({ lastUpdate: time }),
      setLastZoneUpdate: (time) => set({ lastZoneUpdate: time }),

      incrementallyUpdateZones: (newZones) =>
        set((state) => {
          const zoneMap = new Map(state.zones.map((z) => [z.zone_id, z]))
          newZones.forEach((z) => {
            const existing = zoneMap.get(z.zone_id)
            if (!existing || existing.timestamp !== z.timestamp) {
              zoneMap.set(z.zone_id, z)
            }
          })
          return {
            zones: Array.from(zoneMap.values()),
            lastZoneUpdate: new Date().toISOString(),
          }
        }),

      addEvent: (event) =>
        set((state) => ({ events: [...state.events, event] })),
      removeEvent: (eventId) =>
        set((state) => ({
          events: state.events.filter((e) => e.id !== eventId),
        })),
    }),
    {
      name: 'parking-edge-storage',
      partialize: (state) => ({
        zones: state.zones,
        edgeSummary: state.edgeSummary,
        eventImpacts: state.eventImpacts,
        lastZoneUpdate: state.lastZoneUpdate,
      }),
    }
  )
)
