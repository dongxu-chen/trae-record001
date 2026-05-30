import { useEffect, useCallback, useRef } from 'react'
import { useParkingStore } from '@/store'
import {
  fetchZones,
  fetchAllPredictions,
  fetchGuidance,
  fetchEdgeSummary,
  fetchActiveEvents,
} from '@/api'
import type { ZoneReading } from '@/types'

const CACHE_THRESHOLD_MS = 3000

export function useParkingData() {
  const {
    setZones,
    setPredictions,
    setGuidance,
    setEventImpacts,
    setActiveEvents,
    setEdgeSummary,
    incrementallyUpdateZones,
    lastZoneUpdate,
    zones,
  } = useParkingStore()

  const abortRef = useRef<AbortController | null>(null)

  const loadData = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
    abortRef.current = new AbortController()

    try {
      const now = Date.now()
      const lastUpdateMs = lastZoneUpdate ? new Date(lastZoneUpdate).getTime() : 0
      const useCache = zones.length > 0 && now - lastUpdateMs < CACHE_THRESHOLD_MS

      if (!useCache) {
        const [zoneResponse, predictions, guidance, edgeSummary, activeEvents] = await Promise.all([
          fetchZones(false),
          fetchAllPredictions(30),
          fetchGuidance('A'),
          fetchEdgeSummary(),
          fetchActiveEvents(),
        ])

        setZones(zoneResponse.data)
        setEventImpacts(zoneResponse.event_impacts || {})
        setActiveEvents(activeEvents)
        setPredictions(predictions)
        setGuidance(guidance)
        setEdgeSummary(edgeSummary)
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('Failed to load parking data:', err)
      }
    }
  }, [
    setZones,
    setPredictions,
    setGuidance,
    setEventImpacts,
    setActiveEvents,
    setEdgeSummary,
    lastZoneUpdate,
    zones.length,
  ])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => {
      clearInterval(interval)
      if (abortRef.current) {
        abortRef.current.abort()
      }
    }
  }, [loadData])

  return { lastZoneUpdate }
}

export function useSSEStream() {
  const { incrementallyUpdateZones, setEventImpacts, setActiveEvents } = useParkingStore()

  useEffect(() => {
    const es = new EventSource('/api/stream')

    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        if (parsed.event === 'zone_update' && parsed.data) {
          if (Array.isArray(parsed.data)) {
            incrementallyUpdateZones(parsed.data as ZoneReading[])
          } else if (parsed.data.data) {
            incrementallyUpdateZones(parsed.data.data as ZoneReading[])
            if (parsed.data.event_impacts) {
              setEventImpacts(parsed.data.event_impacts)
            }
            if (parsed.data.active_events) {
              setActiveEvents(parsed.data.active_events)
            }
          }
        }
      } catch (e) {
        // ignore
      }
    }

    es.onerror = () => {
      es.close()
    }

    return () => {
      es.close()
    }
  }, [incrementallyUpdateZones, setEventImpacts, setActiveEvents])
}

export function useEdgePrefetch() {
  const { setEdgeSummary } = useParkingStore()

  useEffect(() => {
    async function prefetch() {
      try {
        const summary = await fetchEdgeSummary()
        setEdgeSummary(summary)
      } catch (e) {
        // ignore
      }
    }
    prefetch()
    const interval = setInterval(prefetch, 2000)
    return () => clearInterval(interval)
  }, [setEdgeSummary])
}
