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
        <button @click="undo" class="tool-btn undo-btn" :disabled="historyIndex <= 0">
          ↩️ 撤销
        </button>
        <button @click="redo" class="tool-btn redo-btn" :disabled="historyIndex >= history.length - 1">
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
        <div class="export-dropdown" ref="exportDropdown">
          <button @click="showExportMenu = !showExportMenu" class="tool-btn export-btn">
            📤 导出 ▾
          </button>
          <div v-if="showExportMenu" class="export-menu">
            <button @click="exportSVG; showExportMenu = false" class="export-option">
              SVG 格式
            </button>
            <button @click="exportPNG; showExportMenu = false" class="export-option">
              PNG 格式
            </button>
            <button @click="exportPDF; showExportMenu = false" class="export-option">
              PDF 格式
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
            v-for="(layer, index) in layers"
            :key="layer.id"
            :class="{ active: activeLayer === layer.id }"
            class="layer-item"
          >
            <div class="layer-info" @click="selectLayer(layer.id)">
              <span class="layer-visibility" @click.stop="toggleLayerVisibility(layer.id)">
                {{ layer.visible ? '👁️' : '👁️‍🗨️' }}
              </span>
              <span class="layer-name">{{ layer.name }}</span>
            </div>
            <div class="layer-controls" v-if="layers.length > 1">
              <button class="layer-move" @click.stop="moveLayerUp(layer.id)" v-if="index > 0">
                ⬆️
              </button>
              <button class="layer-move" @click.stop="moveLayerDown(layer.id)" v-if="index < layers.length - 1">
                ⬇️
              </button>
              <button class="layer-delete" @click.stop="deleteLayer(layer.id)">
                🗑️
              </button>
            </div>
          </div>
        </div>
        <button @click="addLayer" class="add-layer-btn">+ 新建图层</button>

        <div v-if="selectedItems.length > 0" class="boolean-operations">
          <h4>布尔运算 (选中{{ selectedItems.length }}个)</h4>
          <div class="boolean-buttons">
            <button @click="booleanUnion" class="boolean-btn" :disabled="selectedItems.length < 2">
              并集
            </button>
            <button @click="booleanSubtract" class="boolean-btn" :disabled="selectedItems.length < 2">
              差集
            </button>
            <button @click="booleanIntersect" class="boolean-btn" :disabled="selectedItems.length < 2">
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
              <svg :viewBox="icon.viewBox" class="icon-preview">
                <path :d="icon.path" :fill="icon.fill || '#3498db'" />
              </svg>
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
        <canvas ref="paperCanvas" id="paper-canvas"></canvas>
      </div>

      <div class="properties-panel">
        <h3>属性</h3>
        <div v-if="selectedItems.length === 1" class="property-group">
          <label>填充颜色</label>
          <input type="color" v-model="fillColor" @input="updateFillColor" />
        </div>
        <div v-if="selectedItems.length === 1" class="property-group">
          <label>描边颜色</label>
          <input type="color" v-model="strokeColor" @input="updateStrokeColor" />
        </div>
        <div v-if="selectedItems.length === 1" class="property-group">
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
      <span>工具: {{ currentToolName }}</span>
      <span>选中: {{ selectedItems.length }} 个</span>
      <span>图层: {{ activeLayerName }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import paper from 'paper'

const canvasContainer = ref(null)
const paperCanvas = ref(null)

const tools = [
  { id: 'select', name: '选择', icon: '👆' },
  { id: 'pen', name: '钢笔', icon: '✒️' },
  { id: 'rectangle', name: '矩形', icon: '⬜' },
  { id: 'circle', name: '圆形', icon: '⭕' }
]

const currentTool = ref('select')
const layers = ref([
  { id: 1, name: '图层 1', visible: true, paperLayer: null }
])
const activeLayer = ref(1)
const selectedItems = ref([])
const fillColor = ref('#3498db')
const strokeColor = ref('#2980b9')
const strokeWidth = ref(2)

const showExportMenu = ref(false)
const showGrid = ref(true)
const snapToGrid = ref(true)
const gridSize = ref(20)

const history = ref([])
const historyIndex = ref(-1)
const MAX_HISTORY = 50
let isRestoringHistory = false

let draggedIcon = null
let guideLines = { horizontal: null, vertical: null }
let gridLayer = null

let path = null
let hitOptions = {
  segments: true,
  stroke: true,
  fill: true,
  tolerance: 5
}
let layerIdCounter = 1

const iconLibrary = [
  { name: '星形', path: 'M24 0l6.6 19.8H50.7L35.7 32.2l6.1 19.8L24 39.6 6.2 52 12.3 32.2 0 19.8h20.1L24 0z', viewBox: '0 0 50 52', fill: '#f39c12' },
  { name: '心形', path: 'M25.6 47.6L8.3 30.4C-2.8 19.3 5.5 1.2 18.9 7.4c4.1 1.9 7.3 5.2 9.2 9.3 1.9-4.1 5.1-7.4 9.2-9.3 13.4-6.2 21.7 11.9 10.6 23L25.6 47.6z', viewBox: '0 0 50 48', fill: '#e74c3c' },
  { name: '三角形', path: 'M25 0L50 43H0L25 0z', viewBox: '0 0 50 43', fill: '#9b59b6' },
  { name: '菱形', path: 'M25 0L50 25 25 50 0 25z', viewBox: '0 0 50 50', fill: '#3498db' },
  { name: '五边形', path: 'M25 0L50 19.1 40.5 50 9.5 50 0 19.1z', viewBox: '0 0 50 50', fill: '#1abc9c' },
  { name: '六边形', path: 'M12.5 0L37.5 0 50 21.7 37.5 43.3 12.5 43.3 0 21.7z', viewBox: '0 0 50 44', fill: '#e67e22' },
  { name: '箭头', path: 'M0 22L25 0 50 22 37.5 22 37.5 44 12.5 44 12.5 22z', viewBox: '0 0 50 44', fill: '#2ecc71' },
  { name: '闪电', path: 'M30 0L10 24h10L15 50 40 20h-10z', viewBox: '0 0 50 50', fill: '#f1c40f' },
  { name: '云', path: 'M40 16c0-6.6-5.4-12-12-12s-12 5.4-12 12c-5.5 0-10 4.5-10 10s4.5 10 10 10h24c4.4 0 8-3.6 8-8s-3.6-8-8-8z', viewBox: '0 0 50 46', fill: '#95a5a6' },
  { name: '月亮', path: 'M25 2C12.3 2 2 12.3 2 25s10.3 23 23 23c3.3 0 6.5-0.7 9.4-2-8.7-2.2-15.4-10.1-15.4-19.4 0-9.4 6.7-17.2 15.4-19.4-2.9-1.3-6.1-2-9.4-2z', viewBox: '0 0 50 50', fill: '#34495e' },
  { name: '太阳', path: 'M25 15c-5.5 0-10 4.5-10 10s4.5 10 10 10 10-4.5 10-10-4.5-10-10-10zm0-15c-1.1 0-2 0.9-2 2v6c0 1.1 0.9 2 2 2s2-0.9 2-2v-6c0-1.1-0.9-2-2-2zm0 42c-1.1 0-2 0.9-2 2v6c0 1.1 0.9 2 2 2s2-0.9 2-2v-6c0-1.1-0.9-2-2-2zM8.6 10.6c-0.8-0.8-2-0.8-2.8 0s-0.8 2 0 2.8l4.2 4.2c0.8 0.8 2 0.8 2.8 0s0.8-2 0-2.8L8.6 10.6zm32.8 25.2c-0.8-0.8-2-0.8-2.8 0s-0.8 2 0 2.8l4.2 4.2c0.8 0.8 2 0.8 2.8 0s0.8-2 0-2.8l-4.2-4.2zM2 27c-1.1 0-2-0.9-2-2s0.9-2 2-2h6c1.1 0 2 0.9 2 2s-0.9 2-2 2H2zm42 0c-1.1 0-2-0.9-2-2s0.9-2 2-2h6c1.1 0 2 0.9 2 2s-0.9 2-2 2h-6zM10.6 39.4c-0.8-0.8-2-0.8-2.8 0l-4.2 4.2c-0.8 0.8-0.8 2 0 2.8s2 0.8 2.8 0l4.2-4.2c0.8-0.8 0.8-2 0-2.8zm25.2-32.8c-0.8-0.8-2-0.8-2.8 0s-0.8 2 0 2.8l4.2 4.2c0.8 0.8 2 0.8 2.8 0s0.8-2 0-2.8l-4.2-4.2z', viewBox: '0 0 50 50', fill: '#f39c12' },
  { name: '房子', path: 'M2 21L25 2 48 21V50H32V34H18V50H2V21z', viewBox: '0 0 50 50', fill: '#8b4513' }
]

const currentToolName = computed(() => {
  return tools.find(t => t.id === currentTool.value)?.name || ''
})

const activeLayerName = computed(() => {
  return layers.value.find(l => l.id === activeLayer.value)?.name || ''
})

function setTool(toolId) {
  currentTool.value = toolId
  setupPaperTool()
}

function setupPaperTool() {
  paper.tool.remove()
  
  const tool = new paper.Tool()
  
  if (currentTool.value === 'select') {
    tool.onMouseDown = onSelectMouseDown
    tool.onMouseDrag = onSelectMouseDrag
    tool.onMouseUp = onSelectMouseUp
  } else if (currentTool.value === 'pen') {
    tool.onMouseDown = onPenMouseDown
    tool.onMouseDrag = onPenMouseDrag
  } else if (currentTool.value === 'rectangle') {
    tool.onMouseDown = onRectMouseDown
    tool.onMouseDrag = onRectMouseDrag
    tool.onMouseUp = onShapeMouseUp
  } else if (currentTool.value === 'circle') {
    tool.onMouseDown = onCircleMouseDown
    tool.onMouseDrag = onCircleMouseDrag
    tool.onMouseUp = onShapeMouseUp
  }
  
  tool.activate()
}

function onSelectMouseDown(event) {
  deselectAll()
  
  const hitResult = paper.project.hitTest(event.point, hitOptions)
  
  if (hitResult) {
    selectItem(hitResult.item)
  }
}

function onSelectMouseDrag(event) {
  if (selectedItems.value.length > 0) {
    selectedItems.value.forEach(item => {
      let newPos = item.position.add(event.delta)
      newPos = snapPointToGrid(newPos)
      item.position = newPos
    })
    showAlignmentGuides(selectedItems.value[0])
  }
}

function onSelectMouseUp(event) {
  removeAlignmentGuides()
  saveSnapshot()
}

function onPenMouseDown(event) {
  const point = snapPointToGrid(event.point)
  if (!path) {
    path = new paper.Path({
      segments: [point],
      strokeColor: strokeColor.value,
      strokeWidth: strokeWidth.value,
      fillColor: null,
      fullySelected: false
    })
    getActivePaperLayer().addChild(path)
  } else {
    path.add(point)
  }
}

function onPenMouseDrag(event) {
  if (path && path.segments.length > 0) {
    const lastSegment = path.segments[path.segments.length - 1]
    lastSegment.point = snapPointToGrid(event.point)
  }
}

let shapeStart = null
let tempShape = null

function onRectMouseDown(event) {
  shapeStart = snapPointToGrid(event.point)
  tempShape = new paper.Path.Rectangle({
    from: shapeStart,
    to: shapeStart,
    strokeColor: strokeColor.value,
    strokeWidth: strokeWidth.value,
    fillColor: fillColor.value
  })
  getActivePaperLayer().addChild(tempShape)
}

function onRectMouseDrag(event) {
  if (tempShape) {
    tempShape.remove()
    tempShape = new paper.Path.Rectangle({
      from: shapeStart,
      to: snapPointToGrid(event.point),
      strokeColor: strokeColor.value,
      strokeWidth: strokeWidth.value,
      fillColor: fillColor.value
    })
    getActivePaperLayer().addChild(tempShape)
  }
}

function onCircleMouseDown(event) {
  shapeStart = snapPointToGrid(event.point)
  tempShape = new paper.Path.Circle({
    center: shapeStart,
    radius: 0,
    strokeColor: strokeColor.value,
    strokeWidth: strokeWidth.value,
    fillColor: fillColor.value
  })
  getActivePaperLayer().addChild(tempShape)
}

function onCircleMouseDrag(event) {
  if (tempShape && shapeStart) {
    tempShape.remove()
    const point = snapPointToGrid(event.point)
    const radius = shapeStart.getDistance(point)
    tempShape = new paper.Path.Circle({
      center: shapeStart,
      radius: radius,
      strokeColor: strokeColor.value,
      strokeWidth: strokeWidth.value,
      fillColor: fillColor.value
    })
    getActivePaperLayer().addChild(tempShape)
  }
}

function onShapeMouseUp(event) {
  if (tempShape) {
    tempShape = null
    shapeStart = null
    saveSnapshot()
  }
}

function selectItem(item) {
  deselectAll()
  item.selected = true
  selectedItems.value = [item]
  
  if (item.fillColor) {
    fillColor.value = item.fillColor.toCSS()
  }
  if (item.strokeColor) {
    strokeColor.value = item.strokeColor.toCSS()
  }
  if (item.strokeWidth != null) {
    strokeWidth.value = item.strokeWidth
  }
}

function deselectAll() {
  selectedItems.value.forEach(item => {
    item.selected = false
  })
  selectedItems.value = []
}

function updateFillColor() {
  if (selectedItems.value.length === 1) {
    selectedItems.value[0].fillColor = fillColor.value
  }
}

function updateStrokeColor() {
  if (selectedItems.value.length === 1) {
    selectedItems.value[0].strokeColor = strokeColor.value
  }
  if (path) {
    path.strokeColor = strokeColor.value
  }
}

function updateStrokeWidth() {
  if (selectedItems.value.length === 1) {
    selectedItems.value[0].strokeWidth = strokeWidth.value
  }
  if (path) {
    path.strokeWidth = strokeWidth.value
  }
}

function addLayer() {
  layerIdCounter++
  const newId = layerIdCounter
  const paperLayer = new paper.Layer()
  paper.project.addLayer(paperLayer)
  layers.value.push({
    id: newId,
    name: `图层 ${newId}`,
    visible: true,
    paperLayer: paperLayer
  })
  activeLayer.value = newId
  paperLayer.activate()
  syncLayerOrder()
}

function syncLayerOrder() {
  for (let i = 0; i < layers.value.length; i++) {
    const layer = layers.value[i]
    if (layer.paperLayer) {
      layer.paperLayer.remove()
      paper.project.addLayer(layer.paperLayer)
    }
  }
  
  const activeLayerObj = layers.value.find(l => l.id === activeLayer.value)
  if (activeLayerObj && activeLayerObj.paperLayer) {
    activeLayerObj.paperLayer.activate()
  }
}

function moveLayerUp(id) {
  const index = layers.value.findIndex(l => l.id === id)
  if (index <= 0) return
  
  [layers.value[index], layers.value[index - 1]] = [layers.value[index - 1], layers.value[index]]
  syncLayerOrder()
}

function moveLayerDown(id) {
  const index = layers.value.findIndex(l => l.id === id)
  if (index >= layers.value.length - 1) return
  
  [layers.value[index], layers.value[index + 1]] = [layers.value[index + 1], layers.value[index]]
  syncLayerOrder()
}

function saveSnapshot() {
  if (isRestoringHistory) return
  
  const snapshot = paper.project.exportJSON({ asString: true })
  
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
  paper.project.clear()
  paper.project.importJSON(snapshot)
  
  layers.value.forEach(layer => {
    if (layer.paperLayer) {
      layer.paperLayer.remove()
    }
  })
  layers.value = [{ id: 1, name: '图层 1', visible: true, paperLayer: paper.project.activeLayer }]
  activeLayer.value = 1
  
  isRestoringHistory = false
  deselectAll()
}

function redo() {
  if (historyIndex.value >= history.value.length - 1) return
  
  isRestoringHistory = true
  historyIndex.value++
  
  const snapshot = history.value[historyIndex.value]
  paper.project.clear()
  paper.project.importJSON(snapshot)
  
  layers.value.forEach(layer => {
    if (layer.paperLayer) {
      layer.paperLayer.remove()
    }
  })
  layers.value = [{ id: 1, name: '图层 1', visible: true, paperLayer: paper.project.activeLayer }]
  activeLayer.value = 1
  
  isRestoringHistory = false
  deselectAll()
}

function toggleGrid() {
  showGrid.value = !showGrid.value
  updateGrid()
}

function toggleSnap() {
  snapToGrid.value = !snapToGrid.value
}

function updateGrid() {
  if (gridLayer) {
    gridLayer.removeChildren()
  }
  
  if (!showGrid.value) return
  
  const view = paper.view
  const width = view.bounds.width
  const height = view.bounds.height
  const size = gridSize.value
  
  for (let x = 0; x <= width; x += size) {
    const line = new paper.Path.Line({
      from: [x, 0],
      to: [x, height],
      strokeColor: new paper.Color(0.7, 0.7, 0.7, 0.3),
      strokeWidth: 1
    })
    gridLayer.addChild(line)
  }
  
  for (let y = 0; y <= height; y += size) {
    const line = new paper.Path.Line({
      from: [0, y],
      to: [width, y],
      strokeColor: new paper.Color(0.7, 0.7, 0.7, 0.3),
      strokeWidth: 1
    })
    gridLayer.addChild(line)
  }
}

function snapPointToGrid(point) {
  if (!snapToGrid.value) return point
  
  const size = gridSize.value
  return new paper.Point(
    Math.round(point.x / size) * size,
    Math.round(point.y / size) * size
  )
}

function showAlignmentGuides(item) {
  removeAlignmentGuides()
  
  if (!item) return
  
  const bounds = item.bounds
  const allItems = getActivePaperLayer().children.filter(child => child !== item && child.visible)
  
  allItems.forEach(other => {
    const otherBounds = other.bounds
    const threshold = 5
    
    if (Math.abs(bounds.left - otherBounds.left) < threshold) {
      guideLines.vertical = new paper.Path.Line({
        from: [otherBounds.left, 0],
        to: [otherBounds.left, paper.view.bounds.height],
        strokeColor: '#e74c3c',
        strokeWidth: 1,
        dashArray: [5, 5]
      })
    }
    
    if (Math.abs(bounds.centerX - otherBounds.centerX) < threshold) {
      guideLines.vertical = new paper.Path.Line({
        from: [otherBounds.centerX, 0],
        to: [otherBounds.centerX, paper.view.bounds.height],
        strokeColor: '#e74c3c',
        strokeWidth: 1,
        dashArray: [5, 5]
      })
    }
    
    if (Math.abs(bounds.right - otherBounds.right) < threshold) {
      guideLines.vertical = new paper.Path.Line({
        from: [otherBounds.right, 0],
        to: [otherBounds.right, paper.view.bounds.height],
        strokeColor: '#e74c3c',
        strokeWidth: 1,
        dashArray: [5, 5]
      })
    }
    
    if (Math.abs(bounds.top - otherBounds.top) < threshold) {
      guideLines.horizontal = new paper.Path.Line({
        from: [0, otherBounds.top],
        to: [paper.view.bounds.width, otherBounds.top],
        strokeColor: '#e74c3c',
        strokeWidth: 1,
        dashArray: [5, 5]
      })
    }
    
    if (Math.abs(bounds.centerY - otherBounds.centerY) < threshold) {
      guideLines.horizontal = new paper.Path.Line({
        from: [0, otherBounds.centerY],
        to: [paper.view.bounds.width, otherBounds.centerY],
        strokeColor: '#e74c3c',
        strokeWidth: 1,
        dashArray: [5, 5]
      })
    }
    
    if (Math.abs(bounds.bottom - otherBounds.bottom) < threshold) {
      guideLines.horizontal = new paper.Path.Line({
        from: [0, otherBounds.bottom],
        to: [paper.view.bounds.width, otherBounds.bottom],
        strokeColor: '#e74c3c',
        strokeWidth: 1,
        dashArray: [5, 5]
      })
    }
  })
}

function removeAlignmentGuides() {
  if (guideLines.horizontal) {
    guideLines.horizontal.remove()
    guideLines.horizontal = null
  }
  if (guideLines.vertical) {
    guideLines.vertical.remove()
    guideLines.vertical = null
  }
}

function onIconDragStart(event, icon) {
  draggedIcon = icon
  event.dataTransfer.effectAllowed = 'copy'
}

function onCanvasDrop(event) {
  event.preventDefault()
  if (!draggedIcon) return
  
  const rect = canvasContainer.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  
  addIconToCanvas(draggedIcon, new paper.Point(x, y))
  draggedIcon = null
  saveSnapshot()
}

function addIconToCanvas(icon, position = null) {
  const path = new paper.Path({
    pathData: icon.path,
    fillColor: icon.fill || fillColor.value,
    strokeColor: strokeColor.value,
    strokeWidth: strokeWidth.value
  })
  
  const bounds = path.bounds
  const scale = 60 / Math.max(bounds.width, bounds.height)
  path.scale(scale)
  
  if (position) {
    path.position = position
  } else {
    path.position = paper.view.center
  }
  
  getActivePaperLayer().addChild(path)
  selectItem(path)
}

function selectLayer(id) {
  activeLayer.value = id
  const layer = layers.value.find(l => l.id === id)
  if (layer && layer.paperLayer) {
    layer.paperLayer.activate()
  }
  deselectAll()
}

function toggleLayerVisibility(id) {
  const layer = layers.value.find(l => l.id === id)
  if (layer && layer.paperLayer) {
    layer.visible = !layer.visible
    layer.paperLayer.visible = layer.visible
  }
}

function deleteLayer(id) {
  if (layers.value.length <= 1) return
  
  const layerIndex = layers.value.findIndex(l => l.id === id)
  const layer = layers.value[layerIndex]
  
  if (layer.paperLayer) {
    layer.paperLayer.remove()
  }
  
  layers.value.splice(layerIndex, 1)
  
  if (activeLayer.value === id) {
    activeLayer.value = layers.value[0].id
    if (layers.value[0].paperLayer) {
      layers.value[0].paperLayer.activate()
    }
  }
  
  syncLayerOrder()
}

function getActivePaperLayer() {
  const layer = layers.value.find(l => l.id === activeLayer.value)
  return layer?.paperLayer || paper.project.activeLayer
}

function segmentsToPoints(segments) {
  return segments.map(seg => new paper.Point(seg.point.x, seg.point.y))
}

function pointsToSegments(points) {
  return points.map(point => new paper.Segment(point))
}

function perpendicularDistance(point, lineStart, lineEnd) {
  const dx = lineEnd.x - lineStart.x
  const dy = lineEnd.y - lineStart.y
  const mag = Math.sqrt(dx * dx + dy * dy)
  
  if (mag === 0) {
    return point.getDistance(lineStart)
  }
  
  const pvx = point.x - lineStart.x
  const pvy = point.y - lineStart.y
  const u = (pvx * dx + pvy * dy) / (mag * mag)
  
  if (u <= 0) {
    return point.getDistance(lineStart)
  } else if (u >= 1) {
    return point.getDistance(lineEnd)
  }
  
  const ix = lineStart.x + u * dx
  const iy = lineStart.y + u * dy
  return point.getDistance(new paper.Point(ix, iy))
}

function ramerDouglasPeucker(points, epsilon = 1.0) {
  if (points.length < 3) return points
  
  let maxDist = 0
  let index = 0
  
  for (let i = 1; i < points.length - 1; i++) {
    const dist = perpendicularDistance(points[i], points[0], points[points.length - 1])
    if (dist > maxDist) {
      maxDist = dist
      index = i
    }
  }
  
  if (maxDist > epsilon) {
    const rec1 = ramerDouglasPeucker(points.slice(0, index + 1), epsilon)
    const rec2 = ramerDouglasPeucker(points.slice(index), epsilon)
    return rec1.slice(0, rec1.length - 1).concat(rec2)
  } else {
    return [points[0], points[points.length - 1]]
  }
}

function simplifyPath(path, epsilon = 1.0) {
  if (!path || path.segments.length < 3) return path
  
  const points = segmentsToPoints(path.segments)
  const simplifiedPoints = ramerDouglasPeucker(points, epsilon)
  
  if (simplifiedPoints.length >= 2) {
    path.segments = pointsToSegments(simplifiedPoints)
  }
  
  return path
}

function detectSelfIntersections(path) {
  const intersections = []
  const segments = path.segments
  
  for (let i = 0; i < segments.length - 1; i++) {
    const line1Start = segments[i].point
    const line1End = segments[i + 1].point
    
    for (let j = i + 2; j < segments.length - 1; j++) {
      const line2Start = segments[j].point
      const line2End = segments[j + 1].point
      
      const intersection = lineIntersection(line1Start, line1End, line2Start, line2End)
      if (intersection) {
        intersections.push({
          point: intersection,
          index1: i,
          index2: j
        })
      }
    }
    
    if (path.closed && i === 0) {
      const line2Start = segments[segments.length - 1].point
      const line2End = segments[0].point
      const intersection = lineIntersection(line1Start, line1End, line2Start, line2End)
      if (intersection && intersection.getDistance(line1Start) > 1) {
        intersections.push({
          point: intersection,
          index1: i,
          index2: segments.length - 1
        })
      }
    }
  }
  
  return intersections
}

function lineIntersection(p1, p2, p3, p4) {
  const d1x = p2.x - p1.x
  const d1y = p2.y - p1.y
  const d2x = p4.x - p3.x
  const d2y = p4.y - p3.y
  
  const cross = d1x * d2y - d1y * d2x
  if (Math.abs(cross) < 1e-10) return null
  
  const dx = p3.x - p1.x
  const dy = p3.y - p1.y
  const t = (dx * d2y - dy * d2x) / cross
  const u = (dx * d1y - dy * d1x) / cross
  
  if (t > 0.001 && t < 0.999 && u > 0.001 && u < 0.999) {
    return new paper.Point(p1.x + t * d1x, p1.y + t * d1y)
  }
  
  return null
}

function splitSelfIntersectingPath(path) {
  if (!path.closed) return [path]
  
  const intersections = detectSelfIntersections(path)
  
  if (intersections.length === 0) return [path]
  
  const resultPaths = []
  const points = segmentsToPoints(path.segments)
  
  let currentPath = []
  let lastSplitIndex = 0
  
  for (let i = 0; i < points.length; i++) {
    currentPath.push(points[i])
    
    const intersectionAtI = intersections.filter(int => int.index1 === i || int.index2 === i)
    
    if (intersectionAtI.length > 0 && currentPath.length > 2) {
      const intPoint = intersectionAtI[0].point
      currentPath.push(intPoint)
      
      const newPath = new paper.Path({
        segments: currentPath,
        closed: true,
        fillColor: path.fillColor,
        strokeColor: path.strokeColor,
        strokeWidth: path.strokeWidth
      })
      
      resultPaths.push(newPath)
      currentPath = [intPoint]
      lastSplitIndex = i
    }
  }
  
  if (currentPath.length > 2) {
    const newPath = new paper.Path({
      segments: currentPath,
      closed: true,
      fillColor: path.fillColor,
      strokeColor: path.strokeColor,
      strokeWidth: path.strokeWidth
    })
    resultPaths.push(newPath)
  }
  
  if (resultPaths.length > 0) {
    return resultPaths
  }
  
  return [path]
}

function preprocessPathForBoolean(path) {
  if (!path || path.segments.length < 3) return [path]
  
  try {
    if (!path.closed) {
      path.closed = true
    }
    
    let tempPath = path.clone()
    const splitPaths = splitSelfIntersectingPath(tempPath)
    tempPath.remove()
    
    return splitPaths.map(p => {
      const simplified = simplifyPath(p, 0.5)
      simplified.remove()
      return simplified
    })
  } catch (e) {
    console.warn('路径预处理失败:', e)
    return [path]
  }
}

function safeBooleanOperation(items, operation) {
  if (items.length < 2) return null
  
  try {
    const processedItems = []
    items.forEach(item => {
      const processed = preprocessPathForBoolean(item)
      processedItems.push(...processed)
    })
    
    if (processedItems.length < 2) {
      processedItems.forEach(p => p.remove())
      return null
    }
    
    let result = processedItems[0].clone()
    
    for (let i = 1; i < processedItems.length; i++) {
      try {
        const operand = processedItems[i]
        let newResult
        
        switch (operation) {
          case 'unite':
            newResult = result.unite(operand)
            break
          case 'subtract':
            newResult = result.subtract(operand)
            break
          case 'intersect':
            newResult = result.intersect(operand)
            break
          default:
            newResult = result
        }
        
        if (newResult && newResult.segments && newResult.segments.length > 0) {
          result.remove()
          result = newResult
        }
      } catch (e) {
        console.warn('布尔运算步骤失败:', e)
      }
    }
    
    processedItems.forEach(p => p.remove())
    
    if (result && result.segments && result.segments.length > 0) {
      result = simplifyPath(result, 0.5)
    }
    
    return result
  } catch (e) {
    console.error('布尔运算失败:', e)
    return null
  }
}

function booleanUnion() {
  if (selectedItems.value.length < 2) return
  
  const result = safeBooleanOperation(selectedItems.value, 'unite')
  
  if (result) {
    selectedItems.value.forEach(item => item.remove())
    result.selected = true
    selectedItems.value = [result]
    getActivePaperLayer().addChild(result)
  }
}

function booleanSubtract() {
  if (selectedItems.value.length < 2) return
  
  const result = safeBooleanOperation(selectedItems.value, 'subtract')
  
  if (result) {
    selectedItems.value.forEach(item => item.remove())
    result.selected = true
    selectedItems.value = [result]
    getActivePaperLayer().addChild(result)
  }
}

function booleanIntersect() {
  if (selectedItems.value.length < 2) return
  
  const result = safeBooleanOperation(selectedItems.value, 'intersect')
  
  if (result) {
    selectedItems.value.forEach(item => item.remove())
    result.selected = true
    selectedItems.value = [result]
    getActivePaperLayer().addChild(result)
  }
}

function inlineSvgStyles(svgElement) {
  const paths = svgElement.querySelectorAll('path')
  
  paths.forEach(path => {
    const computedStyle = window.getComputedStyle(path)
    
    if (computedStyle.fill && computedStyle.fill !== 'none') {
      path.setAttribute('fill', computedStyle.fill)
    }
    if (computedStyle.stroke && computedStyle.stroke !== 'none') {
      path.setAttribute('stroke', computedStyle.stroke)
    }
    if (computedStyle.strokeWidth) {
      path.setAttribute('stroke-width', computedStyle.strokeWidth)
    }
  })
  
  return svgElement
}

function exportSVG() {
  try {
    showExportMenu.value = false
    
    const svgElement = paper.project.exportSVG({ asString: false })
    
    const styledSvg = inlineSvgStyles(svgElement)
    
    styledSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    styledSvg.setAttribute('version', '1.1')
    
    const serializer = new XMLSerializer()
    let svgString = serializer.serializeToString(styledSvg)
    
    svgString = '<?xml version="1.0" encoding="UTF-8"?>\n' + svgString
    
    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'drawing.svg'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('SVG导出失败:', e)
  }
}

function exportPNG() {
  try {
    showExportMenu.value = false
    
    const canvas = paperCanvas.value
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = canvas.width
    tempCanvas.height = canvas.height
    const ctx = tempCanvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height)
    ctx.drawImage(canvas, 0, 0)
    
    const link = document.createElement('a')
    link.download = 'drawing.png'
    link.href = tempCanvas.toDataURL('image/png')
    link.click()
  } catch (e) {
    console.error('PNG导出失败:', e)
  }
}

