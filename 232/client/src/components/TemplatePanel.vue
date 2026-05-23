<template>
  <div class="template-panel" :class="{ open: isOpen }">
    <div class="panel-header" @click="togglePanel">
      <span>📚 模板库</span>
      <span class="toggle-icon">{{ isOpen ? '◀' : '▶' }}</span>
    </div>
    
    <div v-if="isOpen" class="panel-content">
      <div class="category-tabs">
        <button
          v-for="cat in categories"
          :key="cat.id"
          class="tab-btn"
          :class="{ active: activeCategory === cat.id }"
          @click="activeCategory = cat.id"
        >
          {{ cat.icon }} {{ cat.name }}
        </button>
      </div>
      
      <div class="template-list">
        <div
          v-for="template in filteredTemplates"
          :key="template.id"
          class="template-card"
          @click="applyTemplate(template)"
        >
          <div class="template-icon">{{ template.icon }}</div>
          <div class="template-info">
            <div class="template-name">{{ template.name }}</div>
            <div class="template-desc">{{ template.description }}</div>
          </div>
          <div class="apply-btn">使用</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { templates, templateCategories } from '../data/templates.js'

const emit = defineEmits(['applyTemplate'])

const isOpen = ref(false)
const activeCategory = ref('flowchart')

const categories = templateCategories

const filteredTemplates = computed(() => {
  return templates.filter(t => t.category === activeCategory.value)
})

function togglePanel() {
  isOpen.value = !isOpen.value
}

function applyTemplate(template) {
  if (confirm(`确定要应用模板「${template.name}」吗？这将清空当前画布内容。`)) {
    emit('applyTemplate', template)
  }
}
</script>

<style scoped>
.template-panel {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  background: var(--toolbar-bg);
  border-radius: 0 var(--border-radius) var(--border-radius) 0;
  box-shadow: var(--shadow);
  z-index: 100;
  transition: all 0.3s;
  max-height: 80vh;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  white-space: nowrap;
  font-weight: 500;
  border-bottom: 1px solid #e5e7eb;
}

.toggle-icon {
  font-size: 12px;
  color: var(--secondary-color);
}

.panel-content {
  width: 280px;
  max-height: calc(80vh - 50px);
  overflow-y: auto;
}

.category-tabs {
  display: flex;
  padding: 8px;
  gap: 4px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.tab-btn {
  flex: 1;
  padding: 8px 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 6px;
  font-size: 12px;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #e5e7eb;
}

.tab-btn.active {
  background: var(--primary-color);
  color: white;
}

.template-list {
  padding: 8px;
}

.template-card {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: white;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e5e7eb;
  gap: 12px;
}

.template-card:hover {
  border-color: var(--primary-color);
  background: #eff6ff;
  transform: translateX(4px);
}

.template-icon {
  font-size: 28px;
}

.template-info {
  flex: 1;
}

.template-name {
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 2px;
}

.template-desc {
  font-size: 11px;
  color: var(--secondary-color);
}

.apply-btn {
  padding: 6px 12px;
  background: var(--primary-color);
  color: white;
  border-radius: 6px;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
}

.template-card:hover .apply-btn {
  opacity: 1;
}
</style>
