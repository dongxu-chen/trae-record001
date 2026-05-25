<template>
  <div ref="mapContainer" class="heatmap-container">
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <span class="loading-text">数据处理中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import L from 'leaflet'
import h337 from 'heatmap.js'
import { ZoomLevelCache } from '../utils/heatmapCache.js'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  latField: {
    type: String,
    default: 'lat'
  },
  lngField: {
    type: String,
    default: 'lng'
  },
  valueField: {
    type: String,
    default: 'value'
  },
  radius: {
    type: Number,
    default: 25
  },
  maxOpacity: {
    type: Number,
    default: 0.8
  },
  minOpacity: {
    type: Number,
    default: 0.1
  },
  blur: {
    type: Number,
    default: 0.85
  },
  gradient: {
    type: Object,
    default: () => ({
      0.4: 'blue',
      0.6: 'cyan',
      0.7: 'lime',
      0.8: 'yellow',
      1.0: 'red'
    })
  },
  maxValue: {
    type: Number,
    default: null
  },
  minValue: {
    type: Number,
    default: 0
  },
  center: {
    type: Array,
    default: () => [39.9042, 116.4074]
  },
  zoom: {
    type: Number,
    default: 12
  },
  showLegend: {
    type: Boolean,
    default: true
  },
  enableClickQuery: {
    type: Boolean,
    default: true
  },
  useWorker: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['heatmapClick', 'zoomChange', 'moveEnd', 'dataLoaded'])

const mapContainer = ref(null)
const isLoading = ref(false)

let map = null
let heatmapInstance = null
let heatmapCanvas = null
let worker = null
let zoomCache = null

const aggregatedDataCache = new Map()
let currentAggregatedData = []
let isWorkerProcessing = false
let pendingZoom = null

const config = computed(() => ({
  radius: props.radius,
  maxOpacity: props.maxOpacity,
  minOpacity: props.minOpacity,
  blur: props.blur,
  gradient: props.gradient
}))

const initWorker = () => {
  if (!props.useWorker || typeof Worker === 'undefined') {
    return null
  }
  
  try {
    const workerBlob = new Blob([`
      ${workerCode.toString().slice(workerCode.toString().indexOf('{') + 1, -1)}
    `], { type: 'application/javascript' })
    
    const workerUrl = URL.createObjectURL(workerBlob)
    const newWorker = new Worker(workerUrl)
    
    newWorker.onmessage = handleWorkerMessage
    newWorker.onerror = (e) => {
      console.warn('Worker error, falling back to main thread:', e)
      newWorker.terminate()
      worker = null
    }
    
    return newWorker
  } catch (e) {
    console.warn('Failed to create worker:', e)
    return null
  }
}

