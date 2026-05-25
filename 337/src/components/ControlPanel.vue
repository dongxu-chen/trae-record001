<template>
  <div class="control-panel">
    <div class="panel-header">
      <h2>粒子特效编辑器</h2>
      <div class="preset-buttons">
        <button
          v-for="(preset, key) in presets"
          :key="key"
          :class="['preset-btn', { active: currentPreset === key }]"
          @click="$emit('load-preset', key)"
        >
          {{ preset.icon }} {{ preset.name }}
        </button>
      </div>
    </div>

    <div class="panel-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <div class="panel-content">
      <div v-show="activeTab === 'basic'" class="control-group">
        <h3>基础参数</h3>
        
        <div class="control-item">
          <label>粒子数量</label>
          <div class="range-control">
            <input
              type="range"
              :min="100"
              :max="10000"
              :step="100"
              v-model.number="localConfig.particleCount"
              @input="updateConfig"
            />
            <span class="value">{{ localConfig.particleCount }}</span>
          </div>
        </div>

        <div class="control-item">
          <label>发射速率</label>
          <div class="range-control">
            <input
              type="range"
              :min="1"
              :max="1000"
              :step="1"
              v-model.number="localConfig.emissionRate"
              @input="updateConfig"
            />
            <span class="value">{{ localConfig.emissionRate }}/s</span>
          </div>
        </div>

        <div class="control-item">
          <label>最大粒子数</label>
          <div class="range-control">
            <input
              type="range"
              :min="1000"
              :max="20000"
              :step="500"
              v-model.number="localConfig.maxParticles"
              @input="updateConfig"
            />
            <span class="value">{{ localConfig.maxParticles }}</span>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'physics'" class="control-group">
        <h3>物理参数</h3>

        <div class="control-item">
          <label>速度范围</label>
          <div class="dual-range">
            <div class="range-item">
              <span>最小</span>
              <input
                type="range"
                :min="0.1"
                :max="20"
                :step="0.1"
                v-model.number="localConfig.speed.min"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.speed.min.toFixed(1) }}</span>
            </div>
            <div class="range-item">
              <span>最大</span>
              <input
                type="range"
                :min="0.1"
                :max="20"
                :step="0.1"
                v-model.number="localConfig.speed.max"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.speed.max.toFixed(1) }}</span>
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>生命周期</label>
          <div class="dual-range">
            <div class="range-item">
              <span>最小</span>
              <input
                type="range"
                :min="0.1"
                :max="10"
                :step="0.1"
                v-model.number="localConfig.life.min"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.life.min.toFixed(1) }}s</span>
            </div>
            <div class="range-item">
              <span>最大</span>
              <input
                type="range"
                :min="0.1"
                :max="10"
                :step="0.1"
                v-model.number="localConfig.life.max"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.life.max.toFixed(1) }}s</span>
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>重力</label>
          <div class="vector-control">
            <div class="vector-item">
              <span>X</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.gravity.x"
                @input="updateConfig"
              />
            </div>
            <div class="vector-item">
              <span>Y</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.gravity.y"
                @input="updateConfig"
              />
            </div>
            <div class="vector-item">
              <span>Z</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.gravity.z"
                @input="updateConfig"
              />
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>发射方向</label>
          <div class="vector-control">
            <div class="vector-item">
              <span>X</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.direction.x"
                @input="updateConfig"
              />
            </div>
            <div class="vector-item">
              <span>Y</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.direction.y"
                @input="updateConfig"
              />
            </div>
            <div class="vector-item">
              <span>Z</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.direction.z"
                @input="updateConfig"
              />
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>扩散角度</label>
          <div class="range-control">
            <input
              type="range"
              :min="0"
              :max="2"
              :step="0.01"
              v-model.number="localConfig.spread"
              @input="updateConfig"
            />
            <span class="value">{{ localConfig.spread.toFixed(2) }}</span>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'appearance'" class="control-group">
        <h3>外观参数</h3>

        <div class="control-item">
          <label>大小范围</label>
          <div class="dual-range">
            <div class="range-item">
              <span>最小</span>
              <input
                type="range"
                :min="0.01"
                :max="3"
                :step="0.01"
                v-model.number="localConfig.size.min"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.size.min.toFixed(2) }}</span>
            </div>
            <div class="range-item">
              <span>最大</span>
              <input
                type="range"
                :min="0.01"
                :max="3"
                :step="0.01"
                v-model.number="localConfig.size.max"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.size.max.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>颜色</label>
          <div class="color-control">
            <div class="color-item">
              <span>起始</span>
              <input
                type="color"
                v-model="localConfig.color.start"
                @input="updateConfig"
              />
              <span class="color-value">{{ localConfig.color.start }}</span>
            </div>
            <div class="color-item">
              <span>结束</span>
              <input
                type="color"
                v-model="localConfig.color.end"
                @input="updateConfig"
              />
              <span class="color-value">{{ localConfig.color.end }}</span>
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>旋转速度</label>
          <div class="dual-range">
            <div class="range-item">
              <span>最小</span>
              <input
                type="range"
                :min="0"
                :max="10"
                :step="0.1"
                v-model.number="localConfig.rotationSpeed.min"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.rotationSpeed.min.toFixed(1) }}</span>
            </div>
            <div class="range-item">
              <span>最大</span>
              <input
                type="range"
                :min="0"
                :max="10"
                :step="0.1"
                v-model.number="localConfig.rotationSpeed.max"
                @input="updateConfig"
              />
              <span class="value">{{ localConfig.rotationSpeed.max.toFixed(1) }}</span>
            </div>
          </div>
        </div>

        <div class="control-item">
          <label>混合模式</label>
          <select v-model="localConfig.blending" @change="updateConfig">
            <option value="additive">加法混合</option>
            <option value="normal">正常混合</option>
          </select>
        </div>
      </div>

      <div v-show="activeTab === 'emitter'" class="control-group">
        <h3>发射器参数</h3>

        <div class="control-item">
          <label>发射器形状</label>
          <select v-model="localConfig.emitterShape" @change="updateConfig">
            <option value="point">点</option>
            <option value="circle">圆形</option>
            <option value="sphere">球体</option>
            <option value="box">立方体</option>
          </select>
        </div>

        <div class="control-item">
          <label>发射器半径</label>
          <div class="range-control">
            <input
              type="range"
              :min="0.1"
              :max="30"
              :step="0.1"
              v-model.number="localConfig.emitterRadius"
              @input="updateConfig"
            />
            <span class="value">{{ localConfig.emitterRadius.toFixed(1) }}</span>
          </div>
        </div>

        <div class="control-item">
          <label>发射器位置</label>
          <div class="vector-control">
            <div class="vector-item">
              <span>X</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.emitterPosition.x"
                @input="updateConfig"
              />
            </div>
            <div class="vector-item">
              <span>Y</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.emitterPosition.y"
                @input="updateConfig"
              />
            </div>
            <div class="vector-item">
              <span>Z</span>
              <input
                type="number"
                :step="0.1"
                v-model.number="localConfig.emitterPosition.z"
                @input="updateConfig"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'animation'" class="control-group">
        <h3>关键帧动画</h3>

        <div class="control-item">
          <label>预设动画</label>
          <div class="animation-buttons">
            <button
              v-for="anim in animations"
              :key="anim.key"
              class="anim-btn"
              :class="{ active: selectedAnimation === anim.key }"
              @click="selectAnimation(anim.key)"
            >
              {{ anim.icon }} {{ anim.label }}
            </button>
          </div>
        </div>

        <div class="control-item">
          <label>缓动曲线</label>
          <div class="ease-options">
            <button
              v-for="ease in easePresets"
              :key="ease.key"
              :class="['ease-btn', { active: selectedEase === ease.key && !useCustomBezier }]"
              @click="selectEase(ease.key)"
            >
              {{ ease.label }}
            </button>
            <button
              :class="['ease-btn', { active: useCustomBezier }]"
              @click="toggleCustomBezier"
            >
              自定义
            </button>
          </div>
        </div>

        <div class="control-item" v-if="useCustomBezier">
          <BezierEditor
            v-model="bezierParams"
            @apply="applyBezierEase"
          />
        </div>

        <div class="control-item">
          <label>动画控制</label>
          <div class="animation-controls">
            <button @click="playAnimation">▶ 播放</button>
            <button @click="$emit('animation-pause')">⏸ 暂停</button>
            <button @click="$emit('animation-restart')">↻ 重放</button>
            <button @click="$emit('animation-stop')">⏹ 停止</button>
          </div>
        </div>

        <div class="control-item">
          <label>使用自定义曲线播放</label>
          <div class="animation-controls">
            <button
              v-for="anim in animations"
              :key="'bezier-' + anim.key"
              class="anim-btn small"
              @click="playAnimationWithBezier(anim.key)"
            >
              {{ anim.icon }} {{ anim.label }}
            </button>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'interaction'" class="control-group">
        <InteractionPanel
          :mouse-interactor="mouseInteractor"
          @mouse-enabled-change="onMouseEnabledChange"
          @audio-enabled-change="onAudioEnabledChange"
          @audio-reactor-created="onAudioReactorCreated"
        />
      </div>

      <div v-show="activeTab === 'market'" class="control-group">
        <TemplateMarket
          @apply-template="applyTemplate"
          @save-current="saveCurrentTemplate"
        />
      </div>
    </div>

    <div class="panel-footer">
      <div class="playback-controls">
        <button @click="$emit('play')" :class="{ active: isPlaying }">▶ 播放</button>
        <button @click="$emit('pause')" :class="{ active: !isPlaying }">⏸ 暂停</button>
        <button @click="$emit('reset')">↻ 重置</button>
      </div>
      <div class="io-controls">
        <label class="file-input-label">
          📂 导入
          <input type="file" accept=".json" @change="handleImport" style="display: none" />
        </label>
        <button @click="$emit('export')">💾 导出</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { particlePresets } from '../presets/particlePresets.js'
