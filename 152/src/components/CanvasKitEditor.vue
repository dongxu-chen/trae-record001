<template>
  <div class="editor">
    <div class="toolbar">
      <div class="tool-group">
        <button
          v-for="tool in tools"
          :key="tool.id"
          :class="{ active: currentTool === tool.id }"
          @click="setTool(tool.id)"
          class="tool-btn"
        >
          {{ tool.icon }} {{ tool.name }}
        </button>
      </div>
      
      <div class="tool-group">
        <button @click="undo" class="tool-btn" :disabled="historyIndex <= 0">
          ↩️ 撤销
        </button>
        <button @click="redo" class="tool-btn" :disabled="historyIndex >= history.length - 1">
          ↪️ 重做
        </button>
      </div>
      
      <div class="tool-group">
        <button @click="toggleGrid" :class="{ active: showGrid }" class="tool-btn">
          🔲 网格
        </button>
        <button @click="toggleSnap" :class="{ active: snapToGrid }" class="tool-btn">
          🧲 吸附
        </button>
      </div>
      
      <div class="tool-group">
        <button @click="showImportModal = true" class="tool-btn import-btn">
          📥 导入PDF
        </button>
        <div class="export-dropdown">
          <button @click="showExportMenu = !showExportMenu" class="tool-btn export-btn">
            📤 导出 ▾
          </button>
          <div v-if="showExportMenu" class="export-menu" @click.stop>
            <button @click="exportSVG" class="export-option">
              SVG 格式
            </button>
            <button @click="exportPNG" class="export-option">
              PNG 格式
            </button>
            <button @click="exportLottie" class="export-option">
              Lottie 动画
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="layers-panel">
        <h3>图层</h3>
        <div class="layer-list">
          <div
            v-for="(path, index) in paths"
            :key="path.id"
            :class="{ active: selectedIds.includes(path.id) }"
            class="layer-item"
            @click="selectPath(path.id, $event)"
          >
            <div class="layer-info">
              <span class="layer-visibility" @click.stop="toggleVisibility(path.id)">
                {{ path.visible ? '👁️' : '👁️‍🗨️' }}
              </span>
              <span class="layer-name">{{ path.name }}</span>
            </div>
            <button class="layer-delete" @click.stop="deletePath(path.id)">
              🗑️
            </button>
          </div>
        </div>
        <button @click="addPath" class="add-layer-btn">+ 新建路径</button>

        <div v-if="selectedPaths.length >= 2" class="boolean-operations">
          <h4>布尔运算 (选中{{ selectedPaths.length }}个)</h4>
          <div class="boolean-buttons">
            <button @click="booleanUnion" class="boolean-btn">
              并集
            </button>
            <button @click="booleanSubtract" class="boolean-btn">
              差集
            </button>
            <button @click="booleanIntersect" class="boolean-btn">
              交集
            </button>
          </div>
        </div>

        <div class="icon-library">
          <h4>📦 图标库</h4>
          <div class="icon-grid">
            <div
              v-for="(icon, index) in iconLibrary"
              :key="index"
              class="icon-item"
              draggable="true"
              @dragstart="onIconDragStart($event, icon)"
              @click="addIconToCanvas(icon)"
            >
              <span class="icon-preview-emoji">{{ icon.emoji }}</span>
              <span class="icon-name">{{ icon.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <div
        class="canvas-container"
        ref="canvasContainer"
        @dragover.prevent
        @drop="onCanvasDrop"
      >
        <canvas ref="mainCanvas" id="main-canvas"></canvas>
      </div>

      <div class="properties-panel">
        <h3>属性</h3>
        <div v-if="selectedPaths.length === 1" class="property-group">
          <label>填充颜色</label>
          <input type="color" v-model="fillColorHex" @input="updateFillColor" />
        </div>
        <div v-if="selectedPaths.length === 1" class="property-group">
          <label>描边颜色</label>
          <input type="color" v-model="strokeColorHex" @input="updateStrokeColor" />
        </div>
        <div v-if="selectedPaths.length === 1" class="property-group">
          <label>描边宽度</label>
          <input type="range" v-model.number="strokeWidth" min="0" max="20" @input="updateStrokeWidth" />
          <span>{{ strokeWidth }}px</span>
        </div>
        <div v-else class="no-selection">
          选择一个图形以编辑属性
        </div>
      </div>
    </div>

    <div class="status-bar">
      <span>CanvasKit - GPU 加速渲染</span>
      <span>工具: {{ currentToolName }}</span>
      <span>选中: {{ selectedIds.length }} 个</span>
    </div>

    <div v-if="showImportModal" class="modal-overlay" @click="showImportModal = false">
      <div class="modal-content" @click.stop>
        <h3>导入 PDF</h3>
        <input type="file" accept=".pdf" @change="onPDFSelect" ref="pdfInput" />
        <button @click="showImportModal = false" class="close-btn">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { engine } from '../engine/CanvasKitEngine'
import PathModel from '../models/PathModel'
import { pdfImporter } from '../utils/PDFImporter'
import LottieExporter from '../utils/LottieExporter'

const canvasContainer = ref(null)
const mainCanvas = ref(null)
const pdfInput = ref(null)

const tools = [
  { id: 'select', name: '选择', icon: '👆' },
  { id: 'pen', name: '钢笔', icon: '✒️' },
  { id: 'rectangle', name: '矩形', icon: '⬜' },
  { id: 'circle', name: '圆形', icon: '⭕' }
]

const iconLibrary = [
  { name: '星形', emoji: '⭐', type: 'star' },
  { name: '心形', emoji: '❤️', type: 'heart' },
  { name: '三角形', emoji: '🔺', type: 'triangle' },
  { name: '菱形', emoji: '💎', type: 'diamond' },
  { name: '五边形', emoji: '⬟', type: 'pentagon' },
  { name: '六边形', emoji: '⬢', type: 'hexagon' },
  { name: '箭头', emoji: '➡️', type: 'arrow' },
  { name: '闪电', emoji: '⚡', type: 'lightning' },
  { name: '云朵', emoji: '☁️', type: 'cloud' },
  { name: '月亮', emoji: '🌙', type: 'moon' },
  { name: '太阳', emoji: '☀️', type: 'sun' },
  { name: '房子', emoji: '🏠', type: 'house' }
]

const currentTool = ref('select')
const paths = ref([])
const selectedIds = ref([])
const showGrid = ref(true)
const snapToGrid = ref(true)
const gridSize = ref(20)
const showExportMenu = ref(false)
const showImportModal = ref(false)

const history = ref([])
const historyIndex = ref(-1)
const MAX_HISTORY = 50
let isRestoringHistory = false

const fillColorHex = ref('#3399ff')
const strokeColorHex = ref('#0066cc')
const strokeWidth = ref(2)

let isDrawing = false
let currentPath = null
let startPoint = null
let dragOffset = null

const currentToolName = computed(() => {
  return tools.find(t => t.id === currentTool.value)?.name || ''
})

const selectedPaths = computed(() => {
  return paths.value.filter(p => selectedIds.value.includes(p.id))
})

function hexToRgba(hex, alpha = 1) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? [
    parseInt(result[1], 16) / 255,
    parseInt(result[2], 16) / 255,
    parseInt(result[3], 16) / 255,
    alpha
  ] : [0, 0, 0, 1]
}

function rgbaToHex(rgba) {
  const [r, g, b] = rgba
  return '#' + [r, g, b].map(x => {
    const hex = Math.round(x * 255).toString(16)
    return hex.length === 1 ? '0' + hex : hex
  }).join('')
}

function snapPoint(x, y) {
  if (!snapToGrid.value) return { x, y }
  return {
    x: Math.round(x / gridSize.value) * gridSize.value,
    y: Math.round(y / gridSize.value) * gridSize.value
  }
}

function saveSnapshot() {
  if (isRestoringHistory) return
  
  const snapshot = paths.value.map(p => p.toJSON())
  
  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }
  
  history.value.push(snapshot)
  
  if (history.value.length > MAX_HISTORY) {
    history.value.shift()
  }
  
  historyIndex.value = history.value.length - 1
}