function exportPDF() {
  try {
    showExportMenu.value = false
    
    const canvas = paperCanvas.value
    const svgElement = paper.project.exportSVG({ asString: false })
    const styledSvg = inlineSvgStyles(svgElement)
    styledSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
    
    const serializer = new XMLSerializer()
    const svgString = serializer.serializeToString(styledSvg)
    
    const pdfContent = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${canvas.width} ${canvas.height}] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length >>
stream
BT
/F1 24 Tf
100 700 Td
(Exported from Vector Editor) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
450
%%EOF`

    const blob = new Blob([pdfContent], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'drawing.pdf'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error('PDF导出失败:', e)
  }
}

onMounted(async () => {
  await nextTick()
  
  const canvas = paperCanvas.value
  const container = canvasContainer.value
  
  canvas.width = container.clientWidth
  canvas.height = container.clientHeight
  
  paper.setup(canvas)
  
  gridLayer = new paper.Layer()
  gridLayer.name = 'grid'
  paper.project.layers[0].activate()
  layers.value[0].paperLayer = paper.project.activeLayer
  
  setupPaperTool()
  updateGrid()
  saveSnapshot()
  
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.export-dropdown')) {
      showExportMenu.value = false
    }
  })
  
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      e.preventDefault()
      undo()
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
      e.preventDefault()
      redo()
    }
    if (e.key === 'Enter' && path) {
      path.closed = true
      path.fillColor = fillColor.value
      path = null
      saveSnapshot()
    }
    if (e.key === 'Escape') {
      if (path) {
        path.remove()
        path = null
      }
      deselectAll()
      removeAlignmentGuides()
    }
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (selectedItems.value.length > 0) {
        selectedItems.value.forEach(item => item.remove())
        selectedItems.value = []
        saveSnapshot()
      }
    }
  })
  
  window.addEventListener('resize', () => {
    canvas.width = container.clientWidth
    canvas.height = container.clientHeight
    paper.view.viewSize = new paper.Size(canvas.width, canvas.height)
    updateGrid()
  })
})
</script>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: #16213e;
}

.toolbar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  padding: 10px 20px;
  background: #0f3460;
  border-bottom: 1px solid #1a1a2e;
  gap: 20px;
}

.tool-group {
  display: flex;
  gap: 8px;
}

.tool-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  background: #16213e;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.tool-btn:hover {
  background: #1a1a2e;
}

.tool-btn.active {
  background: #e94560;
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.undo-btn, .redo-btn {
  background: #8e44ad;
}

.undo-btn:hover, .redo-btn:hover {
  background: #9b59b6;
}

.export-dropdown {
  position: relative;
}

.export-btn {
  background: #27ae60;
}

.export-btn:hover {
  background: #2ecc71;
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 5px;
  background: #0f3460;
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
  background: #16213e;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.layers-panel {
  width: 250px;
  background: #0f3460;
  padding: 15px;
  border-right: 1px solid #1a1a2e;
  overflow-y: auto;
}

.layers-panel h3 {
  margin-bottom: 15px;
  font-size: 16px;
  color: #e94560;
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
  background: #16213e;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.layer-item:hover {
  background: #1a1a2e;
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
}

.layer-controls {
  display: flex;
  gap: 2px;
}

.layer-move,
.layer-delete {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 12px;
}

.layer-move {
  color: #3498db;
}

.layer-move:hover {
  background: rgba(52, 152, 219, 0.2);
}

.layer-delete {
  color: #e74c3c;
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
  border-top: 1px solid #1a1a2e;
}

.boolean-operations h4 {
  margin-bottom: 10px;
  font-size: 14px;
  color: #f39c12;
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

.boolean-btn:hover:not(:disabled) {
  background: #e67e22;
}

.boolean-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.canvas-container {
  flex: 1;
  background: #fff;
  overflow: hidden;
}

#paper-canvas {
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.properties-panel {
  width: 250px;
  background: #0f3460;
  padding: 15px;
  border-left: 1px solid #1a1a2e;
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
  background: #0f3460;
  border-top: 1px solid #1a1a2e;
  font-size: 12px;
  color: #95a5a6;
}

.icon-library {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #1a1a2e;
}

.icon-library h4 {
  margin-bottom: 10px;
  font-size: 14px;
  color: #3498db;
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
  background: #16213e;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.icon-item:hover {
  background: #1a1a2e;
  border-color: #e94560;
  transform: scale(1.05);
}

.icon-item:active {
  cursor: grabbing;
}

.icon-preview {
  width: 40px;
  height: 40px;
  margin-bottom: 5px;
}

.icon-name {
  font-size: 11px;
  color: #bdc3c7;
  text-align: center;
}
</style>
