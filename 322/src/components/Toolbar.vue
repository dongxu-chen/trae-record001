<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <div class="logo">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#409eff" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="3" y1="9" x2="21" y2="9"></line>
          <line x1="9" y1="21" x2="9" y2="9"></line>
          <path d="M21 15l-5-5L5 21"></path>
        </svg>
        <span>图表标注工具</span>
      </div>
    </div>

    <div class="toolbar-center">
      <div class="tool-group">
        <div
          class="tool-item"
          :class="{ active: currentTool === 'select' }"
          @click="setTool('select')"
          title="选择 (V)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 11l-6 8h18l-6-8-4-6z"></path>
          </svg>
          <span>选择</span>
        </div>

        <div
          class="tool-item"
          :class="{ active: currentTool === 'rectangle' }"
          @click="setTool('rectangle')"
          title="矩形框 (R)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          </svg>
          <span>矩形框</span>
        </div>

        <div
          class="tool-item"
          :class="{ active: currentTool === 'arrow' }"
          @click="setTool('arrow')"
          title="箭头 (A)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
          <span>箭头</span>
        </div>

        <div
          class="tool-item"
          :class="{ active: currentTool === 'text' }"
          @click="setTool('text')"
          title="文本 (T)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="4 7 4 4 20 4 20 7"></polyline>
            <line x1="9" y1="20" x2="15" y2="20"></line>
            <line x1="12" y1="4" x2="12" y2="20"></line>
          </svg>
          <span>文本</span>
        </div>

        <div
          class="tool-item"
          :class="{ active: currentTool === 'pan' }"
          @click="setTool('pan')"
          title="平移 (H)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 11v5a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-5"></path>
            <path d="M4 14h4v-4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4h4"></path>
            <polyline points="15 11 12 8 9 11"></polyline>
          </svg>
          <span>平移</span>
        </div>
      </div>

      <div class="divider"></div>

      <div class="tool-group">
        <div
          class="tool-item"
          :class="{ active: snapEnabled }"
          @click="toggleSnap"
          :title="snapEnabled ? '关闭磁吸吸附' : '开启磁吸吸附'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="4" y1="20" x2="4" y2="10"></line>
            <line x1="4" y1="20" x2="14" y2="20"></line>
            <path d="M4 20l7-7"></path>
            <line x1="10" y1="8" x2="10" y2="4"></line>
            <line x1="10" y1="4" x2="20" y2="4"></line>
            <path d="M10 4l7 7"></path>
            <line x1="4" y1="14" x2="20" y2="14" stroke-dasharray="4,4"></line>
            <line x1="14" y1="4" x2="14" y2="20" stroke-dasharray="4,4"></line>
          </svg>
          <span>磁吸</span>
        </div>
      </div>

      <div class="divider"></div>

      <div class="tool-group">
        <div class="tool-item" @click="undo" :title="'撤销 (Ctrl+Z)'" :disabled="!canUndo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          <span>撤销</span>
        </div>

        <div class="tool-item" @click="redo" :title="'重做 (Ctrl+Y)'" :disabled="!canRedo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.13-9.36L23 10"></path>
          </svg>
          <span>重做</span>
        </div>
      </div>

      <div class="divider"></div>

      <div class="tool-group">
        <div class="tool-item" @click="zoomIn" title="放大">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            <line x1="11" y1="8" x2="11" y2="14"></line>
            <line x1="8" y1="11" x2="14" y2="11"></line>
          </svg>
          <span>放大</span>
        </div>

        <div class="tool-item" @click="zoomOut" title="缩小">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            <line x1="8" y1="11" x2="14" y2="11"></line>
          </svg>
          <span>缩小</span>
        </div>

        <div class="tool-item" @click="resetZoom" title="重置视图">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
          </svg>
          <span>重置</span>
        </div>
      </div>
    </div>

    <div class="toolbar-right">
      <div class="connection-status" @click="showConnectionModal = true">
        <span class="status-dot" :class="connectionStatus"></span>
        <span>{{ connectionText }}</span>
      </div>

      <div class="online-users" v-if="onlineUsers.length > 0">
        <div
          v-for="user in onlineUsers.slice(0, 5)"
          :key="user.id"
          class="user-avatar"
          :style="{ backgroundColor: user.color }"
          :title="user.name"
        >
          {{ user.name.charAt(0) }}
        </div>
        <div v-if="onlineUsers.length > 5" class="user-avatar more">
          +{{ onlineUsers.length - 5 }}
        </div>
      </div>

      <button class="btn btn-secondary" @click="$emit('upload')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        上传图片
      </button>

      <button class="btn btn-purple" @click="$emit('ai-preannotate')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2a5 5 0 0 0-5 5v1a5 5 0 0 0-2 4v5a5 5 0 0 0 5 5h8a5 5 0 0 0 5-5v-5a5 5 0 0 0-2-4V7a5 5 0 0 0-5-5z"></path>
        </svg>
        AI 预标注
      </button>

      <button class="btn btn-info" @click="$emit('show-statistics')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="3" y1="9" x2="21" y2="9"></line>
          <line x1="9" y1="21" x2="9" y2="9"></line>
          <path d="M9 15l3-3 3 3 4-4"></path>
        </svg>
        统计
      </button>

      <button class="btn btn-secondary" @click="$emit('show-shortcuts')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
          <line x1="6" y1="8" x2="6" y2="8"></line>
          <line x1="10" y1="8" x2="10" y2="8"></line>
          <line x1="14" y1="8" x2="14" y2="8"></line>
          <line x1="18" y1="8" x2="18" y2="8"></line>
          <line x1="8" y1="12" x2="8" y2="12"></line>
          <line x1="12" y1="12" x2="12" y2="12"></line>
          <line x1="16" y1="12" x2="16" y2="12"></line>
          <line x1="10" y1="16" x2="14" y2="16"></line>
        </svg>
        快捷键
      </button>

      <button class="btn btn-primary" @click="$emit('check-quality')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        质量检查
      </button>

      <button class="btn btn-success" @click="$emit('export')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        导出
      </button>
    </div>

    <div v-if="showConnectionModal" class="modal-overlay" @click.self="showConnectionModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>协作连接设置</h3>
          <button class="modal-close" @click="showConnectionModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>用户名</label>
            <input type="text" v-model="userName" placeholder="输入您的用户名" />
          </div>
          <div class="form-group">
            <label>房间号</label>
            <input type="text" v-model="roomId" placeholder="输入协作房间号" />
          </div>
          <div class="form-group">
            <label>WebSocket 服务器地址</label>
            <input type="text" v-model="wsUrl" placeholder="ws://localhost:8080" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="disconnect">断开连接</button>
          <button class="btn btn-primary" @click="connect">连接</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { TOOL_MODES, CONNECTION_STATUS } from '../constants'
