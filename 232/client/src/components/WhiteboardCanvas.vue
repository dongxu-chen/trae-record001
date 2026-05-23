<template>
  <div class="whiteboard-container" ref="containerRef">
    <canvas
      ref="canvasRef"
      class="whiteboard-canvas"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @wheel="handleWheel"
      @dblclick="handleDoubleClick"
      @contextmenu="handleContextMenu"
    ></canvas>
    <div v-for="cursor in remoteCursors" :key="cursor.clientId"
         class="remote-cursor"
         :style="{ left: cursor.screenX + 'px', top: cursor.screenY + 'px' }">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z" :fill="cursor.color" :stroke="cursor.color"/>
      </svg>
    </div>
    
    <div v-for="comment in comments" :key="comment.id"
         class="comment-marker"
         :class="{ active: activeCommentId === comment.id, resolved: comment.resolved }"
         :style="{ 
           left: (comment.x * scale + offsetX) + 'px', 
           top: (comment.y * scale + offsetY) + 'px' 
         }"
         @click.stop="selectComment(comment.id)">
      <span class="marker-icon">{{ comment.resolved ? '✅' : '💬' }}</span>
      <span v-if="comment.replies && comment.replies.length > 0" class="reply-count">
        {{ comment.replies.length }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { v4 as uuidv4 } from 'uuid'

const props = defineProps({
  tool: { type: String, default: 'pen' },
  color: { type: String, default: '#000000' },
  lineWidth: { type: Number, default: 3 },
  layers: { type: Array, default: () => [] },
  comments: { type: Array, default: () => [] },
  activeCommentId: { type: String, default: null },
  enablePressure: { type: Boolean, default: true }
})

const emit = defineEmits([
  'startDraw',
  'appendPoints',
  'endDraw',
  'addShape',
  'layerAdded',
  'layerUpdated',
  'layerDeleted',
  'cursorMove',
  'addComment',
  'selectComment'
])

const containerRef = ref(null)
const canvasRef = ref(null)
const ctx = ref(null)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)
const isDrawing = ref(false)
const isPanning = ref(false)
const startX = ref(0)
const startY = ref(0)
const currentLayer = ref(null)
const pendingPoints = ref([])
const lastPointTime = ref(0)
const lastPoint = ref(null)
const pointSendInterval = ref(null)

const remoteCursors = ref([])
const cursorColors = ['#ef4444', '#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899']

const POINT_BATCH_SIZE = 5
const POINT_SEND_DELAY = 30

function getMousePos(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: (e.clientX - rect.left - offsetX.value) / scale.value,
    y: (e.clientY - rect.top - offsetY.value) / scale.value,
    screenX: e.clientX - rect.left,
    screenY: e.clientY - rect.top,
    timestamp: Date.now()
  }
}

function calculatePressure(point1, point2, baseWidth) {
  if (!props.enablePressure || !point1 || !point2) return baseWidth
  
  const distance = Math.sqrt(
    Math.pow(point2.x - point1.x, 2) + Math.pow(point2.y - point1.y, 2)
  )
  const timeDiff = Math.max(point2.timestamp - point1.timestamp, 1)
  const speed = distance / timeDiff
  
  const minWidth = Math.max(0.5, baseWidth * 0.3)
  const maxWidth = baseWidth * 2
  const pressure = Math.min(1, Math.max(0, 1 - speed / 2))
  
  return minWidth + pressure * (maxWidth - minWidth)
}

function handleMouseDown(e) {
  if (e.button === 2) return
  
  const pos = getMousePos(e)
  
  if (e.button === 1 || (e.button === 0 && e.altKey)) {
    isPanning.value = true
    startX.value = e.clientX - offsetX.value
    startY.value = e.clientY - offsetY.value
    return
  }

  isDrawing.value = true
  startX.value = pos.x
  startY.value = pos.y
  lastPoint.value = pos
  lastPointTime.value = pos.timestamp

  const layerId = uuidv4()
  
  switch (props.tool) {
    case 'pen': {
        const pressure = calculatePressure(null, null, props.lineWidth)
        currentLayer.value = {
          id: layerId,
          type: 'pen',
          color: props.color,
          lineWidth: props.lineWidth,
          points: [{ x: pos.x, y: pos.y, pressure }],
          visible: true,
          opacity: 1
        }
        pendingPoints.value = [{ x: pos.x, y: pos.y, pressure }]
        emit('startDraw', { layer: currentLayer.value })
        startPointSending()
        break
      }
    case 'rectangle':
      currentLayer.value = {
        id: layerId,
        type: 'rectangle',
        color: props.color,
        lineWidth: props.lineWidth,
        x: pos.x,
        y: pos.y,
        width: 0,
        height: 0,
        fill: false,
        visible: true,
        opacity: 1
      }
      break
    case 'circle':
      currentLayer.value = {
        id: layerId,
        type: 'circle',
        color: props.color,
        lineWidth: props.lineWidth,
        x: pos.x,
        y: pos.y,
        radiusX: 0,
        radiusY: 0,
        fill: false,
        visible: true,
        opacity: 1
      }
      break
    case 'line':
      currentLayer.value = {
        id: layerId,
        type: 'line',
        color: props.color,
        lineWidth: props.lineWidth,
        x1: pos.x,
        y1: pos.y,
        x2: pos.x,
        y2: pos.y,
        visible: true,
        opacity: 1
      }
      break
    case 'eraser': {
        currentLayer.value = {
          id: layerId,
          type: 'eraser',
          lineWidth: props.lineWidth * 3,
          points: [{ x: pos.x, y: pos.y, pressure: props.lineWidth * 3 }],
          visible: true,
          opacity: 1
        }
        pendingPoints.value = [{ x: pos.x, y: pos.y, pressure: props.lineWidth * 3 }]
        emit('startDraw', { layer: currentLayer.value })
        startPointSending()
        break
      }
  }
}

