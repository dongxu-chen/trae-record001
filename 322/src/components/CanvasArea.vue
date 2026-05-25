<template>
  <div class="canvas-wrapper" ref="wrapperRef">
    <canvas ref="canvasRef"></canvas>

    <div v-if="!hasImage" class="empty-state">
      <div class="empty-icon">
        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="#c0c4cc" stroke-width="1">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
      </div>
      <h3>暂无图片</h3>
      <p>点击左上角"上传图片"按钮开始标注</p>
      <label class="btn btn-primary empty-upload">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        选择图片
        <input type="file" accept="image/*" @change="handleFileSelect" style="display: none" />
      </label>
    </div>

    <div v-if="currentImage" class="image-info">
      <span class="image-name">{{ currentImage.name }}</span>
      <span class="image-size">{{ currentImage.width }} × {{ currentImage.height }}</span>
      <span class="annotation-count">标注: {{ annotations.length }}</span>
    </div>

    <div v-if="currentTool !== 'select'" class="tool-hint">
      {{ toolHint }}
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleFileSelect"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { TOOL_MODES } from '../constants'
import canvasManager from '../utils/canvasManager'
import wsClient from '../utils/websocket'
import shortcutManager from '../utils/shortcutManager'
import db from '../utils/db'

const props = defineProps({
  projectId: {
    type: String,
    default: null
  },
  imageId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['image-loaded', 'annotation-add', 'annotation-update', 'annotation-delete'])

const wrapperRef = ref(null)
const canvasRef = ref(null)
const fileInputRef = ref(null)
const hasImage = ref(false)
const currentImage = ref(null)
const currentImageElement = ref(null)
const annotations = computed(() => canvasManager.annotations.value)
const currentTool = computed(() => canvasManager.currentTool.value)

const toolHint = computed(() => {
  const hints = {
    [TOOL_MODES.RECTANGLE]: '在图片上拖动绘制矩形标注框',
    [TOOL_MODES.ARROW]: '在图片上拖动绘制箭头',
    [TOOL_MODES.TEXT]: '在图片上点击添加文本注释',
    [TOOL_MODES.PAN]: '拖动画布平移视图'
  }
  return hints[currentTool.value] || ''
})

const handleFileSelect = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  try {
    const dataUrl = await readFileAsDataURL(file)
    const img = await loadImageElement(dataUrl)

    const imageData = await db.addImage({
      projectId: props.projectId,
      name: file.name,
      dataUrl: dataUrl,
      width: img.width,
      height: img.height
    })

    await loadImage(dataUrl, { ...imageData, dataUrl: undefined })
    currentImage.value = imageData
    hasImage.value = true

    emit('image-loaded', imageData)

    if (wsClient.isOnline()) {
      wsClient.sendImageLoad(imageData)
    }
  } catch (error) {
    console.error('加载图片失败:', error)
    alert('加载图片失败: ' + error.message)
  } finally {
    e.target.value = ''
  }
}

const readFileAsDataURL = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

