<template>
  <div class="mindmap-canvas-container" ref="containerRef">
    <v-stage
      ref="stageRef"
      :config="stageConfig"
      @click="handleStageClick"
      @wheel="handleWheel"
      @mousedown="handleMouseDown"
      @mouseup="handleMouseUp"
      @mousemove="handleMouseMove"
    >
      <v-layer ref="layerRef">
        <ConnectionLine
          v-for="connection in connections"
          :key="connection.id"
          :from-node="connection.from"
          :to-node="connection.to"
          :color="connection.color"
        />

        <MindMapNode
          v-for="node in visibleNodes"
          :key="node.id"
          :ref="el => setNodeRef(node.id, el)"
          :node="node"
          :is-selected="selectedNodeId === node.id"
          :is-search-result="searchResults.includes(node.id)"
          :search-keyword="searchKeyword"
          @select="handleNodeSelect"
          @edit="handleNodeEdit"
          @dragstart="handleNodeDragStart"
          @dragend="handleNodeDragEnd"
          @toggle-collapse="handleToggleCollapse"
        />
      </v-layer>
    </v-stage>

    <div
      v-if="editingNodeId"
      class="node-editor-overlay"
      @click.self="stopEditing"
    >
      <div class="node-editor">
        <div class="editor-toolbar">
          <button
            :class="{ active: fontWeight === 'bold' }"
            @click="toggleFormat('bold')"
            title="粗体"
          >
            <b>B</b>
          </button>
          <button
            :class="{ active: fontStyle === 'italic' }"
            @click="toggleFormat('italic')"
            title="斜体"
          >
            <i>I</i>
          </button>
          <button
            :class="{ active: textDecoration === 'underline' }"
            @click="toggleFormat('underline')"
            title="下划线"
          >
            <u>U</u>
          </button>
          <div class="color-picker-wrapper">
            <input
              type="color"
              v-model="nodeColor"
            />
          </div>
          <button @click="decreaseFont" title="减小字号">-</button>
          <span class="font-size">{{ fontSize }}px</span>
          <button @click="increaseFont" title="增大字号">+</button>
        </div>
        <textarea
          ref="editorTextarea"
          v-model="editText"
          :style="textareaStyle"
          @keydown="handleEditorKeydown"
          placeholder="输入节点内容..."
        ></textarea>
        <div class="editor-actions">
          <button @click="saveEdit" class="save-btn">保存</button>
          <button @click="stopEditing" class="cancel-btn">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import MindMapNode from './MindMapNode.vue'
import ConnectionLine from './ConnectionLine.vue'
import { useMindMapStore } from '../store/mindmap.js'

const props = defineProps({
  width: {
    type: Number,
    default: 800
  },
  height: {
    type: Number,
    default: 600
  }
})

const emit = defineEmits(['node-selected', 'node-edited', 'node-deleted', 'canvas-click'])

const store = useMindMapStore()
const stageRef = ref(null)
const layerRef = ref(null)
const containerRef = ref(null)
const editorTextarea = ref(null)
const nodeRefs = ref({})
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const editingNodeId = ref(null)
const editText = ref('')
const fontWeight = ref('normal')
const fontStyle = ref('normal')
const textDecoration = ref('none')
const nodeColor = ref('#409eff')
const fontSize = ref(14)

const { state } = store

const selectedNodeId = computed(() => state.selectedNodeId)
const searchResults = computed(() => state.searchResults)
const searchKeyword = computed(() => state.searchKeyword)

const visibleNodes = computed(() => {
  const visible = []
  function collectVisible(nodeId) {
    const node = state.nodes[nodeId]
    if (!node) return
    visible.push(node)
    if (!node.collapsed) {
      node.children.forEach(childId => collectVisible(childId))
    }
  }
  if (state.rootNodeId) {
    collectVisible(state.rootNodeId)
  }
  return visible
})

const connections = computed(() => {
  const conns = []
  function collectConnections(nodeId) {
    const node = state.nodes[nodeId]
    if (!node || node.collapsed) return
    node.children.forEach(childId => {
      const child = state.nodes[childId]
      if (child) {
        conns.push({
          id: `${nodeId}-${childId}`,
          from: node,
          to: child,
          color: node.color
        })
        collectConnections(childId)
      }
    })
  }
  if (state.rootNodeId) {
    collectConnections(state.rootNodeId)
  }
  return conns
})

const stageConfig = computed(() => ({
  width: props.width,
  height: props.height,
  scaleX: state.scale,
  scaleY: state.scale,
  x: state.offsetX,
  y: state.offsetY,
  draggable: false
}))

const textareaStyle = computed(() => ({
  fontSize: `${fontSize.value}px`,
  fontWeight: fontWeight.value,
  fontStyle: fontStyle.value,
  textDecoration: textDecoration.value,
  color: getContrastColor(nodeColor.value)
}))

function setNodeRef(id, el) {
  if (el) {
    nodeRefs.value[id] = el
  }
}

function handleStageClick() {
  store.clearSelection()
  emit('canvas-click')
}

function handleWheel(e) {
  e.evt.preventDefault()
  const oldScale = state.scale
  const delta = e.evt.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(0.25, Math.min(4, oldScale + delta))
  store.setScale(newScale)
}

function handleMouseDown(e) {
  if (e.evt.button === 1 || e.evt.button === 2 || e.evt.ctrlKey) {
    isPanning.value = true
    panStart.value = {
      x: e.evt.clientX - state.offsetX,
      y: e.evt.clientY - state.offsetY
    }
  }
}

function handleMouseUp() {
  isPanning.value = false
}

