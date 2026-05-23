<template>
  <div class="app">
    <Toolbar
      v-model:tool="currentTool"
      v-model:color="currentColor"
      v-model:lineWidth="currentLineWidth"
      :canUndo="canUndo"
      :canRedo="canRedo"
      :isConnected="isConnected"
      :userCount="userCount"
      @undo="undo"
      @redo="redo"
      @zoomIn="zoomIn"
      @zoomOut="zoomOut"
      @resetView="resetView"
      @snapshot="saveSnapshot"
      @clear="clearCanvas"
      @presentation="openPresentation"
    />
    
    <div class="main-content">
      <TemplatePanel @applyTemplate="applyTemplate" />
      
      <WhiteboardCanvas
        ref="canvasRef"
        :tool="currentTool"
        :color="currentColor"
        :lineWidth="currentLineWidth"
        :layers="layers"
        :comments="comments"
        :activeCommentId="activeCommentId"
        :enablePressure="enablePressure"
        @startDraw="handleStartDraw"
        @appendPoints="handleAppendPoints"
        @endDraw="handleEndDraw"
        @addShape="handleAddShape"
        @layerAdded="handleLayerAdded"
        @layerUpdated="handleLayerUpdated"
        @layerDeleted="handleLayerDeleted"
        @cursorMove="handleCursorMove"
        @addComment="handleAddComment"
        @selectComment="handleSelectComment"
      />
      
      <CommentPanel
        :comments="comments"
        :activeCommentId="activeCommentId"
        :currentUser="currentUser"
        :onlineUsers="onlineUsers"
        @select="handleSelectComment"
        @reply="handleReplyComment"
        @resolve="handleResolveComment"
      />
      
      <LayerPanel
        :layers="layers"
        :selectedLayerId="selectedLayerId"
        @select="selectLayer"
        @toggleVisibility="toggleLayerVisibility"
        @move="moveLayer"
        @delete="deleteLayer"
      />
    </div>

    <PresentationMode
      :isOpen="showPresentation"
      :layers="layers"
      @close="showPresentation = false"
    />

    <div v-if="!isConnected" class="connection-overlay">
      <div class="connection-modal">
        <h2>🎨 在线协作白板</h2>
        <p>输入会话ID加入或创建新会话</p>
        <input
          v-model="inputSessionId"
          type="text"
          placeholder="会话ID (留空创建默认)"
          @keyup.enter="connectToSession"
        />
        <input
          v-model="inputUserName"
          type="text"
          placeholder="您的昵称"
          @keyup.enter="connectToSession"
        />
        <button class="btn primary" @click="connectToSession">
          {{ inputSessionId ? '加入会话' : '创建新会话' }}
        </button>
        <div class="hint">💡 相同会话ID的用户可以实时协作</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import Toolbar from './components/Toolbar.vue'
import WhiteboardCanvas from './components/WhiteboardCanvas.vue'
import LayerPanel from './components/LayerPanel.vue'
import TemplatePanel from './components/TemplatePanel.vue'
import CommentPanel from './components/CommentPanel.vue'
import PresentationMode from './components/PresentationMode.vue'
import { useWebSocket } from './composables/useWebSocket'

const canvasRef = ref(null)
const inputSessionId = ref('')
const inputUserName = ref('用户' + Math.floor(Math.random() * 1000))
const enablePressure = ref(true)
const showPresentation = ref(false)

const currentTool = ref('pen')
const currentColor = ref('#000000')
const currentLineWidth = ref(3)

const layers = ref([])
const selectedLayerId = ref(null)
const commandQueue = ref([])
const commandIndex = ref(-1)
const pendingLayers = ref(new Map())

const comments = ref([])
const activeCommentId = ref(null)
const currentUser = ref('')

const onlineUsers = ref([])

const {
  isConnected,
  userCount,
  connect,
  send,
  on,
  off,
  clientId
} = useWebSocket()

const canUndo = computed(() => commandIndex.value >= 0)
const canRedo = computed(() => commandIndex.value < commandQueue.value.length - 1)

function connectToSession() {
  currentUser.value = inputUserName.value.trim() || '匿名用户'
  const sessionId = inputSessionId.value.trim() || 'default'
  connect(sessionId, currentUser.value)
}

function executeCommand(command) {
  command.id = command.id || Date.now().toString()
  
  commandQueue.value = commandQueue.value.slice(0, commandIndex.value + 1)
  commandQueue.value.push(command)
  commandIndex.value++
  
  applyCommand(command)
}