function undo() {
  if (historyIndex.value <= 0) return
  
  isRestoringHistory = true
  historyIndex.value--
  
  const snapshot = history.value[historyIndex.value]
  paths.value = snapshot.map(json => PathModel.fromJSON(json))
  
  selectedIds.value = []
  isRestoringHistory = false
  
  render()
}

function redo() {
  if (historyIndex.value >= history.value.length - 1) return
  
  isRestoringHistory = true
  historyIndex.value++
  
  const snapshot = history.value[historyIndex.value]
  paths.value = snapshot.map(json => PathModel.fromJSON(json))
  
  selectedIds.value = []
  isRestoringHistory = false
  
  render()
}

function setTool(toolId) {
  currentTool.value = toolId
}

function toggleGrid() {
  showGrid.value = !showGrid.value
  render()
}

function toggleSnap() {
  snapToGrid.value = !snapToGrid.value
}

function selectPath(id, event) {
  if (event.shiftKey) {
    const idx = selectedIds.value.indexOf(id)
    if (idx >= 0) {
      selectedIds.value.splice(idx, 1)
    } else {
      selectedIds.value.push(id)
    }
  } else {
    selectedIds.value = [id]
  }
  
  if (selectedIds.value.length === 1) {
    const path = paths.value.find(p => p.id === selectedIds.value[0])
    if (path) {
      fillColorHex.value = rgbaToHex(path.fillColor)
      strokeColorHex.value = rgbaToHex(path.strokeColor)
      strokeWidth.value = path.strokeWidth
    }
  }
  
  render()
}

