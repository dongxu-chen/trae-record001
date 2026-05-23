<template>
  <div v-if="isOpen" class="presentation-overlay">
    <div class="presentation-toolbar">
      <div class="presentation-info">
        🎬 演示模式
        <span class="progress">{{ currentStep }} / {{ totalSteps }}</span>
      </div>
      
      <div class="presentation-controls">
        <button class="control-btn" @click="stepBack" :disabled="currentStep <= 0">
          ⏮️
        </button>
        <button class="control-btn play" @click="togglePlay">
          {{ isPlaying ? '⏸️' : '▶️' }}
        </button>
        <button class="control-btn" @click="stepForward" :disabled="currentStep >= totalSteps - 1">
          ⏭️
        </button>
        
        <div class="speed-control">
          <label>速度:</label>
          <select v-model="playSpeed" @change="updatePlaySpeed">
            <option :value="0.5">0.5x</option>
            <option :value="1">1x</option>
            <option :value="2">2x</option>
            <option :value="4">4x</option>
          </select>
        </div>
        
        <button class="control-btn" @click="exportVideo" :disabled="isRecording">
          {{ isRecording ? '📹 录制中...' : '📹 导出视频' }}
        </button>
        
        <button class="control-btn close" @click="closePresentation">
          ✕
        </button>
      </div>
    </div>
    
    <div class="presentation-canvas">
      <canvas ref="presentationCanvasRef"></canvas>
    </div>
    
    <div v-if="isRecording" class="recording-indicator">
      <span class="recording-dot"></span>
      正在录制... {{ recordingTime }}s
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  layers: { type: Array, default: () => [] }
})

const emit = defineEmits(['close'])

const presentationCanvasRef = ref(null)
const ctx = ref(null)

const isPlaying = ref(false)
const currentStep = ref(0)
const playSpeed = ref(1)
const playInterval = ref(null)

const isRecording = ref(false)
const recordingTime = ref(0)
const mediaRecorder = ref(null)
const recordedChunks = ref([])
const recordingInterval = ref(null)

const playLayers = ref([])

const totalSteps = computed(() => playLayers.value.length)

import { computed } from 'vue'

function buildPlayLayers() {
  playLayers.value = []
  
  props.layers.forEach(layer => {
    if (layer.type === 'pen' || layer.type === 'eraser') {
      if (layer.points && layer.points.length > 1) {
        for (let i = 2; i <= layer.points.length; i++) {
          playLayers.value.push({
            type: 'partial',
            layerId: layer.id,
            layer: {
              ...layer,
              points: layer.points.slice(0, i)
            }
          })
        }
      }
    } else {
      playLayers.value.push({
        type: 'full',
        layerId: layer.id,
        layer: { ...layer }
      })
    }
  })
}

function renderCurrentState() {
  if (!ctx.value) return
  
  const canvas = presentationCanvasRef.value
  ctx.value.clearRect(0, 0, canvas.width, canvas.height)
  ctx.value.fillStyle = '#ffffff'
  ctx.value.fillRect(0, 0, canvas.width, canvas.height)
  
  const drawnLayers = new Map()
  
  for (let i = 0; i <= currentStep.value && i < playLayers.value.length; i++) {
    const step = playLayers.value[i]
    drawnLayers.set(step.layerId, step.layer)
  }
  
  drawnLayers.forEach(layer => drawLayer(layer))
}

function drawLayer(layer) {
  if (!layer.visible) return
  
  ctx.value.globalAlpha = layer.opacity || 1
  ctx.value.strokeStyle = layer.color
  ctx.value.fillStyle = layer.color
  ctx.value.lineWidth = layer.lineWidth || 3
  ctx.value.lineCap = 'round'
  ctx.value.lineJoin = 'round'

  switch (layer.type) {
    case 'pen':
      drawPenStroke(layer)
      break
    case 'eraser':
      break
    case 'rectangle':
      ctx.value.beginPath()
      ctx.value.rect(layer.x, layer.y, layer.width, layer.height)
      if (layer.fill) ctx.value.fill()
      else ctx.value.stroke()
      break
    case 'circle':
      ctx.value.beginPath()
      ctx.value.ellipse(layer.x, layer.y, layer.radiusX, layer.radiusY, 0, 0, Math.PI * 2)
      if (layer.fill) ctx.value.fill()
      else ctx.value.stroke()
      break
    case 'line':
      ctx.value.beginPath()
      ctx.value.moveTo(layer.x1, layer.y1)
      ctx.value.lineTo(layer.x2, layer.y2)
      ctx.value.stroke()
      break
    case 'text':
      ctx.value.font = `${layer.fontSize || 24}px sans-serif`
      ctx.value.fillText(layer.text, layer.x, layer.y)
      break
  }
  
  ctx.value.globalAlpha = 1
}

