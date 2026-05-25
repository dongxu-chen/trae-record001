<template>
  <div class="sidebar">
    <div class="sidebar-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-item"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        <component :is="tab.icon" />
        <span>{{ tab.name }}</span>
      </div>
    </div>

    <div class="sidebar-content">
      <div v-show="activeTab === 'categories'" class="tab-panel">
        <h4 class="panel-title">标注分类</h4>
        <div class="category-list">
          <div
            v-for="cat in categories"
            :key="cat.id"
            class="category-item"
            :class="{ active: currentCategory === cat.id }"
            @click="selectCategory(cat.id)"
          >
            <span class="category-color" :style="{ backgroundColor: cat.color }"></span>
            <div class="category-info">
              <span class="category-name">{{ cat.name }}</span>
              <span class="category-desc">{{ cat.description }}</span>
            </div>
            <span class="category-count">{{ getCategoryCount(cat.id) }}</span>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'annotations'" class="tab-panel">
        <div class="panel-header">
          <h4 class="panel-title">标注列表</h4>
          <span class="annotation-total">{{ annotations.length }} 个</span>
        </div>
        <div class="annotation-list" v-if="annotations.length > 0">
          <div
            v-for="ann in annotations"
            :key="ann.id"
            class="annotation-item"
            :class="{ active: selectedAnnotation?.id === ann.id }"
            @click="selectAnnotation(ann)"
          >
            <span class="ann-type-icon">
              <svg v-if="ann.type === 'rectangle'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              </svg>
              <svg v-else-if="ann.type === 'arrow'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="4 7 4 4 20 4 20 7"></polyline>
                <line x1="9" y1="20" x2="15" y2="20"></line>
                <line x1="12" y1="4" x2="12" y2="20"></line>
              </svg>
            </span>
            <div class="ann-info">
              <div class="ann-header">
                <span class="ann-label">{{ ann.label || '未命名' }}</span>
                <span class="ann-category-tag" :style="{ backgroundColor: ann.color + '20', color: ann.color }">
                  {{ getCategoryName(ann.category) }}
                </span>
              </div>
              <span class="ann-type">{{ getTypeName(ann.type) }}</span>
            </div>
            <button class="ann-delete" @click.stop="deleteAnnotation(ann.id)" title="删除">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
        <div v-else class="empty-annotations">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#c0c4cc" stroke-width="1">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="9" x2="15" y2="9"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
          </svg>
          <p>暂无标注</p>
        </div>
      </div>

      <div v-show="activeTab === 'properties'" class="tab-panel">
        <h4 class="panel-title">属性</h4>
        <div v-if="selectedAnnotation" class="property-form">
          <div class="form-group">
            <label>标注类型</label>
            <div class="property-value">{{ getTypeName(selectedAnnotation.type) }}</div>
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="editCategory" @change="updateCategory">
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>标签</label>
            <input
              type="text"
              v-model="editLabel"
              placeholder="输入标签说明"
              @blur="updateLabel"
              @keyup.enter="updateLabel"
            />
          </div>
          <div v-if="selectedAnnotation.imageCoords" class="form-group">
            <label>坐标信息</label>
            <div class="coords-info">
              <span v-if="selectedAnnotation.type === 'rectangle'">
                X: {{ selectedAnnotation.imageCoords.x.toFixed(1) }},
                Y: {{ selectedAnnotation.imageCoords.y.toFixed(1) }},
                W: {{ selectedAnnotation.imageCoords.width.toFixed(1) }},
                H: {{ selectedAnnotation.imageCoords.height.toFixed(1) }}
              </span>
              <span v-else-if="selectedAnnotation.type === 'arrow'">
                ({{ selectedAnnotation.imageCoords.x1.toFixed(1) }}, {{ selectedAnnotation.imageCoords.y1.toFixed(1) }})
                →
                ({{ selectedAnnotation.imageCoords.x2.toFixed(1) }}, {{ selectedAnnotation.imageCoords.y2.toFixed(1) }})
              </span>
              <span v-else>
                X: {{ selectedAnnotation.imageCoords.x.toFixed(1) }},
                Y: {{ selectedAnnotation.imageCoords.y.toFixed(1) }}
              </span>
            </div>
          </div>
          <div class="form-group">
            <label>创建时间</label>
            <div class="property-value">{{ formatTime(selectedAnnotation.createdAt) }}</div>
          </div>
          <button class="btn btn-danger" style="width: 100%" @click="deleteAnnotation(selectedAnnotation.id)">
            删除此标注
          </button>
        </div>
        <div v-else class="empty-properties">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#c0c4cc" stroke-width="1">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <p>选择一个标注查看属性</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, h } from 'vue'
import { ANNOTATION_CATEGORIES, ANNOTATION_TYPES } from '../constants'
import canvasManager from '../utils/canvasManager'