const loadImageElement = (src) => {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

const loadImage = async (dataUrl, imageInfo) => {
  await canvasManager.loadImage(dataUrl, imageInfo)
  hasImage.value = true
  
  if (canvasManager.backgroundImage) {
    const img = canvasManager.backgroundImage.getElement()
    if (img instanceof HTMLImageElement) {
      currentImageElement.value = img
    }
  }

  if (imageInfo && imageInfo.id) {
    const savedAnnotations = await db.getAnnotations(imageInfo.id)
    if (savedAnnotations.length > 0) {
      canvasManager.loadAnnotations(savedAnnotations)
    }
  }
}

const loadImageById = async (imageId) => {
  const image = await db.getImage(imageId)
  if (image) {
    await loadImage(image.dataUrl, image)
    currentImage.value = image
    emit('image-loaded', image)
  }
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const handleAnnotationAdd = async (annotation) => {
  if (props.projectId && currentImage.value) {
    await db.addAnnotation({
      ...annotation,
      projectId: props.projectId,
      imageId: currentImage.value.id
    })
  }

  if (wsClient.isOnline()) {
    wsClient.sendAnnotationAdd(annotation)
  }

  emit('annotation-add', annotation)
}

const handleAnnotationUpdate = async (annotation) => {
  await db.updateAnnotation(annotation.id, annotation)

  if (wsClient.isOnline()) {
    wsClient.sendAnnotationUpdate(annotation)
  }

  emit('annotation-update', annotation)
}

const handleAnnotationDelete = async (annotation) => {
  await db.deleteAnnotation(annotation.id)

  if (wsClient.isOnline()) {
    wsClient.sendAnnotationDelete(annotation.id)
  }

  emit('annotation-delete', annotation)
}

const handleCursorMove = (position) => {
  if (wsClient.isOnline() && currentImage.value) {
    wsClient.sendCursorMove(position, currentImage.value.id)
  }
}

const handleRemoteAnnotationAdd = (data) => {
  canvasManager.addAnnotationFromData(data.annotation)
  canvasManager.annotations.value.push(data.annotation)
}

const handleRemoteAnnotationUpdate = (data) => {
  const index = canvasManager.annotations.value.findIndex(a => a.id === data.annotation.id)
  if (index !== -1) {
    canvasManager.annotations.value[index] = data.annotation
    const obj = canvasManager.findObjectById(data.annotation.id)
    if (obj) {
      canvasManager.canvas.remove(obj)
      canvasManager.addAnnotationFromData(data.annotation)
    }
  }
}

const handleRemoteAnnotationDelete = (data) => {
  const obj = canvasManager.findObjectById(data.annotationId)
  if (obj) {
    canvasManager.canvas.remove(obj)
  }
  canvasManager.annotations.value = canvasManager.annotations.value.filter(a => a.id !== data.annotationId)
}

const handleRemoteCursorMove = (data, senderId) => {
  if (!canvasManager.remoteCursors.has(senderId)) {
    canvasManager.addRemoteCursor(senderId, data.user)
  }
  canvasManager.updateRemoteCursor(senderId, data.position)
}

const handleUserLeave = (userId) => {
  canvasManager.removeRemoteCursor(userId)
}

const handleUndo = () => {
  canvasManager.undo()
}

const handleRedo = () => {
  canvasManager.redo()
}

const handleOTOperation = (operation, senderId) => {
  if (!operation) return
  
  if (operation.transformed) {
    operation = operation.transformed
  }
  
  canvasManager.applyRemoteOperation(operation)
  
  if (operation.type === 'create') {
    db.addAnnotation({
      ...operation.data,
      projectId: props.projectId,
      imageId: currentImage.value?.id
    })
  } else if (operation.type === 'update' || operation.type === 'move' || operation.type === 'resize') {
    const existing = canvasManager.annotations.value.find(a => a.id === operation.annotationId)
    if (existing) {
      db.updateAnnotation(operation.annotationId, existing)
    }
  } else if (operation.type === 'delete') {
    db.deleteAnnotation(operation.annotationId)
  }
}

const handleLocalOTOperation = (operation) => {
  if (wsClient.isOnline()) {
    wsClient.sendOperation(operation)
  }
}

const handleShortcutTool = (tool) => {
  canvasManager.setTool(tool)
}

const handleShortcutDelete = () => {
  const activeObj = canvasManager.canvas?.getActiveObject()
  if (activeObj && activeObj.annotationId) {
    canvasManager.deleteAnnotation(activeObj.annotationId)
  }
}

const handleShortcutSelectAll = () => {
  if (canvasManager.canvas) {
    const selectableObjects = canvasManager.canvas.getObjects().filter(
      obj => obj.selectable && !obj.isGuideline && obj !== canvasManager.backgroundImage
    )
    if (selectableObjects.length > 0) {
      canvasManager.canvas.setActiveObject(new fabric.ActiveSelection(selectableObjects, {
        canvas: canvasManager.canvas
      }))
      canvasManager.canvas.renderAll()
    }
  }
}

const handleShortcutEscape = () => {
  canvasManager.setTool(TOOL_MODES.SELECT)
  if (canvasManager.canvas) {
    canvasManager.canvas.discardActiveObject()
    canvasManager.canvas.renderAll()
  }
}

const handleShortcutZoomIn = () => {
  if (canvasManager.canvas) {
    canvasManager.canvas.setZoom(canvasManager.canvas.getZoom() * 1.2)
  }
}

const handleShortcutZoomOut = () => {
  if (canvasManager.canvas) {
    canvasManager.canvas.setZoom(canvasManager.canvas.getZoom() * 0.8)
  }
}

const handleShortcutToggleSnap = () => {
  canvasManager.setSnapEnabled(!canvasManager.snapEnabled.value)
}

watch(() => props.imageId, (newId) => {
  if (newId) {
    loadImageById(newId)
  }
})

onMounted(() => {
  if (wrapperRef.value && canvasRef.value) {
    canvasManager.init(wrapperRef.value, canvasRef.value)
    canvasManager.userId = wsClient.userId

    canvasManager.on('annotation:add', handleAnnotationAdd)
    canvasManager.on('annotation:update', handleAnnotationUpdate)
    canvasManager.on('annotation:delete', handleAnnotationDelete)
    canvasManager.on('cursor:move', handleCursorMove)
    canvasManager.on('undo', handleUndo)
    canvasManager.on('redo', handleRedo)
    canvasManager.on('ot:operation', handleLocalOTOperation)

    wsClient.on('annotation_add', handleRemoteAnnotationAdd)
    wsClient.on('annotation_update', handleRemoteAnnotationUpdate)
    wsClient.on('annotation_delete', handleRemoteAnnotationDelete)
    wsClient.on('cursor_move', handleRemoteCursorMove)
    wsClient.on('leave', handleUserLeave)
    wsClient.on('undo', handleUndo)
    wsClient.on('redo', handleRedo)
    wsClient.on('ot_operation', handleOTOperation)

    shortcutManager.init()
    shortcutManager.on('action:tool', handleShortcutTool)
    shortcutManager.on('action:undo', handleUndo)
    shortcutManager.on('action:redo', handleRedo)
    shortcutManager.on('action:delete', handleShortcutDelete)
    shortcutManager.on('action:select_all', handleShortcutSelectAll)
    shortcutManager.on('action:escape', handleShortcutEscape)
    shortcutManager.on('action:zoom_in', handleShortcutZoomIn)
    shortcutManager.on('action:zoom_out', handleShortcutZoomOut)
    shortcutManager.on('action:toggle_snap', handleShortcutToggleSnap)
  }

  if (props.imageId) {
    loadImageById(props.imageId)
  }
})

onUnmounted(() => {
  canvasManager.off('annotation:add', handleAnnotationAdd)
  canvasManager.off('annotation:update', handleAnnotationUpdate)
  canvasManager.off('annotation:delete', handleAnnotationDelete)
  canvasManager.off('cursor:move', handleCursorMove)
  canvasManager.off('undo', handleUndo)
  canvasManager.off('redo', handleRedo)
  canvasManager.off('ot:operation', handleLocalOTOperation)

  wsClient.off('annotation_add', handleRemoteAnnotationAdd)
  wsClient.off('annotation_update', handleRemoteAnnotationUpdate)
  wsClient.off('annotation_delete', handleRemoteAnnotationDelete)
  wsClient.off('cursor_move', handleRemoteCursorMove)
  wsClient.off('leave', handleUserLeave)
  wsClient.off('undo', handleUndo)
  wsClient.off('redo', handleRedo)
  wsClient.off('ot_operation', handleOTOperation)

  shortcutManager.off('action:tool', handleShortcutTool)
  shortcutManager.off('action:undo', handleUndo)
  shortcutManager.off('action:redo', handleRedo)
  shortcutManager.off('action:delete', handleShortcutDelete)
  shortcutManager.off('action:select_all', handleShortcutSelectAll)
  shortcutManager.off('action:escape', handleShortcutEscape)
  shortcutManager.off('action:zoom_in', handleShortcutZoomIn)
  shortcutManager.off('action:zoom_out', handleShortcutZoomOut)
  shortcutManager.off('action:toggle_snap', handleShortcutToggleSnap)
  shortcutManager.destroy()

  canvasManager.destroy()
})

defineExpose({
  triggerFileInput,
  loadImage,
  loadImageById,
  canvasManager,
  currentImage,
  imageElement: currentImageElement
})
</script>

<style scoped>
.canvas-wrapper {
  position: relative;
  flex: 1;
  background-color: #f0f2f5;
  background-image:
    linear-gradient(45deg, #e4e7ed 25%, transparent 25%),
    linear-gradient(-45deg, #e4e7ed 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #e4e7ed 75%),
    linear-gradient(-45deg, transparent 75%, #e4e7ed 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
  overflow: hidden;
}

.canvas-wrapper :deep(canvas) {
  outline: none;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #909399;
}

.empty-icon {
  margin-bottom: 16px;
}

.empty-state h3 {
  font-size: 18px;
  margin-bottom: 8px;
  color: #606266;
}

.empty-state p {
  margin-bottom: 24px;
}

.empty-upload {
  display: inline-flex;
  cursor: pointer;
}

.image-info {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  font-size: 13px;
  color: #606266;
}

.image-name {
  font-weight: 500;
  color: #303133;
}

.annotation-count {
  color: #409eff;
  font-weight: 500;
}

.tool-hint {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 24px;
  background-color: rgba(64, 158, 255, 0.9);
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}
</style>
