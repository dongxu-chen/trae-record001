import React, { useState, useEffect } from 'react'
import { useSelector } from 'react-redux'
import { eventBus, EVENTS } from '../../utils/eventBus'

export default function MetricWidget({ config }) {
  const isRefreshing = useSelector((state) => state.dashboard.isRefreshing)
  const { value = '0', trend = '+0%', trendUp = true } = config
  const [filterHighlight, setFilterHighlight] = useState(false)

  useEffect(() => {
    const handleFilterChanged = () => {
      setFilterHighlight(true)
      setTimeout(() => setFilterHighlight(false), 500)
    }

    const handleFilterCleared = () => {
      setFilterHighlight(true)
      setTimeout(() => setFilterHighlight(false), 500)
    }

    const unsubscribeFilter = eventBus.on(EVENTS.FILTER_CHANGED, handleFilterChanged)
    const unsubscribeClear = eventBus.on(EVENTS.FILTER_CLEARED, handleFilterCleared)

    return () => {
      unsubscribeFilter()
      unsubscribeClear()
    }
  }, [])

  return (
    <div className={`metric-widget ${isRefreshing ? 'refreshing' : ''} ${filterHighlight ? 'filter-highlight' : ''}`}>
      <div className="metric-value">{value}</div>
      <div className={`metric-trend ${trendUp ? 'up' : 'down'}`}>
        <span className="trend-icon">{trendUp ? '↑' : '↓'}</span>
        <span className="trend-value">{trend}</span>
        <span className="trend-label">较上期</span>
      </div>
    </div>
  )
}
