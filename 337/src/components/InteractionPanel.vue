<template>
  <div class="interaction-panel">
    <div class="panel-section">
      <div class="section-header">
        <h5>🖱️ 鼠标交互</h5>
        <label class="toggle-switch">
          <input type="checkbox" :checked="mouseEnabled" @change="toggleMouse" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div v-if="mouseEnabled" class="section-content">
        <div class="control-item">
          <label>交互模式</label>
          <div class="mode-buttons">
            <button
              v-for="mode in interactionModes"
              :key="mode.id"
              :class="['mode-btn', { active: mouseMode === mode.id }]"
              @click="setMouseMode(mode.id)"
            >
              {{ mode.icon }} {{ mode.name }}
            </button>
          </div>
        </div>

        <div class="control-item">
          <label>力度: {{ mouseStrength.toFixed(0) }}</label>
          <input
            type="range"
            min="10"
            max="200"
            step="5"
            v-model.number="mouseStrength"
            @input="updateMouseStrength"
          />
        </div>

        <div class="control-item">
          <label>半径: {{ mouseRadius.toFixed(1) }}</label>
          <input
            type="range"
            min="1"
            max="20"
            step="0.5"
            v-model.number="mouseRadius"
            @input="updateMouseRadius"
          />
        </div>

        <div class="hint">
          💡 点击或拖拽鼠标与粒子互动
        </div>
      </div>
    </div>

    <div class="panel-section">
      <div class="section-header">
        <h5>🎵 音频驱动</h5>
        <label class="toggle-switch">
          <input type="checkbox" :checked="audioEnabled" @change="toggleAudio" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div v-if="audioEnabled" class="section-content">
        <div class="control-item">
          <label>音频源</label>
          <div class="audio-sources">
            <button
              :class="['source-btn', { active: audioSource === 'mic' }]"
              @click="connectMicrophone"
            >
              🎤 麦克风
            </button>
            <label class="source-btn file-input-label">
              📁 音频文件
              <input type="file" accept="audio/*" @change="handleAudioFile" style="display: none" />
            </label>
          </div>
        </div>

        <div v-if="audioConnected" class="audio-controls">
          <div class="control-item">
            <label>灵敏度: {{ audioSensitivity.toFixed(1) }}</label>
            <input
              type="range"
              min="0.5"
              max="3"
              step="0.1"
              v-model.number="audioSensitivity"
              @input="updateSensitivity"
            />
          </div>

          <div class="audio-visualizer">
            <div class="freq-bars">
              <div class="freq-bar bass" :style="{ height: bassHeight }"></div>
              <div class="freq-bar mid" :style="{ height: midHeight }"></div>
              <div class="freq-bar treble" :style="{ height: trebleHeight }"></div>
            </div>
            <div class="freq-labels">
              <span>低频</span>
              <span>中频</span>
              <span>高频</span>
            </div>
          </div>

          <div class="reactive-params">
            <div class="param-item">
              <label>发射速率</label>
              <label class="mini-toggle">
                <input type="checkbox" :checked="reactiveParams.emissionRate.enabled" @change="toggleReactive('emissionRate')" />
                启用
              </label>
            </div>
            <div class="param-item">
              <label>粒子速度</label>
              <label class="mini-toggle">
                <input type="checkbox" :checked="reactiveParams.speed.enabled" @change="toggleReactive('speed')" />
                启用
              </label>
            </div>
            <div class="param-item">
              <label>粒子大小</label>
              <label class="mini-toggle">
                <input type="checkbox" :checked="reactiveParams.size.enabled" @change="toggleReactive('size')" />
                启用
              </label>
            </div>
          </div>

          <div v-if="audioElement" class="audio-player">
            <button @click="togglePlayback" class="play-btn">
              {{ isPlaying ? '⏸' : '▶' }}
            </button>
            <button @click="stopAudio" class="stop-btn">⏹</button>
          </div>
        </div>

        <div v-else class="audio-hint">
          💡 连接音频源以控制粒子动态
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { AudioReactor } from '../audio/AudioReactor.js'

const props = defineProps({
  mouseInteractor: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'mouse-enabled-change',
  'audio-enabled-change',
  'audio-reactor-created'
])

const mouseEnabled = ref(false)
const mouseMode = ref('repel')
const mouseStrength = ref(50)
const mouseRadius = ref(5)

const audioEnabled = ref(false)
const audioSource = ref(null)
const audioConnected = ref(false)
const audioSensitivity = ref(1.5)
const audioReactor = new AudioReactor()
const audioElement = ref(null)
const isPlaying = ref(false)

const bass = ref(0)
const mid = ref(0)
const treble = ref(0)

const reactiveParams = ref({
  emissionRate: { enabled: true, intensity: 1, freqBand: 'bass' },
  speed: { enabled: true, intensity: 0.5, freqBand: 'mid' },
  size: { enabled: true, intensity: 0.3, freqBand: 'treble' },
  color: { enabled: false, intensity: 1, freqBand: 'mid' }
})

const interactionModes = [
  { id: 'repel', name: '排斥', icon: '↗️' },
  { id: 'attract', name: '吸引', icon: '↘️' },
  { id: 'vortex', name: '漩涡', icon: '🌀' },
  { id: 'upward', name: '上升', icon: '⬆️' },
  { id: 'downward', name: '下降', icon: '⬇️' }
]