function toggleVisibility(id) {
  const path = paths.value.find(p => p.id === id)
  if (path) {
    path.visible = !path.visible
    render()
  }
}

function deletePath(id) {
  const idx = paths.value.findIndex(p => p.id === id)
  if (idx >= 0) {
    paths.value[idx].dispose()
    paths.value.splice(idx, 1)
    const selIdx = selectedIds.value.indexOf(id)
    if (selIdx >= 0) selectedIds.value.splice(selIdx, 1)
    saveSnapshot()
    render()
  }
}

function addPath() {
  const path = new PathModel({
    name: `路径 ${paths.value.length + 1}`
  })
  paths.value.push(path)
  saveSnapshot()
  render()
}

function updateFillColor() {
  if (selectedIds.value.length === 1) {
    const path = paths.value.find(p => p.id === selectedIds.value[0])
    if (path) {
      path.fillColor = hexToRgba(fillColorHex.value, 1)
      render()
    }
  }
}

function updateStrokeColor() {
  if (selectedIds.value.length === 1) {
    const path = paths.value.find(p => p.id === selectedIds.value[0])
    if (path) {
      path.strokeColor = hexToRgba(strokeColorHex.value, 1)
      render()
    }
  }
}

function updateStrokeWidth() {
  if (selectedIds.value.length === 1) {
    const path = paths.value.find(p => p.id === selectedIds.value[0])
    if (path) {
      path.strokeWidth = strokeWidth.value
      render()
    }
  }
}

function getCanvasPoint(event) {
  const rect = mainCanvas.value.getBoundingClientRect()
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
}

function onMouseDown(event) {
  const point = getCanvasPoint(event)
  const snapped = snapPoint(point.x, point.y)
  
  if (currentTool.value === 'select') {
    let found = false
    for (let i = paths.value.length - 1; i >= 0; i--) {
      const path = paths.value[i]
      if (!path.visible) continue
      
      const skPath = path.getPath(engine.CanvasKit)
      if (skPath && skPath.contains(point.x, point.y)) {
        selectPath(path.id, event)
        dragOffset = { x: point.x, y: point.y }
        found = true
        break
      }
    }
    if (!found && !event.shiftKey) {
      selectedIds.value = []
      render()
    }
  } else if (currentTool.value === 'pen') {
    if (!isDrawing) {
      isDrawing = true
      currentPath = new PathModel({
        name: `路径 ${paths.value.length + 1}`
      })
      currentPath.moveTo(snapped.x, snapped.y)
    } else {
      currentPath.lineTo(snapped.x, snapped.y)
    }
    render()
  } else if (currentTool.value === 'rectangle' || currentTool.value === 'circle') {
    isDrawing = true
    startPoint = snapped
    currentPath = new PathModel({
      name: `路径 ${paths.value.length + 1}`
    })
  }
}