function applyCommand(command) {
  switch (command.type) {
    case 'addLayer':
      layers.value.push(command.layer)
      break
    case 'updateLayer': {
        const index = layers.value.findIndex(l => l.id === command.layer.id)
        if (index !== -1) {
          layers.value[index] = command.layer
        }
        break
      }
    case 'deleteLayer':
      layers.value = layers.value.filter(l => l.id !== command.layerId)
      break
    case 'moveLayer': {
        const { layerId, direction } = command
        const index = layers.value.findIndex(l => l.id === layerId)
        if (index !== -1) {
          const newIndex = index + direction
          if (newIndex >= 0 && newIndex < layers.value.length) {
            const temp = layers.value[index]
            layers.value[index] = layers.value[newIndex]
            layers.value[newIndex] = temp
          }
        }
        break
      }
    case 'clear':
      layers.value = []
      break
  }
}

function undoCommand(command) {
  switch (command.type) {
    case 'addLayer':
      layers.value = layers.value.filter(l => l.id !== command.layerId)
      break
    case 'updateLayer':
      if (command.originalLayer) {
        const index = layers.value.findIndex(l => l.id === command.layer.id)
        if (index !== -1) {
          layers.value[index] = command.originalLayer
        }
      }
      break
    case 'deleteLayer':
      if (command.layer) {
        layers.value.push(command.layer)
      }
      break
    case 'moveLayer': {
        const { layerId, direction } = command
        const index = layers.value.findIndex(l => l.id === layerId)
        if (index !== -1) {
          const newIndex = index - direction
          if (newIndex >= 0 && newIndex < layers.value.length) {
            const temp = layers.value[index]
            layers.value[index] = layers.value[newIndex]
            layers.value[newIndex] = temp
          }
        }
        break
      }
    case 'clear':
      if (command.originalLayers) {
        layers.value = command.originalLayers
      }
      break
  }
}

function applyTemplate(template) {
  const command = {
    type: 'clear',
    originalLayers: JSON.parse(JSON.stringify(layers.value))
  }
  executeCommand(command)
  
  template.layers.forEach(layer => {
    const newLayer = {
      ...layer,
      id: uuidv4()
    }
    const addCommand = {
      type: 'addLayer',
      layerId: newLayer.id,
      layer: newLayer
    }
    executeCommand(addCommand)
  })
  
  send({ type: 'syncState', state: {
    layers: layers.value,
    commandQueue: commandQueue.value,
    commandIndex: commandIndex.value
  }})
  
  saveToLocalStorage()
}

function handleStartDraw({ layer }) {
  pendingLayers.value.set(layer.id, JSON.parse(JSON.stringify(layer)))
  send({ type: 'startDraw', layer })
}

function handleAppendPoints({ layerId, points }) {
  const pendingLayer = pendingLayers.value.get(layerId)
  if (pendingLayer && pendingLayer.points) {
    pendingLayer.points.push(...points)
  }
  
  const localLayer = layers.value.find(l => l.id === layerId)
  if (localLayer && localLayer.points) {
    localLayer.points.push(...points)
  }
  
  send({ type: 'appendPoints', layerId, points })
}

function handleEndDraw({ layerId, layer }) {
  const pendingLayer = pendingLayers.value.get(layerId)
  if (pendingLayer) {
    pendingLayers.value.delete(layerId)
    
    const command = {
      type: 'addLayer',
      layerId,
      layer: JSON.parse(JSON.stringify(pendingLayer))
    }
    executeCommand(command)
  }
  
  send({ type: 'endDraw', layerId })
}

function handleAddShape({ layer }) {
  const command = {
    type: 'addLayer',
    layerId: layer.id,
    layer: JSON.parse(JSON.stringify(layer))
  }
  executeCommand(command)
  
  send({ type: 'addShape', layer })
}

function handleLayerAdded(layer) {
  handleAddShape({ layer })
}

function handleLayerUpdated(layer) {
  const originalLayer = layers.value.find(l => l.id === layer.id)
  
  const command = {
    type: 'updateLayer',
    layerId: layer.id,
    layer: JSON.parse(JSON.stringify(layer)),
    originalLayer: originalLayer ? JSON.parse(JSON.stringify(originalLayer)) : null
  }
  executeCommand(command)
  
  send({ type: 'updateLayer', layer })
}

