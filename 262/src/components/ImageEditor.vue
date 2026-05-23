<template>
  <div class="editor-container">
    <div class="left-panel">
      <div class="panel-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeLeftTab === 'tools' }"
          @click="activeLeftTab = 'tools'"
        >
          🛠️ 工具
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeLeftTab === 'ai' }"
          @click="activeLeftTab = 'ai'"
        >
          🤖 AI
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeLeftTab === 'batch' }"
          @click="activeLeftTab = 'batch'"
        >
          📦 批量
        </button>
      </div>

      <div v-show="activeLeftTab === 'tools'" class="tab-content">
        <div class="panel-section">
          <h3>文件</h3>
          <div class="btn-group">
            <button class="btn btn-primary" @click="triggerUpload">
              📁 上传图片
            </button>
            <input
              ref="fileInput"
              type="file"
              accept="image/*"
              @change="handleUpload"
              style="display: none"
            />
          </div>
        </div>

        <div class="panel-section">
          <h3>编辑工具</h3>
          <div class="tool-buttons">
            <button
              class="btn tool-btn"
              :class="{ active: currentTool === 'select' }"
              @click="setTool('select')"
            >
              🖱️ 选择
            </button>
            <button
              class="btn tool-btn"
              :class="{ active: currentTool === 'crop' }"
              @click="setTool('crop')"
            >
              ✂️ 裁剪
            </button>
            <button
              class="btn tool-btn"
              :class="{ active: currentTool === 'draw' }"
              @click="setTool('draw')"
            >
              ✏️ 涂鸦
            </button>
            <button
              class="btn tool-btn"
              @click="addText"
            >
              📝 文字
            </button>
          </div>
        </div>

        <div class="panel-section">
          <h3>旋转</h3>
          <div class="btn-group">
            <button class="btn" @click="rotate(-90)">↺ 左旋</button>
            <button class="btn" @click="rotate(90)">↻ 右旋</button>
          </div>
          <div class="slider-group">
            <label>角度: {{ rotation }}°</label>
            <input
              type="range"
              v-model.number="rotation"
              min="-180"
              max="180"
              @input="applyRotation"
            />
          </div>
        </div>

        <div class="panel-section" v-if="currentTool === 'draw'">
          <h3>涂鸦设置</h3>
          <div class="slider-group">
            <label>画笔大小: {{ brushSize }}</label>
            <input
              type="range"
              v-model.number="brushSize"
              min="1"
              max="50"
            />
          </div>
          <div class="color-group">
            <label>颜色:</label>
            <input
              type="color"
              v-model="brushColor"
              class="color-picker"
            />
          </div>
        </div>

        <div class="panel-section" v-if="selectedText">
          <h3>文字设置</h3>
          <div class="input-group">
            <label>内容:</label>
            <input
              type="text"
              v-model="textContent"
              @input="updateText"
            />
          </div>
          <div class="slider-group">
            <label>字号: {{ fontSize }}</label>
            <input
              type="range"
              v-model.number="fontSize"
              min="12"
              max="120"
              @input="updateTextStyle"
            />
          </div>
          <div class="color-group">
            <label>颜色:</label>
            <input
              type="color"
              v-model="textColor"
              @input="updateTextStyle"
              class="color-picker"
            />
          </div>
        </div>

        <div class="panel-section performance-info">
          <h3>⚡ 性能统计</h3>
          <div class="stats-item">
            <span>历史内存:</span>
            <span class="stats-value">{{ historyStats.memoryUsage }}</span>
          </div>
          <div class="stats-item">
            <span>内存节省:</span>
            <span class="stats-value highlight">{{ historyStats.compressionRatio }}</span>
          </div>
          <div class="stats-item">
            <span>图层缓存:</span>
            <span class="stats-value">{{ layerStats.cachedMemory }}</span>
          </div>
          <div class="stats-item">
            <span>WebGL加速:</span>
            <span class="stats-value" :class="{ highlight: webglEnabled }">
              {{ webglEnabled ? '已启用' : '未启用' }}
            </span>
          </div>
        </div>
      </div>

      <div v-show="activeLeftTab === 'ai'" class="tab-content">
        <AIBackgroundPanel
          :canvas="canvas"
          :hasImage="hasSelectedImage"
          @processing="onAIProcessing"
          @complete="onAIComplete"
        />
      </div>

      <div v-show="activeLeftTab === 'batch'" class="tab-content">
        <BatchProcessor @imageSelected="onBatchImageSelected" />
      </div>
    </div>

    <div class="main-content">
      <div class="toolbar">
        <div class="history-buttons">
          <button
            class="btn"
            :disabled="!canUndo"
            @click="undo"
          >
            ↩️ 撤销
          </button>
          <button
            class="btn"
            :disabled="!canRedo"
            @click="redo"
          >
            ↪️ 重做
          </button>
        </div>
        <div class="export-buttons">
          <button class="btn btn-success" @click="exportImage('png')">
            💾 导出 PNG
          </button>
          <button class="btn btn-success" @click="exportImage('jpeg')">
            💾 导出 JPEG
          </button>
          <button class="btn btn-success" @click="exportImage('svg')">
            💾 导出 SVG
          </button>
        </div>
      </div>

      <div class="canvas-wrapper">
        <canvas ref="canvasEl"></canvas>
        <div v-if="isCropping" class="crop-overlay">
          <div
            class="crop-box"
            :style="cropBoxStyle"
            @mousedown="startCropDrag"
          >
            <div class="crop-handle nw" @mousedown.stop="startResize('nw')"></div>
            <div class="crop-handle ne" @mousedown.stop="startResize('ne')"></div>
            <div class="crop-handle sw" @mousedown.stop="startResize('sw')"></div>
            <div class="crop-handle se" @mousedown.stop="startResize('se')"></div>
          </div>
        </div>
        <div v-if="isCropping" class="crop-actions">
          <button class="btn btn-success" @click="applyCrop">✓ 应用裁剪</button>
          <button class="btn" @click="cancelCrop">✕ 取消</button>
        </div>
        <div v-if="isAIProcessing" class="processing-overlay">
          <div class="processing-content">
            <div class="spinner"></div>
            <p>AI 处理中...</p>
          </div>
        </div>
      </div>
    </div>

    <div class="right-panel">
      <div class="panel-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeRightTab === 'filter' }"
          @click="activeRightTab = 'filter'"
        >
          🎨 滤镜
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeRightTab === 'sticker' }"
          @click="activeRightTab = 'sticker'"
        >
          🌟 贴纸
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeRightTab === 'layer' }"
          @click="activeRightTab = 'layer'"
        >
          📚 图层
        </button>
      </div>

      <div v-show="activeRightTab === 'filter'" class="tab-content">
        <div class="panel-section">
          <h3>🎨 滤镜调节 <span class="badge" :class="{ active: webglEnabled }">GPU</span></h3>
          <div class="filter-group">
            <div class="slider-group">
              <label>亮度: {{ brightness }}</label>
              <input
                type="range"
                v-model.number="brightness"
                min="-1"
                max="1"
                step="0.05"
                @input="applyFilters"
              />
            </div>
            <div class="slider-group">
              <label>对比度: {{ contrast }}</label>
              <input
                type="range"
                v-model.number="contrast"
                min="-1"
                max="1"
                step="0.05"
                @input="applyFilters"
              />
            </div>
            <div class="slider-group">
              <label>饱和度: {{ saturation }}</label>
              <input
                type="range"
                v-model.number="saturation"
                min="-1"
                max="1"
                step="0.05"
                @input="applyFilters"
              />
            </div>
            <button class="btn" @click="resetFilters">重置滤镜</button>
          </div>
        </div>
      </div>

      <div v-show="activeRightTab === 'sticker'" class="tab-content">
        <StickerLibrary :canvas="canvas" @add="onStickerAdded" />
      </div>

      <div v-show="activeRightTab === 'layer'" class="tab-content">
        <div class="panel-section">
          <h3>📚 图层管理</h3>
          <div class="layer-list">
            <div
              v-for="(obj, index) in layers"
              :key="obj.layerId || index"
              class="layer-item"
              :class="{ 
                active: isLayerActive(obj),
                hidden: !isLayerVisible(obj)
              }"
              @click="selectLayer(obj)"
            >
              <button
                class="visibility-btn"
                @click.stop="toggleLayerVisibility(obj)"
              >
                {{ isLayerVisible(obj) ? '👁️' : '👁️‍🗨️' }}
              </button>
              <span class="layer-icon">
                {{ getLayerIcon(obj) }}
              </span>
              <span class="layer-name">{{ getLayerName(obj) }}</span>
              <div class="layer-actions">
                <button
                  class="icon-btn"
                  @click.stop="moveLayer(index, -1)"
                  :disabled="index === 0"
                >
                  ↑
                </button>
                <button
                  class="icon-btn"
                  @click.stop="moveLayer(index, 1)"
                  :disabled="index === layers.length - 1"
                >
                  ↓
                </button>
                <button
                  class="icon-btn delete"
                  @click.stop="deleteLayer(obj)"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, onUnmounted } from 'vue'