function onMouseMove(event) {
  const point = getCanvasPoint(event)
  const snapped = snapPoint(point.x, point.y)
  
  if (currentTool.value === 'select' && dragOffset && selectedIds.value.length > 0) {
    const dx = snapped.x - dragOffset.x
    const dy = snapped.y - dragOffset.y
    
    selectedIds.value.forEach(id => {
      const path = paths.value.find(p => p.id === id)
      if (path) {
        path.translate(dx, dy)
      }
    })
    
    dragOffset = { x: snapped.x, y: snapped.y }
    render()
  } else if (isDrawing && currentPath) {
    if (currentTool.value === 'rectangle') {
      currentPath.pathData = ''
      const w = snapped.x - startPoint.x
      const h = snapped.y - startPoint.y
      currentPath.addRect(startPoint.x, startPoint.y, w, h)
      render()
    } else if (currentTool.value === 'circle') {
      currentPath.pathData = ''
      const dx = snapped.x - startPoint.x
      const dy = snapped.y - startPoint.y
      const r = Math.sqrt(dx * dx + dy * dy)
      currentPath.addCircle(startPoint.x, startPoint.y, r)
      render()
    }
  }
}

function onMouseUp(event) {
  dragOffset = null
  
  if (isDrawing && currentPath && currentPath.pathData) {
    paths.value.push(currentPath)
    selectedIds.value = [currentPath.id]
    saveSnapshot()
  }
  
  if (currentTool.value !== 'pen') {
    isDrawing = false
    currentPath = null
  }
  render()
}

function onKeyDown(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === 'z') {
    event.preventDefault()
    undo()
  }
  if ((event.ctrlKey || event.metaKey) && event.key === 'y') {
    event.preventDefault()
    redo()
  }
  if (event.key === 'Enter') {
    if (isDrawing && currentPath) {
      currentPath.close()
      paths.value.push(currentPath)
      selectedIds.value = [currentPath.id]
      saveSnapshot()
      isDrawing = false
      currentPath = null
      render()
    }
  }
  if (event.key === 'Escape') {
    isDrawing = false
    currentPath = null
    selectedIds.value = []
    render()
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedIds.value.length > 0) {
      selectedIds.value.slice().forEach(id => deletePath(id))
    }
  }
}

function onIconDragStart(event, icon) {
  event.dataTransfer.setData('icon-type', icon.type)
}

function onCanvasDrop(event) {
  event.preventDefault()
  const iconType = event.dataTransfer.getData('icon-type')
  const icon = iconLibrary.find(i => i.type === iconType)
  if (icon) {
    const point = getCanvasPoint(event)
    addIconToCanvas(icon, point.x, point.y)
  }
}

