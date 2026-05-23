<template>
  <div class="layer-panel">
    <div class="panel-header">
      <span>📚 图层</span>
      <span class="layer-count">{{ layers.length }} 个</span>
    </div>
    <div class="layer-list">
      <div
        v-for="(layer, index) in reversedLayers"
        :key="layer.id"
        class="layer-item"
        :class="{ selected: selectedLayerId === layer.id }"
        @click="selectLayer(layer.id)"
      >
        <div class="layer-info">
          <span class="layer-icon">{{ getLayerIcon(layer.type) }}</span>
          <span class="layer-name">{{ getLayerName(layer) }}</span>
        </div>
        <div class="layer-actions">
          <button class="action-btn" @click.stop="toggleVisibility(layer.id)" :title="layer.visible ? '隐藏' : '显示'">
            {{ layer.visible ? '👁️' : '👁️‍🗨️' }}
          </button>
          <button class="action-btn" @click.stop="moveLayer(layer.id, -1)" :disabled="index === layers.length - 1" title="上移">
            ⬆️
          </button>
          <button class="action-btn" @click.stop="moveLayer(layer.id, 1)" :disabled="index === 0" title="下移">
            ⬇️
          </button>
          <button class="action-btn delete" @click.stop="deleteLayer(layer.id)" title="删除">
            🗑️
          </button>
        </div>
      </div>
      <div v-if="layers.length === 0" class="empty-state">
        暂无图层
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  layers: { type: Array, default: () => [] },
  selectedLayerId: { type: String, default: null }
})

const emit = defineEmits(['select', 'toggleVisibility', 'move', 'delete'])

const reversedLayers = computed(() => [...props.layers].reverse())

function getLayerIcon(type) {
  const icons = {
    pen: '✏️',
    line: '📏',
    rectangle: '⬜',
    circle: '⭕',
    text: '📝',
    eraser: '🧹'
  }
  return icons[type] || '📄'
}

function getLayerName(layer) {
  const names = {
    pen: '画笔',
    line: '直线',
    rectangle: '矩形',
    circle: '圆形',
    text: layer.text || '文本',
    eraser: '橡皮擦'
  }
  return names[layer.type] || '未知'
}

function selectLayer(id) {
  emit('select', id)
}

function toggleVisibility(id) {
  emit('toggleVisibility', id)
}

function moveLayer(id, direction) {
  emit('move', { id, direction })
}

function deleteLayer(id) {
  if (confirm('确定要删除这个图层吗？')) {
    emit('delete', id)
  }
}
</script>

<style scoped>
.layer-panel {
  width: 280px;
  height: 100%;
  background: var(--toolbar-bg);
  border-left: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.layer-count {
  font-size: 12px;
  color: var(--secondary-color);
  font-weight: normal;
}

.layer-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.layer-item {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: var(--border-radius);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background 0.2s;
  border: 1px solid transparent;
}

.layer-item:hover {
  background: #f3f4f6;
}

.layer-item.selected {
  background: #eff6ff;
  border-color: var(--primary-color);
}

.layer-info {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.layer-icon {
  font-size: 16px;
}

.layer-name {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.layer-actions {
  display: flex;
  gap: 2px;
}

.action-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #e5e7eb;
  opacity: 1;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.action-btn.delete:hover {
  background: #fee2e2;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--secondary-color);
  font-size: 14px;
}
</style>
