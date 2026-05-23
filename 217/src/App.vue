<template>
  <div class="app-container">
    <div class="sidebar">
      <div class="sidebar-header">
        <span>流程图编辑器</span>
        <div class="collab-status" :class="{ connected: isConnected }">
          <span class="status-dot"></span>
          <span>{{ isConnected ? '协作中' : '离线' }}</span>
        </div>
      </div>
      
      <div class="collaborators-list" v-if="isConnected && remoteCollaborators.length > 0">
        <div class="collab-title">在线协作者</div>
        <div v-for="c in remoteCollaborators" :key="c.id" class="collaborator-item">
          <div class="collaborator-avatar" :style="{ backgroundColor: c.color }">
            {{ c.name.charAt(0) }}
          </div>
          <span class="collaborator-name">{{ c.name }}</span>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="section-title">节点类型</div>
        <div
          v-for="node in nodeTypes"
          :key="node.type"
          class="node-item"
          draggable="true"
          @dragstart="handleDragStart($event, node.type)"
        >
          <div class="node-icon" v-html="node.icon"></div>
          <span class="node-label">{{ node.label }}</span>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="section-title">模板库</div>
        <div
          v-for="template in templates"
          :key="template.id"
          class="template-item"
          @click="loadTemplate(template)"
        >
          <div class="template-thumb">{{ template.thumbnail }}</div>
          <div class="template-info">
            <div class="template-name">{{ template.name }}</div>
            <div class="template-desc">{{ template.description }}</div>
          </div>
        </div>
      </div>

      <div class="toolbar">
        <button class="toolbar-btn" @click="handleUndo" :disabled="!canUndo">撤销</button>
        <button class="toolbar-btn" @click="handleRedo" :disabled="!canRedo">重做</button>
        <button class="toolbar-btn" @click="handleAutoLayout">自动布局</button>
        <button class="toolbar-btn" @click="handleClearAll">清空</button>
        <button class="toolbar-btn" :class="{ active: isConnected }" @click="toggleCollaboration">
          {{ isConnected ? '断开协作' : '连接协作' }}
        </button>
      </div>
    </div>

    <div class="main-area">
      <div class="canvas-header">
        <span class="canvas-title">编辑区域</span>
        <div class="canvas-actions">
          <button class="action-btn secondary" @click="exportJSON">导出JSON</button>
          <button class="action-btn primary" @click="exportImage">导出图片</button>
        </div>
      </div>
      <div class="canvas-container">
        <div class="canvas-wrapper" ref="canvasWrapper" @mousemove="handleMouseMove">
          <canvas ref="canvasElement"></canvas>
          
          <div
            v-for="collab in remoteCollaborators"
            :key="collab.id"
            class="collaborator-cursor"
            :style="{ left: collab.x + 'px', top: collab.y + 'px' }"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" :style="{ fill: collab.color }">
              <path d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87c.48 0 .72-.58.38-.92L6.35 2.85a.5.5 0 0 0-.85.36z"/>
            </svg>
            <div class="cursor-label" :style="{ backgroundColor: collab.color }">{{ collab.name }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="properties-panel">
      <div class="properties-header">
        <span>属性面板</span>
        <span v-if="selectedNode" class="node-comments-count" @click="showCommentsPanel = !showCommentsPanel">
          📝 {{ getNodeComments(selectedNode.id).length }}
        </span>
      </div>
      
      <div class="properties-content">
        <div v-if="selectedNode" class="properties-form">
          <div class="node-info">
            <span class="node-info-type">{{ getNodeTypeLabel(selectedNode.nodeType) }}</span>
          </div>
          <div class="form-group">
            <label class="form-label">名称</label>
            <input
              type="text"
              class="form-input"
              v-model="selectedNode.name"
              @input="handleNodeNameChange"
            />
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea
              class="form-textarea"
              v-model="selectedNode.description"
              @input="handleNodeDescriptionChange"
            ></textarea>
          </div>
          <button class="delete-btn" @click="handleDeleteSelectedNode">删除节点</button>
          
          <div class="comments-section" v-if="showCommentsPanel">
            <div class="section-title">批注</div>
            
            <div class="add-comment">
              <textarea
                class="comment-input"
                v-model="newCommentText"
                placeholder="添加批注..."
              ></textarea>
              <button class="comment-submit-btn" @click="handleAddComment" :disabled="!newCommentText.trim()">
                发送
              </button>
            </div>

            <div class="comments-list">
              <div
                v-for="comment in getNodeComments(selectedNode.id)"
                :key="comment.id"
                class="comment-item"
                :class="{ resolved: comment.resolved }"
              >
                <div class="comment-header">
                  <span class="comment-author">{{ comment.author }}</span>
                  <span class="comment-time">{{ formatTime(comment.createdAt) }}</span>
                  <button
                    class="resolve-btn"
                    :class="{ resolved: comment.resolved }"
                    @click="handleResolveComment(comment)"
                  >
                    {{ comment.resolved ? '✓ 已解决' : '解决' }}
                  </button>
                </div>
                <div class="comment-content">{{ comment.content }}</div>
                
                <div v-if="comment.replies.length > 0" class="replies-list">
                  <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
                    <div class="reply-header">
                      <span class="reply-author">{{ reply.author }}</span>
                      <span class="reply-time">{{ formatTime(reply.createdAt) }}</span>
                    </div>
                    <div class="reply-content">{{ reply.content }}</div>
                  </div>
                </div>

                <div class="reply-input-area">
                  <input
                    type="text"
                    class="reply-input"
                    v-model="replyTexts[comment.id]"
                    placeholder="回复..."
                    @keyup.enter="handleReplyComment(comment)"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          选择一个节点以编辑属性
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { fabric } from 'fabric'
import { 
  useHistory, 
  createAddNodeCommand,
  createDeleteNodeCommand,
  createUpdateNodeCommand,
  createMoveNodeCommand,
  createAddConnectionCommand,
  createAutoLayoutCommand,
  createClearAllCommand
} from './composables/useHistory'
import { useFlowchart } from './composables/useFlowchart'
import { useCollaboration } from './composables/useCollaboration'
import { flowchartTemplates } from './data/templates'

const canvasElement = ref(null)
const canvasWrapper = ref(null)
let canvas = null
let lastNodeData = {}
const newCommentText = ref('')
const replyTexts = reactive({})
const showCommentsPanel = ref(true)

const nodeTypes = [
  { type: 'start', label: '开始', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="#28a745"><circle cx="12" cy="12" r="10"/></svg>' },
  { type: 'end', label: '结束', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="#dc3545"><circle cx="12" cy="12" r="10"/></svg>' },
  { type: 'process', label: '处理', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="#007bff"><rect x="2" y="6" width="20" height="12" rx="2"/></svg>' },
  { type: 'decision', label: '判断', icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="#ffc107"><polygon points="12,2 22,12 12,22 2,12"/></svg>' }
]

const templates = flowchartTemplates

const {
  selectedNode,
  nodes,
  connections,
  comments,
  addNode,
  addNodeFromData,
  moveNode,
  updateNode,
  deleteNode,
  addConnectionFromData,
  deleteConnection,
  clearAll,
  autoLayout: runAutoLayout,
  exportToJSON,
  initCanvas,
  selectNodeByFabric,
  getNodeComments,
  addComment,
  replyComment,
  resolveComment
} = useFlowchart()

const {
  canUndo,
  canRedo,
  executeCommand,
  undo,
  redo
} = useHistory()

const {
  isConnected,
  remoteCollaborators,
  connect,
  disconnect,
  broadcastCursor,
  broadcastNodeAdd,
  broadcastNodeMove,
  broadcastNodeUpdate,
  broadcastNodeDelete,
  broadcastConnectionAdd
} = useCollaboration()

const handleDragStart = (event, nodeType) => {
  event.dataTransfer.setData('nodeType', nodeType)
}

const handleDragOver = (event) => {
  event.preventDefault()
}

const handleDrop = (event) => {
  event.preventDefault()
  const nodeType = event.dataTransfer.getData('nodeType')
  if (nodeType && canvas) {
    const rect = canvasWrapper.value.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    
    const config = {
      start: { width: 100, height: 50, label: '开始' },
      end: { width: 100, height: 50, label: '结束' },
      process: { width: 120, height: 60, label: '处理' },
      decision: { width: 100, height: 80, label: '判断' }
    }
    const cfg = config[nodeType]
    const nodeId = Math.max(...nodes.value.map(n => n.id), 0) + 1
    
    const nodeData = {
      id: nodeId,
      nodeType: nodeType,
      name: cfg.label,
      description: '',
      x: x,
      y: y
    }

    const command = createAddNodeCommand(
      nodeData,
      (data) => addNodeFromData(data, canvas),
      (id) => deleteNode(id, canvas)
    )
    executeCommand(command)

    if (isConnected.value) {
      broadcastNodeAdd(nodeData)
    }
  }
}

const getNodeTypeLabel = (type) => {
  const node = nodeTypes.find(n => n.type === type)
  return node ? node.label : type
}

const handleNodeNameChange = () => {
  if (selectedNode.value) {
    const nodeId = selectedNode.value.id
    const newName = selectedNode.value.name
    const oldData = lastNodeData[nodeId] || { name: selectedNode.value.name, description: selectedNode.value.description }
    
    const oldName = oldData.name
    if (oldName !== newName) {
      const command = createUpdateNodeCommand(
        nodeId,
        { name: oldName, description: oldData.description },
        { name: newName, description: oldData.description },
        (id, data) => updateNode(id, data, canvas)
      )
      executeCommand(command)
      lastNodeData[nodeId] = { name: newName, description: oldData.description }

      if (isConnected.value) {
        broadcastNodeUpdate(nodeId, { name: newName })
      }
    }
  }
}

const handleNodeDescriptionChange = () => {
  if (selectedNode.value) {
    const nodeId = selectedNode.value.id
    const newDesc = selectedNode.value.description
    const oldData = lastNodeData[nodeId] || { name: selectedNode.value.name, description: '' }
    
    const oldDesc = oldData.description
    if (oldDesc !== newDesc) {
      const command = createUpdateNodeCommand(
        nodeId,
        { name: oldData.name, description: oldDesc },
        { name: oldData.name, description: newDesc },
        (id, data) => updateNode(id, data, canvas)
      )
      executeCommand(command)
      lastNodeData[nodeId] = { name: oldData.name, description: newDesc }

      if (isConnected.value) {
        broadcastNodeUpdate(nodeId, { description: newDesc })
      }
    }
  }
}

const handleDeleteSelectedNode = () => {
  if (selectedNode.value) {
    const nodeId = selectedNode.value.id
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      const relatedConns = connections.value.filter(
        c => c.fromNodeId === nodeId || c.toNodeId === nodeId
      ).map(c => ({
        id: c.id,
        fromNodeId: c.fromNodeId,
        toNodeId: c.toNodeId
      }))

      const nodeData = {
        id: node.id,
        nodeType: node.nodeType,
        name: node.name,
        description: node.description,
        x: node.x,
        y: node.y
      }

      const command = createDeleteNodeCommand(
        nodeData,
        relatedConns,
        (data) => addNodeFromData(data, canvas),
        (id) => deleteNode(id, canvas),
        (conn) => addConnectionFromData(conn, canvas),
        (id) => deleteConnection(id, canvas)
      )
      executeCommand(command)
      selectedNode.value = null

      if (isConnected.value) {
        broadcastNodeDelete(nodeId)
      }
    }
  }
}

const handleAutoLayout = () => {
  if (nodes.value.length === 0) return
  
  const result = runAutoLayout(canvas)
  if (result.oldPositions.length > 0) {
    const command = createAutoLayoutCommand(
      result.oldPositions,
      result.newPositions,
      (id, x, y) => moveNode(id, x, y, canvas)
    )
    executeCommand(command)
  }
}

const handleClearAll = () => {
  if (nodes.value.length === 0 && connections.value.length === 0) return

  const oldNodes = nodes.value.map(n => ({
    id: n.id,
    nodeType: n.nodeType,
    name: n.name,
    description: n.description,
    x: n.x,
    y: n.y
  }))
  const oldConnections = connections.value.map(c => ({
    id: c.id,
    fromNodeId: c.fromNodeId,
    toNodeId: c.toNodeId
  }))

  const command = createClearAllCommand(
    oldNodes,
    oldConnections,
    (data) => addNodeFromData(data, canvas),
    () => clearAll(canvas),
    (conn) => addConnectionFromData(conn, canvas)
  )
  executeCommand(command)
  selectedNode.value = null
}

const handleUndo = () => {
  undo()
}

const handleRedo = () => {
  redo()
}

const exportJSON = () => {
  const data = exportToJSON()
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'flowchart.json'
  a.click()
  URL.revokeObjectURL(url)
}

const exportImage = () => {
  if (canvas) {
    const dataURL = canvas.toDataURL({
      format: 'png',
      quality: 1,
      multiplier: 2
    })
    const a = document.createElement('a')
    a.href = dataURL
    a.download = 'flowchart.png'
    a.click()
  }
}

const handleConnectionCreated = (connData) => {
  const connInfo = {
    id: connData.id,
    fromNodeId: connData.fromNodeId,
    toNodeId: connData.toNodeId
  }
  
  const command = createAddConnectionCommand(
    connInfo,
    (conn) => addConnectionFromData(conn, canvas),
    (id) => deleteConnection(id, canvas)
  )
  executeCommand(command)

  if (isConnected.value) {
    broadcastConnectionAdd(connInfo)
  }
}

const loadTemplate = (template) => {
  handleClearAll()
  
  setTimeout(() => {
    template.nodes.forEach(nodeData => {
      addNodeFromData({ ...nodeData }, canvas)
    })

    setTimeout(() => {
      template.connections.forEach(connData => {
        addConnectionFromData({ ...connData }, canvas)
      })
    }, 50)
  }, 50)
}

const handleAddComment = () => {
  if (selectedNode.value && newCommentText.value.trim()) {
    addComment(selectedNode.value.id, newCommentText.value.trim())
    newCommentText.value = ''
  }
}

const handleReplyComment = (comment) => {
  if (replyTexts[comment.id]?.trim()) {
    replyComment(comment.id, replyTexts[comment.id].trim())
    replyTexts[comment.id] = ''
  }
}

const handleResolveComment = (comment) => {
  resolveComment(comment.id, !comment.resolved)
}

const formatTime = (isoString) => {
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', { 
    month: 'numeric', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const toggleCollaboration = async () => {
  if (isConnected.value) {
    disconnect()
  } else {
    await connect(canvas, handleCollaborationMessage)
  }
}

const handleCollaborationMessage = (message) => {
  switch (message.type) {
    case 'CURSOR_MOVE':
      const collab = remoteCollaborators.value.find(c => c.id === message.payload.userId)
      if (collab) {
        collab.x = message.payload.x
        collab.y = message.payload.y
      }
      break
  }
}

const handleMouseMove = (e) => {
  if (isConnected.value && canvas) {
    const rect = canvasWrapper.value.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    broadcastCursor(x, y)
  }
}

onMounted(() => {
  if (canvasElement.value && canvasWrapper.value) {
    const wrapper = canvasWrapper.value
    canvas = initCanvas(canvasElement.value, wrapper.clientWidth, wrapper.clientHeight, handleConnectionCreated)
    
    canvas.on('selection:created', (e) => {
      if (e.selected && e.selected.length > 0) {
        const obj = e.selected[0]
        if (obj.nodeId) {
          selectNodeByFabric(obj)
          const node = nodes.value.find(n => n.id === obj.nodeId)
          if (node) {
            lastNodeData[node.id] = {
              name: node.name,
              description: node.description
            }
          }
        }
      }
    })

    canvas.on('selection:updated', (e) => {
      if (e.selected && e.selected.length > 0) {
        const obj = e.selected[0]
        if (obj.nodeId) {
          selectNodeByFabric(obj)
          const node = nodes.value.find(n => n.id === obj.nodeId)
          if (node) {
            lastNodeData[node.id] = {
              name: node.name,
              description: node.description
            }
          }
        }
      }
    })

    canvas.on('selection:cleared', () => {
      selectedNode.value = null
    })

    canvas.on('object:modified', (e) => {
      const obj = e.target
      if (obj && obj.nodeId && !obj.isConnection) {
        const node = nodes.value.find(n => n.id === obj.nodeId)
        if (node) {
          const command = createMoveNodeCommand(
            node.id,
            { x: node.x, y: node.y },
            { x: obj.left, y: obj.top },
            (id, x, y) => moveNode(id, x, y, canvas)
          )
          executeCommand(command)

          if (isConnected.value) {
            broadcastNodeMove(node.id, obj.left, obj.top)
          }
        }
      }
    })

    canvas.on('object:moving', (e) => {
      const obj = e.target
      if (obj && obj.nodeId && !obj.isConnection) {
        const node = nodes.value.find(n => n.id === obj.nodeId)
        if (node) {
          node.x = obj.left
          node.y = obj.top
        }
      }
    })

    wrapper.addEventListener('dragover', handleDragOver)
    wrapper.addEventListener('drop', handleDrop)
  }
})
</script>