function drawPenStroke(layer) {
  if (!layer.points || layer.points.length < 2) return
  
  ctx.value.beginPath()
  ctx.value.strokeStyle = layer.color
  ctx.value.lineCap = 'round'
  ctx.value.lineJoin = 'round'
  
  for (let i = 1; i < layer.points.length; i++) {
    const prev = layer.points[i - 1]
    const curr = layer.points[i]
    
    ctx.value.lineWidth = curr.pressure || layer.lineWidth
    ctx.value.beginPath()
    ctx.value.moveTo(prev.x, prev.y)
    ctx.value.lineTo(curr.x, curr.y)
    ctx.value.stroke()
  }
}

function togglePlay() {
  isPlaying.value = !isPlaying.value
  
  if (isPlaying.value) {
    startPlaying()
  } else {
    stopPlaying()
  }
}

function startPlaying() {
  stopPlaying()
  
  const delay = 100 / playSpeed.value
  playInterval.value = setInterval(() => {
    if (currentStep.value < totalSteps.value - 1) {
      currentStep.value++
      renderCurrentState()
    } else {
      stopPlaying()
      isPlaying.value = false
    }
  }, delay)
}

function stopPlaying() {
  if (playInterval.value) {
    clearInterval(playInterval.value)
    playInterval.value = null
  }
}

function stepBack() {
  if (currentStep.value > 0) {
    currentStep.value--
    renderCurrentState()
  }
}

function stepForward() {
  if (currentStep.value < totalSteps.value - 1) {
    currentStep.value++
    renderCurrentState()
  }
}

function updatePlaySpeed() {
  if (isPlaying.value) {
    stopPlaying()
    startPlaying()
  }
}

function closePresentation() {
  stopPlaying()
  stopRecording()
  emit('close')
}

function exportVideo() {
  if (isRecording.value) {
    stopRecording()
    return
  }
  
  const canvas = presentationCanvasRef.value
  const stream = canvas.captureStream(30)
  
  mediaRecorder.value = new MediaRecorder(stream, {
    mimeType: 'video/webm;codecs=vp9'
  })
  
  recordedChunks.value = []
  
  mediaRecorder.value.ondataavailable = (e) => {
    if (e.data.size > 0) {
      recordedChunks.value.push(e.data)
    }
  }
  
  mediaRecorder.value.onstop = () => {
    const blob = new Blob(recordedChunks.value, { type: 'video/webm' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `whiteboard-presentation-${Date.now()}.webm`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  isRecording.value = true
  recordingTime.value = 0
  currentStep.value = 0
  renderCurrentState()
  
  mediaRecorder.value.start()
  
  recordingInterval.value = setInterval(() => {
    recordingTime.value++
  }, 1000)
  
  isPlaying.value = true
  startPlaying()
  
  const checkEnd = setInterval(() => {
    if (currentStep.value >= totalSteps.value - 1 || !isPlaying.value) {
      clearInterval(checkEnd)
      setTimeout(() => stopRecording(), 500)
    }
  }, 100)
}

function stopRecording() {
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
  
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value)
    recordingInterval.value = null
  }
  
  isRecording.value = false
  stopPlaying()
  isPlaying.value = false
}

function resizeCanvas() {
  if (!presentationCanvasRef.value) return
  
  const container = presentationCanvasRef.value.parentElement
  presentationCanvasRef.value.width = container.clientWidth
  presentationCanvasRef.value.height = container.clientHeight
  renderCurrentState()
}

watch(() => props.isOpen, (open) => {
  if (open) {
    buildPlayLayers()
    currentStep.value = 0
    
    setTimeout(() => {
      ctx.value = presentationCanvasRef.value?.getContext('2d')
      resizeCanvas()
      renderCurrentState()
    }, 100)
  }
})

watch(() => props.layers, () => {
  if (props.isOpen) {
    buildPlayLayers()
  }
}, { deep: true })

onMounted(() => {
  window.addEventListener('resize', resizeCanvas)
})

onUnmounted(() => {
  stopPlaying()
  stopRecording()
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<style scoped>
.presentation-overlay {
  position: fixed;
  inset: 0;
  background: #1a1a2e;
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.presentation-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #16213e;
  color: white;
  border-bottom: 1px solid #0f3460;
}

.presentation-info {
  font-size: 16px;
  font-weight: 500;
}

.progress {
  margin-left: 16px;
  color: #a0aec0;
  font-size: 14px;
}

.presentation-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: #0f3460;
  color: white;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-btn:hover {
  background: #1a4a8a;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.control-btn.play {
  width: 50px;
  height: 50px;
  font-size: 20px;
  background: #e94560;
}

.control-btn.play:hover {
  background: #ff6b6b;
}

.control-btn.close {
  background: #e94560;
  margin-left: 8px;
}

.control-btn.close:hover {
  background: #ff6b6b;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 12px;
  font-size: 14px;
  color: #a0aec0;
}

.speed-control select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #0f3460;
  background: #1a1a2e;
  color: white;
  cursor: pointer;
}

.presentation-canvas {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  overflow: hidden;
}

.presentation-canvas canvas {
  max-width: 100%;
  max-height: 100%;
  background: white;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}

.recording-indicator {
  position: absolute;
  top: 80px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #e94560;
  color: white;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.recording-dot {
  width: 10px;
  height: 10px;
  background: white;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
