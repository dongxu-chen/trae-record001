<template>
  <div class="bezier-editor">
    <div class="editor-header">
      <h4>贝塞尔曲线编辑器</h4>
      <div class="preset-curves">
        <button
          v-for="preset in curvePresets"
          :key="preset.name"
          :class="['preset-btn', { active: isPresetActive(preset) }]"
          @click="applyPreset(preset)"
          :title="preset.name"
        >
          {{ preset.icon }}
        </button>
      </div>
    </div>

    <div class="canvas-container" ref="canvasContainer">
      <canvas
        ref="canvas"
        :width="canvasSize"
        :height="canvasSize"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
      ></canvas>

      <div class="control-point-info" v-if="draggedPoint !== null">
        <span>P{{ draggedPoint }}: ({{ controlPoints[draggedPoint].x.toFixed(2) }}, {{ controlPoints[draggedPoint].y.toFixed(2) }})</span>
      </div>
    </div>

    <div class="editor-footer">
      <div class="curve-params">
        <div class="param-item">
          <span>cubic-bezier(</span>
          <span class="param-value">{{ formatParams() }}</span>
          <span>)</span>
        </div>
      </div>
      <div class="editor-actions">
        <button @click="resetCurve" class="reset-btn">重置</button>
        <button @click="applyCurve" class="apply-btn">应用</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ x1: 0.25, y1: 0.1, x2: 0.25, y2: 1 })
  },
  presetName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'apply'])

const canvas = ref(null)
const canvasContainer = ref(null)
const canvasSize = 280
const padding = 20

const controlPoints = ref([
  { x: 0, y: 1 },
  { x: 0.25, y: 0.1 },
  { x: 0.25, y: 1 },
  { x: 1, y: 0 }
])

const draggedPoint = ref(null)
const currentPreset = ref('')

const curvePresets = [
  { name: 'linear', icon: '─', params: { x1: 0, y1: 0, x2: 1, y2: 1 } },
  { name: 'ease', icon: '⌒', params: { x1: 0.25, y1: 0.1, x2: 0.25, y2: 1 } },
  { name: 'ease-in', icon: '╭', params: { x1: 0.42, y1: 0, x2: 1, y2: 1 } },
  { name: 'ease-out', icon: '╮', params: { x1: 0, y1: 0, x2: 0.58, y2: 1 } },
  { name: 'ease-in-out', icon: '〜', params: { x1: 0.42, y1: 0, x2: 0.58, y2: 1 } },
  { name: 'power2.in', icon: '²↑', params: { x1: 0.55, y1: 0.085, x2: 0.68, y2: 0.53 } },
  { name: 'power2.out', icon: '²↓', params: { x1: 0.25, y1: 0.46, x2: 0.45, y2: 0.94 } },
  { name: 'power4.in', icon: '⁴↑', params: { x1: 0.895, y1: 0.03, x2: 0.685, y2: 0.22 } },
  { name: 'power4.out', icon: '⁴↓', params: { x1: 0.165, y1: 0.84, x2: 0.44, y2: 1 } },
  { name: 'elastic', icon: '∿', params: { x1: 0.68, y1: -0.55, x2: 0.265, y2: 1.55 } },
  { name: 'back-in', icon: '↶', params: { x1: 0.6, y1: -0.28, x2: 0.735, y2: 0.045 } },
  { name: 'back-out', icon: '↷', params: { x1: 0.175, y1: 0.885, x2: 0.32, y2: 1.275 } }
]

watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      controlPoints.value[1] = { x: newVal.x1, y: newVal.y1 }
      controlPoints.value[2] = { x: newVal.x2, y: newVal.y2 }
      draw()
    }
  },
  { deep: true }
)

watch(
  controlPoints,
  () => {
    const params = {
      x1: controlPoints.value[1].x,
      y1: controlPoints.value[1].y,
      x2: controlPoints.value[2].x,
      y2: controlPoints.value[2].y
    }
    emit('update:modelValue', params)
    currentPreset.value = ''
    draw()
  },
  { deep: true }
)

function isPresetActive(preset) {
  return currentPreset.value === preset.name
}