import { loadConfigFromFile } from '../utils/ConfigManager.js'
import BezierEditor from './BezierEditor.vue'
import InteractionPanel from './InteractionPanel.vue'
import TemplateMarket from './TemplateMarket.vue'

const props = defineProps({
  config: {
    type: Object,
    required: true
  },
  currentPreset: {
    type: String,
    default: 'fire'
  },
  isPlaying: {
    type: Boolean,
    default: true
  },
  mouseInteractor: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'load-preset',
  'update-config',
  'play',
  'pause',
  'reset',
  'export',
  'import',
  'play-animation',
  'animation-play',
  'animation-pause',
  'animation-restart',
  'animation-stop',
  'play-animation-with-bezier',
  'apply-bezier-ease',
  'apply-template',
  'save-template'
])

const activeTab = ref('basic')
const presets = particlePresets
const selectedAnimation = ref('pulse')
const selectedEase = ref('power2.inOut')
const useCustomBezier = ref(false)
const bezierParams = ref({ x1: 0.25, y1: 0.1, x2: 0.25, y2: 1 })

const tabs = [
  { key: 'basic', label: '基础', icon: '⚙️' },
  { key: 'physics', label: '物理', icon: '🎯' },
  { key: 'appearance', label: '外观', icon: '🎨' },
  { key: 'emitter', label: '发射器', icon: '💫' },
  { key: 'animation', label: '动画', icon: '🎬' },
  { key: 'interaction', label: '交互', icon: '🖱️' },
  { key: 'market', label: '市场', icon: '🛒' }
]