import canvasManager from '../utils/canvasManager'
import wsClient from '../utils/websocket'

const emit = defineEmits(['upload', 'export', 'check-quality', 'tool-change', 'category-change', 'ai-preannotate', 'show-statistics', 'show-shortcuts'])

const currentTool = computed(() => canvasManager.currentTool.value)
const connectionStatus = computed(() => wsClient.status.value)
const onlineUsers = computed(() => wsClient.users.value)
const canUndo = computed(() => canvasManager.historyStack.length > 0)
const canRedo = computed(() => canvasManager.redoStack.length > 0)
const snapEnabled = computed(() => canvasManager.snapEnabled.value)

const showConnectionModal = ref(false)
const userName = ref(wsClient.userName)
const roomId = ref('default')
const wsUrl = ref('ws://localhost:8080')

const connectionText = computed(() => {
  const statusMap = {
    [CONNECTION_STATUS.ONLINE]: '已连接',
    [CONNECTION_STATUS.OFFLINE]: '未连接',
    [CONNECTION_STATUS.CONNECTING]: '连接中...'
  }
  return statusMap[connectionStatus.value] || '未知'
})

const toggleSnap = () => {
  canvasManager.setSnapEnabled(!snapEnabled.value)
}

const setTool = (tool) => {
  canvasManager.setTool(tool)
  emit('tool-change', tool)
}

const undo = () => {
  canvasManager.undo()
}

const redo = () => {
  canvasManager.redo()
}

const zoomIn = () => {
  if (canvasManager.canvas) {
    canvasManager.canvas.setZoom(canvasManager.canvas.getZoom() * 1.2)
  }
}

const zoomOut = () => {
  if (canvasManager.canvas) {
    canvasManager.canvas.setZoom(canvasManager.canvas.getZoom() * 0.8)
  }
}

const resetZoom = () => {
  if (canvasManager.canvas) {
    canvasManager.canvas.setZoom(1)
    canvasManager.canvas.viewportTransform = [1, 0, 0, 1, 0, 0]
    canvasManager.canvas.renderAll()
  }
}

const connect = async () => {
  try {
    wsClient.setUserName(userName.value)
    await wsClient.connect(wsUrl.value, roomId.value)
    showConnectionModal.value = false
  } catch (error) {
    alert('连接失败: ' + error.message)
  }
}

const disconnect = () => {
  wsClient.disconnect()
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 64px;
  background-color: #fff;
  border-bottom: 1px solid #ebeef5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.tool-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  color: #606266;
  min-width: 56px;
}

.tool-item:hover {
  background-color: #ecf5ff;
  color: #409eff;
}

.tool-item.active {
  background-color: #ecf5ff;
  color: #409eff;
}

.tool-item:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tool-item svg {
  width: 20px;
  height: 20px;
  margin-bottom: 2px;
}

.tool-item span {
  font-size: 11px;
}

.divider {
  width: 1px;
  height: 40px;
  background-color: #e4e7ed;
  margin: 0 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 4px;
  background-color: #f5f7fa;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.connection-status:hover {
  background-color: #ecf5ff;
}

.online-users {
  display: flex;
  align-items: center;
  gap: -4px;
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  border: 2px solid #fff;
  margin-left: -6px;
}

.user-avatar:first-child {
  margin-left: 0;
}

.user-avatar.more {
  background-color: #909399;
}

.btn-purple {
  background: linear-gradient(135deg, #9c27b0 0%, #ba68c8 100%);
  color: #fff;
  border: none;
}

.btn-purple:hover {
  background: linear-gradient(135deg, #7b1fa2 0%, #9c27b0 100%);
}

.btn-info {
  background: linear-gradient(135deg, #00bcd4 0%, #4dd0e1 100%);
  color: #fff;
  border: none;
}

.btn-info:hover {
  background: linear-gradient(135deg, #0097a7 0%, #00bcd4 100%);
}
</style>
