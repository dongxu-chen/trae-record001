<template>
  <Transition name="fade">
    <div 
      v-if="visible && info" 
      class="info-popup"
      :style="popupStyle"
    >
      <div class="popup-header">
        <span class="popup-title">热力值信息</span>
        <button class="popup-close" @click="$emit('close')">×</button>
      </div>
      <div class="popup-content">
        <div class="info-row">
          <span class="info-label">纬度:</span>
          <span class="info-value">{{ info.lat?.toFixed(6) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">经度:</span>
          <span class="info-value">{{ info.lng?.toFixed(6) }}</span>
        </div>
        <div class="info-row heat-row">
          <span class="info-label">热力值:</span>
          <span class="info-value heat-value" :style="{ color: heatColor }">
            {{ formattedHeatValue }}
          </span>
        </div>
        <div class="heat-bar">
          <div 
            class="heat-fill" 
            :style="{ 
              width: heatPercentage + '%',
              background: heatColor 
            }"
          ></div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  info: {
    type: Object,
    default: null
  },
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0 })
  },
  maxValue: {
    type: Number,
    default: 100
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
  }
})

defineEmits(['close'])

const popupStyle = computed(() => ({
  left: props.position.x + 'px',
  top: props.position.y + 'px'
}))

const heatPercentage = computed(() => {
  if (!props.info?.heatValue) return 0
  return Math.min((props.info.heatValue / props.maxValue) * 100, 100)
})

const formattedHeatValue = computed(() => {
  if (props.info?.heatValue == null) return '无数据'
  return props.info.heatValue.toFixed(2)
})

const heatColor = computed(() => {
  const percentage = heatPercentage.value / 100
  const gradientStops = Object.entries(props.gradient)
    .map(([stop, color]) => ({ stop: parseFloat(stop), color }))
    .sort((a, b) => a.stop - b.stop)
  
  if (percentage <= gradientStops[0].stop) {
    return gradientStops[0].color
  }
  
  if (percentage >= gradientStops[gradientStops.length - 1].stop) {
    return gradientStops[gradientStops.length - 1].color
  }
  
  for (let i = 0; i < gradientStops.length - 1; i++) {
    if (percentage >= gradientStops[i].stop && percentage <= gradientStops[i + 1].stop) {
      const range = gradientStops[i + 1].stop - gradientStops[i].stop
      const t = (percentage - gradientStops[i].stop) / range
      return interpolateColor(gradientStops[i].color, gradientStops[i + 1].color, t)
    }
  }
  
  return gradientStops[gradientStops.length - 1].color
})

const interpolateColor = (color1, color2, t) => {
  const parseColor = (color) => {
    const canvas = document.createElement('canvas')
    canvas.width = 1
    canvas.height = 1
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = color
    ctx.fillRect(0, 0, 1, 1)
    const data = ctx.getImageData(0, 0, 1, 1).data
    return { r: data[0], g: data[1], b: data[2] }
  }
  
  const c1 = parseColor(color1)
  const c2 = parseColor(color2)
  
  const r = Math.round(c1.r + (c2.r - c1.r) * t)
  const g = Math.round(c1.g + (c2.g - c1.g) * t)
  const b = Math.round(c1.b + (c2.b - c1.b) * t)
  
  return `rgb(${r}, ${g}, ${b})`
}
</script>

<style scoped>
.info-popup {
  position: absolute;
  z-index: 1001;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  min-width: 200px;
  transform: translate(-50%, -100%) translateY(-10px);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.info-popup::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid rgba(255, 255, 255, 0.98);
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid #eee;
}

.popup-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.popup-close {
  background: none;
  border: none;
  font-size: 20px;
  color: #999;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.popup-close:hover {
  color: #333;
}

.popup-content {
  padding: 12px 14px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-row:last-child {
  margin-bottom: 10px;
}

.info-label {
  color: #666;
}

.info-value {
  color: #333;
  font-weight: 500;
}

.heat-value {
  font-size: 16px;
  font-weight: 600;
}

.heat-bar {
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.heat-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -100%) translateY(-20px);
}
</style>