import { fabric } from 'fabric'
import { webGLFilter } from '../utils/WebGLFilter.js'
import { layerResourceManager } from '../utils/LayerResourceManager.js'
import { commandHistory, generateId } from '../utils/CommandHistory.js'
import AIBackgroundPanel from './AIBackgroundPanel.vue'
import StickerLibrary from './StickerLibrary.vue'
import BatchProcessor from './BatchProcessor.vue'

const canvasEl = ref(null)
const fileInput = ref(null)
let canvas = null

const activeLeftTab = ref('tools')
const activeRightTab = ref('filter')

const currentTool = ref('select')
const rotation = ref(0)
const brushSize = ref(5)
const brushColor = ref('#ff0000')
const textContent = ref('')
const fontSize = ref(32)
const textColor = ref('#000000')
const selectedText = ref(null)

const brightness = ref(0)
const contrast = ref(0)
const saturation = ref(0)
const webglEnabled = ref(false)
const isAIProcessing = ref(false)

const isCropping = ref(false)
const cropBox = ref({ x: 50, y: 50, width: 200, height: 150 })
const cropStartPos = ref({ x: 0, y: 0 })
const resizeHandle = ref(null)
const cropOldState = ref(null)

const layers = ref([])
const layerStats = ref({
  totalLayers: 0,
  hiddenLayers: 0,
  cachedMemory: '0 B',
  memoryLimit: '100 MB'
})

