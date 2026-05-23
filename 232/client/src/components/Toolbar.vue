<template>
  <div class="toolbar">
    <div class="tool-group">
      <button class="btn btn-icon" :class="{ active: tool === 'pen' }" @click="$emit('update:tool', 'pen')" title="画笔">
        ✏️
      </button>
      <button class="btn btn-icon" :class="{ active: tool === 'line' }" @click="$emit('update:tool', 'line')" title="直线">
        📏
      </button>
      <button class="btn btn-icon" :class="{ active: tool === 'rectangle' }" @click="$emit('update:tool', 'rectangle')" title="矩形">
        ⬜
      </button>
      <button class="btn btn-icon" :class="{ active: tool === 'circle' }" @click="$emit('update:tool', 'circle')" title="圆形">
        ⭕
      </button>
      <button class="btn btn-icon" :class="{ active: tool === 'text' }" @click="$emit('update:tool', 'text')" title="文本(双击添加)">
        📝
      </button>
      <button class="btn btn-icon" :class="{ active: tool === 'eraser' }" @click="$emit('update:tool', 'eraser')" title="橡皮擦">
        🧹
      </button>
    </div>

    <div class="divider"></div>

    <div class="tool-group">
      <input type="color" :value="color" @input="$emit('update:color', $event.target.value)" title="颜色">
      <input type="range" min="1" max="20" :value="lineWidth" @input="$emit('update:lineWidth', Number($event.target.value))" title="线宽">
      <span class="line-width-label">{{ lineWidth }}px</span>
    </div>

    <div class="divider"></div>

    <div class="tool-group">
      <button class="btn btn-icon" @click="$emit('undo')" :disabled="!canUndo" title="撤销 (Ctrl+Z)">
        ↩️
      </button>
      <button class="btn btn-icon" @click="$emit('redo')" :disabled="!canRedo" title="重做 (Ctrl+Y)">
        ↪️
      </button>
    </div>

    <div class="divider"></div>

    <div class="tool-group">
      <button class="btn btn-icon" @click="$emit('zoomIn')" title="放大">
        🔍+
      </button>
      <button class="btn btn-icon" @click="$emit('zoomOut')" title="缩小">
        🔍-
      </button>
      <button class="btn btn-icon" @click="$emit('resetView')" title="重置视图">
        🏠
      </button>
    </div>

    <div class="divider"></div>

    <div class="tool-group">
      <button class="btn btn-icon" @click="$emit('snapshot')" title="保存为图片">
        📸
      </button>
      <button class="btn btn-icon" @click="$emit('presentation')" title="演示模式 (Ctrl+P)">
        🎬
      </button>
      <button class="btn btn-icon" @click="$emit('clear')" title="清空画布">
        🗑️
      </button>
    </div>

    <div class="divider"></div>

    <div class="tool-group session-info">
      <span class="connection-status" :class="{ connected: isConnected }">
        {{ isConnected ? '🟢 已连接' : '🔴 未连接' }}
      </span>
      <span class="user-count">👥 {{ userCount }}人在线</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  tool: { type: String, default: 'pen' },
  color: { type: String, default: '#000000' },
  lineWidth: { type: Number, default: 3 },
  canUndo: { type: Boolean, default: false },
  canRedo: { type: Boolean, default: false },
  isConnected: { type: Boolean, default: false },
  userCount: { type: Number, default: 0 }
})

defineEmits([
  'update:tool',
  'update:color',
  'update:lineWidth',
  'undo',
  'redo',
  'zoomIn',
  'zoomOut',
  'resetView',
  'snapshot',
  'presentation',
  'clear'
])
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--toolbar-bg);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid #e5e7eb;
  box-shadow: var(--shadow);
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.divider {
  width: 1px;
  height: 24px;
  background: #e5e7eb;
  margin: 0 4px;
}

.line-width-label {
  font-size: 12px;
  color: var(--secondary-color);
  min-width: 30px;
}

.session-info {
  margin-left: auto;
  font-size: 12px;
  gap: 12px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.connection-status.connected {
  color: #22c55e;
}

.user-count {
  color: var(--secondary-color);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