const bassHeight = computed(() => `${Math.min(100, bass.value * 80)}%`)
const midHeight = computed(() => `${Math.min(100, mid.value * 80)}%`)
const trebleHeight = computed(() => `${Math.min(100, treble.value * 80)}%`)

function toggleMouse(event) {
  mouseEnabled.value = event.target.checked
  if (props.mouseInteractor) {
    props.mouseInteractor.setEnabled(mouseEnabled.value)
  }
  emit('mouse-enabled-change', mouseEnabled.value)
}

function setMouseMode(mode) {
  mouseMode.value = mode
  if (props.mouseInteractor) {
    props.mouseInteractor.setMode(mode)
  }
}

function updateMouseStrength() {
  if (props.mouseInteractor) {
    props.mouseInteractor.setStrength(mouseStrength.value)
  }
}

function updateMouseRadius() {
  if (props.mouseInteractor) {
    props.mouseInteractor.setRadius(mouseRadius.value)
  }
}

function toggleAudio(event) {
  audioEnabled.value = event.target.checked
  if (!audioEnabled.value) {
    audioReactor.stop()
    audioConnected.value = false
  }
  emit('audio-enabled-change', audioEnabled.value)
}

async function connectMicrophone() {
  audioSource.value = 'mic'
  const success = await audioReactor.connectToMicrophone()
  if (success) {
    audioConnected.value = true
    audioReactor.onUpdate = onAudioUpdate
    emit('audio-reactor-created', audioReactor)
    startAudioLoop()
  }
}

async function handleAudioFile(event) {
  const file = event.target.files[0]
  if (file) {
    try {
      audioSource.value = 'file'
      const audio = await audioReactor.loadAudioFile(file)
      audioElement.value = audio
      audioConnected.value = true
      audioReactor.onUpdate = onAudioUpdate
      emit('audio-reactor-created', audioReactor)
      startAudioLoop()
    } catch (error) {
      alert('加载音频文件失败: ' + error.message)
    }
  }
  event.target.value = ''
}

function onAudioUpdate(data) {
  bass.value = data.bass
  mid.value = data.mid
  treble.value = data.treble
}

function startAudioLoop() {
  function update() {
    if (audioConnected.value && audioEnabled.value) {
      audioReactor.update()
      requestAnimationFrame(update)
    }
  }
  requestAnimationFrame(update)
}

function updateSensitivity() {
  audioReactor.setSensitivity(audioSensitivity.value)
}

function toggleReactive(paramName) {
  const param = reactiveParams.value[paramName]
  if (param) {
    param.enabled = !param.enabled
    audioReactor.setReactiveParam(paramName, param)
  }
}

function togglePlayback() {
  if (isPlaying.value) {
    audioReactor.pause()
    isPlaying.value = false
  } else {
    audioReactor.play()
    isPlaying.value = true
  }
}

function stopAudio() {
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value.currentTime = 0
    isPlaying.value = false
  }
}

onUnmounted(() => {
  audioReactor.dispose()
})
</script>

<style scoped>
.interaction-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-section {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.section-header {
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.section-header h5 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.section-content {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  transition: 0.3s;
}

.toggle-slider:before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background: #fff;
  border-radius: 50%;
  transition: 0.3s;
}

.toggle-switch input:checked + .toggle-slider {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.control-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-item label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.mode-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.mode-btn {
  flex: 1;
  min-width: 60px;
  padding: 6px 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.mode-btn:hover {
  background: rgba(102, 126, 234, 0.2);
  color: #fff;
}

.mode-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: #fff;
}

.control-item input[type='range'] {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  outline: none;
}

.control-item input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  cursor: pointer;
}

.hint {
  padding: 8px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 4px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  text-align: center;
}

.audio-sources {
  display: flex;
  gap: 6px;
}

.source-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  text-align: center;
  transition: all 0.2s;
}

.source-btn:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

.source-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.file-input-label {
  display: inline-block;
  cursor: pointer;
}

.audio-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.audio-visualizer {
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
}

.freq-bars {
  display: flex;
  gap: 12px;
  height: 60px;
  align-items: flex-end;
}

.freq-bar {
  flex: 1;
  background: linear-gradient(to top, #667eea, #764ba2);
  border-radius: 3px 3px 0 0;
  min-height: 4px;
  transition: height 0.1s ease-out;
}

.freq-bar.bass {
  background: linear-gradient(to top, #ff6b6b, #ee5a5a);
}

.freq-bar.mid {
  background: linear-gradient(to top, #4ecdc4, #44a08d);
}

.freq-bar.treble {
  background: linear-gradient(to top, #a8edea, #fed6e3);
}

.freq-labels {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}

.freq-labels span {
  flex: 1;
  text-align: center;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

.reactive-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

.mini-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.mini-toggle input {
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.audio-player {
  display: flex;
  gap: 6px;
}

.play-btn,
.stop-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.play-btn:hover,
.stop-btn:hover {
  background: rgba(102, 126, 234, 0.3);
}

.audio-hint {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}
</style>