const historyStats = ref({
  undoCount: 0,
  redoCount: 0,
  memoryUsage: '0 B',
  memoryLimit: '10 MB',
  compressionRatio: '0%'
})

const hasSelectedImage = computed(() => {
  if (!canvas) return false
  const obj = canvas.getActiveObject()
  return obj && obj.type === 'image'
})

const canUndo = computed(() => commandHistory.canUndo())
const canRedo = computed(() => commandHistory.canRedo())

const cropBoxStyle = computed(() => ({
  left: cropBox.value.x + 'px',
  top: cropBox.value.y + 'px',
  width: cropBox.value.width + 'px',
  height: cropBox.value.height + 'px'
}))

onMounted(() => {
  initCanvas()
  webglEnabled.value = webGLFilter.init()
  commandHistory.setCanvas(canvas)
})

onUnmounted(() => {
  webGLFilter.dispose()
  layerResourceManager.dispose()
  commandHistory.dispose()
})

function initCanvas() {
  canvas = new fabric.Canvas(canvasEl.value, {
    width: 800,
    height: 600,
    backgroundColor: '#2a2a4e',
    preserveObjectStacking: true
  })

  canvas.on('object:added', (e) => {
    const obj = e.target
    if (!obj.layerId) {
      obj.layerId = generateId()
    }
    layerResourceManager.registerLayer(obj.layerId, obj)
    updateLayers()
  })

  canvas.on('object:removed', (e) => {
    const obj = e.target
    if (obj.layerId) {
      layerResourceManager.unregisterLayer(obj.layerId)
    }
    updateLayers()
  })

  canvas.on('object:modified', (e) => {
    updateLayers()
  })

  canvas.on('selection:created', handleSelection)
  canvas.on('selection:updated', handleSelection)
  canvas.on('selection:cleared', () => {
    selectedText.value = null
    brightness.value = 0
    contrast.value = 0
    saturation.value = 0
  })

  updateStats()
}

function handleSelection(e) {
  const obj = e.selected[0]
  if (obj && obj.type === 'i-text') {
    selectedText.value = obj
    textContent.value = obj.text
    fontSize.value = obj.fontSize
    textColor.value = obj.fill
  } else {
    selectedText.value = null
  }

  if (obj && obj.type === 'image') {
    const filters = webGLFilter.getCurrentFilters()
    brightness.value = filters.brightness
    contrast.value = filters.contrast
    saturation.value = filters.saturation
  }
}

