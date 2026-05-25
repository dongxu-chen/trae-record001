<template>
  <div class="app-container">
    <div class="map-wrapper" ref="mapWrapper">
      <HeatmapLayer
        ref="heatmapRef"
        :data="displayData"
        :radius="config.radius"
        :maxOpacity="config.maxOpacity"
        :minOpacity="config.minOpacity"
        :blur="config.blur"
        :gradient="config.gradient"
        :maxValue="maxValue"
        :center="center"
        :zoom="zoom"
        :enableClickQuery="config.enableClickQuery"
        @heatmapClick="handleHeatmapClick"
        @zoomChange="handleZoomChange"
        @moveEnd="handleMoveEnd"
        @dataLoaded="handleDataLoaded"
      />
      
      <HeatmapControlPanel
        :radius="config.radius"
        :maxOpacity="config.maxOpacity"
        :minOpacity="config.minOpacity"
        :blur="config.blur"
        :gradient="config.gradient"
        :showLegend="config.showLegend"
        :enableClickQuery="config.enableClickQuery"
        @change="handleConfigChange"
      />
      
      <RegionSelector
        v-if="!isAnimationMode"
        :map="mapInstance"
        :data="displayData"
        @selectionChange="handleSelectionChange"
        @export="handleExport"
      />
      
      <HeatmapLegend
        v-if="config.showLegend"
        :gradient="config.gradient"
        :minValue="0"
        :maxValue="maxValue"
        :position="'bottomright'"
        :title="isAnimationMode ? '动画热力值' : '热力值'"
        :unit="''"
        :decimals="0"
      />
      
      <HeatmapInfoPopup
        :visible="popupVisible"
        :info="clickInfo"
        :position="popupPosition"
        :maxValue="maxValue"
        :gradient="config.gradient"
        @close="popupVisible = false"
      />
      
      <AnimationControlPanel
        v-if="timeSeriesData.length > 0"
        :timeSeriesData="timeSeriesData"
        v-model="isAnimationMode"
        @dataUpdate="handleAnimationDataUpdate"
        @timeChange="handleTimeChange"
      />
      
      <div class="data-controls">
        <div class="data-title">数据控制</div>
        <div class="data-buttons">
          <button 
            class="data-btn" 
            @click="loadThousandPoints"
            :class="{ active: dataMode === 'thousand' }"
          >
            1万点
          </button>
          <button 
            class="data-btn" 
            @click="loadHundredThousandPoints"
            :class="{ active: dataMode === 'hundred-thousand' }"
          >
            10万点
          </button>
          <button 
            class="data-btn million-btn" 
            @click="loadMillionPoints"
            :class="{ active: dataMode === 'million', loading: isLoadingMillion }"
            :disabled="isLoadingMillion"
          >
            {{ isLoadingMillion ? '生成中...' : '100万点' }}
          </button>
        </div>
        <div class="divider"></div>
        <div class="data-buttons">
          <button 
            class="data-btn animate-btn" 
            @click="loadAnimationData"
            :class="{ active: dataMode === 'animation' }"
          >
            🎬 动画数据
          </button>
        </div>
        <div class="data-info">
          <span>当前数据量: <strong>{{ formattedCount }}</strong></span>
          <span v-if="loadTime" class="load-time">加载耗时: {{ loadTime }}ms</span>
          <span v-if="isAnimationMode" class="animation-indicator">
            🎬 动画模式
          </span>
        </div>
      </div>
      
      <div class="status-bar">
        <span>缩放级别: {{ currentZoom }}</span>
        <span>中心点: {{ currentCenter.lat.toFixed(4) }}, {{ currentCenter.lng.toFixed(4) }}</span>
        <span v-if="isAnimationMode">当前: {{ currentTimeLabel }}</span>
      </div>

      <div v-if="exportMessage" class="export-toast">
        {{ exportMessage }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import HeatmapLayer from './components/HeatmapLayer.vue'
import HeatmapLegend from './components/HeatmapLegend.vue'
import HeatmapControlPanel from './components/HeatmapControlPanel.vue'
import HeatmapInfoPopup from './components/HeatmapInfoPopup.vue'
import AnimationControlPanel from './components/AnimationControlPanel.vue'
import RegionSelector from './components/RegionSelector.vue'
import { generateRandomPoints, generateClusterPoints, generateMillionPoints } from './utils/dataGenerator.js'
import { generateTemporalData } from './utils/temporalDataGenerator.js'

const heatmapRef = ref(null)
const mapWrapper = ref(null)
const mapInstance = ref(null)

const heatmapData = ref([])
const displayData = ref([])
const timeSeriesData = ref([])
const dataMode = ref('')
const isLoadingMillion = ref(false)
const loadTime = ref(0)

const center = ref([39.9042, 116.4074])
const zoom = ref(11)
const currentZoom = ref(11)
const currentCenter = ref({ lat: 39.9042, lng: 116.4074 })

const isAnimationMode = ref(false)
const currentTimeLabel = ref('--:--')

const config = reactive({
  radius: 25,
  maxOpacity: 0.8,
  minOpacity: 0.1,
  blur: 0.85,
  gradient: {
    0.4: 'blue',
    0.6: 'cyan',
    0.7: 'lime',
    0.8: 'yellow',
    1.0: 'red'
  },
  showLegend: true,
  enableClickQuery: true
})

const popupVisible = ref(false)
const clickInfo = ref(null)
const popupPosition = ref({ x: 0, y: 0 })

const exportMessage = ref('')

const maxValue = computed(() => {
  if (displayData.value.length === 0) return 100
  return Math.max(...displayData.value.map(p => p.value || 0))
})

const formattedCount = computed(() => {
  const count = displayData.value.length
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1) + ' 百万'
  } else if (count >= 10000) {
    return (count / 10000).toFixed(1) + ' 万'
  }
  return count.toLocaleString()
})