function addIconToCanvas(icon, x = 400, y = 300) {
  const path = new PathModel({
    name: icon.name,
    fillColor: hexToRgba(getIconColor(icon.type), 1)
  })
  
  const size = 50
  switch (icon.type) {
    case 'star':
      const points = []
      for (let i = 0; i < 5; i++) {
        const angle = (i * 72 - 90) * Math.PI / 180
        const innerAngle = ((i * 72) + 36 - 90) * Math.PI / 180
        points.push([x + size * Math.cos(angle), y + size * Math.sin(angle)])
        points.push([x + size * 0.4 * Math.cos(innerAngle), y + size * 0.4 * Math.sin(innerAngle)])
      }
      path.moveTo(points[0][0], points[0][1])
      for (let i = 1; i < points.length; i++) {
        path.lineTo(points[i][0], points[i][1])
      }
      path.close()
      break
    case 'heart':
      path.pathData = `M${x},${y + size * 0.3}
        C${x - size * 0.5},${y - size * 0.3} ${x - size},${y + size * 0.3} ${x},${y + size}
        C${x + size},${y + size * 0.3} ${x + size * 0.5},${y - size * 0.3} ${x},${y + size * 0.3}Z`
      break
    case 'triangle':
      path.moveTo(x, y - size)
      path.lineTo(x + size, y + size * 0.8)
      path.lineTo(x - size, y + size * 0.8)
      path.close()
      break
    case 'diamond':
      path.moveTo(x, y - size)
      path.lineTo(x + size * 0.7, y)
      path.lineTo(x, y + size)
      path.lineTo(x - size * 0.7, y)
      path.close()
      break
    case 'pentagon':
      for (let i = 0; i < 5; i++) {
        const angle = (i * 72 - 90) * Math.PI / 180
        if (i === 0) path.moveTo(x + size * Math.cos(angle), y + size * Math.sin(angle))
        else path.lineTo(x + size * Math.cos(angle), y + size * Math.sin(angle))
      }
      path.close()
      break
    case 'hexagon':
      for (let i = 0; i < 6; i++) {
        const angle = (i * 60 - 30) * Math.PI / 180
        if (i === 0) path.moveTo(x + size * Math.cos(angle), y + size * Math.sin(angle))
        else path.lineTo(x + size * Math.cos(angle), y + size * Math.sin(angle))
      }
      path.close()
      break
    case 'arrow':
      path.moveTo(x - size, y)
      path.lineTo(x + size * 0.3, y)
      path.lineTo(x + size * 0.3, y - size * 0.4)
      path.lineTo(x + size, y)
      path.lineTo(x + size * 0.3, y + size * 0.4)
      path.lineTo(x + size * 0.3, y)
      path.close()
      break
    case 'lightning':
      path.moveTo(x, y - size)
      path.lineTo(x - size * 0.4, y - size * 0.1)
      path.lineTo(x + size * 0.1, y - size * 0.1)
      path.lineTo(x - size * 0.3, y + size)
      path.lineTo(x + size * 0.2, y + size * 0.1)
      path.lineTo(x - size * 0.2, y + size * 0.1)
      path.close()
      break
    case 'cloud':
      path.pathData = `M${x + size},${y}
        C${x + size},${y - size * 0.6} ${x + size * 0.5},${y - size * 0.8} ${x},${y - size * 0.5}
        C${x - size * 0.3},${y - size * 0.8} ${x - size},${y - size * 0.5} ${x - size},${y}
        C${x - size * 1.2},${y} ${x - size * 1.2},${y + size * 0.6} ${x - size},${y + size * 0.6}
        L${x + size},${y + size * 0.6}
        C${x + size * 1.2},${y + size * 0.6} ${x + size * 1.2},${y} ${x + size},${y}Z`
      break
    case 'moon':
      path.pathData = `M${x},${y - size}
        C${x - size * 0.5},${y - size} ${x - size},${y - size * 0.5} ${x - size},${y}
        C${x - size},${y + size * 0.5} ${x - size * 0.5},${y + size} ${x},${y + size}
        C${x - size * 0.3},${y + size * 0.7} ${x - size * 0.5},${y + size * 0.4} ${x - size * 0.5},${y}
        C${x - size * 0.5},${y - size * 0.4} ${x - size * 0.3},${y - size * 0.7} ${x},${y - size}Z`
      break
    case 'sun':
      path.addCircle(x, y, size * 0.5)
      break
    case 'house':
      path.moveTo(x - size, y + size * 0.5)
      path.lineTo(x - size, y - size * 0.2)
      path.lineTo(x, y - size)
      path.lineTo(x + size, y - size * 0.2)
      path.lineTo(x + size, y + size * 0.5)
      path.close()
      break
  }
  
  paths.value.push(path)
  selectedIds.value = [path.id]
  saveSnapshot()
  render()
}