function triggerUpload() {
  fileInput.value.click()
}

function handleUpload(e) {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    fabric.Image.fromURL(event.target.result, (img) => {
      const scale = Math.min(
        (canvas.width - 40) / img.width,
        (canvas.height - 40) / img.height,
        1
      )
      img.scale(scale)
      img.center()
      img.layerId = generateId()
      
      canvas.add(img)
      canvas.setActiveObject(img)
      canvas.renderAll()
      
      commandHistory.addObject(img)
      updateStats()
    })
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

function setTool(tool) {
  currentTool.value = tool

  if (tool === 'select') {
    canvas.isDrawingMode = false
    canvas.selection = true
    canvas.forEachObject((obj) => {
      obj.selectable = true
      obj.evented = true
    })
    isCropping.value = false
  } else if (tool === 'crop') {
    canvas.isDrawingMode = false
    canvas.selection = false
    canvas.discardActiveObject()
    canvas.forEachObject((obj) => {
      obj.selectable = false
      obj.evented = false
    })
    canvas.renderAll()
    initCropBox()
    isCropping.value = true
    cropOldState.value = JSON.stringify(canvas.toJSON())
  } else if (tool === 'draw') {
    canvas.isDrawingMode = true
    canvas.freeDrawingBrush.width = brushSize.value
    canvas.freeDrawingBrush.color = brushColor.value
    isCropping.value = false
  }
}

function initCropBox() {
  const objects = canvas.getObjects()
  if (objects.length > 0) {
    const bounds = canvas.getObjects().reduce(
      (acc, obj) => {
        const objBounds = obj.getBoundingRect()
        return {
          left: Math.min(acc.left, objBounds.left),
          top: Math.min(acc.top, objBounds.top),
          right: Math.max(acc.right, objBounds.left + objBounds.width),
          bottom: Math.max(acc.bottom, objBounds.top + objBounds.height)
        }
      },
      { left: Infinity, top: Infinity, right: 0, bottom: 0 }
    )
    cropBox.value = {
      x: bounds.left,
      y: bounds.top,
      width: bounds.right - bounds.left,
      height: bounds.bottom - bounds.top
    }
  } else {
    cropBox.value = { x: 50, y: 50, width: 200, height: 150 }
  }
}

function startCropDrag(e) {
  cropStartPos.value = {
    x: e.clientX - cropBox.value.x,
    y: e.clientY - cropBox.value.y
  }
  resizeHandle.value = null
  document.addEventListener('mousemove', onCropDrag)
  document.addEventListener('mouseup', stopCropDrag)
}

function startResize(handle, e) {
  resizeHandle.value = handle
  cropStartPos.value = { x: e.clientX, y: e.clientY }
  document.addEventListener('mousemove', onCropResize)
  document.addEventListener('mouseup', stopCropDrag)
}

function onCropDrag(e) {
  const wrapper = canvasEl.value.parentElement
  const rect = wrapper.getBoundingClientRect()
  cropBox.value.x = Math.max(0, Math.min(canvas.width - cropBox.value.width, e.clientX - rect.left - cropStartPos.value.x))
  cropBox.value.y = Math.max(0, Math.min(canvas.height - cropBox.value.height, e.clientY - rect.top - cropStartPos.value.y))
}

function onCropResize(e) {
  const wrapper = canvasEl.value.parentElement
  const rect = wrapper.getBoundingClientRect()
  const dx = e.clientX - cropStartPos.value.x
  const dy = e.clientY - cropStartPos.value.y

  const handle = resizeHandle.value
  if (handle.includes('e')) {
    cropBox.value.width = Math.max(20, cropBox.value.width + dx)
  }
  if (handle.includes('w')) {
    cropBox.value.x = Math.max(0, cropBox.value.x + dx)
    cropBox.value.width = Math.max(20, cropBox.value.width - dx)
  }
  if (handle.includes('s')) {
    cropBox.value.height = Math.max(20, cropBox.value.height + dy)
  }
  if (handle.includes('n')) {
    cropBox.value.y = Math.max(0, cropBox.value.y + dy)
    cropBox.value.height = Math.max(20, cropBox.value.height - dy)
  }

  cropStartPos.value = { x: e.clientX, y: e.clientY }
}

function stopCropDrag() {
  document.removeEventListener('mousemove', onCropDrag)
  document.removeEventListener('mousemove', onCropResize)
  document.removeEventListener('mouseup', stopCropDrag)
}

function applyCrop() {
  const { x, y, width, height } = cropBox.value
  
  const tempCanvas = document.createElement('canvas')
  tempCanvas.width = width
  tempCanvas.height = height
  const tempCtx = tempCanvas.getContext('2d')
  
  const originalCanvas = canvas.lowerCanvasEl
  tempCtx.drawImage(
    originalCanvas,
    x, y, width, height,
    0, 0, width, height
  )

  canvas.clear()
  canvas.setWidth(width)
  canvas.setHeight(height)
  canvas.backgroundColor = '#2a2a4e'

  fabric.Image.fromURL(tempCanvas.toDataURL(), (img) => {
    img.layerId = generateId()
    canvas.add(img)
    canvas.renderAll()
    
    const newState = JSON.stringify(canvas.toJSON())
    commandHistory.crop(cropOldState.value, newState)
    updateStats()
  })

  isCropping.value = false
  setTool('select')
}

function cancelCrop() {
  isCropping.value = false
  setTool('select')
}

function rotate(angle) {
  const activeObj = canvas.getActiveObject()
  if (activeObj) {
    const oldProps = { angle: activeObj.angle || 0 }
    activeObj.rotate((activeObj.angle || 0) + angle)
    canvas.renderAll()
    
    const newProps = { angle: activeObj.angle }
    commandHistory.modifyObject(activeObj, oldProps, newProps)
    updateStats()
  }
}

function applyRotation() {
  const activeObj = canvas.getActiveObject()
  if (activeObj) {
    const oldProps = { angle: activeObj.angle || 0 }
    activeObj.rotate(rotation.value)
    canvas.renderAll()
    
    const newProps = { angle: activeObj.angle }
    commandHistory.modifyObject(activeObj, oldProps, newProps)
    updateStats()
  }
}

function addText() {
  const text = new fabric.IText('双击编辑', {
    left: canvas.width / 2,
    top: canvas.height / 2,
    fontSize: 32,
    fill: '#ffffff',
    fontFamily: 'Arial',
    originX: 'center',
    originY: 'center'
  })
  text.layerId = generateId()
  canvas.add(text)
  canvas.setActiveObject(text)
  canvas.renderAll()
  
  commandHistory.addObject(text)
  updateStats()
  setTool('select')
}

function updateText() {
  if (selectedText.value) {
    const oldProps = { text: selectedText.value.text }
    selectedText.value.set('text', textContent.value)
    canvas.renderAll()
    
    const newProps = { text: textContent.value }
    commandHistory.modifyObject(selectedText.value, oldProps, newProps)
    updateStats()
  }
}

function updateTextStyle() {
  if (selectedText.value) {
    const oldProps = {
      fontSize: selectedText.value.fontSize,
      fill: selectedText.value.fill
    }
    selectedText.value.set('fontSize', fontSize.value)
    selectedText.value.set('fill', textColor.value)
    canvas.renderAll()
    
    const newProps = { fontSize: fontSize.value, fill: textColor.value }
    commandHistory.modifyObject(selectedText.value, oldProps, newProps)
    updateStats()
  }
}

watch(brushSize, (val) => {
  if (canvas.isDrawingMode) {
    canvas.freeDrawingBrush.width = val
  }
})

watch(brushColor, (val) => {
  if (canvas.isDrawingMode) {
    canvas.freeDrawingBrush.color = val
  }
})

let filterDebounceTimer = null
function applyFilters() {
  const activeObj = canvas.getActiveObject()
  if (!activeObj || activeObj.type !== 'image') return

  const imgElement = activeObj.getElement()
  if (!imgElement) return

  clearTimeout(filterDebounceTimer)
  filterDebounceTimer = setTimeout(() => {
    const filters = {
      brightness: brightness.value,
      contrast: contrast.value,
      saturation: saturation.value
    }

    const filteredCanvas = webGLFilter.applyFilter(imgElement, filters)
    
    fabric.Image.fromURL(filteredCanvas.toDataURL(), (filteredImg) => {
      const oldProps = { element: imgElement.src }
      
      activeObj.setElement(filteredImg.getElement())
      activeObj.setCoords()
      canvas.renderAll()
      
      const newProps = { element: filteredImg.getElement().src }
      commandHistory.modifyObject(activeObj, oldProps, newProps)
      updateStats()
    })
  }, 100)
}

function resetFilters() {
  brightness.value = 0
  contrast.value = 0
  saturation.value = 0
  
  const activeObj = canvas.getActiveObject()
  if (activeObj && activeObj.type === 'image') {
    webGLFilter.resetFilters()
    canvas.renderAll()
    updateStats()
  }
}

function undo() {
  commandHistory.undo()
  updateLayers()
  updateStats()
}

function redo() {
  commandHistory.redo()
  updateLayers()
  updateStats()
}

function updateLayers() {
  layers.value = canvas.getObjects().slice().reverse()
}

function getLayerIcon(obj) {
  switch (obj.type) {
    case 'image': return '🖼️'
    case 'i-text':
    case 'text': return '📝'
    case 'path': return '✏️'
    default: return '📦'
  }
}

function getLayerName(obj) {
  switch (obj.type) {
    case 'image': return '图片'
    case 'i-text':
    case 'text': return obj.text?.substring(0, 10) || '文字'
    case 'path': return '涂鸦'
    default: return '对象'
  }
}

function isLayerActive(obj) {
  return canvas.getActiveObject() === obj
}

function isLayerVisible(obj) {
  if (obj.layerId) {
    return layerResourceManager.isLayerVisible(obj.layerId)
  }
  return obj.visible !== false
}

function toggleLayerVisibility(obj) {
  if (!obj.layerId) {
    obj.layerId = generateId()
    layerResourceManager.registerLayer(obj.layerId, obj)
  }

  if (layerResourceManager.isLayerVisible(obj.layerId)) {
    layerResourceManager.hideLayer(obj.layerId)
  } else {
    layerResourceManager.showLayer(obj.layerId)
  }
  canvas.renderAll()
  updateStats()
}

function selectLayer(obj) {
  canvas.setActiveObject(obj)
  canvas.renderAll()
}

function moveLayer(index, direction) {
  const objects = canvas.getObjects()
  const objIndex = objects.length - 1 - index
  const obj = objects[objIndex]
  
  const oldIndex = objIndex
  const newIndex = direction > 0 ? 
    Math.min(objects.length - 1, objIndex + 1) : 
    Math.max(0, objIndex - 1)
  
  if (direction > 0) {
    canvas.bringObjectForward(obj)
  } else {
    canvas.sendObjectBackwards(obj)
  }
  canvas.renderAll()
  
  commandHistory.moveLayer(obj, oldIndex, newIndex)
  updateStats()
}

function deleteLayer(obj) {
  canvas.remove(obj)
  canvas.renderAll()
  
  commandHistory.removeObject(obj)
  updateStats()
}

function updateStats() {
  layerStats.value = layerResourceManager.getMemoryStats()
  historyStats.value = commandHistory.getStats()
}

function onAIProcessing(processing) {
  isAIProcessing.value = processing
}

function onAIComplete(newImg) {
  updateStats()
}

function onStickerAdded(obj) {
  commandHistory.addObject(obj)
  updateStats()
}

function onBatchImageSelected(imageData) {
  fabric.Image.fromURL(imageData.dataUrl, (img) => {
    const scale = Math.min(
      (canvas.width - 40) / img.width,
      (canvas.height - 40) / img.height,
      1
    )
    img.scale(scale)
    img.center()
    img.layerId = generateId()
    
    canvas.add(img)
    canvas.setActiveObject(img)
    canvas.renderAll()
    
    commandHistory.addObject(img)
    updateStats()
  })
}

function exportImage(format) {
  let dataUrl
  let filename = 'edited-image'

  if (format === 'jpeg') {
    dataUrl = canvas.toDataURL({
      format: 'jpeg',
      quality: 0.9,
      multiplier: 2
    })
    filename += '.jpg'
  } else if (format === 'svg') {
    dataUrl = 'data:image/svg+xml;utf8,' + encodeURIComponent(canvas.toSVG())
    filename += '.svg'
  } else {
    dataUrl = canvas.toDataURL({
      format: 'png',
      multiplier: 2
    })
    filename += '.png'
  }

  const link = document.createElement('a')
  link.download = filename
  link.href = dataUrl
  link.click()
}
</script>

<style scoped>
.editor-container {
  display: flex;
  width: 100%;
  height: 100vh;
  background: #1a1a2e;
}

.left-panel,
.right-panel {
  width: 300px;
  background: #16213e;
  border-right: 1px solid #0f3460;
  display: flex;
  flex-direction: column;
}

.right-panel {
  border-right: none;
  border-left: 1px solid #0f3460;
}

.panel-tabs {
  display: flex;
  background: #0f3460;
  padding: 4px;
  gap: 4px;
}

.panel-tabs .tab-btn {
  flex: 1;
  padding: 8px 4px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #888;
  cursor: pointer;
  font-size: 11px;
  transition: all 0.2s;
}

.panel-tabs .tab-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.panel-tabs .tab-btn.active {
  color: #fff;
  background: #e94560;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.panel-section {
  margin-bottom: 24px;
}

.panel-section h3 {
  font-size: 14px;
  margin-bottom: 12px;
  color: #e94560;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.badge {
  font-size: 10px;
  padding: 2px 6px;
  background: #333;
  border-radius: 4px;
  color: #888;
}

.badge.active {
  background: #4ade80;
  color: #000;
}

.btn-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.btn {
  padding: 8px 16px;
  background: #0f3460;
  color: #fff;
  border-radius: 6px;
  font-size: 13px;
  border: 1px solid transparent;
}

.btn:hover {
  background: #533483;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #e94560;
  width: 100%;
}

.btn-success {
  background: #4ade80;
  color: #000;
}

.btn-success:hover {
  background: #22c55e;
}

.tool-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.tool-btn.active {
  background: #e94560;
  border-color: #ff6b8a;
}

.slider-group {
  margin-bottom: 16px;
}

.slider-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #a0a0c0;
}