const handleConfigChange = (newConfig) => {
  Object.assign(config, newConfig)
}

const handleHeatmapClick = (info) => {
  if (!info || info.heatValue == null) return
  
  clickInfo.value = info
  
  if (mapWrapper.value) {
    const map = heatmapRef.value?.getMap()
    if (map) {
      const point = map.latLngToContainerPoint([info.lat, info.lng])
      popupPosition.value = {
        x: point.x,
        y: point.y
      }
    }
  }
  
  popupVisible.value = true
}

const handleZoomChange = (newZoom) => {
  currentZoom.value = newZoom
}

const handleMoveEnd = (info) => {
  currentZoom.value = info.zoom
  currentCenter.value = {
    lat: info.center.lat,
    lng: info.center.lng
  }
}

const loadThousandPoints = () => {
  const start = performance.now()
  dataMode.value = 'thousand'
  isAnimationMode.value = false
  timeSeriesData.value = []
  heatmapData.value = generateClusterPoints(20, 500, center.value[0], center.value[1], 0.8)
  displayData.value = heatmapData.value
  loadTime.value = Math.round(performance.now() - start)
}

const loadHundredThousandPoints = () => {
  const start = performance.now()
  dataMode.value = 'hundred-thousand'
  isAnimationMode.value = false
  timeSeriesData.value = []
  heatmapData.value = generateClusterPoints(50, 2000, center.value[0], center.value[1], 1.5)
  displayData.value = heatmapData.value
  loadTime.value = Math.round(performance.now() - start)
}

const loadMillionPoints = async () => {
  const start = performance.now()
  dataMode.value = 'million'
  isAnimationMode.value = false
  timeSeriesData.value = []
  isLoadingMillion.value = true
  
  try {
    heatmapData.value = await generateMillionPoints(center.value[0], center.value[1])
    displayData.value = heatmapData.value
    loadTime.value = Math.round(performance.now() - start)
  } finally {
    isLoadingMillion.value = false
  }
}

const loadAnimationData = () => {
  const start = performance.now()
  dataMode.value = 'animation'
  timeSeriesData.value = generateTemporalData(5000, 24, center.value[0], center.value[1], 0.6)
  isAnimationMode.value = true
  displayData.value = timeSeriesData.value[0]?.data || []
  loadTime.value = Math.round(performance.now() - start)
}

const handleAnimationDataUpdate = (data) => {
  displayData.value = data
}

const handleTimeChange = (info) => {
  currentTimeLabel.value = info.timeLabel
}

const handleDataLoaded = () => {
}

const handleSelectionChange = (info) => {
}

const handleExport = (info) => {
  exportMessage.value = `✅ 已导出 ${info.count.toLocaleString()} 条数据 (${info.type.toUpperCase()})`
  setTimeout(() => {
    exportMessage.value = ''
  }, 3000)
}

onMounted(async () => {
  await nextTick()
  loadThousandPoints()
  
  setTimeout(() => {
    mapInstance.value = heatmapRef.value?.getMap()
  }, 100)
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
}

.map-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.data-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 16px;
  min-width: 220px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.data-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.data-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.divider {
  height: 1px;
  background: #e0e0e0;
  margin: 12px 0;
}

.data-btn {
  padding: 10px 16px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  transition: all 0.2s;
}

.data-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.data-btn.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.data-btn.million-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.data-btn.million-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.data-btn.million-btn.active {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
}

.data-btn.animate-btn {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  border-color: transparent;
}

.data-btn.animate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(240, 147, 251, 0.4);
}

.data-btn.animate-btn.active {
  background: linear-gradient(135deg, #d87fe5 0%, #e04d60 100%);
}

.data-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.data-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.data-info strong {
  color: #667eea;
  font-weight: 600;
}

.load-time {
  color: #999;
}

.animation-indicator {
  color: #f5576c;
  font-weight: 600;
}

.status-bar {
  position: absolute;
  bottom: 20px;
  left: 20px;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 12px;
  color: #666;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.status-bar span {
  margin-right: 20px;
}

.status-bar span:last-child {
  margin-right: 0;
}

.export-toast {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2000;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  animation: fadeInOut 3s ease;
}

@keyframes fadeInOut {
  0% { opacity: 0; transform: translate(-50%, -50%) scale(0.9); }
  10% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  80% { opacity: 1; }
  100% { opacity: 0; }
}
</style>
