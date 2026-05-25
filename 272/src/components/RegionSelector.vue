<template>
  <div class="region-selector" :class="{ collapsed: isCollapsed }">
    <div class="panel-header" @click="toggleCollapse">
      <span class="panel-title">
        <span class="icon">📊</span>
        区域选择
      </span>
      <span class="collapse-icon">{{ isCollapsed ? '展开 ▼' : '收起 ▲' }}</span>
    </div>
    
    <div class="panel-content" v-show="!isCollapsed">
      <div class="selector-buttons">
        <button 
          class="sel-btn" 
          :class="{ active: isSelecting }"
          @click="toggleSelection"
        >
          <span class="btn-icon">🔲</span>
          {{ isSelecting ? '取消选择' : '框选区域' }}
        </button>
        <button 
          class="sel-btn export-btn" 
          :disabled="!hasSelection"
          @click="exportSelection"
        >
          <span class="btn-icon">📥</span>
          导出CSV
        </button>
        <button 
          class="sel-btn export-btn secondary" 
          :disabled="!hasSelection"
          @click="exportGeoJSON"
        >
          <span class="btn-icon">🗺</span>
          导出GeoJSON
        </button>
      </div>

      <div v-if="hasSelection" class="selection-info">
        <div class="info-title">选中区域统计</div>
        <div class="info-row">
          <span class="info-label">数据点数:</span>
          <span class="info-value">{{ selectionStats.count.toLocaleString() }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">热力值总和:</span>
          <span class="info-value">{{ Math.round(selectionStats.sumValue).toLocaleString() }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">平均值:</span>
          <span class="info-value">{{ selectionStats.avgValue.toFixed(1) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">最大值:</span>
          <span class="info-value">{{ selectionStats.maxValue }}</span>
        </div>
      </div>

      <div v-if="isSelecting" class="selection-hint">
        💡 在地图上按住鼠标拖拽来选择区域
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { exportToCSV, exportGeoJSON, getBoundsStats } from '../utils/csvExporter.js'

const props = defineProps({
  map: {
    type: Object,
    default: null
  },
  data: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['selectionChange', 'export'])

const isCollapsed = ref(false)
const isSelecting = ref(false)
const selectionBounds = ref(null)
const selectionStats = ref({
  count: 0,
  sumValue: 0,
  avgValue: 0,
  maxValue: 0,
  data: []
})

let selectionLayer = null
let startLatLng = null
let tempRectangle = null

const hasSelection = computed(() => {
  return selectionBounds.value !== null
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const toggleSelection = () => {
  if (isSelecting.value) {
    cancelSelection()
  } else {
    startSelection()
  }
}

const startSelection = () => {
  if (!props.map) return
  
  isSelecting.value = true
  clearSelection()
  
  props.map.getContainer().style.cursor = 'crosshair'
  props.map.dragging.disable()
  
  props.map.on('mousedown', onMouseDown)
}

const cancelSelection = () => {
  if (!props.map) return
  
  isSelecting.value = false
  props.map.getContainer().style.cursor = ''
  props.map.dragging.enable()
  
  props.map.off('mousedown', onMouseDown)
  props.map.off('mousemove', onMouseMove)
  props.map.off('mouseup', onMouseUp)
  
  if (tempRectangle) {
    props.map.removeLayer(tempRectangle)
    tempRectangle = null
  }
}

const clearSelection = () => {
  if (selectionLayer && props.map) {
    props.map.removeLayer(selectionLayer)
    selectionLayer = null
  }
  selectionBounds.value = null
  selectionStats.value = {
    count: 0,
    sumValue: 0,
    avgValue: 0,
    maxValue: 0,
    data: []
  }
}

const onMouseDown = (e) => {
  startLatLng = e.latlng
  
  if (tempRectangle && props.map) {
    props.map.removeLayer(tempRectangle)
  }
  
  tempRectangle = L.rectangle([startLatLng, startLatLng], {
    color: '#667eea',
    weight: 2,
    fillOpacity: 0.2,
    dashArray: '5, 5'
  }).addTo(props.map)
  
  props.map.on('mousemove', onMouseMove)
  props.map.on('mouseup', onMouseUp)
}

const onMouseMove = (e) => {
  if (!tempRectangle || !startLatLng) return
  
  const bounds = L.latLngBounds(startLatLng, e.latlng)
  tempRectangle.setBounds(bounds)
}

const onMouseUp = (e) => {
  props.map.off('mousemove', onMouseMove)
  props.map.off('mouseup', onMouseUp)
  
  if (!startLatLng) return
  
  const endLatLng = e.latlng
  const bounds = L.latLngBounds(startLatLng, endLatLng)
  
  if (bounds.getNorth() - bounds.getSouth() < 0.001 ||
      bounds.getEast() - bounds.getWest() < 0.001) {
    if (tempRectangle && props.map) {
      props.map.removeLayer(tempRectangle)
      tempRectangle = null
    }
    startLatLng = null
    return
  }
  
  if (selectionLayer && props.map) {
    props.map.removeLayer(selectionLayer)
  }
  
  selectionLayer = L.rectangle(bounds, {
    color: '#667eea',
    weight: 2,
    fillColor: '#667eea',
    fillOpacity: 0.15
  }).addTo(props.map)
  
  if (tempRectangle && props.map) {
    props.map.removeLayer(tempRectangle)
    tempRectangle = null
  }
  
  selectionBounds.value = {
    north: bounds.getNorth(),
    south: bounds.getSouth(),
    east: bounds.getEast(),
    west: bounds.getWest()
  }
  
  updateSelectionStats()
  startLatLng = null
  
  emit('selectionChange', {
    bounds: selectionBounds.value,
    stats: selectionStats.value
  })
}

const updateSelectionStats = () => {
  if (!selectionBounds.value || !props.data) return
  
  const stats = getBoundsStats(props.data, selectionBounds.value)
  selectionStats.value = stats
}

const exportSelection = () => {
  if (!hasSelection.value) return
  
  const now = new Date()
  const filename = `heatmap_export_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}.csv`
  
  const success = exportToCSV(selectionStats.value.data, filename)
  
  if (success) {
    emit('export', { type: 'csv', count: selectionStats.value.count, filename })
  }
}

const exportGeoJSON = () => {
  if (!hasSelection.value) return
  
  const now = new Date()
  const filename = `heatmap_export_${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}.geojson`
  
  const success = exportGeoJSON(selectionStats.value.data, filename)
  
  if (success) {
    emit('export', { type: 'geojson', count: selectionStats.value.count, filename })
  }
}

onMounted(() => {
})

onUnmounted(() => {
  cancelSelection()
  clearSelection()
})

defineExpose({
  clearSelection,
  startSelection,
  cancelSelection,
  selectionStats,
  selectionBounds
})
</script>

<style scoped>
.region-selector {
  position: absolute;
  top: 20px;
  right: 280px;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 220px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
  cursor: pointer;
  border-radius: 10px 10px 0 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon {
  font-size: 16px;
}

.collapse-icon {
  font-size: 12px;
  opacity: 0.9;
}

.panel-content {
  padding: 14px;
}

.selector-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 14px;
}

.sel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 14px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  transition: all 0.2s;
}

.sel-btn:hover:not(:disabled) {
  border-color: #11998e;
  color: #11998e;
}

.sel-btn.active {
  border-color: #11998e;
  background: #11998e;
  color: white;
}

.export-btn {
  border-color: #11998e;
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
}

.export-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #0e8077 0%, #2ed66e 100%);
  color: white;
}

.export-btn.secondary {
  background: white;
  color: #11998e;
}

.export-btn.secondary:hover:not(:disabled) {
  background: #f0faf8;
}

.sel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  font-size: 14px;
}

.selection-info {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.info-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 12px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  color: #666;
}

.info-value {
  font-weight: 600;
  color: #11998e;
}

.selection-hint {
  font-size: 12px;
  color: #666;
  text-align: center;
  padding: 8px;
  background: #fff3cd;
  border-radius: 6px;
}
</style>
