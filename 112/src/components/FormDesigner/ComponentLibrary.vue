<template>
  <aside class="component-library">
    <h3>组件库</h3>
    <div class="component-list">
      <div
        v-for="component in componentList"
        :key="component.type"
        class="component-item"
        draggable="true"
        @dragstart="handleDragStart($event, component)"
      >
        <el-icon class="component-icon">
          <component :is="component.icon" />
        </el-icon>
        <span class="component-label">{{ component.label }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { componentList } from './config/componentConfig.js'

const emit = defineEmits(['drag-start'])

function handleDragStart(event, component) {
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('text/plain', JSON.stringify(component))
  emit('drag-start', component)
}
</script>

<style scoped>
.component-library {
  width: 240px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  padding: 16px;
  overflow-y: auto;
}

.component-library h3 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.component-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.component-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 8px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: grab;
  transition: all 0.2s;
  user-select: none;
}

.component-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.component-item:active {
  cursor: grabbing;
}

.component-icon {
  font-size: 24px;
  color: #409eff;
  margin-bottom: 8px;
}

.component-label {
  font-size: 12px;
  color: #606266;
  text-align: center;
}
</style>
