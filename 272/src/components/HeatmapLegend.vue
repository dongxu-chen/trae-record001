<template>
  <div class="heatmap-legend" :style="positionStyle">
    <div class="legend-header">
      <span class="legend-title">{{ title }}</span>
      <span class="legend-unit" v-if="unit">{{ unit }}</span>
    </div>
    <div class="gradient-bar" ref="gradientBar"></div>
    <div class="legend-labels">
      <span class="min-label">{{ formattedMin }}</span>
      <span class="max-label">{{ formattedMax }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'

const props = defineProps({
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
  minValue: {
    type: Number,
    default: 0
  },
  maxValue: {
    type: Number,
    default: 100
  },
  position: {
    type: String,
    default: 'bottomright',
    validator: (val) => ['topright', 'topleft', 'bottomright', 'bottomleft'].includes(val)
  },
  title: {
    type: String,
    default: '热力值'
  },
  unit: {
    type: String,
    default: ''
  },
  decimals: {
    type: Number,
    default: 0
  }
})

const gradientBar = ref(null)

const positionStyle = computed(() => {
  const styles = {
    position: 'absolute',
    zIndex: 1000,
    background: 'rgba(255, 255, 255, 0.95)',
    padding: '12px 16px',
    borderRadius: '8px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.15)',
    minWidth: '180px'
  }

  const positions = props.position.split(/(?=[lr])/)
  if (positions[0] === 'top') {
    styles.top = '20px'
  } else {
    styles.bottom = '20px'
  }
  if (positions[1] === 'right') {
    styles.right = '20px'
  } else {
    styles.left = '20px'
  }

  return styles
})

const formattedMin = computed(() => {
  return Number(props.minValue).toFixed(props.decimals)
})

const formattedMax = computed(() => {
  return Number(props.maxValue).toFixed(props.decimals)
})

const generateGradient = () => {
  if (!gradientBar.value) return

  const stops = Object.entries(props.gradient)
    .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))
    .map(([stop, color]) => `${color} ${parseFloat(stop) * 100}%`)
    .join(', ')

  gradientBar.value.style.background = `linear-gradient(to right, ${stops})`
}

watch(() => props.gradient, () => {
  generateGradient()
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    generateGradient()
  })
})
</script>

<style scoped>
.heatmap-legend {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.legend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.legend-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.legend-unit {
  font-size: 12px;
  color: #666;
}

.gradient-bar {
  height: 12px;
  border-radius: 6px;
  margin-bottom: 6px;
}

.legend-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}
</style>