const animations = [
  { key: 'pulse', label: '脉冲', icon: '💓' },
  { key: 'colorShift', label: '变色', icon: '🌈' },
  { key: 'explosion', label: '爆炸', icon: '💥' },
  { key: 'spiral', label: '螺旋', icon: '🌀' }
]

const easePresets = [
  { key: 'power1.inOut', label: 'Power1' },
  { key: 'power2.inOut', label: 'Power2' },
  { key: 'power3.inOut', label: 'Power3' },
  { key: 'power4.inOut', label: 'Power4' },
  { key: 'elastic.out', label: 'Elastic' },
  { key: 'back.inOut', label: 'Back' }
]

const localConfig = ref(JSON.parse(JSON.stringify(props.config)))

function selectAnimation(key) {
  selectedAnimation.value = key
}

function selectEase(key) {
  selectedEase.value = key
  useCustomBezier.value = false
}

function toggleCustomBezier() {
  useCustomBezier.value = !useCustomBezier.value
}

function playAnimation() {
  emit('play-animation', selectedAnimation.value)
}

function applyBezierEase(params) {
  emit('apply-bezier-ease', params)
}

function playAnimationWithBezier(animKey) {
  emit('play-animation-with-bezier', {
    animation: animKey,
    bezier: bezierParams.value
  })
}