function handleContextMenu(e) {
  e.preventDefault()
  const pos = getMousePos(e)
  
  const content = prompt('输入评论内容:')
  if (content) {
    emit('addComment', {
      x: pos.x,
      y: pos.y,
      content
    })
  }
}

function startPointSending() {
  stopPointSending()
  pointSendInterval.value = setInterval(() => {
    if (pendingPoints.value.length > 0) {
      const batch = pendingPoints.value.splice(0, POINT_BATCH_SIZE)
      if (currentLayer.value) {
        emit('appendPoints', {
          layerId: currentLayer.value.id,
          points: batch
        })
      }
    }
  }, POINT_SEND_DELAY)
}

function stopPointSending() {
  if (pointSendInterval.value) {
    clearInterval(pointSendInterval.value)
    pointSendInterval.value = null
  }
  
  if (pendingPoints.value.length > 0 && currentLayer.value) {
    emit('appendPoints', {
      layerId: currentLayer.value.id,
      points: pendingPoints.value
    })
    pendingPoints.value = []
  }
}

function handleMouseMove(e) {
  const pos = getMousePos(e)
  
  emit('cursorMove', { x: pos.x, y: pos.y, screenX: pos.screenX, screenY: pos.screenY })

  if (isPanning.value) {
    offsetX.value = e.clientX - startX.value
    offsetY.value = e.clientY - startY.value
    render()
    return
  }

  if (!isDrawing.value || !currentLayer.value) return

  switch (props.tool) {
    case 'pen': {
        const pressure = calculatePressure(lastPoint.value, pos, props.lineWidth)
        const point = { x: pos.x, y: pos.y, pressure }
        currentLayer.value.points.push(point)
        pendingPoints.value.push(point)
        lastPoint.value = pos
        break
      }
    case 'eraser': {
        const pressure = calculatePressure(lastPoint.value, pos, props.lineWidth * 3)
        const point = { x: pos.x, y: pos.y, pressure }
        currentLayer.value.points.push(point)
        pendingPoints.value.push(point)
        lastPoint.value = pos
        break
      }
    case 'rectangle':
      currentLayer.value.width = pos.x - startX.value
      currentLayer.value.height = pos.y - startY.value
      break
    case 'circle':
      currentLayer.value.radiusX = Math.abs(pos.x - startX.value)
      currentLayer.value.radiusY = Math.abs(pos.y - startY.value)
      break
    case 'line':
      currentLayer.value.x2 = pos.x
      currentLayer.value.y2 = pos.y
      break
  }
  
  render()
}

function handleMouseUp(e) {
  if (e.button === 2) return
  
  if (isPanning.value) {
    isPanning.value = false
    return
  }

  if (isDrawing.value && currentLayer.value) {
    stopPointSending()
    
    if (currentLayer.value.type === 'pen' || currentLayer.value.type === 'eraser') {
      emit('endDraw', { layerId: currentLayer.value.id, layer: currentLayer.value })
    } else {
      emit('addShape', { layer: currentLayer.value })
    }
    
    currentLayer.value = null
    pendingPoints.value = []
    lastPoint.value = null
  }
  
  isDrawing.value = false
}

function handleWheel(e) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  const newScale = Math.max(0.1, Math.min(5, scale.value * delta))
  
  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  
  offsetX.value = mouseX - (mouseX - offsetX.value) * (newScale / scale.value)
  offsetY.value = mouseY - (mouseY - offsetY.value) * (newScale / scale.value)
  scale.value = newScale
  
  render()
}

