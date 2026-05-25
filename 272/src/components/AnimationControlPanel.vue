<template>
  <div class="animation-panel" :class="{ collapsed: isCollapsed }">
    <div class="panel-header" @click="toggleCollapse">
      <span class="panel-title">
        <span class="icon">⏱</span>
        时间动画
      </span>
      <span class="collapse-icon">{{ isCollapsed ? '展开 ▼' : '收起 ▲' }}</span>
    </div>
    
    <div class="panel-content" v-show="!isCollapsed">
      <div class="mode-selector">
        <button 
          class="mode-btn" 
          :class="{ active: !isAnimationMode }"
          @click="setStaticMode"
        >
          静态模式
        </button>
        <button 
          class="mode-btn" 
          :class="{ active: isAnimationMode }"
          @click="setAnimationMode"
        >
          动画模式
        </button>
      </div>

      <div v-if="isAnimationMode" class="animation-controls">
        <div class="time-display">
          <span class="time-label">当前时间:</span>
          <span class="time-value">{{ currentTimeLabel }}</span>
        </div>

        <div class="progress-bar-container">
          <div class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: (animationProgress * 100) + '%' }"
            ></div>
          </div>
          <input 
            type="range" 
            v-model.number="animationProgress"
            min="0" 
            max="1" 
            step="0.01"
            class="progress-slider"
            @input="onProgressChange"
          />
        </div>

        <div class="time-markers">
          <span v-for="(marker, idx) in timeMarkers" :key="idx" class="time-marker">
            {{ marker }}
          </span>
        </div>

        <div class="control-buttons">
          <button class="ctrl-btn" @click="skipToStart" title="开始">
            ⏮
          </button>
          <button class="ctrl-btn play-btn" @click="togglePlay" :title="isPlaying ? '暂停' : '播放'">
            {{ isPlaying ? '⏸' : '▶' }}
          </button>
          <button class="ctrl-btn" @click="skipToEnd" title="结束">
            ⏭
          </button>
        </div>

        <div class="speed-control">
          <span class="speed-label">速度:</span>
          <select v-model="playbackSpeed" class="speed-select" @change="updateSpeed">
            <option :value="0.25">0.25x</option>
            <option :value="0.5">0.5x</option>
            <option :value="1">1x</option>
            <option :value="2">2x</option>
            <option :value="4">4x</option>
          </select>
        </div>

        <div class="interpolation-control">
          <label class="control-label">
            平滑过渡
            <input 
              type="checkbox" 
              v-model="useInterpolation"
              class="control-checkbox"
              @change="toggleInterpolation"
            />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  timeSeriesData: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'timeChange', 'dataUpdate'])

const isCollapsed = ref(false)
const isAnimationMode = ref(false)
const isPlaying = ref(false)
const animationProgress = ref(0)
const playbackSpeed = ref(1)
const useInterpolation = ref(true)

let animationFrameId = null
let lastFrameTime = 0

const currentTimeIndex = computed(() => {
  if (!props.timeSeriesData || props.timeSeriesData.length === 0) return 0
  return Math.floor(animationProgress.value * (props.timeSeriesData.length - 1))
})

const currentTimeLabel = computed(() => {
  if (!props.timeSeriesData || props.timeSeriesData.length === 0) return '--:--'
  return props.timeSeriesData[currentTimeIndex.value]?.timeLabel || '--:--'
})

