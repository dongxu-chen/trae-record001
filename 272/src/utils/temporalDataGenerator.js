export const generateTemporalData = (
  pointCount = 1000,
  timeSteps = 24,
  centerLat = 39.9042,
  centerLng = 116.4074,
  spread = 0.5
) => {
  const timeSeriesData = []
  
  const basePoints = []
  for (let i = 0; i < pointCount; i++) {
    const lat = centerLat + (Math.random() - 0.5) * spread
    const lng = centerLng + (Math.random() - 0.5) * spread
    basePoints.push({
      lat,
      lng,
      baseValue: Math.random() * 50 + 10,
      phase: Math.random() * Math.PI * 2,
      frequency: 0.5 + Math.random() * 1.5
    })
  }
  
  for (let t = 0; t < timeSteps; t++) {
    const timeData = []
    const timeProgress = t / timeSteps
    
    for (let i = 0; i < basePoints.length; i++) {
      const point = basePoints[i]
      const waveValue = Math.sin(timeProgress * Math.PI * 2 * point.frequency + point.phase)
      const timeFactor = 0.5 + 0.5 * waveValue
      const randomFactor = 0.8 + Math.random() * 0.4
      
      timeData.push({
        lat: point.lat,
        lng: point.lng,
        value: Math.round(point.baseValue * timeFactor * randomFactor),
        time: t
      })
    }
    
    timeSeriesData.push({
      timeIndex: t,
      timeLabel: formatTimeLabel(t, timeSteps),
      data: timeData
    })
  }
  
  return timeSeriesData
}

const formatTimeLabel = (index, total) => {
  const hour = Math.floor((index / total) * 24)
  return `${hour.toString().padStart(2, '0')}:00`
}

export const generateHeatwaveData = (
  pointCount = 5000,
  timeSteps = 12,
  centerLat = 39.9042,
  centerLng = 116.4074
) => {
  const timeSeriesData = []
  const hotspots = []
  
  const hotspotCount = 8
  for (let i = 0; i < hotspotCount; i++) {
    hotspots.push({
      lat: centerLat + (Math.random() - 0.5) * 0.8,
      lng: centerLng + (Math.random() - 0.5) * 0.8,
      maxRadius: 0.05 + Math.random() * 0.1,
      intensity: 50 + Math.random() * 50,
      peakTime: Math.floor(Math.random() * timeSteps * 0.6) + timeSteps * 0.2
    })
  }
  
  for (let t = 0; t < timeSteps; t++) {
    const timeData = []
    
    for (let h = 0; h < hotspotCount; h++) {
      const hotspot = hotspots[h]
      const timeFactor = Math.exp(-Math.pow(t - hotspot.peakTime, 2) / (2 * Math.pow(timeSteps * 0.3, 2)))
      const pointsInHotspot = Math.floor(pointCount / hotspotCount * timeFactor)
      
      for (let i = 0; i < pointsInHotspot; i++) {
        const angle = Math.random() * Math.PI * 2
        const distance = Math.sqrt(Math.random()) * hotspot.maxRadius * timeFactor
        
        timeData.push({
          lat: hotspot.lat + distance * Math.cos(angle),
          lng: hotspot.lng + distance * Math.sin(angle),
          value: Math.round(hotspot.intensity * timeFactor * (0.7 + Math.random() * 0.6)),
          time: t
        })
      }
    }
    
    timeSeriesData.push({
      timeIndex: t,
      timeLabel: `第${t + 1}小时`,
      data: timeData
    })
  }
  
  return timeSeriesData
}

export const interpolateTimeData = (timeSeriesData, progress) => {
  const totalSteps = timeSeriesData.length
  const exactIndex = progress * (totalSteps - 1)
  const lowerIndex = Math.floor(exactIndex)
  const upperIndex = Math.min(lowerIndex + 1, totalSteps - 1)
  const interpFactor = exactIndex - lowerIndex
  
  if (interpFactor === 0) {
    return timeSeriesData[lowerIndex].data
  }
  
  const lowerData = timeSeriesData[lowerIndex].data
  const upperData = timeSeriesData[upperIndex].data
  
  const pointMap = new Map()
  
  for (let i = 0; i < lowerData.length; i++) {
    const point = lowerData[i]
    const key = `${point.lat.toFixed(5)}_${point.lng.toFixed(5)}`
    pointMap.set(key, {
      lat: point.lat,
      lng: point.lng,
      lowerValue: point.value,
      upperValue: 0,
      hasUpper: false
    })
  }
  
  for (let i = 0; i < upperData.length; i++) {
    const point = upperData[i]
    const key = `${point.lat.toFixed(5)}_${point.lng.toFixed(5)}`
    
    if (pointMap.has(key)) {
      const entry = pointMap.get(key)
      entry.upperValue = point.value
      entry.hasUpper = true
    } else {
      pointMap.set(key, {
        lat: point.lat,
        lng: point.lng,
        lowerValue: 0,
        upperValue: point.value,
        hasUpper: true
      })
    }
  }
  
  const interpolatedData = []
  pointMap.forEach((entry) => {
    const value = entry.lowerValue * (1 - interpFactor) + entry.upperValue * interpFactor
    if (value > 1) {
      interpolatedData.push({
        lat: entry.lat,
        lng: entry.lng,
        value: Math.round(value)
      })
    }
  })
  
  return interpolatedData
}