function handleLayerDeleted(layerId) {
  deleteLayer(layerId)
}

function selectLayer(id) {
  selectedLayerId.value = id
}

function toggleLayerVisibility(id) {
  const layer = layers.value.find(l => l.id === id)
  if (layer) {
    handleLayerUpdated({ ...layer, visible: !layer.visible })
  }
}

function moveLayer({ id, direction }) {
  const command = {
    type: 'moveLayer',
    layerId: id,
    direction
  }
  executeCommand(command)
  
  send({ type: 'moveLayer', layerId: id, direction })
}

function deleteLayer(id) {
  const layer = layers.value.find(l => l.id === id)
  
  const command = {
    type: 'deleteLayer',
    layerId: id,
    layer: layer ? JSON.parse(JSON.stringify(layer)) : null
  }
  executeCommand(command)
  
  send({ type: 'deleteLayer', layerId: id })
}

function undo() {
  if (!canUndo.value) return
  
  const command = commandQueue.value[commandIndex.value]
  undoCommand(command)
  commandIndex.value--
  
  send({ type: 'undo' })
  saveToLocalStorage()
}

function redo() {
  if (!canRedo.value) return
  
  commandIndex.value++
  const command = commandQueue.value[commandIndex.value]
  applyCommand(command)
  
  send({ type: 'redo' })
  saveToLocalStorage()
}

function zoomIn() {
  if (canvasRef.value) {
    canvasRef.value.scale.value = Math.min(5, canvasRef.value.scale.value * 1.2)
    canvasRef.value.render()
  }
}

function zoomOut() {
  if (canvasRef.value) {
    canvasRef.value.scale.value = Math.max(0.1, canvasRef.value.scale.value / 1.2)
    canvasRef.value.render()
  }
}

function resetView() {
  if (canvasRef.value) {
    canvasRef.value.resetView()
  }
}

function saveSnapshot() {
  if (canvasRef.value) {
    const dataUrl = canvasRef.value.takeSnapshot()
    const link = document.createElement('a')
    link.download = `whiteboard-${Date.now()}.png`
    link.href = dataUrl
    link.click()
  }
}

function clearCanvas() {
  if (!confirm('确定要清空所有内容吗？')) return
  
  const command = {
    type: 'clear',
    originalLayers: JSON.parse(JSON.stringify(layers.value))
  }
  executeCommand(command)
  
  send({ type: 'clear' })
  saveToLocalStorage()
}

function openPresentation() {
  showPresentation.value = true
}

function handleCursorMove(pos) {
  send({ type: 'cursor', x: pos.x, y: pos.y, screenX: pos.screenX, screenY: pos.screenY })
}

function handleAddComment({ x, y, content }) {
  const comment = {
    id: uuidv4(),
    x,
    y,
    content,
    author: currentUser.value,
    timestamp: Date.now(),
    resolved: false,
    replies: []
  }
  comments.value.push(comment)
  send({ type: 'addComment', comment })
  saveCommentsToLocalStorage()
}

function handleSelectComment(commentId) {
  activeCommentId.value = commentId
  
  const comment = comments.value.find(c => c.id === commentId)
  if (comment && canvasRef.value) {
    canvasRef.value.offsetX.value = -comment.x * canvasRef.value.scale.value + 400
    canvasRef.value.offsetY.value = -comment.y * canvasRef.value.scale.value + 300
    canvasRef.value.render()
  }
}

function handleReplyComment({ commentId, content }) {
  const comment = comments.value.find(c => c.id === commentId)
  if (comment) {
    const reply = {
      id: uuidv4(),
      content,
      author: currentUser.value,
      timestamp: Date.now()
    }
    comment.replies = comment.replies || []
    comment.replies.push(reply)
    
    send({ type: 'replyComment', commentId, reply })
    saveCommentsToLocalStorage()
  }
}

function handleResolveComment(commentId) {
  const comment = comments.value.find(c => c.id === commentId)
  if (comment) {
    comment.resolved = !comment.resolved
    send({ type: 'resolveComment', commentId, resolved: comment.resolved })
    saveCommentsToLocalStorage()
  }
}

function saveToLocalStorage() {
  const state = {
    layers: layers.value,
    commandQueue: commandQueue.value,
    commandIndex: commandIndex.value
  }
  localStorage.setItem('whiteboard-state', JSON.stringify(state))
}