function getIconColor(type) {
  const colors = {
    star: '#ffd700',
    heart: '#ff4444',
    triangle: '#9955ff',
    diamond: '#3399ff',
    pentagon: '#33cc99',
    hexagon: '#ff9933',
    arrow: '#33cc33',
    lightning: '#ffcc00',
    cloud: '#99aabb',
    moon: '#666688',
    sun: '#ffdd33',
    house: '#aa6633'
  }
  return colors[type] || '#3399ff'
}

function performBooleanOperation(operation) {
  if (selectedIds.value.length < 2) return
  
  const ck = engine.CanvasKit
  const selectedPaths = selectedIds.value.map(id => paths.value.find(p => p.id === id))
  
  let resultPath = selectedPaths[0].getPath(ck)
  
  for (let i = 1; i < selectedPaths.length; i++) {
    const otherPath = selectedPaths[i].getPath(ck)
    resultPath = resultPath.op(otherPath, operation)
  }
  
  if (resultPath) {
    const simplified = resultPath.simplify()
    const svgData = simplified.toSVGString()
    
    const newPath = new PathModel({
      pathData: svgData,
      name: '布尔结果',
      fillColor: selectedPaths[0].fillColor,
      strokeColor: selectedPaths[0].strokeColor,
      strokeWidth: selectedPaths[0].strokeWidth
    })
    
    selectedIds.value.slice().forEach(id => deletePath(id))
    
    paths.value.push(newPath)
    selectedIds.value = [newPath.id]
    saveSnapshot()
    render()
  }
}

function booleanUnion() {
  performBooleanOperation(engine.CanvasKit.PathOp.Union)
}

function booleanSubtract() {
  performBooleanOperation(engine.CanvasKit.PathOp.Difference)
}

function booleanIntersect() {
  performBooleanOperation(engine.CanvasKit.PathOp.Intersect)
}