function handleDoubleClick(e) {
  if (props.tool !== 'text') return
  
  const pos = getMousePos(e)
  const text = prompt('请输入文本:')
  if (text) {
    const layer = {
      id: uuidv4(),
      type: 'text',
      text,
      x: pos.x,
      y: pos.y,
      color: props.color,
      fontSize: 24,
      visible: true,
      opacity: 1
    }
    emit('addShape', { layer })
    render()
  }
}

function selectComment(commentId) {
  emit('selectComment', commentId)
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

function drawEraserStroke(layer) {
  if (!layer.points || layer.points.length < 2) return
  
  ctx.value.globalCompositeOperation = 'destination-out'
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
  
  ctx.value.globalCompositeOperation = 'source-over'
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
      drawEraserStroke(layer)
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

function render() {
  if (!ctx.value) return
  
  const canvas = canvasRef.value
  ctx.value.clearRect(0, 0, canvas.width, canvas.height)
  
  ctx.value.save()
  ctx.value.fillStyle = '#ffffff'
  ctx.value.fillRect(0, 0, canvas.width, canvas.height)
  
  ctx.value.translate(offsetX.value, offsetY.value)
  ctx.value.scale(scale.value, scale.value)
  
  drawGrid()
  
  props.layers.forEach(layer => drawLayer(layer))
  
  if (currentLayer.value) {
    drawLayer(currentLayer.value)
  }
  
  ctx.value.restore()
}

function drawGrid() {
  const gridSize = 20
  ctx.value.strokeStyle = '#e5e7eb'
  ctx.value.lineWidth = 0.5
  
  const startX = -offsetX.value / scale.value
  const startY = -offsetY.value / scale.value
  const endX = (canvasRef.value.width - offsetX.value) / scale.value
  const endY = (canvasRef.value.height - offsetY.value) / scale.value
  
  for (let x = Math.floor(startX / gridSize) * gridSize; x < endX; x += gridSize) {
    ctx.value.beginPath()
    ctx.value.moveTo(x, startY)
    ctx.value.lineTo(x, endY)
    ctx.value.stroke()
  }
  
  for (let y = Math.floor(startY / gridSize) * gridSize; y < endY; y += gridSize) {
    ctx.value.beginPath()
    ctx.value.moveTo(startX, y)
    ctx.value.lineTo(endX, y)
    ctx.value.stroke()
  }
}

function resizeCanvas() {
  if (!containerRef.value || !canvasRef.value) return
  
  canvasRef.value.width = containerRef.value.clientWidth
  canvasRef.value.height = containerRef.value.clientHeight
  render()
}

function takeSnapshot() {
  return canvasRef.value.toDataURL('image/png')
}

function resetView() {
  scale.value = 1
  offsetX.value = 0
  offsetY.value = 0
  render()
}

function updateRemoteCursor(clientId, x, y, screenX, screenY) {
  let cursor = remoteCursors.value.find(c => c.clientId === clientId)
  const colorIndex = Math.abs(clientId.charCodeAt(0) || 0) % cursorColors.length
  
  if (!cursor) {
    cursor = { clientId, color: cursorColors[colorIndex] }
    remoteCursors.value.push(cursor)
  }
  
  cursor.x = x
  cursor.y = y
  cursor.screenX = screenX
  cursor.screenY = screenY
}

function removeRemoteCursor(clientId) {
  remoteCursors.value = remoteCursors.value.filter(c => c.clientId !== clientId)
}

watch(() => props.layers, () => render(), { deep: true })
watch(() => props.comments, () => {}, { deep: true })

onMounted(() => {
  ctx.value = canvasRef.value.getContext('2d')
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
})

onUnmounted(() => {
  stopPointSending()
  window.removeEventListener('resize', resizeCanvas)
})

defineExpose({
  render,
  takeSnapshot,
  resetView,
  updateRemoteCursor,
  removeRemoteCursor,
  scale,
  offsetX,
  offsetY,
  getContext: () => ctx.value,
  getCanvas: () => canvasRef.value
})
</script>

<style scoped>
.whiteboard-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #f3f4f6;
}

.whiteboard-canvas {
  cursor: crosshair;
}

.remote-cursor {
  position: absolute;
  pointer-events: none;
  z-index: 100;
  transition: left 0.05s, top 0.05s;
}

.comment-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  cursor: pointer;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 2px solid #e5e7eb;
  transition: all 0.2s;
}

.comment-marker:hover {
  transform: translate(-50%, -50%) scale(1.1);
  border-color: var(--primary-color);
}

.comment-marker.active {
  border-color: var(--primary-color);
  background: #eff6ff;
}

.comment-marker.resolved {
  opacity: 0.6;
}

.marker-icon {
  font-size: 16px;
}

.reply-count {
  font-size: 11px;
  background: var(--primary-color);
  color: white;
  border-radius: 10px;
  padding: 1px 5px;
  min-width: 16px;
  text-align: center;
}
</style>
