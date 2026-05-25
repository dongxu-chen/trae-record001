<template>
  <div class="control-panel" :class="{ collapsed: isCollapsed }">
    <div class="panel-header" @click="toggleCollapse">
      <span class="panel-title">{{ title }}</span>
      <span class="collapse-icon">{{ isCollapsed ? '展开 ▼' : '收起 ▲' }}</span>
    </div>
    
    <div class="panel-content" v-show="!isCollapsed">
      <div class="control-group">
        <label class="control-label">
          半径 ({{ radius }})
        </label>
        <input 
          type="range" 
          v-model.number="radius" 
          :min="minRadius" 
          :max="maxRadius" 
          step="1"
          class="control-slider"
          @input="emitChange"
        />
      </div>

      <div class="control-group">
        <label class="control-label">
          最大透明度 ({{ maxOpacity }})
        </label>
        <input 
          type="range" 
          v-model.number="maxOpacity" 
          min="0" 
          max="1" 
          step="0.05"
          class="control-slider"
          @input="emitChange"
        />
      </div>

      <div class="control-group">
        <label class="control-label">
          最小透明度 ({{ minOpacity }})
        </label>
        <input 
          type="range" 
          v-model.number="minOpacity" 
          min="0" 
          max="1" 
          step="0.05"
          class="control-slider"
          @input="emitChange"
        />
      </div>

      <div class="control-group">
        <label class="control-label">
          模糊度 ({{ blur }})
        </label>
        <input 
          type="range" 
          v-model.number="blur" 
          min="0" 
          max="1" 
          step="0.05"
          class="control-slider"
          @input="emitChange"
        />
      </div>

      <div class="control-group">
        <label class="control-label">配色方案</label>
        <div class="preset-colors">
          <div 
            v-for="(preset, index) in colorPresets" 
            :key="index"
            class="color-preset"
            :class="{ active: isPresetActive(preset.gradient) }"
            @click="applyPreset(preset)"
          >
            <div 
              class="preset-preview"
              :style="{ background: getPreviewGradient(preset.gradient) }"
            ></div>
            <span class="preset-name">{{ preset.name }}</span>
          </div>
        </div>
      </div>

      <div class="control-group">
        <label class="control-label">
          显示图例
          <input 
            type="checkbox" 
            v-model="showLegend"
            class="control-checkbox"
            @change="emitChange"
          />
        </label>
      </div>

      <div class="control-group">
        <label class="control-label">
          点击查询热力值
          <input 
            type="checkbox" 
            v-model="enableClickQuery"
            class="control-checkbox"
            @change="emitChange"
          />
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '热力图配置'
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
    default: () => ({})
  },
  showLegend: {
    type: Boolean,
    default: true
  },
  enableClickQuery: {
    type: Boolean,
    default: true
  },
  minRadius: {
    type: Number,
    default: 5
  },
  maxRadius: {
    type: Number,
    default: 100
  }
})

const emit = defineEmits(['change'])

const isCollapsed = ref(false)
const radius = ref(props.radius)
const maxOpacity = ref(props.maxOpacity)
const minOpacity = ref(props.minOpacity)
const blur = ref(props.blur)
const showLegend = ref(props.showLegend)
const enableClickQuery = ref(props.enableClickQuery)

const colorPresets = [
  {
    name: '经典热力',
    gradient: { 0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red' }
  },
  {
    name: '蓝红渐变',
    gradient: { 0.0: '#0000ff', 0.5: '#ff00ff', 1.0: '#ff0000' }
  },
  {
    name: '绿色系',
    gradient: { 0.2: '#edf8e9', 0.4: '#bae4b3', 0.6: '#74c476', 0.8: '#31a354', 1.0: '#006d2c' }
  },
  {
    name: '紫色系',
    gradient: { 0.2: '#f2f0f7', 0.4: '#cbc9e2', 0.6: '#9e9ac8', 0.8: '#756bb1', 1.0: '#54278f' }
  },
  {
    name: '橙色系',
    gradient: { 0.2: '#feedde', 0.4: '#fdbe85', 0.6: '#fd8d3c', 0.8: '#e6550d', 1.0: '#a63603' }
  },
  {
    name: '灰度',
    gradient: { 0.0: '#ffffff', 0.5: '#888888', 1.0: '#000000' }
  }
]

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const emitChange = () => {
  emit('change', {
    radius: radius.value,
    maxOpacity: maxOpacity.value,
    minOpacity: minOpacity.value,
    blur: blur.value,
    showLegend: showLegend.value,
    enableClickQuery: enableClickQuery.value
  })
}

const isPresetActive = (presetGradient) => {
  const currentKeys = Object.keys(props.gradient).sort()
  const presetKeys = Object.keys(presetGradient).sort()
  
  if (currentKeys.length !== presetKeys.length) return false
  
  return currentKeys.every((key, i) => 
    Math.abs(parseFloat(key) - parseFloat(presetKeys[i])) < 0.001 &&
    props.gradient[key] === presetGradient[presetKeys[i]]
  )
}

const getPreviewGradient = (gradient) => {
  const stops = Object.entries(gradient)
    .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))
    .map(([stop, color]) => `${color} ${parseFloat(stop) * 100}%`)
    .join(', ')
  
  return `linear-gradient(to right, ${stops})`
}

const applyPreset = (preset) => {
  emit('change', {
    radius: radius.value,
    maxOpacity: maxOpacity.value,
    minOpacity: minOpacity.value,
    blur: blur.value,
    gradient: preset.gradient,
    showLegend: showLegend.value,
    enableClickQuery: enableClickQuery.value
  })
}

watch(() => props, (newProps) => {
  radius.value = newProps.radius
  maxOpacity.value = newProps.maxOpacity
  minOpacity.value = newProps.minOpacity
  blur.value = newProps.blur
  showLegend.value = newProps.showLegend
  enableClickQuery.value = newProps.enableClickQuery
}, { deep: true })
</script>

<style scoped>
.control-panel {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 260px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  user-select: none;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
}

.collapse-icon {
  font-size: 12px;
  opacity: 0.9;
}

.panel-content {
  padding: 16px;
}

.control-group {
  margin-bottom: 16px;
}

.control-group:last-child {
  margin-bottom: 0;
}

.control-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
  cursor: pointer;
}

.control-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e0e0e0;
  border-radius: 3px;
  outline: none;
}

.control-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: #667eea;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.control-slider::-webkit-slider-thumb:hover {
  transform: scale(1.1);
}

.control-checkbox {
  margin-left: 8px;
  cursor: pointer;
}

.preset-colors {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.color-preset {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.color-preset:hover {
  background: #f5f5f5;
}

.color-preset.active {
  border-color: #667eea;
  background: #f0f3ff;
}

.preset-preview {
  width: 100%;
  height: 20px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.preset-name {
  font-size: 11px;
  color: #666;
}
</style>