function exportSVG() {
  showExportMenu.value = false
  
  let svgContent = '<?xml version="1.0" encoding="UTF-8"?>\n'
  svgContent += '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="800" height="600">\n'
  
  paths.value.forEach(path => {
    if (!path.visible) return
    
    const fill = `rgba(${Math.round(path.fillColor[0] * 255)}, ${Math.round(path.fillColor[1] * 255)}, ${Math.round(path.fillColor[2] * 255)}, ${path.fillColor[3]})`
    const stroke = `rgba(${Math.round(path.strokeColor[0] * 255)}, ${Math.round(path.strokeColor[1] * 255)}, ${Math.round(path.strokeColor[2] * 255)}, ${path.strokeColor[3]})`
    
    svgContent += `  <path d="${path.pathData}" fill="${fill}" stroke="${stroke}" stroke-width="${path.strokeWidth}" />\n`
  })
  
  svgContent += '</svg>'
  
  const blob = new Blob([svgContent], { type: 'image/svg+xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'drawing.svg'
  a.click()
  URL.revokeObjectURL(url)
}

function exportPNG() {
  showExportMenu.value = false
  
  const canvas = document.createElement('canvas')
  canvas.width = 800
  canvas.height = 600
  const ctx = canvas.getContext('2d')
  
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  paths.value.forEach(path => {
    if (!path.visible) return
    
    const p = new Path2D(path.pathData)
    
    const fill = `rgba(${Math.round(path.fillColor[0] * 255)}, ${Math.round(path.fillColor[1] * 255)}, ${Math.round(path.fillColor[2] * 255)}, ${path.fillColor[3]})`
    ctx.fillStyle = fill
    ctx.fill(p)
    
    const stroke = `rgba(${Math.round(path.strokeColor[0] * 255)}, ${Math.round(path.strokeColor[1] * 255)}, ${Math.round(path.strokeColor[2] * 255)}, ${path.strokeColor[3]})`
    ctx.strokeStyle = stroke
    ctx.lineWidth = path.strokeWidth
    ctx.stroke(p)
  })
  
  canvas.toBlob(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'drawing.png'
    a.click()
    URL.revokeObjectURL(url)
  })
}

function exportLottie() {
  showExportMenu.value = false
  
  const exporter = new LottieExporter()
  exporter.setSize(800, 600)
  exporter.addLayer(paths.value.filter(p => p.visible))
  exporter.download('animation.json')
}

async function onPDFSelect(event) {
  const file = event.target.files[0]
  if (!file) return
  
  try {
    const pageData = await pdfImporter.importPDF(file)
    
    pageData.paths.forEach((pathData, index) => {
      const path = new PathModel({
        pathData,
        name: `PDF 路径 ${index + 1}`,
        fillColor: [0.8, 0.2, 0.2, 1],
        strokeColor: [0, 0, 0, 1],
        strokeWidth: 1
      })
      paths.value.push(path)
    })
    
    saveSnapshot()
    render()
    showImportModal.value = false
  } catch (e) {
    console.error('PDF导入失败:', e)
    alert('PDF导入失败: ' + e.message)
  }
}

function render() {
  if (!engine.initialized) return
  
  const ck = engine.CanvasKit
  const canvas = engine.canvas
  const width = engine.width
  const height = engine.height
  
  canvas.clear([1, 1, 1, 1])
  
  if (showGrid.value) {
    const gridPaint = new ck.Paint()
    gridPaint.setColor([0.8, 0.8, 0.8, 1])
    gridPaint.setStrokeWidth(1)
    gridPaint.setAntiAlias(true)
    
    for (let x = 0; x <= width; x += gridSize.value) {
      canvas.drawLine(x, 0, x, height, gridPaint)
    }
    for (let y = 0; y <= height; y += gridSize.value) {
      canvas.drawLine(0, y, width, y, gridPaint)
    }
    
    gridPaint.delete()
  }
  
  paths.value.forEach(path => {
    if (!path.visible) return
    
    const skPath = path.getPath(ck)
    if (!skPath) return
    
    const isSelected = selectedIds.value.includes(path.id)
    
    const fillPaint = new ck.Paint()
    fillPaint.setColor(path.fillColor)
    fillPaint.setAntiAlias(true)
    canvas.drawPath(skPath, fillPaint)
    fillPaint.delete()
    
    const strokePaint = new ck.Paint()
    strokePaint.setColor(isSelected ? [1, 0.5, 0, 1] : path.strokeColor)
    strokePaint.setStrokeWidth(isSelected ? path.strokeWidth + 2 : path.strokeWidth)
    strokePaint.setStyle(ck.PaintStyle.Stroke)
    strokePaint.setAntiAlias(true)
    canvas.drawPath(skPath, strokePaint)
    strokePaint.delete()
  })
  
  if (isDrawing && currentPath && currentPath.pathData) {
    const skPath = currentPath.getPath(ck)
    if (skPath) {
      const previewPaint = new ck.Paint()
      previewPaint.setColor([0.2, 0.6, 1, 0.5])
      previewPaint.setStyle(ck.PaintStyle.Stroke)
      previewPaint.setStrokeWidth(2)
      previewPaint.setAntiAlias(true)
      canvas.drawPath(skPath, previewPaint)
      previewPaint.delete()
    }
  }
  
  engine.flush()
}

onMounted(async () => {
  await nextTick()
  
  const container = canvasContainer.value
  const canvas = mainCanvas.value
  
  canvas.width = container.clientWidth
  canvas.height = container.clientHeight
  
  await engine.init(canvas, canvas.width, canvas.height)
  
  window.addEventListener('mousedown', onMouseDown)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('keydown', onKeyDown)
  
  document.addEventListener('click', () => {
    showExportMenu.value = false
  })
  
  saveSnapshot()
  render()
})

onUnmounted(() => {
  window.removeEventListener('mousedown', onMouseDown)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('keydown', onKeyDown)
  
  paths.value.forEach(p => p.dispose())
  engine.dispose()
})
</script>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: #1a1a2e;
}

.toolbar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding: 10px 20px;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
  gap: 20px;
  flex-wrap: wrap;
}

.tool-group {
  display: flex;
  gap: 8px;
}

.tool-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #0f3460;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.tool-btn:hover {
  background: #1a4a80;
}