function saveCommentsToLocalStorage() {
  localStorage.setItem('whiteboard-comments', JSON.stringify(comments.value))
}

function loadFromLocalStorage() {
  const saved = localStorage.getItem('whiteboard-state')
  if (saved) {
    try {
      const state = JSON.parse(saved)
      layers.value = state.layers || []
      commandQueue.value = state.commandQueue || []
      commandIndex.value = state.commandIndex ?? -1
    } catch (e) {
      console.error('Failed to load saved state:', e)
    }
  }
  
  const savedComments = localStorage.getItem('whiteboard-comments')
  if (savedComments) {
    try {
      comments.value = JSON.parse(savedComments) || []
    } catch (e) {
      console.error('Failed to load saved comments:', e)
    }
  }
}

function setupWebSocketHandlers() {
  on('init', (message) => {
    onlineUsers.value = message.onlineUsers || [{ id: clientId.value, name: currentUser.value }]
    
    if (message.state) {
      layers.value = message.state.layers || []
      commandQueue.value = message.state.commandQueue || []
      commandIndex.value = message.state.commandIndex ?? -1
    }
    
    if (message.comments) {
      comments.value = message.comments || []
    }
    
    if (layers.value.length === 0) {
      loadFromLocalStorage()
      if (layers.value.length > 0) {
        send({
          type: 'syncState',
          state: {
            layers: layers.value,
            commandQueue: commandQueue.value,
            commandIndex: commandIndex.value
          }
        })
      }
    }
  })

  on('userJoined', (message) => {
    if (!onlineUsers.value.find(u => u.id === message.clientId)) {
      onlineUsers.value.push({ id: message.clientId, name: message.userName || '用户' })
    }
  })

  on('startDraw', (message) => {
    if (message.clientId !== clientId.value && message.layer) {
      pendingLayers.value.set(message.layer.id, JSON.parse(JSON.stringify(message.layer)))
      layers.value.push(message.layer)
    }
  })

  on('appendPoints', (message) => {
    if (message.clientId !== clientId.value) {
      const layer = layers.value.find(l => l.id === message.layerId)
      const pendingLayer = pendingLayers.value.get(message.layerId)
      
      if (layer && layer.points) {
        layer.points.push(...message.points)
      }
      if (pendingLayer && pendingLayer.points) {
        pendingLayer.points.push(...message.points)
      }
    }
  })

  on('endDraw', (message) => {
    if (message.clientId !== clientId.value) {
      pendingLayers.value.delete(message.layerId)
      saveToLocalStorage()
    }
  })

  on('addShape', (message) => {
    if (message.clientId !== clientId.value && message.layer) {
      const command = {
        type: 'addLayer',
        layerId: message.layer.id,
        layer: JSON.parse(JSON.stringify(message.layer))
      }
      
      commandQueue.value = commandQueue.value.slice(0, commandIndex.value + 1)
      commandQueue.value.push(command)
      commandIndex.value++
      layers.value.push(message.layer)
      saveToLocalStorage()
    }
  })

  on('updateLayer', (message) => {
    if (message.clientId !== clientId.value && message.layer) {
      const index = layers.value.findIndex(l => l.id === message.layer.id)
      if (index !== -1) {
        const command = {
          type: 'updateLayer',
          layerId: message.layer.id,
          layer: JSON.parse(JSON.stringify(message.layer)),
          originalLayer: JSON.parse(JSON.stringify(layers.value[index]))
        }
        
        commandQueue.value = commandQueue.value.slice(0, commandIndex.value + 1)
        commandQueue.value.push(command)
        commandIndex.value++
        layers.value[index] = message.layer
        saveToLocalStorage()
      }
    }
  })

  on('deleteLayer', (message) => {
    if (message.clientId !== clientId.value) {
      const layer = layers.value.find(l => l.id === message.layerId)
      
      const command = {
        type: 'deleteLayer',
        layerId: message.layerId,
        layer: layer ? JSON.parse(JSON.stringify(layer)) : null
      }
      
      commandQueue.value = commandQueue.value.slice(0, commandIndex.value + 1)
      commandQueue.value.push(command)
      commandIndex.value++
      layers.value = layers.value.filter(l => l.id !== message.layerId)
      saveToLocalStorage()
    }
  })

  on('moveLayer', (message) => {
    if (message.clientId !== clientId.value) {
      const { layerId, direction } = message
      const index = layers.value.findIndex(l => l.id === layerId)
      
      if (index !== -1) {
        const newIndex = index + direction
        if (newIndex >= 0 && newIndex < layers.value.length) {
          const command = {
            type: 'moveLayer',
            layerId,
            direction
          }
          
          commandQueue.value = commandQueue.value.slice(0, commandIndex.value + 1)
          commandQueue.value.push(command)
          commandIndex.value++
          
          const temp = layers.value[index]
          layers.value[index] = layers.value[newIndex]
          layers.value[newIndex] = temp
          saveToLocalStorage()
        }
      }
    }
  })

  on('undo', (message) => {
    if (message.clientId !== clientId.value) {
      if (commandIndex.value >= 0) {
        const command = commandQueue.value[commandIndex.value]
        undoCommand(command)
        commandIndex.value--
        saveToLocalStorage()
      }
    }
  })

  on('redo', (message) => {
    if (message.clientId !== clientId.value) {
      if (commandIndex.value < commandQueue.value.length - 1) {
        commandIndex.value++
        const command = commandQueue.value[commandIndex.value]
        applyCommand(command)
        saveToLocalStorage()
      }
    }
  })

  on('clear', (message) => {
    if (message.clientId !== clientId.value) {
      const command = {
        type: 'clear',
        originalLayers: JSON.parse(JSON.stringify(layers.value))
      }
      
      commandQueue.value = commandQueue.value.slice(0, commandIndex.value + 1)
      commandQueue.value.push(command)
      commandIndex.value++
      layers.value = []
      saveToLocalStorage()
    }
  })

  on('stateSync', (message) => {
    if (message.clientId !== clientId.value && message.state) {
      layers.value = message.state.layers || []
      commandQueue.value = message.state.commandQueue || []
      commandIndex.value = message.state.commandIndex ?? -1
      saveToLocalStorage()
    }
  })

  on('addComment', (message) => {
    if (message.clientId !== clientId.value && message.comment) {
      comments.value.push(message.comment)
      saveCommentsToLocalStorage()
    }
  })

  on('replyComment', (message) => {
    if (message.clientId !== clientId.value) {
      const comment = comments.value.find(c => c.id === message.commentId)
      if (comment && message.reply) {
        comment.replies = comment.replies || []
        comment.replies.push(message.reply)
        saveCommentsToLocalStorage()
      }
    }
  })

  on('resolveComment', (message) => {
    if (message.clientId !== clientId.value) {
      const comment = comments.value.find(c => c.id === message.commentId)
      if (comment) {
        comment.resolved = message.resolved
        saveCommentsToLocalStorage()
      }
    }
  })

  on('cursor', (message) => {
    if (message.clientId !== clientId.value && canvasRef.value) {
      canvasRef.value.updateRemoteCursor(
        message.clientId,
        message.x,
        message.y,
        message.screenX,
        message.screenY
      )
    }
  })

  on('userLeft', (message) => {
    onlineUsers.value = onlineUsers.value.filter(u => u.id !== message.clientId)
    if (canvasRef.value) {
      canvasRef.value.removeRemoteCursor(message.clientId)
    }
  })
}

function handleKeydown(e) {
  if (e.ctrlKey || e.metaKey) {
    if (e.key === 'z') {
      e.preventDefault()
      if (e.shiftKey) {
        redo()
      } else {
        undo()
      }
    } else if (e.key === 'y') {
      e.preventDefault()
      redo()
    } else if (e.key === 'p') {
      e.preventDefault()
      openPresentation()
    }
  }
}

onMounted(() => {
  setupWebSocketHandlers()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.app {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.connection-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.connection-modal {
  background: white;
  padding: 40px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
  max-width: 400px;
  width: 90%;
}

.connection-modal h2 {
  font-size: 24px;
  margin-bottom: 12px;
  color: #1f2937;
}

.connection-modal p {
  color: #6b7280;
  margin-bottom: 24px;
}

.connection-modal input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.connection-modal input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.connection-modal .btn.primary {
  width: 100%;
  padding: 12px;
  background: var(--primary-color);
  color: white;
  font-size: 16px;
  font-weight: 500;
  margin-top: 8px;
}

.connection-modal .btn.primary:hover {
  background: #2563eb;
}

.hint {
  margin-top: 16px;
  font-size: 13px;
  color: #6b7280;
}
</style>