function applyPreset(preset) {
  controlPoints.value[1] = { x: preset.params.x1, y: preset.params.y1 }
  controlPoints.value[2] = { x: preset.params.x2, y: preset.params.y2 }
  currentPreset.value = preset.name
  draw()
}

function formatParams() {
  const p1 = controlPoints.value[1]
  const p2 = controlPoints.value[2]
  return `${p1.x.toFixed(2)}, ${p1.y.toFixed(2)}, ${p2.x.toFixed(2)}, ${p2.y.toFixed(2)}`
}

function resetCurve() {
  controlPoints.value[1] = { x: 0.25, y: 0.1 }
  controlPoints.value[2] = { x: 0.25, y: 1 }
  currentPreset.value = ''
  draw()
}

function applyCurve() {
  emit('apply', {
    x1: controlPoints.value[1].x,
    y1: controlPoints.value[1].y,
    x2: controlPoints.value[2].x,
    y2: controlPoints.value[2].y,
    preset: currentPreset.value
  })
}

function toCanvasX(x) {
  return padding + x * (canvasSize - padding * 2)
}

function toCanvasY(y) {
  return canvasSize - padding - y * (canvasSize - padding * 2)
}

function fromCanvasX(canvasX) {
  return (canvasX - padding) / (canvasSize - padding * 2)
}

function fromCanvasY(canvasY) {
  return (canvasSize - padding - canvasY) / (canvasSize - padding * 2)
}

function getPointAtT(t) {
  const p0 = controlPoints.value[0]
  const p1 = controlPoints.value[1]
  const p2 = controlPoints.value[2]
  const p3 = controlPoints.value[3]

  const mt = 1 - t
  const mt2 = mt * mt
  const mt3 = mt2 * mt
  const t2 = t * t
  const t3 = t2 * t

  return {
    x: mt3 * p0.x + 3 * mt2 * t * p1.x + 3 * mt * t2 * p2.x + t3 * p3.x,
    y: mt3 * p0.y + 3 * mt2 * t * p1.y + 3 * mt * t2 * p2.y + t3 * p3.y
  }
}

function draw() {
  if (!canvas.value) return

  const ctx = canvas.value.getContext('2d')
  const size = canvasSize

  ctx.clearRect(0, 0, size, size)

  ctx.fillStyle = '#0f0f1a'
  ctx.fillRect(0, 0, size, size)

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)'
  ctx.lineWidth = 1

  for (let i = 0; i <= 10; i++) {
    const pos = padding + (i / 10) * (size - padding * 2)
    ctx.beginPath()
    ctx.moveTo(pos, padding)
    ctx.lineTo(pos, size - padding)
    ctx.stroke()

    ctx.beginPath()
    ctx.moveTo(padding, pos)
    ctx.lineTo(size - padding, pos)
    ctx.stroke()
  }

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])

  ctx.beginPath()
  ctx.moveTo(toCanvasX(0), toCanvasY(0))
  ctx.lineTo(toCanvasX(controlPoints.value[1].x), toCanvasY(controlPoints.value[1].y))
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(toCanvasX(1), toCanvasY(0))
  ctx.lineTo(toCanvasX(controlPoints.value[2].x), toCanvasY(controlPoints.value[2].y))
  ctx.stroke()

  ctx.setLineDash([])

  ctx.strokeStyle = '#667eea'
  ctx.lineWidth = 3
  ctx.beginPath()

  for (let t = 0; t <= 1; t += 0.01) {
    const point = getPointAtT(t)
    const x = toCanvasX(point.x)
    const y = toCanvasY(point.y)

    if (t === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.stroke()

  const gradient = ctx.createLinearGradient(0, size, size, 0)
  gradient.addColorStop(0, 'rgba(102, 126, 234, 0.1)')
  gradient.addColorStop(1, 'rgba(118, 75, 162, 0.1)')

  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.moveTo(toCanvasX(0), toCanvasY(0))
  for (let t = 0; t <= 1; t += 0.01) {
    const point = getPointAtT(t)
    ctx.lineTo(toCanvasX(point.x), toCanvasY(point.y))
  }
  ctx.lineTo(toCanvasX(1), toCanvasY(0))
  ctx.closePath()
  ctx.fill()

  for (let i = 0; i < controlPoints.value.length; i++) {
    const point = controlPoints.value[i]
    const x = toCanvasX(point.x)
    const y = toCanvasY(point.y)

    if (i === 0 || i === 3) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.3)'
      ctx.beginPath()
      ctx.arc(x, y, 6, 0, Math.PI * 2)
      ctx.fill()
    } else {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
      ctx.strokeStyle = '#667eea'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.arc(x, y, 10, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()

      ctx.fillStyle = '#667eea'
      ctx.font = 'bold 10px monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(`P${i}`, x, y)
    }
  }

  ctx.fillStyle = 'rgba(255, 255, 255, 0.5)'
  ctx.font = '10px monospace'
  ctx.textAlign = 'left'
  ctx.fillText('0', padding - 15, size - padding + 4)
  ctx.textAlign = 'right'
  ctx.fillText('1', size - padding + 15, size - padding + 4)
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  ctx.fillText('1', padding - 8, padding)
  ctx.fillText('0', padding - 8, size - padding)
}