const timeMarkers = computed(() => {
  if (!props.timeSeriesData || props.timeSeriesData.length === 0) return []
  
  const markers = []
  const step = Math.max(1, Math.floor(props.timeSeriesData.length / 4))
  
  for (let i = 0; i < props.timeSeriesData.length; i += step) {
    markers.push(props.timeSeriesData[i].timeLabel)
  }
  
  return markers
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const setStaticMode = () => {
  stopAnimation()
  isAnimationMode.value = false
  emit('update:modelValue', false)
}

const setAnimationMode = () => {
  isAnimationMode.value = true
  emit('update:modelValue', true)
  emitDataUpdate()
}

const togglePlay = () => {
  if (isPlaying.value) {
    stopAnimation()
  } else {
    startAnimation()
  }
}

const startAnimation = () => {
  if (isPlaying.value) return
  
  isPlaying.value = true
  lastFrameTime = performance.now()
  animate()
}

const stopAnimation = () => {
  isPlaying.value = false
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
}

const animate = () => {
  if (!isPlaying.value) return
  
  const now = performance.now()
  const delta = (now - lastFrameTime) / 1000
  lastFrameTime = now
  
  const step = 0.1 * playbackSpeed.value * delta
  animationProgress.value += step
  
  if (animationProgress.value >= 1) {
    animationProgress.value = 0
  }
  
  emitDataUpdate()
  emit('timeChange', {
    progress: animationProgress.value,
    timeIndex: currentTimeIndex.value,
    timeLabel: currentTimeLabel.value
  })
  
  animationFrameId = requestAnimationFrame(animate)
}

const skipToStart = () => {
  animationProgress.value = 0
  emitDataUpdate()
}

const skipToEnd = () => {
  animationProgress.value = 1
  emitDataUpdate()
}

const onProgressChange = () => {
  emitDataUpdate()
  emit('timeChange', {
    progress: animationProgress.value,
    timeIndex: currentTimeIndex.value,
    timeLabel: currentTimeLabel.value
  })
}

const updateSpeed = () => {
}

const toggleInterpolation = () => {
  emitDataUpdate()
}

const emitDataUpdate = () => {
  if (!props.timeSeriesData || props.timeSeriesData.length === 0) return
  
  let data
  if (useInterpolation.value) {
    data = interpolateData(props.timeSeriesData, animationProgress.value)
  } else {
    data = props.timeSeriesData[currentTimeIndex.value]?.data || []
  }
  
  emit('dataUpdate', data)
}

const interpolateData = (timeSeriesData, progress) => {
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
    const key = `${point.lat.toFixed(4)}_${point.lng.toFixed(4)}`
    pointMap.set(key, {
      lat: point.lat,
      lng: point.lng,
      lowerValue: point.value,
      upperValue: 0
    })
  }
  
  for (let i = 0; i < upperData.length; i++) {
    const point = upperData[i]
    const key = `${point.lat.toFixed(4)}_${point.lng.toFixed(4)}`
    
    if (pointMap.has(key)) {
      const entry = pointMap.get(key)
      entry.upperValue = point.value
    } else {
      pointMap.set(key, {
        lat: point.lat,
        lng: point.lng,
        lowerValue: 0,
        upperValue: point.value
      })
    }
  }
  
  const result = []
  pointMap.forEach((entry) => {
    const value = entry.lowerValue * (1 - interpFactor) + entry.upperValue * interpFactor
    if (value > 1) {
      result.push({
        lat: entry.lat,
        lng: entry.lng,
        value: Math.round(value)
      })
    }
  })
  
  return result
}

watch(() => props.timeSeriesData, () => {
  animationProgress.value = 0
  if (isAnimationMode.value) {
    emitDataUpdate()
  }
}, { deep: false })

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    setAnimationMode()
  } else {
    setStaticMode()
  }
})

onUnmounted(() => {
  stopAnimation()
})

defineExpose({
  startAnimation,
  stopAnimation,
  isPlaying,
  currentTimeLabel
})
</script>

<style scoped>
.animation-panel {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  min-width: 380px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  border-radius: 12px 12px 0 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon {
  font-size: 18px;
}

.collapse-icon {
  font-size: 12px;
  opacity: 0.9;
}

.panel-content {
  padding: 16px 20px;
}

.mode-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.mode-btn {
  flex: 1;
  padding: 8px 16px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  transition: all 0.2s;
}

.mode-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.mode-btn.active {
  border-color: #667eea;
  background: #667eea;
  color: white;
}

.animation-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.time-display {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.time-label {
  font-size: 13px;
  color: #666;
}

.time-value {
  font-size: 18px;
  font-weight: 600;
  color: #667eea;
}

.progress-bar-container {
  position: relative;
  height: 24px;
  display: flex;
  align-items: center;
}

.progress-bar {
  position: absolute;
  left: 0;
  right: 0;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  transition: width 0.1s linear;
}

.progress-slider {
  position: absolute;
  left: 0;
  right: 0;
  width: 100%;
  height: 24px;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  cursor: pointer;
  z-index: 1;
}

.progress-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: #667eea;
  border: 3px solid white;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
}

.time-markers {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
  margin-top: -4px;
}

.control-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 4px;
}

.ctrl-btn {
  width: 44px;
  height: 44px;
  border: none;
  background: #f5f5f5;
  border-radius: 50%;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.ctrl-btn:hover {
  background: #e8e8e8;
  transform: scale(1.05);
}

.play-btn {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 22px;
}

.play-btn:hover {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%);
}

.speed-control {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.speed-label {
  font-size: 13px;
  color: #666;
}

.speed-select {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.interpolation-control {
  display: flex;
  justify-content: center;
}

.control-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
}

.control-checkbox {
  cursor: pointer;
}
</style>