const workerCode = () => {
  class HeatmapWorker {
    constructor() {
      this.rawData = { data: new Float64Array(), length: 0, maxValue: 0 }
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
        const key = gridX + '_' + gridY
        
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

  const workerInstance = new HeatmapWorker()

  self.onmessage = (e) => {
    const { type, payload } = e.data
    
    switch (type) {
      case 'init':
        workerInstance.init(payload.data, payload.latField, payload.lngField, payload.valueField)
        self.postMessage({ type: 'initComplete' })
        break
        
      case 'aggregate':
        const result = workerInstance.aggregateForZoom(payload.zoom)
        self.postMessage({ 
          type: 'aggregateComplete', 
          payload: { data: result, zoom: payload.zoom }
        })
        break
        
      case 'query':
        const value = workerInstance.queryHeatValue(payload.lat, payload.lng, payload.radius, payload.zoom)
        self.postMessage({
          type: 'queryComplete',
          payload: { value, lat: payload.lat, lng: payload.lng }
        })
        break
        
      case 'clearCache':
        workerInstance.clearCache()
        self.postMessage({ type: 'clearCacheComplete' })
        break
    }
  }
}

const handleWorkerMessage = (e) => {
  const { type, payload } = e.data
  
  switch (type) {
    case 'initComplete':
      isLoading.value = false
      isWorkerProcessing = false
      requestAggregate(map.getZoom())
      emit('dataLoaded')
      break
      
    case 'aggregateComplete':
      isWorkerProcessing = false
      currentAggregatedData = payload.data
      aggregatedDataCache.set(payload.zoom, payload.data)
      renderHeatmap()
      
      if (pendingZoom !== null) {
        const nextZoom = pendingZoom
        pendingZoom = null
        requestAggregate(nextZoom)
      }
      break
      
    case 'queryComplete':
      emit('heatmapClick', {
        lat: payload.lat,
        lng: payload.lng,
        heatValue: payload.value
      })
      break
  }
}

const requestAggregate = (zoom) => {
  if (aggregatedDataCache.has(zoom)) {
    currentAggregatedData = aggregatedDataCache.get(zoom)
    renderHeatmap()
    return
  }
  
  if (worker && !isWorkerProcessing) {
    isWorkerProcessing = true
    worker.postMessage({ type: 'aggregate', payload: { zoom } })
  } else if (worker && isWorkerProcessing) {
    pendingZoom = zoom
  } else {
    currentAggregatedData = aggregateDataForZoomMainThread(zoom)
    aggregatedDataCache.set(zoom, currentAggregatedData)
    renderHeatmap()
  }
}

const aggregateDataForZoomMainThread = (zoom) => {
  const data = props.data
  if (!data || data.length < 10000) {
    return data.map(item => ({
      lat: parseFloat(item[props.latField]),
      lng: parseFloat(item[props.lngField]),
      value: parseFloat(item[props.valueField]) || 1
    }))
  }

  const gridSize = Math.max(0.0001, 0.01 / Math.pow(2, zoom - 10))
  const grid = new Map()
  
  for (let i = 0; i < data.length; i++) {
    const item = data[i]
    const lat = parseFloat(item[props.latField])
    const lng = parseFloat(item[props.lngField])
    const value = parseFloat(item[props.valueField]) || 1
    
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
  
  const result = []
  grid.forEach((cell) => {
    result.push({
      lat: cell.sumLat / cell.count,
      lng: cell.sumLng / cell.count,
      value: cell.sumValue
    })
  })
  
  return result
}

const renderHeatmap = () => {
  if (!heatmapInstance || !map) return
  
  const center = map.getCenter()
  const zoom = map.getZoom()
  
  if (zoomCache.has(zoom)) {
    const cachedData = zoomCache.get(zoom).data
    heatmapInstance.setData(cachedData)
    return
  }
  
  const dataPoints = []
  let maxVal = 0
  const bounds = map.getBounds()
  const padding = 0.1
  const paddedBounds = bounds.pad(padding)
  
  for (let i = 0; i < currentAggregatedData.length; i++) {
    const point = currentAggregatedData[i]
    
    if (!paddedBounds.contains([point.lat, point.lng])) {
      continue
    }
    
    const containerPoint = map.latLngToContainerPoint([point.lat, point.lng])
    
    dataPoints.push({
      x: Math.round(containerPoint.x),
      y: Math.round(containerPoint.y),
      value: point.value
    })
    
    if (point.value > maxVal) {
      maxVal = point.value
    }
  }
  
  const heatmapData = {
    max: props.maxValue || maxVal || 100,
    min: props.minValue,
    data: dataPoints
  }
  
  heatmapInstance.setData(heatmapData)
  zoomCache.set(zoom, heatmapData)
}

const getHeatValueAtPoint = (lat, lng) => {
  if (worker) {
    worker.postMessage({
      type: 'query',
      payload: {
        lat,
        lng,
        radius: props.radius,
        zoom: map.getZoom()
      }
    })
    return null
  }
  
  const zoom = map.getZoom()
  const gridSize = Math.max(0.0001, 0.01 / Math.pow(2, zoom - 10))
  const searchRadius = props.radius * gridSize
  
  let totalValue = 0
  let count = 0
  
  for (let i = 0; i < currentAggregatedData.length; i++) {
    const point = currentAggregatedData[i]
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

const initMap = () => {
  map = L.map(mapContainer.value, {
    center: props.center,
    zoom: props.zoom,
    zoomControl: true
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  heatmapCanvas = document.createElement('div')
  heatmapCanvas.style.position = 'absolute'
  heatmapCanvas.style.top = '0'
  heatmapCanvas.style.left = '0'
  heatmapCanvas.style.width = '100%'
  heatmapCanvas.style.height = '100%'
  heatmapCanvas.style.pointerEvents = 'none'
  
  map.getPanes().overlayPane.appendChild(heatmapCanvas)

  heatmapInstance = h337.create({
    container: heatmapCanvas,
    ...config.value
  })

  map.on('movestart', () => {
    heatmapCanvas.style.opacity = '0.7'
  })

  map.on('moveend', () => {
    heatmapCanvas.style.opacity = '1'
    renderHeatmap()
    emit('moveEnd', {
      center: map.getCenter(),
      zoom: map.getZoom()
    })
  })

  map.on('zoomstart', () => {
    heatmapCanvas.style.opacity = '0.5'
  })

  map.on('zoomend', () => {
    heatmapCanvas.style.opacity = '1'
    const newZoom = map.getZoom()
    requestAggregate(newZoom)
    emit('zoomChange', newZoom)
  })

  map.on('resize', () => {
    const size = map.getSize()
    heatmapCanvas.style.width = size.x + 'px'
    heatmapCanvas.style.height = size.y + 'px'
    zoomCache.clear()
    renderHeatmap()
  })

  if (props.enableClickQuery) {
    map.on('click', (e) => {
      const lat = e.latlng.lat
      const lng = e.latlng.lng
      
      const value = getHeatValueAtPoint(lat, lng)
      
      if (value !== null || !worker) {
        emit('heatmapClick', {
          lat,
          lng,
          heatValue: value
        })
      }
    })
  }
}

const initData = () => {
  if (!props.data || props.data.length === 0) {
    return
  }
  
  aggregatedDataCache.clear()
  zoomCache.clear()
  
  if (worker) {
    isLoading.value = true
    isWorkerProcessing = true
    worker.postMessage({
      type: 'init',
      payload: {
        data: props.data,
        latField: props.latField,
        lngField: props.lngField,
        valueField: props.valueField
      }
    })
  } else {
    requestAggregate(map?.getZoom() || props.zoom)
    emit('dataLoaded')
  }
}

watch(() => props.data, () => {
  initData()
}, { deep: false })

watch(config, () => {
  if (heatmapInstance) {
    heatmapInstance.configure(config.value)
    zoomCache.clear()
    renderHeatmap()
  }
}, { deep: true })

watch(() => [props.center, props.zoom], ([newCenter, newZoom]) => {
  if (map) {
    map.setView(newCenter, newZoom)
  }
}, { deep: true })

onMounted(async () => {
  await nextTick()
  
  zoomCache = new ZoomLevelCache()
  
  if (props.useWorker) {
    worker = initWorker()
  }
  
  initMap()
  
  nextTick(() => {
    initData()
  })
})

onUnmounted(() => {
  if (worker) {
    worker.terminate()
    worker = null
  }
  
  if (map) {
    map.remove()
    map = null
  }
  
  heatmapInstance = null
  aggregatedDataCache.clear()
  
  if (zoomCache) {
    zoomCache.clear()
    zoomCache = null
  }
})

defineExpose({
  getMap: () => map,
  getHeatValueAtPoint,
  updateHeatmap: () => {
    zoomCache.clear()
    renderHeatmap()
  },
  clearCache: () => {
    aggregatedDataCache.clear()
    zoomCache.clear()
    if (worker) {
      worker.postMessage({ type: 'clearCache' })
    }
  }
})
</script>

<style scoped>
.heatmap-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 12px;
  font-size: 14px;
  color: #666;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