function getClickedPoint(mouseX, mouseY) {
  for (let i = 1; i <= 2; i++) {
    const point = controlPoints.value[i]
    const x = toCanvasX(point.x)
    const y = toCanvasY(point.y)
    const dist = Math.sqrt((mouseX - x) ** 2 + (mouseY - y) ** 2)
    if (dist < 15) {
      return i
    }
  }
  return null
}

function onMouseDown(e) {
  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvasSize / rect.width
  const scaleY = canvasSize / rect.height
  const x = (e.clientX - rect.left) * scaleX
  const y = (e.clientY - rect.top) * scaleY

  const pointIndex = getClickedPoint(x, y)
  if (pointIndex !== null) {
    draggedPoint.value = pointIndex
  }
}

function onMouseMove(e) {
  if (draggedPoint.value === null) return

  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvasSize / rect.width
  const scaleY = canvasSize / rect.height
  let x = (e.clientX - rect.left) * scaleX
  let y = (e.clientY - rect.top) * scaleY

  x = Math.max(padding - 50, Math.min(canvasSize - padding + 50, x))
  y = Math.max(padding - 50, Math.min(canvasSize - padding + 50, y))

  controlPoints.value[draggedPoint.value] = {
    x: Math.max(-0.5, Math.min(1.5, fromCanvasX(x))),
    y: Math.max(-0.5, Math.min(1.5, fromCanvasY(y)))
  }
}

function onMouseUp() {
  draggedPoint.value = null
}

onMounted(() => {
  if (props.modelValue) {
    controlPoints.value[1] = { x: props.modelValue.x1, y: props.modelValue.y1 }
    controlPoints.value[2] = { x: props.modelValue.x2, y: props.modelValue.y2 }
  }
  draw()
})
</script>

<style scoped>
.bezier-editor {
  background: rgba(15, 15, 25, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  user-select: none;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.editor-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.preset-curves {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  max-width: 180px;
}

.preset-btn {
  width: 28px;
  height: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.preset-btn:hover {
  background: rgba(102, 126, 234, 0.3);
  border-color: rgba(102, 126, 234, 0.5);
}

.preset-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.canvas-container {
  position: relative;
  display: flex;
  justify-content: center;
}

.canvas-container canvas {
  border-radius: 8px;
  cursor: pointer;
  max-width: 100%;
  height: auto;
}

.control-point-info {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(0, 0, 0, 0.7);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  color: #667eea;
}

.editor-footer {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.curve-params {
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-family: monospace;
  color: rgba(255, 255, 255, 0.7);
}

.param-item {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.param-value {
  color: #667eea;
  font-weight: 600;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.reset-btn,
.apply-btn {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.reset-btn:hover {
  background: rgba(255, 100, 100, 0.2);
  border-color: rgba(255, 100, 100, 0.5);
}

.apply-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
}

.apply-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
</style>