const props = defineProps({
  annotations: {
    type: Array,
    default: () => []
  },
  selectedAnnotation: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:selectedAnnotation', 'category-change', 'annotation-delete', 'annotation-update'])

const activeTab = ref('categories')
const editLabel = ref('')
const editCategory = ref('')

const tabs = [
  {
    id: 'categories',
    name: '分类',
    icon: () => h('svg', { width: '18', height: '18', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z' }),
      h('line', { x1: '7', y1: '7', x2: '7.01', y2: '7' })
    ])
  },
  {
    id: 'annotations',
    name: '标注',
    icon: () => h('svg', { width: '18', height: '18', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' })
    ])
  },
  {
    id: 'properties',
    name: '属性',
    icon: () => h('svg', { width: '18', height: '18', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('circle', { cx: '12', cy: '12', r: '3' }),
      h('path', { d: 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z' })
    ])
  }
]

const categories = ANNOTATION_CATEGORIES
const currentCategory = computed(() => canvasManager.currentCategory.value)
const annotations = computed(() => canvasManager.annotations.value)

watch(() => props.selectedAnnotation, (val) => {
  if (val) {
    editLabel.value = val.label || ''
    editCategory.value = val.category
  }
})

const getCategoryCount = (categoryId) => {
  return props.annotations.filter(a => a.category === categoryId).length
}

const getCategoryName = (categoryId) => {
  const cat = categories.find(c => c.id === categoryId)
  return cat ? cat.name : categoryId
}

const getTypeName = (type) => {
  const typeMap = {
    [ANNOTATION_TYPES.RECTANGLE]: '矩形框',
    [ANNOTATION_TYPES.ARROW]: '箭头',
    [ANNOTATION_TYPES.TEXT]: '文本'
  }
  return typeMap[type] || type
}

const selectCategory = (categoryId) => {
  canvasManager.setCategory(categoryId)
  emit('category-change', categoryId)
}

const selectAnnotation = (annotation) => {
  const obj = canvasManager.findObjectById(annotation.id)
  if (obj) {
    canvasManager.canvas.setActiveObject(obj)
    canvasManager.canvas.renderAll()
  }
  emit('update:selectedAnnotation', annotation)
}

const deleteAnnotation = (annotationId) => {
  if (confirm('确定要删除此标注吗？')) {
    canvasManager.deleteAnnotation(annotationId)
    emit('annotation-delete', annotationId)
  }
}

const updateLabel = () => {
  if (props.selectedAnnotation) {
    const updated = canvasManager.updateAnnotation(props.selectedAnnotation.id, {
      label: editLabel.value
    })
    if (updated) {
      emit('annotation-update', updated)
    }
  }
}

const updateCategory = () => {
  if (props.selectedAnnotation) {
    const updated = canvasManager.updateAnnotation(props.selectedAnnotation.id, {
      category: editCategory.value
    })
    if (updated) {
      emit('annotation-update', updated)
    }
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}
</script>

<style scoped>
.sidebar {
  width: 320px;
  background-color: #fff;
  border-left: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-tabs {
  display: flex;
  border-bottom: 1px solid #ebeef5;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 8px;
  cursor: pointer;
  color: #909399;
  transition: all 0.2s;
  gap: 4px;
  font-size: 12px;
}

.tab-item:hover {
  background-color: #f5f7fa;
  color: #606266;
}

.tab-item.active {
  color: #409eff;
  border-bottom: 2px solid #409eff;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
}

.tab-panel {
  padding: 16px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.annotation-total {
  font-size: 12px;
  color: #909399;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.category-item:hover {
  background-color: #f5f7fa;
}

.category-item.active {
  background-color: #ecf5ff;
  border-color: #409eff;
}

.category-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  flex-shrink: 0;
}

.category-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.category-desc {
  font-size: 11px;
  color: #909399;
}

.category-count {
  font-size: 12px;
  color: #909399;
  background-color: #f5f7fa;
  padding: 2px 8px;
  border-radius: 10px;
}

.annotation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.annotation-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.annotation-item:hover {
  background-color: #f5f7fa;
}

.annotation-item.active {
  background-color: #ecf5ff;
  border-left-color: #409eff;
}

.ann-type-icon {
  color: #606266;
  flex-shrink: 0;
}

.ann-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.ann-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ann-label {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ann-category-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  flex-shrink: 0;
}

.ann-type {
  font-size: 11px;
  color: #909399;
}

.ann-delete {
  background: none;
  border: none;
  cursor: pointer;
  color: #c0c4cc;
  padding: 4px;
  border-radius: 4px;
  opacity: 0;
  transition: all 0.2s;
}

.annotation-item:hover .ann-delete {
  opacity: 1;
}

.ann-delete:hover {
  color: #f56c6c;
  background-color: #fef0f0;
}

.empty-annotations,
.empty-properties {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
  text-align: center;
  gap: 12px;
}

.property-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.property-value {
  font-size: 13px;
  color: #606266;
  background-color: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
}

.coords-info {
  font-size: 12px;
  color: #606266;
  background-color: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  font-family: monospace;
  line-height: 1.5;
}
</style>