.tool-btn.active {
  background: #e94560;
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.export-btn, .import-btn {
  background: #27ae60;
}

.export-btn:hover, .import-btn:hover {
  background: #2ecc71;
}

.export-dropdown {
  position: relative;
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 5px;
  background: #16213e;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  min-width: 150px;
}

.export-option {
  display: block;
  width: 100%;
  padding: 10px 15px;
  border: none;
  background: transparent;
  color: #fff;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s;
  border-radius: 6px;
}

.export-option:hover {
  background: #0f3460;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.layers-panel {
  width: 280px;
  background: #16213e;
  padding: 15px;
  border-right: 1px solid #0f3460;
  overflow-y: auto;
}

.layers-panel h3, .layers-panel h4 {
  margin-bottom: 15px;
  font-size: 16px;
  color: #e94560;
}

.layers-panel h4 {
  font-size: 14px;
  color: #3498db;
  margin-top: 20px;
}

.layer-list {
  margin-bottom: 15px;
}

.layer-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  margin-bottom: 5px;
  background: #0f3460;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.layer-item:hover {
  background: #1a4a80;
}

.layer-item.active {
  background: #e94560;
}

.layer-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.layer-visibility {
  cursor: pointer;
  font-size: 16px;
}

.layer-name {
  font-size: 14px;
  color: #fff;
}

.layer-delete {
  background: none;
  border: none;
  color: #e74c3c;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.layer-delete:hover {
  background: rgba(231, 76, 60, 0.2);
}

.add-layer-btn {
  width: 100%;
  padding: 10px;
  border: 2px dashed #3498db;
  border-radius: 6px;
  background: transparent;
  color: #3498db;
  cursor: pointer;
  transition: all 0.2s;
}

.add-layer-btn:hover {
  background: rgba(52, 152, 219, 0.1);
}

.boolean-operations {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #0f3460;
}

.boolean-buttons {
  display: flex;
  gap: 5px;
}

.boolean-btn {
  flex: 1;
  padding: 8px;
  border: none;
  border-radius: 4px;
  background: #f39c12;
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.boolean-btn:hover {
  background: #e67e22;
}

.icon-library {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #0f3460;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.icon-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  background: #0f3460;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.icon-item:hover {
  background: #1a4a80;
  border-color: #e94560;
  transform: scale(1.05);
}

.icon-item:active {
  cursor: grabbing;
}

.icon-preview-emoji {
  font-size: 24px;
  margin-bottom: 5px;
}

.icon-name {
  font-size: 11px;
  color: #bdc3c7;
  text-align: center;
}

.canvas-container {
  flex: 1;
  background: #fff;
  overflow: hidden;
  cursor: crosshair;
}

#main-canvas {
  width: 100%;
  height: 100%;
}

.properties-panel {
  width: 250px;
  background: #16213e;
  padding: 15px;
  border-left: 1px solid #0f3460;
}

.properties-panel h3 {
  margin-bottom: 15px;
  font-size: 16px;
  color: #e94560;
}

.property-group {
  margin-bottom: 15px;
}

.property-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #bdc3c7;
}

.property-group input[type="color"] {
  width: 100%;
  height: 40px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
}

.property-group input[type="range"] {
  width: 100%;
  margin-bottom: 5px;
}

.property-group span {
  font-size: 12px;
  color: #95a5a6;
}

.no-selection {
  color: #7f8c8d;
  font-size: 14px;
  text-align: center;
  padding: 20px;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  padding: 8px 20px;
  background: #16213e;
  border-top: 1px solid #0f3460;
  font-size: 12px;
  color: #95a5a6;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-content {
  background: #16213e;
  padding: 30px;
  border-radius: 12px;
  color: #fff;
  min-width: 400px;
}

.modal-content h3 {
  margin-bottom: 20px;
  color: #e94560;
}

.modal-content input[type="file"] {
  width: 100%;
  margin-bottom: 20px;
  padding: 10px;
  background: #0f3460;
  border-radius: 6px;
}

.close-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  background: #e94560;
  color: #fff;
  cursor: pointer;
}
</style>
