<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header">
      <h3 v-if="!isCollapsed">我的思维导图</h3>
      <button @click="$emit('toggle-collapse')" class="collapse-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline :points="isCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"></polyline>
        </svg>
      </button>
    </div>

    <div v-if="!isCollapsed" class="search-box">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索节点..."
        @input="handleSearch"
      />
      <button v-if="searchQuery" @click="clearSearch" class="clear-btn">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div v-if="searchResults.length > 0 && !isCollapsed" class="search-results">
      <div class="results-header">
        <span>搜索结果 ({{ searchResults.length }})</span>
      </div>
      <div class="results-list">
        <div
          v-for="node in searchResults"
          :key="node.id"
          class="result-item"
          @click="$emit('focus-node', node.id)"
        >
          <div class="result-dot" :style="{ background: node.color }"></div>
          <span class="result-text">{{ node.text }}</span>
        </div>
      </div>
    </div>

    <div v-if="!isCollapsed" class="mindmap-list">
      <div class="list-header">
        <span>文件列表</span>
        <button @click="$emit('new')" class="new-btn" title="新建">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>
      <div class="list-content">
        <div
          v-for="mindmap in mindmaps"
          :key="mindmap.id"
          :class="{ active: currentId === mindmap.id }"
          class="mindmap-item"
          @click="$emit('open', mindmap.id)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <div class="item-info">
            <span class="item-title">{{ mindmap.title }}</span>
            <span class="item-date">{{ formatDate(mindmap.updatedAt) }}</span>
          </div>
          <button
            class="delete-btn"
            @click.stop="$emit('delete', mindmap.id)"
            title="删除"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
        <div v-if="mindmaps.length === 0" class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <p>暂无思维导图</p>
          <button @click="$emit('new')" class="create-first">创建第一个</button>
        </div>
      </div>
    </div>

    <div v-if="!isCollapsed && selectedNode" class="node-info">
      <div class="info-header">
        <span>节点信息</span>
      </div>
      <div class="info-content">
        <div class="info-row">
          <span class="label">文本:</span>
          <span class="value">{{ selectedNode.text }}</span>
        </div>
        <div class="info-row">
          <span class="label">子节点:</span>
          <span class="value">{{ selectedNode.children?.length || 0 }}</span>
        </div>
        <div class="info-row">
          <span class="label">颜色:</span>
          <span class="color-dot" :style="{ background: selectedNode.color }"></span>
        </div>
        <div class="info-actions">
          <button @click="$emit('add-child')" class="action-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            添加子节点
          </button>
          <button @click="$emit('edit-node')" class="action-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            编辑
          </button>
          <button @click="$emit('delete-node')" class="action-btn danger">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            删除
          </button>
        </div>
      </div>
    </div>

    <div v-if="isCollapsed" class="collapsed-actions">
      <button @click="$emit('new')" title="新建">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      <button @click="$emit('search-toggle')" title="搜索">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  mindmaps: {
    type: Array,
    default: () => []
  },
  currentId: {
    type: String,
    default: null
  },
  selectedNode: {
    type: Object,
    default: null
  },
  isCollapsed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'toggle-collapse',
  'search',
  'focus-node',
  'new',
  'open',
  'delete',
  'add-child',
  'edit-node',
  'delete-node',
  'search-toggle'
])

const searchQuery = ref('')
const searchResults = ref([])

function handleSearch() {
  emit('search', searchQuery.value)
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  emit('search', '')
}

function formatDate(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return date.toLocaleDateString('zh-CN')
}

function updateSearchResults(results) {
  searchResults.value = results
}

defineExpose({
  updateSearchResults
})
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--header-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
}

.collapse-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.collapse-btn:hover {
  background: var(--border-color);
  color: var(--text-color);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.search-box svg {
  color: var(--info-color);
  flex-shrink: 0;
}

.search-box input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  color: var(--text-color);
  outline: none;
}

.search-box input::placeholder {
  color: var(--info-color);
}

.clear-btn {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: var(--info-color);
  transition: all 0.2s;
}

.clear-btn:hover {
  background: var(--border-color);
  color: var(--text-color);
}

.search-results {
  border-bottom: 1px solid var(--border-color);
}

.results-header {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--info-color);
  font-weight: 600;
}

.results-list {
  max-height: 150px;
  overflow-y: auto;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.result-item:hover {
  background: var(--border-color);
}

.result-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.result-text {
  font-size: 13px;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mindmap-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  font-size: 12px;
  color: var(--info-color);
  font-weight: 600;
}

.new-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.new-btn:hover {
  background: var(--primary-color);
  color: white;
}

.list-content {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.mindmap-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.mindmap-item:hover {
  background: var(--border-color);
}

.mindmap-item.active {
  background: var(--primary-color);
  color: white;
}

.mindmap-item.active .item-title,
.mindmap-item.active .item-date {
  color: white;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  display: block;
  font-size: 13px;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-date {
  display: block;
  font-size: 11px;
  color: var(--info-color);
  margin-top: 2px;
}

.delete-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--info-color);
  opacity: 0;
  transition: all 0.2s;
}

.mindmap-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: var(--danger-color);
  color: white;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-state svg {
  color: var(--border-color);
  margin-bottom: 12px;
}

.empty-state p {
  font-size: 13px;
  color: var(--info-color);
  margin-bottom: 16px;
}

.create-first {
  padding: 8px 16px;
  background: var(--primary-color);
  color: white;
  border-radius: 6px;
  font-size: 13px;
  transition: opacity 0.2s;
}

.create-first:hover {
  opacity: 0.9;
}

.node-info {
  border-top: 1px solid var(--border-color);
  padding: 12px;
}

.info-header {
  font-size: 12px;
  color: var(--info-color);
  font-weight: 600;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-row .label {
  color: var(--info-color);
  min-width: 50px;
}

.info-row .value {
  color: var(--text-color);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.color-dot {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}

.info-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  flex: 1;
  min-width: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 10px;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-color);
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--border-color);
}

.action-btn.danger:hover {
  background: var(--danger-color);
  color: white;
  border-color: var(--danger-color);
}

.collapsed-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  gap: 12px;
}

.collapsed-actions button {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.collapsed-actions button:hover {
  background: var(--border-color);
  color: var(--primary-color);
}
</style>