function handleMouseMove(e) {
  if (isPanning.value) {
    store.setOffset(e.evt.clientX - panStart.value.x, e.evt.clientY - panStart.value.y)
  }
}

function handleNodeSelect(nodeId) {
  store.selectNode(nodeId)
  emit('node-selected', nodeId)
}

function handleNodeEdit(nodeId) {
  const node = state.nodes[nodeId]
  if (!node) return

  editingNodeId.value = nodeId
  editText.value = node.text
  fontWeight.value = node.fontWeight
  fontStyle.value = node.fontStyle
  textDecoration.value = node.textDecoration
  nodeColor.value = node.color
  fontSize.value = node.fontSize

  nextTick(() => {
    if (editorTextarea.value) {
      editorTextarea.value.focus()
      editorTextarea.value.select()
    }
  })
}

function handleNodeDragStart(nodeId, e) {
}

function handleNodeDragEnd(nodeId, e) {
  const node = state.nodes[nodeId]
  if (!node) return
  const newPos = e.target.position()
  store.updateNode(nodeId, {
    x: newPos.x,
    y: newPos.y
  })
  store.saveToStorage()
}

function handleToggleCollapse(nodeId) {
  store.toggleCollapse(nodeId)
  store.saveToStorage()
}

function toggleFormat(format) {
  switch (format) {
    case 'bold':
      fontWeight.value = fontWeight.value === 'bold' ? 'normal' : 'bold'
      break
    case 'italic':
      fontStyle.value = fontStyle.value === 'italic' ? 'normal' : 'italic'
      break
    case 'underline':
      textDecoration.value = textDecoration.value === 'underline' ? 'none' : 'underline'
      break
  }
}

function increaseFont() {
  fontSize.value = Math.min(32, fontSize.value + 2)
}

function decreaseFont() {
  fontSize.value = Math.max(10, fontSize.value - 2)
}

function handleEditorKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    saveEdit()
  } else if (e.key === 'Escape') {
    stopEditing()
  }
}

function saveEdit() {
  if (!editingNodeId.value) return

  store.updateNode(editingNodeId.value, {
    text: editText.value,
    fontWeight: fontWeight.value,
    fontStyle: fontStyle.value,
    textDecoration: textDecoration.value,
    color: nodeColor.value,
    fontSize: fontSize.value
  })
  store.saveToStorage()
  stopEditing()
}

function stopEditing() {
  editingNodeId.value = null
  editText.value = ''
}

function getContrastColor(bgColor) {
  const hex = bgColor.replace('#', '')
  const r = parseInt(hex.substr(0, 2), 16)
  const g = parseInt(hex.substr(2, 2), 16)
  const b = parseInt(hex.substr(4, 2), 16)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  return brightness > 128 ? '#333333' : '#ffffff'
}

function focusNode(nodeId) {
  const node = state.nodes[nodeId]
  if (!node) return

  const centerX = props.width / 2 - node.x * state.scale - node.width * state.scale / 2
  const centerY = props.height / 2 - node.y * state.scale - node.height * state.scale / 2

  store.setOffset(centerX, centerY)
  store.selectNode(nodeId)
}

function getStage() {
  if (stageRef.value) {
    return stageRef.value.getStage()
  }
  return null
}

defineExpose({
  focusNode,
  getStage
})

onMounted(() => {
  const handleKeyDown = (e) => {
    if (editingNodeId.value) return

    if (e.key === 'Delete' && selectedNodeId.value) {
      store.deleteNode(selectedNodeId.value)
      store.saveToStorage()
      emit('node-deleted', selectedNodeId.value)
    }

    if (e.key === 'Tab' && selectedNodeId.value) {
      e.preventDefault()
      const parent = state.nodes[selectedNodeId.value]
      if (parent) {
        const newNode = store.createNode('新节点', selectedNodeId.value, parent.x + 200, parent.y)
        store.selectNode(newNode.id)
        store.saveToStorage()
        emit('node-edited', newNode.id)
      }
    }
  }

  window.addEventListener('keydown', handleKeyDown)
  return () => window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.mindmap-canvas-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 20px,
      rgba(0, 0, 0, 0.03) 20px,
      rgba(0, 0, 0, 0.03) 21px
    ),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 20px,
      rgba(0, 0, 0, 0.03) 20px,
      rgba(0, 0, 0, 0.03) 21px
    );
  cursor: grab;
}

.mindmap-canvas-container:active {
  cursor: grabbing;
}

.node-editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.node-editor {
  background: var(--bg-color);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  padding: 16px;
  min-width: 350px;
}

.editor-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
  align-items: center;
}

.editor-toolbar button {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-color);
  color: var(--text-color);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.editor-toolbar button:hover {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.editor-toolbar button.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.color-picker-wrapper {
  display: flex;
  align-items: center;
}

.color-picker-wrapper input[type="color"] {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  padding: 2px;
  background: var(--bg-color);
}

.font-size {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 40px;
  text-align: center;
}

textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  resize: vertical;
  font-family: inherit;
  font-size: 14px;
  background: var(--bg-color);
  color: var(--text-color);
}

textarea:focus {
  outline: none;
  border-color: var(--primary-color);
}

.editor-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  justify-content: flex-end;
}

.save-btn, .cancel-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.save-btn {
  background: var(--primary-color);
  color: white;
  border: none;
}

.save-btn:hover {
  opacity: 0.9;
}

.cancel-btn {
  background: var(--border-color);
  color: var(--text-color);
  border: none;
}

.cancel-btn:hover {
  opacity: 0.8;
}
</style>