watch(
  () => props.config,
  (newConfig) => {
    localConfig.value = JSON.parse(JSON.stringify(newConfig))
  },
  { deep: true }
)

function updateConfig() {
  emit('update-config', JSON.parse(JSON.stringify(localConfig.value)))
}

async function handleImport(event) {
  const file = event.target.files[0]
  if (file) {
    try {
      const result = await loadConfigFromFile(file)
      emit('import', result.data)
    } catch (error) {
      alert('导入失败: ' + error.message)
    }
  }
  event.target.value = ''
}

function onMouseEnabledChange(enabled) {
  console.log('Mouse interaction:', enabled)
}

function onAudioEnabledChange(enabled) {
  console.log('Audio reactor:', enabled)
}

function onAudioReactorCreated(reactor) {
  emit('audio-reactor-created', reactor)
}

function applyTemplate(template) {
  emit('apply-template', template)
}

function saveCurrentTemplate() {
  const name = prompt('输入模板名称:', '我的特效')
  if (name) {
    emit('save-template', {
      name,
      config: JSON.parse(JSON.stringify(localConfig.value))
    })
  }
}
</script>

<style scoped>
.control-panel {
  width: 380px;
  height: 100%;
  background: rgba(15, 15, 25, 0.95);
  backdrop-filter: blur(10px);
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  color: #fff;
}

.panel-header {
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-header h2 {
  margin: 0 0 15px 0;
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.preset-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.preset-btn {
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.preset-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(102, 126, 234, 0.5);
}

.preset-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.panel-tabs {
  display: flex;
  padding: 10px 20px;
  gap: 5px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
}

.tab-btn {
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  color: #fff;
  background: rgba(102, 126, 234, 0.3);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: transparent;
}

.panel-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.control-group {
  margin-bottom: 20px;
}

.control-group h3 {
  margin: 0 0 15px 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.control-item {
  margin-bottom: 18px;
}

.control-item label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.range-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-control input[type='range'] {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
}

.range-control input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.2s;
}

.range-control input[type='range']::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.range-control .value {
  min-width: 60px;
  text-align: right;
  font-size: 13px;
  font-family: 'Monaco', 'Consolas', monospace;
  color: #667eea;
}

.dual-range {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.range-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.range-item span {
  min-width: 35px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.range-item input[type='range'] {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  outline: none;
}

.range-item input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
}

.range-item .value {
  min-width: 50px;
  text-align: right;
  font-size: 12px;
  font-family: 'Monaco', 'Consolas', monospace;
  color: #667eea;
}

.vector-control {
  display: flex;
  gap: 10px;
}

.vector-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.vector-item span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 600;
}

.vector-item input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.vector-item input:focus {
  border-color: #667eea;
}

.color-control {
  display: flex;
  gap: 15px;
}

.color-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.color-item span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.color-item input[type='color'] {
  width: 100%;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}

.color-item input[type='color']::-webkit-color-swatch-wrapper {
  padding: 0;
}

.color-item input[type='color']::-webkit-color-swatch {
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

.color-value {
  font-size: 11px;
  font-family: 'Monaco', 'Consolas', monospace;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
}

select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s;
}

select:focus {
  border-color: #667eea;
}

.animation-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.anim-btn {
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.anim-btn:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

.animation-controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.animation-controls button {
  flex: 1;
  min-width: 70px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.animation-controls button:hover {
  background: rgba(102, 126, 234, 0.3);
}

.panel-footer {
  padding: 15px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.playback-controls,
.io-controls {
  display: flex;
  gap: 8px;
}

.playback-controls button,
.io-controls button,
.file-input-label {
  flex: 1;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  text-align: center;
}

.playback-controls button:hover,
.io-controls button:hover,
.file-input-label:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

.playback-controls button.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.anim-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.anim-btn.small {
  padding: 8px;
  font-size: 11px;
}

.ease-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ease-btn {
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.ease-btn:hover {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.4);
  color: #fff;
}

.ease-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: #fff;
}
</style>