.slider-group input[type="range"] {
  width: 100%;
  height: 6px;
  background: #0f3460;
  border-radius: 3px;
  appearance: none;
}

.slider-group input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  background: #e94560;
  border-radius: 50%;
  cursor: pointer;
}

.color-group {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.color-group label {
  font-size: 13px;
  color: #a0a0c0;
}

.color-picker {
  width: 50px;
  height: 36px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: transparent;
}

.input-group {
  margin-bottom: 12px;
}

.input-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: #a0a0c0;
}

.input-group input {
  width: 100%;
  padding: 8px 12px;
  background: #0f3460;
  border: 1px solid #1a1a2e;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.history-buttons,
.export-buttons {
  display: flex;
  gap: 8px;
}

.canvas-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: auto;
}

canvas {
  border: 2px solid #0f3460;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.crop-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 800px;
  height: 600px;
  pointer-events: none;
}

.crop-box {
  position: absolute;
  border: 2px solid #e94560;
  background: rgba(233, 69, 96, 0.1);
  cursor: move;
  pointer-events: auto;
}

.crop-handle {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #e94560;
  border: 2px solid #fff;
  border-radius: 50%;
}

.crop-handle.nw { top: -6px; left: -6px; cursor: nw-resize; }
.crop-handle.ne { top: -6px; right: -6px; cursor: ne-resize; }
.crop-handle.sw { bottom: -6px; left: -6px; cursor: sw-resize; }
.crop-handle.se { bottom: -6px; right: -6px; cursor: se-resize; }

.crop-actions {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 12px;
  z-index: 100;
}

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.processing-content {
  text-align: center;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #0f3460;
  border-top-color: #e94560;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.processing-content p {
  color: #fff;
  font-size: 16px;
}

.layer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.layer-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #0f3460;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.layer-item:hover {
  background: #1a1a2e;
}

.layer-item.active {
  border-color: #e94560;
  background: rgba(233, 69, 96, 0.1);
}

.layer-item.hidden {
  opacity: 0.5;
}

.visibility-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.layer-icon {
  font-size: 18px;
}

.layer-name {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.layer-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a2e;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.icon-btn:hover:not(:disabled) {
  background: #533483;
}

.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.icon-btn.delete:hover {
  background: #e94560;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.performance-info {
  background: rgba(15, 52, 96, 0.5);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #0f3460;
}

.stats-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 12px;
  color: #a0a0c0;
}

.stats-value {
  font-weight: 600;
  color: #fff;
}

.stats-value.highlight {
  color: #4ade80;
}
</style>
