<template>
  <div class="left-panel">
    <div class="panel-header">组件列表</div>
    <div class="component-list">
      <div
        v-for="comp in componentTypes"
        :key="comp.type"
        class="component-item"
        :data-type="comp.type"
        draggable="true"
        @dragstart="handleDragStart"
      >
        <span class="component-icon">{{ comp.icon }}</span>
        <span>{{ comp.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { componentTypes } from './componentConfig.js'

const emit = defineEmits(['addComponent'])

const handleDragStart = (e) => {
  e.dataTransfer.effectAllowed = 'copy'
  e.dataTransfer.setData('text/plain', e.target.dataset.type)
}
</script>

<style scoped>
.left-panel {
  background: #fff;
}

.panel-header {
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #e8e8e8;
  background: #fafafa;
}

.component-list {
  padding: 12px;
}

.component-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.component-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
  color: #409eff;
}

.component-item:active {
  cursor: grabbing;
}

.component-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
</style>
