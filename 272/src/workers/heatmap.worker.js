class HeatmapWorker {
  constructor() {
    this.rawData = []
    this.cachedAggregatedData = new Map()
  }

  init(data, latField, lngField, valueField) {
    this.rawData = this.processRawData(data, latField, lngField, valueField)
    this.cachedAggregatedData.clear()
  }

  processRawData(data, latField, lngField, valueField) {
    const processed = new Float64Array(data.length * 3)
    let maxVal = 0
    
    for (let i = 0; i < data.length; i++) {
      const item = data[i]
      const lat = parseFloat(item[latField])
      const lng = parseFloat(item[lngField])
      const value = parseFloat(item[valueField]) || 1
      
      const idx = i * 3
      processed[idx] = lat
      processed[idx + 1] = lng
      processed[idx + 2] = value
      
      if (value > maxVal) {
        maxVal = value
      }
    }
    
    return {
      data: processed,
      length: data.length,
      maxValue: maxVal
    }
  }

  aggregateForZoom(zoom) {
    if (this.cachedAggregatedData.has(zoom)) {
      return this.cachedAggregatedData.get(zoom)
    }

    const { data, length } = this.rawData
    const result = []
    
    if (length < 10000) {
      const simplified = []
      for (let i = 0; i < length; i++) {
        const idx = i * 3
        simplified.push({
          lat: data[idx],
          lng: data[idx + 1],
          value: data[idx + 2]
        })
      }
      this.cachedAggregatedData.set(zoom, simplified)
      return simplified
    }

    const gridSize = Math.max(0.0001, 0.01 / Math.pow(2, zoom - 10))
    const grid = new Map()
    
    for (let i = 0; i < length; i++) {
      const idx = i * 3
      const lat = data[idx]
      const lng = data[idx + 1]
      const value = data[idx + 2]
      
      const gridX = Math.floor(lng / gridSize)
      const gridY = Math.floor(lat / gridSize)
      const key = `${gridX}_${gridY}`
      
      if (grid.has(key)) {
        const cell = grid.get(key)
        cell.sumLat += lat
        cell.sumLng += lng
        cell.sumValue += value
        cell.count++
      } else {
        grid.set(key, {
          sumLat: lat,
          sumLng: lng,
          sumValue: value,
          count: 1
        })
      }
    }
    
    grid.forEach((cell) => {
      result.push({
        lat: cell.sumLat / cell.count,
        lng: cell.sumLng / cell.count,
        value: cell.sumValue
      })
    })
    
    this.cachedAggregatedData.set(zoom, result)
    return result
  }

  queryHeatValue(lat, lng, radius, zoom) {
    const aggregatedData = this.aggregateForZoom(zoom)
    const gridSize = Math.max(0.0001, 0.01 / Math.pow(2, zoom - 10))
    const searchRadius = radius * gridSize
    
    let totalValue = 0
    let count = 0
    
    for (let i = 0; i < aggregatedData.length; i++) {
      const point = aggregatedData[i]
      const dx = point.lng - lng
      const dy = point.lat - lat
      const distance = Math.sqrt(dx * dx + dy * dy)
      
      if (distance < searchRadius) {
        const influence = Math.max(0, 1 - distance / searchRadius)
        totalValue += point.value * influence
        count++
      }
    }
    
    return count > 0 ? totalValue : null
  }

  clearCache() {
    this.cachedAggregatedData.clear()
  }
}

const worker = new HeatmapWorker()

self.onmessage = (e) => {
  const { type, payload } = e.data
  
  switch (type) {
    case 'init':
      worker.init(payload.data, payload.latField, payload.lngField, payload.valueField)
      self.postMessage({ type: 'initComplete' })
      break
      
    case 'aggregate':
      const result = worker.aggregateForZoom(payload.zoom)
      self.postMessage({ 
        type: 'aggregateComplete', 
        payload: { data: result, zoom: payload.zoom }
      })
      break
      
    case 'query':
      const value = worker.queryHeatValue(payload.lat, payload.lng, payload.radius, payload.zoom)
      self.postMessage({
        type: 'queryComplete',
        payload: { value, lat: payload.lat, lng: payload.lng }
      })
      break
      
    case 'clearCache':
      worker.clearCache()
      self.postMessage({ type: 'clearCacheComplete' })
      break
  }
}
